"""Lista os documentos dentro de cada processo dos blocos prioritários do SEI/ICMBio.

Para cada processo nos blocos prioritários, navega até sua página no SEI e extrai
a lista de documentos (título, id interno) sem ler seu conteúdo.

Depende de: 01_fontes_web/sei/blocos_internos.json (gerado por listar_blocos_sei.py)

Credenciais lidas de variáveis de ambiente:
    SEI_LOGIN   — login institucional
    SEI_SENHA   — senha

Uso:
    export SEI_LOGIN=seu.login
    export SEI_SENHA=sua_senha
    python3 scripts/coleta/listar_documentos_sei.py

    # Processar apenas um bloco específico (para testes):
    python3 scripts/coleta/listar_documentos_sei.py --bloco "Comitê Científico do RAN"

    # Retomar execução anterior (pula processos já catalogados):
    python3 scripts/coleta/listar_documentos_sei.py --retomar

Saída: 01_fontes_web/sei/documentos_por_processo.json
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_SIP = "https://sei.icmbio.gov.br/sip/"
BASE_SEI = "https://sei.icmbio.gov.br/sei/"
LOGIN_URL = (
    BASE_SIP
    + "login.php?sigla_orgao_sistema=ICMBio&sigla_sistema=SEI&infra_url=L3NlaS8="
)
INPUT_FILE = Path(__file__).resolve().parents[2] / "01_fontes_web" / "sei" / "blocos_internos.json"
OUTPUT_FILE = Path(__file__).resolve().parents[2] / "01_fontes_web" / "sei" / "documentos_por_processo.json"
ATRASO = 1.2  # segundos entre requisições

BLOCOS_PRIORITARIOS = {
    "Avaliação do risco de extinção da Herpetofauna",
    "Processo de Avaliação do Estado de Conservação da Fauna",
    "PAN Cerrado Pantanal - CERPAN",
    "PAN Nordeste",
    "PAN Sul",
    "PAN Sudeste",
    "PAN Espinhaço",
    "PAN Baixo Iguaçu",
    "PAN Paraíba do Sul",
    "Quelônios amazônicos",
    "Crocodilianos",
    "Monitoramento da fauna / Programa Monitora/Plano de Manejo.",
    "Processos do Alvo Complementar Quelônios Amazônicos - Programa Monitora - Ana Paula e Lilian",
    "Espécies Invasoras/Espécies Migratórias",
    "Guias/Publicações",
    "Comitê Científico do RAN",
}


# ---------------------------------------------------------------------------
# Sessão e login
# ---------------------------------------------------------------------------

def criar_sessao() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    })
    return s


def fazer_login(sessao: requests.Session, login: str, senha: str) -> BeautifulSoup:
    """Faz login no SEI e retorna o soup da página principal pós-login."""
    resp = sessao.get(LOGIN_URL, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")
    form = soup.find("form")
    if not form:
        raise RuntimeError("Formulário de login não encontrado.")

    dados = {
        inp.get("name"): inp.get("value", "")
        for inp in form.find_all("input")
        if inp.get("name")
    }
    dados["txtUsuario"] = login
    dados["pwdSenha"] = senha
    dados["hdnAcao"] = "2"
    dados.setdefault("selOrgao", "0")

    action = form.get("action") or LOGIN_URL
    if not action.startswith("http"):
        action = urljoin(BASE_SIP, action)

    resp = sessao.post(action, data=dados, timeout=30)
    resp.raise_for_status()

    if "controlador.php" not in resp.url and "sei/" not in resp.url:
        soup_erro = BeautifulSoup(resp.text, "lxml")
        msg = soup_erro.find(class_="infraMensagemErro") or soup_erro.find(id="divInfraMensagem")
        detalhe = msg.get_text(strip=True) if msg else "(sem mensagem de erro)"
        raise RuntimeError(f"Login falhou: {detalhe}\nURL: {resp.url}")

    return BeautifulSoup(resp.text, "lxml")


# ---------------------------------------------------------------------------
# Navegação nos blocos e processos
# ---------------------------------------------------------------------------

def obter_url_lista_blocos(soup_principal: BeautifulSoup) -> str:
    link = next(
        (a["href"] for a in soup_principal.find_all("a", href=True)
         if "bloco_interno_listar" in a["href"]),
        None,
    )
    if not link:
        raise RuntimeError("Link de blocos internos não encontrado na página principal.")
    return link if link.startswith("http") else urljoin(BASE_SEI, link)


def obter_processos_bloco(
    sessao: requests.Session,
    url_processos_bloco: str,
) -> list[dict]:
    """Retorna lista de processos do bloco com número e URL de acesso."""
    resp = sessao.get(url_processos_bloco, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")
    tabela = soup.find("table", class_="infraTable") or soup.find("table")
    if not tabela:
        return []

    # Colunas: [checkbox | Seq. | Processo | Tipo | Anotações | Ações]
    processos = []
    for linha in tabela.find_all("tr")[1:]:
        tds = linha.find_all("td")
        if len(tds) < 3:
            continue
        col_processo = tds[2]
        numero = col_processo.get_text(strip=True)
        if not numero:
            continue
        link = next(
            (a["href"] for a in col_processo.find_all("a", href=True)
             if "procedimento_trabalhar" in a["href"]),
            None,
        )
        url = (link if link.startswith("http") else urljoin(BASE_SEI, link)) if link else None
        tipo = tds[3].get_text(strip=True) if len(tds) > 3 else ""
        anotacao = tds[4].get_text(strip=True) if len(tds) > 4 else ""
        processos.append({
            "numero": numero,
            "tipo": tipo,
            "anotacao": anotacao,
            "url": url,
        })

    return processos


# ---------------------------------------------------------------------------
# Extração de documentos de um processo
# ---------------------------------------------------------------------------

def _script_com_arvore(html: str) -> str:
    """Retorna o conteúdo do <script> que contém os nós da árvore SEI."""
    soup = BeautifulSoup(html, "lxml")
    for sc in soup.find_all("script"):
        if "infraArvoreNo" in sc.get_text():
            return sc.get_text()
    return ""


def _extrair_nos_documento(js: str) -> list[dict]:
    """
    Extrai nós DOCUMENTO do JavaScript da árvore SEI.

    Padrão: Nos[N] = new infraArvoreNo("DOCUMENTO","ID","PASTA","URL","IFRAME","TITULO",...)
    """
    padrao = re.compile(
        r'Nos\[\d+\] = new infraArvoreNo\('
        r'"DOCUMENTO",'       # tipo
        r'"(\d+)",'           # id interno
        r'"[^"]*",'           # pasta pai
        r'"([^"]*)",'         # url relativa
        r'"[^"]*",'           # target iframe
        r'"([^"]*)"'          # título
    )
    documentos = []
    for m in padrao.finditer(js):
        id_doc, url_rel, titulo = m.group(1), m.group(2), m.group(3)
        documentos.append({
            "id": id_doc,
            "titulo": titulo,
            "url_relativa": url_rel,
        })
    return documentos


def _url_abrir_todas_pastas(js: str) -> str | None:
    """Extrai a URL da ação ABRIR_PASTAS da árvore SEI."""
    m = re.search(
        r'infraArvoreAcao\("ABRIR_PASTAS","[^"]*","[^"]*","([^"]+)"',
        js,
    )
    return m.group(1) if m else None


def extrair_documentos_processo(
    sessao: requests.Session,
    url_processo: str,
) -> tuple[list[dict], str | None]:
    """
    Navega ao processo, abre todas as pastas e extrai a lista de documentos.

    Retorna (documentos, erro_str). Se erro_str não for None, a extração falhou.
    """
    try:
        # 1. Página do processo → ifrArvore
        resp = sessao.get(url_processo, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        iframe = soup.find("iframe", id="ifrArvore")
        if not iframe:
            return [], "ifrArvore não encontrado na página do processo"

        # 2. Carrega a árvore
        url_arvore = urljoin(BASE_SEI, iframe["src"])
        time.sleep(ATRASO)
        resp2 = sessao.get(url_arvore, timeout=30)
        resp2.raise_for_status()
        js = _script_com_arvore(resp2.text)
        if not js:
            return [], "Script da árvore não encontrado"

        # 3. Tenta abrir todas as pastas para ver todos os documentos
        url_abrir = _url_abrir_todas_pastas(js)
        if url_abrir:
            url_abrir_abs = url_abrir if url_abrir.startswith("http") else urljoin(BASE_SEI, url_abrir)
            time.sleep(ATRASO)
            resp3 = sessao.get(url_abrir_abs, timeout=30)
            resp3.raise_for_status()
            js_completo = _script_com_arvore(resp3.text)
            if js_completo:
                js = js_completo

        documentos = _extrair_nos_documento(js)
        return documentos, None

    except requests.RequestException as e:
        return [], f"Erro de rede: {e}"
    except Exception as e:
        return [], f"Erro inesperado: {e}"


# ---------------------------------------------------------------------------
# Fluxo principal
# ---------------------------------------------------------------------------

def carregar_resultado_existente() -> dict:
    if OUTPUT_FILE.exists():
        return json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
    return {"data_coleta": date.today().isoformat(), "processos": []}


def salvar(resultado: dict) -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--bloco",
        metavar="NOME",
        help="Processa apenas o bloco com este nome (para testes).",
    )
    parser.add_argument(
        "--retomar",
        action="store_true",
        help="Retoma execução anterior, pulando processos já catalogados.",
    )
    args = parser.parse_args()

    login = os.environ.get("SEI_LOGIN")
    senha = os.environ.get("SEI_SENHA")
    if not login or not senha:
        print("Erro: defina SEI_LOGIN e SEI_SENHA antes de executar.", file=sys.stderr)
        sys.exit(1)

    if not INPUT_FILE.exists():
        print(f"Erro: {INPUT_FILE} não encontrado. Execute listar_blocos_sei.py primeiro.", file=sys.stderr)
        sys.exit(1)

    dados_blocos = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

    resultado = carregar_resultado_existente() if args.retomar else {
        "data_coleta": date.today().isoformat(),
        "processos": [],
    }
    ja_catalogados = {p["numero"] for p in resultado["processos"]} if args.retomar else set()

    # Filtra blocos a processar
    blocos = [
        b for b in dados_blocos["blocos"]
        if b["descricao"] in BLOCOS_PRIORITARIOS
        and (not args.bloco or b["descricao"] == args.bloco)
    ]

    if not blocos:
        print("Nenhum bloco encontrado com os critérios especificados.")
        sys.exit(0)

    print("Fazendo login no SEI/ICMBio...")
    sessao = criar_sessao()
    soup_principal = fazer_login(sessao, login, senha)
    print("Login realizado com sucesso.")

    url_lista_blocos = obter_url_lista_blocos(soup_principal)
    time.sleep(ATRASO)
    resp_blocos = sessao.get(url_lista_blocos, timeout=30)
    soup_blocos = BeautifulSoup(resp_blocos.text, "lxml")
    tabela_blocos = (
        soup_blocos.find("table", id="tblBlocos")
        or soup_blocos.find("table", class_="infraTable")
    )

    # Monta mapa: descrição → url_processos (com infra_hash fresco)
    mapa_url_blocos: dict[str, str] = {}
    for linha in tabela_blocos.find_all("tr")[1:]:
        descricao = linha.find_all("td")[7].get_text(strip=True) if len(linha.find_all("td")) > 7 else ""
        if descricao not in BLOCOS_PRIORITARIOS:
            continue
        link = next(
            (a["href"] for a in linha.find_all("a", href=True)
             if "rel_bloco_protocolo_listar" in a["href"]),
            None,
        )
        if link:
            mapa_url_blocos[descricao] = link if link.startswith("http") else urljoin(BASE_SEI, link)

    total_processos = sum(len(b["processos"]) for b in blocos)
    total_novos = total_processos - len(ja_catalogados)
    print(f"\n{len(blocos)} bloco(s) prioritário(s) | {total_processos} processo(s) | "
          f"{len(ja_catalogados)} já catalogados | {total_novos} a processar\n")

    processados = 0
    erros = 0

    for bloco in blocos:
        descricao_bloco = bloco["descricao"]
        print(f"=== {descricao_bloco} ({len(bloco['processos'])} proc) ===")

        url_processos_bloco = mapa_url_blocos.get(descricao_bloco)
        if not url_processos_bloco:
            print(f"  AVISO: URL do bloco não encontrada na listagem atual. Pulando.")
            continue

        time.sleep(ATRASO)
        processos_bloco = obter_processos_bloco(sessao, url_processos_bloco)

        for proc in processos_bloco:
            numero = proc["numero"]
            if numero in ja_catalogados:
                print(f"  [{numero}] já catalogado, pulando.")
                continue

            if not proc["url"]:
                print(f"  [{numero}] sem URL de acesso, pulando.")
                resultado["processos"].append({
                    "numero": numero,
                    "bloco": descricao_bloco,
                    "tipo": proc["tipo"],
                    "anotacao": proc["anotacao"],
                    "documentos": [],
                    "total_documentos": 0,
                    "erro": "URL do processo não disponível",
                })
                continue

            time.sleep(ATRASO)
            documentos, erro = extrair_documentos_processo(sessao, proc["url"])

            if erro:
                print(f"  [{numero}] ERRO: {erro}")
                erros += 1
            else:
                print(f"  [{numero}] {proc['tipo']} — {len(documentos)} doc(s)")

            resultado["processos"].append({
                "numero": numero,
                "bloco": descricao_bloco,
                "tipo": proc["tipo"],
                "anotacao": proc["anotacao"],
                "documentos": documentos,
                "total_documentos": len(documentos),
                "erro": erro,
            })
            ja_catalogados.add(numero)
            processados += 1

            # Salva a cada 10 processos para não perder progresso
            if processados % 10 == 0:
                resultado["data_coleta"] = date.today().isoformat()
                salvar(resultado)

        print()

    resultado["data_coleta"] = date.today().isoformat()
    salvar(resultado)

    total_docs = sum(p["total_documentos"] for p in resultado["processos"])
    print(f"Concluído: {processados} processo(s) catalogados | {erros} erro(s)")
    print(f"Total de documentos encontrados: {total_docs}")
    print(f"Salvo em {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

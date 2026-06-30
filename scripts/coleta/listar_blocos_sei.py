"""Lista os blocos internos do SEI/ICMBio e os processos em cada bloco.

Faz login via SIP (autenticação do gov.br), navega até a listagem de blocos
internos da unidade e exporta o resultado em JSON.

Credenciais lidas de variáveis de ambiente (nunca hardcoded):
    SEI_LOGIN   — login institucional
    SEI_SENHA   — senha

Uso:
    export SEI_LOGIN=seu.login
    export SEI_SENHA=sua_senha
    python3 scripts/coleta/listar_blocos_sei.py

    # Só listar blocos, sem buscar processos de cada um:
    python3 scripts/coleta/listar_blocos_sei.py --sem-processos

Saída: 01_fontes_web/sei/blocos_internos.json
"""

import argparse
import json
import os
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
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "01_fontes_web" / "sei"
ATRASO = 1.0  # segundos entre requisições


def criar_sessao() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 (coleta RAN/ICMBio chatbot; uso interno)"})
    return s


def fazer_login(sessao: requests.Session, login: str, senha: str) -> BeautifulSoup:
    """Faz login no SEI e retorna o soup da página principal pós-login."""
    resp = sessao.get(LOGIN_URL, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")
    form = soup.find("form")
    if not form:
        raise RuntimeError("Formulário de login não encontrado na página do SIP.")

    dados = {inp.get("name"): inp.get("value", "") for inp in form.find_all("input") if inp.get("name")}

    # Nomes reais dos campos do formulário SIP do SEI/ICMBio
    dados["txtUsuario"] = login
    dados["pwdSenha"] = senha
    # hdnAcao=2 reproduz o onsubmit="acaoLogin(2)" do botão ACESSAR
    dados["hdnAcao"] = "2"
    # selOrgao: ICMBio = "0" (valor pré-selecionado na página)
    dados.setdefault("selOrgao", "0")

    action = form.get("action") or LOGIN_URL
    if not action.startswith("http"):
        action = urljoin(BASE_SIP, action)

    resp = sessao.post(action, data=dados, timeout=30)
    resp.raise_for_status()

    if "controlador.php" not in resp.url and "sei/" not in resp.url:
        soup_erro = BeautifulSoup(resp.text, "lxml")
        msg_erro = soup_erro.find(class_="infraMensagemErro") or soup_erro.find(id="divInfraMensagem")
        detalhe = msg_erro.get_text(strip=True) if msg_erro else "(sem mensagem de erro visível)"
        raise RuntimeError(f"Login falhou. {detalhe}\nURL atual: {resp.url}")

    print("Login realizado com sucesso.")
    return BeautifulSoup(resp.text, "lxml")


def listar_blocos(sessao: requests.Session, soup_principal: BeautifulSoup) -> list[dict]:
    """Busca a lista de blocos internos da unidade atual.

    Extrai a URL com infra_hash da página principal para evitar erro "Link sem assinatura".
    """
    # Encontra o link de blocos internos na página principal (já tem infra_hash)
    link_blocos = None
    for a in soup_principal.find_all("a", href=True):
        if "bloco_interno_listar" in a["href"]:
            link_blocos = a["href"]
            break

    if not link_blocos:
        raise RuntimeError("Link de blocos internos não encontrado na página principal. Verifique permissões do usuário.")

    url = link_blocos if link_blocos.startswith("http") else urljoin(BASE_SEI, link_blocos)
    resp = sessao.get(url, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")
    tabela = soup.find("table", id="tblBlocos") or soup.find("table", class_="infraTable")

    if not tabela:
        # Tenta identificar qualquer tabela com dados
        tabelas = soup.find_all("table")
        tabela = next((t for t in tabelas if t.find("tr") and len(t.find_all("tr")) > 1), None)

    if not tabela:
        print("AVISO: nenhuma tabela de blocos encontrada. Salvando HTML para inspeção.")
        (OUTPUT_DIR / "debug_blocos.html").write_text(resp.text, encoding="utf-8")
        return []

    # Colunas: [checkbox | Número | Sinalizações | Atribuição | Estado | Geradora | Grupo | Descrição | Ações]
    blocos = []
    linhas = tabela.find_all("tr")[1:]  # pula cabeçalho
    for linha in linhas:
        colunas = linha.find_all("td")
        if len(colunas) < 8:
            continue

        numero = colunas[1].get_text(strip=True)
        atribuicao = colunas[3].get_text(strip=True)
        estado = colunas[4].get_text(strip=True)
        geradora = colunas[5].get_text(strip=True)
        grupo = colunas[6].get_text(strip=True)
        descricao = colunas[7].get_text(strip=True)

        # Extrai a URL completa (com infra_hash) do link de processos na coluna Número
        url_processos = None
        for a in colunas[1].find_all("a", href=True):
            if "rel_bloco_protocolo_listar" in a["href"]:
                href = a["href"]
                url_processos = href if href.startswith("http") else urljoin(BASE_SEI, href)
                break

        blocos.append({
            "numero": numero,
            "descricao": descricao,
            "atribuicao": atribuicao,
            "estado": estado,
            "geradora": geradora,
            "grupo": grupo,
            "url_processos": url_processos,
            "processos": [],
        })

    return blocos


def listar_processos_bloco(sessao: requests.Session, url_processos: str) -> list[dict]:
    """Busca os processos dentro de um bloco usando a URL com infra_hash."""
    resp = sessao.get(url_processos, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")
    tabelas = soup.find_all("table")
    tabela = next((t for t in tabelas if t.find("tr") and len(t.find_all("tr")) > 1), None)
    if not tabela:
        return []

    # Descobre colunas pelo cabeçalho
    header = tabela.find("tr")
    colunas_header = [th.get_text(strip=True) for th in header.find_all(["th", "td"])]

    processos = []
    for linha in tabela.find_all("tr")[1:]:
        colunas = linha.find_all("td")
        if not colunas:
            continue
        entrada = {}
        for i, nome in enumerate(colunas_header):
            if nome and i < len(colunas):
                entrada[nome] = colunas[i].get_text(strip=True)
        if entrada:
            processos.append(entrada)

    return processos


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sem-processos", action="store_true", help="Lista apenas os blocos, sem buscar processos de cada um.")
    args = parser.parse_args()

    login = os.environ.get("SEI_LOGIN")
    senha = os.environ.get("SEI_SENHA")
    if not login or not senha:
        print("Erro: defina as variáveis de ambiente SEI_LOGIN e SEI_SENHA antes de executar.", file=sys.stderr)
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    sessao = criar_sessao()

    print("Fazendo login no SEI/ICMBio...")
    soup_principal = fazer_login(sessao, login, senha)

    print("Buscando lista de blocos internos...")
    blocos = listar_blocos(sessao, soup_principal)
    print(f"{len(blocos)} bloco(s) encontrado(s).")

    if not args.sem_processos:
        for bloco in blocos:
            if bloco["url_processos"]:
                print(f"  → Buscando processos do bloco: {bloco['descricao'] or bloco['numero']}")
                bloco["processos"] = listar_processos_bloco(sessao, bloco["url_processos"])
                print(f"     {len(bloco['processos'])} processo(s)")
                time.sleep(ATRASO)
            else:
                print(f"  → Bloco sem URL de processos: {bloco['descricao'] or bloco['numero']} (pulando)")

    resultado = {
        "data_coleta": date.today().isoformat(),
        "total_blocos": len(blocos),
        "blocos": blocos,
    }

    saida = OUTPUT_DIR / "blocos_internos.json"
    saida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSalvo em {saida}")


if __name__ == "__main__":
    main()

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


def fazer_login(sessao: requests.Session, login: str, senha: str) -> None:
    resp = sessao.get(LOGIN_URL, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")
    form = soup.find("form")
    if not form:
        raise RuntimeError("Formulário de login não encontrado na página do SIP.")

    # Coleta campos ocultos do formulário (tokens, parâmetros fixos)
    dados = {}
    for inp in form.find_all("input"):
        nome = inp.get("name")
        valor = inp.get("value", "")
        if nome:
            dados[nome] = valor

    # Substitui/adiciona credenciais (nomes padrão do SIP do SEI)
    dados["infra_login"] = login
    dados["infra_senha"] = senha

    action = form.get("action") or LOGIN_URL
    if not action.startswith("http"):
        action = urljoin(BASE_SIP, action)

    resp = sessao.post(action, data=dados, timeout=30)
    resp.raise_for_status()

    # Verifica se o login foi bem-sucedido (página do SEI carregada)
    if "controlador.php" not in resp.url and "sei/" not in resp.url:
        soup_erro = BeautifulSoup(resp.text, "lxml")
        msg_erro = soup_erro.find(class_="infraMensagemErro") or soup_erro.find(id="divInfraMensagem")
        detalhe = msg_erro.get_text(strip=True) if msg_erro else "(sem mensagem de erro visível)"
        raise RuntimeError(f"Login falhou. {detalhe}\nURL atual: {resp.url}")

    print("Login realizado com sucesso.")


def listar_blocos(sessao: requests.Session) -> list[dict]:
    """Busca a lista de blocos internos da unidade atual."""
    url = BASE_SEI + "controlador.php?acao=bloco_interno_listar"
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

    blocos = []
    linhas = tabela.find_all("tr")[1:]  # pula cabeçalho
    for linha in linhas:
        colunas = linha.find_all("td")
        if not colunas:
            continue

        # Estrutura típica: [checkbox | descrição | qtd_processos | ações]
        descricao = colunas[1].get_text(strip=True) if len(colunas) > 1 else colunas[0].get_text(strip=True)

        # Tenta extrair o ID do bloco a partir dos links/botões da linha
        id_bloco = None
        for tag in linha.find_all(["a", "button", "input"]):
            href = tag.get("href", "") or tag.get("onclick", "") or ""
            for parte in href.split("&"):
                if "id_bloco" in parte or "idBloco" in parte:
                    id_bloco = parte.split("=")[-1].strip("'\" ")
                    break
            if id_bloco:
                break

        blocos.append({
            "id_bloco": id_bloco,
            "descricao": descricao,
            "processos": [],
        })

    return blocos


def listar_processos_bloco(sessao: requests.Session, id_bloco: str) -> list[dict]:
    """Busca os processos dentro de um bloco interno específico."""
    url = BASE_SEI + f"controlador.php?acao=bloco_interno_listar_processos&id_bloco={id_bloco}"
    resp = sessao.get(url, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")
    tabela = soup.find("table", id="tblProcessos") or soup.find("table", class_="infraTable")
    if not tabela:
        return []

    processos = []
    for linha in tabela.find_all("tr")[1:]:
        colunas = linha.find_all("td")
        if not colunas:
            continue
        numero = colunas[0].get_text(strip=True) if colunas else ""
        tipo = colunas[1].get_text(strip=True) if len(colunas) > 1 else ""
        atribuicao = colunas[2].get_text(strip=True) if len(colunas) > 2 else ""
        processos.append({"numero": numero, "tipo": tipo, "atribuicao": atribuicao})

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
    fazer_login(sessao, login, senha)

    print("Buscando lista de blocos internos...")
    blocos = listar_blocos(sessao)
    print(f"{len(blocos)} bloco(s) encontrado(s).")

    if not args.sem_processos:
        for bloco in blocos:
            if bloco["id_bloco"]:
                print(f"  → Buscando processos do bloco: {bloco['descricao']}")
                bloco["processos"] = listar_processos_bloco(sessao, bloco["id_bloco"])
                print(f"     {len(bloco['processos'])} processo(s)")
                time.sleep(ATRASO)
            else:
                print(f"  → Bloco sem ID identificado: {bloco['descricao']} (pulando processos)")

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

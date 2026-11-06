"""Baixa do SEI/ICMBio os documentos técnicos dos processos autorizados (ADR 0010).

Para cada processo com status_exportacao == "autorizado" em
01_fontes_web/sei/processos_para_exportacao.json, abre o processo pela pesquisa rápida do
SEI, lê a árvore de documentos e baixa só os documentos listados em
01_fontes_web/sei/processos_docs.csv, identificados pelo número SEI que aparece entre
parênteses no título do documento.

Salva em 04_documentos_pendentes_avaliacao/sei/<processo>/<numero_documento>.<ext>,
onde <processo> é o número do processo com "-" no lugar de "/". Os arquivos ficam
pendentes de avaliação de sensibilidade (ADR 0002): nada daqui vai para a base sem essa
avaliação.

Travas (ver ADR 0010):
  - Só leitura. O script só faz requisições às ações da lista ACOES_PERMITIDAS. A página
    de um documento no SEI também traz ações que alteram o processo (assinar, excluir,
    enviar e-mail...); nenhuma delas é chamada.
  - Só os documentos da lista autorizada. O resto da árvore é ignorado.
  - Documento cujo nó na árvore mencione "restrito" ou "sigiloso" é pulado e registrado:
    a decisão sobre documentos de acesso restrito está em aberto (ADR 0004).
  - Pausa de ATRASO segundos entre requisições.
  - Nada do conteúdo nem dos títulos é impresso no terminal: só números, contagens,
    tipos e tamanhos.
  - Retomável: o manifesto registra cada documento; numa nova execução, os já baixados
    (com o arquivo presente) são pulados.

Credenciais (do .env, nunca impressas):
    SEI_LOGIN, SEI_SENHA

Uso:
    set -a && . ./.env && set +a
    python scripts/coleta/exportar_documentos_sei.py --piloto      # 10 processos do piloto
    python scripts/coleta/exportar_documentos_sei.py               # todos os autorizados
    python scripts/coleta/exportar_documentos_sei.py --processo 02071.000061/2022-82

Manifesto: 01_fontes_web/sei/exportacao_sei_manifesto.json (fora do git).
"""

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
from listar_documentos_sei import (  # noqa: E402
    BASE_SEI,
    _script_com_arvore,
    _url_abrir_todas_pastas,
    criar_sessao,
    fazer_login,
)

RAIZ = Path(__file__).resolve().parents[2]
PROCESSOS_JSON = RAIZ / "01_fontes_web" / "sei" / "processos_para_exportacao.json"
DOCS_CSV = RAIZ / "01_fontes_web" / "sei" / "processos_docs.csv"
PILOTO_XLSX = RAIZ / "01_fontes_web" / "sei" / "piloto_exportacao_sei.xlsx"
MANIFESTO = RAIZ / "01_fontes_web" / "sei" / "exportacao_sei_manifesto.json"
DESTINO = RAIZ / "04_documentos_pendentes_avaliacao" / "sei"

ATRASO = 1.5  # segundos entre requisições

# Únicas ações do SEI que o script pode chamar (todas de leitura).
ACOES_PERMITIDAS = {
    "protocolo_pesquisa_rapida",   # pesquisa do processo pelo número
    "procedimento_trabalhar",      # página do processo (destino da pesquisa)
    "procedimento_visualizar",     # árvore de documentos (inclui "abrir todas as pastas")
    "arvore_visualizar",
    "documento_download_anexo",    # arquivo de documento externo (PDF, DOCX...)
    "documento_visualizar",        # documento feito no editor do SEI (HTML)
}
TERMOS_RESTRICAO = re.compile(r"restrit|sigilos", re.IGNORECASE)

EXTENSOES = {
    "application/pdf": ".pdf",
    "text/html": ".html",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "application/zip": ".zip",
}


class AcaoNaoPermitida(RuntimeError):
    pass


def acao_da_url(url: str) -> str:
    return (parse_qs(urlparse(url.replace("&amp;", "&")).query).get("acao") or [""])[0]


class ClienteSEI:
    """Sessão no SEI que só aceita requisições às ações de ACOES_PERMITIDAS."""

    def __init__(self, login: str, senha: str):
        self._login, self._senha = login, senha
        self.sessao = criar_sessao()
        self.pagina_atual = fazer_login(self.sessao, login, senha)

    def _conferir(self, url: str) -> str:
        acao = acao_da_url(url)
        if acao not in ACOES_PERMITIDAS:
            raise AcaoNaoPermitida(acao or "(sem ação)")
        return urljoin(BASE_SEI, url.replace("&amp;", "&"))

    def _sessao_expirou(self, resp: requests.Response) -> bool:
        return "login.php" in resp.url

    def get(self, url: str, timeout: int = 60) -> requests.Response:
        url_abs = self._conferir(url)
        time.sleep(ATRASO)
        resp = self.sessao.get(url_abs, timeout=timeout)
        resp.raise_for_status()
        return resp

    def abrir_processo(self, numero: str) -> BeautifulSoup:
        """Abre o processo pela pesquisa rápida; refaz o login uma vez se a sessão caiu."""
        for tentativa in (1, 2):
            form = self.pagina_atual.find("form", id="frmProtocoloPesquisaRapida")
            if form is None:
                raise RuntimeError("formulário de pesquisa rápida não encontrado")
            url_abs = self._conferir(form["action"])
            dados = {i.get("name"): i.get("value", "") for i in form.find_all("input") if i.get("name")}
            dados["txtPesquisaRapida"] = numero
            time.sleep(ATRASO)
            resp = self.sessao.post(url_abs, data=dados, timeout=60)
            resp.raise_for_status()
            if self._sessao_expirou(resp) and tentativa == 1:
                self.pagina_atual = fazer_login(self.sessao, self._login, self._senha)
                continue
            if acao_da_url(resp.url) != "procedimento_trabalhar":
                raise RuntimeError(f"pesquisa não abriu o processo (ação {acao_da_url(resp.url)!r})")
            soup = BeautifulSoup(resp.text, "lxml")
            self.pagina_atual = soup
            return soup
        raise RuntimeError("sessão expirada e novo login não resolveu")


def ler_arvore(cliente: ClienteSEI, soup_processo: BeautifulSoup) -> str:
    iframe = soup_processo.find("iframe", id="ifrArvore")
    if not iframe:
        raise RuntimeError("árvore do processo não encontrada")
    js = _script_com_arvore(cliente.get(iframe["src"]).text)
    if not js:
        raise RuntimeError("script da árvore não encontrado")
    url_abrir = _url_abrir_todas_pastas(js)
    if url_abrir:
        js = _script_com_arvore(cliente.get(url_abrir).text) or js
    return js


def nos_documento(js: str) -> dict[str, dict]:
    """Mapeia número SEI (entre parênteses no título) → nó do documento na árvore.

    Para cada nó: índice, ícone, URL de download (propriedade .src) e se algum texto do
    nó menciona acesso restrito ou sigiloso.
    """
    por_indice = {}
    for m in re.finditer(r'Nos\[(\d+)\] = new infraArvoreNo\((.*?)\);', js):
        indice, corpo = m.group(1), m.group(2)
        if not corpo.startswith('"DOCUMENTO"'):
            continue
        args = [a or b for a, b in re.findall(r'"((?:[^"\\]|\\.)*)"|(null|true|false|\d+)', corpo)]
        titulo = args[5] if len(args) > 5 else ""
        numero = re.search(r"\((\d+)\)\s*$", titulo)
        icone = next((a.split("/")[-1].split("?")[0] for a in args if re.search(r"\.(svg|png|gif)", a)), "")
        por_indice[indice] = {
            "numero": numero.group(1) if numero else None,
            "icone": icone,
            "restrito": bool(TERMOS_RESTRICAO.search(corpo)),
            "src": None,
            "src_html": None,
            "cancelado": icone == "documento_cancelado.svg",
        }
    for m in re.finditer(r"Nos\[(\d+)\]\.(\w+)\s*=\s*(['\"])(.*?)\3\s*;", js):
        indice, prop, _, valor = m.groups()
        if indice not in por_indice:
            continue
        if prop == "src" and valor:
            por_indice[indice]["src"] = valor
        if prop == "html" and not por_indice[indice]["src"]:
            # Arquivos que o navegador não exibe (ZIP, tipo não identificado): o SEI deixa
            # .src vazio e põe o link de download dentro do HTML do nó.
            link = re.search(r"controlador\.php\?acao=documento_download_anexo[^\"'<> ]*", valor)
            if link:
                por_indice[indice]["src_html"] = link.group(0)
        if TERMOS_RESTRICAO.search(valor) and prop not in ("src", "html"):
            por_indice[indice]["restrito"] = True
    for n in por_indice.values():
        n["src"] = n["src"] or n["src_html"]
    return {n["numero"]: n for n in por_indice.values() if n["numero"]}


def extensao(resp: requests.Response) -> str:
    cd = resp.headers.get("content-disposition", "")
    m = re.search(r'filename\*?=(?:UTF-8\'\')?"?[^";]*?(\.[A-Za-z0-9]{2,5})"?\s*(?:;|$)', cd)
    if m:
        return m.group(1).lower()
    tipo = (resp.headers.get("content-type") or "").split(";")[0].strip().lower()
    return EXTENSOES.get(tipo, ".bin")


def carregar_manifesto() -> dict:
    if MANIFESTO.exists():
        return json.loads(MANIFESTO.read_text(encoding="utf-8"))
    return {"documentos": {}}


def salvar_manifesto(manifesto: dict) -> None:
    manifesto["atualizado_em"] = datetime.now().isoformat(timespec="seconds")
    MANIFESTO.write_text(json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8")


def processos_alvo(args) -> list[str]:
    autorizados = [p["numero"] for p in json.loads(PROCESSOS_JSON.read_text(encoding="utf-8"))["processos"]
                   if p.get("status_exportacao") == "autorizado"]
    if args.processo:
        return [n for n in args.processo if n in autorizados]
    if args.piloto:
        from openpyxl import load_workbook
        ws = load_workbook(PILOTO_XLSX, read_only=True)["Processos"]
        piloto = [r[1] for r in ws.iter_rows(min_row=2, values_only=True) if r[1]]
        return [n for n in piloto if n in autorizados]
    return autorizados


def exportar_processo(cliente: ClienteSEI, numero: str, esperados: list[str], manifesto: dict) -> Counter:
    resultado = Counter()
    pasta = DESTINO / numero.replace("/", "-")
    pasta.mkdir(parents=True, exist_ok=True)

    pendentes = []
    for num_doc in esperados:
        reg = manifesto["documentos"].get(num_doc)
        if reg and reg["status"] == "baixado" and (RAIZ / reg["arquivo"]).exists():
            resultado["ja_baixado"] += 1
        else:
            pendentes.append(num_doc)
    if not pendentes:
        return resultado

    nos = nos_documento(ler_arvore(cliente, cliente.abrir_processo(numero)))

    for num_doc in pendentes:
        registro = {"processo": numero, "status": None, "data": datetime.now().isoformat(timespec="seconds")}
        no = nos.get(num_doc)
        try:
            if no is None:
                registro["status"] = "nao_encontrado_na_arvore"
            elif no["cancelado"]:
                registro["status"] = "cancelado_no_sei"
            elif no["restrito"]:
                registro["status"] = "pulado_restrito"
                registro["icone"] = no["icone"]
            elif not no["src"]:
                registro["status"] = "sem_url_de_download"
                registro["icone"] = no["icone"]
            else:
                resp = cliente.get(no["src"], timeout=180)
                if "login.php" in resp.url:
                    raise RuntimeError("sessão expirou no download")
                arquivo = pasta / f"{num_doc}{extensao(resp)}"
                arquivo.write_bytes(resp.content)
                registro.update({
                    "status": "baixado",
                    "arquivo": str(arquivo.relative_to(RAIZ)),
                    "bytes": len(resp.content),
                    "sha256": hashlib.sha256(resp.content).hexdigest(),
                    "content_type": (resp.headers.get("content-type") or "").split(";")[0],
                    "icone": no["icone"],
                    "acao": acao_da_url(no["src"]),
                })
        except AcaoNaoPermitida as e:
            registro["status"] = "acao_nao_permitida"
            registro["acao"] = str(e)
        except (requests.RequestException, RuntimeError) as e:
            registro["status"] = "erro"
            registro["erro"] = type(e).__name__
        manifesto["documentos"][num_doc] = registro
        resultado[registro["status"]] += 1
    return resultado


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--piloto", action="store_true", help="Só os 10 processos do piloto")
    grupo.add_argument("--processo", action="append", metavar="NUMERO", help="Só este processo (pode repetir)")
    args = parser.parse_args()

    login, senha = os.environ.get("SEI_LOGIN"), os.environ.get("SEI_SENHA")
    if not login or not senha:
        sys.exit("Defina SEI_LOGIN e SEI_SENHA (ex.: set -a && . ./.env && set +a).")

    with DOCS_CSV.open(encoding="utf-8", newline="") as f:
        docs_por_processo: dict[str, list[str]] = {}
        for linha in csv.DictReader(f):
            if linha["status_exportacao"] == "autorizado":
                docs_por_processo.setdefault(linha["numero_processo"], []).append(linha["numero_documento_sei"])

    alvos = processos_alvo(args)
    total_docs = sum(len(docs_por_processo.get(n, [])) for n in alvos)
    print(f"{len(alvos)} processo(s), {total_docs} documento(s) a exportar.")

    manifesto = carregar_manifesto()
    cliente = ClienteSEI(login, senha)
    print("Login ok.")

    geral = Counter()
    inicio = time.time()
    for i, numero in enumerate(alvos, start=1):
        try:
            res = exportar_processo(cliente, numero, docs_por_processo.get(numero, []), manifesto)
        except (requests.RequestException, RuntimeError) as e:
            print(f"  [{i}/{len(alvos)}] {numero}: ERRO no processo ({type(e).__name__}: {str(e)[:80]})")
            geral["erro_processo"] += 1
            continue
        finally:
            salvar_manifesto(manifesto)
        geral.update(res)
        print(f"  [{i}/{len(alvos)}] {numero}: " + ", ".join(f"{k} {v}" for k, v in sorted(res.items())))

    minutos = (time.time() - inicio) / 60
    print(f"\nConcluído em {minutos:.1f} min: " + ", ".join(f"{k} {v}" for k, v in sorted(geral.items())))
    print(f"Manifesto: {MANIFESTO.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()

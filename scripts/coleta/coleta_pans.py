"""Coleta metadados e links de documentos dos PANs do ICMBio (ver docs/processos/coleta_fontes_web.md)."""

import argparse
import json
import re
import time
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

LISTING_URL = "https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan"
HEADERS = {"User-Agent": "Mozilla/5.0 (coleta RAN/ICMBio chatbot; uso interno)"}
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "01_fontes_web" / "pans"
DOC_EXTENSIONS = (".pdf", ".xlsx", ".docx", ".zip")
TENTATIVAS = 3


def buscar_html(url: str) -> BeautifulSoup:
    ultimo_erro = None
    for tentativa in range(1, TENTATIVAS + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            resp.encoding = "utf-8"
            return BeautifulSoup(resp.text, "lxml")
        except requests.RequestException as erro:
            ultimo_erro = erro
            time.sleep(2 * tentativa)
    raise RuntimeError(f"Falha ao buscar {url} após {TENTATIVAS} tentativas: {ultimo_erro}")


def slug_da_url(url: str) -> str:
    return url.rstrip("/").rsplit("/", 1)[-1]


def listar_pans(soup: BeautifulSoup) -> list[dict]:
    """Extrai os PANs em execução e finalizados da página de listagem.

    A página intercala marcadores de texto ("PANS EM EXECUÇÃO" / "PANS
    FINALIZADOS" / "SAIBA MAIS") com cards de link em ordem de documento,
    sem uma estrutura de seção própria — por isso o estado precisa ser
    rastreado manualmente conforme os elementos são percorridos.
    """
    pans = []
    status = None
    for el in soup.find_all(["p", "a"]):
        if el.name == "p":
            texto = el.get_text(strip=True).upper()
            if "PANS EM EXEC" in texto:
                status = "em_execucao"
            elif "PANS FINALIZAD" in texto:
                status = "finalizado"
            elif "SAIBA MAIS" in texto:
                status = None
        elif status and "govbr-card-content" in (el.get("class") or []):
            href = el.get("href", "")
            if not href or "/saiba-mais/" in href:
                continue
            pans.append({
                "nome": el.get_text(strip=True),
                "slug": slug_da_url(href),
                "url": href,
                "status": status,
            })
    return pans


def extrair_secoes(content: BeautifulSoup) -> dict:
    """Agrupa o texto da página por seção, usando os títulos `<p class="callout">` como marcadores."""
    secoes: dict[str, list] = {}
    secao_atual = None
    for el in content.find_all(["p", "table", "dl"]):
        if el.name == "p" and "callout" in (el.get("class") or []):
            secao_atual = el.get_text(strip=True)
            secoes.setdefault(secao_atual, [])
            continue
        if secao_atual is None:
            continue
        secoes[secao_atual].append(el)
    return {
        titulo: "\n".join(t for t in (e.get_text(" ", strip=True) for e in elementos) if t)
        for titulo, elementos in secoes.items()
    }


def extrair_documentos(content: BeautifulSoup, url_pagina: str) -> list[dict]:
    """Lista todos os links para PDF/XLSX/DOCX/ZIP encontrados no conteúdo da página."""
    documentos = []
    for a in content.find_all("a", href=True):
        href = a["href"]
        if not href.lower().endswith(DOC_EXTENSIONS):
            continue
        href_abs = urljoin(url_pagina, href)
        ciclo = re.search(r"/(\d+)-ciclo/", href_abs)
        contexto_el = a.find_parent(["tr", "li", "p", "dd"])
        documentos.append({
            "texto_link": a.get_text(strip=True),
            "contexto": contexto_el.get_text(" ", strip=True) if contexto_el else None,
            "url": href_abs,
            "nome_arquivo": href_abs.rsplit("/", 1)[-1],
            "extensao": href_abs.rsplit(".", 1)[-1].lower(),
            "ciclo": ciclo.group(1) if ciclo else None,
        })
    return documentos


def extrair_detalhe(soup: BeautifulSoup, url_pagina: str) -> dict:
    content = soup.find("div", id="content")
    if content is None:
        return {"titulo": None, "secoes": {}, "documentos": []}
    titulo_el = content.find(["h1", "h2"])
    return {
        "titulo": titulo_el.get_text(strip=True) if titulo_el else None,
        "secoes": extrair_secoes(content),
        "documentos": extrair_documentos(content, url_pagina),
    }


def coletar(limite: int | None, atraso: float) -> list[dict]:
    indice = listar_pans(buscar_html(LISTING_URL))
    if limite:
        indice = indice[:limite]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    hoje = date.today().isoformat()

    for i, pan in enumerate(indice, start=1):
        print(f"[{i}/{len(indice)}] {pan['nome']} ({pan['url']})")
        detalhe = extrair_detalhe(buscar_html(pan["url"]), pan["url"])
        registro = {**pan, "data_coleta": hoje, **detalhe}

        pasta_pan = OUTPUT_DIR / pan["slug"]
        pasta_pan.mkdir(parents=True, exist_ok=True)
        (pasta_pan / "metadados.json").write_text(
            json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        pan["data_coleta"] = hoje
        pan["total_documentos"] = len(detalhe["documentos"])

        if i < len(indice):
            time.sleep(atraso)

    (OUTPUT_DIR / "_indice_pans.json").write_text(
        json.dumps(indice, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return indice


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limite", type=int, default=None, help="Coletar apenas os N primeiros PANs (para teste).")
    parser.add_argument("--atraso", type=float, default=1.0, help="Segundos de espera entre requisições.")
    args = parser.parse_args()

    indice = coletar(args.limite, args.atraso)
    print(f"\nConcluído: {len(indice)} PANs coletados em {OUTPUT_DIR}")


if __name__ == "__main__":
    main()

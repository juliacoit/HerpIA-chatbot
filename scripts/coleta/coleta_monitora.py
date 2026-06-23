"""Coleta metadados e links de documentos do Programa Monitora do ICMBio (ver docs/processos/coleta_fontes_web.md).

Diferente dos PANs, o Monitora não tem uma página de listagem com N subpáginas
descobertas por crawling: são 8 categorias de conteúdo com URLs fixas, e cada
categoria pode seguir um de três padrões de HTML distintos:

1. SEÇÕES  — `<p class="callout">Título</p>` agrupando links (Materiais de Apoio,
   Livros, Artigos, Encontro dos Saberes). Mesmo padrão usado nos PANs.
2. LISTAGEM — listagem de pasta do Plone (`<table class="listing">`), usada na
   categoria Dados. Os links terminam em "/view" em vez da extensão do arquivo.
3. FLAT — links diretos no corpo do texto, sem seções (Estrutura do Programa,
   Relatórios, Legislação). Tratado como caso particular de SEÇÕES (sem callouts).
"""

import argparse
import json
import time
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

CATEGORIAS = [
    {"nome": "Materiais de Apoio", "slug": "materiais-de-apoio",
     "url": "https://www.gov.br/icmbio/pt-br/assuntos/monitoramento/conteudo/Materiais-de-Apoio"},
    {"nome": "Artigos", "slug": "artigos",
     "url": "https://www.gov.br/icmbio/pt-br/assuntos/monitoramento/conteudo/artigos-Monitora"},
    {"nome": "Estrutura do Programa Monitora", "slug": "estrutura-do-programa",
     "url": "https://www.gov.br/icmbio/pt-br/assuntos/monitoramento/conteudo/estrutura-do-programa-monitora"},
    {"nome": "Relatórios", "slug": "relatorios",
     "url": "https://www.gov.br/icmbio/pt-br/assuntos/monitoramento/conteudo/relatorios"},
    {"nome": "Dados", "slug": "dados",
     "url": "https://www.gov.br/icmbio/pt-br/assuntos/monitoramento/conteudo/dados"},
    {"nome": "Livros, Monografias, Dissertações e Teses", "slug": "livros",
     "url": "https://www.gov.br/icmbio/pt-br/assuntos/monitoramento/conteudo/livros/livros"},
    {"nome": "Legislação", "slug": "legislacao",
     "url": "https://www.gov.br/icmbio/pt-br/assuntos/monitoramento/conteudo/legislacao/legislacao"},
    {"nome": "Encontro dos Saberes", "slug": "encontro-dos-saberes",
     "url": "https://www.gov.br/icmbio/pt-br/assuntos/monitoramento/conteudo/encontro-dos-saberes"},
]

# Painéis Power BI: não são coletáveis por scraping HTML simples (dados renderizados
# via API do Power BI). Registrados como limitação conhecida, não como erro.
PAINEIS_POWERBI = [
    {"nome": "Painel de dados gerenciais do Programa Monitora",
     "url": "https://app.powerbi.com/view?r=eyJrIjoiOWNlNDA5MmEtODQ0Ny00ZjdlLTllZDItZDMyZTM3YzlhMjU3IiwidCI6ImMxNGUyYjU2LWM1YmMtNDNiZC1hZDljLTQwOGNmNmNjMzU2MCJ9",
     "motivo": "SPA do Power BI, sem HTML estático; dados exigiriam exportação manual ou descoberta de API."},
    {"nome": "Painel Interativo Relatório Florestal",
     "url": "https://www.gov.br/icmbio/pt-br/assuntos/monitoramento/painel-interativo-relatorio-florestal-1",
     "motivo": "Página gov.br que embute painel Power BI; mesmo motivo do painel gerencial."},
]

HEADERS = {"User-Agent": "Mozilla/5.0 (coleta RAN/ICMBio chatbot; uso interno)"}
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "01_fontes_web" / "monitora"
DOC_EXTENSIONS = (".pdf", ".xlsx", ".docx", ".doc", ".pptx", ".ppt", ".zip", ".csv")
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


def extrair_secoes(content: BeautifulSoup) -> dict:
    """Agrupa o texto da página por seção, usando os títulos `<p class="callout">` como marcadores.

    Páginas sem nenhum callout (padrão FLAT) simplesmente retornam um dict vazio —
    o conteúdo ainda é coberto por `extrair_documentos`, que não depende de seções.
    """
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
    """Lista todos os links para arquivos (PDF/XLSX/DOCX/PPTX/ZIP/CSV) no conteúdo da página.

    Cobre tanto o padrão SEÇÕES quanto o FLAT — a busca não depende de callouts.
    Algumas páginas (ex: Materiais de Apoio) têm links decorativos duplicados
    apontando para a mesma URL de outro documento da célula; eles entram aqui e
    devem ser deduplicados por URL na etapa de download (mesmo comportamento já
    usado para os PANs).
    """
    documentos = []
    for a in content.find_all("a", href=True):
        href = a["href"]
        if not href.lower().endswith(DOC_EXTENSIONS):
            continue
        href_abs = urljoin(url_pagina, href)
        contexto_el = a.find_parent(["tr", "li", "p", "dd"])
        documentos.append({
            "texto_link": a.get_text(strip=True),
            "contexto": contexto_el.get_text(" ", strip=True) if contexto_el else None,
            "url": href_abs,
            "nome_arquivo": href_abs.rsplit("/", 1)[-1],
            "extensao": href_abs.rsplit(".", 1)[-1].lower(),
        })
    return documentos


def extrair_listagem_plone(content: BeautifulSoup, url_pagina: str) -> list[dict]:
    """Extrai itens de uma listagem de pasta do Plone (`<table class="listing">`).

    Cada linha tem um link de título (terminado em "/view", em vez da extensão do
    arquivo) e colunas de tipo/data. Itens sem extensão reconhecível no link de
    título (ex: link para uma subpágina, não um arquivo) são ignorados aqui.
    """
    documentos = []
    tabela = content.find("table", class_="listing")
    if tabela is None:
        return documentos

    for linha in tabela.find_all("tr"):
        celulas = linha.find_all("td")
        if not celulas:
            continue
        link = celulas[0].find("a", href=True)
        if link is None:
            continue

        href = urljoin(url_pagina, link["href"])
        href_sem_view = href[:-len("/view")] if href.endswith("/view") else href
        if not href_sem_view.lower().endswith(DOC_EXTENSIONS):
            continue  # link para subpágina/painel, não para um arquivo

        tipo = celulas[1].get_text(strip=True) if len(celulas) > 1 else None
        data_modificacao = celulas[-1].get_text(strip=True) if len(celulas) > 2 else None

        documentos.append({
            "texto_link": link.get_text(strip=True),
            "contexto": tipo,
            "url": href_sem_view,
            "nome_arquivo": href_sem_view.rsplit("/", 1)[-1],
            "extensao": href_sem_view.rsplit(".", 1)[-1].lower(),
            "data_modificacao": data_modificacao,
        })
    return documentos


def extrair_detalhe(soup: BeautifulSoup, url_pagina: str) -> dict:
    content = soup.find("div", id="content")
    if content is None:
        return {"titulo": None, "padrao": None, "secoes": {}, "documentos": []}

    titulo_el = content.find(["h1", "h2"])
    titulo = titulo_el.get_text(strip=True) if titulo_el else None

    if content.find("table", class_="listing") is not None:
        return {
            "titulo": titulo,
            "padrao": "listagem",
            "secoes": {},
            "documentos": extrair_listagem_plone(content, url_pagina),
        }

    secoes = extrair_secoes(content)
    return {
        "titulo": titulo,
        "padrao": "secoes" if secoes else "flat",
        "secoes": secoes,
        "documentos": extrair_documentos(content, url_pagina),
    }


def coletar(atraso: float) -> list[dict]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    hoje = date.today().isoformat()
    indice = []

    for i, categoria in enumerate(CATEGORIAS, start=1):
        print(f"[{i}/{len(CATEGORIAS)}] {categoria['nome']} ({categoria['url']})")
        detalhe = extrair_detalhe(buscar_html(categoria["url"]), categoria["url"])
        registro = {**categoria, "data_coleta": hoje, **detalhe}

        pasta_categoria = OUTPUT_DIR / categoria["slug"]
        pasta_categoria.mkdir(parents=True, exist_ok=True)
        (pasta_categoria / "metadados.json").write_text(
            json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        indice.append({
            **categoria,
            "data_coleta": hoje,
            "padrao": detalhe["padrao"],
            "total_documentos": len(detalhe["documentos"]),
        })

        if i < len(CATEGORIAS):
            time.sleep(atraso)

    (OUTPUT_DIR / "_indice_monitora.json").write_text(
        json.dumps({"categorias": indice, "paineis_powerbi_nao_coletados": PAINEIS_POWERBI},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return indice


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--atraso", type=float, default=1.0, help="Segundos de espera entre requisições.")
    args = parser.parse_args()

    indice = coletar(args.atraso)
    total_docs = sum(c["total_documentos"] for c in indice)
    print(f"\nConcluído: {len(indice)} categorias coletadas, {total_docs} documentos indexados em {OUTPUT_DIR}")
    print(f"{len(PAINEIS_POWERBI)} painel(éis) Power BI registrados como não coletáveis (ver _indice_monitora.json).")


if __name__ == "__main__":
    main()

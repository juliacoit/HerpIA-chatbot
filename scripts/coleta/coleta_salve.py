"""Coleta metadados das fichas de espécies de Répteis e Anfíbios do SALVE/ICMBio
(ver docs/processos/coleta_salve_detalhado.md).

Diferente do Monitora e dos PANs (HTML tradicional do gov.br), o SALVE é servido
por uma SPA Vue.js sem conteúdo no HTML inicial. Em vez de renderizar a página
(Playwright/Selenium), a coleta usa diretamente a API REST pública por trás do
front-end, localizada inspecionando o bundle JS do site:

1. GET /salve-api/public/search?grupoIds=<ids>&paginationPageSize=N[&paginationPageNumber=P
   &paginationTotalPages=T&paginationTotalRecords=R]
   Lista as fichas de um grupo taxonômico, paginada. A primeira chamada só leva
   `paginationPageSize`; as chamadas seguintes devem reenviar os três parâmetros
   de paginação recebidos na resposta anterior.

2. GET /salve-api/public/fichaHtml?idFicha=<id_ficha>&section=<secao>
   Traz o conteúdo de uma ficha, já dividido em seções (taxonomia, distribuição,
   ameaças, conservação, referências bibliográficas etc.) — uma chamada por seção.

Aviso de volume: ~2086 fichas de Répteis+Anfíbios × 11 seções = ~23 mil requisições
de conteúdo, além da paginação da busca. Com o --atraso padrão (1s), uma coleta
completa leva horas. Use --limite para testar antes de rodar a coleta completa.
"""

import argparse
import json
import re
import time
import unicodedata
from datetime import date
from pathlib import Path

import requests

API_BASE = "https://salve.icmbio.gov.br/salve-api/public/"
HEADERS = {"User-Agent": "Mozilla/5.0 (coleta RAN/ICMBio chatbot; uso interno)"}
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "01_fontes_web" / "salve"
TENTATIVAS = 3
TAMANHO_PAGINA = 100

# IDs confirmados via GET /salve-api/public/selectOptions (campo "groups").
GRUPOS_HERPETOFAUNA = {"Répteis": 1266, "Anfíbios": 1257}

# Seções documentadas em GET /salve-api/public/ (endpoint fichaHtml).
SECOES_FICHA = [
    "header",
    "taxonomicClassification",
    "distribution",
    "naturalHistory",
    "population",
    "threats",
    "uses",
    "conservation",
    "research",
    "bibliographicReferences",
    "authors",
]


def chamar_api(caminho: str, params: dict) -> dict:
    ultimo_erro = None
    for tentativa in range(1, TENTATIVAS + 1):
        try:
            resp = requests.get(API_BASE + caminho, params=params, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as erro:
            ultimo_erro = erro
            time.sleep(2 * tentativa)
    raise RuntimeError(f"Falha ao chamar {caminho} ({params}) após {TENTATIVAS} tentativas: {ultimo_erro}")


def limpar_html(texto: str | None) -> str:
    """Remove as tags HTML simples (itálico, span) usadas nos nomes científicos da API."""
    if not texto:
        return ""
    return re.sub(r"<[^>]+>", "", texto).replace("&nbsp;", " ").strip()


def slugificar(nome: str) -> str:
    nome = unicodedata.normalize("NFKD", limpar_html(nome)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9]+", "-", nome).strip("-").lower()


def listar_fichas(grupo_ids: list[int], atraso: float, limite: int | None) -> list[dict]:
    """Pagina GET /search por grupoIds até esgotar paginationTotalPages (ou até --limite)."""
    fichas: list[dict] = []
    grupo_ids_param = ",".join(str(g) for g in grupo_ids)
    pagina = 1
    total_paginas = None
    total_registros = None

    while True:
        params = {"grupoIds": grupo_ids_param, "paginationPageSize": TAMANHO_PAGINA}
        if total_paginas is not None:
            params.update(
                paginationPageNumber=pagina,
                paginationTotalPages=total_paginas,
                paginationTotalRecords=total_registros,
            )

        resposta = chamar_api("search", params)
        if resposta.get("status") != 200:
            raise RuntimeError(f"Erro na busca de fichas (página {pagina}): {resposta.get('msg')}")

        fichas.extend(resposta["data"])
        paginacao = resposta.get("pagination", {})
        total_paginas = paginacao.get("paginationTotalPages", 1)
        total_registros = paginacao.get("paginationTotalRecords", len(fichas))

        print(f"  página {pagina}/{total_paginas} — {len(fichas)} fichas acumuladas")

        if (limite and len(fichas) >= limite) or pagina >= total_paginas:
            break

        pagina += 1
        time.sleep(atraso)

    return fichas[:limite] if limite else fichas


def coletar_secoes_ficha(id_ficha: str, atraso: float) -> dict:
    secoes = {}
    for i, secao in enumerate(SECOES_FICHA):
        resposta = chamar_api("fichaHtml", {"idFicha": id_ficha, "section": secao})
        secoes[secao] = resposta.get("data") if resposta.get("status") == 200 else None
        if i < len(SECOES_FICHA) - 1:
            time.sleep(atraso)
    return secoes


def montar_registro(item: dict, secoes: dict, hoje: str) -> dict:
    return {
        "id_ficha": item.get("id_ficha"),
        "nome_cientifico": limpar_html(item.get("nm_cientifico")),
        "nome_cientifico_atual": limpar_html(item.get("nm_cientifico_atual")),
        "nome_comum": item.get("no_comum"),
        "grupo": item.get("ds_grupo_salve"),
        "categoria_risco": item.get("cd_categoria_final"),
        "categoria_risco_completa": item.get("de_categoria_final_completa"),
        "bioma": item.get("no_bioma"),
        "periodo_avaliacao": item.get("de_periodo_avaliacao"),
        "situacao_ficha": item.get("cd_situacao_ficha"),
        "excluida": item.get("st_excluida"),
        "justificativa_exclusao": item.get("ds_justificativa_exclusao"),
        "doi": item.get("ds_doi"),
        "url_origem": f"{API_BASE}fichaHtml?idFicha={item.get('id_ficha')}",
        "data_coleta": hoje,
        "secoes": secoes,
    }


def coletar(atraso: float, limite: int | None, retomar: bool = False) -> list[dict]:
    pasta_fichas = OUTPUT_DIR / "fichas"
    pasta_fichas.mkdir(parents=True, exist_ok=True)
    hoje = date.today().isoformat()

    print("Listando fichas de Répteis e Anfíbios...")
    fichas = listar_fichas(list(GRUPOS_HERPETOFAUNA.values()), atraso, limite)
    print(f"{len(fichas)} fichas encontradas.\n")

    slugs_usados: dict[str, int] = {}
    indice = []
    puladas = 0
    for i, item in enumerate(fichas, start=1):
        nome_cientifico = limpar_html(item.get("nm_cientifico"))
        slug_base = slugificar(item.get("nm_cientifico_atual") or item.get("nm_cientifico") or item["id_ficha"])
        ocorrencias = slugs_usados.get(slug_base, 0)
        slugs_usados[slug_base] = ocorrencias + 1
        slug = slug_base if ocorrencias == 0 else f"{slug_base}-{ocorrencias}"

        pasta_ficha = pasta_fichas / slug
        arquivo_existente = pasta_ficha / "metadados.json"

        if retomar and arquivo_existente.exists():
            print(f"[{i}/{len(fichas)}] {slug} — já coletada, pulando")
            puladas += 1
        else:
            print(f"[{i}/{len(fichas)}] {nome_cientifico} ({item.get('cd_categoria_final')}) -> {slug}")
            secoes = coletar_secoes_ficha(item["id_ficha"], atraso)
            registro = montar_registro(item, secoes, hoje)
            pasta_ficha.mkdir(parents=True, exist_ok=True)
            arquivo_existente.write_text(
                json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            if i < len(fichas):
                time.sleep(atraso)

        indice.append({
            "slug": slug,
            "nome_cientifico": nome_cientifico,
            "grupo": item.get("ds_grupo_salve"),
            "categoria_risco": item.get("cd_categoria_final"),
            "id_ficha": item.get("id_ficha"),
        })

    if retomar and puladas:
        print(f"\n{puladas} fichas já existiam e foram puladas.")

    (OUTPUT_DIR / "_indice_salve.json").write_text(
        json.dumps({
            "data_coleta": hoje,
            "grupos_coletados": GRUPOS_HERPETOFAUNA,
            "total_fichas": len(indice),
            "fichas": indice,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return indice


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--atraso", type=float, default=1.0, help="Segundos de espera entre requisições à API.")
    parser.add_argument("--limite", type=int, default=None, help="Coletar apenas as N primeiras fichas (para teste).")
    parser.add_argument("--retomar", action="store_true", help="Pular fichas que já têm metadados.json — retoma coleta interrompida.")
    args = parser.parse_args()

    indice = coletar(args.atraso, args.limite, args.retomar)
    print(f"\nConcluído: {len(indice)} fichas de Répteis/Anfíbios coletadas em {OUTPUT_DIR}")


if __name__ == "__main__":
    main()

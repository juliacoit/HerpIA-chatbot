"""Extrai texto limpo das fichas SALVE coletadas em 01_fontes_web/salve/fichas/.

Lê cada metadados.json, converte HTML em texto plano e serializa campos
estruturados (tabelas, classificação taxonômica) em texto legível.
Salva o resultado em 07_processados/textos_extraidos/salve/<slug>.json.
"""

import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

FICHAS_DIR = Path(__file__).resolve().parents[2] / "01_fontes_web" / "salve" / "fichas"
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "07_processados" / "textos_extraidos" / "salve"


def limpar_html(html: str | None) -> str:
    """Converte HTML em texto plano preservando separação entre parágrafos."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all(["p", "div", "br"]):
        tag.insert_before("\n\n")
    texto = soup.get_text(" ")
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n +", "\n", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def extrair_visao_geral(header: dict | None) -> str:
    if not header:
        return ""
    partes = []
    justificativa = limpar_html(header.get("justificative"))
    if justificativa:
        partes.append(f"Justificativa da avaliação:\n{justificativa}")
    autoria = (header.get("authorship") or "").strip()
    if autoria:
        partes.append(f"Autoria: {autoria}")
    citacao = limpar_html(header.get("citation"))
    if citacao:
        partes.append(f"Citação recomendada:\n{citacao}")
    return "\n\n".join(partes)


def extrair_taxonomia(sec: dict | None) -> str:
    if not sec:
        return ""
    partes = []
    arvore = sec.get("tree") or []
    if arvore:
        niveis = [
            f"{item['name']}: {limpar_html(str(item.get('value', '')))}"
            for item in arvore
            if item.get("value")
        ]
        partes.append(" | ".join(niveis))
    if sec.get("commonNames"):
        partes.append(f"Nomes comuns: {sec['commonNames']}")
    if sec.get("oldNames"):
        partes.append(f"Sinonímias: {sec['oldNames']}")
    notas_tax = limpar_html(sec.get("taxonomicNotes"))
    if notas_tax:
        partes.append(f"Notas taxonômicas: {notas_tax}")
    notas_morf = limpar_html(sec.get("morphologicalNotes"))
    if notas_morf:
        partes.append(f"Notas morfológicas: {notas_morf}")
    return "\n\n".join(partes)


def extrair_distribuicao(sec: dict | None) -> str:
    if not sec:
        return ""
    partes = []
    if sec.get("endemicOfBrazil"):
        partes.append(f"Endêmica do Brasil: {sec['endemicOfBrazil']}")
    if sec.get("states"):
        partes.append(f"Estados: {sec['states']}")
    if sec.get("biomes"):
        partes.append(f"Biomas: {sec['biomes']}")
    if sec.get("watersheds"):
        partes.append(f"Bacias hidrográficas: {sec['watersheds']}")
    if sec.get("vlEoo"):
        partes.append(f"Extensão de Ocorrência (EOO): {sec['vlEoo']} km²")
    dist_global = limpar_html(sec.get("globalDistribution"))
    if dist_global:
        partes.append(f"Distribuição global:\n{dist_global}")
    dist_nacional = limpar_html(sec.get("nationalDistribution"))
    if dist_nacional:
        partes.append(f"Distribuição no Brasil:\n{dist_nacional}")
    eoo_mem = limpar_html(sec.get("eooCalculationMemory"))
    if eoo_mem:
        partes.append(f"Cálculo da EOO:\n{eoo_mem}")
    return "\n\n".join(partes)


def extrair_historia_natural(sec: dict | None) -> str:
    if not sec:
        return ""
    partes = []
    if sec.get("migratorySpecie"):
        partes.append(f"Espécie migratória: {sec['migratorySpecie']}")
    descricao = limpar_html(sec.get("description"))
    if descricao:
        partes.append(descricao)

    food = sec.get("foodHabit") or {}
    tipos_alim = [t["type"] for t in (food.get("table") or []) if t.get("type")]
    if tipos_alim:
        partes.append(f"Hábito alimentar: {', '.join(tipos_alim)}")
    especialista = food.get("specialist") or {}
    if especialista.get("yn") and especialista["yn"] != "Não":
        partes.append(f"Especialista de micro-hábitat: {especialista['yn']}")

    repro = sec.get("reproduction") or {}
    linhas_repro = []
    for row in repro.get("table") or []:
        nome = row.get("name", "")
        macho = row.get("male", "")
        femea = row.get("female", "")
        if nome and (macho or femea):
            linhas_repro.append(f"{nome}: macho={macho or '-'}, fêmea={femea or '-'}")
    if linhas_repro:
        partes.append("Dados de reprodução:\n" + "\n".join(linhas_repro))
    if repro.get("offspringSize"):
        partes.append(f"Tamanho da ninhada: {repro['offspringSize']}")
    if repro.get("gestationTime"):
        partes.append(f"Período de incubação/gestação: {repro['gestationTime']}")

    return "\n\n".join(partes)


def extrair_populacao(sec: dict | None) -> str:
    if not sec:
        return ""
    partes = []
    if sec.get("generationalTime"):
        partes.append(f"Tempo geracional: {sec['generationalTime']}")
    if sec.get("populationTrend"):
        partes.append(f"Tendência populacional: {sec['populationTrend']}")
    if sec.get("sexRatio"):
        partes.append(f"Razão sexual: {sec['sexRatio']}")
    if sec.get("mortalityRate"):
        partes.append(f"Taxa de mortalidade: {sec['mortalityRate']}")
    obs = limpar_html(sec.get("populationObservations"))
    if obs:
        partes.append(obs)
    return "\n\n".join(partes)


def extrair_ameacas(sec: dict | None) -> str:
    if not sec:
        return ""
    partes = []
    descricao = limpar_html(sec.get("description"))
    if descricao:
        partes.append(descricao)
    categorias = []
    for item in sec.get("table") or []:
        tipo = item.get("type") or {}
        if isinstance(tipo, dict) and tipo.get("description"):
            categorias.append(tipo["description"])
        elif isinstance(tipo, str) and tipo:
            categorias.append(tipo)
    if categorias:
        partes.append("Categorias de ameaça:\n" + "\n".join(f"- {c}" for c in categorias))
    return "\n\n".join(partes)


def extrair_uso(sec: dict | None) -> str:
    if not sec:
        return ""
    partes = []
    descricao = limpar_html(sec.get("description"))
    if descricao:
        partes.append(descricao)
    tipos = [
        item["type"]
        for item in (sec.get("table") or [])
        if isinstance(item.get("type"), str) and item["type"]
    ]
    if tipos:
        partes.append("Tipos de uso/exploração:\n" + "\n".join(f"- {t}" for t in tipos))
    return "\n\n".join(partes)


def extrair_conservacao(sec: dict | None) -> str:
    if not sec:
        return ""
    partes = []
    descricao = limpar_html(sec.get("description"))
    if descricao:
        partes.append(descricao)

    historico = sec.get("historyTable") or []
    if historico:
        linhas = []
        for h in historico:
            linha = f"{h.get('type', '')} {h.get('year', '')}: {h.get('category', '')}"
            if h.get("criteria"):
                linha += f" (critério {h['criteria']})"
            linhas.append(linha)
        partes.append("Histórico de avaliação de risco:\n" + "\n".join(f"- {l}" for l in linhas))

    ucs = sec.get("UCPresenceTable") or []
    if ucs:
        partes.append(
            "Unidades de conservação com registro:\n"
            + "\n".join(f"- {u['name']} ({u.get('sphere', '')})" for u in ucs)
        )

    acoes = sec.get("conservationActionsTable") or []
    if acoes:
        partes.append(
            "Ações de conservação:\n"
            + "\n".join(f"- {a['name']}: {a.get('situation', '')}" for a in acoes)
        )

    return "\n\n".join(partes)


def extrair_pesquisa(sec: dict | None) -> str:
    if not sec:
        return ""
    partes = []
    descricao = limpar_html(sec.get("description"))
    if descricao:
        partes.append(descricao)
    temas = sec.get("table") or []
    if temas:
        partes.append(
            "Necessidades de pesquisa:\n"
            + "\n".join(f"- {t['theme']}: {t.get('situation', '')}" for t in temas if t.get("theme"))
        )
    return "\n\n".join(partes)


def extrair_referencias(sec: dict | None) -> str:
    if not sec:
        return ""
    tabela = sec.get("table") or {}
    refs = tabela.get("refsTaxon") or []
    if not refs:
        return ""
    return "\n".join(limpar_html(r) for r in refs if r)


def processar_ficha(slug: str, dados: dict) -> dict:
    secoes_raw = dados.get("secoes") or {}
    dist = secoes_raw.get("distribution") or {}

    return {
        "slug": slug,
        "id_ficha": dados.get("id_ficha"),
        "nome_cientifico": dados.get("nome_cientifico"),
        "nome_cientifico_atual": dados.get("nome_cientifico_atual"),
        "nome_comum": dados.get("nome_comum"),
        "grupo": dados.get("grupo"),
        "categoria_risco": dados.get("categoria_risco"),
        "categoria_risco_completa": dados.get("categoria_risco_completa"),
        "bioma": dados.get("bioma"),
        "estados": dist.get("states", ""),
        "doi": dados.get("doi"),
        "url_origem": dados.get("url_origem"),
        "data_coleta": dados.get("data_coleta"),
        "secoes": {
            "visao_geral": extrair_visao_geral(secoes_raw.get("header")),
            "taxonomia": extrair_taxonomia(secoes_raw.get("taxonomicClassification")),
            "distribuicao": extrair_distribuicao(dist),
            "historia_natural": extrair_historia_natural(secoes_raw.get("naturalHistory")),
            "populacao": extrair_populacao(secoes_raw.get("population")),
            "ameacas": extrair_ameacas(secoes_raw.get("threats")),
            "uso": extrair_uso(secoes_raw.get("uses")),
            "conservacao": extrair_conservacao(secoes_raw.get("conservation")),
            "pesquisa": extrair_pesquisa(secoes_raw.get("research")),
            "referencias": extrair_referencias(secoes_raw.get("bibliographicReferences")),
        },
    }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fichas = sorted(FICHAS_DIR.glob("*/metadados.json"))
    print(f"{len(fichas)} fichas encontradas em {FICHAS_DIR}")

    for caminho in fichas:
        slug = caminho.parent.name
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        resultado = processar_ficha(slug, dados)
        saida = OUTPUT_DIR / f"{slug}.json"
        saida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  ✓ {resultado['nome_cientifico']}")

    print(f"\nConcluído: {len(fichas)} fichas em {OUTPUT_DIR}")


if __name__ == "__main__":
    main()

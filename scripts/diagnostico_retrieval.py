"""Diagnóstico do retrieval do endpoint /buscar — caso "anfíbios no Cerrado".

Contexto: um teste manual do POST /buscar com a pergunta "quais anfíbios
ocorrem no Cerrado?" retornou 5 chunks com scores concentrados entre 0.61 e
0.66 (faixa estreita, sinal de match fraco) e nenhum deles trazia de fato uma
lista de anfíbios do Cerrado — a maioria eram parágrafos genéricos sobre o
bioma, vindos de PANs de outros grupos taxonômicos (cactáceas, aves,
lepidópteros).

Este script é só de DIAGNÓSTICO. Ele não altera nada do pipeline de
produção (routers, schemas, services) — apenas reaproveita as funções já
existentes em backend/services/retrieval.py e backend/config.py para rodar
uma bateria de buscas e registrar o que a base realmente devolve.

Nota sobre imports: backend/dependencies.py expõe obter_qdrant() e
obter_modelo_embedding(), mas essas funções dependem de um Request do
FastAPI (elas só leem request.app.state, populado no lifespan de
backend/main.py). Fora de uma requisição HTTP não há Request para injetar,
então este script chama diretamente as mesmas funções que o lifespan usa
para popular esse estado — conectar_qdrant() e carregar_modelo_embedding(),
ambas em backend/services/retrieval.py — o que dá exatamente o mesmo cliente
Qdrant e o mesmo modelo de embeddings que o endpoint /buscar usa em
produção, sem precisar do servidor HTTP rodando.

Pré-requisito: se o Qdrant estiver em modo embutido (QDRANT_LOCAL_PATH no
.env), o diretório de dados só pode estar aberto por um processo por vez —
pare o `uvicorn backend.main:app` antes de rodar este script.

Uso:
    python scripts/diagnostico_retrieval.py

Saída:
    diagnosticos/retrieval-cerrado-anfibios.md
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from backend.config import obter_settings  # noqa: E402
from backend.schemas import ChunkRecuperado  # noqa: E402
from backend.services.retrieval import (  # noqa: E402
    carregar_modelo_embedding,
    conectar_qdrant,
    buscar_chunks,
)

ARQUIVO_SAIDA = RAIZ / "diagnosticos" / "retrieval-cerrado-anfibios.md"

# ---------------------------------------------------------------------------
# Tarefa 2 — casos de teste
# ---------------------------------------------------------------------------
CASOS_TESTE: list[dict] = [
    {
        "id": "1-baseline",
        "pergunta": "quais anfíbios ocorrem no Cerrado?",
        "top_k": 5,
        "fontes": None,
        "descricao": (
            "Repetição do teste manual original que motivou este diagnóstico "
            "— referência para comparar com os demais casos."
        ),
    },
    {
        "id": "2-top_k_20",
        "pergunta": "quais anfíbios ocorrem no Cerrado?",
        "top_k": 20,
        "fontes": None,
        "descricao": (
            "Mesma pergunta, top_k maior — checar se algo relevante aparece "
            "mais abaixo no ranking (indício de problema de ranking, não de "
            "cobertura)."
        ),
    },
    {
        "id": "3-fonte_monitora",
        "pergunta": "quais anfíbios ocorrem no Cerrado?",
        "top_k": 10,
        "fontes": ["monitora"],
        "descricao": "Isolar a fonte Monitora para ver cobertura/ranking só dentro dela.",
    },
    {
        "id": "4-fonte_salve",
        "pergunta": "quais anfíbios ocorrem no Cerrado?",
        "top_k": 10,
        "fontes": ["salve"],
        "descricao": "Isolar a fonte SALVE para ver cobertura/ranking só dentro dela.",
    },
    {
        "id": "5-reformulacao",
        "pergunta": "lista de espécies de anfíbios ameaçados no bioma Cerrado",
        "top_k": 10,
        "fontes": None,
        "descricao": (
            "Reformulação da pergunta original — testar sensibilidade da busca "
            "semântica à forma como a pergunta é escrita."
        ),
    },
    {
        "id": "6-termo_especifico",
        "pergunta": "anuros Cerrado conservação",
        "top_k": 10,
        "fontes": None,
        "descricao": (
            "Termo mais próximo do vocabulário técnico dos documentos (anuros) "
            "e consulta mais curta, testando se isso melhora o ranking."
        ),
    },
]

# ---------------------------------------------------------------------------
# Tarefa 1 — heurística de leitura humana (NÃO é métrica de avaliação)
# ---------------------------------------------------------------------------
PALAVRAS_HEURISTICA = ["anfíbio", "anfíbios", "anuro", "anuros", "herpetofauna"]


def marcar_possivelmente_relevante(chunk: ChunkRecuperado) -> bool:
    """Heurística simples e grosseira: sinaliza um resultado como
    'possivelmente relevante' se o texto do chunk ou o nome do documento
    contiver alguma das palavras-chave em PALAVRAS_HEURISTICA (case-insensitive).

    Isto é só um sinalizador para facilitar a leitura humana da tabela abaixo
    — não mede relevância de verdade (não avalia se o trecho responde à
    pergunta, só se contém certas palavras) e não deve ser tratado como
    métrica de qualidade do retrieval.
    """
    alvo = f"{chunk.texto} {chunk.documento}".lower()
    return any(palavra in alvo for palavra in PALAVRAS_HEURISTICA)


def truncar(texto: str, tamanho: int = 200) -> str:
    texto = " ".join(texto.split())
    if len(texto) <= tamanho:
        return texto
    return texto[:tamanho].rstrip() + "…"


@dataclass
class ResultadoCaso:
    caso: dict
    chunks: list[ChunkRecuperado] = field(default_factory=list)


def rodar_casos(client, modelo, settings) -> list[ResultadoCaso]:
    resultados = []
    for caso in CASOS_TESTE:
        print(f"[executando] {caso['id']}: {caso['pergunta']!r} "
              f"(top_k={caso['top_k']}, fontes={caso['fontes']})")
        chunks = buscar_chunks(
            client=client,
            modelo=modelo,
            settings=settings,
            pergunta=caso["pergunta"],
            top_k=caso["top_k"],
            fontes=caso["fontes"],
        )
        resultados.append(ResultadoCaso(caso=caso, chunks=chunks))
    return resultados


# ---------------------------------------------------------------------------
# Tarefa 3 — cobertura do corpus (sem abrir PDFs)
# ---------------------------------------------------------------------------
def checar_cobertura_corpus(client, settings) -> dict:
    """Varre os metadados já indexados (payload do Qdrant) via scroll,
    coletando nomes de documento e seções distintos por fonte — sem baixar
    vetores nem abrir PDF nenhum. Usado para responder: existe algum PAN de
    Herpetofauna do Cerrado indexado, ou só o do Nordeste?
    """
    documentos_por_fonte: dict[str, set[str]] = {}
    secoes_por_fonte: dict[str, set[str]] = {}
    total_pontos = 0

    proximo_offset = None
    while True:
        pontos, proximo_offset = client.scroll(
            collection_name=settings.qdrant_collection,
            with_payload=["fonte", "documento", "secao", "categoria"],
            with_vectors=False,
            limit=500,
            offset=proximo_offset,
        )
        if not pontos:
            break
        for ponto in pontos:
            total_pontos += 1
            payload = ponto.payload or {}
            fonte = payload.get("fonte", "desconhecida")
            documento = payload.get("documento", "")
            secao = payload.get("secao") or payload.get("categoria") or ""
            documentos_por_fonte.setdefault(fonte, set()).add(documento)
            if secao:
                secoes_por_fonte.setdefault(fonte, set()).add(secao)
        if proximo_offset is None:
            break

    termos_herpetofauna = ["herpetofauna", "anfíbio", "anfibio", "anuro", "réptil", "reptil"]
    termos_cerrado = ["cerrado"]
    termos_nordeste = ["nordeste"]

    def contem_algum(texto: str, termos: list[str]) -> bool:
        texto = texto.lower()
        return any(t in texto for t in termos)

    docs_herpetofauna = sorted(
        doc
        for docs in documentos_por_fonte.values()
        for doc in docs
        if contem_algum(doc, termos_herpetofauna)
    )
    docs_herpetofauna_cerrado = [d for d in docs_herpetofauna if contem_algum(d, termos_cerrado)]
    docs_herpetofauna_nordeste = [d for d in docs_herpetofauna if contem_algum(d, termos_nordeste)]

    return {
        "total_pontos_verificados": total_pontos,
        "fontes_encontradas": sorted(documentos_por_fonte.keys()),
        "n_documentos_por_fonte": {
            fonte: len(docs) for fonte, docs in sorted(documentos_por_fonte.items())
        },
        "docs_herpetofauna": docs_herpetofauna,
        "docs_herpetofauna_cerrado": docs_herpetofauna_cerrado,
        "docs_herpetofauna_nordeste": docs_herpetofauna_nordeste,
    }


# ---------------------------------------------------------------------------
# Tarefa 4 — geração do relatório em Markdown
# ---------------------------------------------------------------------------
def gerar_tabela_caso(resultado: ResultadoCaso) -> str:
    caso = resultado.caso
    linhas = [
        f"### Caso {caso['id']}",
        "",
        f"- **Pergunta**: {caso['pergunta']!r}",
        f"- **top_k**: {caso['top_k']}",
        f"- **fontes**: {caso['fontes'] or 'todas'}",
        f"- **Por que este caso existe**: {caso['descricao']}",
        f"- **Resultados retornados**: {len(resultado.chunks)}",
        "",
    ]
    if not resultado.chunks:
        linhas.append("_Nenhum resultado retornado._")
        linhas.append("")
        return "\n".join(linhas)

    linhas.append("| # | score | fonte | documento | seção | página | possivelmente relevante* | trecho (~200 car.) |")
    linhas.append("|---|-------|-------|-----------|-------|--------|--------------------------|---------------------|")
    for i, chunk in enumerate(resultado.chunks, start=1):
        pagina = chunk.pagina_inicio
        if chunk.pagina_fim and chunk.pagina_fim != chunk.pagina_inicio:
            pagina = f"{chunk.pagina_inicio}-{chunk.pagina_fim}"
        sinalizador = "sim" if marcar_possivelmente_relevante(chunk) else "não"
        trecho = truncar(chunk.texto).replace("|", "\\|")
        documento = (chunk.documento or "").replace("|", "\\|")
        secao = (chunk.secao or "").replace("|", "\\|")
        linhas.append(
            f"| {i} | {chunk.score:.4f} | {chunk.fonte} | {documento} | {secao} | "
            f"{pagina if pagina is not None else '—'} | {sinalizador} | {trecho} |"
        )
    linhas.append("")
    return "\n".join(linhas)


def gerar_secao_cobertura(cobertura: dict) -> str:
    linhas = [
        "## Cobertura do corpus",
        "",
        (
            "Verificação feita varrendo os metadados já indexados no Qdrant "
            "(campos `documento` e `secao`/`categoria` do payload), sem abrir "
            "nenhum PDF."
        ),
        "",
        f"- Pontos verificados: {cobertura['total_pontos_verificados']}",
        f"- Fontes presentes na coleção: {', '.join(cobertura['fontes_encontradas'])}",
        f"- Documentos distintos por fonte: {cobertura['n_documentos_por_fonte']}",
        "",
        "Documentos cujo nome contém termos de herpetofauna "
        f"({', '.join(PALAVRAS_HEURISTICA)}, réptil/reptil):",
        "",
    ]
    if cobertura["docs_herpetofauna"]:
        for doc in cobertura["docs_herpetofauna"]:
            linhas.append(f"- {doc}")
    else:
        linhas.append("- _Nenhum documento com esses termos no nome foi encontrado._")
    linhas.append("")

    linhas.append(
        f"- PAN de Herpetofauna com 'Cerrado' no nome do documento: "
        f"{'SIM — ' + '; '.join(cobertura['docs_herpetofauna_cerrado']) if cobertura['docs_herpetofauna_cerrado'] else 'NÃO encontrado'}"
    )
    linhas.append(
        f"- PAN de Herpetofauna com 'Nordeste' no nome do documento: "
        f"{'SIM — ' + '; '.join(cobertura['docs_herpetofauna_nordeste']) if cobertura['docs_herpetofauna_nordeste'] else 'NÃO encontrado'}"
    )
    linhas.append("")
    linhas.append(
        "_Aviso: esta verificação olha só o **nome do documento** e a "
        "**seção/categoria** nos metadados já indexados — não abre o "
        "conteúdo dos PDFs. Um PAN de Herpetofauna do Cerrado pode existir "
        "na base de fontes web (`01_fontes_web/`) sem ter sido indexado, ou "
        "pode estar indexado com um nome de documento que não contém "
        "nenhum dos termos buscados; nesse segundo caso este script não o "
        "detectaria e a checagem exigiria uma revisão manual do inventário "
        "(`06_inventario/inventario_fontes.xlsx`)._"
    )
    linhas.append("")
    return "\n".join(linhas)


def gerar_relatorio(resultados: list[ResultadoCaso], cobertura: dict) -> str:
    hoje = date.today().isoformat()

    total_flags = sum(
        1 for r in resultados for c in r.chunks if marcar_possivelmente_relevante(c)
    )
    total_chunks = sum(len(r.chunks) for r in resultados)

    partes = [
        "# Diagnóstico de retrieval — \"anfíbios no Cerrado\"",
        "",
        f"_Gerado em {hoje} por `scripts/diagnostico_retrieval.py`. "
        "Diagnóstico apenas — nenhuma mudança de produção foi feita nesta tarefa._",
        "",
        "## Resumo executivo",
        "",
        "<!-- PREENCHER: 3-5 linhas com o achado principal, revisadas à mão "
        "após leitura das tabelas abaixo. -->",
        "",
        "## Casos de teste",
        "",
        (
            "Heurística de leitura (coluna \"possivelmente relevante\"): marca "
            f"\"sim\" quando o texto do chunk ou o nome do documento contém "
            f"alguma das palavras {', '.join(PALAVRAS_HEURISTICA)} "
            "(case-insensitive). **Isto não é uma métrica de avaliação** — é só "
            "um sinalizador grosseiro para facilitar a leitura humana da "
            "tabela; um \"sim\" não garante que o trecho responda à pergunta, "
            "e um \"não\" não garante que seja irrelevante."
        ),
        "",
        f"Total de resultados coletados em todos os casos: {total_chunks} "
        f"(sinalizados como possivelmente relevantes: {total_flags}).",
        "",
    ]

    for resultado in resultados:
        partes.append(gerar_tabela_caso(resultado))

    partes.append(gerar_secao_cobertura(cobertura))

    partes.extend([
        "## Hipóteses",
        "",
        "<!-- PREENCHER: causas prováveis observadas nos dados acima "
        "(ranking? cobertura do corpus? chunking? ausência de busca léxica?). -->",
        "",
        "## Opções para decisão",
        "",
        "<!-- PREENCHER: 3-4 caminhos possíveis de melhoria, cada um com "
        "prós/contras em 1-2 linhas. Não implementar nenhuma delas nesta tarefa. -->",
        "",
    ])

    return "\n".join(partes)


def main() -> None:
    settings = obter_settings()

    print(f"Carregando modelo de embeddings (mesma config de produção)...")
    modelo = carregar_modelo_embedding()

    print("Conectando ao Qdrant...")
    client = conectar_qdrant(settings)

    resultados = rodar_casos(client, modelo, settings)

    print("Verificando cobertura do corpus (metadados indexados)...")
    cobertura = checar_cobertura_corpus(client, settings)

    relatorio = gerar_relatorio(resultados, cobertura)

    ARQUIVO_SAIDA.parent.mkdir(parents=True, exist_ok=True)
    ARQUIVO_SAIDA.write_text(relatorio, encoding="utf-8")
    print(f"\nRelatório gravado em {ARQUIVO_SAIDA.relative_to(RAIZ)}")

    print("\n" + "=" * 70)
    print("RESUMO — casos rodados:")
    for resultado in resultados:
        caso = resultado.caso
        n_flags = sum(1 for c in resultado.chunks if marcar_possivelmente_relevante(c))
        print(
            f"  {caso['id']}: {len(resultado.chunks)} resultados, "
            f"{n_flags} sinalizados como possivelmente relevantes (heurística)"
        )
    print("\nCobertura do corpus:")
    print(f"  PAN Herpetofauna Cerrado encontrado: "
          f"{'sim' if cobertura['docs_herpetofauna_cerrado'] else 'não'}")
    print(f"  PAN Herpetofauna Nordeste encontrado: "
          f"{'sim' if cobertura['docs_herpetofauna_nordeste'] else 'não'}")
    print("=" * 70)
    print(
        "\nEste script só gera o diagnóstico. Nenhuma mudança de chunking, "
        "indexação ou lógica de busca foi feita. Revisar o relatório e as "
        "seções 'Resumo executivo', 'Hipóteses' e 'Opções para decisão' "
        "(marcadas com <!-- PREENCHER --> quando geradas automaticamente) "
        "antes de decidir os próximos passos."
    )


if __name__ == "__main__":
    main()

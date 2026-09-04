"""Priorização heurística de fonte (e, quando aplicável, de bioma/categoria
de risco) para perguntas de "lista de espécies por bioma/táxon" — ex.:
"quais anfíbios ocorrem no Cerrado?".

Contexto (ver diagnosticos/retrieval-cerrado-anfibios.md, caso 4): sem filtro
de fonte, esse tipo de pergunta é dominado por parágrafos genéricos sobre o
bioma vindos de PANs de táxons não relacionados, enquanto o conteúdo
realmente relevante — fichas de espécie do SALVE — fica abaixo do corte.
Isolar `fontes=["salve"]` já reproduz boa precisão para esse padrão de
pergunta (caso 4 do relatório).

Bioma/categoria de risco (ver diagnosticos/agregacao-biomas-fichas-salve.md):
mesmo priorizando SALVE, o LLM ainda tinha que inferir do texto corrido se
uma ficha cobria o bioma/categoria perguntado — e errava em ambas as
direções (incluía espécie de bioma errado, omitia a evidência mais forte).
Como toda ficha SALVE já carrega `bioma`/`categoria_risco` como metadado
estruturado (`gerar_chunks.py`), dá para filtrar de forma determinística no
Qdrant em vez de depender do LLM — tira a decisão da geração, mesmo
princípio da priorização de fonte acima. Só se aplica quando a fonte
prioritária já é SALVE (a única fonte com esses campos); nunca combinado com
uma busca sem filtro de fonte, ou excluiria monitora/pans inteiros (ver
docstring de `buscar_chunks`).

Este módulo não altera `buscar_chunks` (backend/services/retrieval.py) nem o
endpoint de depuração `/buscar` (backend/routers/busca.py) — só o endpoint
`/perguntar` passa a usar `buscar_chunks_priorizados`.
"""

import re

from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

from backend.config import Settings
from backend.schemas import ChunkRecuperado
from backend.services.retrieval import buscar_chunks

# Heurística de palavra-chave — NÃO é uma classificação confiável de intenção.
# Pode errar em perguntas ambíguas (ver "Opções para decisão", item 4, no
# relatório de diagnóstico). Detecta perguntas do tipo "quais/lista de
# espécies/anfíbios/répteis ... ocorrem/existem em <lugar>".
#
# "quais/lista de" sozinho é permissivo demais: casa com perguntas como
# "Quais UCs foram citadas ... no PAN Herpetofauna do Espinhaço?" ou "Quais
# são os objetivos do PAN Herpetofauna do Espinhaço?", em que "quais" não se
# refere a uma lista de espécies (falso positivo visto em D3/A2, ver
# diagnosticos/teste-perguntas-dominio.md). Por isso a palavra-gatilho
# precisa estar próxima (até 4 palavras) de "espécies".
_PADRAO_PEDIDO_LISTA = re.compile(
    r"\b(quais?|lista(?:\s+de)?|liste)\b(?:\s+\S+){0,4}?\s+esp[ée]cies\b",
    re.IGNORECASE,
)
_PADRAO_TAXON_HERPETOFAUNA = re.compile(
    r"\b(anf[íi]bios?|anuros?|r[ée]pteis?|serpentes?|lagartos?|"
    r"quel[ôo]nios?|jacar[ée]s?|herpetofauna)\b",
    re.IGNORECASE,
)
_PADRAO_OCORRENCIA = re.compile(
    r"\b(ocorrem?|existem?|h[áa]|ameaçad[ao]s?)\b", re.IGNORECASE
)

FONTE_PRIORITARIA_PADRAO = "salve"

# Vocabulário fechado (8 valores) — o mesmo usado em `bioma` nas fichas SALVE
# (ver `scripts/processamento/gerar_chunks.py:normalizar_biomas`), conferido
# contra os dados reais indexados. Não cobre "Desconhecido" (não é um bioma
# perguntável). Chave em minúsculas/sem forma alternativa comum -> valor
# exatamente como aparece no payload (o que o filtro precisa bater).
_BIOMAS_CONHECIDOS = {
    "amazônia": "Amazônia", "amazonia": "Amazônia",
    "caatinga": "Caatinga",
    "cerrado": "Cerrado",
    "mata atlântica": "Mata Atlântica", "mata atlantica": "Mata Atlântica",
    "pampa": "Pampa",
    "pantanal": "Pantanal",
    "sistema costeiro-marinho": "Sistema Costeiro-Marinho",
    "costeiro-marinho": "Sistema Costeiro-Marinho",
}

# Cada categoria casa com o código SALVE isolado (maiúsculo, sem
# re.IGNORECASE — "na"/"em" minúsculos são palavras comuns do português, só
# a forma maiúscula EN/NA isolada é inequívoca) ou o nome por extenso em
# português (esse sim case-insensitive, via grupo (?i:...)). Vocabulário
# fechado (8 valores), conferido contra os dados reais indexados.
_PADROES_CATEGORIA_RISCO = {
    "CR": re.compile(r"\bCR\b|(?i:criticamente\s+(?:em\s+perigo|ameaçad[ao]s?))"),
    "EN": re.compile(r"\bEN\b|(?i:\bem\s+perigo\b)"),
    "VU": re.compile(r"\bVU\b|(?i:vulner[aá]ve(?:l|is)\b)"),
    "NT": re.compile(r"\bNT\b|(?i:quase\s+ameaçad[ao]s?)"),
    "LC": re.compile(r"\bLC\b|(?i:(?:menos|pouco)\s+preocupante)"),
    "DD": re.compile(r"\bDD\b|(?i:dados\s+insuficientes)"),
    "EX": re.compile(r"\bEX\b|(?i:extint[ao]s?)"),
    "NA": re.compile(r"\bNA\b|(?i:n[ãa]o\s+avaliad[ao]s?)"),
}


def detectar_biomas(pergunta: str) -> list[str] | None:
    pergunta_lower = pergunta.lower()
    encontrados = {v for k, v in _BIOMAS_CONHECIDOS.items() if k in pergunta_lower}
    return sorted(encontrados) or None


def detectar_categorias_risco(pergunta: str) -> list[str] | None:
    encontradas = [codigo for codigo, padrao in _PADROES_CATEGORIA_RISCO.items() if padrao.search(pergunta)]
    return encontradas or None


def detectar_fonte_prioritaria(pergunta: str) -> str | None:
    """Retorna a fonte a priorizar se a pergunta casar com o padrão de
    "lista de espécies por bioma/táxon", ou None caso contrário.
    """
    tem_taxon = _PADRAO_TAXON_HERPETOFAUNA.search(pergunta)
    if not tem_taxon:
        return None
    tem_pedido_lista = _PADRAO_PEDIDO_LISTA.search(pergunta)
    tem_ocorrencia = _PADRAO_OCORRENCIA.search(pergunta)
    if tem_pedido_lista or tem_ocorrencia:
        return FONTE_PRIORITARIA_PADRAO
    return None


def _chave_chunk(chunk: ChunkRecuperado) -> tuple:
    return (chunk.fonte, chunk.documento, chunk.secao, chunk.pagina_inicio, chunk.texto)


def buscar_chunks_priorizados(
    client: QdrantClient,
    modelo: SentenceTransformer,
    settings: Settings,
    pergunta: str,
    top_k: int,
    fontes: list[str] | None = None,
) -> list[ChunkRecuperado]:
    """Como buscar_chunks, mas quando o cliente não pede uma fonte
    explicitamente e a pergunta casa com o padrão de "lista de espécies por
    bioma/táxon", reserva as vagas do top_k para a fonte prioritária
    primeiro, completando o restante (se sobrar vaga) com os melhores
    resultados da busca sem filtro.

    Isso é priorização por reserva de vagas, não reordenação por score puro:
    um merge por score simples reproduziria o mesmo viés que motivou este
    módulo, já que os trechos genéricos dos PANs tendem a ter score mais
    alto e ocupariam as vagas de novo.
    """
    if fontes:
        return buscar_chunks(client, modelo, settings, pergunta, top_k, fontes)

    fonte_prioritaria = detectar_fonte_prioritaria(pergunta)
    if not fonte_prioritaria:
        return buscar_chunks(client, modelo, settings, pergunta, top_k, None)

    # bioma/categoria_risco só existem no payload de fichas SALVE — só faz
    # sentido aplicar esse filtro extra quando a fonte prioritária já é
    # SALVE (ver docstring do módulo e de buscar_chunks).
    biomas = categorias = None
    if fonte_prioritaria == "salve":
        biomas = detectar_biomas(pergunta)
        categorias = detectar_categorias_risco(pergunta)

    prioritarios = buscar_chunks(
        client, modelo, settings, pergunta, top_k, [fonte_prioritaria],
        bioma=biomas, categoria_risco=categorias,
    )

    faltam = top_k - len(prioritarios)
    if faltam <= 0:
        return prioritarios

    vistos = {_chave_chunk(c) for c in prioritarios}
    complementares = []
    gerais = buscar_chunks(client, modelo, settings, pergunta, top_k, None)
    for chunk in gerais:
        if len(complementares) >= faltam:
            break
        chave = _chave_chunk(chunk)
        if chave in vistos:
            continue
        vistos.add(chave)
        complementares.append(chunk)

    return prioritarios + complementares

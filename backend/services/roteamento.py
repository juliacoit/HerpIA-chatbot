"""Priorização heurística de fonte (e, quando aplicável, de metadado
estruturado de ficha SALVE) para perguntas de "lista de espécies por
bioma/táxon" — ex.: "quais anfíbios ocorrem no Cerrado?".

Contexto (ver diagnosticos/retrieval-cerrado-anfibios.md, caso 4): sem filtro
de fonte, esse tipo de pergunta é dominado por parágrafos genéricos sobre o
bioma vindos de PANs de táxons não relacionados, enquanto o conteúdo
realmente relevante — fichas de espécie do SALVE — fica abaixo do corte.
Isolar `fontes=["salve"]` já reproduz boa precisão para esse padrão de
pergunta (caso 4 do relatório).

Metadado estruturado da ficha SALVE — bioma, categoria de risco, grupo
(Anfíbios/Répteis), estados (ver diagnosticos/agregacao-biomas-fichas-salve.md):
mesmo priorizando SALVE, o LLM ainda tinha que inferir do texto corrido se
uma ficha cobria o critério perguntado — e errava em ambas as direções
(incluía espécie fora do critério, omitia a evidência mais forte). Como toda
ficha SALVE já carrega esses campos como metadado estruturado
(`gerar_chunks.py`), dá para filtrar de forma determinística no Qdrant em
vez de depender do LLM — tira a decisão da geração, mesmo princípio da
priorização de fonte acima. `detectar_filtros_salve` agrega os quatro
detectores; cada um só entra no filtro se achar algo na pergunta. Só se
aplica quando a fonte prioritária já é SALVE (a única fonte com esses
campos); nunca combinado com uma busca sem filtro de fonte, ou excluiria
monitora/pans inteiros (ver docstring de `buscar_chunks`).

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
# espécies/anfíbios/répteis ... ocorrem/existem/são encontrados em <lugar>".
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
    r"\b(ocorrem?|existem?|h[áa]|ameaçad[ao]s?|encontr(?:ados?|adas?|am|a-se))\b",
    re.IGNORECASE,
)

FONTE_PRIORITARIA_PADRAO = "salve"


def _buscar_por_dicionario(pergunta: str, dicionario: dict[str, str]) -> list[str] | None:
    """Helper genérico para os campos "vocabulário fechado, valor de payload
    já normalizado" das fichas SALVE (bioma, estados — mesmo padrão vale
    para o próximo campo que precisar disso). `dicionario` mapeia alias em
    minúsculas (com e sem acento, quando plausível) -> valor exatamente como
    aparece no payload (o que o filtro precisa bater).

    Casamento por `\\b...\\b`, não substring solto: chaves curtas (ex.: um
    nome de estado) podem aparecer dentro de outra palavra por acaso
    ("reparável" contém "pará") — ver diagnosticos/agregacao-biomas-fichas-salve.md
    para o histórico de por que esse cuidado importa aqui.
    """
    pergunta_lower = pergunta.lower()
    encontrados = {
        canonico
        for alias, canonico in dicionario.items()
        if re.search(rf"\b{re.escape(alias)}\b", pergunta_lower)
    }
    return sorted(encontrados) or None


# Vocabulário fechado (8 valores) — o mesmo usado em `bioma` nas fichas SALVE
# (ver `scripts/processamento/gerar_chunks.py:normalizar_lista_csv`),
# conferido contra os dados reais indexados. Não cobre "Desconhecido" (não é
# um bioma perguntável).
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

# Mesmo subconjunto de palavras já validado em `_PADRAO_TAXON_HERPETOFAUNA`
# (não adiciona vocabulário novo nem toca naquele padrão — ele já decide
# quando priorizar SALVE, testado e ajustado ao longo de várias baterias;
# aqui só refina, entre os casos que já disparam a priorização, qual grupo
# taxonômico foi pedido). "Herpetofauna" fica de fora de propósito — cobre
# os dois grupos, não deve virar filtro.
_TERMOS_ANFIBIOS = re.compile(r"\b(anf[íi]bios?|anuros?)\b", re.IGNORECASE)
_TERMOS_REPTEIS = re.compile(
    r"\b(r[ée]pteis?|serpentes?|lagartos?|quel[ôo]nios?|jacar[ée]s?)\b", re.IGNORECASE
)

# 26 estados + DF. Sem alias sem acento para "Pará" — "para" é preposição
# comum demais, geraria falso positivo constante. "Acre" tem risco residual
# documentado (também é uma palavra comum, "sabor acre") — aceito, mesmo
# padrão de imprecisão tolerada já usado nos outros vocabulários fechados
# deste módulo (ver `criticamente em perigo` casando CR e EN).
_ESTADOS_CONHECIDOS = {
    "acre": "Acre",
    "alagoas": "Alagoas",
    "amapá": "Amapá", "amapa": "Amapá",
    "amazonas": "Amazonas",
    "bahia": "Bahia",
    "ceará": "Ceará", "ceara": "Ceará",
    "distrito federal": "Distrito Federal",
    "espírito santo": "Espírito Santo", "espirito santo": "Espírito Santo",
    "goiás": "Goiás", "goias": "Goiás",
    "maranhão": "Maranhão", "maranhao": "Maranhão",
    "mato grosso do sul": "Mato Grosso do Sul",
    "mato grosso": "Mato Grosso",
    "minas gerais": "Minas Gerais",
    "pará": "Pará",
    "paraíba": "Paraíba", "paraiba": "Paraíba",
    "paraná": "Paraná", "parana": "Paraná",
    "pernambuco": "Pernambuco",
    "piauí": "Piauí", "piaui": "Piauí",
    "rio de janeiro": "Rio de Janeiro",
    "rio grande do norte": "Rio Grande do Norte",
    "rio grande do sul": "Rio Grande do Sul",
    "rondônia": "Rondônia", "rondonia": "Rondônia",
    "roraima": "Roraima",
    "santa catarina": "Santa Catarina",
    "são paulo": "São Paulo", "sao paulo": "São Paulo",
    "sergipe": "Sergipe",
    "tocantins": "Tocantins",
}


def detectar_biomas(pergunta: str) -> list[str] | None:
    return _buscar_por_dicionario(pergunta, _BIOMAS_CONHECIDOS)


def detectar_estados(pergunta: str) -> list[str] | None:
    return _buscar_por_dicionario(pergunta, _ESTADOS_CONHECIDOS)


def detectar_categorias_risco(pergunta: str) -> list[str] | None:
    encontradas = [codigo for codigo, padrao in _PADROES_CATEGORIA_RISCO.items() if padrao.search(pergunta)]
    return encontradas or None


def detectar_grupo(pergunta: str) -> list[str] | None:
    grupos = []
    if _TERMOS_ANFIBIOS.search(pergunta):
        grupos.append("Anfíbios")
    if _TERMOS_REPTEIS.search(pergunta):
        grupos.append("Répteis")
    return grupos or None


def detectar_filtros_salve(pergunta: str) -> dict[str, list[str]]:
    """Agrega todos os detectores de metadado estruturado de fichas SALVE
    num único dict pronto para `buscar_chunks(..., filtros_metadados=...)`.
    Cada chave só entra se o detector achou algo — um dict vazio é o valor
    correto quando nada foi detectado (equivalente a "sem filtro").
    """
    filtros: dict[str, list[str]] = {}
    for campo, detector in (
        ("bioma", detectar_biomas),
        ("categoria_risco", detectar_categorias_risco),
        ("grupo", detectar_grupo),
        ("estados", detectar_estados),
    ):
        valores = detector(pergunta)
        if valores:
            filtros[campo] = valores
    return filtros


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

    # bioma/categoria_risco/grupo/estados só existem no payload de fichas
    # SALVE — só faz sentido aplicar esse filtro extra quando a fonte
    # prioritária já é SALVE (ver docstring do módulo e de buscar_chunks).
    filtros_metadados = detectar_filtros_salve(pergunta) if fonte_prioritaria == "salve" else None

    prioritarios = buscar_chunks(
        client, modelo, settings, pergunta, top_k, [fonte_prioritaria],
        filtros_metadados=filtros_metadados,
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

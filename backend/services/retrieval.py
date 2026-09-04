"""Busca semântica no Qdrant: embeda a pergunta com BGE-M3 e recupera os
chunks mais similares, já filtrados por nível de sensibilidade.

Reaproveita a mesma configuração de modelo/coleção usada na indexação
(scripts/indexacao/indexar_chunks.py) — trocar o modelo de embeddings
(ADR 0005, ainda temporário) exige atualizar os dois lugares.
"""

from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchAny, MatchValue
from sentence_transformers import SentenceTransformer

from backend.config import Settings
from backend.schemas import ChunkRecuperado

MODELO_EMBEDDING = "BAAI/bge-m3"
RAIZ = Path(__file__).resolve().parents[2]

# Só chunks de fontes já avaliadas e autorizadas podem ser recuperados. Nenhum
# chunk de 04_documentos_pendentes_avaliacao/ ou 05_documentos_sensiveis_nao_indexar/
# chega a ser indexado (ver gerar_chunks.py), mas este filtro na consulta é a
# segunda camada de defesa — não a única — do requisito de acesso do roadmap
# (Fase 6: "verificar que apenas chunks de documentos autorizados são retornados").
FILTRO_ACESSO = [FieldCondition(key="nivel_sensibilidade", match=MatchValue(value="autorizado"))]


def carregar_modelo_embedding() -> SentenceTransformer:
    return SentenceTransformer(MODELO_EMBEDDING)


def conectar_qdrant(settings: Settings) -> QdrantClient:
    if settings.qdrant_local_path:
        caminho = Path(settings.qdrant_local_path)
        if not caminho.is_absolute():
            caminho = RAIZ / caminho
        return QdrantClient(path=str(caminho))
    return QdrantClient(url=settings.qdrant_url)


def buscar_chunks(
    client: QdrantClient,
    modelo: SentenceTransformer,
    settings: Settings,
    pergunta: str,
    top_k: int,
    fontes: list[str] | None = None,
    bioma: list[str] | None = None,
    categoria_risco: list[str] | None = None,
) -> list[ChunkRecuperado]:
    """`bioma`/`categoria_risco` só têm efeito sobre chunks que têm esses
    campos no payload (hoje só fichas SALVE, ver gerar_chunks.py) — um chunk
    de outra fonte sem o campo nunca bate um MatchAny, então nunca combine
    esses filtros com uma busca sem `fontes=["salve"]`, ou eles excluiriam
    monitora/pans inteiros por engano. Quem decide quando aplicar é
    `backend/services/roteamento.py`, não esta função.
    """
    vetor = modelo.encode([pergunta], normalize_embeddings=True)[0]

    condicoes = list(FILTRO_ACESSO)
    if fontes:
        condicoes.append(FieldCondition(key="fonte", match=MatchAny(any=fontes)))
    if bioma:
        condicoes.append(FieldCondition(key="bioma", match=MatchAny(any=bioma)))
    if categoria_risco:
        condicoes.append(FieldCondition(key="categoria_risco", match=MatchAny(any=categoria_risco)))

    resultados = client.query_points(
        collection_name=settings.qdrant_collection,
        query=vetor.tolist(),
        limit=top_k,
        query_filter=Filter(must=condicoes),
    ).points

    return [
        ChunkRecuperado(
            score=r.score,
            fonte=r.payload.get("fonte", ""),
            documento=r.payload.get("documento", ""),
            texto=r.payload.get("texto", ""),
            secao=r.payload.get("secao") or r.payload.get("categoria"),
            pagina_inicio=r.payload.get("pagina_inicio"),
            pagina_fim=r.payload.get("pagina_fim"),
            url_origem=r.payload.get("url_origem"),
            caminho_local=r.payload.get("caminho_local"),
            nivel_sensibilidade=r.payload.get("nivel_sensibilidade"),
        )
        for r in resultados
        if r.payload
    ]

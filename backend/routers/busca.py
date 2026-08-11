"""Endpoint de busca semântica pura (sem geração) — útil para depurar o
retrieval isoladamente antes de acionar o LLM.
"""

from fastapi import APIRouter, Depends
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

from backend.config import Settings, obter_settings
from backend.dependencies import obter_modelo_embedding, obter_qdrant
from backend.schemas import BuscaRequest, BuscaResponse
from backend.services.retrieval import buscar_chunks

router = APIRouter(prefix="/buscar", tags=["busca"])


@router.post("", response_model=BuscaResponse)
async def buscar(
    body: BuscaRequest,
    client: QdrantClient = Depends(obter_qdrant),
    modelo: SentenceTransformer = Depends(obter_modelo_embedding),
    settings: Settings = Depends(obter_settings),
) -> BuscaResponse:
    resultados = buscar_chunks(client, modelo, settings, body.pergunta, body.top_k, body.fontes)
    return BuscaResponse(pergunta=body.pergunta, resultados=resultados)

"""Endpoint principal do RAG: busca + geração de resposta com citações."""

import httpx
from fastapi import APIRouter, Depends, HTTPException
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

from backend.config import Settings, obter_settings
from backend.dependencies import obter_llm, obter_modelo_embedding, obter_qdrant
from backend.schemas import PerguntarRequest, PerguntarResponse
from backend.services.geracao import gerar_resposta
from backend.services.llm import LLMClient
from backend.services.roteamento import buscar_chunks_priorizados

router = APIRouter(prefix="/perguntar", tags=["perguntar"])


@router.post("", response_model=PerguntarResponse)
async def perguntar(
    body: PerguntarRequest,
    client: QdrantClient = Depends(obter_qdrant),
    modelo: SentenceTransformer = Depends(obter_modelo_embedding),
    llm: LLMClient = Depends(obter_llm),
    settings: Settings = Depends(obter_settings),
) -> PerguntarResponse:
    chunks = buscar_chunks_priorizados(client, modelo, settings, body.pergunta, body.top_k, body.fontes)
    try:
        return await gerar_resposta(llm, body.pergunta, chunks)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                f"LLM local (Ollama) indisponível: {exc}. Ver ADR 0006 — "
                "rode 'ollama serve' e baixe o modelo com "
                f"'ollama pull {settings.llm_model}'."
            ),
        ) from exc

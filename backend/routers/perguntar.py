"""Endpoint principal do RAG: busca + geração de resposta com citações."""

import time

import httpx
from fastapi import APIRouter, Depends, HTTPException
from psycopg_pool import ConnectionPool
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

from backend.config import Settings, obter_settings
from backend.dependencies import obter_db_pool, obter_llm, obter_modelo_embedding, obter_qdrant
from backend.schemas import PerguntarRequest, PerguntarResponse
from backend.services.geracao import gerar_resposta
from backend.services.llm import LLMClient
from backend.services.logging_db import registrar_interacao
from backend.services.roteamento import buscar_chunks_priorizados

router = APIRouter(prefix="/perguntar", tags=["perguntar"])


@router.post("", response_model=PerguntarResponse)
async def perguntar(
    body: PerguntarRequest,
    client: QdrantClient = Depends(obter_qdrant),
    modelo: SentenceTransformer = Depends(obter_modelo_embedding),
    llm: LLMClient = Depends(obter_llm),
    settings: Settings = Depends(obter_settings),
    db_pool: ConnectionPool | None = Depends(obter_db_pool),
) -> PerguntarResponse:
    chunks = buscar_chunks_priorizados(client, modelo, settings, body.pergunta, body.top_k, body.fontes)

    inicio = time.perf_counter()
    try:
        resultado = await gerar_resposta(llm, body.pergunta, chunks, settings)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                f"LLM local (Ollama) indisponível: {exc}. Ver ADR 0006 — "
                "rode 'ollama serve' e baixe o modelo com "
                f"'ollama pull {settings.llm_model}'."
            ),
        ) from exc
    tempo_resposta_ms = int((time.perf_counter() - inicio) * 1000)

    resultado.id = registrar_interacao(
        db_pool,
        pergunta=body.pergunta,
        top_k=body.top_k,
        fontes_filtro=body.fontes,
        resposta=resultado.resposta,
        evidencia_suficiente=resultado.evidencia_suficiente,
        resposta_fundamentada=resultado.resposta_fundamentada,
        justificativa_groundedness=resultado.justificativa_groundedness,
        citacoes=resultado.citacoes,
        chunks=chunks,
        modelo_llm=settings.llm_model,
        tempo_resposta_ms=tempo_resposta_ms,
    )
    return resultado

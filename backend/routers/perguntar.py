"""Endpoint principal do RAG: busca + geração de resposta com citações."""

import json
import time

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response
from psycopg_pool import ConnectionPool
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

from backend.config import Settings, obter_settings
from backend.dependencies import (
    exigir_usuario_para,
    obter_catalogo_especies,
    obter_db_pool,
    obter_llm,
    obter_modelo_embedding,
    obter_qdrant,
)
from backend.schemas import PerguntarRequest, PerguntarResponse
from backend.services.auth import UsuarioAutenticado
from backend.services.especies_salve import CatalogoEspecies
from backend.services.geracao import gerar_resposta
from backend.services.llm import LLMClient, registrar_uso_llm
from backend.services.logging_db import descrever_rota, registrar_interacao
from backend.services.roteamento import buscar_chunks_priorizados

router = APIRouter(prefix="/perguntar", tags=["perguntar"])


@router.post("", response_model=PerguntarResponse)
async def perguntar(
    body: PerguntarRequest,
    response: Response,
    client: QdrantClient = Depends(obter_qdrant),
    modelo: SentenceTransformer = Depends(obter_modelo_embedding),
    llm: LLMClient = Depends(obter_llm),
    settings: Settings = Depends(obter_settings),
    db_pool: ConnectionPool | None = Depends(obter_db_pool),
    usuario: UsuarioAutenticado | None = Depends(exigir_usuario_para("consulta")),
    catalogo: CatalogoEspecies | None = Depends(obter_catalogo_especies),
) -> PerguntarResponse:
    if body.incluir_contextos and not settings.permitir_modo_avaliacao:
        raise HTTPException(status_code=403, detail="Modo de avaliação desabilitado neste ambiente.")

    chunks = buscar_chunks_priorizados(
        client, modelo, settings, body.pergunta, body.top_k, body.fontes, catalogo=catalogo
    )

    inicio = time.perf_counter()
    try:
        with registrar_uso_llm() as uso_llm:
            resultado = await gerar_resposta(
                llm, body.pergunta, chunks, settings, incluir_avaliacao=body.incluir_contextos
            )
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
    # Uso de tokens por chamada ao LLM (geração e, se ligado, juiz), para a
    # bateria detectar prompts perto do limite de contexto sem mudar o schema.
    response.headers["X-LLM-Uso"] = json.dumps(uso_llm)

    # Requisições de avaliação não entram na tabela `interacoes` (não são uso
    # real e trazem respostas retidas): `id` fica None, sem feedback possível.
    if body.incluir_contextos:
        return resultado

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
        rota=descrever_rota(body.pergunta, body.fontes, catalogo),
        tipo_saida=resultado.tipo_saida,
        origem_retencao=resultado._origem_retencao,
        resposta_original=resultado._resposta_original,
        llm_temperatura=settings.llm_temperature,
        llm_seed=settings.llm_seed,
        usuario_id=usuario.id if usuario else None,
    )
    return resultado

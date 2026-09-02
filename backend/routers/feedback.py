"""Endpoint de feedback do usuário (thumbs up/down) por resposta, Fase 6."""

from fastapi import APIRouter, Depends, HTTPException
from psycopg_pool import ConnectionPool

from backend.dependencies import obter_db_pool
from backend.schemas import FeedbackRequest, FeedbackResponse
from backend.services.logging_db import registrar_feedback

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackResponse)
async def feedback(
    body: FeedbackRequest, pool: ConnectionPool | None = Depends(obter_db_pool)
) -> FeedbackResponse:
    if pool is None:
        raise HTTPException(
            status_code=503,
            detail="PostgreSQL indisponível nesta sessão — feedback não pode ser registrado agora.",
        )
    encontrada = registrar_feedback(
        pool,
        interacao_id=body.interacao_id,
        avaliacao=body.avaliacao,
        comentario=body.comentario,
    )
    if not encontrada:
        raise HTTPException(status_code=404, detail=f"Interação {body.interacao_id} não encontrada.")
    return FeedbackResponse()

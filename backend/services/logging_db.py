"""Logging de perguntas/respostas e feedback no PostgreSQL (Fase 6).

Só grava metadados das citações/chunks recuperados (fonte, documento,
página, score) — nunca o texto completo dos chunks, que já vive no Qdrant e
nos documentos de origem; evita duplicar dado (potencialmente sensível, ver
CLAUDE.md) num segundo lugar sem necessidade.

Gravar nunca derruba a requisição: se o pool for None (PostgreSQL
indisponível, ver backend/db.py) ou a escrita falhar, só loga um aviso e
devolve None/False.
"""

import logging

from psycopg.types.json import Json
from psycopg_pool import ConnectionPool

from backend.schemas import ChunkRecuperado, Citacao

log = logging.getLogger(__name__)


def registrar_interacao(
    pool: ConnectionPool | None,
    *,
    pergunta: str,
    top_k: int,
    fontes_filtro: list[str] | None,
    resposta: str,
    evidencia_suficiente: bool,
    resposta_fundamentada: bool,
    justificativa_groundedness: str | None,
    citacoes: list[Citacao],
    chunks: list[ChunkRecuperado],
    modelo_llm: str,
    tempo_resposta_ms: int,
) -> int | None:
    if pool is None:
        return None

    chunks_meta = [
        {
            "fonte": c.fonte,
            "documento": c.documento,
            "secao": c.secao,
            "pagina_inicio": c.pagina_inicio,
            "pagina_fim": c.pagina_fim,
            "score": c.score,
        }
        for c in chunks
    ]
    try:
        with pool.connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO interacoes (
                    pergunta, top_k, fontes_filtro, resposta,
                    evidencia_suficiente, resposta_fundamentada,
                    justificativa_groundedness, citacoes, chunks_recuperados,
                    modelo_llm, tempo_resposta_ms
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    pergunta,
                    top_k,
                    # lista vazia -> NULL: um TEXT[] vazio sem elementos não
                    # dá pra psycopg inferir o tipo do array ao adaptar.
                    fontes_filtro or None,
                    resposta,
                    evidencia_suficiente,
                    resposta_fundamentada,
                    justificativa_groundedness,
                    Json([c.model_dump() for c in citacoes]),
                    Json(chunks_meta),
                    modelo_llm,
                    tempo_resposta_ms,
                ),
            )
            interacao_id = cur.fetchone()[0]
            conn.commit()
            return interacao_id
    except Exception as exc:
        log.warning("Falha ao registrar interação no PostgreSQL: %s", exc)
        return None


def registrar_feedback(
    pool: ConnectionPool, *, interacao_id: int, avaliacao: int, comentario: str | None
) -> bool:
    """Devolve False se `interacao_id` não existir. Assume pool != None —
    quem chama (backend/routers/feedback.py) já trata o caso de pool
    indisponível antes de chegar aqui."""
    with pool.connection() as conn:
        existe = conn.execute("SELECT 1 FROM interacoes WHERE id = %s", (interacao_id,)).fetchone()
        if existe is None:
            return False
        conn.execute(
            "INSERT INTO feedback (interacao_id, avaliacao, comentario) VALUES (%s, %s, %s)",
            (interacao_id, avaliacao, comentario),
        )
        conn.commit()
        return True

"""Dependências injetadas nos endpoints (padrão FastAPI Depends).

Os recursos pesados (modelo de embeddings, cliente Qdrant, cliente LLM) são
carregados uma única vez no startup (ver main.py, lifespan) e reaproveitados
a cada requisição — carregar o BGE-M3 por requisição inviabilizaria a latência.
"""

from fastapi import Request
from psycopg_pool import ConnectionPool
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

from backend.services.llm import LLMClient


def obter_qdrant(request: Request) -> QdrantClient:
    return request.app.state.qdrant_client


def obter_modelo_embedding(request: Request) -> SentenceTransformer:
    return request.app.state.modelo_embedding


def obter_llm(request: Request) -> LLMClient:
    return request.app.state.llm_client


def obter_db_pool(request: Request) -> ConnectionPool | None:
    """None quando o PostgreSQL não estava acessível no startup — ver
    backend/db.py. Quem usa (routers/perguntar.py, routers/feedback.py)
    trata esse caso sem quebrar a requisição."""
    return request.app.state.db_pool

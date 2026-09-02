"""Backend FastAPI do HerpIA (Sistema RAG para Consulta Inteligente de Dados
sobre a Herpetofauna Brasileira — RAN/ICMBio), Fase 6 do roadmap.

Esqueleto inicial: busca semântica (/buscar), geração de resposta com
citações (/perguntar), logging de interações e feedback (/feedback) em
PostgreSQL. Ainda não implementados: busca híbrida, autenticação de
usuários — ver docs/processos/backend_fastapi.md.

Rodar localmente:
    uvicorn backend.main:app --reload
Docs interativas: http://localhost:8000/docs
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.config import obter_settings
from backend.db import abrir_pool, fechar_pool
from backend.routers import busca, feedback, perguntar
from backend.services.llm import criar_llm_client
from backend.services.retrieval import MODELO_EMBEDDING, carregar_modelo_embedding, conectar_qdrant


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = obter_settings()
    print(f"Carregando modelo de embeddings ({MODELO_EMBEDDING})...")
    app.state.modelo_embedding = carregar_modelo_embedding()
    app.state.qdrant_client = conectar_qdrant(settings)
    app.state.llm_client = criar_llm_client(settings)
    app.state.db_pool = abrir_pool(settings)
    yield
    fechar_pool(app.state.db_pool)


app = FastAPI(
    title="HerpIA — API",
    description=(
        "HerpIA — Assistente Inteligente para Consulta de Informações sobre a "
        "Herpetofauna Brasileira. Nome técnico: Sistema RAG para Consulta "
        "Inteligente de Dados sobre a Herpetofauna Brasileira — RAN/ICMBio. "
        "RAG sobre herpetofauna brasileira (répteis e anfíbios) para "
        "técnicos e gestores do RAN/ICMBio."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(busca.router)
app.include_router(perguntar.router)
app.include_router(feedback.router)


@app.get("/saude", tags=["saude"])
async def saude() -> dict:
    return {"status": "ok"}

"""Backend FastAPI do chatbot RAG do RAN/ICMBio (Fase 6 do roadmap).

Esqueleto inicial: busca semântica (/buscar) e geração de resposta com
citações (/perguntar). Ainda não implementados: logging/feedback em
PostgreSQL, busca híbrida, autenticação de usuários — ver
docs/processos/backend_fastapi.md.

Rodar localmente:
    uvicorn backend.main:app --reload
Docs interativas: http://localhost:8000/docs
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.config import obter_settings
from backend.routers import busca, perguntar
from backend.services.llm import criar_llm_client
from backend.services.retrieval import MODELO_EMBEDDING, carregar_modelo_embedding, conectar_qdrant


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = obter_settings()
    print(f"Carregando modelo de embeddings ({MODELO_EMBEDDING})...")
    app.state.modelo_embedding = carregar_modelo_embedding()
    app.state.qdrant_client = conectar_qdrant(settings)
    app.state.llm_client = criar_llm_client(settings)
    yield


app = FastAPI(
    title="Chatbot RAN/ICMBio — API",
    description=(
        "RAG sobre herpetofauna brasileira (répteis e anfíbios) para "
        "técnicos e gestores do RAN/ICMBio."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(busca.router)
app.include_router(perguntar.router)


@app.get("/saude", tags=["saude"])
async def saude() -> dict:
    return {"status": "ok"}

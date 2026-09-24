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

from fastapi import Depends, FastAPI

from backend.config import Settings, obter_settings
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
async def saude(settings: Settings = Depends(obter_settings)) -> dict:
    # Configuração do LLM em vigor no processo do backend (não no de quem
    # chama) — usada pela bateria para registrar o que de fato rodou.
    return {
        "status": "ok",
        "llm": {
            "provider": settings.llm_provider,
            "modelo": settings.llm_model,
            "num_ctx": settings.llm_num_ctx,
            "temperature": settings.llm_temperature,
            "seed": settings.llm_seed,
            "think": settings.llm_think,
            "timeout": settings.llm_timeout,
            "groundedness_verificar": settings.groundedness_verificar,
            "top_k_padrao": settings.top_k_padrao,
        },
    }

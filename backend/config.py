"""Configuração do backend, carregada do .env (ver .env.example na raiz).

Reaproveita as mesmas variáveis já usadas pelos scripts de indexação
(QDRANT_URL, QDRANT_LOCAL_PATH, QDRANT_COLLECTION) e definidas no ADR 0006
(LLM_PROVIDER, OLLAMA_URL, LLM_MODEL) — nenhuma variável nova.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

RAIZ = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=RAIZ / ".env", extra="ignore")

    app_env: str = "development"

    qdrant_url: str = "http://localhost:6333"
    qdrant_local_path: str | None = None
    qdrant_collection: str = "ran_herpetofauna"

    llm_provider: str = "ollama"
    ollama_url: str = "http://localhost:11434"
    llm_model: str = "qwen2.5:3b-instruct"
    openai_api_key: str | None = None

    top_k_padrao: int = 5

    groundedness_verificar: bool = True


@lru_cache
def obter_settings() -> Settings:
    return Settings()

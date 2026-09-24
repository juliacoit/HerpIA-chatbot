"""Configuração do backend, carregada do .env (ver .env.example na raiz).

Reaproveita as mesmas variáveis já usadas pelos scripts de indexação
(QDRANT_URL, QDRANT_LOCAL_PATH, QDRANT_COLLECTION) e definidas no ADR 0006
(LLM_PROVIDER, OLLAMA_URL, LLM_MODEL). Os parâmetros LLM_NUM_CTX,
LLM_TEMPERATURE, LLM_SEED, LLM_THINK e LLM_TIMEOUT foram acrescentados para a
comparação de geradores (diagnosticos/comparacao-geradores-rodada1.md).
"""

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

RAIZ = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=RAIZ / ".env", extra="ignore")

    app_env: str = "development"

    database_url: str = "postgresql://ran_user:change_me@localhost:5432/ran_chatbot"

    qdrant_url: str = "http://localhost:6333"
    qdrant_local_path: str | None = None
    qdrant_collection: str = "ran_herpetofauna"

    llm_provider: str = "ollama"
    ollama_url: str = "http://localhost:11434"
    llm_model: str = "qwen2.5:3b-instruct"
    # Parâmetros enviados ao Ollama. None = não enviar o campo (vale o padrão
    # do modelo). num_ctx é o único com default ativo: o padrão do Ollama
    # (4096) já quase estoura com top_k=5 (3977 tokens medidos).
    llm_num_ctx: int = 8192
    llm_temperature: float | None = None
    llm_seed: int | None = None
    llm_think: bool | str | None = None  # true/false, ou low/medium/high (gpt-oss)
    llm_timeout: float = 120.0
    openai_api_key: str | None = None

    top_k_padrao: int = 5

    groundedness_verificar: bool = True

    @field_validator("llm_think", mode="before")
    @classmethod
    def _normalizar_think(cls, valor):
        # Sem isto, "false" vindo do ambiente ficaria string (bool | str) e o
        # Ollama receberia "false" em vez de false.
        if valor is None or isinstance(valor, bool):
            return valor
        texto = str(valor).strip().lower()
        if texto == "":
            return None
        if texto in ("true", "false"):
            return texto == "true"
        if texto in ("low", "medium", "high"):
            return texto
        raise ValueError("LLM_THINK aceita true/false ou low/medium/high")


@lru_cache
def obter_settings() -> Settings:
    return Settings()

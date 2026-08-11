"""Interface de LLM para a etapa de geração (ADR 0006).

Isola a chamada ao modelo de linguagem atrás de LLMClient.generate(prompt)
para que trocar de modelo local ou migrar para uma API paga no futuro seja
só uma troca de implementação — o resto do pipeline (retrieval, filtro de
acesso, formatação de citações) não muda.
"""

from abc import ABC, abstractmethod

import httpx

from backend.config import Settings


class LLMClient(ABC):
    @abstractmethod
    async def generate(self, prompt: str) -> str:
        """Gera uma resposta em texto a partir do prompt completo."""


class OllamaLLMClient(LLMClient):
    """Implementação temporária (ADR 0006): LLM local via Ollama."""

    def __init__(self, base_url: str, modelo: str, timeout: float = 120.0):
        self._base_url = base_url.rstrip("/")
        self._modelo = modelo
        self._timeout = timeout

    async def generate(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resposta = await client.post(
                f"{self._base_url}/api/generate",
                json={"model": self._modelo, "prompt": prompt, "stream": False},
            )
            resposta.raise_for_status()
            return resposta.json()["response"].strip()


def criar_llm_client(settings: Settings) -> LLMClient:
    if settings.llm_provider == "ollama":
        return OllamaLLMClient(base_url=settings.ollama_url, modelo=settings.llm_model)
    raise ValueError(
        f"LLM_PROVIDER={settings.llm_provider!r} ainda não implementado — "
        "só 'ollama' está disponível no momento (ver ADR 0006)."
    )

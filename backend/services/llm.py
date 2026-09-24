"""Interface de LLM para a etapa de geração (ADR 0006).

Isola a chamada ao modelo de linguagem atrás de LLMClient.generate(prompt)
para que trocar de modelo local ou migrar para uma API paga no futuro seja
só uma troca de implementação — o resto do pipeline (retrieval, filtro de
acesso, formatação de citações) não muda.
"""

from abc import ABC, abstractmethod
from contextlib import contextmanager
from contextvars import ContextVar

import httpx

from backend.config import Settings

# Uso de tokens das chamadas feitas dentro de uma requisição (ver
# registrar_uso_llm). Fica fora da interface LLMClient de propósito: quem
# chama generate() não precisa saber disso.
_uso_llm: ContextVar[list[dict] | None] = ContextVar("uso_llm", default=None)

LIMIAR_ALERTA_CONTEXTO = 0.85


@contextmanager
def registrar_uso_llm():
    """Coleta o uso de tokens de cada generate() feito dentro do bloco, na
    ordem das chamadas (em /perguntar: geração e, se ligado, juiz)."""
    uso: list[dict] = []
    token = _uso_llm.set(uso)
    try:
        yield uso
    finally:
        _uso_llm.reset(token)


class LLMClient(ABC):
    @abstractmethod
    async def generate(self, prompt: str) -> str:
        """Gera uma resposta em texto a partir do prompt completo."""


class OllamaLLMClient(LLMClient):
    """Implementação temporária (ADR 0006): LLM local via Ollama."""

    def __init__(
        self,
        base_url: str,
        modelo: str,
        opcoes: dict | None = None,
        think: bool | str | None = None,
        timeout: float = 120.0,
    ):
        self._base_url = base_url.rstrip("/")
        self._modelo = modelo
        self._opcoes = opcoes or {}
        self._think = think
        self._timeout = timeout

    async def generate(self, prompt: str) -> str:
        payload = {"model": self._modelo, "prompt": prompt, "stream": False}
        if self._opcoes:
            payload["options"] = self._opcoes
        if self._think is not None:
            payload["think"] = self._think
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resposta = await client.post(f"{self._base_url}/api/generate", json=payload)
            resposta.raise_for_status()
            corpo = resposta.json()
        self._registrar_uso(corpo)
        return corpo["response"].strip()

    def _registrar_uso(self, corpo: dict) -> None:
        """Loga prompt_eval_count/eval_count para detectar prompts perto do
        limite de contexto (o Ollama corta o início do prompt em silêncio)."""
        num_ctx = self._opcoes.get("num_ctx")
        uso = {
            "prompt_eval_count": corpo.get("prompt_eval_count"),
            "eval_count": corpo.get("eval_count"),
            "num_ctx": num_ctx,
        }
        alerta = ""
        if num_ctx and uso["prompt_eval_count"] and uso["prompt_eval_count"] > LIMIAR_ALERTA_CONTEXTO * num_ctx:
            alerta = f" ⚠ acima de {LIMIAR_ALERTA_CONTEXTO:.0%} do contexto"
        print(
            f"[llm] {self._modelo}: prompt={uso['prompt_eval_count']}/{num_ctx} "
            f"saída={uso['eval_count']}{alerta}"
        )
        lista = _uso_llm.get()
        if lista is not None:
            lista.append(uso)


def criar_llm_client(settings: Settings) -> LLMClient:
    if settings.llm_provider == "ollama":
        opcoes = {"num_ctx": settings.llm_num_ctx}
        if settings.llm_temperature is not None:
            opcoes["temperature"] = settings.llm_temperature
        if settings.llm_seed is not None:
            opcoes["seed"] = settings.llm_seed
        return OllamaLLMClient(
            base_url=settings.ollama_url,
            modelo=settings.llm_model,
            opcoes=opcoes,
            think=settings.llm_think,
            timeout=settings.llm_timeout,
        )
    raise ValueError(
        f"LLM_PROVIDER={settings.llm_provider!r} ainda não implementado — "
        "só 'ollama' está disponível no momento (ver ADR 0006)."
    )

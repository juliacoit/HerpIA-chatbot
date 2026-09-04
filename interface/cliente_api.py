"""Cliente HTTP do backend FastAPI (backend/main.py), usado pela interface
Streamlit (interface/app.py). Isola as chamadas de rede da lógica de exibição
— mesma separação de responsabilidades do resto do projeto.
"""

import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

API_BASE_URL = os.environ.get("BACKEND_API_URL", "http://localhost:8000")
TIMEOUT_SEGUNDOS = 60.0


class ErroAPI(Exception):
    """Erro de comunicação com o backend, com mensagem já pronta para exibição."""


def _tratar_erro_conexao(exc: httpx.ConnectError) -> ErroAPI:
    return ErroAPI(
        f"Não foi possível conectar ao backend em {API_BASE_URL}. "
        "Confirme que ele está rodando (`uvicorn backend.main:app`) — "
        "ver SETUP_PROJETO.md."
    )


def verificar_saude() -> bool:
    try:
        resposta = httpx.get(f"{API_BASE_URL}/saude", timeout=5.0)
        return resposta.status_code == 200
    except httpx.ConnectError:
        return False


def perguntar(pergunta: str, top_k: int = 5, fontes: list[str] | None = None) -> dict:
    """POST /perguntar — retrieval + geração com citações e groundedness."""
    payload: dict = {"pergunta": pergunta, "top_k": top_k}
    if fontes:
        payload["fontes"] = fontes

    try:
        resposta = httpx.post(f"{API_BASE_URL}/perguntar", json=payload, timeout=TIMEOUT_SEGUNDOS)
    except httpx.ConnectError as exc:
        raise _tratar_erro_conexao(exc) from exc

    if resposta.status_code == 503:
        detalhe = resposta.json().get("detail", "Serviço indisponível (503).")
        raise ErroAPI(detalhe)
    resposta.raise_for_status()
    return resposta.json()


def enviar_feedback(interacao_id: int, avaliacao: int, comentario: str | None = None) -> None:
    """POST /feedback — thumbs up/down (1/-1) para uma interação já registrada."""
    payload: dict = {"interacao_id": interacao_id, "avaliacao": avaliacao}
    if comentario:
        payload["comentario"] = comentario

    try:
        resposta = httpx.post(f"{API_BASE_URL}/feedback", json=payload, timeout=TIMEOUT_SEGUNDOS)
    except httpx.ConnectError as exc:
        raise _tratar_erro_conexao(exc) from exc

    if resposta.status_code == 503:
        raise ErroAPI("PostgreSQL indisponível — não é possível registrar feedback nesta sessão.")
    if resposta.status_code == 404:
        raise ErroAPI("Interação não encontrada — não é possível registrar feedback.")
    resposta.raise_for_status()

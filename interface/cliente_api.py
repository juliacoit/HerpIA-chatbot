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


class ErroSessao(ErroAPI):
    """O backend recusou a sessão (ausente ou expirada) — é preciso entrar de novo."""


def _tratar_erro_conexao(exc: httpx.ConnectError) -> ErroAPI:
    return ErroAPI(
        f"Não foi possível conectar ao backend em {API_BASE_URL}. "
        "Confirme que ele está rodando (`uvicorn backend.main:app`) — "
        "ver SETUP_PROJETO.md."
    )


def _cabecalhos(token: str | None) -> dict:
    return {"Authorization": f"Bearer {token}"} if token else {}


def _detalhe(resposta: httpx.Response, padrao: str) -> str:
    try:
        detalhe = resposta.json().get("detail")
    except ValueError:
        return padrao
    return detalhe if isinstance(detalhe, str) else padrao


def _post(caminho: str, payload: dict, token: str | None = None) -> httpx.Response:
    try:
        resposta = httpx.post(
            f"{API_BASE_URL}{caminho}", json=payload, headers=_cabecalhos(token), timeout=TIMEOUT_SEGUNDOS
        )
    except httpx.ConnectError as exc:
        raise _tratar_erro_conexao(exc) from exc
    if resposta.status_code == 401 and not caminho.startswith("/auth/"):
        raise ErroSessao(_detalhe(resposta, "Sessão ausente ou expirada. Entre novamente."))
    return resposta


def estado_backend() -> dict | None:
    """GET /saude. Devolve None se o backend não respondeu; senão, um dict
    com `auth_exigir` ("nada", "feedback" ou "tudo" — ver AUTH_EXIGIR no
    .env.example), que decide se a interface mostra a tela de login."""
    try:
        resposta = httpx.get(f"{API_BASE_URL}/saude", timeout=5.0)
    except httpx.HTTPError:
        return None
    if resposta.status_code != 200:
        return None
    return {"auth_exigir": resposta.json().get("auth", {}).get("exigir", "nada")}


def verificar_saude() -> bool:
    return estado_backend() is not None


def entrar(usuario: str, senha: str) -> dict:
    """POST /auth/login — devolve token, validade e dados do usuário."""
    resposta = _post("/auth/login", {"usuario": usuario, "senha": senha})
    if resposta.status_code != 200:
        raise ErroAPI(_detalhe(resposta, "Não foi possível entrar."))
    return resposta.json()


def primeiro_acesso(usuario: str, codigo_convite: str, senha: str) -> None:
    """POST /auth/primeiro-acesso — troca o código de convite pela senha escolhida."""
    resposta = _post(
        "/auth/primeiro-acesso", {"usuario": usuario, "codigo_convite": codigo_convite, "senha": senha}
    )
    if resposta.status_code != 200:
        raise ErroAPI(_detalhe(resposta, "Não foi possível definir a senha."))


def usuario_da_sessao(token: str) -> dict | None:
    """GET /auth/eu — dados do usuário (`usuario`, `nome`) se a sessão ainda
    vale; None se o backend a recusou. Levanta ErroAPI se o backend não
    respondeu, para quem chama não confundir "fora do ar" com "sessão expirada"."""
    try:
        resposta = httpx.get(f"{API_BASE_URL}/auth/eu", headers=_cabecalhos(token), timeout=10.0)
    except httpx.HTTPError as exc:
        raise ErroAPI("O backend não respondeu ao verificar a sessão.") from exc
    if resposta.status_code == 401:
        return None
    if resposta.status_code != 200:
        raise ErroAPI(_detalhe(resposta, "Não foi possível verificar a sessão."))
    return resposta.json()


def sair(token: str) -> None:
    """POST /auth/sair — encerra a sessão no backend. Falha de rede não
    impede a saída na interface, que esquece o token de qualquer forma."""
    try:
        _post("/auth/sair", {}, token)
    except ErroAPI:
        pass


def perguntar(
    pergunta: str, top_k: int = 5, fontes: list[str] | None = None, token: str | None = None
) -> dict:
    """POST /perguntar — retrieval + geração com citações e groundedness."""
    payload: dict = {"pergunta": pergunta, "top_k": top_k}
    if fontes:
        payload["fontes"] = fontes

    resposta = _post("/perguntar", payload, token)
    if resposta.status_code == 503:
        raise ErroAPI(_detalhe(resposta, "Serviço indisponível (503)."))
    resposta.raise_for_status()
    return resposta.json()


def enviar_feedback(
    interacao_id: int,
    avaliacao: int,
    comentario: str | None = None,
    token: str | None = None,
    motivos: list[str] | None = None,
) -> None:
    """POST /feedback — thumbs up/down (1/-1) para uma interação já registrada,
    com comentário e motivos (só no negativo) opcionais."""
    payload: dict = {"interacao_id": interacao_id, "avaliacao": avaliacao}
    if comentario:
        payload["comentario"] = comentario
    if motivos:
        payload["motivos"] = motivos

    resposta = _post("/feedback", payload, token)
    if resposta.status_code == 503:
        raise ErroAPI("PostgreSQL indisponível — não é possível registrar feedback nesta sessão.")
    if resposta.status_code == 404:
        raise ErroAPI("Interação não encontrada — não é possível registrar feedback.")
    resposta.raise_for_status()

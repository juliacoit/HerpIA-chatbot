"""Dependências injetadas nos endpoints (padrão FastAPI Depends).

Os recursos pesados (modelo de embeddings, cliente Qdrant, cliente LLM) são
carregados uma única vez no startup (ver main.py, lifespan) e reaproveitados
a cada requisição — carregar o BGE-M3 por requisição inviabilizaria a latência.
"""

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from psycopg_pool import ConnectionPool
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

from backend.config import Settings, obter_settings
from backend.services import auth
from backend.services.auth import UsuarioAutenticado
from backend.services.especies_salve import CatalogoEspecies
from backend.services.llm import LLMClient

# auto_error=False: a ausência do cabeçalho não é erro por si só — quem decide
# se a sessão é obrigatória é exigir_usuario_para, conforme AUTH_EXIGIR.
esquema_bearer = HTTPBearer(auto_error=False)


def obter_qdrant(request: Request) -> QdrantClient:
    return request.app.state.qdrant_client


def obter_modelo_embedding(request: Request) -> SentenceTransformer:
    return request.app.state.modelo_embedding


def obter_llm(request: Request) -> LLMClient:
    return request.app.state.llm_client


def obter_catalogo_especies(request: Request) -> CatalogoEspecies | None:
    """None se o catálogo não carregou no startup (ou nos testes, que não
    rodam o lifespan): a busca segue sem o roteamento por espécie."""
    return getattr(request.app.state, "catalogo_especies", None)


def obter_db_pool(request: Request) -> ConnectionPool | None:
    """None quando o PostgreSQL não estava acessível no startup — ver
    backend/db.py. Quem usa (routers/perguntar.py, routers/feedback.py)
    trata esse caso sem quebrar a requisição."""
    return request.app.state.db_pool


def obter_usuario_opcional(
    credenciais: HTTPAuthorizationCredentials | None = Depends(esquema_bearer),
    pool: ConnectionPool | None = Depends(obter_db_pool),
) -> UsuarioAutenticado | None:
    """Usuário da sessão enviada em `Authorization: Bearer <token>`, ou None
    (sem cabeçalho, sessão inválida/expirada ou PostgreSQL indisponível)."""
    if credenciais is None or pool is None:
        return None
    return auth.obter_usuario_da_sessao(pool, credenciais.credentials)


def exigir_usuario_para(escopo: str):
    """Dependência por endpoint: `escopo` é "consulta" (/buscar, /perguntar)
    ou "feedback". Devolve o usuário (ou None quando o escopo não exige
    sessão e nenhuma foi enviada); responde 401 quando AUTH_EXIGIR cobre o
    escopo e não há sessão válida."""

    def dependencia(
        usuario: UsuarioAutenticado | None = Depends(obter_usuario_opcional),
        pool: ConnectionPool | None = Depends(obter_db_pool),
        settings: Settings = Depends(obter_settings),
    ) -> UsuarioAutenticado | None:
        exigido = settings.auth_exigir == "tudo" or (
            settings.auth_exigir == "feedback" and escopo == "feedback"
        )
        if exigido and usuario is None:
            if pool is None:
                raise HTTPException(
                    status_code=503,
                    detail="PostgreSQL indisponível nesta sessão — não é possível verificar o acesso agora.",
                )
            raise HTTPException(
                status_code=401,
                detail="Sessão ausente ou expirada. Entre novamente.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return usuario

    return dependencia

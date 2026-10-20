"""Endpoints de autenticação: primeiro acesso, login, sessão atual e saída.

Regras e modelo de acesso em backend/services/auth.py e
docs/processos/autenticacao.md.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from psycopg_pool import ConnectionPool

from backend.config import Settings, obter_settings
from backend.dependencies import esquema_bearer, obter_db_pool, obter_usuario_opcional
from backend.schemas import (
    LoginRequest,
    LoginResponse,
    OkResponse,
    PrimeiroAcessoRequest,
    UsuarioResponse,
)
from backend.services import auth
from backend.services.auth import UsuarioAutenticado

router = APIRouter(prefix="/auth", tags=["auth"])


def _exigir_pool(pool: ConnectionPool | None) -> ConnectionPool:
    if pool is None:
        raise HTTPException(
            status_code=503,
            detail="PostgreSQL indisponível nesta sessão — não é possível autenticar agora.",
        )
    return pool


@router.post("/primeiro-acesso", response_model=OkResponse)
async def primeiro_acesso(
    body: PrimeiroAcessoRequest, pool: ConnectionPool | None = Depends(obter_db_pool)
) -> OkResponse:
    try:
        auth.definir_senha_com_convite(_exigir_pool(pool), body.usuario, body.codigo_convite, body.senha)
    except auth.ErroAutenticacao as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return OkResponse()


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    pool: ConnectionPool | None = Depends(obter_db_pool),
    settings: Settings = Depends(obter_settings),
) -> LoginResponse:
    pool = _exigir_pool(pool)
    try:
        usuario = auth.autenticar(pool, body.usuario, body.senha)
    except auth.ContaBloqueada as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except auth.ErroAutenticacao as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    token, expira_em = auth.criar_sessao(pool, usuario.id, settings.auth_sessao_horas)
    return LoginResponse(
        token=token,
        expira_em=expira_em,
        usuario=UsuarioResponse(usuario=usuario.usuario, nome=usuario.nome),
    )


@router.get("/eu", response_model=UsuarioResponse)
async def eu(usuario: UsuarioAutenticado | None = Depends(obter_usuario_opcional)) -> UsuarioResponse:
    if usuario is None:
        raise HTTPException(status_code=401, detail="Sessão ausente ou expirada. Entre novamente.")
    return UsuarioResponse(usuario=usuario.usuario, nome=usuario.nome)


@router.post("/sair", response_model=OkResponse)
async def sair(
    credenciais: HTTPAuthorizationCredentials | None = Depends(esquema_bearer),
    pool: ConnectionPool | None = Depends(obter_db_pool),
) -> OkResponse:
    if credenciais is not None and pool is not None:
        auth.encerrar_sessao(pool, credenciais.credentials)
    return OkResponse()

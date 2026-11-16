"""Autenticação (docs/processos/autenticacao.md): hash de senha, regra de
quem exige sessão em cada modo de AUTH_EXIGIR e usuario_id no log.

Nada aqui conecta ao PostgreSQL. O fluxo completo contra o banco real
(convite, login, bloqueio) continua coberto só pelo teste manual descrito em
autenticacao.md.
"""

import pytest
from fastapi import HTTPException

from backend.config import Settings
from backend.dependencies import exigir_usuario_para
from backend.services import auth
from backend.services.auth import UsuarioAutenticado
from tests.test_logging_interacoes import PoolFalso, _registrar, _valores

POOL_PRESENTE = object()  # a dependência só verifica se o pool é None


# --- senha --------------------------------------------------------------------


def test_hash_confere_so_com_a_senha_certa():
    guardado = auth.gerar_hash_senha("senha-longa-123")
    assert guardado.startswith("scrypt$")
    assert "senha-longa-123" not in guardado
    assert auth.verificar_senha("senha-longa-123", guardado)
    assert not auth.verificar_senha("senha-longa-124", guardado)


def test_hash_usa_sal_diferente_a_cada_vez():
    assert auth.gerar_hash_senha("mesma-senha-123") != auth.gerar_hash_senha("mesma-senha-123")


@pytest.mark.parametrize("guardado", ["", "texto", "bcrypt$1$2$3$a$b", "scrypt$x$8$1$AA==$AA=="])
def test_hash_malformado_nao_confere(guardado):
    assert not auth.verificar_senha("qualquer-coisa", guardado)


def test_senha_nova_curta_e_recusada():
    with pytest.raises(auth.ErroAutenticacao):
        auth.validar_senha_nova("curta")
    auth.validar_senha_nova("x" * auth.TAMANHO_MINIMO_SENHA)


def test_usuario_normalizado():
    assert auth.normalizar_usuario("  Nome.Sobrenome ") == "nome.sobrenome"


# --- quem exige sessão ---------------------------------------------------------


def _checar(modo: str, escopo: str, usuario=None, pool=POOL_PRESENTE):
    dependencia = exigir_usuario_para(escopo)
    return dependencia(usuario=usuario, pool=pool, settings=Settings(auth_exigir=modo))


@pytest.mark.parametrize("modo,escopo", [
    ("nada", "consulta"), ("nada", "feedback"), ("feedback", "consulta"),
])
def test_sem_sessao_liberado(modo, escopo):
    assert _checar(modo, escopo) is None


@pytest.mark.parametrize("modo,escopo", [
    ("tudo", "consulta"), ("tudo", "feedback"), ("feedback", "feedback"),
])
def test_sem_sessao_bloqueado_com_401(modo, escopo):
    with pytest.raises(HTTPException) as erro:
        _checar(modo, escopo)
    assert erro.value.status_code == 401


def test_sem_banco_responde_503_em_vez_de_liberar():
    with pytest.raises(HTTPException) as erro:
        _checar("tudo", "consulta", pool=None)
    assert erro.value.status_code == 503


def test_com_sessao_devolve_o_usuario():
    usuario = UsuarioAutenticado(id=3, usuario="nome.sobrenome", nome="Nome Sobrenome")
    assert _checar("tudo", "consulta", usuario=usuario) is usuario


# --- usuario_id no log ------------------------------------------------------------


def test_log_grava_usuario_id_junto_com_as_colunas_novas():
    pool = PoolFalso()
    _registrar(pool, tipo_saida="gerada", llm_seed=42, usuario_id=3)
    valores = _valores(pool)  # também confere colunas × parâmetros
    assert valores["usuario_id"] == 3
    assert valores["tipo_saida"] == "gerada"
    assert valores["llm_seed"] == 42


def test_log_anonimo_grava_usuario_id_nulo():
    pool = PoolFalso()
    _registrar(pool)
    assert _valores(pool)["usuario_id"] is None


# --- limite global de falhas ---------------------------------------------------


def test_limite_de_falhas_abre_de_novo_quando_a_janela_passa():
    agora = [0.0]
    limite = auth.LimiteDeFalhas(maximo=3, janela_segundos=60, relogio=lambda: agora[0])
    for _ in range(3):
        assert not limite.excedido()
        limite.registrar_falha()
    assert limite.excedido()
    agora[0] = 59.0
    assert limite.excedido()
    agora[0] = 60.0
    assert not limite.excedido()


def test_login_para_de_calcular_hash_depois_de_muitas_falhas(monkeypatch):
    import asyncio

    from backend.routers import auth as rotas
    from backend.schemas import LoginRequest

    chamadas = []

    def autenticar_falso(pool, usuario, senha):
        chamadas.append(usuario)
        raise auth.ErroAutenticacao("Usuário ou senha inválidos.")

    monkeypatch.setattr(rotas.auth, "autenticar", autenticar_falso)
    monkeypatch.setattr(rotas, "limite_falhas", auth.LimiteDeFalhas(maximo=2, janela_segundos=60))

    def tentar():
        corpo = LoginRequest(usuario="ninguem", senha="senha-errada-123")
        return asyncio.run(rotas.login(corpo, pool=POOL_PRESENTE, settings=Settings()))

    for _ in range(2):
        with pytest.raises(HTTPException) as exc:
            tentar()
        assert exc.value.status_code == 401
    with pytest.raises(HTTPException) as exc:
        tentar()
    assert exc.value.status_code == 429
    assert len(chamadas) == 2  # a terceira nem chegou à verificação de senha


def test_fonte_desconhecida_nao_vira_html():
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "interface"))
    import tema

    assert "<script>" not in tema.chip_fonte("<script>alert(1)</script>")

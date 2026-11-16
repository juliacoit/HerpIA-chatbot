"""Autenticação de usuários: contas locais por convite, senha com hash e
sessão por token.

Modelo de acesso (ver docs/processos/autenticacao.md):

- Não há autocadastro. A administração cria a conta
  (scripts/infra/gerenciar_usuarios.py), que nasce sem senha e com um
  código de convite de uso único; a pessoa define a própria senha no
  primeiro acesso. Senha esquecida = novo convite, pelo mesmo script.
- Senha: nunca gravada em claro. Hash scrypt (hashlib, sem dependência
  nova) com sal aleatório por usuário; os parâmetros vão junto no texto do
  hash, para poderem subir depois sem invalidar as senhas antigas.
- Sessão: token aleatório devolvido uma vez no login. O banco guarda só o
  SHA-256 dele — quem ler a tabela `sessoes` não consegue se passar por
  ninguém. O mesmo vale para o código de convite.
- Falhas de login: mensagem única para usuário inexistente, conta
  inativa e senha errada (não revela quais usuários existem), e bloqueio
  temporário depois de tentativas seguidas.

As funções recebem o pool do PostgreSQL já aberto (backend/db.py). Sem
PostgreSQL não há autenticação possível — quem chama trata o pool None.
"""

import base64
import hashlib
import hmac
import secrets
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from psycopg_pool import ConnectionPool

TAMANHO_MINIMO_SENHA = 10
TENTATIVAS_ATE_BLOQUEIO = 5
MINUTOS_BLOQUEIO = 15
# Limite global (todas as contas somadas) de falhas de login e de convite.
# O bloqueio acima é por conta e não cobre tentativas com usuários que não
# existem, que também custam um scrypt cada; com a interface publicada na
# internet, isso seria um jeito barato de ocupar a CPU.
FALHAS_GLOBAIS_MAXIMO = 20
FALHAS_GLOBAIS_JANELA_SEGUNDOS = 60

# Parâmetros do scrypt (custo de CPU/memória por tentativa de senha). n=2**15
# com r=8 usa ~32 MB por verificação; por isso o maxmem explícito, acima do
# limite padrão do OpenSSL.
_SCRYPT_N = 2**15
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_MAXMEM = 64 * 1024 * 1024
_TAMANHO_SAL = 16
_TAMANHO_HASH = 32


class LimiteDeFalhas:
    """Janela deslizante em memória: vale para um processo do backend (o
    HerpIA roda com um só) e zera quando ele reinicia."""

    def __init__(self, maximo: int, janela_segundos: float, relogio=time.monotonic):
        self.maximo = maximo
        self.janela_segundos = janela_segundos
        self._relogio = relogio
        self._falhas: deque[float] = deque()

    def excedido(self) -> bool:
        limite = self._relogio() - self.janela_segundos
        while self._falhas and self._falhas[0] <= limite:
            self._falhas.popleft()
        return len(self._falhas) >= self.maximo

    def registrar_falha(self) -> None:
        self._falhas.append(self._relogio())


class ErroAutenticacao(Exception):
    """Falha esperada de autenticação, com mensagem pronta para o usuário."""


class ContaBloqueada(ErroAutenticacao):
    pass


@dataclass
class UsuarioAutenticado:
    id: int
    usuario: str
    nome: str


def normalizar_usuario(usuario: str) -> str:
    return usuario.strip().lower()


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _b64(dados: bytes) -> str:
    return base64.b64encode(dados).decode("ascii")


def _scrypt(senha: str, sal: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(
        senha.encode("utf-8"), salt=sal, n=n, r=r, p=p, maxmem=_SCRYPT_MAXMEM, dklen=_TAMANHO_HASH
    )


def gerar_hash_senha(senha: str) -> str:
    sal = secrets.token_bytes(_TAMANHO_SAL)
    derivado = _scrypt(senha, sal, _SCRYPT_N, _SCRYPT_R, _SCRYPT_P)
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${_b64(sal)}${_b64(derivado)}"


def verificar_senha(senha: str, hash_guardado: str) -> bool:
    try:
        algoritmo, n, r, p, sal_b64, derivado_b64 = hash_guardado.split("$")
        if algoritmo != "scrypt":
            return False
        sal = base64.b64decode(sal_b64)
        esperado = base64.b64decode(derivado_b64)
        calculado = _scrypt(senha, sal, int(n), int(r), int(p))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(calculado, esperado)


# Hash de uma senha qualquer, calculado uma vez: usado para gastar o mesmo
# tempo de verificação quando o usuário não existe ou não tem senha, para o
# tempo de resposta não revelar quais usuários existem.
_HASH_DESCARTAVEL = gerar_hash_senha(secrets.token_urlsafe(16))


def validar_senha_nova(senha: str) -> None:
    if len(senha) < TAMANHO_MINIMO_SENHA:
        raise ErroAutenticacao(f"A senha precisa ter pelo menos {TAMANHO_MINIMO_SENHA} caracteres.")


def _hash_token(token: str) -> str:
    """SHA-256 de um token aleatório de alta entropia (sessão ou convite).
    Diferente de senha, não precisa de scrypt: o token não é adivinhável."""
    return hashlib.sha256(token.encode("ascii", "ignore")).hexdigest()


def gerar_codigo_convite() -> str:
    return secrets.token_urlsafe(12)


# ---------------------------------------------------------------------------
# Contas (usadas por scripts/infra/gerenciar_usuarios.py)
# ---------------------------------------------------------------------------


def criar_usuario(pool: ConnectionPool, usuario: str, nome: str, validade_convite_dias: int) -> str:
    """Cria a conta sem senha e devolve o código de convite (mostrado uma
    única vez). Levanta ErroAutenticacao se o usuário já existir."""
    usuario = normalizar_usuario(usuario)
    if not usuario or not nome.strip():
        raise ErroAutenticacao("Usuário e nome são obrigatórios.")
    codigo = gerar_codigo_convite()
    with pool.connection() as conn:
        if conn.execute("SELECT 1 FROM usuarios WHERE usuario = %s", (usuario,)).fetchone():
            raise ErroAutenticacao(f"Já existe uma conta para '{usuario}'.")
        conn.execute(
            """
            INSERT INTO usuarios (usuario, nome, convite_hash, convite_expira_em)
            VALUES (%s, %s, %s, %s)
            """,
            (usuario, nome.strip(), _hash_token(codigo), _agora() + timedelta(days=validade_convite_dias)),
        )
        conn.commit()
    return codigo


def gerar_novo_convite(pool: ConnectionPool, usuario: str, validade_convite_dias: int) -> str:
    """Redefinição de senha: apaga a senha atual, encerra as sessões abertas
    e devolve um novo código de convite."""
    usuario = normalizar_usuario(usuario)
    codigo = gerar_codigo_convite()
    with pool.connection() as conn:
        linha = conn.execute(
            """
            UPDATE usuarios
               SET senha_hash = NULL, convite_hash = %s, convite_expira_em = %s,
                   tentativas_falhas = 0, bloqueado_ate = NULL
             WHERE usuario = %s
         RETURNING id
            """,
            (_hash_token(codigo), _agora() + timedelta(days=validade_convite_dias), usuario),
        ).fetchone()
        if linha is None:
            raise ErroAutenticacao(f"Não existe conta para '{usuario}'.")
        conn.execute("DELETE FROM sessoes WHERE usuario_id = %s", (linha[0],))
        conn.commit()
    return codigo


def definir_ativo(pool: ConnectionPool, usuario: str, ativo: bool) -> None:
    usuario = normalizar_usuario(usuario)
    with pool.connection() as conn:
        linha = conn.execute(
            "UPDATE usuarios SET ativo = %s WHERE usuario = %s RETURNING id", (ativo, usuario)
        ).fetchone()
        if linha is None:
            raise ErroAutenticacao(f"Não existe conta para '{usuario}'.")
        if not ativo:
            conn.execute("DELETE FROM sessoes WHERE usuario_id = %s", (linha[0],))
        conn.commit()


def listar_usuarios(pool: ConnectionPool) -> list[dict]:
    with pool.connection() as conn:
        linhas = conn.execute(
            """
            SELECT usuario, nome, ativo, senha_hash IS NOT NULL, convite_expira_em, ultimo_login_em
              FROM usuarios ORDER BY usuario
            """
        ).fetchall()
    return [
        {
            "usuario": u,
            "nome": nome,
            "ativo": ativo,
            "senha_definida": tem_senha,
            "convite_expira_em": convite_expira_em,
            "ultimo_login_em": ultimo_login_em,
        }
        for u, nome, ativo, tem_senha, convite_expira_em, ultimo_login_em in linhas
    ]


# ---------------------------------------------------------------------------
# Primeiro acesso, login e sessão (usados por backend/routers/auth.py)
# ---------------------------------------------------------------------------

_MENSAGEM_CONVITE_INVALIDO = (
    "Usuário ou código de convite inválido, ou convite expirado. "
    "Solicite um novo código à administração do HerpIA."
)
_MENSAGEM_LOGIN_INVALIDO = "Usuário ou senha inválidos."


def definir_senha_com_convite(pool: ConnectionPool, usuario: str, codigo: str, senha: str) -> None:
    """Primeiro acesso (ou redefinição): troca o código de convite pela
    senha escolhida. O convite é de uso único."""
    validar_senha_nova(senha)
    usuario = normalizar_usuario(usuario)
    with pool.connection() as conn:
        linha = conn.execute(
            "SELECT id, convite_hash, convite_expira_em, ativo FROM usuarios WHERE usuario = %s",
            (usuario,),
        ).fetchone()
        valido = (
            linha is not None
            and linha[3]
            and linha[1] is not None
            and linha[2] is not None
            and linha[2] > _agora()
            and hmac.compare_digest(linha[1], _hash_token(codigo.strip()))
        )
        if not valido:
            raise ErroAutenticacao(_MENSAGEM_CONVITE_INVALIDO)
        conn.execute(
            """
            UPDATE usuarios
               SET senha_hash = %s, convite_hash = NULL, convite_expira_em = NULL,
                   tentativas_falhas = 0, bloqueado_ate = NULL
             WHERE id = %s
            """,
            (gerar_hash_senha(senha), linha[0]),
        )
        conn.commit()


def autenticar(pool: ConnectionPool, usuario: str, senha: str) -> UsuarioAutenticado:
    """Confere usuário e senha. Levanta ErroAutenticacao (mensagem única) ou
    ContaBloqueada."""
    usuario = normalizar_usuario(usuario)
    with pool.connection() as conn:
        linha = conn.execute(
            """
            SELECT id, nome, senha_hash, ativo, bloqueado_ate
              FROM usuarios WHERE usuario = %s
            """,
            (usuario,),
        ).fetchone()

        if linha is None or not linha[3] or linha[2] is None:
            verificar_senha(senha, _HASH_DESCARTAVEL)
            raise ErroAutenticacao(_MENSAGEM_LOGIN_INVALIDO)

        usuario_id, nome, senha_hash, _, bloqueado_ate = linha
        if bloqueado_ate is not None and bloqueado_ate > _agora():
            raise ContaBloqueada(
                f"Acesso bloqueado temporariamente após {TENTATIVAS_ATE_BLOQUEIO} tentativas "
                f"sem sucesso. Aguarde {MINUTOS_BLOQUEIO} minutos e tente de novo."
            )

        if not verificar_senha(senha, senha_hash):
            conn.execute(
                """
                UPDATE usuarios
                   SET tentativas_falhas = CASE WHEN tentativas_falhas + 1 >= %s THEN 0
                                                ELSE tentativas_falhas + 1 END,
                       bloqueado_ate = CASE WHEN tentativas_falhas + 1 >= %s THEN %s
                                            ELSE bloqueado_ate END
                 WHERE id = %s
                """,
                (
                    TENTATIVAS_ATE_BLOQUEIO,
                    TENTATIVAS_ATE_BLOQUEIO,
                    _agora() + timedelta(minutes=MINUTOS_BLOQUEIO),
                    usuario_id,
                ),
            )
            conn.commit()
            raise ErroAutenticacao(_MENSAGEM_LOGIN_INVALIDO)

        conn.execute(
            """
            UPDATE usuarios SET tentativas_falhas = 0, bloqueado_ate = NULL, ultimo_login_em = %s
             WHERE id = %s
            """,
            (_agora(), usuario_id),
        )
        conn.commit()
    return UsuarioAutenticado(id=usuario_id, usuario=usuario, nome=nome)


def criar_sessao(pool: ConnectionPool, usuario_id: int, duracao_horas: int) -> tuple[str, datetime]:
    """Devolve (token, expira_em). O token só existe em claro nesta resposta."""
    token = secrets.token_urlsafe(32)
    expira_em = _agora() + timedelta(hours=duracao_horas)
    with pool.connection() as conn:
        conn.execute("DELETE FROM sessoes WHERE expira_em < %s", (_agora(),))
        conn.execute(
            "INSERT INTO sessoes (token_hash, usuario_id, expira_em) VALUES (%s, %s, %s)",
            (_hash_token(token), usuario_id, expira_em),
        )
        conn.commit()
    return token, expira_em


def obter_usuario_da_sessao(pool: ConnectionPool, token: str) -> UsuarioAutenticado | None:
    with pool.connection() as conn:
        linha = conn.execute(
            """
            SELECT u.id, u.usuario, u.nome
              FROM sessoes s JOIN usuarios u ON u.id = s.usuario_id
             WHERE s.token_hash = %s AND s.expira_em > %s AND u.ativo
            """,
            (_hash_token(token), _agora()),
        ).fetchone()
    if linha is None:
        return None
    return UsuarioAutenticado(id=linha[0], usuario=linha[1], nome=linha[2])


def encerrar_sessao(pool: ConnectionPool, token: str) -> None:
    with pool.connection() as conn:
        conn.execute("DELETE FROM sessoes WHERE token_hash = %s", (_hash_token(token),))
        conn.commit()

"""Feedback com motivos e comentário: validação do pedido, uma avaliação por
usuário logado (reenviar substitui) e rótulos da interface.

Nada aqui conecta ao PostgreSQL: o pool é falso, guarda o SQL recebido e
responde aos SELECTs com o que o teste definir.
"""

import sys
from contextlib import contextmanager
from pathlib import Path
from typing import get_args

import pytest
from pydantic import ValidationError

from backend.schemas import FeedbackRequest, MotivoFeedback
from backend.services.logging_db import registrar_feedback

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "interface"))
import apresentacao  # noqa: E402


class _Cursor:
    def __init__(self, linha):
        self._linha = linha

    def fetchone(self):
        return self._linha


class PoolFalso:
    """`dono_interacao`: linha devolvida pelo SELECT em interacoes (None =
    interação inexistente). `feedback_anterior`: linha do SELECT em feedback."""

    def __init__(self, dono_interacao, feedback_anterior=None):
        self._dono = dono_interacao
        self._anterior = feedback_anterior
        self.gravado = []

    def execute(self, sql, params=None):
        self.gravado.append((sql, params))
        if "FROM interacoes" in sql:
            return _Cursor(self._dono)
        if "FROM feedback" in sql:
            return _Cursor(self._anterior)
        return _Cursor(None)

    def commit(self):
        pass

    @contextmanager
    def connection(self):
        yield self

    def escritas(self):
        return [(sql, p) for sql, p in self.gravado if sql.startswith(("INSERT", "UPDATE"))]


def test_motivos_so_no_feedback_negativo():
    ok = FeedbackRequest(interacao_id=1, avaliacao=-1, motivos=["fonte_errada", "incompleta"])
    assert ok.motivos == ["fonte_errada", "incompleta"]
    with pytest.raises(ValidationError, match="motivos"):
        FeedbackRequest(interacao_id=1, avaliacao=1, motivos=["incompleta"])
    with pytest.raises(ValidationError):
        FeedbackRequest(interacao_id=1, avaliacao=-1, motivos=["motivo_inventado"])


def test_positivo_com_comentario_e_aceito():
    pedido = FeedbackRequest(interacao_id=1, avaliacao=1, comentario="Citou a ficha certa.")
    assert pedido.motivos is None


def test_rotulos_da_interface_cobrem_os_codigos_do_backend():
    assert list(apresentacao.MOTIVOS_FEEDBACK) == list(get_args(MotivoFeedback))


def test_primeiro_feedback_do_usuario_insere_com_motivos():
    pool = PoolFalso(dono_interacao=(3,))
    assert registrar_feedback(
        pool, interacao_id=10, avaliacao=-1, comentario="Faltou o PAN.",
        usuario_id=3, motivos=["incompleta", "fonte_errada", "incompleta"],
    )
    [(sql, params)] = pool.escritas()
    assert sql.startswith("INSERT INTO feedback")
    assert params == (10, -1, "Faltou o PAN.", 3, ["fonte_errada", "incompleta"])


def test_reenvio_do_mesmo_usuario_substitui_a_avaliacao():
    pool = PoolFalso(dono_interacao=(3,), feedback_anterior=(55,))
    assert registrar_feedback(pool, interacao_id=10, avaliacao=1, comentario="Boa.", usuario_id=3)
    [(sql, params)] = pool.escritas()
    assert sql.startswith("UPDATE feedback")
    assert params == (1, "Boa.", None, 55)


def test_anonimo_sempre_insere_sem_consultar_feedback_anterior():
    pool = PoolFalso(dono_interacao=(None,), feedback_anterior=(55,))
    assert registrar_feedback(pool, interacao_id=10, avaliacao=1, comentario=None)
    [(sql, _)] = pool.escritas()
    assert sql.startswith("INSERT INTO feedback")
    assert not any("FROM feedback" in s for s, _ in pool.gravado)


@pytest.mark.parametrize("dono", [None, (4,)])
def test_interacao_inexistente_ou_de_outro_usuario_nao_grava(dono):
    pool = PoolFalso(dono_interacao=dono)
    assert not registrar_feedback(pool, interacao_id=10, avaliacao=-1, comentario=None, usuario_id=3)
    assert pool.escritas() == []


@pytest.mark.parametrize(
    ("avaliacao", "comentario", "esperado"),
    [
        (1, None, "Feedback enviado: positivo. Obrigado!"),
        (-1, "Fonte errada.", "Feedback enviado: negativo, com comentário. Obrigado!"),
    ],
)
def test_resumo_do_feedback_enviado(avaliacao, comentario, esperado):
    assert apresentacao.resumo_feedback(avaliacao, comentario) == esperado

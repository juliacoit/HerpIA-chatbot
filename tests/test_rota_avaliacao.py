"""Checagens determinísticas de rota (avaliacao/rota.py)."""

import json

import pytest

from avaliacao.casos import carregar_casos
from avaliacao.rota import checar_rota

PERGUNTA_GATE = "Quais espécies de anuros existem no Pantanal?"      # dispara o gate (C2)
PERGUNTA_SEM_GATE = "Quem coordena o PAN Tartarugas Marinhas?"      # não dispara (D2)


def _caso(pergunta, rota=None, fonte=None, falha=None):
    return {"user_input": pergunta, "rota_esperada": rota, "fonte_esperada": fonte, "falha_conhecida": falha}


def test_decisao_ok_e_divergente():
    assert checar_rota(_caso(PERGUNTA_GATE, rota="salve"), []).decisao == "ok"
    assert checar_rota(_caso(PERGUNTA_SEM_GATE, rota="nenhuma"), []).decisao == "ok"
    assert checar_rota(_caso(PERGUNTA_GATE, rota="nenhuma"), []).decisao == "divergente"
    assert checar_rota(_caso(PERGUNTA_SEM_GATE, rota="salve"), []).decisao == "divergente"


def test_rota_omitida_e_indiferente():
    r = checar_rota(_caso(PERGUNTA_GATE), ["salve"])
    assert r.decisao == "nao_checada"
    assert r.efeito == "nao_checada"
    assert r.status == "nao_checada"


def test_efeito_estrito_com_rota_salve():
    caso = _caso(PERGUNTA_GATE, rota="salve", fonte="salve")
    assert checar_rota(caso, ["salve", "pans"]).efeito == "ok"
    # SALVE presente, mas não em primeiro: falha no modo estrito.
    assert checar_rota(caso, ["pans", "salve"]).efeito == "divergente"
    assert checar_rota(caso, []).efeito == "divergente"


def test_efeito_frouxo_sem_rota_salve():
    caso = _caso(PERGUNTA_SEM_GATE, rota="nenhuma", fonte="pans")
    r = checar_rota(caso, ["salve", "salve", "pans", "monitora"])
    assert r.efeito == "ok"  # basta aparecer no top-k
    assert r.fracao_fonte_esperada == pytest.approx(0.25)
    r = checar_rota(caso, ["salve", "monitora"])
    assert r.efeito == "divergente"
    assert r.fracao_fonte_esperada == 0.0


def test_falha_conhecida_vira_status_proprio_e_avisa_quando_passa():
    falhando = checar_rota(_caso(PERGUNTA_GATE, rota="nenhuma", fonte="pans", falha="gate dispara"), ["salve"])
    assert falhando.decisao == "falha_conhecida"
    assert falhando.efeito == "falha_conhecida"
    assert falhando.status == "falha_conhecida"
    assert not falhando.falha_conhecida_passou

    passando = checar_rota(_caso(PERGUNTA_SEM_GATE, rota="nenhuma", fonte="pans", falha="gate dispara"), ["pans"])
    assert passando.status == "ok"
    assert passando.falha_conhecida_passou


def test_divergente_prevalece_no_status():
    r = checar_rota(_caso(PERGUNTA_GATE, rota="salve", fonte="pans"), ["salve"])
    assert r.decisao == "ok"
    assert r.efeito == "divergente"
    assert r.status == "divergente"


def test_decisao_da_bateria_atual():
    # Estado de 2026-10-19: só D4, L2 e L8 divergem, todos marcados como falha
    # conhecida (falso positivo do gate com nome de PAN na pergunta).
    resultados = {c["id"]: checar_rota(c, []) for c in carregar_casos() if c["rota_esperada"]}
    divergentes = {i for i, r in resultados.items() if r.decisao == "divergente"}
    assert divergentes == set()
    conhecidas = {i for i, r in resultados.items() if r.decisao == "falha_conhecida"}
    assert conhecidas == {"D4", "L2", "L8"}
    assert resultados["A2"].rota_obtida == "nenhuma"
    assert resultados["A2"].rota_obtida == "nenhuma"


@pytest.mark.parametrize(
    "linha, mensagem",
    [
        ({"id": "A1", "reference": "PENDENTE_VALIDACAO_RAN", "rota_esperada": "pans"}, "rota_esperada"),
        ({"id": "A1", "reference": "PENDENTE_VALIDACAO_RAN", "falha_conhecida": " "}, "falha_conhecida"),
    ],
)
def test_campos_novos_invalidos(tmp_path, linha, mensagem):
    arquivo = tmp_path / "casos.jsonl"
    arquivo.write_text(json.dumps(linha) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match=mensagem):
        carregar_casos(arquivo)

"""Padrões de dado sensível: o que a redação automática remove e o que só é
sinalizado. Coordenadas deixaram de ser removidas com o ADR 0009."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "classificacao"))

from regras_pii import FLAGS, FLAGS_REDIGIVEIS, redigir_texto  # noqa: E402

COORDENADA_DECIMAL = "-24.4833, -46.6750"
COORDENADA_DMS = "24°29'15\"S"


def chaves(flags) -> set[str]:
    return {flag[0] for flag in flags}


def test_coordenadas_nao_sao_redigidas():
    texto = f"Registro em {COORDENADA_DECIMAL} e em {COORDENADA_DMS}, na ilha."
    redigido, contagens = redigir_texto(texto)
    assert redigido == texto
    assert contagens == {}


def test_padroes_de_coordenada_continuam_na_lista_para_a_triagem():
    por_chave = {flag[0]: flag for flag in FLAGS}
    assert por_chave["coordenada_decimal"][1].search(COORDENADA_DECIMAL)
    assert por_chave["coordenada_dms"][1].search(COORDENADA_DMS)
    assert not chaves(FLAGS_REDIGIVEIS) & {"coordenada_decimal", "coordenada_dms"}


def test_dados_pessoais_continuam_redigidos():
    texto = "CPF 123.456.789-09, contato fulano@exemplo.org, telefone (62) 99999-0000."
    redigido, contagens = redigir_texto(texto)
    assert "123.456.789-09" not in redigido
    assert "fulano@exemplo.org" not in redigido
    assert "99999-0000" not in redigido
    assert contagens == {"cpf": 1, "email": 1, "telefone": 1}
    assert chaves(FLAGS_REDIGIVEIS) == {"cpf", "email", "telefone"}


def test_dado_pessoal_e_removido_e_coordenada_fica_no_mesmo_texto():
    texto = f"Coletor: fulano@exemplo.org. Ponto: {COORDENADA_DECIMAL}."
    redigido, contagens = redigir_texto(texto)
    assert redigido == f"Coletor: [e-mail removido]. Ponto: {COORDENADA_DECIMAL}."
    assert contagens == {"email": 1}

"""avaliacao/casos.jsonl em sincronia com a bateria de domínio."""

import json

import pytest

from avaliacao.casos import REFERENCIA_PENDENTE, carregar_casos
from teste_perguntas_dominio import CASOS_TESTE


def test_casos_jsonl_cobre_a_bateria_inteira():
    casos = carregar_casos()
    assert [c["id"] for c in casos] == [c["id"] for c in CASOS_TESTE]


def test_pergunta_vem_da_bateria():
    bateria = {c["id"]: c["pergunta"] for c in CASOS_TESTE}
    for caso in carregar_casos():
        assert caso["user_input"] == bateria[caso["id"]]
        assert caso["categoria"] == caso["id"][0]


def test_nenhum_gabarito_escrito_fora_do_ran():
    # Gabaritos só entram quando a equipe técnica do RAN validar; até lá,
    # todos ficam pendentes. Quando entrarem, este teste deve ser revisto.
    assert all(c["reference"] == REFERENCIA_PENDENTE for c in carregar_casos())
    assert not any(c["tem_referencia"] for c in carregar_casos())


@pytest.mark.parametrize(
    "linha, mensagem",
    [
        ({"id": "Z9", "reference": REFERENCIA_PENDENTE}, "não existe"),
        ({"id": "A1", "reference": ""}, "reference vazio"),
        ({"id": "A1", "reference": REFERENCIA_PENDENTE, "fonte_esperada": "sei"}, "fonte_esperada"),
        ({"id": "A1", "reference": REFERENCIA_PENDENTE, "top_k": 50}, "top_k"),
        ({"id": "A1", "reference": REFERENCIA_PENDENTE, "user_input": "duplicada"}, "campos desconhecidos"),
    ],
)
def test_linha_invalida_e_rejeitada(tmp_path, linha, mensagem):
    arquivo = tmp_path / "casos.jsonl"
    arquivo.write_text(json.dumps(linha) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match=mensagem):
        carregar_casos(arquivo)


def test_id_repetido_e_rejeitado(tmp_path):
    arquivo = tmp_path / "casos.jsonl"
    linha = json.dumps({"id": "A1", "reference": REFERENCIA_PENDENTE})
    arquivo.write_text(linha + "\n" + linha + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="repetido"):
        carregar_casos(arquivo)

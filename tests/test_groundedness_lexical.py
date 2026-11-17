"""Testes da camada 1 (verificação lexical) de backend/services/groundedness.py:
nomes em posição estrutural de alta precisão sem apoio nos trechos."""

import pytest

from backend.schemas import ChunkRecuperado
from backend.services.groundedness import checar_ancoras_estruturais

# Resumo do trecho real do SALVE recuperado na interação 1415 (2026-11-17).
_TRECHO_SALVE = (
    "Espécie: Acanthochelys radiolata (Mikan, 1820)\n"
    "Categoria de risco: Menos Preocupante (LC)\n"
    "Justificativa da avaliação: Acanthochelys radiolata é endêmica do "
    "Brasil, ocorre no bioma Mata Atlântica. Todavia, não há indícios de que "
    "estas ameaças possam afetar a espécie ao ponto de colocá-la em risco de "
    "extinção. Ocorre em várias unidades de conservação, inclusive de "
    "proteção integral. Assim, Acanthochelys radiolata foi avaliada como "
    "Menos Preocupante (LC)."
)


@pytest.fixture
def chunks() -> list[ChunkRecuperado]:
    return [
        ChunkRecuperado(
            score=0.56, fonte="salve",
            documento="Acanthochelys radiolata (Mikan, 1820)",
            secao="visao_geral", texto=_TRECHO_SALVE,
            nivel_sensibilidade="autorizado",
        )
    ]


@pytest.mark.parametrize("inicio_item", [
    "Não houve evidências suficientes de ameaças significativas.",
    "Não há indícios de ameaças que coloquem a espécie em risco.",
    "Havia registros em unidades de conservação.",
])
def test_negacao_e_haver_liderando_item_nao_sao_entidade(chunks, inicio_item):
    resposta = (
        "A espécie foi avaliada como Menos Preocupante (LC):\n\n"
        "1. Ocorre em várias unidades de conservação.\n\n"
        f"2. {inicio_item}"
    )
    ancorada, sem_apoio = checar_ancoras_estruturais(resposta, chunks, "pergunta")
    assert ancorada, sem_apoio


def test_nome_inventado_liderando_item_continua_barrado(chunks):
    resposta = (
        "Espécies associadas:\n\n"
        "1. Leptotrombidium akarai - transmite doença à espécie."
    )
    ancorada, sem_apoio = checar_ancoras_estruturais(resposta, chunks, "pergunta")
    assert not ancorada
    assert sem_apoio == ["Leptotrombidium akarai"]


def test_nome_inventado_com_parenteses_continua_barrado(chunks):
    resposta = "Não houve registro de Acanthochelys inventada (Silva, 2020)."
    ancorada, sem_apoio = checar_ancoras_estruturais(resposta, chunks, "pergunta")
    assert not ancorada
    assert sem_apoio == ["Acanthochelys inventada"]

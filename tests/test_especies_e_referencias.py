"""Roteamento por espécie citada na pergunta (backend/services/especies_salve.py
e roteamento.buscar_chunks_priorizados) e verificação de referências
bibliográficas inventadas (groundedness.checar_referencias_bibliograficas).
Casos de 2026-11-17."""

import asyncio
import json

import pytest

from backend.config import Settings
from backend.schemas import ChunkRecuperado
from backend.services import roteamento
from backend.services.especies_salve import CatalogoEspecies, nomes_da_especie
from backend.services.groundedness import (
    checar_referencias_bibliograficas,
    verificar_groundedness_detalhado,
)
from backend.services.logging_db import descrever_rota
from tests.conftest import LLMFalso

RADIOLATA = "Acanthochelys radiolata (Mikan, 1820)"
SPIXII = "Acanthochelys spixii (Duméril & Bibron, 1835)"


@pytest.fixture
def catalogo():
    return CatalogoEspecies({
        RADIOLATA: "Brazilian radiolated swamp turtle, Cágado-amarelo, Strahlen-Plattschildkröte",
        SPIXII: "Cágado-preto, Black spiny-necked swamp turtle",
        "Caiman latirostris (Daudin, 1802)": "Jacaré-do-papo-amarelo",
        "Rhinella diptycha (Cope, 1862)": "Sapo-cururu, Sapo",
        "Rhinella icterica (Spix, 1824)": "Sapo-cururu",
        "Amphisbaena alba Linnaeus, 1758": "Cobra-de-duas-cabeças",
        "Amphisbaena fuliginosa Linnaeus, 1758": "Cobra-de-duas-cabeças",
        "Leposternon microcephalum Wagler, 1824": "Cobra-de-duas-cabeças",
        "Amphisbaena vermicularis Wagler, 1824": "Cobra-de-duas-cabeças",
    })


# --- catálogo de nomes ----------------------------------------------------


def test_nomes_da_especie():
    assert nomes_da_especie(RADIOLATA, "Cágado-amarelo, Cágado") == ["acanthochelys radiolata", "cagado amarelo"]
    assert nomes_da_especie("Bothrops jararaca", None) == ["bothrops jararaca"]


@pytest.mark.parametrize("pergunta, esperado", [
    ("por que o cágado-amarelo foi classificado como menos preocupante?", [RADIOLATA]),
    ("qual a justificativa para acanthochelys-radiolata-mikan-1820 ser LC?", [RADIOLATA]),
    ("compare Acanthochelys radiolata e o cágado-preto", [RADIOLATA, SPIXII]),
    ("onde ocorre o sapo-cururu?", ["Rhinella diptycha (Cope, 1862)", "Rhinella icterica (Spix, 1824)"]),
    ("quais as ameaças ao sapo?", []),                      # nome de uma palavra só
    ("a cobra-de-duas-cabeças é venenosa?", []),            # mais de 3 fichas
    ("quais anfíbios ocorrem no Cerrado?", []),
])
def test_detectar_especies(catalogo, pergunta, esperado):
    assert catalogo.detectar(pergunta) == esperado


# --- roteamento -----------------------------------------------------------


def _chunk(documento, secao="visao_geral", fonte="salve"):
    return ChunkRecuperado(score=0.5, fonte=fonte, documento=documento, texto=f"{documento} {secao}", secao=secao)


@pytest.fixture
def buscas(monkeypatch):
    chamadas = []

    def buscar_falso(client, modelo, settings, pergunta, top_k, fontes, filtros_metadados=None, excluir_secoes=None):
        chamadas.append({"fontes": fontes, "filtros": filtros_metadados, "excluir": excluir_secoes})
        if filtros_metadados and "documento" in filtros_metadados:
            return [_chunk(filtros_metadados["documento"][0], s) for s in ("visao_geral", "ameacas")]
        return [_chunk("PAN peixe-boi", f"pagina-{i}", "pans") for i in range(top_k)]

    monkeypatch.setattr(roteamento, "buscar_chunks", buscar_falso)
    return chamadas


def test_nome_comum_restringe_a_busca_a_ficha(catalogo, buscas):
    pergunta = "por que o cágado-amarelo foi classificado como menos preocupante?"
    chunks = roteamento.buscar_chunks_priorizados(None, None, Settings(_env_file=None), pergunta, 5, None, catalogo)
    assert buscas[0] == {"fontes": ["salve"], "filtros": {"documento": [RADIOLATA]}, "excluir": ["referencias"]}
    assert [c.documento for c in chunks[:2]] == [RADIOLATA, RADIOLATA]
    assert len(chunks) == 5  # completado com a busca geral
    assert buscas[1]["fontes"] is None


def test_pergunta_que_cita_pan_nao_restringe(catalogo, buscas):
    pergunta = "o cágado-amarelo está em algum PAN?"
    roteamento.buscar_chunks_priorizados(None, None, Settings(_env_file=None), pergunta, 5, None, catalogo)
    assert all(not (c["filtros"] or {}).get("documento") for c in buscas)


def test_fontes_sem_salve_nao_restringe(catalogo, buscas):
    pergunta = "por que o cágado-amarelo foi classificado assim?"
    roteamento.buscar_chunks_priorizados(None, None, Settings(_env_file=None), pergunta, 5, ["pans"], catalogo)
    assert buscas == [{"fontes": ["pans"], "filtros": None, "excluir": ["referencias"]}]


def test_fontes_com_salve_restringe_e_completa_com_as_fontes(catalogo, buscas):
    pergunta = "por que o cágado-amarelo foi classificado assim?"
    roteamento.buscar_chunks_priorizados(
        None, None, Settings(_env_file=None), pergunta, 5, ["salve", "pans"], catalogo
    )
    assert buscas[0]["filtros"] == {"documento": [RADIOLATA]}
    assert buscas[1]["fontes"] == ["salve", "pans"]


def test_sem_catalogo_comportamento_anterior(buscas):
    pergunta = "por que o cágado-amarelo foi classificado assim?"
    roteamento.buscar_chunks_priorizados(None, None, Settings(_env_file=None), pergunta, 5, None, None)
    assert buscas == [{"fontes": None, "filtros": None, "excluir": ["referencias"]}]


@pytest.mark.parametrize("fontes", [None, ["salve"], ["pans"]])
def test_descrever_rota_com_especies(catalogo, buscas, fontes):
    pergunta = "por que o cágado-amarelo foi classificado como menos preocupante?"
    roteamento.buscar_chunks_priorizados(None, None, Settings(_env_file=None), pergunta, 5, fontes, catalogo)
    rota = descrever_rota(pergunta, fontes, catalogo)
    if fontes == ["pans"]:
        assert "especies" not in rota
        assert buscas[0]["fontes"] == ["pans"]
    else:
        assert rota["especies"] == [RADIOLATA]
        assert buscas[0]["fontes"] == [rota["fonte_prioritaria"]]
        assert buscas[0]["filtros"] == rota["filtros"]
        assert rota.get("fontes_do_cliente") == fontes
    json.dumps(rota)


# --- referências bibliográficas -------------------------------------------

# Trechos reais (resumidos) da ficha: a seção Distribuição cita "Bérnils et
# al., 2005" no texto; as Referências vêm quebradas a cada ponto pelo chunker.
TRECHO_DISTRIBUICAO = (
    "Há registros confirmados para Rio de Janeiro (Mikan, 1820; Rhodin et al., 1984; "
    "Bérnils et al ., 2005; Santos et al ., 2008)."
)
TRECHO_REFERENCIAS = (
    "Mikan, J.\n\nC.\n\n(1820) Delectus Florae et Faunae Brasiliensis Wien, Antonii Straus., 54pp.\n\n"
    "Pinto, H.\n\nB.\n\nA., Valadão, R.\n\nM.\n\n(2024) Assessing Brazilian turtles’ vulnerability "
    "by using species distribution models and dispersal constraints.\n\n"
    "Moraes, R.L.\n\n(2008) Sistema de Autorização de Informação em Biodiversidade - SISBIO ."
)
CHUNKS_REF = [
    ChunkRecuperado(score=0.5, fonte="salve", documento=RADIOLATA, texto=t, secao=s)
    for t, s in ((TRECHO_DISTRIBUICAO, "distribuicao"), (TRECHO_REFERENCIAS, "referencias"))
]
REFERENCIA_INVENTADA = (
    "3. Bérnils, A.C., Silva-Soares, F.M., & Moraes, R.L. (2005) Distribuição da fauna de "
    "quelônios no Brasil: uma revisão. Revista Brasileira de Herpetologia, 18(2), 147-163."
)
REFERENCIAS_REAIS = (
    "As seguintes referências tratam da espécie:\n\n"
    "1. Mikan, J.C. (1820) Delectus Florae et Faunae Brasiliensis Wien, Antonii Strauß., 54pp.\n"
    "2. Pinto, H.B.A., Valadão, R.M. (2024) Assessing Brazilian turtles' vulnerability by using "
    "species distribution models.\n"
    "- **Moraes, R.L.** (2008) Sistema de Autorização de Informação em Biodiversidade - SISBIO."
)


def test_referencias_reais_reformatadas_passam():
    ok, sem_apoio = checar_referencias_bibliograficas(REFERENCIAS_REAIS, CHUNKS_REF)
    assert ok, sem_apoio


def test_referencia_inventada_e_barrada():
    ok, sem_apoio = checar_referencias_bibliograficas(REFERENCIAS_REAIS + "\n" + REFERENCIA_INVENTADA, CHUNKS_REF)
    assert not ok
    assert sem_apoio == [REFERENCIA_INVENTADA]


def test_texto_corrido_e_autor_institucional_nao_sao_checados():
    resposta = (
        "A espécie foi avaliada em 2016 como Menos Preocupante (LC).\n"
        "- ICMBio (2018) Livro Vermelho inexistente nos trechos.\n"
        "Segundo Bérnils et al. (2005), a espécie ocorre no Rio de Janeiro."
    )
    assert checar_referencias_bibliograficas(resposta, CHUNKS_REF) == (True, [])


def test_groundedness_retem_referencia_inventada_sem_chamar_juiz():
    llm = LLMFalso([])
    fundamentada, justificativa, origem = asyncio.run(verificar_groundedness_detalhado(
        llm, "quais referências tratam de Acanthochelys radiolata?",
        REFERENCIAS_REAIS + "\n" + REFERENCIA_INVENTADA, CHUNKS_REF,
    ))
    assert (fundamentada, origem) == (False, "lexical")
    assert justificativa.startswith("Verificação lexical de referências bibliográficas")
    assert "Bérnils" in justificativa
    assert llm.prompts == []

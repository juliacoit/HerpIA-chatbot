"""Resposta direta dos campos da ficha SALVE (backend/services/campos_salve.py),
exclusão da seção de referências na busca e defaults de temperatura/seed.

Os textos imitam o formato real dos chunks SALVE (gerar_chunks.py), com o
caso da interação 1415 (2026-11-17)."""

import asyncio

import numpy as np
import pytest

from backend.config import Settings
from backend.schemas import ChunkRecuperado
from backend.services import retrieval
from backend.services.campos_salve import (
    detectar_campo_pedido,
    extrair_historico,
    extrair_justificativa,
    identificar_ficha,
    responder_campo_salve,
)
from backend.services.geracao import gerar_resposta
from backend.services.roteamento import secoes_excluidas
from tests.conftest import LLMFalso

DOC = "Acanthochelys radiolata (Mikan, 1820)"
CABECALHO = (
    f"Espécie: {DOC} (Brazilian radiolated swamp turtle, Cágado-amarelo, Strahlen-Plattschildkröte)\n"
    "Grupo: Répteis\n"
    "Categoria de risco: Menos Preocupante (LC)\n"
    "Bioma: Cerrado, Mata Atlântica\n"
)
JUSTIFICATIVA = (
    "Acanthochelys radiolata é endêmica do Brasil, ocorre no bioma Mata Atlântica. "
    "Todavia, não há indícios de que estas ameaças possam afetar a espécie ao ponto "
    "de colocá-la em risco de extinção. Assim, Acanthochelys radiolata foi avaliada "
    "como Menos Preocupante (LC)."
)
TEXTO_VISAO_GERAL = (
    CABECALHO + "Seção: Visão geral\n\n"
    f"Justificativa da avaliação:\n{JUSTIFICATIVA}\n\n"
    "Autoria: Fulano de Tal\n\nCitação recomendada:\nTal, F. 2026."
)
HISTORICO = (
    "Histórico de avaliação de risco:\n"
    "- Nacional Brasil 2016: Menos Preocupante (LC)\n"
    "- Global 2010: Quase Ameaçada (NT)\n"
    "- Estadual 2007: Dados Insuficientes (DD)\n"
)
TEXTO_CONSERVACAO = (
    CABECALHO + "Seção: Conservação\n\n" + HISTORICO
    + "\nUnidades de conservação com registro:\n- REBIO de Pedra Talhada (Federais)"
)
TEXTO_REFERENCIAS = CABECALHO + "Seção: Referências\n\nMikan, J. C. (1820) Delectus Florae et Faunae Brasiliensis."


def _chunk(texto, secao, documento=DOC, parte=1, n_partes=1, fonte="salve"):
    return ChunkRecuperado(
        score=0.5, fonte=fonte, documento=documento, texto=texto, secao=secao,
        parte=parte, n_partes=n_partes, nivel_sensibilidade="autorizado",
    )


@pytest.fixture
def chunks_1415():
    return [
        _chunk(TEXTO_VISAO_GERAL, "visao_geral"),
        _chunk(TEXTO_CONSERVACAO, "conservacao"),
        _chunk(TEXTO_REFERENCIAS, "referencias"),
    ]


# --- qual campo a pergunta pede -------------------------------------------


@pytest.mark.parametrize("pergunta, campo", [
    ("qual a justificativa de avaliação para acanthochelys-radiolata-mikan-1820 ser classificada como LC?",
     "justificativa"),
    ("Por que Acanthochelys radiolata foi classificada como Menos Preocupante?", "justificativa"),
    ("Qual o motivo da classificação do cágado-amarelo?", "justificativa"),
    ("Qual o histórico de avaliação de risco de Acanthochelys radiolata?", "historico"),
    ("Quais foram as avaliações anteriores do cágado-amarelo?", "historico"),
    ("Quais as ameaças ao cágado-amarelo?", None),
    ("Qual o histórico e a justificativa da avaliação do cágado-amarelo?", None),
])
def test_detectar_campo_pedido(pergunta, campo):
    assert detectar_campo_pedido(pergunta) == campo


# --- qual ficha a pergunta cita -------------------------------------------


@pytest.mark.parametrize("pergunta", [
    "justificativa para acanthochelys-radiolata-mikan-1820 ser LC?",
    "justificativa da avaliação de Acanthochelys radiolata",
    "por que o cágado-amarelo foi classificado assim?",
    "por que o Cagado Amarelo foi classificado assim?",
])
def test_identificar_ficha_por_nome_cientifico_ou_comum(chunks_1415, pergunta):
    assert identificar_ficha(pergunta, chunks_1415) == DOC


def test_identificar_ficha_ambigua_ou_ausente(chunks_1415):
    outra = _chunk(
        "Espécie: Acanthochelys spixii (Duméril & Bibron, 1835) (Cágado-preto)\n", "visao_geral",
        documento="Acanthochelys spixii (Duméril & Bibron, 1835)",
    )
    pergunta = "justificativa de Acanthochelys radiolata e de Acanthochelys spixii"
    assert identificar_ficha(pergunta, chunks_1415 + [outra]) is None
    assert identificar_ficha("justificativa de Bothrops jararaca", chunks_1415) is None


def test_nome_comum_de_uma_palavra_nao_identifica():
    chunk = _chunk(f"Espécie: {DOC} (Cágado)\n", "visao_geral")
    assert identificar_ficha("justificativa do cágado", [chunk]) is None


def test_ficha_de_outra_fonte_nao_conta(chunks_1415):
    pan = _chunk("Espécie: Acanthochelys radiolata ...", None, documento=DOC, fonte="pans")
    assert identificar_ficha("justificativa de Acanthochelys radiolata", [pan]) is None


# --- extração dos campos --------------------------------------------------


def test_extrair_justificativa_ate_autoria():
    assert extrair_justificativa(TEXTO_VISAO_GERAL) == JUSTIFICATIVA


def test_extrair_justificativa_incompleta_devolve_none():
    # Sem Autoria/Citação depois: o texto pode continuar na parte 2 da seção.
    assert extrair_justificativa(CABECALHO + f"Justificativa da avaliação:\n{JUSTIFICATIVA}") is None
    assert extrair_justificativa(TEXTO_CONSERVACAO) is None


def test_extrair_historico_termina_em_linha_em_branco():
    assert extrair_historico(TEXTO_CONSERVACAO) == [
        "Nacional Brasil 2016: Menos Preocupante (LC)",
        "Global 2010: Quase Ameaçada (NT)",
        "Estadual 2007: Dados Insuficientes (DD)",
    ]


def test_extrair_historico_no_fim_do_trecho_so_na_ultima_parte():
    texto = CABECALHO + "Seção: Conservação\n\n" + HISTORICO
    assert extrair_historico(texto, ultima_parte=False) is None
    assert len(extrair_historico(texto, ultima_parte=True)) == 3


# --- resposta completa ----------------------------------------------------


def test_responder_justificativa_caso_1415(chunks_1415):
    pergunta = "qual a justificativa de avaliação para acanthochelys-radiolata-mikan-1820 ser classificada como LC?"
    r = responder_campo_salve(pergunta, chunks_1415)
    assert r.campo == "justificativa"
    assert r.chunk.secao == "visao_geral"
    assert "Menos Preocupante (LC)" in r.texto
    assert f"> {JUSTIFICATIVA}" in r.texto  # transcrita, não reescrita
    assert "Observação" not in r.texto


def test_responder_justificativa_com_categoria_errada_na_pergunta(chunks_1415):
    r = responder_campo_salve("qual a justificativa para Acanthochelys radiolata ser VU?", chunks_1415)
    assert r.texto.startswith(
        "Observação: a pergunta menciona VU, mas a categoria registrada na ficha é Menos Preocupante (LC)."
    )


def test_responder_historico(chunks_1415):
    r = responder_campo_salve("Qual o histórico de avaliação de risco do cágado-amarelo?", chunks_1415)
    assert r.campo == "historico"
    assert r.chunk.secao == "conservacao"
    assert "- Estadual 2007: Dados Insuficientes (DD)" in r.texto
    assert "Categoria atual registrada na ficha: Menos Preocupante (LC)." in r.texto


def test_sem_trecho_do_campo_volta_para_o_llm(chunks_1415):
    so_referencias = [c for c in chunks_1415 if c.secao == "referencias"]
    assert responder_campo_salve("justificativa de Acanthochelys radiolata", so_referencias) is None


# --- integração com gerar_resposta ----------------------------------------


def test_gerar_resposta_extraida_nao_chama_llm(chunks_1415):
    llm = LLMFalso([])  # qualquer chamada ao LLM levantaria IndexError
    settings = Settings(_env_file=None)
    r = asyncio.run(gerar_resposta(llm, "justificativa da avaliação de Acanthochelys radiolata?", chunks_1415, settings,
                                   incluir_avaliacao=True))
    assert llm.prompts == []
    assert (r.tipo_saida, r.resposta_fundamentada, r.evidencia_suficiente) == ("extraida_salve", True, True)
    assert [c.secao for c in r.citacoes] == ["visao_geral"]
    assert [c.secao for c in r.avaliacao.contextos] == ["visao_geral"]


def test_gerar_resposta_com_extracao_desligada_usa_llm(chunks_1415):
    llm = LLMFalso(["Resposta do modelo."])
    settings = Settings(_env_file=None, extracao_campos_salve=False, groundedness_verificar=False)
    r = asyncio.run(gerar_resposta(llm, "justificativa da avaliação de Acanthochelys radiolata?", chunks_1415, settings))
    assert len(llm.prompts) == 1
    assert r.tipo_saida == "gerada"


# --- exclusão da seção de referências -------------------------------------


@pytest.mark.parametrize("pergunta, esperado", [
    ("qual a justificativa de avaliação para acanthochelys-radiolata-mikan-1820?", ["referencias"]),
    ("Quais as ameaças ao cágado-amarelo?", ["referencias"]),
    ("Quais as referências bibliográficas da ficha do cágado-amarelo?", None),
    ("Quais estudos registraram Acanthochelys radiolata na Bahia?", None),
    ("Quem descreveu Acanthochelys radiolata?", None),
])
def test_secoes_excluidas(pergunta, esperado):
    assert secoes_excluidas(pergunta) == esperado


class _ModeloFalso:
    def encode(self, textos, normalize_embeddings=True):
        return np.array([[0.0, 1.0]])


class _QdrantFalso:
    def __init__(self):
        self.filtros = []

    def query_points(self, collection_name, query, limit, query_filter):
        self.filtros.append(query_filter)

        class _Resposta:
            points = []
        return _Resposta()


def test_buscar_chunks_exclui_secoes_com_must_not():
    cliente = _QdrantFalso()
    settings = Settings(_env_file=None)
    retrieval.buscar_chunks(cliente, _ModeloFalso(), settings, "p", 5, excluir_secoes=["referencias"])
    retrieval.buscar_chunks(cliente, _ModeloFalso(), settings, "p", 5)
    com, sem = cliente.filtros
    assert [(c.key, c.match.any) for c in com.must_not] == [("secao", ["referencias"])]
    assert sem.must_not is None


# --- temperatura e seed ---------------------------------------------------


def test_temperatura_e_seed_fixos_por_padrao():
    s = Settings(_env_file=None)
    assert (s.llm_temperature, s.llm_seed) == (0.0, 42)


def test_temperatura_e_seed_vazios_nao_enviam(monkeypatch):
    monkeypatch.setenv("LLM_TEMPERATURE", "")
    monkeypatch.setenv("LLM_SEED", "")
    s = Settings(_env_file=None)
    assert (s.llm_temperature, s.llm_seed) == (None, None)

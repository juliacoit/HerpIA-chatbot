"""Modo de avaliação offline em /perguntar (Fase 1 da avaliação com RAGAS,
diagnosticos/ragas_fase0.md).

Requisitos testados:
- sem `incluir_contextos`, a resposta é a de sempre, só com `avaliacao: null`;
- `incluir_contextos` com PERMITIR_MODO_AVALIACAO desligado dá 403;
- com a trava ligada, `avaliacao` vem preenchida em todos os caminhos, com
  os contextos idênticos ao texto do prompt e a resposta original das retidas;
- em modo de avaliação, registrar_interacao não é chamado.
"""

import pytest

from backend.config import Settings
from backend.services.geracao import gerar_resposta, montar_prompt
from backend.services.groundedness import MENSAGEM_NAO_FUNDAMENTADA
from backend.services.llm import ContextoExcedidoError
from tests.conftest import LLMFalso

PERGUNTA = "Quais as ameaças à jararaca-do-Vale?"
RESPOSTA_OK = "A principal ameaça é a perda de habitat no Cerrado [Trecho 1]."
RESPOSTA_ABSTENCAO = "Os trechos fornecidos não contêm informação sobre essa pergunta."
# Nome científico seguido de parênteses que não aparece em nenhum trecho:
# dispara o hard gate lexical (camada 1) sem chamar o juiz.
RESPOSTA_FABRICADA = "A espécie Bothrops inventadus (Silva, 1999) também ocorre no Cerrado."
JUIZ_SIM = "SIM\nJustificativa: apoiada no trecho 1."
JUIZ_NAO = "NÃO\nJustificativa: afirma algo que os trechos não dizem."

# Chaves de PerguntarResponse antes da Fase 1.
CHAVES_ORIGINAIS = {
    "id", "pergunta", "resposta", "citacoes", "evidencia_suficiente",
    "resposta_fundamentada", "justificativa_groundedness",
}


def _settings(groundedness_verificar: bool = True) -> Settings:
    return Settings(_env_file=None, groundedness_verificar=groundedness_verificar)


# --- endpoint ---------------------------------------------------------------


def test_sem_flag_resposta_inalterada(cliente_api):
    cliente, estado = cliente_api([RESPOSTA_OK, JUIZ_SIM])
    r = cliente.post("/perguntar", json={"pergunta": PERGUNTA})
    assert r.status_code == 200
    corpo = r.json()
    assert set(corpo) == CHAVES_ORIGINAIS | {"avaliacao"}
    assert corpo["avaliacao"] is None
    assert corpo["id"] == 42
    assert corpo["resposta"] == RESPOSTA_OK
    assert len(estado["registros"]) == 1


def test_flag_com_trava_desligada_da_403_sem_buscar(cliente_api):
    cliente, estado = cliente_api([RESPOSTA_OK, JUIZ_SIM], permitir_modo_avaliacao=False)
    r = cliente.post("/perguntar", json={"pergunta": PERGUNTA, "incluir_contextos": True})
    assert r.status_code == 403
    assert r.json()["detail"] == "Modo de avaliação desabilitado neste ambiente."
    assert estado["buscas"] == 0
    assert estado["llm"].prompts == []
    assert estado["registros"] == []


def test_trava_ligada_sem_flag_continua_normal(cliente_api):
    cliente, estado = cliente_api([RESPOSTA_OK, JUIZ_SIM], permitir_modo_avaliacao=True)
    corpo = cliente.post("/perguntar", json={"pergunta": PERGUNTA}).json()
    assert corpo["avaliacao"] is None
    assert corpo["id"] == 42
    assert len(estado["registros"]) == 1


def test_modo_avaliacao_preenche_e_nao_registra(cliente_api, chunks):
    cliente, estado = cliente_api([RESPOSTA_OK, JUIZ_SIM], permitir_modo_avaliacao=True)
    r = cliente.post("/perguntar", json={"pergunta": PERGUNTA, "incluir_contextos": True})
    assert r.status_code == 200
    corpo = r.json()
    assert estado["registros"] == []
    assert corpo["id"] is None
    assert corpo["avaliacao"]["tipo_saida"] == "gerada"
    contextos = corpo["avaliacao"]["contextos"]
    assert len(contextos) == len(chunks)
    # Texto idêntico ao do prompt: o prompt de geração (primeira chamada ao
    # LLM) é exatamente montar_prompt sobre os mesmos chunks, e cada contexto
    # traz o chunk.texto que montar_prompt usou, na mesma ordem.
    assert estado["llm"].prompts[0] == montar_prompt(PERGUNTA, chunks)
    assert [c["texto"] for c in contextos] == [c.texto for c in chunks]
    for c in contextos:
        assert c["texto"] in estado["llm"].prompts[0]
    assert [c["nivel_sensibilidade"] for c in contextos] == ["autorizado"] * 3
    # Citações deduplicam (2 chunks da mesma ficha); contextos não.
    assert len(corpo["citacoes"]) == 2
    assert "X-LLM-Uso" in r.headers


def test_modo_avaliacao_retida_traz_resposta_original(cliente_api):
    cliente, estado = cliente_api([RESPOSTA_OK, JUIZ_NAO], permitir_modo_avaliacao=True)
    corpo = cliente.post("/perguntar", json={"pergunta": PERGUNTA, "incluir_contextos": True}).json()
    assert corpo["resposta"] == MENSAGEM_NAO_FUNDAMENTADA
    assert corpo["avaliacao"]["tipo_saida"] == "retida_groundedness"
    assert corpo["avaliacao"]["origem_retencao"] == "juiz_llm"
    assert corpo["avaliacao"]["resposta_original"] == RESPOSTA_OK
    assert estado["registros"] == []


def test_sem_flag_retida_nao_vaza_resposta_original(cliente_api):
    cliente, _ = cliente_api([RESPOSTA_OK, JUIZ_NAO], permitir_modo_avaliacao=True)
    r = cliente.post("/perguntar", json={"pergunta": PERGUNTA})
    assert r.json()["avaliacao"] is None
    assert RESPOSTA_OK not in r.text


# --- gerar_resposta: todos os caminhos de retorno -----------------------------


async def _gerar(respostas, chunks, pergunta=PERGUNTA, incluir=True, groundedness=True):
    llm = LLMFalso(respostas)
    resultado = await gerar_resposta(llm, pergunta, chunks, _settings(groundedness), incluir_avaliacao=incluir)
    return resultado, llm


@pytest.mark.asyncio
async def test_caminho_sem_chunks():
    resultado, llm = await _gerar([], [])
    assert resultado.avaliacao.tipo_saida == "sem_chunks"
    assert resultado.avaliacao.contextos == []
    assert llm.prompts == []


@pytest.mark.asyncio
async def test_caminho_sei_nao_indexado(chunks):
    resultado, llm = await _gerar([], chunks, pergunta="Qual o último processo SEI sobre a espécie?")
    assert resultado.avaliacao.tipo_saida == "sei_nao_indexado"
    assert resultado.avaliacao.contextos == []  # recuperados, mas não foram a prompt nenhum
    assert llm.prompts == []


@pytest.mark.asyncio
async def test_caminho_contexto_excedido(chunks):
    resultado, _ = await _gerar([ContextoExcedidoError("num_ctx=8192")], chunks)
    assert resultado.avaliacao.tipo_saida == "contexto_excedido"
    assert [c.texto for c in resultado.avaliacao.contextos] == [c.texto for c in chunks]
    assert resultado.avaliacao.resposta_original is None


@pytest.mark.asyncio
async def test_caminho_gerada(chunks):
    resultado, llm = await _gerar([RESPOSTA_OK, JUIZ_SIM], chunks)
    assert resultado.avaliacao.tipo_saida == "gerada"
    assert resultado.avaliacao.origem_retencao is None
    assert len(llm.prompts) == 2


@pytest.mark.asyncio
async def test_caminho_abstencao_sem_juiz(chunks):
    resultado, llm = await _gerar([RESPOSTA_ABSTENCAO], chunks)
    assert resultado.resposta == RESPOSTA_ABSTENCAO
    assert resultado.resposta_fundamentada is True
    assert resultado.avaliacao.tipo_saida == "abstencao"
    assert len(llm.prompts) == 1  # só a geração; a camada 0 aprovou sem juiz


@pytest.mark.asyncio
async def test_caminho_retida_lexical(chunks):
    resultado, llm = await _gerar([RESPOSTA_FABRICADA], chunks)
    assert resultado.resposta == MENSAGEM_NAO_FUNDAMENTADA
    assert resultado.avaliacao.tipo_saida == "retida_groundedness"
    assert resultado.avaliacao.origem_retencao == "lexical"
    assert resultado.avaliacao.resposta_original == RESPOSTA_FABRICADA
    assert len(llm.prompts) == 1  # hard gate decide sem juiz


@pytest.mark.asyncio
async def test_caminho_retida_juiz_nao_realizado(chunks):
    resultado, _ = await _gerar([RESPOSTA_OK, ContextoExcedidoError("num_ctx=8192")], chunks)
    assert resultado.avaliacao.tipo_saida == "retida_groundedness"
    assert resultado.avaliacao.origem_retencao == "juiz_nao_realizado"
    assert resultado.avaliacao.resposta_original == RESPOSTA_OK


@pytest.mark.asyncio
async def test_groundedness_desligado_e_gerada(chunks):
    resultado, llm = await _gerar([RESPOSTA_ABSTENCAO], chunks, groundedness=False)
    assert resultado.avaliacao.tipo_saida == "gerada"  # sem verificação, não há camada 0
    assert len(llm.prompts) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "respostas, pergunta, usa_chunks",
    [
        ([], PERGUNTA, False),
        ([], "Qual o último processo SEI?", True),
        ([ContextoExcedidoError("x")], PERGUNTA, True),
        ([RESPOSTA_OK, JUIZ_SIM], PERGUNTA, True),
        ([RESPOSTA_OK, JUIZ_NAO], PERGUNTA, True),
        ([RESPOSTA_ABSTENCAO], PERGUNTA, True),
    ],
)
async def test_sem_incluir_avaliacao_e_none_em_todos_os_caminhos(respostas, pergunta, usa_chunks, chunks):
    resultado, _ = await _gerar(respostas, chunks if usa_chunks else [], pergunta=pergunta, incluir=False)
    assert resultado.avaliacao is None

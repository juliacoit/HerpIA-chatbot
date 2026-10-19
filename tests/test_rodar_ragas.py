"""Script da avaliação RAGAS (avaliacao/rodar_ragas.py), sem chamada paga.

O juiz é substituído por métricas falsas que só registram os argumentos, e o
/perguntar por um httpx.MockTransport. Nada aqui importa ragas ou anthropic.
"""

import asyncio
import json
import os
import sys
from types import SimpleNamespace

import httpx
import pytest

from avaliacao import rodar_ragas
from avaliacao.rodar_ragas import (
    METRICAS,
    ModoAvaliacaoDesabilitado,
    agregar_por_categoria,
    ajustar_args_juiz,
    avaliar_caso,
    coletar,
    gerar_relatorio,
)


class MetricaFalsa:
    """Devolve o valor fixo (ou levanta a exceção) e guarda os argumentos."""

    def __init__(self, valor=0.9):
        self.valor = valor
        self.chamadas: list[dict] = []

    async def ascore(self, **kwargs):
        self.chamadas.append(kwargs)
        if isinstance(self.valor, Exception):
            raise self.valor
        return SimpleNamespace(value=self.valor)


def _metricas(**valores):
    return {m: MetricaFalsa(valores.get(m, 0.9)) for m in METRICAS}


def _caso(id_caso="A1", referencia=None):
    return {
        "id": id_caso, "categoria": id_caso[0],
        "user_input": "Qual a categoria de risco de Bothrops marmoratus?",
        "reference": referencia or "PENDENTE_VALIDACAO_RAN",
        "tem_referencia": referencia is not None,
        "fonte_esperada": "salve", "rota_esperada": None, "falha_conhecida": None,
        "top_k": None, "fontes": None,
    }


def _contexto(texto="Categoria de risco: Quase Ameaçada (NT).", fonte="salve", nivel="autorizado"):
    c = {"fonte": fonte, "documento": "Ficha Bothrops marmoratus", "secao": "Categoria",
         "pagina_inicio": None, "pagina_fim": None, "score": 0.8, "texto": texto}
    if nivel is not ...:  # ... = campo ausente
        c["nivel_sensibilidade"] = nivel
    return c


def _corpo(tipo="gerada", contextos=None, resposta="É Quase Ameaçada (NT) [Trecho 1].", original=None, retencao=None):
    return {
        "resposta": resposta,
        "resposta_fundamentada": tipo != "retida_groundedness",
        "avaliacao": {
            "tipo_saida": tipo,
            "origem_retencao": retencao,
            "contextos": [_contexto()] if contextos is None else contextos,
            "resposta_original": original,
        },
    }


def _rodar(coro):
    return asyncio.run(coro)


# --- bloqueio por sensibilidade --------------------------------------------

@pytest.mark.parametrize("nivel", [None, ..., "restrito", "pendente", "Autorizado", ""])
def test_bloqueio_falha_fechado_e_nao_chama_o_juiz(nivel):
    metricas = _metricas()
    contextos = [_contexto(), _contexto(texto="trecho suspeito", nivel=nivel)]
    r = _rodar(avaliar_caso(_caso(), _corpo(contextos=contextos), metricas))
    assert r.status == "bloqueado_sensibilidade"
    assert all(not m.chamadas for m in metricas.values())
    assert r.chamadas_estimadas == 0
    assert r.texto_avaliado is None
    # A rota é local e sem custo: continua checada mesmo no caso bloqueado.
    assert r.rota is not None


def test_bloqueio_tambem_vale_no_dry_run():
    r = _rodar(avaliar_caso(_caso(), _corpo(contextos=[_contexto(nivel=None)]), None))
    assert r.status == "bloqueado_sensibilidade"
    assert r.metricas_planejadas == []


def test_relatorio_e_json_nao_guardam_o_texto_dos_contextos():
    r = _rodar(avaliar_caso(_caso(), _corpo(contextos=[_contexto(texto="TEXTO-DO-TRECHO")]), None))
    assert all("texto" not in c for c in r.contextos)
    assert "TEXTO-DO-TRECHO" not in json.dumps(rodar_ragas.asdict(r), ensure_ascii=False)


# --- escolha das métricas e dos argumentos ---------------------------------

def test_sem_gabarito_so_faithfulness_e_relevancia():
    metricas = _metricas()
    r = _rodar(avaliar_caso(_caso(), _corpo(), metricas))
    assert r.status == "avaliado"
    assert set(r.notas) == {"faithfulness", "answer_relevancy"}
    assert not metricas["context_precision_with_reference"].chamadas
    assert not metricas["context_recall"].chamadas
    assert metricas["faithfulness"].chamadas == [{
        "user_input": _caso()["user_input"],
        "response": "É Quase Ameaçada (NT) [Trecho 1].",
        "retrieved_contexts": ["Categoria de risco: Quase Ameaçada (NT)."],
    }]
    assert metricas["answer_relevancy"].chamadas[0].keys() == {"user_input", "response"}


def test_com_gabarito_roda_as_metricas_de_contexto():
    metricas = _metricas()
    r = _rodar(avaliar_caso(_caso(referencia="Gabarito do RAN."), _corpo(), metricas))
    assert set(r.notas) == set(METRICAS)
    assert metricas["context_recall"].chamadas[0]["reference"] == "Gabarito do RAN."
    assert metricas["context_precision_with_reference"].chamadas[0]["reference"] == "Gabarito do RAN."


def test_subconjunto_de_metricas_para_o_smoke_test():
    metricas = _metricas()
    r = _rodar(avaliar_caso(_caso(), _corpo(), metricas, ("faithfulness",)))
    assert set(r.notas) == {"faithfulness"}
    assert not metricas["answer_relevancy"].chamadas
    assert r.chamadas_estimadas == 2


def test_retida_avalia_a_resposta_original():
    metricas = _metricas()
    corpo = _corpo(tipo="retida_groundedness", resposta="MENSAGEM FIXA DE RETENÇÃO",
                   original="Texto do LLM antes da retenção.", retencao="juiz_llm")
    r = _rodar(avaliar_caso(_caso(), corpo, metricas))
    assert r.origem_texto == "resposta_original"
    assert metricas["faithfulness"].chamadas[0]["response"] == "Texto do LLM antes da retenção."
    assert r.origem_retencao == "juiz_llm"


@pytest.mark.parametrize("tipo", ["sem_chunks", "sei_nao_indexado", "contexto_excedido"])
def test_saidas_sem_texto_do_llm_nao_sao_avaliadas(tipo):
    metricas = _metricas()
    contextos = [] if tipo != "contexto_excedido" else [_contexto()]
    r = _rodar(avaliar_caso(_caso(), _corpo(tipo=tipo, contextos=contextos), metricas))
    assert r.status == "sem_texto_llm"
    assert all(not m.chamadas for m in metricas.values())


def test_dry_run_planeja_sem_chamar():
    caso = _caso(referencia="Gabarito do RAN.")
    corpo = _corpo(contextos=[_contexto(), _contexto(texto="outro trecho")])
    r = _rodar(avaliar_caso(caso, corpo, None))
    assert r.status == "planejado"
    assert r.metricas_planejadas == list(METRICAS)
    # faithfulness 2 + relevância 3 + precisão 1 por contexto (2) + recall 1
    assert r.chamadas_estimadas == 8
    assert r.caracteres_enviados > 0
    assert r.notas == {}


def test_erro_numa_metrica_nao_derruba_as_outras():
    metricas = _metricas(faithfulness=RuntimeError("400 tool_choice"))
    r = _rodar(avaliar_caso(_caso(), _corpo(), metricas))
    assert "faithfulness" in r.erros_metricas
    assert r.notas == {"answer_relevancy": 0.9}


def test_nan_vira_none():
    r = _rodar(avaliar_caso(_caso(), _corpo(), _metricas(faithfulness=float("nan"))))
    assert r.notas["faithfulness"] is None


# --- coleta ----------------------------------------------------------------

def _cliente(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://teste")


def test_coleta_pede_modo_de_avaliacao_com_top_k():
    recebidos = []

    def handler(request):
        recebidos.append(json.loads(request.content))
        return httpx.Response(200, json=_corpo())

    async def rodar():
        async with _cliente(handler) as client:
            return await coletar(client, _caso(), top_k=5, timeout=10)

    _rodar(rodar())
    assert recebidos == [{"pergunta": _caso()["user_input"], "top_k": 5, "incluir_contextos": True}]


def test_coleta_403_interrompe():
    async def rodar():
        async with _cliente(lambda r: httpx.Response(403, json={"detail": "desabilitado"})) as client:
            await coletar(client, _caso(), top_k=5, timeout=10)

    with pytest.raises(ModoAvaliacaoDesabilitado):
        _rodar(rodar())


# --- juiz, agregação e relatório ------------------------------------------

def test_ajuste_do_juiz_remove_amostragem():
    args = {"temperature": 0.01, "top_p": 0.1, "max_tokens": 8192,
            "tool_choice": {"type": "auto", "disable_parallel_tool_use": True}}
    ajustados = ajustar_args_juiz(args)
    assert "temperature" not in ajustados and "top_p" not in ajustados
    assert ajustados["tool_choice"]["type"] == "auto"
    assert ajustados["max_tokens"] == 8192


def test_telemetria_desligada_e_sem_metricas_multimodais():
    assert os.environ["RAGAS_DO_NOT_TRACK"] == "true"
    assert set(METRICAS) == {"faithfulness", "answer_relevancy", "context_precision_with_reference", "context_recall"}
    # Importar o script não carrega ragas nem anthropic: o dry-run não depende deles.
    assert "ragas" not in sys.modules
    assert "anthropic" not in sys.modules


def test_agregacao_por_categoria_ignora_nan_e_erro():
    resultados = [
        _rodar(avaliar_caso(_caso("A1"), _corpo(), _metricas(faithfulness=1.0))),
        _rodar(avaliar_caso(_caso("A2"), _corpo(), _metricas(faithfulness=0.5))),
        _rodar(avaliar_caso(_caso("A3"), _corpo(), _metricas(faithfulness=float("nan")))),
        _rodar(avaliar_caso(_caso("C1"), _corpo(), _metricas(faithfulness=RuntimeError("x")))),
    ]
    cats = agregar_por_categoria(resultados)
    assert cats["A"]["faithfulness"] == pytest.approx(0.75)
    assert cats["A"]["n_faithfulness"] == 2
    assert cats["C"]["faithfulness"] is None
    assert cats["C"]["n_faithfulness"] == 0
    assert cats["A"]["casos"] == 3 and cats["A"]["avaliados"] == 3


def test_relatorio_traz_metadados_e_todos_os_casos():
    resultados = [
        _rodar(avaliar_caso(_caso("A1"), _corpo(), None)),
        _rodar(avaliar_caso(_caso("C1"), _corpo(contextos=[_contexto(nivel=None)]), None)),
    ]
    meta = {"timestamp_iso": "2026-10-19T10:00:00", "dry_run": True, "juiz": "claude-sonnet-5-5",
            "versao_ragas": "0.4.3", "top_k": 5, "git_commit": "abc1234"}
    md = gerar_relatorio(resultados, meta)
    assert "DRY-RUN" in md
    for trecho in ("claude-sonnet-5-5", "0.4.3", "`5`", "abc1234", "| A1 |", "| C1 |", "bloqueado_sensibilidade"):
        assert trecho in md

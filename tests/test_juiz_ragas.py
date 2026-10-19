"""Contornos do juiz Claude no ragas 0.4.3 + instructor 1.17.0, sem rede.

Confere o payload que iria à API da Anthropic (diagnosticos/ragas_fase0.md,
seção 8.2): tool_choice auto, sem temperature/top_p. Uma atualização do ragas
ou do instructor pode quebrar esses contornos (ADR 0007), e este teste é a
conferência. O cliente HTTP do SDK recebe um transporte falso, que captura a
requisição e devolve uma resposta fabricada: nenhuma chamada sai da máquina.
Também confere a contagem de tokens (UsoJuiz) feita no hook de resposta.
Pulado quando requirements-avaliacao.txt não está instalado.
"""

import asyncio
import json

import pytest

pytest.importorskip("ragas")
anthropic = pytest.importorskip("anthropic")
httpx2 = pytest.importorskip("httpx2")

from avaliacao import rodar_ragas  # noqa: E402
from avaliacao.rodar_ragas import UsoJuiz  # noqa: E402


def _resposta_falsa(corpo: dict):
    ferramenta = corpo["tools"][0]["name"]
    if ferramenta == "StatementGeneratorOutput":
        entrada = {"statements": ["A espécie é Quase Ameaçada."]}
    else:
        entrada = {"statements": [{"statement": "A espécie é Quase Ameaçada.", "reason": "ok", "verdict": 1}]}
    return httpx2.Response(200, json={
        "id": "msg_falso", "type": "message", "role": "assistant", "model": corpo["model"],
        "content": [{"type": "tool_use", "id": "toolu_falso", "name": ferramenta, "input": entrada}],
        "stop_reason": "tool_use", "stop_sequence": None,
        "usage": {"input_tokens": 100, "output_tokens": 20},
    })


def _transporte_falso(monkeypatch, handler):
    """Injeta o transporte no cliente HTTP que criar_metricas monta, mantendo
    os event_hooks dele (é ali que o uso de tokens é contado)."""
    original = anthropic.DefaultAsyncHttpxClient
    monkeypatch.setattr(
        anthropic, "DefaultAsyncHttpxClient",
        lambda **kwargs: original(transport=httpx2.MockTransport(handler), **kwargs),
    )


def _faithfulness(metricas):
    return asyncio.run(metricas["faithfulness"].ascore(
        user_input="Qual a categoria de risco?",
        response="É Quase Ameaçada.",
        retrieved_contexts=["Categoria de risco: Quase Ameaçada (NT)."],
    ))


def test_payload_do_juiz_aplica_os_contornos_e_conta_tokens(monkeypatch):
    capturados: list[dict] = []

    def handler(request):
        capturados.append(json.loads(request.content))
        return _resposta_falsa(capturados[-1])

    _transporte_falso(monkeypatch, handler)
    uso = UsoJuiz()
    metricas = rodar_ragas.criar_metricas("claude-sonnet-5-5", "low", ("faithfulness",), uso=uso, api_key="falsa")

    assert _faithfulness(metricas).value == 1.0
    assert len(capturados) == rodar_ragas.estimar_chamadas("faithfulness", 1)
    for corpo in capturados:
        assert corpo["model"] == "claude-sonnet-5-5"
        assert corpo["tool_choice"] == {"type": "auto", "disable_parallel_tool_use": True}
        assert "temperature" not in corpo and "top_p" not in corpo
        assert corpo["max_tokens"] == rodar_ragas.MAX_TOKENS_JUIZ
        assert corpo["output_config"] == {"effort": "low"}
    assert (uso.requisicoes, uso.input_tokens, uso.output_tokens) == (2, 200, 40)
    assert uso.respostas_erro == 0


def test_resposta_de_erro_da_api_conta_como_erro(monkeypatch):
    _transporte_falso(monkeypatch, lambda request: httpx2.Response(
        400, json={"type": "error", "error": {"type": "invalid_request_error", "message": "teste"}},
    ))
    uso = UsoJuiz()
    metricas = rodar_ragas.criar_metricas("claude-sonnet-5-5", "low", ("faithfulness",), uso=uso, api_key="falsa")

    with pytest.raises(Exception):
        _faithfulness(metricas)
    assert uso.requisicoes == 0
    assert uso.respostas_erro >= 1


def test_telemetria_do_ragas_desligada():
    from ragas._analytics import do_not_track

    assert do_not_track()

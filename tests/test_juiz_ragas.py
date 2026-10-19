"""Contornos do juiz Claude no ragas 0.4.3 + instructor 1.17.0, sem rede.

Confere o payload que iria à API da Anthropic (diagnosticos/ragas_fase0.md,
seção 8.2): tool_choice auto, sem temperature/top_p. Uma atualização do ragas
ou do instructor pode quebrar esses contornos (ADR 0007), e este teste é a
conferência. O AsyncAnthropic recebe um transporte HTTP falso, que captura a
requisição e devolve uma resposta fabricada: nenhuma chamada sai da máquina.
Pulado quando requirements-avaliacao.txt não está instalado.
"""

import asyncio
import json

import pytest

pytest.importorskip("ragas")
anthropic = pytest.importorskip("anthropic")
httpx2 = pytest.importorskip("httpx2")

from avaliacao import rodar_ragas  # noqa: E402


def _cliente_falso(capturados: list[dict]):
    def handler(request):
        corpo = json.loads(request.content)
        capturados.append(corpo)
        ferramenta = corpo["tools"][0]["name"]
        if ferramenta == "StatementGeneratorOutput":
            entrada = {"statements": ["A espécie é Quase Ameaçada."]}
        else:
            entrada = {"statements": [{"statement": "A espécie é Quase Ameaçada.", "reason": "ok", "verdict": 1}]}
        return httpx2.Response(200, json={
            "id": "msg_falso", "type": "message", "role": "assistant", "model": corpo["model"],
            "content": [{"type": "tool_use", "id": "toolu_falso", "name": ferramenta, "input": entrada}],
            "stop_reason": "tool_use", "stop_sequence": None,
            "usage": {"input_tokens": 1, "output_tokens": 1},
        })

    # Subclasse, não função: o instructor confere isinstance(client, AsyncAnthropic).
    class ClienteFalso(anthropic.AsyncAnthropic):
        def __init__(self):
            super().__init__(
                api_key="falsa", max_retries=0,
                http_client=anthropic.DefaultAsyncHttpxClient(transport=httpx2.MockTransport(handler)),
            )

    return ClienteFalso


def test_payload_do_juiz_aplica_os_contornos(monkeypatch):
    capturados: list[dict] = []
    monkeypatch.setattr(anthropic, "AsyncAnthropic", _cliente_falso(capturados))

    metricas = rodar_ragas.criar_metricas("claude-sonnet-5-5", "low", ("faithfulness",))
    resultado = asyncio.run(metricas["faithfulness"].ascore(
        user_input="Qual a categoria de risco?",
        response="É Quase Ameaçada.",
        retrieved_contexts=["Categoria de risco: Quase Ameaçada (NT)."],
    ))

    assert resultado.value == 1.0
    assert len(capturados) == rodar_ragas.estimar_chamadas("faithfulness", 1)
    for corpo in capturados:
        assert corpo["model"] == "claude-sonnet-5-5"
        assert corpo["tool_choice"] == {"type": "auto", "disable_parallel_tool_use": True}
        assert "temperature" not in corpo and "top_p" not in corpo
        assert corpo["max_tokens"] == rodar_ragas.MAX_TOKENS_JUIZ
        assert corpo["output_config"] == {"effort": "low"}


def test_telemetria_do_ragas_desligada():
    from ragas._analytics import do_not_track

    assert do_not_track()

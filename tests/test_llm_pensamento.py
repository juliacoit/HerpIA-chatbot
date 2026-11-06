"""Raciocínio (`<think>`) fora da resposta e saída `resposta_vazia`
(experimento Lumi-4B, Fase 3, docs/processos/experimento_lumi_4b.md).

Requisitos testados:
- sem tags, o texto sai idêntico (o qwen2.5:3b de produção não muda);
- bloco completo, `</think>` sem abertura e `<think>` sem fechamento;
- OllamaLLMClient.generate envia `think`, filtra a resposta e registra
  think/latência no uso;
- resposta vazia vira `tipo_saida="resposta_vazia"` sem chamar o juiz.
"""

import asyncio
import json

import httpx
import pytest

from backend.config import Settings
from backend.services import llm as modulo_llm
from backend.services.geracao import gerar_resposta
from backend.services.llm import OllamaLLMClient, registrar_uso_llm, remover_blocos_pensamento
from tests.conftest import LLMFalso

# --- remover_blocos_pensamento ---------------------------------------------


@pytest.mark.parametrize("texto", [
    "A jararaca ocorre no Cerrado [Trecho 1].",
    "  espaços nas pontas e\n\nquebras de linha  ",
    "Texto que fala de think e de <thinking> sem ser a tag.",
    "",
])
def test_sem_tags_texto_identico(texto):
    assert remover_blocos_pensamento(texto) == texto


def test_bloco_completo_removido():
    texto = "<think>\nO usuário pergunta...\n</think>\n\nResposta final."
    assert remover_blocos_pensamento(texto) == "\n\nResposta final."


def test_varios_blocos_removidos():
    texto = "<think>a</think>Parte 1. <think>b</think>Parte 2."
    assert remover_blocos_pensamento(texto) == "Parte 1. Parte 2."


def test_fechamento_sem_abertura():
    # O <think> estava no prompt (template); a saída começa no meio do raciocínio.
    texto = "raciocínio solto\n</think>\nResposta final."
    assert remover_blocos_pensamento(texto) == "\nResposta final."


def test_abertura_sem_fechamento_vira_vazio():
    assert remover_blocos_pensamento("<think>\nPensando e pensando...") == ""


def test_texto_antes_de_abertura_sem_fechamento_fica():
    assert remover_blocos_pensamento("Resposta.\n<think>de novo...") == "Resposta.\n"


def test_tags_em_maiusculas():
    assert remover_blocos_pensamento("<THINK>x</Think>Resposta.") == "Resposta."


# --- OllamaLLMClient.generate ----------------------------------------------


def _ollama_falso(monkeypatch, corpo_resposta: dict) -> list[dict]:
    """Troca o transporte do httpx.AsyncClient criado em generate() e guarda
    os payloads enviados."""
    enviados: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        enviados.append(json.loads(request.content))
        return httpx.Response(200, json=corpo_resposta)

    original = httpx.AsyncClient
    monkeypatch.setattr(
        modulo_llm.httpx, "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs),
    )
    return enviados


def _cliente(think):
    return OllamaLLMClient("http://ollama-falso:11434", "lumi-4b", {"num_ctx": 16384}, think=think)


def _gerar_com_uso(cliente):
    async def rodar():
        with registrar_uso_llm() as uso:
            texto = await cliente.generate("prompt")
        return texto, uso
    return asyncio.run(rodar())


def test_generate_com_parser_resposta_limpa(monkeypatch, capsys):
    enviados = _ollama_falso(monkeypatch, {
        "response": "  Resposta final.  ", "thinking": "raciocínio em inglês",
        "prompt_eval_count": 48, "eval_count": 183,
    })
    texto, uso = _gerar_com_uso(_cliente(True))
    assert texto == "Resposta final."
    assert enviados[0]["think"] is True
    assert uso[0]["think"] is True
    assert uso[0]["latencia_s"] >= 0
    assert (uso[0]["prompt_eval_count"], uso[0]["eval_count"]) == (48, 183)
    log = capsys.readouterr().out
    assert "lumi-4b think=True" in log and "pensamento=20 chars" in log
    assert "raciocínio em inglês" not in log  # só o tamanho, nunca o conteúdo
    assert "removidas" not in log


def test_generate_think_false_enviado_explicito(monkeypatch):
    enviados = _ollama_falso(monkeypatch, {"response": "Ok."})
    texto, _ = _gerar_com_uso(_cliente(False))
    assert texto == "Ok."
    assert enviados[0]["think"] is False


def test_generate_sem_think_nao_envia_campo(monkeypatch):
    enviados = _ollama_falso(monkeypatch, {"response": "Ok."})
    _gerar_com_uso(_cliente(None))
    assert "think" not in enviados[0]


def test_generate_remove_tags_que_vazaram(monkeypatch, capsys):
    _ollama_falso(monkeypatch, {"response": "<think>x</think>\nResposta."})
    texto, _ = _gerar_com_uso(_cliente(None))
    assert texto == "Resposta."
    assert "tags <think> removidas" in capsys.readouterr().out


def test_generate_abertura_sem_fechamento_devolve_vazio(monkeypatch):
    _ollama_falso(monkeypatch, {"response": "<think>pensando sem parar..."})
    texto, _ = _gerar_com_uso(_cliente(None))
    assert texto == ""


# --- gerar_resposta: resposta_vazia ----------------------------------------


@pytest.mark.parametrize("groundedness", [True, False])
@pytest.mark.asyncio
async def test_resposta_vazia_nao_chama_juiz(chunks, groundedness):
    llm = LLMFalso([""])  # o juiz levantaria IndexError se fosse chamado
    settings = Settings(_env_file=None, groundedness_verificar=groundedness)
    resultado = await gerar_resposta(llm, "Onde ocorre a espécie?", chunks, settings, incluir_avaliacao=True)
    assert len(llm.prompts) == 1
    assert resultado.avaliacao.tipo_saida == "resposta_vazia"
    assert [c.texto for c in resultado.avaliacao.contextos] == [c.texto for c in chunks]
    assert resultado.avaliacao.resposta_original is None
    assert resultado.resposta.startswith("Não foi possível gerar a resposta")
    assert resultado.resposta_fundamentada is False
    assert resultado.evidencia_suficiente is True
    assert resultado.citacoes


@pytest.mark.asyncio
async def test_resposta_vazia_fora_do_modo_avaliacao(chunks):
    llm = LLMFalso([""])
    resultado = await gerar_resposta(llm, "Onde ocorre a espécie?", chunks, Settings(_env_file=None))
    assert resultado.avaliacao is None
    assert resultado.resposta_fundamentada is False

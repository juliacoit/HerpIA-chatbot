"""Logging de interações (prioridade 10 do diagnóstico da sessão RAN):
colunas novas preenchidas, `resposta_original` só no banco, e `descrever_rota`
equivalente ao que `buscar_chunks_priorizados` realmente faz.

Nada aqui conecta ao PostgreSQL: o pool é falso e guarda o SQL e os
parâmetros recebidos.
"""

import json
from contextlib import contextmanager

import pytest

from avaliacao.casos import carregar_casos
from backend.config import Settings
from backend.schemas import ChunkRecuperado, Citacao
from backend.services import roteamento
from backend.services.logging_db import descrever_rota, registrar_interacao

PERGUNTA = "Quais as ameaças à jararaca-do-Vale?"
RESPOSTA_OK = "A principal ameaça é a perda de habitat no Cerrado [Trecho 1]."
RESPOSTA_FABRICADA = "A espécie Bothrops inventadus (Silva, 1999) também ocorre no Cerrado."
RESPOSTA_ABSTENCAO = "Os trechos fornecidos não contêm informação sobre essa pergunta."
JUIZ_SIM = "SIM\nJustificativa: apoiada no trecho 1."
JUIZ_NAO = "NÃO\nJustificativa: afirma algo que os trechos não dizem."

COLUNAS_NOVAS = [
    "chunk_ids", "rota", "tipo_saida", "origem_retencao",
    "resposta_original", "llm_temperatura", "llm_seed",
]


class _Cursor:
    def fetchone(self):
        return (7,)


class _Conexao:
    def __init__(self, gravado):
        self._gravado = gravado

    def execute(self, sql, params=None):
        self._gravado.append((sql, params))
        return _Cursor()

    def commit(self):
        pass


class PoolFalso:
    def __init__(self):
        self.gravado = []

    @contextmanager
    def connection(self):
        yield _Conexao(self.gravado)


def _chunks():
    return [
        ChunkRecuperado(score=0.71, fonte="salve", documento="Ficha X", secao="conservacao", parte=1,
                        texto="t1", chunk_id="salve:x.json:3"),
        ChunkRecuperado(score=0.65, fonte="pans", documento="PAN.pdf", secao="pan-x", pagina_inicio=2,
                        pagina_fim=3, parte=7, texto="t2", chunk_id="pans:pan-x/PAN.json:6"),
    ]


def _registrar(pool, **extra):
    base = dict(
        pergunta="p", top_k=2, fontes_filtro=None, resposta="r", evidencia_suficiente=True,
        resposta_fundamentada=True, justificativa_groundedness=None,
        citacoes=[Citacao(fonte="salve", documento="Ficha X", texto="t1")], chunks=_chunks(),
        modelo_llm="qwen2.5:3b-instruct", tempo_resposta_ms=10,
    )
    base.update(extra)
    return registrar_interacao(pool, **base)


def _valores(pool):
    sql, params = pool.gravado[0]
    colunas = sql.split("INSERT INTO interacoes (", 1)[1].split(")", 1)[0]
    nomes = [c.strip() for c in colunas.replace("\n", " ").split(",")]
    assert len(nomes) == len(params)
    return {n: (p.obj if hasattr(p, "obj") else p) for n, p in zip(nomes, params)}


# --- registrar_interacao -----------------------------------------------------


def test_colunas_novas_preenchidas():
    pool = PoolFalso()
    rota = {"fonte_prioritaria": "salve", "filtros": {"bioma": ["Cerrado"]}}
    assert _registrar(pool, rota=rota, tipo_saida="gerada", llm_temperatura=0.0, llm_seed=42) == 7
    v = _valores(pool)
    assert set(COLUNAS_NOVAS) <= set(v)
    assert v["chunk_ids"] == [
        {"chunk_id": "salve:x.json:3", "score": 0.71},
        {"chunk_id": "pans:pan-x/PAN.json:6", "score": 0.65},
    ]
    assert v["rota"] == rota
    assert v["tipo_saida"] == "gerada"
    assert v["origem_retencao"] is None
    assert v["resposta_original"] is None
    assert (v["llm_temperatura"], v["llm_seed"]) == (0.0, 42)
    # colunas antigas continuam iguais
    assert v["chunks_recuperados"][0] == {
        "fonte": "salve", "documento": "Ficha X", "secao": "conservacao",
        "pagina_inicio": None, "pagina_fim": None, "score": 0.71,
    }


def test_rota_none_grava_null_e_temperatura_seed_nulos():
    pool = PoolFalso()
    _registrar(pool, rota=None)
    v = _valores(pool)
    assert v["rota"] is None
    assert v["llm_temperatura"] is None and v["llm_seed"] is None


def test_resposta_original_so_para_retidas():
    pool = PoolFalso()
    _registrar(pool, resposta_fundamentada=True, resposta_original="não devia gravar")
    assert _valores(pool)["resposta_original"] is None

    pool = PoolFalso()
    _registrar(pool, resposta_fundamentada=False, tipo_saida="retida_groundedness",
               origem_retencao="lexical", resposta_original=RESPOSTA_FABRICADA)
    v = _valores(pool)
    assert v["resposta_original"] == RESPOSTA_FABRICADA
    assert v["origem_retencao"] == "lexical"


def test_pool_none_nao_grava():
    assert _registrar(None) is None


# --- endpoint: o que vai para o log e o que NÃO vai para a resposta ----------


def test_endpoint_retida_loga_original_e_nao_expoe(cliente_api):
    cliente, estado = cliente_api([RESPOSTA_FABRICADA])
    r = cliente.post("/perguntar", json={"pergunta": PERGUNTA, "fontes": ["salve"]})
    corpo = r.json()
    assert corpo["tipo_saida"] == "retida_groundedness"
    assert corpo["resposta_fundamentada"] is False
    assert RESPOSTA_FABRICADA not in r.text
    assert "resposta_original" not in corpo
    assert "origem_retencao" not in corpo
    reg = estado["registros"][0]
    assert reg["resposta_original"] == RESPOSTA_FABRICADA
    assert reg["origem_retencao"] == "lexical"
    assert reg["tipo_saida"] == "retida_groundedness"
    assert reg["rota"] is None  # fontes explícitas: o roteamento não roda


def test_endpoint_retida_pelo_juiz(cliente_api):
    cliente, estado = cliente_api([RESPOSTA_OK, JUIZ_NAO])
    r = cliente.post("/perguntar", json={"pergunta": PERGUNTA})
    assert RESPOSTA_OK not in r.text
    reg = estado["registros"][0]
    assert (reg["tipo_saida"], reg["origem_retencao"]) == ("retida_groundedness", "juiz_llm")
    assert reg["resposta_original"] == RESPOSTA_OK


def test_endpoint_gerada_e_abstencao(cliente_api):
    cliente, estado = cliente_api([RESPOSTA_OK, JUIZ_SIM, RESPOSTA_ABSTENCAO])
    corpo1 = cliente.post("/perguntar", json={"pergunta": PERGUNTA}).json()
    corpo2 = cliente.post("/perguntar", json={"pergunta": "Há registros de X no Pampa?"}).json()
    assert corpo1["tipo_saida"] == "gerada"
    assert corpo2["tipo_saida"] == "abstencao"
    assert corpo2["resposta_fundamentada"] is True  # o cálculo não mudou
    r1, r2 = estado["registros"]
    assert (r1["tipo_saida"], r1["origem_retencao"], r1["resposta_original"]) == ("gerada", None, None)
    assert (r2["tipo_saida"], r2["origem_retencao"], r2["resposta_original"]) == ("abstencao", None, None)
    assert r1["rota"] == {"fonte_prioritaria": None, "filtros": {}}


def test_endpoint_grava_temperatura_e_seed_efetivos(cliente_api, monkeypatch):
    from backend.config import obter_settings
    from backend.main import app

    cliente, estado = cliente_api([RESPOSTA_OK, JUIZ_SIM])
    app.dependency_overrides[obter_settings] = lambda: Settings(_env_file=None, llm_temperature=0.2, llm_seed=7)
    cliente.post("/perguntar", json={"pergunta": PERGUNTA})
    reg = estado["registros"][0]
    assert (reg["llm_temperatura"], reg["llm_seed"]) == (0.2, 7)


# --- descrever_rota == o que buscar_chunks_priorizados faz -------------------


def _perguntas():
    perguntas = [c["user_input"] for c in carregar_casos()]
    perguntas += [
        "Quais anfíbios ameaçados ocorrem no Cerrado?",
        "Quais répteis vulneráveis existem na Bahia e em Minas Gerais?",
        "Quais espécies de serpentes há no PAN Herpetofauna do Sul?",
        "Tem algum protocolo de monitoramento sobre lagartos?",
        "Quando foi a última avaliação do risco de extinção da Tracajá",
    ]
    return perguntas


@pytest.mark.parametrize("fontes", [None, [], ["salve"], ["monitora", "pans", "salve"]])
def test_descrever_rota_equivale_a_buscar_chunks_priorizados(monkeypatch, fontes):
    chamadas = []

    def buscar_falso(client, modelo, settings, pergunta, top_k, fontes, filtros_metadados=None):
        chamadas.append({"fontes": fontes, "filtros": filtros_metadados})
        return []  # força a busca complementar quando há prioridade

    monkeypatch.setattr(roteamento, "buscar_chunks", buscar_falso)
    settings = Settings(_env_file=None)
    for pergunta in _perguntas():
        chamadas.clear()
        roteamento.buscar_chunks_priorizados(None, None, settings, pergunta, 5, fontes)
        rota = descrever_rota(pergunta, fontes)
        if rota is None:
            assert chamadas == [{"fontes": fontes, "filtros": None}], pergunta
        elif rota["fonte_prioritaria"] is None:
            assert chamadas == [{"fontes": None, "filtros": None}], pergunta
        else:
            primeira = chamadas[0]
            assert primeira["fontes"] == [rota["fonte_prioritaria"]], pergunta
            assert (primeira["filtros"] or {}) == rota["filtros"], pergunta
        json.dumps(rota)  # serializável para a coluna JSONB

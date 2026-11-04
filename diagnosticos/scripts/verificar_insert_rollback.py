"""Confere o INSERT de `registrar_interacao` contra o PostgreSQL local de
verdade (tipos das colunas novas, adaptação JSONB), SEM gravar nada: o pool
entrega uma conexão real cujo `commit()` vira `rollback()`. Depois da
chamada, confere que a contagem de linhas não mudou.
"""

from contextlib import contextmanager

import psycopg

from backend.config import obter_settings
from backend.schemas import ChunkRecuperado, Citacao
from backend.services.logging_db import descrever_rota, registrar_interacao

settings = obter_settings()


class _ConexaoSemCommit:
    def __init__(self, conn):
        self._conn = conn

    def execute(self, *a, **k):
        return self._conn.execute(*a, **k)

    def commit(self):
        # Lê a linha inserida antes de desfazer, para provar que as colunas
        # novas aceitaram os valores.
        linha = self._conn.execute(
            "select chunk_ids, rota, tipo_saida, origem_retencao, resposta_original, "
            "llm_temperatura, llm_seed from interacoes order by id desc limit 1"
        ).fetchone()
        print("linha inserida (antes do rollback):", linha)
        self._conn.rollback()


class PoolSemCommit:
    @contextmanager
    def connection(self):
        with psycopg.connect(settings.database_url) as conn:
            yield _ConexaoSemCommit(conn)


def contar():
    with psycopg.connect(settings.database_url) as conn:
        return conn.execute("select count(*) from interacoes").fetchone()[0]


antes = contar()
chunks = [ChunkRecuperado(score=0.69, fonte="salve", documento="Rhinella diptycha (Cope, 1862)",
                          secao="conservacao", parte=1, texto="t", chunk_id="salve:rhinella-diptycha.json:4")]
iid = registrar_interacao(
    PoolSemCommit(), pergunta="teste de rollback", top_k=1, fontes_filtro=None, resposta="r",
    evidencia_suficiente=True, resposta_fundamentada=False, justificativa_groundedness="x",
    citacoes=[Citacao(fonte="salve", documento="d", secao="conservacao", parte=1, texto="t")], chunks=chunks,
    modelo_llm="qwen2.5:3b-instruct", tempo_resposta_ms=1,
    rota=descrever_rota("Quais anfíbios ameaçados ocorrem no Cerrado?", None),
    tipo_saida="retida_groundedness", origem_retencao="lexical", resposta_original="original",
    llm_temperatura=None, llm_seed=None,
)
depois = contar()
print(f"id devolvido: {iid}; linhas antes={antes} depois={depois}")
assert iid is not None and antes == depois

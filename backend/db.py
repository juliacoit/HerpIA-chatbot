"""Pool de conexões com o PostgreSQL, para logging de perguntas/respostas e
feedback (Fase 6).

Mesmo padrão de app.state usado para o Qdrant e o modelo de embeddings
(main.py, lifespan): o pool é aberto uma vez no startup e reaproveitado a
cada requisição via Depends (backend/dependencies.py).

O PC servidor com PostgreSQL ainda não está configurado neste momento do
projeto (mesma pendência já documentada para o Qdrant no roadmap, Fase
5.2) — abrir o pool nunca derruba o processo: se a conexão falhar no
startup, `abrir_pool` devolve None e o logging/feedback ficam desativados
nesta sessão (com aviso no console), sem afetar `/buscar` nem `/perguntar`,
que não dependem do PostgreSQL para funcionar.
"""

import logging

from psycopg_pool import ConnectionPool

from backend.config import Settings

log = logging.getLogger(__name__)

TIMEOUT_ABERTURA_SEGUNDOS = 5

_SCHEMA = """
CREATE TABLE IF NOT EXISTS interacoes (
    id BIGSERIAL PRIMARY KEY,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    pergunta TEXT NOT NULL,
    top_k INTEGER NOT NULL,
    fontes_filtro TEXT[],
    resposta TEXT NOT NULL,
    evidencia_suficiente BOOLEAN NOT NULL,
    resposta_fundamentada BOOLEAN NOT NULL,
    justificativa_groundedness TEXT,
    citacoes JSONB NOT NULL DEFAULT '[]',
    chunks_recuperados JSONB NOT NULL DEFAULT '[]',
    modelo_llm TEXT NOT NULL,
    tempo_resposta_ms INTEGER
);

CREATE TABLE IF NOT EXISTS feedback (
    id BIGSERIAL PRIMARY KEY,
    interacao_id BIGINT NOT NULL REFERENCES interacoes(id) ON DELETE CASCADE,
    avaliacao SMALLINT NOT NULL CHECK (avaliacao IN (-1, 1)),
    comentario TEXT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def abrir_pool(settings: Settings) -> ConnectionPool | None:
    """Abre o pool e garante o schema. Devolve None (sem levantar) se o
    PostgreSQL não estiver acessível — ver docstring do módulo."""
    pool = ConnectionPool(settings.database_url, min_size=1, max_size=5, open=False)
    try:
        pool.open(wait=True, timeout=TIMEOUT_ABERTURA_SEGUNDOS)
        with pool.connection() as conn:
            conn.execute(_SCHEMA)
            conn.commit()
        log.info("PostgreSQL conectado — schema de interações/feedback verificado.")
        return pool
    except Exception as exc:  # psycopg_pool.PoolTimeout, psycopg.OperationalError etc.
        log.warning(
            "PostgreSQL indisponível (%s) — logging de perguntas/respostas e "
            "feedback ficam desativados nesta sessão. /buscar e /perguntar "
            "continuam funcionando normalmente. Ver docker-compose.yml / "
            "túnel SSH (docs/roadmap.md, Fase 5.2, mesma pendência do PC "
            "servidor já documentada para o Qdrant).",
            exc,
        )
        pool.close()
        return None


def fechar_pool(pool: ConnectionPool | None) -> None:
    if pool is not None:
        pool.close()

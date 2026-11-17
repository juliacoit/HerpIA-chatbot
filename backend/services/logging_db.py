"""Logging de perguntas/respostas e feedback no PostgreSQL (Fase 6).

O que vai para `interacoes`:
- `chunks_recuperados`: metadados de cada chunk enviado ao LLM (fonte,
  documento, seção, página, score), sem o texto;
- `citacoes`: as citações exibidas ao usuário, **com** o texto de cada uma
  (o mesmo trecho do chunk que o usuário vê na interface, não o documento
  completo);
- desde 2026-11 (diagnosticos/2026-11-04_sessao_supervisionada_ran.md,
  prioridade 10), o necessário para reproduzir uma interação sem exportar o
  índice: `chunk_ids` (ordem e score), `rota` do roteamento SALVE,
  `tipo_saida`/`origem_retencao` (que camada decidiu), `resposta_original`
  das retidas e a temperatura/seed efetivos do LLM.

`resposta_original` só existe no banco: nunca volta na resposta do
`/perguntar` (fica em atributo privado de `PerguntarResponse`) nem aparece
na interface. É texto que a verificação de fundamentação reteve.

Gravar nunca derruba a requisição: se o pool for None (PostgreSQL
indisponível, ver backend/db.py) ou a escrita falhar, só loga um aviso e
devolve None/False.
"""

import logging

from psycopg.types.json import Json
from psycopg_pool import ConnectionPool

from backend.schemas import ChunkRecuperado, Citacao
from backend.services.especies_salve import CatalogoEspecies
from backend.services.roteamento import (
    detectar_filtros_salve,
    detectar_fonte_prioritaria,
    especies_para_rotear,
    secoes_excluidas,
)

log = logging.getLogger(__name__)


def descrever_rota(
    pergunta: str, fontes: list[str] | None, catalogo: CatalogoEspecies | None = None
) -> dict | None:
    """O que `roteamento.buscar_chunks_priorizados` decide para esta
    pergunta, no formato gravado na coluna `rota`.

    Quando a pergunta cita espécies do catálogo: `especies`, com
    `fonte_prioritaria` "salve" e o filtro por `documento` (e
    `fontes_do_cliente`, se houver). Quando o cliente mandou `fontes`, a
    priorização não roda: grava só `fontes_do_cliente` e `secoes_excluidas`
    (até 2026-11-17 era None). Sem `fontes`: `fonte_prioritaria` (None se a
    pergunta não casou com o padrão), os `filtros` de metadado SALVE
    aplicados à busca prioritária e `secoes_excluidas` (None quando a
    pergunta pede bibliografia). Linhas anteriores a 2026-11-17 não têm
    `secoes_excluidas` nem `especies`.

    Reproduz as mesmas condições de `buscar_chunks_priorizados` com as
    mesmas funções puras, em vez de mudar a assinatura daquela função (que
    está fora do escopo desta mudança). `tests/test_logging_interacoes.py`
    confere a equivalência contra `buscar_chunks_priorizados`.
    """
    excluidas = secoes_excluidas(pergunta)
    especies = especies_para_rotear(pergunta, fontes, catalogo)
    if especies:
        rota = {
            "especies": especies, "fonte_prioritaria": "salve",
            "filtros": {"documento": especies}, "secoes_excluidas": excluidas,
        }
        if fontes:
            rota["fontes_do_cliente"] = fontes
        return rota
    if fontes:
        return {"fontes_do_cliente": fontes, "secoes_excluidas": excluidas}
    fonte_prioritaria = detectar_fonte_prioritaria(pergunta)
    filtros = detectar_filtros_salve(pergunta) if fonte_prioritaria == "salve" else {}
    return {"fonte_prioritaria": fonte_prioritaria, "filtros": filtros, "secoes_excluidas": excluidas}


def registrar_interacao(
    pool: ConnectionPool | None,
    *,
    pergunta: str,
    top_k: int,
    fontes_filtro: list[str] | None,
    resposta: str,
    evidencia_suficiente: bool,
    resposta_fundamentada: bool,
    justificativa_groundedness: str | None,
    citacoes: list[Citacao],
    chunks: list[ChunkRecuperado],
    modelo_llm: str,
    tempo_resposta_ms: int,
    rota: dict | None = None,
    tipo_saida: str | None = None,
    origem_retencao: str | None = None,
    resposta_original: str | None = None,
    llm_temperatura: float | None = None,
    llm_seed: int | None = None,
    usuario_id: int | None = None,
) -> int | None:
    if pool is None:
        return None

    chunks_meta = [
        {
            "fonte": c.fonte,
            "documento": c.documento,
            "secao": c.secao,
            "pagina_inicio": c.pagina_inicio,
            "pagina_fim": c.pagina_fim,
            "score": c.score,
        }
        for c in chunks
    ]
    chunk_ids = [{"chunk_id": c.chunk_id, "score": c.score} for c in chunks]
    try:
        with pool.connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO interacoes (
                    pergunta, top_k, fontes_filtro, resposta,
                    evidencia_suficiente, resposta_fundamentada,
                    justificativa_groundedness, citacoes, chunks_recuperados,
                    modelo_llm, tempo_resposta_ms,
                    chunk_ids, rota, tipo_saida, origem_retencao,
                    resposta_original, llm_temperatura, llm_seed, usuario_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                          %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    pergunta,
                    top_k,
                    # lista vazia -> NULL: um TEXT[] vazio sem elementos não
                    # dá pra psycopg inferir o tipo do array ao adaptar.
                    fontes_filtro or None,
                    resposta,
                    evidencia_suficiente,
                    resposta_fundamentada,
                    justificativa_groundedness,
                    Json([c.model_dump() for c in citacoes]),
                    Json(chunks_meta),
                    modelo_llm,
                    tempo_resposta_ms,
                    Json(chunk_ids),
                    Json(rota) if rota is not None else None,
                    tipo_saida,
                    origem_retencao,
                    # Só para retidas, mesmo que quem chama mande algo.
                    resposta_original if not resposta_fundamentada else None,
                    llm_temperatura,
                    llm_seed,
                    usuario_id,
                ),
            )
            interacao_id = cur.fetchone()[0]
            conn.commit()
            return interacao_id
    except Exception as exc:
        log.warning("Falha ao registrar interação no PostgreSQL: %s", exc)
        return None


def registrar_feedback(
    pool: ConnectionPool,
    *,
    interacao_id: int,
    avaliacao: int,
    comentario: str | None,
    usuario_id: int | None = None,
    motivos: list[str] | None = None,
) -> bool:
    """Devolve False se `interacao_id` não existir — ou se a interação for de
    outro usuário: os ids são sequenciais, então sem essa checagem qualquer
    pessoa avaliaria a resposta de outra. Interações anônimas (sem
    usuario_id) continuam avaliáveis por qualquer um, como antes do login.

    Usuário logado tem uma avaliação por interação: reenviar substitui a
    anterior (é assim que a interface acrescenta um comentário depois do
    polegar). Sem login não há como saber de quem é a linha, então cada
    envio anônimo continua virando uma linha nova.
    Assume pool != None — quem chama (backend/routers/feedback.py) já trata
    o caso de pool indisponível antes de chegar aqui."""
    with pool.connection() as conn:
        interacao = conn.execute(
            "SELECT usuario_id FROM interacoes WHERE id = %s", (interacao_id,)
        ).fetchone()
        if interacao is None:
            return False
        if interacao[0] is not None and interacao[0] != usuario_id:
            return False
        motivos = sorted(set(motivos)) if motivos else None
        anterior = None
        if usuario_id is not None:
            anterior = conn.execute(
                "SELECT id FROM feedback WHERE interacao_id = %s AND usuario_id = %s ORDER BY id DESC LIMIT 1",
                (interacao_id, usuario_id),
            ).fetchone()
        if anterior is not None:
            conn.execute(
                "UPDATE feedback SET avaliacao = %s, comentario = %s, motivos = %s, atualizado_em = now() WHERE id = %s",
                (avaliacao, comentario, motivos, anterior[0]),
            )
        else:
            conn.execute(
                "INSERT INTO feedback (interacao_id, avaliacao, comentario, usuario_id, motivos)"
                " VALUES (%s, %s, %s, %s, %s)",
                (interacao_id, avaliacao, comentario, usuario_id, motivos),
            )
        conn.commit()
        return True

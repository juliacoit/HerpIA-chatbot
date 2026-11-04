"""Utilitários compartilhados pelos scripts descartáveis da sessão RAN
(26/10/2026). Só leitura: trabalha sobre o cache exportado por
sessao_ran_00_exportar_indice.py e consulta o PostgreSQL em modo read-only.

O Qdrant embutido (QDRANT_LOCAL_PATH) faz busca exata (força bruta) com
distância cosseno, então `ranking()` abaixo — produto interno entre vetores
normalizados, mesmo filtro `nivel_sensibilidade == autorizado` e mesmo
filtro de fonte — reproduz a ordem de `buscar_chunks`.
"""

import json
import os
from functools import lru_cache
from pathlib import Path

import numpy as np

CACHE = Path(os.environ.get("SESSAO_RAN_CACHE", "indice"))


@lru_cache
def payloads() -> list[dict]:
    with open(CACHE / "payloads.jsonl", encoding="utf-8") as f:
        return [json.loads(l) for l in f]


@lru_cache
def vetores() -> np.ndarray:
    v = np.load(CACHE / "vetores.npy")
    return v / np.linalg.norm(v, axis=1, keepdims=True)


@lru_cache
def modelo():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer("BAAI/bge-m3")


def embed(textos: list[str]) -> np.ndarray:
    return modelo().encode(textos, normalize_embeddings=True)


def ranking(pergunta: str, fontes=("monitora", "pans", "salve"), vetor=None) -> list[tuple[int, int, float]]:
    """[(posição 1-based, índice no cache, score)] de todos os chunks
    autorizados das fontes pedidas, em ordem decrescente de score."""
    q = embed([pergunta])[0] if vetor is None else vetor
    ps = payloads()
    mascara = np.array(
        [p.get("nivel_sensibilidade") == "autorizado" and (not fontes or p.get("fonte") in fontes) for p in ps]
    )
    scores = vetores() @ q
    scores = np.where(mascara, scores, -np.inf)
    ordem = np.argsort(-scores)
    n = int(mascara.sum())
    return [(i + 1, int(idx), float(scores[idx])) for i, idx in enumerate(ordem[:n])]


def rotulo(idx: int) -> str:
    p = payloads()[idx]
    sec = p.get("secao") or p.get("categoria")
    pag = f" p{p.get('pagina_inicio')}-{p.get('pagina_fim')}" if p.get("pagina_inicio") else ""
    return f"{p.get('fonte')}|{p.get('documento')}|{sec}{pag}|parte {p.get('parte')}/{p.get('n_partes')}"


def consultar_pg(sql: str, params=None) -> list[dict]:
    import psycopg

    from backend.config import obter_settings

    with psycopg.connect(obter_settings().database_url) as conn:
        conn.read_only = True
        cur = conn.execute(sql, params)
        cols = [d.name for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

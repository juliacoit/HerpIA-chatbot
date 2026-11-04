"""Diagnóstico descartável (sessão RAN 26/10/2026): reproduz offline o
retrieval das interações #786–#801 e confere contra o que ficou registrado
em `interacoes.chunks_recuperados` (fonte, documento, seção, página, score).

Como a interface manda `fontes=[monitora, pans, salve]` explicitamente,
`buscar_chunks_priorizados` cai direto em `buscar_chunks` (sem roteamento),
então a reprodução é só o ranking por cosseno com o filtro de acesso.

Saída: <cache>/contextos_sessao.json com, por interação, os índices (no
cache) dos chunks do contexto e se a reprodução bateu com o log.
"""

import json

from sessao_ran_comum import CACHE, consultar_pg, payloads, ranking, rotulo

linhas = consultar_pg(
    "select id, pergunta, top_k, fontes_filtro, resposta, resposta_fundamentada, "
    "justificativa_groundedness, citacoes, chunks_recuperados from interacoes "
    "where id between 786 and 801 order by id"
)
ps = payloads()
saida = {}
for r in linhas:
    rk = ranking(r["pergunta"], tuple(r["fontes_filtro"] or ()))
    top = rk[: r["top_k"]]
    log = r["chunks_recuperados"]
    bate = all(
        ps[idx]["documento"] == c["documento"]
        and (ps[idx].get("secao") or ps[idx].get("categoria")) == c["secao"]
        and abs(score - c["score"]) < 1e-3
        for (_, idx, score), c in zip(top, log)
    ) and len(top) == len(log)
    print(f"#{r['id']} reprodução {'OK' if bate else 'DIVERGE'}")
    if not bate:
        for (_, idx, score), c in zip(top, log):
            print(f"   repro {score:.4f} {rotulo(idx)}\n   log   {c['score']:.4f} {c['documento']} {c['secao']}")
    saida[r["id"]] = {
        "pergunta": r["pergunta"],
        "resposta": r["resposta"],
        "fundamentada": r["resposta_fundamentada"],
        "justificativa": r["justificativa_groundedness"],
        "contexto": [idx for _, idx, _ in top],
        "scores": [s for _, _, s in top],
        "citacoes": [
            {"documento": c["documento"], "secao": c.get("secao"), "pagina_inicio": c.get("pagina_inicio")}
            for c in r["citacoes"]
        ],
        "reproducao_bate": bate,
    }
(CACHE / "contextos_sessao.json").write_text(json.dumps(saida, ensure_ascii=False, indent=1))

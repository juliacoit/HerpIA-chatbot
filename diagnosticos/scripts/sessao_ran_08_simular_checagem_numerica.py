"""Diagnóstico descartável (sessão RAN 26/10/2026) — H2.

Simula OFFLINE (sem alterar backend/services/groundedness.py; só importa
`dividir_frases`) duas checagens extras sobre a resposta exibida:

  A (presença): todo ano 19xx/20xx e toda sigla de categoria
    (LC|NT|VU|EN|CR|DD|EW|EX) da resposta aparece em algum chunk do
    contexto ou na pergunta.
  B (co-ocorrência, mais estrita): numa frase da resposta que tem ano E
    categoria, cada par (ano, categoria) precisa aparecer junto numa
    janela de 2 linhas de algum chunk (ex.: "Nacional Brasil 2024: Em
    Perigo (EN)"). Motivo: o cabeçalho de toda ficha SALVE repete a
    categoria, então A sozinha quase nunca falha em SALVE.

Roda sobre (a) as 16 interações da sessão e (b) todas as interações de
`interacoes` cujo retrieval reproduz exatamente o log (o contexto em si não
é gravado no banco). Respostas retidas ficam de fora: o banco guarda só a
mensagem de retenção, não a resposta original.
"""

import json
import re
import sys
from collections import Counter

import numpy as np

from backend.services.groundedness import checar_abstencao_pura, dividir_frases
from sessao_ran_comum import CACHE, consultar_pg, embed, payloads, vetores

RE_ANO = re.compile(r"\b(?:19|20)\d{2}\b")
RE_CAT = re.compile(r"\b(?:LC|NT|VU|EN|CR|DD|EW|EX)\b")

ps = payloads()
V = vetores()
fonte_arr = np.array([p["fonte"] for p in ps])


def contexto_reproduzido(r, q):
    fontes = r["fontes_filtro"] or ["monitora", "pans", "salve"]
    s = V @ q
    s = np.where(np.isin(fonte_arr, fontes), s, -np.inf)
    top = np.argsort(-s)[: r["top_k"]]
    log = r["chunks_recuperados"]
    ok = len(log) == len(top) and all(
        ps[i]["documento"] == c["documento"] and abs(float(s[i]) - c["score"]) < 1e-3 for i, c in zip(top, log)
    )
    # empates (mesmo arquivo em 2 categorias) trocam de ordem: aceita como multiconjunto
    if not ok and len(log) == len(top):
        ok = sorted(round(float(s[i]), 3) for i in top) == sorted(round(c["score"], 3) for c in log) and \
            sorted(ps[i]["documento"] for i in top) == sorted(c["documento"] for c in log)
    return ok, [int(i) for i in top]


def checar(resposta, pergunta, textos):
    alvo = " \n".join(textos) + " \n" + pergunta
    falhas_a = sorted({t for t in RE_ANO.findall(resposta) + RE_CAT.findall(resposta)
                       if not re.search(r"\b" + t + r"\b", alvo)})
    janelas = []
    for t in textos:
        linhas = t.splitlines()
        janelas += [" ".join(linhas[i:i + 2]) for i in range(len(linhas))]
    falhas_b = []
    for frase in dividir_frases(resposta):
        anos, cats = set(RE_ANO.findall(frase)), set(RE_CAT.findall(frase))
        for a in anos:
            for c in cats:
                if not any(re.search(r"\b" + a + r"\b", j) and re.search(r"\b" + c + r"\b", j) for j in janelas):
                    falhas_b.append(f"{a}+{c}")
    return falhas_a, sorted(set(falhas_b))


linhas = consultar_pg(
    "select id, pergunta, top_k, fontes_filtro, resposta, resposta_fundamentada, chunks_recuperados "
    "from interacoes order by id"
)
Q = embed([r["pergunta"] for r in linhas])
stats = Counter()
retidas_a, retidas_b = [], []
sessao = {}
for r, q in zip(linhas, Q):
    stats["total"] += 1
    if not r["resposta_fundamentada"]:
        stats["retida_no_pipeline (fora)"] += 1
        continue
    ok, ctx = contexto_reproduzido(r, q)
    if not ok:
        stats["retrieval_nao_reproduz (fora)"] += 1
        continue
    stats["avaliadas"] += 1
    tem_num = bool(RE_ANO.search(r["resposta"]) or RE_CAT.search(r["resposta"]))
    stats["avaliadas_com_ano_ou_categoria"] += tem_num
    fa, fb = checar(r["resposta"], r["pergunta"], [ps[i]["texto"] for i in ctx])
    abst = checar_abstencao_pura(r["resposta"])
    if fa:
        stats["reteria_A"] += 1
        retidas_a.append((r["id"], fa, abst, r["pergunta"][:90]))
    if fb:
        stats["reteria_B"] += 1
        retidas_b.append((r["id"], fb, abst, r["pergunta"][:90]))
    if 786 <= r["id"] <= 801:
        sessao[r["id"]] = (fa, fb)

print("Resumo:", dict(stats))
print("\nSessão #786–#801 (A = presença, B = co-ocorrência):")
for i in range(786, 802):
    print(f"  #{i}: {sessao.get(i, 'fora (retida ou não reproduz)')}")
print(f"\nRetidas por A ({len(retidas_a)}):")
for x in retidas_a:
    print("  ", x)
print(f"\nRetidas por B ({len(retidas_b)}):")
for x in retidas_b:
    print("  ", x)
(CACHE / "h2_retidas.json").write_text(json.dumps({"A": retidas_a, "B": retidas_b}, ensure_ascii=False))

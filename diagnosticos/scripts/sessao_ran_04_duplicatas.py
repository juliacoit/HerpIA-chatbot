"""Diagnóstico descartável (sessão RAN 26/10/2026) — H4 (#798, boilerplate).

Quantifica chunks duplicados no índice inteiro:
  1. duplicata exata: hash do texto normalizado (minúsculas, sem acento,
     espaços colapsados);
  2. quase-duplicata: cosseno > 0,95 entre vetores BGE-M3 (busca exaustiva
     em blocos, sem índice aproximado).
Agrupa por componente conexo (union-find) e reporta por fonte/documento.
"""

import hashlib
import re
import unicodedata
from collections import Counter, defaultdict

import numpy as np

from sessao_ran_comum import payloads, vetores

LIMIAR = 0.95
ps = payloads()
V = vetores()
n = len(ps)


def norm(t):
    t = unicodedata.normalize("NFKD", t.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t).strip()


def corpo(p):
    # Fichas SALVE: ignora o cabeçalho (Espécie/Categoria/Bioma/DOI/Seção),
    # senão nenhuma seção de espécies diferentes colidiria por hash.
    t = p["texto"]
    if p["fonte"] == "salve" and "\n\n" in t:
        t = t.split("\n\n", 1)[1]
    return norm(t)


pai = list(range(n))


def achar(i):
    while pai[i] != i:
        pai[i] = pai[pai[i]]
        i = pai[i]
    return i


def unir(a, b):
    ra, rb = achar(a), achar(b)
    if ra != rb:
        pai[rb] = ra


# 1) exatas
por_hash = defaultdict(list)
for i, p in enumerate(ps):
    por_hash[hashlib.sha1(corpo(p).encode()).hexdigest()].append(i)
grupos_exatos = [g for g in por_hash.values() if len(g) > 1]
em_exatos = sum(len(g) for g in grupos_exatos)
print(f"Duplicatas exatas (corpo normalizado): {len(grupos_exatos)} grupos, {em_exatos} chunks, "
      f"{em_exatos - len(grupos_exatos)} redundantes ({(em_exatos - len(grupos_exatos)) / n:.1%} do índice)")

# 2) quase-duplicatas por cosseno
pares = 0
for ini in range(0, n, 2000):
    bloco = V[ini:ini + 2000] @ V.T
    for li, cols in zip(*np.nonzero(bloco > LIMIAR)):
        i = ini + li
        if cols > i:
            pares += 1
            unir(i, int(cols))
comp = defaultdict(list)
for i in range(n):
    comp[achar(i)].append(i)
grupos = [g for g in comp.values() if len(g) > 1]
em_grupos = sum(len(g) for g in grupos)
print(f"Quase-duplicatas (cos > {LIMIAR}): {pares} pares, {len(grupos)} grupos, {em_grupos} chunks em grupos, "
      f"{em_grupos - len(grupos)} redundantes ({(em_grupos - len(grupos)) / n:.1%} do índice)")

print("\nChunks em grupos de quase-duplicatas, por fonte (e % da fonte):")
tot_fonte = Counter(p["fonte"] for p in ps)
c = Counter(ps[i]["fonte"] for g in grupos for i in g)
for f, k in c.most_common():
    print(f"  {f:9s} {k:6d}  ({k / tot_fonte[f]:.1%} de {tot_fonte[f]})")


def tipo_grupo(g):
    docs = {ps[i]["documento"] for i in g}
    cats = {(ps[i]["documento"], ps[i].get("categoria")) for i in g}
    if len(docs) == 1 and len(cats) > 1:
        return "mesmo arquivo indexado em >1 categoria"
    if len(docs) == 1:
        return "mesmo documento (repetição interna)"
    return "documentos diferentes (boilerplate/versões)"


print("\nGrupos por tipo:")
tipos = Counter()
for g in grupos:
    tipos[tipo_grupo(g)] += len(g) - 1
for t, k in tipos.most_common():
    print(f"  {k:6d} redundantes — {t}")

print("\nArquivos (mesmo nome) indexados em mais de uma categoria:")
cats_por_doc = defaultdict(set)
chunks_por_doc_cat = Counter()
for p in ps:
    if p["fonte"] != "salve":
        cats_por_doc[(p["fonte"], p["documento"])].add(p.get("categoria"))
        chunks_por_doc_cat[(p["fonte"], p["documento"], p.get("categoria"))] += 1
multi = {k: v for k, v in cats_por_doc.items() if len(v) > 1}
redund = sum(sum(chunks_por_doc_cat[(f, d, c)] for c in sorted(cs)[1:]) for (f, d), cs in multi.items())
print(f"  {len(multi)} arquivos, {redund} chunks redundantes")
for (f, d), cs in sorted(multi.items(), key=lambda kv: -chunks_por_doc_cat[(kv[0][0], kv[0][1], sorted(kv[1])[0])])[:15]:
    print(f"   {f} {d[:70]} -> {sorted(cs)}")

print("\nDocumentos que mais participam de grupos com OUTROS documentos (boilerplate/versões):")
doc_cnt = Counter()
for g in grupos:
    if tipo_grupo(g).startswith("documentos diferentes"):
        for i in g:
            doc_cnt[(ps[i]["fonte"], ps[i]["documento"])] += 1
for (f, d), k in doc_cnt.most_common(25):
    print(f"  {k:5d} {f:8s} {d[:90]}")

print("\nMaiores grupos com documentos diferentes (tamanho, docs distintos, amostra de texto):")
dif = sorted((g for g in grupos if tipo_grupo(g).startswith("documentos diferentes")), key=len, reverse=True)
for g in dif[:12]:
    docs = Counter(ps[i]["documento"] for i in g)
    print(f"  {len(g):4d} chunks / {len(docs)} docs: {ps[g[0]]['texto'][:110]!r}")
    print(f"        ex.: {', '.join(d[:45] for d in list(docs)[:4])}")

# grupo do #798 (Apresentação dos roteiros metodológicos)
alvo = [i for i, p in enumerate(ps) if p["documento"].startswith("Nobreetal2023RoteiroMetodologicoManejoFlorestal") and p.get("pagina_inicio") == 6]
for i in alvo:
    g = comp[achar(i)]
    print(f"\nGrupo do chunk de #798 ({ps[i]['documento']} p6): {len(g)} chunks — "
          + "; ".join(sorted({ps[j]['documento'][:40] for j in g})))

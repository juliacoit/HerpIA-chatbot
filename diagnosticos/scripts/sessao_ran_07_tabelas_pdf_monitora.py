"""Diagnóstico descartável (sessão RAN 26/10/2026) — H4 (#800), alcance
com detecção real de tabela (PyMuPDF `find_tables`), SÓ LEITURA, restrito
aos PDFs do Monitora indexados (onde estão os protocolos). Conta páginas
com tabela de >= 3 linhas e >= 3 colunas por documento.
"""

import json
from collections import Counter
from pathlib import Path

import fitz

from sessao_ran_comum import payloads

docs = sorted({(p["categoria"], p["documento"]) for p in payloads() if p["fonte"] == "monitora"})
base = Path("01_fontes_web/monitora")
res = {}
faltando = 0
for cat, nome in docs:
    cands = list(base.glob(f"{cat}/**/{nome}"))
    if not cands:
        faltando += 1
        continue
    try:
        d = fitz.open(cands[0])
    except Exception:
        continue
    paginas_tab = 0
    for pg in d:
        try:
            if any(t.row_count >= 3 and t.col_count >= 3 for t in pg.find_tables().tables):
                paginas_tab += 1
        except Exception:
            pass
    res[nome] = (paginas_tab, len(d))
    d.close()
com = {k: v for k, v in res.items() if v[0] > 0}
print(f"PDFs Monitora indexados: {len(docs)}; abertos: {len(res)}; não localizados: {faltando}")
print(f"PDFs com >= 1 página com tabela (>=3x3): {len(com)}; páginas com tabela: {sum(v[0] for v in com.values())} de {sum(v[1] for v in res.values())}")
for k, (t, n) in sorted(com.items(), key=lambda kv: -kv[1][0])[:30]:
    print(f"  {t:4d}/{n:<4d} {k[:95]}")

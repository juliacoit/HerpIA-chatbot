"""Diagnóstico descartável (sessão RAN 26/10/2026) — H4 (#800), alcance.

Heurística de texto (não abre PDFs): um chunk de PDF "parece tabela
achatada" quando tem >= 15 linhas e >= 70% delas com menos de 45
caracteres — a assinatura do `page.get_text()` emitindo célula por linha.
É estimativa: também pega sumários, listas de nomes e legendas.
"""

from collections import Counter

from sessao_ran_comum import payloads

ps = payloads()
por_doc = Counter()
tot_doc = Counter()
n_tab = 0
for p in ps:
    if p["fonte"] == "salve":
        continue
    tot_doc[(p["fonte"], p["documento"])] += 1
    linhas = [l for l in p["texto"].splitlines() if l.strip()]
    if len(linhas) >= 15 and sum(len(l) < 45 for l in linhas) / len(linhas) >= 0.7:
        n_tab += 1
        por_doc[(p["fonte"], p["documento"])] += 1
pdf_total = sum(tot_doc.values())
print(f"chunks de PDF com assinatura de tabela/lista achatada: {n_tab} de {pdf_total} ({n_tab / pdf_total:.1%})")
print(f"documentos com >= 1 chunk assim: {len(por_doc)} de {len(tot_doc)}")
print(f"documentos com >= 20% dos chunks assim: {sum(1 for d, k in por_doc.items() if k / tot_doc[d] >= 0.2)}")
print("\nTop 25 documentos (chunks tabela / total):")
for (f, d), k in por_doc.most_common(25):
    print(f"  {k:4d}/{tot_doc[(f, d)]:<4d} {f:8s} {d[:95]}")
print("\nDocumentos de protocolos/estrutura do Monitora com essa assinatura:")
for (f, d), k in sorted(por_doc.items()):
    if f == "monitora" and any(s in d.lower() for s in ("protocolo", "estrutura", "roteiro", "guia")):
        print(f"  {k:4d}/{tot_doc[(f, d)]:<4d} {d[:95]}")

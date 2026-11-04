"""Diagnóstico descartável (sessão RAN 26/10/2026) — H4 (#800, tabela achatada).

Abre o PDF original SÓ PARA LEITURA (PyMuPDF), detecta a tabela da página 1
com `page.find_tables()` e mostra as linhas como o PDF as organiza
(linha/coluna), para comparar com o texto extraído que foi indexado
(`page.get_text()` em scripts/processamento/extrair_texto_pdfs.py).
"""

import sys

import fitz

pdf = sys.argv[1]
doc = fitz.open(pdf)
pagina = doc[0]
print(f"páginas: {len(doc)}  tamanho p1: {pagina.rect}")
tabs = pagina.find_tables()
print(f"tabelas detectadas na p1: {len(tabs.tables)}")
for t in tabs.tables:
    print(f"\n--- tabela {t.bbox} linhas={t.row_count} colunas={t.col_count}")
    print("cabeçalho:", t.header.names)
    for linha in t.extract():
        celulas = [(c or "").replace("\n", " ")[:55] for c in linha]
        if any("agarto" in c or "rosof" in c or "Sonora" in c or "acústica" in c for c in celulas):
            print("  >>", " | ".join(celulas))
doc.close()

"""Diagnóstico descartável (sessão RAN 26/10/2026) — H7 (escopo e #795).

1. Composição do índice por fonte e, quando dá para inferir pelo nome do
   PAN/arquivo (heurística de palavra-chave), por grupo: herpetofauna,
   multi-táxon/territorial (pode conter herpetofauna) e outros táxons.
2. Chunks por espécie nas fichas SALVE (base para pergunta agregada #795).
3. Em quantas interações registradas o roteamento SALVE dispararia
   (para dimensionar o efeito da interface mandar as 3 fontes sempre).
"""

import re
from collections import Counter

from backend.services.roteamento import detectar_fonte_prioritaria
from sessao_ran_comum import consultar_pg, payloads

# Casamento por início de token (separando por não-letra), não substring:
# "UCsapoiadas" contém "sapo", "pmp-bp" contém nada disso etc.
HERP = re.compile(r"(?:^|[^a-zà-ÿ])(?:herpeto|quel[oô]ni|tartarugas?(?:-marinhas)?\b|r[eé]pte|anf[ií]bi|anuro|"
                  r"jacar|crocodil|serpente|lagart|bothrops|jabuti|podocnemis|perereca)", re.I)
MULTI = re.compile(r"paraiba-do-sul|sao-francisco|alto-parana|iguacu|mogi|manguezal|cavernas|"
                   r"territorial|tocantins|araguaia|espinhaco|planalto|lagoas-do-sul|rivulideos|"
                   r"baixo-iguacu|ecossistemas|campos-sulinos|cerrado|caatinga|amazonia|mata-atlantica", re.I)

ps = payloads()
print("Chunks por fonte:", Counter(p["fonte"] for p in ps))
grupo = Counter()
docs_grupo = Counter()
cats = Counter()
vistos = set()
for p in ps:
    f = p["fonte"]
    if f == "salve":
        g = "herpetofauna (SALVE)"
    else:
        alvo = f"{p.get('categoria', '')} {p['documento']}"
        g = "herpetofauna" if HERP.search(alvo) else ("multi-táxon/territorial" if MULTI.search(alvo) else "outros táxons/institucional")
        cats[(f, p.get("categoria"), g)] += 1
    grupo[(f, g)] += 1
    if (f, p["documento"]) not in vistos:
        vistos.add((f, p["documento"]))
        docs_grupo[(f, g)] += 1
tot = len(ps)
print("\nComposição por fonte × grupo (chunks / documentos):")
for (f, g), k in sorted(grupo.items()):
    print(f"  {f:9s} {g:30s} {k:6d} ({k / tot:5.1%})  docs={docs_grupo[(f, g)]}")
print("\nCategorias PAN classificadas como herpetofauna:")
for (f, c, g), k in sorted(cats.items()):
    if g == "herpetofauna" and f == "pans":
        print(f"  {k:5d} {c}")
print("\nDocumentos Monitora classificados como herpetofauna:")
for d in sorted({p["documento"] for p in ps if p["fonte"] == "monitora" and HERP.search(p["documento"] + p.get("categoria", ""))}):
    print("  ", d)

print("\n#795 — chunks por espécie (SALVE), top 10 e distribuição:")
por_esp = Counter(p["documento"] for p in ps if p["fonte"] == "salve")
for d, k in por_esp.most_common(10):
    print(f"  {k:4d} {d}")
vals = sorted(por_esp.values())
print(f"  fichas={len(vals)} mediana={vals[len(vals) // 2]} min={vals[0]} max={vals[-1]}")

print("\nRoteamento SALVE nas interações registradas:")
rs = consultar_pg("select id, pergunta, fontes_filtro from interacoes")
disp = [r for r in rs if detectar_fonte_prioritaria(r["pergunta"])]
print(f"  dispararia em {len(disp)} de {len(rs)} interações; "
      f"destas, com fontes explícitas (roteamento ignorado): {sum(1 for r in disp if r['fontes_filtro'])}")
print(f"  perguntas distintas que disparam: {len({r['pergunta'] for r in disp})} de {len({r['pergunta'] for r in rs})}")

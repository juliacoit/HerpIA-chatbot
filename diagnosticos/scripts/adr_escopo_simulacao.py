"""Simulação offline para o ADR de escopo (herpetofauna) — nada é gravado.

Usa o cache exportado por sessao_ran_00_exportar_indice.py (payloads do
Qdrant) e calcula:
  1. grupos por fonte (mesma heurística por nome de sessao_ran_09);
  2. classificação POR CONTEÚDO dos chunks de PANs territoriais/multi-táxon:
     o chunk entra se mencionar nome científico (binômio), nome comum ou
     sinônimo de alguma ficha SALVE — o mesmo dicionário da expansão de
     consulta (prioridade 6 do diagnóstico);
  3. o mesmo critério aplicado aos PANs de "outros táxons" e ao Monitora,
     só para medir (a proposta não os classifica por conteúdo);
  4. os termos que mais disparam, para estimar falso positivo.
"""

import json
import re
import unicodedata
from collections import Counter, defaultdict

from sessao_ran_comum import CACHE, payloads

ps = payloads()


def norm(t):
    t = unicodedata.normalize("NFKD", t.lower())
    return "".join(c for c in t if not unicodedata.combining(c))


# --- dicionário a partir do SALVE ------------------------------------------
termos = {}  # termo normalizado -> (tipo, ficha)
for p in ps:
    if p["fonte"] != "salve":
        continue
    ficha = p["documento"]
    binomio = " ".join(ficha.split()[:2])
    termos.setdefault(norm(binomio), ("cientifico", ficha))
    for nome in re.split(r",\s*", p.get("nome_comum") or ""):
        nome = re.sub(r"\s*\(.*?\)", "", nome).strip()
        if len(nome) >= 4:
            termos.setdefault(norm(nome), ("comum", ficha))
    if p["secao"] == "taxonomia":
        m = re.search(r"Sinonímias:\s*(.+)", p["texto"])
        if m:
            for s in m.group(1).split(","):
                s = " ".join(s.split()[:2])
                if len(s.split()) == 2:
                    termos.setdefault(norm(s), ("sinonimo", ficha))
print("termos no dicionário:", Counter(t for t, _ in termos.values()))

ordenados = sorted(termos, key=len, reverse=True)
padrao = re.compile(r"(?<![a-z0-9])(" + "|".join(re.escape(t) for t in ordenados) + r")(?![a-z0-9])")

HERP = re.compile(r"(?:^|[^a-zà-ÿ])(?:herpeto|quel[oô]ni|tartarugas?(?:-marinhas)?\b|r[eé]pte|anf[ií]bi|anuro|"
                  r"jacar|crocodil|serpente|lagart|bothrops|jabuti|podocnemis|perereca)", re.I)
MULTI = re.compile(r"paraiba-do-sul|sao-francisco|alto-parana|iguacu|mogi|manguezal|cavernas|"
                   r"territorial|tocantins|araguaia|espinhaco|planalto|lagoas-do-sul|rivulideos|"
                   r"baixo-iguacu|ecossistemas|campos-sulinos|cerrado|caatinga|amazonia|mata-atlantica", re.I)


def grupo(p):
    if p["fonte"] == "salve":
        return "salve"
    alvo = f"{p.get('categoria', '')} {p['documento']}"
    if HERP.search(alvo):
        return f"{p['fonte']}:herp"
    if p["fonte"] == "pans" and MULTI.search(alvo):
        return "pans:multi"
    return f"{p['fonte']}:outros"


cont = Counter()
incl = Counter()
termos_hit = defaultdict(Counter)
docs_herp = defaultdict(Counter)
docs_incl = defaultdict(Counter)
docs_total = defaultdict(Counter)
for p in ps:
    g = grupo(p)
    cont[g] += 1
    docs_total[g][(p.get("categoria"), p["documento"])] += 1
    if g.endswith(":herp"):
        docs_herp[g][(p.get("categoria"), p["documento"])] += 1
    if g == "salve":
        continue
    achados = set(padrao.findall(norm(p["texto"])))
    if achados:
        incl[g] += 1
        docs_incl[g][(p.get("categoria"), p["documento"])] += 1
        for t in achados:
            termos_hit[g][t] += 1

print("\nchunks por grupo:", dict(cont), "total:", sum(cont.values()))
print("\nchunks que mencionam espécie do SALVE (por grupo):")
for g in sorted(cont):
    if g != "salve":
        print(f"  {g:16s} {incl[g]:6d} de {cont[g]:6d} ({incl[g] / cont[g]:.1%})  docs com ≥1: {len(docs_incl[g])} de {len(docs_total[g])}")

for g in ("pans:multi", "pans:outros", "monitora:outros"):
    print(f"\ntermos mais frequentes em {g} (chunks):")
    for t, k in termos_hit[g].most_common(20):
        print(f"   {k:5d} {t!r} {termos[t]}")

print("\nPANs de herpetofauna (pelo nome) — documentos:")
for (cat, d), k in sorted(docs_herp["pans:herp"].items()):
    print(f"  {k:4d} {cat} | {d}")
print("\nMonitora 'herp' pelo nome:", sorted(docs_herp["monitora:herp"].items()))
print("\nMonitora: documentos com >= 30% dos chunks mencionando espécie SALVE:")
for (cat, d), k in sorted(docs_incl["monitora:outros"].items(), key=lambda kv: -kv[1] / docs_total["monitora:outros"][kv[0]]):
    tot = docs_total["monitora:outros"][(cat, d)]
    if k / tot >= 0.3:
        print(f"  {k:4d}/{tot:<4d} {cat} | {d}")

# --- variante estrita: sem nome comum de uma palavra só --------------------
# Os nomes comuns simples colidem com sobrenomes, topônimos e outros táxons
# ("cunha", "pintada" de onça-pintada, "cecilia", "cipo" de Serra do Cipó,
# "coral"). Fica: binômio científico, sinônimo e nome comum composto
# (com hífen ou mais de uma palavra).
estritos = [t for t, (tipo, _) in termos.items() if tipo != "comum" or ("-" in t or " " in t)]
estritos.sort(key=len, reverse=True)
padrao_e = re.compile(r"(?<![a-z0-9])(" + "|".join(re.escape(t) for t in estritos) + r")(?![a-z0-9])")
incl_e = Counter()
hit_e = defaultdict(Counter)
docs_e = defaultdict(set)
for p in ps:
    g = grupo(p)
    if g == "salve":
        continue
    achados = set(padrao_e.findall(norm(p["texto"])))
    if achados:
        incl_e[g] += 1
        docs_e[g].add(p["documento"])
        for t in achados:
            hit_e[g][t] += 1
print(f"\nVARIANTE ESTRITA ({len(estritos)} termos):")
for g in sorted(cont):
    if g != "salve":
        print(f"  {g:16s} {incl_e[g]:6d} de {cont[g]:6d} ({incl_e[g] / cont[g]:.1%})  docs: {len(docs_e[g])}")
for g in ("pans:multi", "pans:outros"):
    print(f"  termos estritos mais frequentes em {g}:", hit_e[g].most_common(12))
json.dump({"cont": cont, "incl": incl, "incl_estrito": incl_e}, open(CACHE / "adr_escopo.json", "w"))

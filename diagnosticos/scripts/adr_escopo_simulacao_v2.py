"""Simulação offline do ADR 0008 depois das decisões da equipe do RAN de
2026-11-11 — só leitura, nada é gravado.

Diferente de adr_escopo_simulacao.py (que usa o cache do Qdrant e classifica
PAN territorial por trecho), este lê direto os `chunks.jsonl` de
`07_processados/chunks/` e aplica as regras decididas:

  1. tartarugas marinhas ficam fora (fichas SALVE, PAN Tartarugas Marinhas,
     conteúdo nos relatórios do PMP-BP);
  2. PAN classificado inteiro: entra se tiver réptil ou anfíbio entre as
     espécies-alvo, senão fica fora;
  3. Monitora por subprograma, componente e alvo.

Uso (a partir da raiz do repositório):
    venv/bin/python diagnosticos/scripts/adr_escopo_simulacao_v2.py

Imprime só contagens, nomes de PAN, nomes de arquivo e nomes científicos.
"""

import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CHUNKS = RAIZ / "07_processados" / "chunks"


def carregar(fonte: str) -> list[dict]:
    caminho = CHUNKS / fonte / "chunks.jsonl"
    if not caminho.exists():
        return []
    with open(caminho, encoding="utf-8") as f:
        return [json.loads(linha) for linha in f]


def norm(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


def secao(titulo: str) -> None:
    print(f"\n{'=' * 78}\n{titulo}\n{'=' * 78}")


salve, pans, monitora, publicacoes = (carregar(f) for f in ("salve", "pans", "monitora", "publicacoes"))
print(f"chunks: salve={len(salve)} pans={len(pans)} monitora={len(monitora)} "
      f"(índice atual={len(salve) + len(pans) + len(monitora)}) publicacoes={len(publicacoes)} (não indexadas)")

# --------------------------------------------------------------------------
# 1. Tartarugas marinhas
# --------------------------------------------------------------------------
# As cinco espécies com ocorrência no Brasil (famílias Cheloniidae e
# Dermochelyidae). A lista final é da equipe do RAN.
TARTARUGAS_MARINHAS = [
    "Caretta caretta",
    "Chelonia mydas",
    "Eretmochelys imbricata",
    "Lepidochelys olivacea",
    "Dermochelys coriacea",
]
_abrev = [f"{b.split()[0][0]}\\.\\s*{b.split()[1]}" for b in TARTARUGAS_MARINHAS]
RE_TMAR = re.compile(
    "|".join(norm(b) for b in TARTARUGAS_MARINHAS) + "|" + "|".join(norm(a) for a in _abrev)
    + r"|tartarugas?[\s-]+marinhas?|quelonios?\s+marinhos?"
    + r"|tartarugas?[\s-]+(?:verde|cabecuda|oliva|de[\s-]+couro|de[\s-]+pente)"
)

secao("1. TARTARUGAS MARINHAS")
fichas_tmar = Counter()
for p in salve:
    binomio = " ".join(p["documento"].split()[:2])
    if binomio in TARTARUGAS_MARINHAS:
        fichas_tmar[p["documento"]] += 1
print("1.1 Fichas SALVE de tartarugas marinhas (saem inteiras):")
for ficha, n in sorted(fichas_tmar.items()):
    print(f"   {n:4d} chunks  {ficha}")
print(f"   total: {len(fichas_tmar)} fichas, {sum(fichas_tmar.values())} chunks "
      f"(SALVE passa de {len(salve)} para {len(salve) - sum(fichas_tmar.values())} chunks; "
      f"fichas de {len({p['documento'] for p in salve})} para {len({p['documento'] for p in salve}) - len(fichas_tmar)})")

n_pan_tmar = Counter(p["documento"] for p in pans if p["categoria"] == "pan-tartarugas-marinhas")
print(f"\n1.2 PAN Tartarugas Marinhas (categoria pan-tartarugas-marinhas): "
      f"{len(n_pan_tmar)} documentos, {sum(n_pan_tmar.values())} chunks")

print("\n1.3 Menções a tartarugas marinhas nos demais PANs, por categoria (chunks com menção / total):")
tot_cat = Counter(p["categoria"] for p in pans)
men_cat = Counter()
men_doc = defaultdict(Counter)
tot_doc = defaultdict(Counter)
for p in pans:
    tot_doc[p["categoria"]][p["documento"]] += 1
    if p["categoria"] != "pan-tartarugas-marinhas" and RE_TMAR.search(norm(p["texto"])):
        men_cat[p["categoria"]] += 1
        men_doc[p["categoria"]][p["documento"]] += 1
for cat, n in men_cat.most_common():
    print(f"   {n:5d} / {tot_cat[cat]:5d}  {cat}")
print(f"   total fora do PAN Tartarugas Marinhas: {sum(men_cat.values())} chunks em {len(men_cat)} PANs")

print("\n1.4 Relatórios do PMP-BP e afins dentro de pan-peixe-boi-marinho (menção / total do documento):")
pb = "pan-peixe-boi-marinho"
for doc, total in sorted(tot_doc[pb].items(), key=lambda kv: -men_doc[pb][kv[0]]):
    if men_doc[pb][doc]:
        print(f"   {men_doc[pb][doc]:5d} / {total:5d}  {doc}")
pmp = [d for d in tot_doc[pb] if "pmp" in norm(d)]
print(f"   documentos com 'pmp' no nome: {len(pmp)}; chunks: {sum(tot_doc[pb][d] for d in pmp)}; "
      f"com menção a tartaruga marinha: {sum(men_doc[pb][d] for d in pmp)}")

print("\n1.5 Menções a tartarugas marinhas no Monitora (menção / total do documento):")
men_mon = Counter()
tot_mon = Counter()
for p in monitora:
    chave = (p["categoria"], p["documento"])
    tot_mon[chave] += 1
    if RE_TMAR.search(norm(p["texto"])):
        men_mon[chave] += 1
for chave, n in men_mon.most_common():
    print(f"   {n:5d} / {tot_mon[chave]:5d}  {chave[0]} | {chave[1]}")
print(f"   total: {sum(men_mon.values())} chunks em {len(men_mon)} documentos")

if publicacoes:
    men_pub = Counter(p["documento"] for p in publicacoes if RE_TMAR.search(norm(p["texto"])))
    print(f"\n1.6 Publicações do RAN (ainda não indexadas): {sum(men_pub.values())} chunks com menção, "
          f"em {len(men_pub)} de {len({p['documento'] for p in publicacoes})} documentos")

# --------------------------------------------------------------------------
# 2. PANs: classificação por PAN (espécie-alvo de herpetofauna)
# --------------------------------------------------------------------------
secao("2. PANs — CLASSIFICAÇÃO POR PAN")

PANS_HERPETO = {
    "pan-herpetofauna-do-espinhaco", "pan-herpetofauna-do-nordeste", "pan-herpetofauna-do-sudeste",
    "pan-herpetofauna-do-sul", "pan-herpetofauna-insular", "pan-quelonios",
}
# PANs definidos por território/ambiente, não por um grupo taxonômico. O termo
# é o que se procura nas fichas SALVE, perto de "Plano de Ação Nacional"/"PAN".
PANS_TERRITORIAIS = {
    "pan-alto-parana": r"alto parana",
    "pan-cavernas-do-brasil": r"cavernas do brasil|patrimonio espeleologico",
    "pan-cavernas-do-sao-francisco": r"cavernas do sao francisco",
    "pan-cerpam": r"cerpan|cerrado e pantanal",
    "pan-iguacu": r"baixo iguacu",
    "pan-lagoas-do-sul": r"lagoas do sul|sistemas lacustres e lagunares",
    "pan-manguezal": r"manguezal",
    "pan-mogi-pardo-sapucai-mirim-grande": r"mogi|sapucai",
    "pan-paraiba-do-sul": r"paraiba do sul",
    "pan-sao-francisco": r"bacia do (?:rio )?sao francisco|pan sao francisco",
    "pan-xingu": r"xingu",
}

# Evidência 1: fichas SALVE cuja seção Conservação cita o PAN.
RE_PAN = re.compile(r"plano de acao nacional|\bpan\b")
fichas_por_pan = defaultdict(set)
for p in salve:
    if p["secao"] != "conservacao":
        continue
    binomio = " ".join(p["documento"].split()[:2])
    if binomio in TARTARUGAS_MARINHAS:
        continue
    texto = norm(p["texto"])
    for m in RE_PAN.finditer(texto):
        janela = texto[m.start(): m.start() + 260]
        for cat, termo in PANS_TERRITORIAIS.items():
            if re.search(termo, janela):
                fichas_por_pan[cat].add(binomio)

# Evidência 2: chunks do PAN que citam espécie do SALVE (binômio, sinônimo ou
# nome comum composto — a "variante estrita" do ADR), sem tartarugas marinhas.
termos = {}
for p in salve:
    binomio = " ".join(p["documento"].split()[:2])
    if binomio in TARTARUGAS_MARINHAS:
        continue
    termos.setdefault(norm(binomio), binomio)
    for nome in re.split(r",\s*", p.get("nome_comum") or ""):
        nome = re.sub(r"\s*\(.*?\)", "", nome).strip()
        if len(nome) >= 4 and ("-" in nome or " " in nome):
            termos.setdefault(norm(nome), binomio)
    if p["secao"] == "taxonomia":
        m = re.search(r"Sinonímias:\s*(.+)", p["texto"])
        if m:
            for s in m.group(1).split(","):
                s = " ".join(s.split()[:2])
                if len(s.split()) == 2:
                    termos.setdefault(norm(s), binomio)
RE_SALVE = re.compile(
    r"(?<![a-z0-9])(" + "|".join(re.escape(t) for t in sorted(termos, key=len, reverse=True)) + r")(?![a-z0-9])"
)
print(f"dicionário estrito (sem tartarugas marinhas): {len(termos)} termos")

docs_cat = defaultdict(set)
chunks_men = Counter()
especies_men = defaultdict(set)
for p in pans:
    docs_cat[p["categoria"]].add(p["documento"])
    achados = set(RE_SALVE.findall(norm(p["texto"])))
    if achados:
        chunks_men[p["categoria"]] += 1
        especies_men[p["categoria"]].update(termos[t] for t in achados)


def grupo_pan(cat: str) -> str:
    if cat == "pan-tartarugas-marinhas":
        return "tartarugas_marinhas"
    if cat in PANS_HERPETO:
        return "herpetofauna"
    if cat in PANS_TERRITORIAIS:
        return "territorial"
    return "outro_taxon"


print("\n2.1 PANs territoriais (11): evidência de espécie-alvo de herpetofauna")
print("   chunks docs | fichas SALVE que citam o PAN | chunks do PAN c/ espécie SALVE (espécies distintas) | PAN")
resultado_territorial = {}
for cat in sorted(PANS_TERRITORIAIS):
    e1, e2, esp = len(fichas_por_pan[cat]), chunks_men[cat], len(especies_men[cat])
    situacao = "ENTRA" if e1 else ("A CONFIRMAR" if e2 else "FORA")
    resultado_territorial[cat] = situacao
    print(f"   {tot_cat[cat]:5d} {len(docs_cat[cat]):4d} | {e1:3d} | {e2:4d} ({esp:3d}) | {cat} -> {situacao}")
    if e1:
        print(f"        fichas: {', '.join(sorted(fichas_por_pan[cat]))}")
for situacao in ("ENTRA", "A CONFIRMAR", "FORA"):
    cats = [c for c, s in resultado_territorial.items() if s == situacao]
    print(f"   {situacao}: {len(cats)} PANs, {sum(tot_cat[c] for c in cats)} chunks")

print("\n2.2 PANs de outros táxons: os que mais citam espécie do SALVE (para a equipe conferir a portaria)")
for cat, n in chunks_men.most_common():
    if grupo_pan(cat) == "outro_taxon" and n >= 5:
        print(f"   {n:4d} / {tot_cat[cat]:5d} chunks, {len(especies_men[cat]):3d} espécies  {cat}")

print("\n2.3 Totais por grupo de PAN")
tot_grupo = Counter()
n_grupo = Counter()
for cat, n in tot_cat.items():
    tot_grupo[grupo_pan(cat)] += n
    n_grupo[grupo_pan(cat)] += 1
for g in ("herpetofauna", "territorial", "tartarugas_marinhas", "outro_taxon"):
    print(f"   {g:20s} {n_grupo[g]:3d} PANs  {tot_grupo[g]:6d} chunks")

print("\n2.4 Documentos de herpetofauna arquivados na categoria de outro PAN (saem pela regra por PAN)")
for cat, doc in (
    ("pan-peixe-boi-marinho", "2024-pan-peixe-boi-marinho-estudo-tecnico-criacao-arie-tartarugas.pdf"),
    ("pan-peixes-e-eglas-da-ma", "2024-pan-herpetofauna-do-nordeste-acao-1-2-criacao-corredores-ecologicos.pdf"),
):
    print(f"   {tot_doc[cat][doc]:4d} chunks ({men_doc[cat][doc]} com tartaruga marinha)  {cat} | {doc}")

# --------------------------------------------------------------------------
# 3. Monitora: subprograma, componente e alvo por documento
# --------------------------------------------------------------------------
secao("3. MONITORA — CLASSIFICAÇÃO AUTOMÁTICA POR DOCUMENTO")

SUBPROGRAMAS = {
    "marinho_costeiro": r"marinho[\s-]+(?:e[\s-]+)?costeiro",
    "aquatico_continental": r"aquatico[\s-]+continental",
    # "florestal" sozinho pega "manejo florestal" e "Código Florestal"; exige o
    # nome do componente.
    "terrestre_florestal": r"componente[\s-]+florestal",
    "terrestre_campestre_savanico": r"campestre[\s-]+(?:e[\s-]+)?savanic",
}
# O nome do arquivo, quando diz o subprograma ou o alvo, vale mais que a
# contagem no texto.
NOME_SUBPROGRAMA = {
    "marinho_costeiro": r"marinh|costeir|recifal|manguezal|pesca",
    "aquatico_continental": r"aquatico|igarape|pirarucu|quelonio",
    "terrestre_florestal": r"florestal",
    "terrestre_campestre_savanico": r"campestre|savnico|savanico",
}
NOME_OUTRO_ALVO = r"borboleta|aves|mamifero|plantas|formasdevida|castanha|caa"
RE_HERP = re.compile(r"anfibi|anuro|lagarto|queloni|reptei|reptil|jacare|crocodil|serpente|tracaja|herpetofauna")
RE_OUTROS = re.compile(
    r"borboleta|\baves?\b|mamifero|\bpesca|pescador|pescado|\bpeixe|ictio|pirarucu|planta|vegeta|arbore"
    r"|odonata|libelula|recife|manguezal|caranguejo|coral"
)
INSTRUCOES_GERAIS = {"legislacao", "estrutura-do-programa"}

docs = defaultdict(lambda: {"n": 0, "herp": 0, "outros": 0, **{k: 0 for k in SUBPROGRAMAS}})
for p in monitora:
    d = docs[(p["categoria"], p["documento"])]
    d["nome"] = norm(p["documento"])
    d["n"] += 1
    texto = norm(p["texto"])
    d["herp"] += len(RE_HERP.findall(texto))
    d["outros"] += len(RE_OUTROS.findall(texto))
    for nome, regex in SUBPROGRAMAS.items():
        d[nome] += len(re.findall(regex, texto))


def classificar(categoria: str, d: dict) -> tuple[str, str]:
    """(situação, motivo). Limiar: o subprograma domina com >= 3 menções e
    >= 60% das menções a subprograma; o alvo é herpetofauna com >= 10 menções
    e >= 50% das menções a alvo."""
    if categoria in INSTRUCOES_GERAIS:
        return "Entra", "instruções gerais (legislação/estrutura do programa)"
    total_sub = sum(d[k] for k in SUBPROGRAMAS)
    dominante = max(SUBPROGRAMAS, key=lambda k: d[k])
    tem_sub = d[dominante] >= 3 and d[dominante] / total_sub >= 0.6
    pelo_nome = [k for k, regex in NOME_SUBPROGRAMA.items() if re.search(regex, d["nome"])]
    if len(pelo_nome) == 1:
        dominante, tem_sub = pelo_nome[0], True
    total_alvo = d["herp"] + d["outros"]
    alvo_herp = d["herp"] >= 10 and d["herp"] / total_alvo >= 0.5
    alvo_outro = d["outros"] >= 10 and d["herp"] / total_alvo < 0.1
    if alvo_herp:
        if tem_sub and dominante == "terrestre_florestal":
            return "Fora por enquanto", "alvo herpetofauna, componente Florestal"
        return "Entra", "alvo herpetofauna" + (f", {dominante}" if tem_sub else ", subprograma não identificado")
    if tem_sub and dominante == "marinho_costeiro":
        return "Fora", "subprograma Marinho e Costeiro"
    if tem_sub and dominante == "terrestre_florestal":
        return "Fora por enquanto", "componente Florestal"
    if tem_sub:
        return "A definir", f"{dominante}, alvo misto ou de outro grupo"
    if alvo_outro or re.search(NOME_OUTRO_ALVO, d["nome"]):
        return "Fora", "alvo de outro grupo, sem subprograma identificado"
    return "Não classificável", "sem sinal suficiente de subprograma nem de alvo"


situacoes = defaultdict(list)
for (categoria, doc), d in sorted(docs.items()):
    situacao, motivo = classificar(categoria, d)
    situacoes[situacao].append((categoria, doc, d["n"], motivo))
print(f"documentos: {len(docs)} (pares categoria/arquivo); chunks: {len(monitora)}")
for situacao in ("Entra", "Fora", "Fora por enquanto", "A definir", "Não classificável"):
    itens = situacoes[situacao]
    print(f"\n   {situacao}: {len(itens)} documentos, {sum(i[2] for i in itens)} chunks")
    for categoria, doc, n, motivo in itens:
        print(f"      {n:4d}  {categoria} | {doc[:70]}  [{motivo}]")

# --------------------------------------------------------------------------
# 4. Resumo
# --------------------------------------------------------------------------
secao("4. RESUMO (chunks do índice atual)")
salve_in = len(salve) - sum(fichas_tmar.values())
pans_herp = tot_grupo["herpetofauna"]
pans_terr_in = sum(tot_cat[c] for c, s in resultado_territorial.items() if s == "ENTRA")
pans_terr_conf = sum(tot_cat[c] for c, s in resultado_territorial.items() if s == "A CONFIRMAR")
mon_in = sum(i[2] for i in situacoes["Entra"])
mon_indef = sum(i[2] for s in ("A definir", "Não classificável") for i in situacoes[s])
total = len(salve) + len(pans) + len(monitora)
dentro = salve_in + pans_herp + pans_terr_in + mon_in
print(f"   SALVE em escopo:                 {salve_in}")
print(f"   PANs de herpetofauna:            {pans_herp}")
print(f"   PANs territoriais que entram:    {pans_terr_in}  (a confirmar: {pans_terr_conf})")
print(f"   Monitora que entra:              {mon_in}  (a definir/não classificável: {mon_indef})")
print(f"   em escopo (piso):                {dentro} de {total} ({dentro / total:.1%})")
print(f"   teto, se tudo o que está em aberto entrar: {dentro + pans_terr_conf + mon_indef} "
      f"({(dentro + pans_terr_conf + mon_indef) / total:.1%})")

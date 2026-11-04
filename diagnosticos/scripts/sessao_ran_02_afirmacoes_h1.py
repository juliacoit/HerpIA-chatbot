"""Diagnóstico descartável (sessão RAN 26/10/2026) — H1.

Para cada interação, classifica as afirmações factuais "verificáveis por
string" da resposta (anos, siglas de categoria, critérios IUCN, itens de
lista e nomes próprios listados à mão abaixo) em:
  citado      — aparece no texto de alguma citação exibida (interacoes.citacoes)
  contexto    — não aparece nas citações, mas aparece em algum chunk do prompt
  ausente     — não aparece em nenhum chunk do prompt nem na pergunta
O contexto vem da reprodução (sessao_ran_01), validada contra o log.
"""

import json
import re
import unicodedata

from sessao_ran_comum import CACHE, consultar_pg, payloads, rotulo

NOMES_EXTRAS = {
    786: ["2014", "Bernardes", "quase ameaçada", "NT"],
    787: ["Jabuti", "A4cd", "A1cd+2cd", "dados insuficientes"],
    788: ["Jabuti-açu", "duas reservas", "70%", "A4cd", "2024"],
    790: ["TTWG", "Turtles of the World", "Chelonian Research Monographs", "terceira edição",
          "Comissão de Taxonomia", "Working Group", "2014"],
    791: ["bolsista", "GEF Terrestre", "Analista ambiental", "Doutora em Ciências Ambientais"],
    797: ["municípios", "municipais"],
}


def norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", t.lower())
    return re.sub(r"\s+", " ", "".join(c for c in t if not unicodedata.combining(c)))


def afirmacoes(iid: int, resposta: str) -> list[str]:
    itens = set(re.findall(r"\b(?:19|20)\d{2}\b", resposta))
    itens |= set(re.findall(r"\b(?:LC|NT|VU|EN|CR|DD|EW|EX|NA)\b", resposta))
    itens |= set(re.findall(r"\b[AB-E]\d[a-e]+(?:\+\d[a-e]+)*\b", resposta))
    for linha in resposta.splitlines():
        linha = linha.strip(" -•*\t")
        if 3 < len(linha) < 80 and re.match(r"^[A-ZÁÉÍÓÚ]{2,}", linha):
            itens.add(linha)
    itens |= set(NOMES_EXTRAS.get(iid, []))
    return sorted(itens)


ctx = json.loads((CACHE / "contextos_sessao.json").read_text())
ps = payloads()
db = {r["id"]: r for r in consultar_pg("select id, citacoes from interacoes where id between 786 and 801")}
resumo = {}
for iid_s, c in ctx.items():
    iid = int(iid_s)
    texto_citado = norm(" ".join(x.get("texto") or "" for x in db[iid]["citacoes"]))
    textos_ctx = [norm(ps[i]["texto"]) for i in c["contexto"]]
    pergunta = norm(c["pergunta"])
    linhas = []
    cont = {"citado": 0, "contexto": 0, "ausente": 0}
    for a in afirmacoes(iid, c["resposta"]):
        an = norm(a)
        if not re.search(r"\w", an):
            continue
        pad = re.compile(r"(?<!\w)" + re.escape(an) + r"(?!\w)")
        if pad.search(texto_citado):
            cls = "citado"
        elif any(pad.search(t) for t in textos_ctx):
            onde = [n + 1 for n, t in enumerate(textos_ctx) if pad.search(t)]
            cls = "contexto"
            a = f"{a}  (trecho(s) {onde})"
        elif pad.search(pergunta):
            cls = "citado"
            a = f"{a}  (eco da pergunta)"
        else:
            cls = "ausente"
        cont[cls] += 1
        linhas.append(f"   {cls:9s} {a}")
    resumo[iid] = cont
    print(f"#{iid}  citações exibidas={len(db[iid]['citacoes'])} chunks no prompt={len(c['contexto'])}  {cont}")
    for i, idx in enumerate(c["contexto"], 1):
        print(f"     [T{i}] {rotulo(idx)}")
    print("\n".join(linhas))
(CACHE / "h1_resumo.json").write_text(json.dumps(resumo))

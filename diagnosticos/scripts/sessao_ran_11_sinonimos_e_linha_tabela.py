"""Diagnóstico descartável (sessão RAN 26/10/2026) — H3 (#796) e H5 (#799).

1. Quantas fichas SALVE trazem "Sinonímias:" na seção taxonomia (base para
   uma tabela de sinônimos extraída do próprio índice, sem dado externo) e
   quantos nomes comuns são ambíguos (mesmo nome em mais de uma ficha).
2. Estimativa offline do efeito de serializar a tabela do Monitora linha a
   linha: embeda a linha "Paisagem Sonora" (e a de lagartos) como se fosse
   um chunk próprio e compara o score com o 5º colocado de cada pergunta.
   Nada é indexado: é só um produto interno em memória.
"""

import re
from collections import defaultdict

from sessao_ran_comum import embed, payloads, ranking

ps = payloads()
fichas_sin, n_sin = set(), 0
for p in ps:
    if p["fonte"] == "salve" and p["secao"] == "taxonomia":
        m = re.search(r"Sinonímias:\s*(.+)", p["texto"])
        if m:
            fichas_sin.add(p["documento"])
            n_sin += len([s for s in m.group(1).split(",") if s.strip()])
total = len({p["documento"] for p in ps if p["fonte"] == "salve"})
print(f"fichas com 'Sinonímias:': {len(fichas_sin)} de {total}; sinônimos listados: {n_sin}")

nome_para_fichas = defaultdict(set)
for p in ps:
    if p["fonte"] == "salve" and p.get("nome_comum"):
        for nome in re.split(r",\s*", p["nome_comum"]):
            nome = re.sub(r"\s*\(.*?\)", "", nome).strip().lower()
            if nome:
                nome_para_fichas[nome].add(p["documento"])
amb = {k: v for k, v in nome_para_fichas.items() if len(v) > 1}
print(f"nomes comuns distintos: {len(nome_para_fichas)}; ambíguos (>1 ficha): {len(amb)}")
for k in ["tracajá", "jabuti", "cururu", "jararaca"]:
    print(f"  '{k}' -> {sorted(nome_para_fichas.get(k, []))}")

LINHAS = {
    "Paisagem Sonora": "Programa Monitora — subprograma Terrestre, componente Campestre e Savânico, alvo complementar "
                       "Paisagem Sonora: Protocolo avançado de monitoramento do alvo complementar paisagem acústica do "
                       "componente Campestre e Savânico. Centro: CEMAVE. Situação: Em fase de testes para validação do protocolo.",
    "Lagartos Terrestres": "Programa Monitora — subprograma Terrestre, componente Campestre e Savânico, alvo complementar "
                           "Lagartos Terrestres: Protocolo básico de monitoramento do alvo complementar lagartos terrestres do "
                           "componente Campestre e Savânico. Centro: RAN. Obs.: Existem dois protocolos em teste: lagartos em "
                           "geral e do gênero Liolemus em ambientes de dunas. Situação: Em fase de testes para validação do protocolo.",
}
vets = dict(zip(LINHAS, embed(list(LINHAS.values()))))
for pergunta, alvo in [
    ("existe um protocolo de monitoramento bioacústico no âmbito do programa monitora?", "Paisagem Sonora"),
    ("existe um protocolo de monitoramento de paisagem sonora no âmbito do programa monitora?", "Paisagem Sonora"),
    ("Tem algum protocolo de monitoramento sobre lagartos?", "Lagartos Terrestres"),
    ("quais são os protocolos de monitoramento de alvos complementares de répteis e anfíbios do programa monitora?", "Lagartos Terrestres"),
]:
    q = embed([pergunta])[0]
    rk = ranking(pergunta, vetor=q)
    s = float(vets[alvo] @ q)
    pos = sum(1 for _, _, sc in rk if sc > s) + 1
    print(f"\nP: {pergunta}\n   linha '{alvo}' isolada: score {s:.4f} -> entraria na posição {pos} (5º atual: {rk[4][2]:.4f})")

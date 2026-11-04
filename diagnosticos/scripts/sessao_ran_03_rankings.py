"""Diagnóstico descartável (sessão RAN 26/10/2026) — H3, H4 (#798) e H5.

Para cada pergunta (original da sessão + variações), mostra em que posição
do ranking (mesmo filtro da interface: monitora+pans+salve, autorizado)
aparece o chunk/documento que deveria ter sido recuperado. Também roda com
fontes=["salve"] quando o alvo é uma ficha, para separar "a ficha não é
semanticamente próxima" de "a ficha perde para PDFs".
"""

import re

from sessao_ran_comum import payloads, ranking, rotulo

ps = payloads()


def doc(prefixo, secao=None, contem=None):
    def f(p):
        if not (p.get("documento") or "").startswith(prefixo):
            return False
        if secao and (p.get("secao") or p.get("categoria")) != secao:
            return False
        return not contem or re.search(contem, p["texto"], re.I) is not None
    return f


CASOS = [
    ("H3 #786 tracajá", [
        "Quando foi a última avaliação do risco de extinção da Tracajá",
        "Quando foi a última avaliação do risco de extinção do tracajá (Podocnemis unifilis)?",
        "Quando foi a última avaliação do risco de extinção de Podocnemis unifilis",
        "tracajá",
     ], {"P. unifilis (qualquer chunk)": doc("Podocnemis unifilis"),
         "P. unifilis conservação c/ Histórico": doc("Podocnemis unifilis", "conservacao", "Histórico de avaliação")},
     True),
    ("H3 #787/#788 jabutis", [
        "Quando foi, e qual o resultado da avaliação mais recente do estado de conservação ou risco de extinção dos jabutis",
        "Quando foi, e qual o resultado da avaliação mais recente do estado de conservação ou risco de extinção das duas espécies de Jabutis que ocorrem no Brasil?",
        "Quais são as duas espécies de jabutis que ocorrem no BRasil",
     ], {"C. carbonarius (qualquer)": doc("Chelonoidis carbonarius"),
         "C. carbonarius conservação c/ Histórico": doc("Chelonoidis carbonarius", "conservacao", "Histórico de avaliação"),
         "C. denticulatus conservação c/ Histórico": doc("Chelonoidis denticulatus", "conservacao", "Histórico de avaliação")},
     True),
    ("H3 #790 seção", [
        "Quando foi a avaliação do risco de extinção mais recente da espécie Chelonoidis carbonarius",
     ], {"C. carbonarius conservação c/ Histórico": doc("Chelonoidis carbonarius", "conservacao", "Histórico de avaliação"),
         "C. carbonarius conservação (qualquer parte)": doc("Chelonoidis carbonarius", "conservacao")},
     True),
    ("H3 #796 sinonímia", [
        "em quais municipios e unidades de conservação ocorre a espécie bufo schneider",
        "em quais municipios e unidades de conservação ocorre a espécie Bufo schneideri",
        "em quais municipios e unidades de conservação ocorre a espécie Rhinella schneideri",
        "em quais municipios e unidades de conservação ocorre a espécie Rhinella diptycha, e qual seu status de conservação?",
     ], {"R. diptycha (qualquer)": doc("Rhinella diptycha"),
         "R. diptycha taxonomia (sinonímias)": doc("Rhinella diptycha", "taxonomia"),
         "R. diptycha conservação (UCs)": doc("Rhinella diptycha", "conservacao")},
     True),
    ("H4 #798 boilerplate", [
        "quais são os protocolos de monitoramento de alvos complementares de répteis e anfíbios do programa monitora?",
        "Tem algum protocolo de monitoramento sobre lagartos?",
     ], {"INTRANETEstrutura (qualquer)": doc("INTRANETEstrutura_Alvos_Protocolos"),
         "INTRANETEstrutura c/ 'Lagartos Terrestres'": doc("INTRANETEstrutura_Alvos_Protocolos", contem="Lagartos Terrestres")},
     False),
    ("H5 #799 bioacústica", [
        "existe um protocolo de monitoramento bioacústico no âmbito do programa monitora?",
        "existe um protocolo de monitoramento de paisagem acústica no âmbito do programa monitora?",
        "existe um protocolo de monitoramento de paisagem sonora no âmbito do programa monitora?",
        "monitoramento acústico passivo com gravadores automáticos no Programa Monitora",
     ], {"INTRANETEstrutura c/ 'Paisagem Sonora'": doc("INTRANETEstrutura_Alvos_Protocolos", contem="Paisagem Sonora"),
         "qualquer chunk c/ 'paisagem (sonora|acústica)'": lambda p: re.search(r"paisagem (sonora|ac[uú]stica)", p["texto"], re.I) is not None},
     False),
]

for titulo, perguntas, alvos, testar_salve in CASOS:
    print("=" * 100, "\n" + titulo)
    for pergunta in perguntas:
        print(f"\n  P: {pergunta}")
        for fontes in [("monitora", "pans", "salve")] + ([("salve",)] if testar_salve else []):
            rk = ranking(pergunta, fontes)
            print(f"    fontes={'+'.join(fontes)}  top-5:")
            for pos, idx, s in rk[:5]:
                print(f"      {pos:>3} {s:.4f} {rotulo(idx)[:120]}")
            for nome, pred in alvos.items():
                hits = [(pos, idx, s) for pos, idx, s in rk if pred(ps[idx])]
                if hits:
                    pos, idx, s = hits[0]
                    print(f"      -> {nome}: 1ª posição {pos} (score {s:.4f}, Δ p/ 5º = {rk[4][2]-s:+.4f}) [{len(hits)} chunks]")
                else:
                    print(f"      -> {nome}: não existe no índice com esse filtro")

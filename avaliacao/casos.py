"""Casos da avaliação offline com RAGAS (ADR 0007).

`avaliacao/casos.jsonl` só guarda o que a bateria de domínio não tem: o
gabarito (`reference`), a fonte esperada da recuperação (`fonte_esperada`),
a decisão esperada do gate do SALVE (`rota_esperada`), uma falha já
conhecida (`falha_conhecida`) e, opcionalmente, `top_k` e `fontes`. Ver
avaliacao/README.md e avaliacao/rota.py. A pergunta e a categoria vêm de
`CASOS_TESTE` em scripts/teste_perguntas_dominio.py, para não haver duas
cópias da bateria. Importar esse script não tem efeito colateral além de
acrescentar a raiz do repositório ao sys.path (verificado em
diagnosticos/ragas_fase0.md, "Decisões", item 3).

`reference` nunca é escrito por quem desenvolve: vem da equipe técnica do
RAN. Enquanto não vier, fica PENDENTE_VALIDACAO_RAN, e o caso pula as
métricas que dependem de gabarito.
"""

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ARQUIVO_CASOS = RAIZ / "avaliacao" / "casos.jsonl"
REFERENCIA_PENDENTE = "PENDENTE_VALIDACAO_RAN"
FONTES_VALIDAS = {"monitora", "pans", "salve"}
ROTAS_VALIDAS = {"salve", "nenhuma"}
CAMPOS_PERMITIDOS = {"id", "reference", "fonte_esperada", "rota_esperada", "falha_conhecida", "top_k", "fontes"}

sys.path.insert(0, str(RAIZ / "scripts"))
from teste_perguntas_dominio import CASOS_TESTE  # noqa: E402


def carregar_casos(caminho: Path = ARQUIVO_CASOS) -> list[dict]:
    """Junta cada linha do JSONL com o caso da bateria de mesmo `id`, na
    ordem do JSONL. Levanta ValueError se uma linha for inválida."""
    bateria = {c["id"]: c for c in CASOS_TESTE}
    casos = []
    vistos = set()
    for n, linha in enumerate(caminho.read_text(encoding="utf-8").splitlines(), start=1):
        if not linha.strip():
            continue
        dados = json.loads(linha)
        local = f"{caminho.name}:{n}"
        extras = set(dados) - CAMPOS_PERMITIDOS
        if extras:
            raise ValueError(f"{local}: campos desconhecidos {sorted(extras)}")
        id_caso = dados.get("id")
        if id_caso not in bateria:
            raise ValueError(f"{local}: id {id_caso!r} não existe em CASOS_TESTE")
        if id_caso in vistos:
            raise ValueError(f"{local}: id {id_caso!r} repetido")
        vistos.add(id_caso)
        referencia = dados.get("reference")
        if not isinstance(referencia, str) or not referencia.strip():
            raise ValueError(f"{local}: reference vazio (use {REFERENCIA_PENDENTE})")
        fonte = dados.get("fonte_esperada")
        if fonte is not None and fonte not in FONTES_VALIDAS:
            raise ValueError(f"{local}: fonte_esperada {fonte!r} fora de {sorted(FONTES_VALIDAS)}")
        rota = dados.get("rota_esperada")
        if rota is not None and rota not in ROTAS_VALIDAS:
            raise ValueError(f"{local}: rota_esperada {rota!r} fora de {sorted(ROTAS_VALIDAS)} (ou omita)")
        falha = dados.get("falha_conhecida")
        if falha is not None and not (isinstance(falha, str) and falha.strip()):
            raise ValueError(f"{local}: falha_conhecida deve ser um texto não vazio")
        top_k = dados.get("top_k")
        if top_k is not None and not (isinstance(top_k, int) and 1 <= top_k <= 20):
            raise ValueError(f"{local}: top_k deve ser inteiro de 1 a 20")
        fontes = dados.get("fontes")
        if fontes is not None and not (isinstance(fontes, list) and set(fontes) <= FONTES_VALIDAS):
            raise ValueError(f"{local}: fontes deve ser lista dentro de {sorted(FONTES_VALIDAS)}")

        caso_bateria = bateria[id_caso]
        casos.append({
            "id": id_caso,
            "categoria": id_caso[0],
            "user_input": caso_bateria["pergunta"],
            "reference": referencia,
            "tem_referencia": referencia != REFERENCIA_PENDENTE,
            "fonte_esperada": fonte,
            "rota_esperada": rota,  # None = indiferente (não checar a decisão)
            "falha_conhecida": falha,
            "top_k": top_k,     # None = o padrão do script (5, o mesmo do frontend)
            "fontes": fontes,
        })
    return casos

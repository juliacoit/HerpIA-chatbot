"""Diagnóstico descartável (sessão RAN 26/10/2026) — H2/H6.

Reaplica OFFLINE as camadas determinísticas do verificador
(backend/services/groundedness.py: camada 1 hard gate, camada 0 abstenção
pura, camada 2 pistas de meio de frase) às 16 respostas exibidas, com o
contexto reproduzido. Não chama o juiz por LLM (camada 3). Para respostas
exibidas como "Fundamentada" que não são abstenção pura, a aprovação veio
necessariamente do juiz por LLM.
"""

import json

from backend.schemas import ChunkRecuperado
from backend.services.groundedness import (
    checar_abstencao_pura,
    checar_ancoras_estruturais,
    checar_ancoras_meio_frase,
)
from sessao_ran_comum import CACHE, payloads

ps = payloads()
ctx = json.loads((CACHE / "contextos_sessao.json").read_text())
for iid, c in ctx.items():
    chunks = [ChunkRecuperado(score=s, fonte=ps[i]["fonte"], documento=ps[i]["documento"], texto=ps[i]["texto"])
              for i, s in zip(c["contexto"], c["scores"])]
    if not c["fundamentada"]:
        print(f"#{iid}: retida no pipeline — {c['justificativa'][:160]}")
        continue
    ok1, sem1 = checar_ancoras_estruturais(c["resposta"], chunks, c["pergunta"])
    pura = checar_abstencao_pura(c["resposta"])
    _, pistas = checar_ancoras_meio_frase(c["resposta"], chunks, c["pergunta"])
    decidiu = "camada 0 (abstenção pura, sem juiz)" if pura else "camada 3 (juiz LLM disse SIM)"
    print(f"#{iid}: camada1_ok={ok1} {sem1 or ''} | decidiu: {decidiu} | pistas camada 2 enviadas ao juiz: {pistas}")

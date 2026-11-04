"""Diagnóstico descartável (sessão supervisionada RAN, 26/10/2026).

Exporta, SÓ PARA LEITURA, payloads e vetores do Qdrant embutido
(QDRANT_LOCAL_PATH) para um cache fora do repositório, para as análises de
ranking/duplicatas rodarem sem reabrir o Qdrant a cada consulta. Nenhuma
escrita no Qdrant: só `scroll`.

Uso: python diagnosticos/scripts/sessao_ran_00_exportar_indice.py <dir_saida>
Saída: <dir_saida>/payloads.jsonl (sem vetor) e <dir_saida>/vetores.npy
(mesma ordem), mais ids.json.
"""

import json
import sys
from pathlib import Path

import numpy as np

from backend.config import obter_settings
from backend.services.retrieval import conectar_qdrant

saida = Path(sys.argv[1])
saida.mkdir(parents=True, exist_ok=True)
settings = obter_settings()
client = conectar_qdrant(settings)

ids, vetores = [], []
offset = None
with open(saida / "payloads.jsonl", "w", encoding="utf-8") as f:
    while True:
        pontos, offset = client.scroll(
            settings.qdrant_collection, limit=2000, offset=offset, with_payload=True, with_vectors=True
        )
        for p in pontos:
            ids.append(str(p.id))
            vetores.append(np.asarray(p.vector, dtype=np.float32))
            f.write(json.dumps(p.payload, ensure_ascii=False) + "\n")
        if offset is None:
            break
np.save(saida / "vetores.npy", np.vstack(vetores))
(saida / "ids.json").write_text(json.dumps(ids))
print(f"{len(ids)} pontos exportados para {saida}")
client.close()

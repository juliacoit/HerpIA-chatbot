"""Prova de que a Parte 1 (citações/estados/logging) não muda retrieval nem
geração: para as perguntas #786–#801, grava os chunks que iriam ao LLM
(via `buscar_chunks_priorizados`, o mesmo caminho do /perguntar) e o hash
do prompt montado por `montar_prompt`. Roda uma vez no commit base e outra
depois das mudanças; os dois JSON têm de ser idênticos.

Não chama o LLM. Abre o Qdrant embutido só para consulta (exige o backend
parado, por causa da trava do modo arquivo). Lê as perguntas do PostgreSQL
em modo read_only.

Uso: python diagnosticos/scripts/prova_geracao_inalterada.py <saida.json>
"""

import hashlib
import json
import sys

import psycopg

from backend.config import obter_settings
from backend.services.geracao import montar_prompt
from backend.services.retrieval import carregar_modelo_embedding, conectar_qdrant
from backend.services.roteamento import buscar_chunks_priorizados

FONTES_INTERFACE = ["monitora", "pans", "salve"]

settings = obter_settings()
with psycopg.connect(settings.database_url) as conn:
    conn.read_only = True
    linhas = conn.execute(
        "select id, pergunta, top_k from interacoes where id between 786 and 801 order by id"
    ).fetchall()

client = conectar_qdrant(settings)
modelo = carregar_modelo_embedding()
saida = {}
for iid, pergunta, top_k in linhas:
    for rotulo, fontes in (("interface", FONTES_INTERFACE), ("sem_fontes", None)):
        chunks = buscar_chunks_priorizados(client, modelo, settings, pergunta, top_k, fontes)
        prompt = montar_prompt(pergunta, chunks)
        saida[f"{iid}/{rotulo}"] = {
            "chunks": [
                [c.fonte, c.documento, c.secao, c.pagina_inicio, c.pagina_fim, round(c.score, 6),
                 hashlib.sha1(c.texto.encode()).hexdigest()]
                for c in chunks
            ],
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "prompt_chars": len(prompt),
        }
client.close()
with open(sys.argv[1], "w", encoding="utf-8") as f:
    json.dump(saida, f, ensure_ascii=False, indent=1, sort_keys=True)
print(f"{len(saida)} combinações gravadas em {sys.argv[1]}")

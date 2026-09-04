"""Migração pontual: normaliza o campo `bioma` já indexado no Qdrant de
string ("Amazônia, Cerrado, Pantanal") para lista (["Amazônia", "Cerrado",
"Pantanal"]) — só payload, sem reencodar embeddings.

Contexto (ver diagnosticos/agregacao-biomas-fichas-salve.md): perguntas de
"espécies por bioma" filtravam mal porque o LLM tinha que inferir do texto
corrido se uma ficha cobria o bioma perguntado. `gerar_chunks.py` já foi
corrigido para gravar `bioma` como lista a partir de agora
(normalizar_biomas), o que habilita um filtro de payload determinístico
(FieldCondition + MatchAny, mesmo padrão de `nivel_sensibilidade`) em
`backend/services/retrieval.py` — mas os ~20 mil chunks do SALVE já
indexados em 2026-08-10 ainda têm o campo antigo (string). Reencodar tudo de
novo com BGE-M3 seria caro e desnecessário: o texto do chunk (o que é
embedado) não mudou, só um campo de metadado — `client.set_payload` atualiza
só os campos passados, sem tocar no vetor.

Idempotente: rodar de novo sobre pontos já migrados (bioma já é lista) não
quebra nada, `normalizar_biomas` aceita string ou lista.

Uso:
    python scripts/indexacao/migrar_payload_bioma.py
    python scripts/indexacao/migrar_payload_bioma.py --dry-run
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from tqdm import tqdm

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts" / "processamento"))
from gerar_chunks import normalizar_biomas  # noqa: E402

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_LOCAL_PATH = os.getenv("QDRANT_LOCAL_PATH")
COLECAO = os.getenv("QDRANT_COLLECTION", "ran_herpetofauna")
TAMANHO_LOTE = 256


def conectar_qdrant():
    from qdrant_client import QdrantClient

    if QDRANT_LOCAL_PATH:
        caminho = Path(QDRANT_LOCAL_PATH)
        if not caminho.is_absolute():
            caminho = RAIZ / caminho
        print(f"Usando Qdrant embutido (local) em {caminho}")
        return QdrantClient(path=str(caminho))
    return QdrantClient(url=QDRANT_URL)


def migrar(client, dry_run: bool) -> dict:
    from qdrant_client.models import FieldCondition, Filter, MatchValue

    relatorio = {"revisados": 0, "atualizados": 0, "ja_lista": 0}
    offset = None
    barra = tqdm(desc="[salve] migrando bioma", unit="chunk")

    while True:
        pontos, offset = client.scroll(
            collection_name=COLECAO,
            scroll_filter=Filter(must=[FieldCondition(key="fonte", match=MatchValue(value="salve"))]),
            limit=TAMANHO_LOTE,
            offset=offset,
            with_payload=["bioma"],
            with_vectors=False,
        )
        if not pontos:
            break

        for ponto in pontos:
            relatorio["revisados"] += 1
            bioma_atual = (ponto.payload or {}).get("bioma")
            if isinstance(bioma_atual, list):
                relatorio["ja_lista"] += 1
                continue
            nova_lista = normalizar_biomas(bioma_atual)
            relatorio["atualizados"] += 1
            if not dry_run:
                client.set_payload(
                    collection_name=COLECAO,
                    payload={"bioma": nova_lista},
                    points=[ponto.id],
                )
        barra.update(len(pontos))

        if offset is None:
            break
    barra.close()
    return relatorio


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="Só conta, não escreve no Qdrant")
    args = parser.parse_args()

    client = conectar_qdrant()
    relatorio = migrar(client, dry_run=args.dry_run)

    modo = "DRY RUN — nada escrito" if args.dry_run else "CONCLUÍDO"
    print(
        f"\n{modo} — {relatorio['revisados']} chunks salve revisados, "
        f"{relatorio['atualizados']} atualizados, "
        f"{relatorio['ja_lista']} já estavam em formato de lista."
    )


if __name__ == "__main__":
    main()

"""Reindexa só o que mudou numa fonte depois de um novo chunking.

`indexar_chunks.py --fonte X` reencoda todos os chunks da fonte. Quando o
chunking muda poucos documentos (ex.: o ADR 0009, que deixou de remover
coordenadas em 30 documentos de Monitora e PANs), quase todo vetor seria
recalculado para o mesmo texto. Este script compara o `chunks.jsonl` com o
que está no Qdrant e faz só o necessário:

  - texto novo ou alterado  -> gera o embedding e grava o ponto (upsert);
  - só metadado alterado    -> regrava o payload, sem tocar no vetor;
  - ponto sem chunk         -> apaga (órfão: o documento passou a ter menos
                               chunks, e `indexar_chunks.py` não remove esses).

O resultado é o mesmo de reindexar a fonte inteira e apagar os órfãos.

Uso (backend parado, por causa da trava do Qdrant embutido):
    python scripts/indexacao/reindexar_alterados.py --fonte pans --dry-run
    python scripts/indexacao/reindexar_alterados.py --fonte pans
    python scripts/indexacao/reindexar_alterados.py --fonte pans --conferir

`--dry-run` só mostra as contagens. `--conferir` não grava: verifica se todo
ponto da fonte tem payload idêntico ao chunk e se não sobra órfão.
"""

import argparse
import sys
import uuid

from indexar_chunks import (
    COLECAO,
    NAMESPACE_CHUNK_ID,
    TAMANHO_LOTE,
    carregar_modelo,
    conectar_qdrant,
    ler_chunks,
)

FONTES = ["monitora", "pans", "salve"]


def id_do_ponto(chunk_id: str) -> str:
    return str(uuid.uuid5(NAMESPACE_CHUNK_ID, chunk_id))


def payloads_no_qdrant(client, fonte: str) -> dict[str, dict]:
    """{id do ponto: payload} de todos os pontos da fonte, sem os vetores."""
    from qdrant_client.models import FieldCondition, Filter, MatchValue

    filtro = Filter(must=[FieldCondition(key="fonte", match=MatchValue(value=fonte))])
    pontos: dict[str, dict] = {}
    proximo = None
    while True:
        lote, proximo = client.scroll(
            collection_name=COLECAO, scroll_filter=filtro, limit=2000,
            offset=proximo, with_payload=True, with_vectors=False,
        )
        for ponto in lote:
            pontos[str(ponto.id)] = ponto.payload
        if proximo is None:
            return pontos


def comparar(client, fonte: str) -> tuple[list[dict], list[dict], list[str], int]:
    """(chunks a reencodar, chunks só com payload diferente, ids órfãos, total de chunks)."""
    atuais = payloads_no_qdrant(client, fonte)
    reencodar, so_payload, vistos = [], [], set()
    for chunk in ler_chunks(fonte):
        id_ = id_do_ponto(chunk["chunk_id"])
        vistos.add(id_)
        payload = atuais.get(id_)
        if payload is None or payload.get("texto") != chunk["texto"]:
            reencodar.append(chunk)
        elif payload != chunk:
            so_payload.append(chunk)
    orfaos = [id_ for id_ in atuais if id_ not in vistos]
    return reencodar, so_payload, orfaos, len(vistos)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--fonte", choices=FONTES, required=True)
    parser.add_argument("--dry-run", action="store_true", help="Só mostra o que mudaria")
    parser.add_argument("--conferir", action="store_true", help="Verifica se o Qdrant bate com o chunks.jsonl")
    args = parser.parse_args()

    client = conectar_qdrant()
    reencodar, so_payload, orfaos, total = comparar(client, args.fonte)
    print(f"[{args.fonte}] {total} chunks no arquivo | texto novo ou alterado: {len(reencodar)} | "
          f"só payload: {len(so_payload)} | órfãos no Qdrant: {len(orfaos)}")

    if args.conferir:
        ok = not (reencodar or so_payload or orfaos)
        print("  Qdrant idêntico ao chunks.jsonl." if ok else "  DIVERGE do chunks.jsonl.")
        sys.exit(0 if ok else 1)
    if args.dry_run:
        return

    from qdrant_client.models import PointIdsList, PointStruct

    if reencodar:
        modelo = carregar_modelo()
        for i in range(0, len(reencodar), TAMANHO_LOTE):
            lote = reencodar[i: i + TAMANHO_LOTE]
            vetores = modelo.encode(
                [c["texto"] for c in lote], batch_size=TAMANHO_LOTE,
                show_progress_bar=False, normalize_embeddings=True,
            )
            client.upsert(collection_name=COLECAO, points=[
                PointStruct(id=id_do_ponto(c["chunk_id"]), vector=v.tolist(), payload=c)
                for c, v in zip(lote, vetores)
            ])
            print(f"  reencodados {min(i + TAMANHO_LOTE, len(reencodar))}/{len(reencodar)}", flush=True)
    for chunk in so_payload:
        client.overwrite_payload(collection_name=COLECAO, payload=chunk, points=[id_do_ponto(chunk["chunk_id"])])
    if orfaos:
        client.delete(collection_name=COLECAO, points_selector=PointIdsList(points=orfaos))
    print(f"  [{args.fonte}] concluído: {len(reencodar)} reencodados, {len(so_payload)} payloads regravados, "
          f"{len(orfaos)} órfãos apagados.")


if __name__ == "__main__":
    main()

"""Smoke test do pipeline de indexação (Fase 5.3), em CPU, com poucos chunks.

Objetivo: validar o pipeline completo (carregar BGE-M3 -> gerar embeddings ->
upsert no Qdrant embutido -> busca) numa amostra pequena, antes de rodar a
indexação real com todos os ~59 mil chunks (mais viável depois que a GPU
voltar — em CPU, o modelo completo seria da ordem de várias horas).

Usa uma coleção Qdrant separada (sufixo "_smoketest"), isolada da coleção de
produção (QDRANT_COLLECTION) — não interfere com uma indexação real futura.

Uso:
    python scripts/indexacao/smoke_test_indexacao.py
    python scripts/indexacao/smoke_test_indexacao.py --fonte salve --n 10
    python scripts/indexacao/smoke_test_indexacao.py --manter-colecao   # não apaga ao final
"""

import argparse
import itertools
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from indexar_chunks import (  # noqa: E402
    COLECAO,
    NAMESPACE_CHUNK_ID,
    carregar_modelo,
    conectar_qdrant,
    ler_chunks,
)

COLECAO_TESTE = f"{COLECAO}_smoketest"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fonte", choices=["monitora", "pans", "salve"], default="monitora",
                        help="Fonte de onde ler a amostra (padrão: monitora, a menor)")
    parser.add_argument("--n", type=int, default=15, help="Número de chunks na amostra (padrão: 15)")
    parser.add_argument("--manter-colecao", action="store_true",
                        help="Não apaga a coleção de teste ao final (útil para inspecionar no dashboard/CLI)")
    args = parser.parse_args()

    import uuid
    from qdrant_client.models import Distance, PointStruct, VectorParams

    print(f"1. Lendo amostra de {args.n} chunks de '{args.fonte}'...")
    amostra = list(itertools.islice(ler_chunks(args.fonte), args.n))
    if not amostra:
        print(f"   Nenhum chunk encontrado em 07_processados/chunks/{args.fonte}/chunks.jsonl — rode gerar_chunks.py antes.")
        return
    print(f"   OK — {len(amostra)} chunks lidos (ex.: {amostra[0]['documento']!r}).")

    print("\n2. Conectando ao Qdrant (deve usar modo embutido via QDRANT_LOCAL_PATH)...")
    client = conectar_qdrant()

    print(f"\n3. Recriando coleção de teste '{COLECAO_TESTE}' (isolada da produção)...")
    if client.collection_exists(COLECAO_TESTE):
        client.delete_collection(COLECAO_TESTE)
    client.create_collection(
        collection_name=COLECAO_TESTE,
        vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
    )

    print("\n4. Carregando BGE-M3 (CPU — primeira vez pode demorar se o cache do passo 2 não tiver terminado)...")
    t0 = time.time()
    modelo = carregar_modelo()
    print(f"   Modelo carregado em {time.time() - t0:.1f}s — dispositivo: {modelo.device}")

    print(f"\n5. Gerando embeddings para {len(amostra)} chunks...")
    t0 = time.time()
    textos = [c["texto"] for c in amostra]
    vetores = modelo.encode(textos, show_progress_bar=False, normalize_embeddings=True)
    dt = time.time() - t0
    print(f"   OK — {len(vetores)} vetores gerados em {dt:.1f}s ({dt / len(vetores):.2f}s/chunk) — dimensão: {len(vetores[0])}")

    print("\n6. Indexando (upsert) no Qdrant embutido...")
    pontos = [
        PointStruct(
            id=str(uuid.uuid5(NAMESPACE_CHUNK_ID, chunk["chunk_id"])),
            vector=vetor.tolist(),
            payload=chunk,
        )
        for chunk, vetor in zip(amostra, vetores)
    ]
    client.upsert(collection_name=COLECAO_TESTE, points=pontos)
    contagem = client.count(collection_name=COLECAO_TESTE).count
    print(f"   OK — {contagem} pontos na coleção de teste.")

    print("\n7. Rodando busca de teste...")
    pergunta = "monitoramento participativo de espécies em unidades de conservação"
    vetor_pergunta = modelo.encode([pergunta], normalize_embeddings=True)[0]
    resultados = client.query_points(
        collection_name=COLECAO_TESTE, query=vetor_pergunta.tolist(), limit=3
    ).points
    print(f'   Pergunta: "{pergunta}"')
    for i, r in enumerate(resultados, start=1):
        payload = r.payload or {}
        trecho = (payload.get("texto") or "")[:150].replace("\n", " ")
        print(f"   {i}. score={r.score:.4f} | doc={payload.get('documento')} | {trecho}...")

    if args.manter_colecao:
        print(f"\nColeção de teste mantida: '{COLECAO_TESTE}' (apague manualmente quando terminar).")
    else:
        client.delete_collection(COLECAO_TESTE)
        print(f"\nColeção de teste '{COLECAO_TESTE}' removida (pipeline validado, nada fica para trás).")

    print("\nSMOKE TEST CONCLUÍDO — pipeline OK em CPU. Pronto para a indexação real quando a GPU voltar.")


if __name__ == "__main__":
    main()

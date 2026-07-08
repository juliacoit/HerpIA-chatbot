"""Gera embeddings com BGE-M3 e indexa os chunks já gerados no Qdrant.

Fase 5.3 do roadmap. Usa o modelo escolhido temporariamente para testes
(ver docs/decisoes/0005-escolha-temporaria-modelo-embeddings.md) — os
vetores gerados aqui são descartáveis, não é a decisão final de produção.

Lê 07_processados/chunks/<fonte>/chunks.jsonl (gerado por gerar_chunks.py) e
indexa cada chunk no Qdrant: vetor denso (busca semântica) + payload com o
texto completo e os metadados de rastreabilidade (fonte, documento, página/
seção, URL/caminho local, data de coleta, nível de sensibilidade).

Reindexação é idempotente: o ID de cada ponto no Qdrant é derivado do
chunk_id (uuid5), então rodar o script de novo sobre os mesmos chunks
atualiza os pontos existentes em vez de duplicá-los.

Uso:
    python scripts/indexacao/indexar_chunks.py
    python scripts/indexacao/indexar_chunks.py --fonte salve
    python scripts/indexacao/indexar_chunks.py --recriar-colecao
    python scripts/indexacao/indexar_chunks.py --buscar "qual o status de conservação da jararaca?"

Pré-requisitos:
    pip install sentence-transformers qdrant-client
    Qdrant acessível (docker compose up -d no servidor + túnel SSH no
    PC de desenvolvimento — ver docs/infraestrutura-local.md).
    Verificar com: python scripts/check_services.py
"""

import argparse
import json
import os
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

RAIZ = Path(__file__).resolve().parents[2]
CHUNKS_DIR = RAIZ / "07_processados" / "chunks"

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLECAO = os.getenv("QDRANT_COLLECTION", "ran_herpetofauna")

MODELO_NOME = "BAAI/bge-m3"
DIMENSAO_VETOR = 1024
TAMANHO_LOTE = 32

# UUID fixo usado como namespace para gerar IDs de ponto estáveis a partir do
# chunk_id (mesmo chunk_id -> mesmo ID no Qdrant -> reindexar atualiza, não duplica).
NAMESPACE_CHUNK_ID = uuid.UUID("d9a1f5b0-3c9b-4a44-9d6b-9c9d4a2b6e10")


def carregar_modelo():
    from sentence_transformers import SentenceTransformer
    print(f"Carregando {MODELO_NOME} (pode demorar bastante na primeira vez — baixa ~2 GB)...")
    return SentenceTransformer(MODELO_NOME)


def conectar_qdrant():
    from qdrant_client import QdrantClient
    return QdrantClient(url=QDRANT_URL)


def garantir_colecao(client, recriar: bool = False):
    from qdrant_client.models import Distance, VectorParams

    existe = client.collection_exists(COLECAO)
    if existe and recriar:
        print(f"Recriando coleção '{COLECAO}' (dados indexados anteriormente serão apagados)...")
        client.delete_collection(COLECAO)
        existe = False
    if not existe:
        client.create_collection(
            collection_name=COLECAO,
            vectors_config=VectorParams(size=DIMENSAO_VETOR, distance=Distance.COSINE),
        )
        print(f"Coleção '{COLECAO}' criada (dimensão={DIMENSAO_VETOR}, distância=cosine).")
    else:
        print(f"Coleção '{COLECAO}' já existe — reaproveitando (upsert por chunk_id).")


def ler_chunks(fonte: str):
    caminho = CHUNKS_DIR / fonte / "chunks.jsonl"
    if not caminho.exists():
        print(f"  [{fonte}] {caminho} não encontrado — rode gerar_chunks.py antes de indexar.")
        return
    with caminho.open(encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if linha:
                yield json.loads(linha)


def indexar_fonte(client, modelo, fonte: str) -> dict:
    from qdrant_client.models import PointStruct

    relatorio = {"chunks": 0, "erros": 0}
    lote = []

    def enviar_lote():
        if not lote:
            return
        textos = [c["texto"] for c in lote]
        vetores = modelo.encode(
            textos, batch_size=TAMANHO_LOTE, show_progress_bar=False, normalize_embeddings=True
        )
        pontos = [
            PointStruct(
                id=str(uuid.uuid5(NAMESPACE_CHUNK_ID, chunk["chunk_id"])),
                vector=vetor.tolist(),
                payload=chunk,
            )
            for chunk, vetor in zip(lote, vetores)
        ]
        client.upsert(collection_name=COLECAO, points=pontos)
        relatorio["chunks"] += len(pontos)
        lote.clear()

    for chunk in ler_chunks(fonte):
        try:
            lote.append(chunk)
            if len(lote) >= TAMANHO_LOTE:
                enviar_lote()
        except Exception as e:
            print(f"  ✗ {chunk.get('chunk_id')} — ERRO: {e}", file=sys.stderr)
            relatorio["erros"] += 1
    enviar_lote()

    print(f"  [{fonte}] {relatorio['chunks']} chunks indexados ({relatorio['erros']} erros).")
    return relatorio


def buscar(client, modelo, pergunta: str, top_k: int):
    vetor = modelo.encode([pergunta], normalize_embeddings=True)[0]
    resultados = client.search(collection_name=COLECAO, query_vector=vetor.tolist(), limit=top_k)

    print(f"\nPergunta: {pergunta}\n")
    if not resultados:
        print("Nenhum resultado — a coleção está vazia? Rode o script sem --buscar primeiro.")
        return
    for i, r in enumerate(resultados, start=1):
        payload = r.payload or {}
        origem = payload.get("documento") or payload.get("caminho_local", "?")
        trecho = (payload.get("texto") or "")[:300].replace("\n", " ")
        print(f"{i}. score={r.score:.4f} | fonte={payload.get('fonte')} | doc={origem}")
        print(f"   {trecho}...\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fonte", choices=["monitora", "pans", "salve"], default=None,
                        help="Indexar apenas esta fonte (padrão: todas)")
    parser.add_argument("--recriar-colecao", action="store_true",
                        help="Apaga e recria a coleção antes de indexar (destrutivo)")
    parser.add_argument("--buscar", metavar="PERGUNTA", default=None,
                        help="Não indexa — roda uma busca de teste na coleção já existente")
    parser.add_argument("--top-k", type=int, default=5, help="Número de resultados na busca de teste")
    args = parser.parse_args()

    client = conectar_qdrant()

    if args.buscar:
        modelo = carregar_modelo()
        buscar(client, modelo, args.buscar, args.top_k)
        return

    garantir_colecao(client, recriar=args.recriar_colecao)
    modelo = carregar_modelo()

    fontes = [args.fonte] if args.fonte else ["monitora", "pans", "salve"]
    total = {"chunks": 0, "erros": 0}
    print(f"\nIndexando chunks com {MODELO_NOME} na coleção '{COLECAO}'...\n")
    for fonte in fontes:
        relatorio = indexar_fonte(client, modelo, fonte)
        for chave in total:
            total[chave] += relatorio.get(chave, 0)

    print(f"\nCONCLUÍDO — {total['chunks']} chunks indexados, {total['erros']} erros no total.")


if __name__ == "__main__":
    main()

"""Sincroniza campos de metadado do payload SALVE já indexado no Qdrant a
partir de `07_processados/chunks/salve/chunks.jsonl` — sem reencodar
embeddings (o texto do chunk, e portanto o vetor, não muda quando só um
campo de metadado é adicionado ou corrigido).

Generaliza a migração pontual feita para `bioma` (string -> lista, ver
diagnosticos/agregacao-biomas-fichas-salve.md) para qualquer campo de
metadado da ficha SALVE que passe a existir/mudar em `gerar_chunks.py`: rode
`gerar_chunks.py --fonte salve` para regravar o `chunks.jsonl` com o campo
novo, adicione o nome do campo em `CAMPOS_METADADOS` abaixo (se ainda não
estiver) e rode este script — não precisa editar o resto.

Calcula o ID de cada ponto diretamente do `chunk_id` (mesmo `uuid5` e
namespace de `scripts/indexacao/indexar_chunks.py`), em vez de escanear o
Qdrant primeiro — mais simples e não depende do estado atual do payload.

Uso:
    python scripts/indexacao/sincronizar_payload_salve.py
    python scripts/indexacao/sincronizar_payload_salve.py --dry-run
    python scripts/indexacao/sincronizar_payload_salve.py --campos bioma,grupo,estados
"""

import argparse
import json
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from tqdm import tqdm

RAIZ = Path(__file__).resolve().parents[2]
CHUNKS_SALVE = RAIZ / "07_processados" / "chunks" / "salve" / "chunks.jsonl"

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_LOCAL_PATH = os.getenv("QDRANT_LOCAL_PATH")
COLECAO = os.getenv("QDRANT_COLLECTION", "ran_herpetofauna")

# Mesmo namespace fixo de indexar_chunks.py — precisa ser idêntico para o ID
# calculado aqui bater com o ponto já existente no Qdrant.
NAMESPACE_CHUNK_ID = uuid.UUID("d9a1f5b0-3c9b-4a44-9d6b-9c9d4a2b6e10")

# Campos de metadado sincronizáveis (nunca inclua "texto" — mudar o texto
# exige reencodar o vetor, isso não é responsabilidade deste script, é
# indexar_chunks.py). Adicione aqui o nome de qualquer campo novo que
# gerar_chunks.py passar a gravar no chunk SALVE.
CAMPOS_METADADOS = ["bioma", "categoria_risco", "grupo", "estados"]


def conectar_qdrant():
    from qdrant_client import QdrantClient

    if QDRANT_LOCAL_PATH:
        caminho = Path(QDRANT_LOCAL_PATH)
        if not caminho.is_absolute():
            caminho = RAIZ / caminho
        print(f"Usando Qdrant embutido (local) em {caminho}")
        return QdrantClient(path=str(caminho))
    return QdrantClient(url=QDRANT_URL)


def sincronizar(client, campos: list[str], dry_run: bool) -> dict:
    relatorio = {"processados": 0, "erros": 0}
    total = sum(1 for _ in CHUNKS_SALVE.open(encoding="utf-8"))

    with CHUNKS_SALVE.open(encoding="utf-8") as f:
        for linha in tqdm(f, total=total, desc="[salve] sincronizando payload", unit="chunk"):
            linha = linha.strip()
            if not linha:
                continue
            chunk = json.loads(linha)
            payload = {campo: chunk.get(campo) for campo in campos}
            ponto_id = str(uuid.uuid5(NAMESPACE_CHUNK_ID, chunk["chunk_id"]))

            relatorio["processados"] += 1
            if not dry_run:
                try:
                    client.set_payload(collection_name=COLECAO, payload=payload, points=[ponto_id])
                except Exception as e:
                    print(f"  ✗ {chunk['chunk_id']} — ERRO: {e}")
                    relatorio["erros"] += 1

    return relatorio


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="Só conta, não escreve no Qdrant")
    parser.add_argument(
        "--campos", default=None,
        help=f"Lista separada por vírgula (padrão: todos — {', '.join(CAMPOS_METADADOS)})",
    )
    args = parser.parse_args()

    if not CHUNKS_SALVE.exists():
        print(f"{CHUNKS_SALVE} não encontrado — rode gerar_chunks.py --fonte salve antes.")
        return

    campos = args.campos.split(",") if args.campos else CAMPOS_METADADOS
    campos_invalidos = set(campos) - set(CAMPOS_METADADOS)
    if campos_invalidos:
        print(f"Campo(s) desconhecido(s): {campos_invalidos}. Válidos: {CAMPOS_METADADOS}")
        return

    client = conectar_qdrant()
    relatorio = sincronizar(client, campos, dry_run=args.dry_run)

    modo = "DRY RUN — nada escrito" if args.dry_run else "CONCLUÍDO"
    print(
        f"\n{modo} — {relatorio['processados']} chunks salve processados "
        f"(campos: {', '.join(campos)}), {relatorio['erros']} erros."
    )


if __name__ == "__main__":
    main()

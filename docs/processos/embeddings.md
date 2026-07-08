# Geração de embeddings e indexação no Qdrant

- **Status:** 🔶 Script implementado (`scripts/indexacao/indexar_chunks.py`), aguardando
  primeira execução real contra o Qdrant do servidor e avaliação de qualidade
- **Última atualização:** 2026-07-08
- **Responsável(eis):** Script `scripts/indexacao/indexar_chunks.py`

## Objetivo

Gerar embeddings para cada chunk já produzido (ver
[chunking dos documentos autorizados](chunking.md)) e indexá-los no Qdrant
para recuperação semântica. Ver [`docs/roadmap.md`](../roadmap.md), Fase 5.

## Entradas

- `07_processados/chunks/<fonte>/chunks.jsonl` — gerado pelo processo de
  [chunking](chunking.md), que já lê exclusivamente de
  `03_documentos_autorizados/`.

## Saídas

- Pontos indexados no Qdrant, com payload de metadados (fonte, documento,
  página, URL/caminho local, data de coleta, nível de sensibilidade).
- Registro de IDs e status no PostgreSQL.

## Ferramentas

- Modelo de embeddings: **`BAAI/bge-m3`** (via `sentence-transformers`), escolhido
  **temporariamente** para testar os chunks já gerados — ver
  [ADR 0005](../decisoes/0005-escolha-temporaria-modelo-embeddings.md) e
  [`escolha_modelo_embeddings.md`](escolha_modelo_embeddings.md) para a decisão final
  (ainda pendente, condicionada a orçamento para API).
- Qdrant como banco vetorial de destino, cliente `qdrant-client`.
- Vetor denso de 1024 dimensões, métrica de similaridade cosseno.
- Registro de IDs/status no PostgreSQL: **ainda não implementado** (a indexação hoje
  só grava no Qdrant).

## Passo a passo

Implementado em `scripts/indexacao/indexar_chunks.py`:

1. Conecta ao Qdrant (`QDRANT_URL` do `.env`) e garante que a coleção
   (`QDRANT_COLLECTION`) existe, com vetor de 1024 dimensões e distância cosseno.
2. Carrega o modelo `BAAI/bge-m3` (`sentence-transformers`) — primeira execução baixa
   ~2 GB, ficam em cache local depois.
3. Lê `07_processados/chunks/<fonte>/chunks.jsonl` (uma fonte por vez ou todas).
4. Gera embeddings em lotes de 32 chunks, com o texto normalizado.
5. Indexa cada chunk no Qdrant com o payload completo do chunk (fonte, documento,
   página/seção, URL/caminho local, data de coleta, nível de sensibilidade, texto).
   O ID de cada ponto é derivado do `chunk_id` (uuid5) — reindexar os mesmos chunks
   atualiza os pontos existentes em vez de duplicá-los.

Uso:

```bash
# Verificar que o Qdrant está acessível (ver docs/infraestrutura-local.md)
python scripts/check_services.py

# Indexar todas as fontes
python scripts/indexacao/indexar_chunks.py

# Indexar só uma fonte, ou recriar a coleção do zero
python scripts/indexacao/indexar_chunks.py --fonte salve
python scripts/indexacao/indexar_chunks.py --recriar-colecao

# Busca de teste, sem reindexar (para avaliar qualidade da recuperação)
python scripts/indexacao/indexar_chunks.py --buscar "qual o status de conservação da jararaca?"
```

**Ainda não implementado:** registro de IDs/status da indexação no PostgreSQL (mencionado
nas Saídas) e busca híbrida (esparsa + multi-vetor do BGE-M3) — por ora só o vetor
denso é usado, suficiente para testar a qualidade básica de recuperação.

## Frequência de execução

Após cada rodada de chunking (Fase 4) de uma fonte.

## Observações sobre dados sensíveis

Só devem ser indexados chunks gerados a partir de
`03_documentos_autorizados/` (garantia que já vem do processo de chunking).
Nenhum chunk deve ser enviado a uma API externa de embeddings/LLM antes dessa
autorização (ver ADR 0002).

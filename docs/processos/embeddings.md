# Geração de embeddings e indexação no Qdrant

- **Status:** A definir
- **Última atualização:** 2026-07-03
- **Responsável(eis):**

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

- Modelo de embeddings: **decisão pendente** — recomendação inicial é
  `text-embedding-3-small` (OpenAI API) para o protótipo, com opção de trocar
  depois por modelo open-source em português (ver roadmap, seção "Decisões
  pendentes").
- Qdrant como banco vetorial de destino.

## Passo a passo

Ainda não implementado. Esboço:

1. Ler `chunks.jsonl` de cada fonte.
2. Gerar embeddings dos chunks com o modelo escolhido.
3. Indexar no Qdrant com o payload de metadados; registrar IDs/status no
   PostgreSQL.

## Frequência de execução

Após cada rodada de chunking (Fase 4) de uma fonte.

## Observações sobre dados sensíveis

Só devem ser indexados chunks gerados a partir de
`03_documentos_autorizados/` (garantia que já vem do processo de chunking).
Nenhum chunk deve ser enviado a uma API externa de embeddings/LLM antes dessa
autorização (ver ADR 0002).

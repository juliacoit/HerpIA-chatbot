# Chunking e geração de embeddings

- **Status:** A definir
- **Última atualização:** 2026-07-02
- **Responsável(eis):**

## Objetivo

Transformar os textos extraídos (`07_processados/textos_extraidos/`) em chunks
adequados para recuperação semântica, gerar embeddings para cada chunk e indexá-los
no Qdrant. Ver [`docs/roadmap.md`](../roadmap.md), Fases 4 e 5.

## Entradas

- `07_processados/textos_extraidos/salve/<slug>.json`
- `07_processados/textos_extraidos/<fonte>/...json` (Monitora, PANs, publicações —
  gerados pelo pipeline de extração de PDFs)
- Apenas documentos já classificados como autorizados (`03_documentos_autorizados/`)
  entram nesta etapa.

## Saídas

- `07_processados/chunks/<fonte>/chunks.jsonl`
- Pontos indexados no Qdrant, com payload de metadados (fonte, documento, página,
  URL/caminho local, data de coleta).
- Registro de IDs e status no PostgreSQL.

## Ferramentas

- Modelo de embeddings: **decisão pendente** — recomendação inicial é
  `text-embedding-3-small` (OpenAI API) para o protótipo, com opção de trocar depois
  por modelo open-source em português (ver roadmap, seção "Decisões pendentes").
- Qdrant como banco vetorial de destino.

## Passo a passo

Estratégias já decididas por fonte (roadmap Fase 4), passo a passo de execução ainda
não implementado:

1. **SALVE:** um chunk por seção da ficha; seções longas divididas por parágrafo.
   Tamanho alvo ~2000 caracteres (~500 tokens). Cada chunk inclui cabeçalho com
   metadados da espécie (nome, categoria, bioma, DOI).
2. **PDFs (Monitora, PANs, publicações):** janela deslizante com overlap (ex.: 500
   tokens, overlap 50 tokens), preferindo splits em final de frase ou parágrafo. Cada
   chunk inclui fonte, nome do documento, página, URL/caminho local, data de coleta.
   Publicações científicas devem incluir também metadados bibliográficos (autores,
   ano, título, DOI).
3. Gerar embeddings dos chunks com o modelo escolhido.
4. Indexar no Qdrant com o payload de metadados; registrar IDs/status no PostgreSQL.

## Frequência de execução

Após cada rodada de extração de texto (Fase 2) e classificação de sensibilidade
(Fase 3) de uma fonte.

## Observações sobre dados sensíveis

Só devem ser chunkados e indexados documentos já movidos para
`03_documentos_autorizados/`. Nenhum chunk deve ser enviado a uma API externa de
embeddings/LLM antes dessa autorização (ver ADR 0002).

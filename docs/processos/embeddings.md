# Geração de embeddings e indexação no Qdrant

- **Status:** 🔶 Script implementado (`scripts/indexacao/indexar_chunks.py`), aguardando
  primeira execução real e avaliação de qualidade — como o PC servidor ainda não foi
  configurado (pendência de segurança de rede, ver ADR 0003), a primeira execução deve
  usar o **modo embutido do Qdrant** (sem Docker, sem rede), não o servidor dedicado
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

1. Conecta ao Qdrant e garante que a coleção (`QDRANT_COLLECTION`) existe, com vetor
   de 1024 dimensões e distância cosseno. Duas formas de conectar (ver "Onde rodar o
   Qdrant" abaixo):
   - `QDRANT_URL` do `.env` → servidor Qdrant (Docker + túnel SSH).
   - `QDRANT_LOCAL_PATH` do `.env` → modo embutido, sem servidor (tem prioridade sobre
     `QDRANT_URL` quando definido).
2. Carrega o modelo `BAAI/bge-m3` (`sentence-transformers`) — primeira execução baixa
   ~2 GB, ficam em cache local depois.
3. Lê `07_processados/chunks/<fonte>/chunks.jsonl` (uma fonte por vez ou todas).
4. Gera embeddings em lotes de 32 chunks, com o texto normalizado. Uma barra de
   progresso (`tqdm`) mostra o andamento por fonte durante a execução.
5. Indexa cada chunk no Qdrant com o payload completo do chunk (fonte, documento,
   página/seção, URL/caminho local, data de coleta, nível de sensibilidade, texto).
   O ID de cada ponto é derivado do `chunk_id` (uuid5) — reindexar os mesmos chunks
   atualiza os pontos existentes em vez de duplicá-los.

Rodar por partes (uma fonte por dia, por exemplo) já é possível com `--fonte`.
Se uma fonte for interrompida no meio, `--retomar` pula os chunks cujo ID já
está na coleção, sem reencodá-los — só reencoda o que falta. Sem `--retomar`,
o comportamento padrão é reencodar tudo de novo (necessário se o texto do
chunk mudou desde a última indexação, já que o `chunk_id` é derivado de
`fonte:caminho:índice`, não do conteúdo — não muda se o texto for corrigido
sem mudar o índice do chunk).

### Onde rodar o Qdrant

| | Servidor (Docker + túnel SSH) | Modo embutido (`QDRANT_LOCAL_PATH`) |
|---|---|---|
| Quando usar | PC servidor já configurado (ADR 0003) | Enquanto o PC servidor não estiver configurado — sem Docker, sem porta de rede envolvida |
| Configuração | `QDRANT_URL` no `.env` + `docker compose up -d` no servidor + túnel SSH no dev | `QDRANT_LOCAL_PATH=07_processados/qdrant_local` no `.env` |
| Persistência | Volume Docker no servidor | Diretório local (`07_processados/qdrant_local/`, gitignored) |
| Dashboard web | Sim (`QDRANT_URL/dashboard`) | Não |
| Migração depois | — | Os dados não migram automaticamente — ao migrar para o servidor, reindexar do zero (os vetores desta fase já são descartáveis, ver ADR 0005) |

Uso (com o modo embutido, sem precisar de Docker nem SSH):

```bash
# .env: QDRANT_LOCAL_PATH=07_processados/qdrant_local

# Indexar todas as fontes
python scripts/indexacao/indexar_chunks.py

# Indexar só uma fonte, ou recriar a coleção do zero
python scripts/indexacao/indexar_chunks.py --fonte salve
python scripts/indexacao/indexar_chunks.py --recriar-colecao

# Rodar em partes (uma fonte hoje, outra amanhã) e retomar uma fonte
# interrompida no meio sem reencodar o que já foi indexado
python scripts/indexacao/indexar_chunks.py --fonte pans --retomar

# Busca de teste, sem reindexar (para avaliar qualidade da recuperação)
python scripts/indexacao/indexar_chunks.py --buscar "qual o status de conservação da jararaca?"
```

Quando o PC servidor estiver configurado (ver
[`docs/infraestrutura-local.md`](../infraestrutura-local.md)), basta remover
`QDRANT_LOCAL_PATH` do `.env` (ou deixar sem valor) para o script voltar a usar
`QDRANT_URL`; validar com `python scripts/check_services.py` antes.

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

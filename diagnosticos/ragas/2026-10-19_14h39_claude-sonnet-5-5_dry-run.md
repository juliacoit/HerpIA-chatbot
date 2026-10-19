# Avaliação RAGAS — HerpIA (DRY-RUN, sem chamadas ao juiz)

_Gerado em 2026-10-19T14:34:21 por `avaliacao/rodar_ragas.py`._

## Metadados

- **dry_run:** `True`
- **juiz:** `claude-sonnet-5-5`
- **esforco_juiz:** `low`
- **max_tokens_juiz:** `8192`
- **embeddings_answer_relevancy:** `BAAI/bge-m3`
- **metricas:** `['faithfulness', 'answer_relevancy', 'context_precision_with_reference', 'context_recall']`
- **top_k:** `5`
- **n_casos:** `36`
- **versao_ragas:** `não instalado`
- **versao_instructor:** `não instalado`
- **versao_anthropic:** `não instalado`
- **git_commit:** `09dea2d`
- **git_sujo:** `True`
- **url_base:** `http://localhost:8000`
- **backend_llm_modelo:** `qwen2.5:3b-instruct`
- **backend_groundedness_verificar:** `True`

## Resumo

- planejado: 35
- sem_texto_llm: 1
- chamadas ao juiz estimadas (sem retries): 175
- caracteres que seriam enviados à API: 330.816
- checagens de rota: falha_conhecida=3, nao_checada=17, ok=16

## Por categoria

| Cat. | Casos | Avaliados | Faith. | Relev. | CtxPrec. | CtxRec. |
|---|---:|---:|---:|---:|---:|---:|
| A | 3 | 0 | — (n=0) | — (n=0) | — (n=0) | — (n=0) |
| B | 3 | 0 | — (n=0) | — (n=0) | — (n=0) | — (n=0) |
| C | 3 | 0 | — (n=0) | — (n=0) | — (n=0) | — (n=0) |
| D | 4 | 0 | — (n=0) | — (n=0) | — (n=0) | — (n=0) |
| F | 6 | 0 | — (n=0) | — (n=0) | — (n=0) | — (n=0) |
| G | 5 | 0 | — (n=0) | — (n=0) | — (n=0) | — (n=0) |
| H | 2 | 0 | — (n=0) | — (n=0) | — (n=0) | — (n=0) |
| I | 1 | 0 | — (n=0) | — (n=0) | — (n=0) | — (n=0) |
| J | 1 | 0 | — (n=0) | — (n=0) | — (n=0) | — (n=0) |
| L | 8 | 0 | — (n=0) | — (n=0) | — (n=0) | — (n=0) |

## Por caso

| Caso | Status | Saída | Retenção | Rota | Contextos | Chamadas | Faith. | Relev. | CtxPrec. | CtxRec. |
|---|---|---|---|---|---|---:|---:|---:|---:|---:|
| A1 | planejado | gerada | — | ok | salve,salve,salve,salve,salve | 5 | — | — | — | — |
| A2 | planejado | gerada | — | ok | pans,pans,pans,pans,pans | 5 | — | — | — | — |
| A3 | planejado | gerada | — | ok | monitora,monitora,monitora,monitora,monitora | 5 | — | — | — | — |
| B1 | planejado | gerada | — | nao_checada | pans,pans,pans,pans,pans | 5 | — | — | — | — |
| B2 | planejado | retida_groundedness | lexical | nao_checada | monitora,monitora,monitora,monitora,monitora | 5 | — | — | — | — |
| B3 | planejado | abstencao | — | nao_checada | pans,pans,pans,pans,pans | 5 | — | — | — | — |
| C1 | planejado | gerada | — | ok | salve,salve,salve,salve,salve | 5 | — | — | — | — |
| C2 | planejado | gerada | — | ok | salve,salve,salve,salve,salve | 5 | — | — | — | — |
| C3 | planejado | retida_groundedness | juiz_llm | ok | salve,salve,salve,salve,salve | 5 | — | — | — | — |
| D1 | planejado | gerada | — | ok | pans,pans,pans,pans,pans | 5 | — | — | — | — |
| D2 | planejado | gerada | — | ok | pans,pans,pans,pans,pans | 5 | — | — | — | — |
| D3 | planejado | gerada | — | ok | pans,pans,pans,pans,pans | 5 | — | — | — | — |
| D4 | planejado | abstencao | — | falha_conhecida | salve,salve,salve,salve,salve | 5 | — | — | — | — |
| F2 | planejado | retida_groundedness | juiz_llm | nao_checada | monitora,pans,pans,pans,pans | 5 | — | — | — | — |
| F3 | planejado | abstencao | — | nao_checada | pans,pans,pans,pans,pans | 5 | — | — | — | — |
| F4 | planejado | abstencao | — | nao_checada | pans,pans,pans,pans,pans | 5 | — | — | — | — |
| F5 | planejado | gerada | — | ok | pans,pans,pans,pans,pans | 5 | — | — | — | — |
| F6 | planejado | gerada | — | ok | salve,salve,salve,salve,salve | 5 | — | — | — | — |
| F7 | planejado | gerada | — | nao_checada | monitora,monitora,monitora,monitora,monitora | 5 | — | — | — | — |
| G1 | sem_texto_llm | sei_nao_indexado | — | nao_checada | — | 0 | — | — | — | — |
| G2 | planejado | abstencao | — | nao_checada | pans,pans,pans,monitora,pans | 5 | — | — | — | — |
| G3 | planejado | abstencao | — | nao_checada | pans,pans,pans,pans,pans | 5 | — | — | — | — |
| G4 | planejado | gerada | — | nao_checada | monitora,pans,pans,pans,monitora | 5 | — | — | — | — |
| G5 | planejado | abstencao | — | nao_checada | pans,pans,pans,pans,pans | 5 | — | — | — | — |
| H1 | planejado | gerada | — | ok | salve,salve,salve,salve,salve | 5 | — | — | — | — |
| H2 | planejado | gerada | — | ok | salve,pans,pans,pans,pans | 5 | — | — | — | — |
| I1 | planejado | gerada | — | ok | salve,salve,pans,pans,salve | 5 | — | — | — | — |
| J1 | planejado | retida_groundedness | lexical | nao_checada | pans,pans,pans,pans,pans | 5 | — | — | — | — |
| L1 | planejado | gerada | — | nao_checada | pans,pans,pans,pans,pans | 5 | — | — | — | — |
| L2 | planejado | gerada | — | falha_conhecida | salve,salve,salve,salve,salve | 5 | — | — | — | — |
| L3 | planejado | abstencao | — | nao_checada | salve,salve,salve,salve,salve | 5 | — | — | — | — |
| L4 | planejado | gerada | — | ok | salve,salve,salve,salve,salve | 5 | — | — | — | — |
| L5 | planejado | retida_groundedness | lexical | ok | salve,salve,salve,salve,salve | 5 | — | — | — | — |
| L6 | planejado | abstencao | — | nao_checada | pans,pans,pans,pans,pans | 5 | — | — | — | — |
| L7 | planejado | abstencao | — | nao_checada | monitora,monitora,monitora,monitora,monitora | 5 | — | — | — | — |
| L8 | planejado | gerada | — | falha_conhecida | salve,salve,salve,salve,salve | 5 | — | — | — | — |

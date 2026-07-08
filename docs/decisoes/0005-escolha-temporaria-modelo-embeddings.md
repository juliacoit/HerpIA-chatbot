# 0005. Escolha temporária do modelo de embeddings para testes

- **Status:** Decisão parcial tomada — BGE-M3 escolhido temporariamente para testar os chunks já gerados; decisão final de produção segue pendente
- **Data:** 2026-07-08
- **Responsável(eis):** Julia Coite

## Contexto

A Fase 5 do [`docs/roadmap.md`](../roadmap.md) depende de escolher um modelo de
embeddings antes de indexar os 59.080 chunks já gerados na Fase 4 (Monitora,
PANs, SALVE). O documento de apoio
[`docs/processos/escolha_modelo_embeddings.md`](../processos/escolha_modelo_embeddings.md)
levanta três opções: (A) `text-embedding-3-small` da OpenAI, (B)
`text-embedding-3-large` da OpenAI, e (C) modelo open-source local (BGE-M3 ou
multilingual-e5-large).

A decisão final entre as opções A/B (API paga) e C (local) depende de a
equipe do RAN definir se há orçamento para custear uma API de embeddings de
forma recorrente — uma decisão institucional, não só técnica, que ainda não
foi tomada.

Enquanto essa decisão de orçamento não sai, os chunks já gerados ficam
parados sem nenhuma validação prática: ainda não se sabe se a estratégia de
chunking (Fase 4) produz vetores de boa qualidade para recuperação. Esperar a
decisão de orçamento para só então testar atrasaria a validação de todo o
pipeline sem necessidade.

## Decisão

Usar o **BGE-M3** (Opção C, modelo local) **temporariamente**, apenas para:

1. Gerar embeddings de teste sobre os chunks já existentes em
   `07_processados/chunks/`.
2. Indexá-los no Qdrant e validar a qualidade da recuperação (buscas de
   teste, avaliação manual por amostragem de perguntas reais do domínio).
3. Detectar problemas de chunking ou do pipeline antes da equipe decidir o
   modelo definitivo.

Essa escolha **não é a decisão final de produção** — existe para permitir
testar o pipeline fim a fim (chunking → embeddings → Qdrant → busca) sem
depender da decisão de orçamento da equipe sobre custear uma API paga.

O motivo de escolher especificamente o BGE-M3 (e não o multilingual-e5-large)
para esse teste está detalhado em
[`docs/processos/escolha_modelo_embeddings.md`](../processos/escolha_modelo_embeddings.md):
suporte nativo a busca híbrida e ausência de convenção de prefixo obrigatório
reduzem o risco de erro nesta fase exploratória.

## Consequências

- Os vetores gerados nesta fase são **descartáveis**: se a equipe decidir por
  uma API paga (Opção A/B), os embeddings de teste com BGE-M3 serão apagados
  e regenerados do zero com o modelo escolhido — vetores de modelos
  diferentes não são compatíveis entre si.
- Permite validar, com dados reais, se a estratégia de chunking (Fase 4) e a
  configuração do Qdrant (Fase 5.2) funcionam antes de comprometer a escolha
  definitiva.
- Nenhuma coleção criada durante esse teste deve ser tratada como "final" para
  o backend (Fase 6) até a decisão de orçamento ser confirmada com a equipe.
- Se a equipe confirmar que não há orçamento para API, esta decisão temporária
  tende a se tornar a decisão definitiva (BGE-M3 segue em produção) — isso
  deve ser registrado como **atualização deste mesmo ADR**, não um novo, já
  que a estratégia não muda, só o status.

## Próximas etapas

- [ ] Implementar `scripts/indexacao/indexar_chunks.py` usando BGE-M3
  (`sentence-transformers` ou `FlagEmbedding`)
- [ ] Subir/validar o Qdrant (Fase 5.2)
- [ ] Indexar os 59.080 chunks existentes com BGE-M3
- [ ] Rodar buscas de teste e avaliar qualidade manualmente (amostra de
  perguntas reais do domínio)
- [ ] Levar o resultado do teste + a necessidade (ou não) de orçamento para
  API para decisão final com a equipe do RAN
- [ ] Atualizar este ADR quando a decisão definitiva for confirmada

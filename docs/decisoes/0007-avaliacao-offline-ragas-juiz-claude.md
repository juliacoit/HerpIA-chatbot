# 0007. Avaliação offline com RAGAS e juiz Claude via API da Anthropic

- **Status:** Proposta (rascunho de 2026-10-14; aceitar depois da primeira execução paga autorizada)
- **Data:** 2026-10-14
- **Responsável(eis):** Julia Coite

## Contexto

Hoje a qualidade das respostas é medida pela bateria de domínio
(`scripts/teste_perguntas_dominio.py`), com avaliação manual. A
fundamentação é verificada pelo juiz interno de groundedness
(`backend/services/groundedness.py`), um LLM local de 3B que também gera a
resposta. As rodadas de comparação de juízes
(`diagnosticos/comparacao-juizes-rodada2.md`) mostraram que os juízes locais
erram nos dois sentidos. Falta uma medida externa, repetível e numérica, que
possa rodar a cada mudança no pipeline (meta de "% de acerto por categoria",
reunião de 2026-08-19).

Alternativas consideradas:

- **Juiz local (Ollama):** custo zero, mas é o mesmo tipo de modelo que está
  sendo avaliado, e a rodada 2 mostrou baixa confiabilidade.
- **Juiz via API paga, em produção:** descartado. O projeto não tem verba
  para API paga no caminho de produção (ADR 0006), e a produção não pode
  depender de serviço externo para responder.
- **Juiz via API paga, só offline:** custo por execução, sob demanda, sem
  afetar o serviço. Foi a opção escolhida.

## Decisão

1. **Avaliação offline com RAGAS** (`avaliacao/rodar_ragas.py`), rodada sob
   demanda no PC de desenvolvimento, a cada mudança relevante no pipeline. O
   juiz **não** entra em produção.
2. **Juiz: Claude via API da Anthropic, com modelo fixado.** O padrão é
   `claude-sonnet-5-5`, e `--juiz claude-haiku-5-5` serve para medir a
   concordância entre juízes. O modelo e a versão do ragas vão nos metadados
   de cada relatório. Nesses modelos, `temperature`/`top_p` diferentes do
   padrão dão erro 400, portanto **não há "temperatura 0"**: a
   reprodutibilidade vem de fixar modelo, prompts e versão do ragas, não da
   amostragem.
3. **Bloqueio por sensibilidade, falhando fechado.** Antes de qualquer
   chamada à API, o script confere o `nivel_sensibilidade` de **todos** os
   contextos do caso. Só `"autorizado"` é aceito, para todas as fontes
   (monitora, pans, salve). Qualquer outro valor, inclusive `None` ou campo
   ausente, pula o caso inteiro (`bloqueado_sensibilidade`), e o texto nunca é
   enviado. Na contagem de 2026-10-14, os 59.085 chunks indexados eram todos
   `autorizado`. Só vão à API trechos já recuperados (nunca documentos
   inteiros), conforme as regras do `CLAUDE.md`.
4. **Modo de avaliação no backend travado por configuração.** O
   `incluir_contextos` em `/perguntar` só é aceito com
   `PERMITIR_MODO_AVALIACAO=true`, que fica ligado apenas no `.env` do PC de
   desenvolvimento; sem ele, a resposta é HTTP 403. A trava existe porque a
   resposta passa a incluir `resposta_original`, que pode ser uma resposta
   retida por não ser fundamentada. Requisições de avaliação não são
   gravadas na tabela `interacoes`.
5. **`ragas==0.4.3` fixado, apesar da CVE-2026-6587** (SSRF, afeta 0.2.3 a
   0.4.3, sem versão corrigida em 2026-10-14). Mitigações:
   - **nunca usar as métricas multimodais** (`MultiModalFaithfulness`,
     `MultiModalRelevance`), únicas que alcançam o código vulnerável
     (`metrics/collections/multi_modal_faithfulness/util.py`);
   - os contextos vêm só do nosso backend;
   - a execução é offline, só no PC de desenvolvimento;
   - telemetria do ragas desligada (`RAGAS_DO_NOT_TRACK=true`).
6. **Dependências isoladas:** `requirements-avaliacao.txt` (ragas,
   instructor, anthropic) inclui `requirements-dev.txt` (pytest) e fica fora
   da imagem de produção.
7. **Gabaritos (`reference`) só da equipe técnica do RAN.** Enquanto não
   houver gabarito validado, o caso usa `PENDENTE_VALIDACAO_RAN` e pula as
   métricas que dependem de referência (`ContextPrecisionWithReference`,
   `ContextRecall`).

## Consequências

- Há uma medida externa e numérica de fidelidade e relevância por categoria
  da bateria. Ela também permite comparar o juiz interno com o RAGAS (matriz
  2×2, separando as retenções em que o juiz interno nem chegou a julgar).
- **Custo por execução**, que precisa de autorização a cada rodada paga.
  Isso contrasta com a falta de verba registrada no ADR 0006; a origem desse
  custo precisa ser confirmada com a equipe. O `--dry-run` e o `--max-casos`
  existem para controlar o custo.
- Trechos autorizados de fontes públicas passam a ser enviados à Anthropic
  durante a avaliação. Isso é coerente com a regra do projeto ("só trechos já
  recuperados, filtrados e autorizados"), mas amplia os destinatários desses
  dados.
- O ragas 0.4.3 com Claude 5.5 depende de contornos: `provider="anthropic"`,
  `tool_choice={"type": "auto"}` (o `tool_choice` forçado do instructor dá
  400) e a remoção de `temperature`/`top_p`. Ver `diagnosticos/ragas_fase0.md`,
  seção 8.2. Uma atualização de ragas ou instructor pode quebrar esses
  contornos; conferir a cada atualização.
- A avaliação roda com o `top_k` do frontend (5) e por isso não é
  diretamente comparável às baterias anteriores, que usaram `top_k=8`.
- Reavaliar a CVE quando sair uma versão do ragas posterior à 0.4.3.

# Sessões supervisionadas com a equipe do RAN

- **Status:** Em desenvolvimento (1ª sessão diagnosticada; correções da Parte 1 implementadas numa branch ainda não integrada)
- **Última atualização:** 2026-11-04
- **Responsável(eis):** Julia Coite

## Objetivo

Validar o HerpIA com quem vai usá-lo (Fase 8 do roadmap). Técnicos e gestores
do RAN fazem perguntas reais na interface e comentam cada resposta. Cada
problema é diagnosticado com evidência do código, dos logs e do índice, antes
de qualquer correção.

## Entradas

- **Histórico comentado da sessão:** HTML exportado da interface com os
  comentários da equipe. O da sessão de 26/10/2026 está fora do repositório
  (`Downloads/sessao-herpia-2026-10-26-comentada.html`). A versão sem
  comentários está em `logs/sessoes/`, que o git ignora. Não há script
  versionado que gere esse HTML.
- **Tabela `interacoes`** do PostgreSQL local (pergunta, resposta, citações,
  chunks, estado). Desde 2026-11 ela grava também `chunk_ids`, `rota`,
  `tipo_saida`, `origem_retencao`, `resposta_original` (só das retidas) e
  temperatura/seed. Com isso, a próxima sessão é reproduzível sem exportar o
  índice.
- **Índice Qdrant embutido** (`07_processados/qdrant_local`), só leitura.

## Saídas

- Diagnóstico em `diagnosticos/AAAA-MM-DD_sessao_supervisionada_ran.md`, com
  hipóteses, veredito, alcance e opções de correção.
- Casos de teste propostos em `diagnosticos/casos_sessao_ran_<data>.yaml`, a
  integrar à bateria só depois de aprovação.
- Correções em branch própria, com relatório
  `diagnosticos/AAAA-MM-DD_implementacao_pos_sessao_ran.md`.
- ADRs para decisões de escopo e política (`docs/decisoes/`).

## Ferramentas

Scripts descartáveis em `diagnosticos/scripts/`, todos só leitura:

- `sessao_ran_00_exportar_indice.py` exporta payloads e vetores para um cache
  fora do repositório. Os scripts `sessao_ran_01` a `sessao_ran_11`
  reproduzem o retrieval e medem as hipóteses.
- `prova_geracao_inalterada.py` compara chunks e prompt antes e depois de uma
  mudança.
- `verificar_insert_rollback.py` testa o INSERT do log sem gravar.
- `adr_escopo_simulacao.py` simula a classificação de escopo.

Para verificar a interface no navegador, use o Chromium do Playwright por CDP
(ver `design_system.md`). O Playwright do MCP exige o Chrome do sistema.

## Passo a passo

1. Sessão na interface com a equipe; exportar o histórico com os comentários.
2. Reconhecimento: o que o log guarda para cada interação; reproduzir o
   retrieval e conferir contra `chunks_recuperados`/`chunk_ids`.
3. Testar cada hipótese com evidência e quantificar o alcance no log e no
   índice inteiros. Registrar o que não foi possível verificar.
4. Entregar o diagnóstico e os casos propostos e **parar**. A Júlia aprova o
   que entra.
5. Implementar só o aprovado, numa branch nova, com a prova de que
   retrieval e geração não mudaram quando a mudança for só de exibição.
6. Entregar o relatório de implementação e parar de novo.

## Onde paramos (2026-11-04)

**Sessão de 26/10/2026** (16 interações, #786–#801):

- diagnóstico concluído: `diagnosticos/2026-11-04_sessao_supervisionada_ran.md`;
- casos propostos: `diagnosticos/casos_sessao_ran_2026-10-26.yaml`.

**Decisões da equipe (04/11/2026):**

- a base deve ser restrita à herpetofauna (ADR 0008);
- coordenadas exatas de ocorrência são permitidas (ADR 0009);
- "volume de dados" (#795) ainda não tem definição.

**Implementado, mas não integrado.** A branch `fix/citacoes-estados-logging`
saiu de `feature/avaliacao-ragas`, porque a `main` está cerca de 30 commits
atrás. Não houve merge nem push. Relatório:
`diagnosticos/2026-11-04_implementacao_pos_sessao_ran.md`.

- **Prioridade 1:** uma citação por seção da ficha SALVE; na interface, um
  cartão por documento, com cada seção expansível.
- **Prioridade 3:** `tipo_saida` em toda resposta; abstenção pura aparece como
  "sem evidência"; trechos recolhidos nas respostas retidas e sem evidência.
- **Prioridade 10:** colunas novas no log, com migração aditiva **já aplicada
  no banco local**. O dump de antes está em
  `~/backups/herpia/interacoes_feedback_2026-11-04_pre-migracao.sql`.
- **Verificação:** 102 testes passando; a prova de geração inalterada deu
  resultado idêntico byte a byte.

**Aguardando aprovação da Júlia:**

1. Merge/push da branch. Antes, `feature/avaliacao-ragas` precisa entrar na
   `main`, ou o PR passa a incluí-la.
2. Gravação real de uma interação nas colunas novas. Até agora foi testada só
   com rollback.
3. Prioridades ainda não iniciadas:
   - 2: a interface manda as 3 fontes e desliga o roteamento SALVE;
   - 4: diversificação dos resultados e colapso de quase-duplicatas;
   - 5: rebaixar a seção `referencias`;
   - 6: expansão por nome comum e sinônimo;
   - 7: tabela curada do Monitora;
   - 8: checagem de ano × categoria;
   - 9: rota determinística de avaliação/status;
   - 11: ajustes na reindexação semestral.

   O ADR 0008 recomenda decidir a 2 depois de medir com o filtro de escopo.

**Aguardando respostas da equipe** (ver os ADRs):

- **ADR 0008:** tartarugas marinhas dos relatórios PMP-BP; documentos
  institucionais do Monitora; regra por conteúdo ou lista explícita para os
  PANs territoriais; texto da mensagem de fora de escopo.
- **ADR 0009:** coordenadas no juiz externo do RAGAS; coordenadas removidas
  dos PDFs; restrição por espécie; login como pré-requisito; log sem
  coordenadas; download de CSV.

**Limitações conhecidas que continuam:**

- recusas com redação fora de `_PADRAO_ABSTENCAO` (#795) ainda aparecem como
  "Fundamentada";
- sem `LLM_SEED`/`LLM_TEMPERATURE`, o estado de uma mesma pergunta varia entre
  rodadas;
- na sem evidência, o expansor de trechos fica colado à faixa de estado
  (ajuste visual pendente).

**Para retomar:**

```bash
git switch fix/citacoes-estados-logging
venv/bin/python -m pytest -q                       # 102 testes
# Prova de geração inalterada (backend parado, por causa da trava do Qdrant embutido):
PYTHONPATH=. venv/bin/python diagnosticos/scripts/prova_geracao_inalterada.py /tmp/prova.json
```

## Frequência de execução

Sob demanda, a cada sessão com a equipe do RAN. A próxima deve usar as colunas
novas do log, para reproduzir as interações sem exportar o índice.

## Observações sobre dados sensíveis

- O histórico comentado e o log podem conter nomes de servidores e perguntas
  sobre espécies ameaçadas. O HTML comentado fica fora do repositório.
- Nada dos scripts de diagnóstico escreve no Qdrant ou no PostgreSQL. O cache
  do índice fica fora do repositório.
- `resposta_original` (respostas retidas) só existe no banco e nunca volta na
  API.
- Coordenadas de ocorrência continuam fora da base até o ADR 0009 ser aceito e
  implementado.

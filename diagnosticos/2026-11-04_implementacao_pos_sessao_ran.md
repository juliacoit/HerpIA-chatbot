# Implementação pós-sessão RAN — citações, estados, logging e ADRs de escopo e coordenadas

_2026-11-04, máquina de desenvolvimento. Branch `fix/citacoes-estados-logging`, sem merge e sem
push. Base: `feature/avaliacao-ragas` (`69f0267`), e não a `main`. Ver "Divergências", item 1._

Referências: `diagnosticos/2026-11-04_sessao_supervisionada_ran.md` (diagnóstico) e
`diagnosticos/casos_sessao_ran_2026-10-26.yaml` (casos propostos).

## Commits

| Commit | O quê |
|---|---|
| `bfd413c` fix(citacoes) | Uma citação por seção da ficha SALVE (prioridade 1, backend) |
| `8950168` feat(perguntar) | `tipo_saida` sempre na resposta; mensagem de retenção sem "fontes citadas abaixo" (prioridade 3, backend) |
| `ff0b83c` feat(logging) | `chunk_ids`, `rota`, `tipo_saida`, `origem_retencao`, `resposta_original`, temperatura/seed + migração aditiva (prioridade 10) |
| `46c1a0f` feat(interface) | Cartão por documento com seções expansíveis; estado "sem evidência"; trechos recolhidos em retidas e sem evidência (prioridades 1 e 3, interface) |
| `fbc3252` docs(processos) | `backend_fastapi.md`, `interface_streamlit.md`, `design_system.md` |
| `cb16551` docs(decisoes) | ADR 0008 (escopo) e ADR 0009 (coordenadas), status Proposta |

Cada commit de código passa a suíte inteira sozinho.

## Parte 1 — o que foi implementado e onde

### 1.1 Citações por seção da ficha

- **`backend/services/geracao.py`:**
  - `_chave_citacao`: sem página (SALVE), a chave é `(fonte, documento, secao,
    parte)`; com página (PDF), `(fonte, documento, pagina_inicio, pagina_fim)`,
    como antes.
  - `montar_citacoes`: uma citação por chave, na ordem do primeiro chunk de
    cada uma. Garantia de cobertura: textos **distintos** de PDF que caem na
    mesma chave são concatenados com `SEPARADOR_TRECHOS` (`[…]`), em vez de o
    segundo sumir (caso do TCC em #795: partes 21 e 22 com páginas 17–18).
    Texto idêntico, como o mesmo PDF indexado em duas categorias (#799), não
    se repete.
- **`backend/schemas.py`:** `Citacao.parte`; `ChunkRecuperado.parte` e
  `ChunkRecuperado.chunk_id`.
- **`backend/services/retrieval.py`:** só o mapeamento do payload para esses
  dois campos (2 linhas). A busca, o filtro e a ordem não mudaram.
- **`interface/app.py`:**
  - `_renderizar_documento`: um cartão por documento, com um expander por
    seção ou intervalo de páginas;
  - `_renderizar_citacoes`: legenda "Citações: N documentos, M trechos".
- **`interface/apresentacao.py`** (novo, sem Streamlit): `agrupar_citacoes`
  (ordem do melhor chunk de cada documento), `rotulos_trechos` ("Conservação ·
  parte 2", "p. 14–15") e `resumo_citacoes`.
- **Docstring de `backend/services/logging_db.py` corrigida:** `citacoes`
  guarda o texto.

### 1.2 Estado "sem evidência" e respostas retidas

- **`geracao.gerar_resposta`:** calcula `tipo_saida` em todos os caminhos e o
  expõe em `PerguntarResponse.tipo_saida`. A regra é a mesma que antes só
  valia no modo de avaliação: `retida_groundedness` se não fundamentada,
  `abstencao` se a camada 0 aprovou, senão `gerada`; os caminhos `sem_chunks`,
  `sei_nao_indexado` e `contexto_excedido` vêm fixos. O modo de avaliação
  continua idêntico.
- **`apresentacao.estado_resposta`:** retida > sem evidência > fundamentada.
  Abstenção pura → `sem_evidencia`.
- **`apresentacao.titulo_trechos` + `app._renderizar_citacoes`:** em retida,
  "Trechos recuperados (não verificados)"; em sem evidência, "Trechos
  recuperados". Os dois ficam recolhidos (`st.expander`, `expanded=False`).
- **`geracao.MENSAGEM_RETENCAO`:** substitui `MENSAGEM_NAO_FUNDAMENTADA` na
  troca da resposta retida, sem "consulte diretamente as fontes citadas
  abaixo". O mesmo vale para `MENSAGEM_CONTEXTO_EXCEDIDO`.
  `groundedness.py` não mudou (Divergências, item 3).

### 1.3 Logging

- **`backend/db.py`:** migração aditiva no `_SCHEMA`, o padrão do projeto, que
  não usa Alembic: `ALTER TABLE interacoes ADD COLUMN IF NOT EXISTS ...` para
  `chunk_ids JSONB`, `rota JSONB`, `tipo_saida TEXT`, `origem_retencao TEXT`,
  `resposta_original TEXT`, `llm_temperatura DOUBLE PRECISION` e `llm_seed
  INTEGER`. Todas anuláveis e sem default; idempotente no startup.
- **`backend/services/logging_db.py`:**
  - `registrar_interacao` grava as colunas novas; `resposta_original` só
    quando `resposta_fundamentada` é False.
  - `descrever_rota(pergunta, fontes)` devolve `None` quando o roteamento não
    roda (fontes explícitas) ou `{"fonte_prioritaria", "filtros"}` quando
    roda.
- **`backend/schemas.py`:** `PerguntarResponse._origem_retencao` e
  `._resposta_original` como `PrivateAttr`. O Pydantic nunca os serializa.
- **`backend/routers/perguntar.py`:** passa rota, tipo, origem, original,
  temperatura e seed ao log.

### Migração no banco local

- **Dump antes de aplicar:**
  `/home/juliacoite/backups/herpia/interacoes_feedback_2026-11-04_pre-migracao.sql`
  (`interacoes` + `feedback`, 11 MB, sha256 `e325c2f2…a2925`), fora do
  repositório.
- **Aplicada** com `backend.db.abrir_pool` (o mesmo caminho do startup).
- **Conferências:**
  - 738 linhas antes e depois;
  - hash md5 das colunas antigas, linha a linha, idêntico antes e depois
    (`f67df01f48432edfc39f251d7f1412a0`);
  - as 7 colunas novas estão NULL em todas as linhas antigas.
- **INSERT real com as colunas novas** (`diagnosticos/scripts/verificar_insert_rollback.py`),
  com o `commit()` trocado por rollback: os tipos e o JSONB foram aceitos e a
  contagem continuou em 738.
  - **Efeito colateral:** a sequência de `id` avançou um número (802
    consumido). Os ids já têm lacunas; nada mais foi gravado.

## Testes

- **Suíte:** 70 → **102 testes, todos passando**. Novos:
  - `tests/test_citacoes.py` (8): SALVE com várias seções (#797), partes da
    mesma seção (#787), PDF com mesmo intervalo de páginas, mesmo arquivo em
    duas categorias, cobertura total chunk ↔ citação;
  - `tests/test_logging_interacoes.py` (12): colunas novas com pool falso;
    `resposta_original` só em retidas e **ausente do JSON do `/perguntar`**
    (retida lexical e retida pelo juiz); temperatura/seed; equivalência
    `descrever_rota` × `buscar_chunks_priorizados` em todas as perguntas da
    bateria + 5 extras, com `fontes` None, `[]`, `["salve"]` e as 3 fontes;
  - `tests/test_apresentacao_interface.py` (12): estados (#792, #794, #795,
    #796/#799/#801, SEI, sem chunks, contexto excedido, precedência, item sem
    `tipo_saida`) e agrupamento (#797, #787, ordem pelo melhor chunk).
- **4 testes antigos falharam pelas mudanças de contrato pedidas** e foram
  ajustados, sem afrouxar a asserção:
  - `test_sem_flag_resposta_inalterada`: o conjunto exato de chaves ganhou
    `tipo_saida`;
  - `test_modo_avaliacao_preenche_e_nao_registra`: de 2 para 3 citações,
    porque as 2 seções da mesma ficha agora são citações separadas. A ordem
    das seções também passou a ser conferida;
  - `test_modo_avaliacao_retida_traz_resposta_original` e
    `test_caminho_retida_lexical`: comparam com `MENSAGEM_RETENCAO`.
- **Prova de que a geração não mudou** (`diagnosticos/scripts/prova_geracao_inalterada.py`):
  - para #786–#801, com as 3 fontes da interface e também sem fontes (caminho
    do roteamento), grava a lista de chunks que iriam ao LLM (fonte,
    documento, seção, páginas, score, sha1 do texto) e o sha256 do prompt de
    `montar_prompt`, contra o índice real;
  - rodado no commit base antes de qualquer mudança e de novo no fim:
    **32 combinações, 160 chunks, JSON idêntico byte a byte** (sha256
    `948fed1f…a97f17` nos dois);
  - `groundedness.py`, `roteamento.py`, `PROMPT_SISTEMA` e `montar_prompt`
    não aparecem no diff contra a base.

## Critérios de aceite

Ponta a ponta com Ollama (`qwen2.5:3b-instruct`, subido pelo
`scripts/infra/subir_ollama.sh` e desligado no fim), backend e Streamlit em
`127.0.0.1`. O backend rodou com `DATABASE_URL` apontando para uma porta sem
serviço: as perguntas de teste **não** gravaram linhas em `interacoes` (regra
3). A interface foi conferida no Chromium do Playwright por CDP; o Playwright
do MCP exige o Chrome do sistema, que não está instalado (mesma limitação de
`docs/processos/design_system.md`). Screenshots no scratchpad da sessão.

| Critério | Resultado |
|---|---|
| #797: um cartão da ficha com todas as seções enviadas ao LLM, incluindo Conservação com as UCs | **Passou.** 1 cartão, 5 expanders (Visão geral, Conservação, Distribuição, População, Referências); Conservação aberto mostra o Histórico e a lista de UCs |
| #787: seções com o Histórico | **Passou.** 1 cartão; Conservação partes 1, 2 e 4 em expanders próprios; parte 1 aberta com "Nacional Brasil 2024: EN" |
| #796, #799, #801 como "sem evidência" | **Passou.** `tipo_saida="abstencao"` nas três pela API; #801 também conferida na tela (faixa "Não há evidência suficiente", trechos recolhidos em "Trechos recuperados") |
| #794 retida, com trechos recolhidos em "Trechos recuperados (não verificados)" | **Passou na tela** (retida pela camada lexical, "Bengal", como na sessão; motivo exibido; trechos recolhidos). **Ressalva:** a geração não é determinística. Em 5 rodadas pela API: 1 abstenção pura (sem evidência), 1 retida pelo juiz e 2 recusas com outra redação aprovadas como "Fundamentada" (ver Limitações) |
| #792 continua "Fundamentada" | **Passou** (`tipo_saida="gerada"`) |
| `resposta_original` nunca na API nem na interface | **Passou** (testes de endpoint; JSON sem as chaves e sem o texto) |
| Colunas novas preenchidas | **Passou** em teste unitário e no INSERT real com rollback. **Não verificado** de ponta a ponta com gravação persistida, para não escrever no banco além da migração. Pode ser feito com sua autorização |

## Limitações conhecidas

- **Recusas fora de `_PADRAO_ABSTENCAO` continuam "Fundamentada".** É o caso
  de #795, e também de 2 das 5 rodadas de #794 nesta verificação ("Não há
  informações sobre estratégias...", com o nome científico entre parênteses):
  não são abstenção pura, vão ao juiz e ele aprova. Fica assim, como pedido;
  ampliar o padrão é mexer no verificador.
- **Não-determinismo:** sem `LLM_TEMPERATURE`/`LLM_SEED`, o estado de uma
  mesma pergunta varia entre rodadas (#794 acima). A exibição está correta
  para cada `tipo_saida`; o que varia é a geração.
- **Qualidade da resposta não mudou** (fora de escopo). Na rodada de #797 o
  modelo disse que não havia lista de UCs, embora ela estivesse no trecho
  exibido. Agora o usuário consegue ver a contradição.
- **`descrever_rota` duplica a condição** de `buscar_chunks_priorizados` (com
  as mesmas funções puras). Um teste de equivalência protege; se
  `roteamento.py` mudar, o teste avisa.
- **Visual:** na sem evidência, o expander de trechos fica colado à faixa (na
  retida, a legenda do motivo separa os dois). Registrado em
  `design_system.md` como ajuste pendente.
- **`/buscar` também passou a devolver `chunk_id` e `parte`** em cada
  resultado (campos aditivos de `ChunkRecuperado`).

## Divergências entre o pedido e o código

1. **"Branch nova a partir da principal."** A `main` está 30 commits atrás do
   código diagnosticado: não tem `tipo_saida`, camada 0 nem modo de
   avaliação. Parei e perguntei; você escolheu `feature/avaliacao-ragas`. O PR
   depende de essa branch entrar na `main` primeiro, ou passa a incluí-la.
   A `feature/avaliacao-ragas` local (`69f0267`) está um commit à frente da
   do origin (`8e8caf5`).
2. **Título "Fontes citadas".** É o título do HTML exportado da sessão; a
   interface usava "Citações (N)". Mantive "Citações" na fundamentada (agora
   "Citações: N documentos, M trechos") e troquei por "Trechos recuperados
   (não verificados)" na retida e "Trechos recuperados" na sem evidência.
3. **Mensagem de retenção.** O texto que manda consultar "as fontes citadas
   abaixo" fica em `groundedness.MENSAGEM_NAO_FUNDAMENTADA`, e
   `groundedness.py` está fora de escopo. A mensagem nova ficou em
   `geracao.py`, que é quem troca a resposta pela mensagem. A constante antiga
   continua existindo, sem uso no backend. Apliquei o mesmo à mensagem de
   contexto excedido, que também mostra o estado "retida".
4. **Precedência "retida > sem evidência > fundamentada".** Aplicada ao pé da
   letra, o bloqueio do SEI (que vem com `resposta_fundamentada=False`)
   passaria a "retida". "Retida" ficou definida como `resposta_fundamentada`
   False **com** chunks recuperados; o SEI continua "sem evidência", como
   antes.
5. **Rota "o que `buscar_chunks_priorizados` decidiu".** A função não devolve
   a decisão, e `roteamento.py` está fora de escopo. A rota é recalculada em
   `logging_db.descrever_rota`, com teste de equivalência (Limitações).
6. **`chunk_id`** não existia em `ChunkRecuperado`: foi lido do payload em
   `retrieval.py` (só mapeamento, sem mudança de lógica). O mesmo vale para
   `parte`, necessário para a chave de citação.
7. **Status dos ADRs:** o template usa "Proposta"; segui o template.
8. **Versionamento de schema:** não há Alembic; o padrão é o `_SCHEMA`
   idempotente de `backend/db.py`, e a migração seguiu esse padrão.
9. **Expander aninhado:** `docs/processos/interface_streamlit.md` dizia que o
   Streamlit não permite. Na versão instalada (1.63) funciona; testado e
   registrado.

## Parte 2 — ADR 0008, escopo herpetofauna (Proposta, não implementado)

`docs/decisoes/0008-escopo-da-base-herpetofauna.md`. Resumo:

- **Mecanismo:** campo de payload `escopo` (`herpetofauna`/`fora`) +
  `escopo_regra`, gravado com `set_payload` pelo id `uuid5(chunk_id)` (padrão
  de `sincronizar_payload_salve.py`), sem reindexar. O filtro vai em
  `FILTRO_ACESSO`, ligado por `ESCOPO_PADRAO`.
- **Regras e contagens** (`diagnosticos/scripts/adr_escopo_simulacao.py`,
  offline): SALVE 20.069 + PANs herpeto 2.222 (62 docs, com 2 arquivados em
  outros PANs) + PANs territoriais por conteúdo ~132 + Monitora herpeto 230
  (4 docs) ≈ **22.650 chunks em escopo (≈38%)**.
- **Classificação por conteúdo:** usa o mesmo dicionário SALVE da prioridade
  6. A variante com nome comum de uma palavra é inaceitável, porque os termos
  que mais disparam são falsos positivos ("cunha", "pintada", "cecilia",
  "cipo"). Recomendação: variante estrita (binômio + sinônimo + nome comum
  composto), com 132 chunks de 7.552.
- **Monitora:** os 4 documentos herpeto, mais uma tabela curada das linhas de
  herpetofauna do `INTRANETEstrutura` (anuros, lagartos e as linhas de
  quelônios da p. 2). O resto do programa sai, inclusive o que responde A3.
- **Fora de escopo:** recomendação de léxico de outros táxons + ausência de
  qualquer termo herpetológico, com novo `tipo_saida="fora_de_escopo"` → sem
  evidência. "A onça come jacaré?" não é recusada.
- **Impacto:** A3 e F5 mudam de gabarito; casos O1, M7–M9 e N2–N4 da sessão
  mudam; o boilerplate de PANs de outros táxons sai da disputa; a prioridade 2
  deve ser decidida depois de medir com o filtro ligado.
- **Reversível** por configuração e reclassificação; nada é apagado.
- **Questões em aberto:**
  - tartarugas marinhas nos relatórios PMP-BP (1.091 chunks de PANs de outros
    táxons que mencionam espécie SALVE): entram ou não?
  - documentos institucionais do Monitora: perder ou manter linhas curadas?
  - regra por conteúdo ou lista explícita para os PANs territoriais?
  - texto da mensagem de fora de escopo.

## Parte 3 — ADR 0009, coordenadas (Proposta, não implementado)

`docs/decisoes/0009-coordenadas-de-ocorrencia.md`. Resumo:

- **Conflitos citados literalmente,** com redação proposta em diff, não
  aplicada:
  - os padrões `coordenada_decimal`/`coordenada_dms` (`redigivel=True`) e a
    docstring de `regras_pii.py`;
  - duas regras do `CLAUDE.md`;
  - `docs/fontes-de-dados.md`, `coleta_salve_detalhado.md`,
    `classificacao_sensibilidade.md`, a decisão 7 dos critérios da bateria e
    os ADRs 0002/0004.
- **Variantes:**
  - **A (recomendada):** permissão só para os registros do SALVE; os PDFs
    continuam redigidos;
  - **B:** também os PDFs. Exige rechunk de 30 documentos e um extrator
    espécie↔coordenada.
- **Armazenamento:** tabela `ocorrencias` no PostgreSQL (espécie, lat/long,
  datum, precisão, município, UF, UC, data, fonte, id do registro SALVE,
  sensibilidade, data de exportação). Rota estruturada por template, **sem
  LLM**. Log só com os ids dos registros, não as coordenadas.
- **Ingestão:** piloto de uma espécie em `export=reg` antes de qualquer coleta,
  para verificar formato, campos, datum, volume, cadência e, sobretudo, se a
  exportação pública já generaliza registros sensíveis. Nenhuma coleta feita.
- **Sensibilidade:** `autorizado` (como hoje), `autorizado_local` (exibível a
  usuário autenticado, nunca vai a API externa; o bloqueio do RAGAS já falha
  fechado) e `sensivel`.
- **Questões em aberto:**
  - coordenadas podem ir ao juiz externo do RAGAS?
  - a permissão vale também para os PDFs (3.174 substituições em 30 docs)?
  - há restrição por espécie (CR, alvos de tráfico)?
  - o login é pré-requisito?
  - log sem coordenadas?
  - download de CSV pela interface?

## Estado do ambiente ao final

- Backend, Streamlit e Ollama desligados (o Ollama estava parado antes e foi
  subido só para a verificação).
- Qdrant sem escrita. PostgreSQL com a migração aditiva aplicada e nada mais
  (a única outra escrita foi o INSERT desfeito por rollback, que consumiu o
  id 802).
- `.env` intocado e fora do versionamento.

# Avaliação offline com RAGAS — Fase 0 (diagnóstico)

Data: 2026-10-14. Branch: `experimento/comparacao-geradores`.

Somente leitura: nenhum arquivo de código foi alterado, nenhum pacote foi
instalado e nenhuma chamada paga foi feita. Os pacotes `ragas` e `instructor`
foram baixados só como wheel, num diretório temporário, para ler o código-fonte.

> **Atenção ao estado do repositório.** `backend/services/geracao.py`,
> `groundedness.py` e `llm.py` têm alterações **não commitadas** (rodada 2 de
> juízes). Entre elas está o caminho `ContextoExcedidoError`, citado abaixo. A
> Fase 1 deve partir de um commit dessas alterações, senão o diff da avaliação
> fica misturado com o da rodada 2.

---

## 1. `montar_prompt`: o texto dos contextos

`backend/services/geracao.py:93`:

```python
def montar_prompt(pergunta: str, chunks: list[ChunkRecuperado]) -> str:
    trechos = "\n\n".join(
        f"[Trecho {i + 1} — fonte: {c.fonte}, documento: {c.documento}]\n{c.texto}"
        for i, c in enumerate(chunks)
    )
    return f"{PROMPT_SISTEMA}\n\nTrechos recuperados:\n{trechos}\n\nPergunta: {pergunta}\n\nResposta:"
```

- **Sem truncamento, limpeza nem deduplicação:** usa `c.texto` inteiro, de todos os chunks.
- **Sem reordenação:** respeita a ordem recebida. Essa ordem vem do roteamento
  (`roteamento.py:278`, `prioritarios + complementares`). A única
  deduplicação do pipeline está ali (`_chave_chunk`) e acontece **antes** de
  `montar_prompt`.
- **O único acréscimo** é o cabeçalho `[Trecho i — fonte: …, documento: …]`,
  que vem antes de cada texto.
- **Truncamento silencioso não existe mais.** Desde `truncate=False`
  (`llm.py:70`), um prompt que não cabe no contexto vira `ContextoExcedidoError`.

**Proposta:** `ContextoAvaliacao.texto = chunk.texto`, sem o cabeçalho. Fonte
e documento já vão em campos próprios. Para o RAGAS, colocar o cabeçalho
dentro do contexto só adicionaria ruído às métricas de contexto. O texto é
idêntico, byte a byte, ao que entra no prompt depois do cabeçalho.

O juiz interno (`groundedness.py:498`) monta os trechos com o **mesmo**
formato e a mesma lista de chunks. Contextos do RAGAS e do juiz interno são,
portanto, o mesmo material.

## 2. `montar_citacoes`: deduplica

`geracao.py:101`:

```python
chave = (c.fonte, c.documento, c.pagina_inicio, c.pagina_fim)
if chave in vistas:
    continue
```

- **Deduplica** por (fonte, documento, página inicial, página final), sem
  levar a seção em conta. Assim, `len(citacoes) <= len(chunks)`.
- `Citacao.texto = c.texto` vem do **primeiro** chunk de cada chave. Os textos
  de outros chunks com a mesma chave (por exemplo, seções diferentes da mesma
  ficha SALVE) **não aparecem** na resposta.
- **Consequência:** não dá para reconstruir os contextos a partir de
  `citacoes`. O campo novo `avaliacao.contextos` é necessário mesmo.

## 3. Saídas fixas de `gerar_resposta`

`MENSAGEM_NAO_FUNDAMENTADA` (`groundedness.py:84`):

> "Não foi possível confirmar que a resposta gerada está totalmente apoiada nos
> trechos recuperados da base de conhecimento, então ela foi retida para evitar
> apresentar uma informação não verificada. Tente reformular a pergunta de forma
> mais específica ou consulte diretamente as fontes citadas abaixo."

| `tipo_saida` proposto | Onde | Texto devolvido | LLM chamado? | citações |
|---|---|---|---|---|
| `sem_chunks` | `geracao.py:132` | "Não há evidência suficiente na base de conhecimento…" | não | `[]` |
| `sei_nao_indexado` | `geracao.py:141` | "A base de conhecimento ainda não tem documentos do SEI…" | não | `[]` (mas **há** chunks) |
| `contexto_excedido` | `geracao.py:163` (não commitado) | "Não foi possível gerar a resposta: os trechos…" | tentou, erro 400 | sim |
| `retida_groundedness` | `geracao.py:184` | `MENSAGEM_NAO_FUNDAMENTADA` | sim | sim |
| `gerada` | `geracao.py:188` | texto do LLM | sim | sim |

As quatro saídas previstas no prompt conferem com o código. Há três detalhes
que afetam a avaliação:

- **`sei_nao_indexado` tem chunks.** Eles foram recuperados, mas não foram para
  o prompt, porque o retorno acontece antes de `montar_prompt`. Proposta:
  `contextos = []` nesse caminho, já que "contextos = o que foi para o prompt".
  Os chunks recuperados ficariam num campo à parte só se você quiser medir a
  rota.
- **A retenção tem três origens diferentes, todas com `resposta_fundamentada=False`:**
  1. o hard gate lexical (`groundedness.py:541`), sem chamada ao LLM;
  2. o veredito "NÃO" do juiz por LLM;
  3. **o juiz não conseguiu julgar** (`groundedness.py:518`, quando o prompt do
     juiz estoura o contexto e devolve "Verificação não realizada").

  Os casos do tipo 3 não são uma discordância de verdade. Se entrarem na
  matriz 2×2 de concordância, ficam contados como "juiz interno disse NÃO".
  Proposta: um campo `origem_retencao: Literal["lexical", "juiz_llm", "juiz_nao_realizado"] | None`
  dentro de `DadosAvaliacao`, para separar esses casos na matriz.
- **Abstenção pura é aprovada sem chamar o juiz** (`groundedness.py:548`):
  `tipo_saida = "gerada"`, com `resposta_fundamentada=True` e sem justificativa.
  Não é um caminho fixo; aviso apenas para leitura do relatório.

Fora de `gerar_resposta`, o router devolve **HTTP 503** se o Ollama cair
(`routers/perguntar.py:234`). O script de avaliação deve registrar esse caso
como erro de coleta, não como `tipo_saida`.

## 4. `nivel_sensibilidade`

**Pelo código (sem abrir o Qdrant):**

- `scripts/processamento/gerar_chunks.py:208` e `:262`: os dois caminhos de
  geração de chunk (ficha SALVE e PDF de monitora/pans) gravam o valor fixo
  `"nivel_sensibilidade": "autorizado"`.
- `backend/services/retrieval.py:304`: toda busca do backend filtra
  `nivel_sensibilidade == "autorizado"` (`FILTRO_ACESSO`). Chunks com qualquer
  outro valor, inclusive `None` ou campo ausente, **nunca chegam** a
  `/perguntar`.

Então, se o índice foi gerado só por `gerar_chunks.py`, o esperado é
**100 % `autorizado`**. A contagem real confirma isso.

**Contagem real (2026-10-14):**

| fonte | `autorizado` | outro valor | ausente/`None` |
|---|---:|---:|---:|
| monitora | 7.220 | 0 | 0 |
| pans | 31.796 | 0 | 0 |
| salve | 20.069 | 0 | 0 |
| **total** | **59.085** | 0 | 0 |

Os 59.085 pontos da coleção `ran_herpetofauna` estão todos como `autorizado`.
A contagem com o filtro `FILTRO_ACESSO` também deu 59.085.

**Como foi feita:** o Qdrant roda em modo arquivo local (`QDRANT_LOCAL_PATH`),
que trava a pasta para um único cliente. Por isso a contagem foi feita **com
o backend parado**: um único `QdrantClient(path=…)`, aberto por
`retrieval.conectar_qdrant`, fez um `scroll` só com o payload de `fonte` e
`nivel_sensibilidade`, sem vetores. O cliente foi fechado antes de o backend
subir, e o índice não foi alterado.

**Lista permitida (decisão de 2026-10-14):** `nivel_sensibilidade == "autorizado"`,
para todas as fontes (monitora, pans, salve). A checagem do script de
avaliação **falha fechado**: qualquer outro valor, inclusive `None` ou campo
ausente, bloqueia o caso inteiro antes de qualquer chamada à API.

## 5. Bateria existente

- **Onde:** `scripts/teste_perguntas_dominio.py`.
- **Formato:** Python, não JSON.
  - `CASOS_TESTE: list[dict]` (linha 66), com chaves `id`, `categoria`,
    `pergunta` e `objetivo`.
  - `ESPERADO: dict[str, tuple[str, set[str]]]` (linha 348), com
    `responder` / `recusar` / `corrigir_premissa` e as fontes que precisam ser
    citadas.
  - Dois `assert` mantêm os dois em sincronia.
  - `CASOS_TESTE_PENDENTES_SEI` (K1) fica fora da bateria.
- **Casos:** 36. A=3, B=3, C=3, D=4, F=6, G=5, H=2, I=1, J=1, L=8.
- **Identificação:** a primeira letra do `id` é a categoria (`--categorias G,L`
  filtra por `c["id"][0]`).
- **Como chama a API:** `rodar_caso` (linha 450) faz
  `client.post("/perguntar", json={"pergunta": ..., "top_k": top_k})`, sem
  `fontes`, e lê `X-LLM-Uso` com `json.loads(resp.headers.get("X-LLM-Uso", "[]"))`.
  O header é uma lista de `{prompt_eval_count, eval_count, num_ctx}`, uma
  entrada por chamada ao Ollama (geração e juiz).
- **`top_k` padrão da bateria: 8.** O padrão da API é 5. O exemplo do
  `casos.jsonl` no prompt usa `top_k: 5`. Se a avaliação RAGAS deve ser
  comparável com as baterias anteriores, o `top_k` deveria ser **8**.
  **Decidido:** o valor do frontend, 5 (ver "Decisões", item 2).
- **Outro material reaproveitável:** `diagnosticos/juizes/conjunto_rotulado.jsonl`
  traz casos com `trechos` e rótulos humanos de groundedness (rodada 2). Não
  serve como gabarito do RAGAS, mas serve para **calibrar o próprio
  `Faithfulness`** contra rótulos humanos, sem passar pelo backend.

**Proposta para não duplicar:** o `avaliacao/casos.jsonl` guarda só o que a
bateria não tem: `id`, `reference`, `fonte_esperada` e `top_k` opcional. A
`pergunta` e a `categoria` são lidas de `CASOS_TESTE`, importado do script, e
o script valida que todo `id` do JSONL existe na bateria. Isso diverge um
pouco do formato do prompt, que repete `user_input`. **Decidido:** formato
enxuto (ver "Decisões", item 3).

## 6. Verificar a rota sem mudar o roteamento

A rota não aparece na resposta, mas **as funções que a decidem são puras**,
sem Qdrant nem LLM, e podem ser importadas pelo script de avaliação:

- `roteamento.detectar_fonte_prioritaria(pergunta)` devolve `"salve"` ou `None`.
- `roteamento.detectar_filtros_salve(pergunta)` devolve os filtros de
  bioma/categoria/grupo/estado aplicados.

**Proposta, com duas checagens determinísticas:**

1. **Decisão da rota:** recalcular `detectar_fonte_prioritaria(pergunta)` e
   comparar com `fonte_esperada`. Isso pega regressões no regex, por exemplo
   os falsos positivos D3/A2 já documentados.
2. **Efeito da rota:** nos contextos devolvidos, conferir que
   `contextos[0].fonte == fonte_esperada` e calcular a fração de contextos da
   fonte esperada. "Todos os contextos" seria rígido demais: quando o SALVE
   não preenche o `top_k`, o roteamento completa com outras fontes
   (`roteamento.py:262`). Como os chunks prioritários vêm **primeiro**, o
   primeiro contexto é um bom indicador.

A ressalva: a checagem 1 testa a mesma função que a produção usa, então ela
detecta regressão, não erro de especificação. Só a checagem 2 confirma o efeito
de ponta a ponta. A fonte esperada do `ESPERADO` (por exemplo `{"pans", "salve"}`)
é sobre **citações** e não serve direto como `fonte_esperada` de rota.

## 7. Settings (`backend/config.py`)

- `pydantic-settings`: `class Settings(BaseSettings)` com
  `SettingsConfigDict(env_file=RAIZ / ".env", extra="ignore")`.
- Os nomes são snake_case em Python e a variável de ambiente correspondente
  é o mesmo nome em maiúsculas, sem distinção de caixa: `groundedness_verificar`
  vira `GROUNDEDNESS_VERIFICAR`.
- O padrão para booleanos já existe: `groundedness_verificar: bool = True`.
- `obter_settings()` usa `@lru_cache`, então mudar o `.env` exige reiniciar o
  backend. Nos testes, use `app.dependency_overrides[obter_settings]`.
- Flag nova: `permitir_modo_avaliacao: bool = False`, que vira
  `PERMITIR_MODO_AVALIACAO`. Documentar em `.env.example` com `false`.
- `.env` está no `.gitignore` (linhas 7–9: `.env`, `.env.*`, `!.env.example`).
  A `ANTHROPIC_API_KEY` não entra em `Settings` do backend: só o script de
  avaliação a lê.

**Testes:** o repositório **não tem suíte de testes** (nenhum `test_*.py` ou
`conftest.py`, e `pytest` não está instalado). A Fase 1 precisa criar
`tests/` e acrescentar `pytest` e `pytest-asyncio`, de preferência no
`requirements-avaliacao.txt` ou num `requirements-dev.txt`, não em
`requirements.txt`. **Decidido:** `requirements-dev.txt` (ver "Decisões", item 6).

## 8. Dependências

Ambiente atual: Python 3.14.4, pydantic 2.13.4, httpx 0.28.1, fastapi
0.141.1, sentence-transformers 5.6.0. Não há Dockerfile do backend: o
`docker-compose.yml` só sobe as imagens `postgres:16` e `qdrant/qdrant`. O
risco de o RAGAS entrar na imagem de produção hoje é nulo. Mesmo assim, ele
fica em `requirements-avaliacao.txt`.

### 8.1 Versão do `ragas` e CVE

- **A versão mais recente no PyPI é 0.4.3**, que está **dentro** da faixa
  afetada pela CVE-2026-6587 (SSRF, 0.2.3–0.4.3). **Não existe versão
  corrigida**: o advisory registra que o mantenedor não respondeu.
- **Onde está o código afetado:**
  `ragas/metrics/collections/multi_modal_faithfulness/util.py`
  (`_try_process_url` / `_try_process_local_file`). É o único arquivo de
  `metrics/collections` que faz requisições HTTP.
  - Ele é acionado por `retrieved_contexts` passados à métrica
    **`MultiModalFaithfulness`**, que não vamos usar.
  - O módulo é **importado** junto com `ragas.metrics.collections`, mas a
    função só roda se a métrica for chamada.
  - Nossos contextos vêm do nosso próprio backend.
- **Recomendação:** fixar `ragas==0.4.3` e seguir com estas mitigações:
  - nunca usar as métricas multimodais (`MultiModalFaithfulness` e `MultiModalRelevance`);
  - rodar só no PC de desenvolvimento, que é offline e sob demanda;
  - registrar o risco no ADR e reavaliar quando sair uma versão nova.

  A alternativa seria fixar 0.2.2, anterior à faixa, mas ela não tem
  `metrics.collections` nem `llm_factory(client=…)`, o que inviabiliza a
  especificação. **Decidido:** 0.4.3 com as mitigações (ver "Decisões", item 4).

### 8.2 `llm_factory` com `AsyncAnthropic` e `claude-sonnet-5-5`

Conferido no código-fonte do wheel 0.4.3 (`ragas/llms/base.py:579`).
**A chamada do prompt, como está escrita, não funciona.** São três problemas,
e todos têm solução sem fork:

1. **`provider` tem padrão `"openai"`.**
   `llm_factory("claude-sonnet-5-5", client=AsyncAnthropic())` tentaria tratar
   o cliente como OpenAI. É preciso passar `provider="anthropic"`.
2. **`tool_choice` forçado dá 400.** Com `provider="anthropic"`, o ragas usa
   `instructor.from_anthropic(client)` (`base.py:557`), cujo modo padrão é
   `Mode.TOOLS`. Nesse modo, o instructor envia
   `tool_choice={"type": "tool", ...}`
   (`instructor/v2/providers/anthropic/handlers.py:402`). No
   `claude-sonnet-5-5` e no `claude-haiku-5-5`, `tool_choice` `tool`/`any`
   retorna **400**.
   - O instructor só força quando `tool_choice` não vem nos kwargs
     (`handlers.py:383`), e o ragas repassa kwargs extras do `llm_factory`
     para cada chamada (`base.py:771`).
   - **Contorno:** `llm_factory(..., tool_choice={"type": "auto"})`. A ferramenta
     continua `strict` pelo schema. Se o modelo não chamar a ferramenta, o
     instructor faz retry de validação.
3. **Parâmetros de amostragem dão 400.** `InstructorModelArgs` tem padrão
   `temperature=0.01`, `top_p=0.1` e `max_tokens=1024` (`base.py:724`), e
   para Anthropic eles são repassados sem mapeamento (`base.py:801`). No
   `claude-sonnet-5-5` e no `claude-haiku-5-5`, **qualquer valor não padrão de
   `temperature`/`top_p` retorna 400.** Portanto:
   - **"temperatura 0" não é suportada nesses modelos.** O determinismo vem
     de fixar o modelo, e não da amostragem. Quero registrar isso no ADR.
   - **Contorno:** depois de criar o LLM, remover `temperature` e `top_p` de
     `llm.model_args`.
   - **`max_tokens=1024` é baixo:** os dois modelos rodam com pensamento
     adaptativo por padrão, e o pensamento consome `max_tokens`. Proposta:
     `max_tokens=8192` e `output_config={"effort": "low"}`, a ser validado.

O cliente async é detectado automaticamente (`_check_client_async`,
`base.py:780`). Os IDs `claude-sonnet-5-5` ($2/$10 por MTok) e
`claude-haiku-5-5` ($0,10/$0,50 por MTok até 100k tokens de prompt) são
válidos.

Os contornos 2 e 3 dependem de comportamento interno do ragas e do
instructor. **Só dá para confirmar com uma chamada real.** Proposta para a
Fase 3: um *smoke test* de **uma** chamada `Faithfulness` em um caso, com
custo estimado abaixo de US$ 0,05, feito apenas com sua autorização. Ele
seria a "primeira execução paga", antes da bateria inteira.

### 8.3 Conflitos (resolução com `pip install --dry-run`, sem instalar nada)

`ragas==0.4.3` + `anthropic` resolvem sobre o venv atual **sem alterar**
pydantic, httpx, fastapi nem numpy. Pontos de atenção:

- **`instructor` regride para 1.3.2** se não for fixado. É uma versão antiga,
  sem o handler Anthropic moderno. Com `instructor>=1.11`, resolve para
  **1.17.0**, junto com `openai` 3.3.0, sem conflito. Fixar explicitamente.
- **Não usar o extra `instructor[anthropic]`:** ele fixa `anthropic==0.93.0`,
  que conflita com o SDK 1.14.0 (atual). O SDK 1.x da Anthropic usa `httpx2`,
  um pacote separado do `httpx` 0.28 que o backend e a interface usam. Os dois
  convivem.
- O ragas puxa a pilha `langchain` 1.x, `langgraph`, `datasets` 5.1 e
  `scikit-network`, todas só no venv de avaliação. Com Python 3.14, algum
  desses pacotes pode precisar compilar a partir do código-fonte; só a
  instalação real confirma isso.
- **Telemetria:** o ragas envia eventos de uso por padrão (`track(...)` em
  `llm_factory` e nas chamadas; `ragas/_analytics.py`). Os eventos levam
  provider e modelo, não o texto. Mesmo assim, o script deve definir
  `RAGAS_DO_NOT_TRACK=true` antes de importar o ragas.
- `HuggingFaceEmbeddings` existe em `ragas/embeddings/huggingface_provider.py`
  e usa `sentence-transformers`, que já está instalado. O BGE-M3 já está em
  cache local.

**Proposta de `requirements-avaliacao.txt`:**

```
-r requirements.txt
ragas==0.4.3          # CVE-2026-6587 sem correção; ver ADR (não usar métricas multimodais)
instructor==1.17.0    # sem o extra [anthropic], que fixa anthropic==0.93
anthropic==1.14.0
pytest
pytest-asyncio
```

As métricas pedidas existem em `ragas.metrics.collections`: `Faithfulness`,
`AnswerRelevancy`, `ContextPrecisionWithReference` e `ContextRecall`. As
assinaturas conferem:
- `Faithfulness.ascore(user_input, response, retrieved_contexts)`;
- `AnswerRelevancy.ascore(user_input, response)`.

O `MetricResult` tem `.value` e `.reason`.

---

## Decisões (2026-10-14)

1. **Lista permitida:** `nivel_sensibilidade == "autorizado"`, todas as fontes.
   Falha fechado para qualquer outro valor, inclusive `None`.
2. **`top_k`:** o valor do frontend. `interface/app.py:183` usa
   `st.slider(..., value=5)`, e `interface/cliente_api.py:38` usa `top_k: int = 5`.
   O padrão é **5**, igual ao `top_k_padrao` do backend. Por isso, a avaliação
   RAGAS **não** é diretamente comparável às baterias de
   `diagnosticos/baterias/`, que rodaram com `top_k=8`. O relatório da
   avaliação deve registrar o `top_k` nos metadados.
3. **`casos.jsonl` enxuto:** só `id`, `reference` e `fonte_esperada`. A pergunta
   e a categoria são lidas de `CASOS_TESTE`. Import verificado com um audit
   hook do Python (`sys.addaudithook`):
   - nenhuma escrita em arquivo, subprocesso ou conexão de rede durante o import;
   - o único efeito colateral é `sys.path.insert(0, RAIZ)` (linha 57), que
     acrescenta a raiz do repositório e de que o script de avaliação precisa de
     qualquer forma;
   - os dois `assert` de sincronia (linhas 386–387) rodam no import, o que é
     desejável;
   - `main()` está protegido por `if __name__ == "__main__"`.
4. **`ragas==0.4.3`** aceito com as mitigações da CVE-2026-6587 (seção 8.1).
   Será registrado no ADR.
5. **`DadosAvaliacao`:** com `origem_retencao`; `contextos = []` no caminho
   `sei_nao_indexado`; e **`tipo_saida = "abstencao"`** novo, para abstenção
   pura aprovada sem juiz (`groundedness.py:548`), distinta de `gerada`.
6. **Dependências de teste:** `requirements-dev.txt` com `pytest` e
   `pytest-asyncio`, incluído por `requirements-avaliacao.txt` (`-r`).
7. **Branch:** a Júlia commita a rodada 2, e depois sai
   `feature/avaliacao-ragas` a partir desse commit.

### Versão do Python

**Não existe especificação de Python 3.11 no projeto.** Não há
`pyproject.toml`, `.python-version`, `runtime.txt` nem Dockerfile do backend.
O que existe:

| Onde | O que diz |
|---|---|
| `venv/pyvenv.cfg` | `version = 3.14.4`, `executable = /usr/bin/python3.14` (o Python do sistema) |
| `docs/processos/coleta_*_detalhado.md`, `SETUP_DOWNLOAD_REMOTO.md` | "Python 3.10+" |
| skill `icmbio-rag` (`~/.claude/skills/icmbio-rag/SKILL.md:124`) | "Prefer: Python 3.13" (preferência, não requisito) |
| `diagnosticos/comparacao-geradores-rodada1.md:38` | "a documentação do projeto diz 3.11", afirmação sem fonte no repositório |

Neste PC só existe o interpretador 3.14 (`/usr/bin/python3.14`): não há 3.11
nem pyenv/uv. Todas as dependências atuais rodam em 3.14.4. Um
`pip install --dry-run --only-binary=:all:` de `ragas==0.4.3`,
`instructor==1.17.0`, `anthropic==1.14.0`, `pytest` e `pytest-asyncio`
resolveu **só com wheels prontos para 3.14**, sem compilar nada. Os requisitos
mínimos também são compatíveis: anthropic ≥3.10, instructor ≥3.9, ragas ≥3.9.

**Sugestão (a decidir):** formalizar "Python 3.14" (`.python-version` +
README) e corrigir a frase do relatório da rodada 1. Isso deveria valer
também para o PC servidor, quando o backend for para lá.

## Fontes

- Advisory da CVE-2026-6587:
  https://advisories.gitlab.com/pypi/ragas/CVE-2026-6587/ e
  https://osv.dev/vulnerability/GHSA-95ww-475f-pr4f
- Código-fonte de `ragas==0.4.3` e `instructor==1.17.0` (wheels do PyPI,
  lidos localmente).
- Restrições de amostragem e `tool_choice` do `claude-sonnet-5-5` e do
  `claude-haiku-5-5`: referência da Claude API (skill `claude-api`, cache de
  2026-10-06).

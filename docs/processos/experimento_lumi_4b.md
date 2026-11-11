# Experimento: Lumi-4B como gerador do HerpIA

- **Status:** 🔶 Em desenvolvimento. Fases 0 a 3 concluídas; Fase 4 (baterias) em andamento
- **Última atualização:** 2026-11-11
- **Responsável(eis):** Júlia (decisões), Claude Code (execução supervisionada)

> Experimento isolado. Nada vai para produção nem para o servidor do RAN. Sem as
> variáveis de ambiente novas, o HerpIA continua usando o `qwen2.5:3b-instruct`
> exatamente como hoje.

## Objetivo

Avaliar o `ceia-br/lumi-4b` (CEIA-UFG, publicado em 28/10/2026) como possível
substituto do LLM de geração de 3B (ADR 0006). A comparação usa as mesmas
condições em quatro configurações:

| Config | `LLM_MODEL` | `LLM_THINK` |
|---|---|---|
| C1 (linha de base) | `qwen2.5:3b-instruct` | — |
| C2 | `nemotron-3-nano:4b` | `false` |
| C3 | `lumi-4b` | `false` |
| C4 | `lumi-4b` | `true` |

## Entradas

- Pesos oficiais do Hugging Face, `ceia-br/lumi-4b`, com a revisão fixada (ver "Procedência").
- `nemotron-3-nano:4b` da biblioteca do Ollama, como referência de arquitetura.
- Bateria de domínio (`scripts/teste_perguntas_dominio.py`, 36 casos) e avaliação RAGAS (`avaliacao/rodar_ragas.py`, 36 casos).

## Saídas

- `~/experimentos-llm/lumi-4b-Q4_K_M.gguf`, **fora do repositório** (o `.gitignore` cobre `*.gguf`, `*.safetensors` e `modelos/`).
- `experimentos/lumi-4b/Modelfile.lumi` (Fase 2, aprovado em 2026-11-06). O `ollama create` é rodado a partir de uma cópia idêntica em `~/experimentos-llm/`, porque o `FROM ./lumi-4b-Q4_K_M.gguf` é relativo à pasta do Modelfile.
- Baterias em `diagnosticos/baterias/`, RAGAS em `diagnosticos/ragas/`, relatório `diagnosticos/AAAA-MM-DD_avaliacao_lumi_4b.md` e rascunho do **ADR 0011** com status "Proposta". Os números 0008 e 0009 estão em uso na branch `fix/citacoes-estados-logging`, e o 0010 (exportação automatizada do SEI) na `docs/decisao-sei-publicacoes`.

## Ferramentas

Ficam fora do repositório, em `~/experimentos-llm/`, e **não entram no `requirements.txt`**:

- `llama.cpp` no commit `c6a0ff11a0fe` (2026-11-04), com `llama-quantize` compilado só para CPU.
- `venv-conversao/` com Python 3.14.4, torch 2.11.0+cpu, **transformers 4.57.6**, `huggingface_hub[cli]` e `cmake` (instalado por pip).
- Ollama nativo **0.32.9** (`~/.local/bin/ollama`), escutando só em `127.0.0.1:11434`. Não está no `docker-compose.yml`.

## Procedência

| Item | Valor |
|---|---|
| Commit no HF | `1c8928e189f0fb1380f5f1dab1b2e0a0fb814c6e` (last_modified 2026-10-28) |
| `model.safetensors` | 7.947.142.640 bytes · SHA256 `067b6a08844bb7b5161fbd2329299c33bf16ce422e1fbb52e24362f4d56d82cf` (confere com o LFS) |
| `lumi-4b-f16.gguf` (v2) | 7.957.646.880 bytes · SHA256 `e417b9699c42669f0912f0b4b62cf1aef71bb03f369fa318ffad3b85dc6ed8f2` |
| `lumi-4b-Q4_K_M.gguf` (v2) | 2.837.073.184 bytes (5,70 BPW) · SHA256 `88c664b5a31d2f41c40f658e57b245db8b6628473f74a1f5e51fd12267b079ba` (igual ao blob do `lumi-4b` no Ollama) |
| `nemotron-3-nano:4b` | digest `d94b6dfae26d` · blob do modelo `sha256:527db2cf…2970` (Q4_K_M) |

A v2 dos GGUFs (2026-11-06) substituiu a v1 só para corrigir `general.name` e
`general.finetune` (ver Fase 2). Os 263 tensores são idênticos byte a byte nas
duas versões, tanto no f16 quanto no Q4_K_M. Os hashes da v1 (`f85104aa…`,
`78196f3f…`) ficaram em `~/experimentos-llm/procedencia-arquivos-apagados.txt`.

## Passo a passo (o que foi feito)

### Fase 0: reconhecimento

- O backend chama o Ollama pela **API nativa `/api/generate`** (`backend/services/llm.py`, `OllamaLLMClient.generate`).
- `LLM_MODEL`, `LLM_THINK`, `LLM_NUM_CTX`, `LLM_TEMPERATURE`, `LLM_SEED` e `LLM_TIMEOUT` **já existem** (`backend/config.py`). A Fase 3 só acrescenta o filtro de `<think>`, a saída `resposta_vazia` e a linha de log.
- O juiz de groundedness usa a mesma instância do LLM, por isso `GROUNDEDNESS_VERIFICAR=false` em todo o experimento.

### Fase 1: obtenção e conversão

1. Branch `experimento/lumi-4b` criada a partir de `feature/avaliacao-ragas` (`69f0267`). A `main` não tem o código do RAGAS; o único commit dela que falta na feature é `a1fc317`, que só altera o README.
2. A conversão foi feita **a partir de `69f0267`**, sem os commits da `fix/citacoes-estados-logging`, por decisão da Júlia.
3. O worktree fica em `../chatbot-ran-icmbio-lumi`, porque o diretório principal está em uso na `fix/citacoes-estados-logging`.
4. Download com `hf download --revision <commit>`, pelo xet: 1h27, entre 0,15 e 4 MB/s.
5. **Primeira conversão (transformers 4.57.6): falhou.** O erro foi `ValueError: Tokenizer class TokenizersBackend does not exist`. A classe é do transformers 5.x, que salvou o modelo (5.8.1).
6. **Segunda conversão (transformers 5.8.1): exit 0, mas o GGUF saiu errado.** Ficou `nemotron_h_moe`, com FFN e KV zerados e campos de experts inventados.
   - Causa: no transformers 5, o `NemotronHConfig` nativo traz padrões de MoE (`num_experts_per_tok=2`, entre outros), e o conversor decide se o modelo é MoE pela presença dessa chave (`conversion/nemotron.py:454`).
   - O arquivo foi apagado; o SHA256 dele (`c60889ad…5d42`) ficou registrado em `~/experimentos-llm/procedencia-arquivos-apagados.txt`.
7. **Terceira conversão: correta.**
   - Feita com transformers 4.57.6, a partir de uma cópia com hardlinks (`CEIA-Lumi-4B-conv/`). Só o `tokenizer_config.json` foi reescrito na cópia, com `TokenizersBackend` → `PreTrainedTokenizerFast`. O original não foi alterado.
   - O tokenizador deu IDs idênticos aos do transformers 5.8.1 em 8 textos (396 tokens).
   - As 17 checagens de metadados e tensores contra o `config.json` passaram: arquitetura `nemotron_h`; camadas M/-/* = 21/17/4; FFN 12544 só nas camadas MLP; KV = 8 só nas camadas de atenção; EOS = 11 (`<|im_end|>`).
8. Quantização Q4_K_M: 51 dos 263 tensores usaram quantização de reserva, porque o `hidden_size` de 3136 não é múltiplo de 256. Isso explica os 5,70 BPW.

### Fase 2: Modelfile (concluída em 2026-11-06)

- O pull do `nemotron-3-nano:4b` funcionou, então o Ollama 0.32.9 aceita `nemotron_h`. **Não é preciso atualizar o Ollama.**
- O Modelfile do Nemotron **não tem TEMPLATE em Go**: usa `TEMPLATE {{ .Prompt }}` com `RENDERER nemotron-3-nano` e `PARSER nemotron-3-nano`, que são código embutido no Ollama.
- O código da v0.32.9 foi lido (`model/renderers/nemotron3nano.go`, `model/parsers/nemotron3nano.go`, `server/routes.go`):
  - o `/api/generate` embrulha o `prompt` como mensagem `user` e aplica o RENDERER;
  - com `think` omitido, o padrão é `true`.
- **Comparação com o `chat_template.jinja` do Lumi:** os tokens especiais, o bloco system (sempre emitido) e o final do prompt com e sem thinking são iguais. Há duas diferenças:
  - o renderizador remove `/think` e `/no_think` do texto;
  - o renderizador aplica `TrimSpace` na mensagem `user`.
  - Nenhuma das duas afeta o HerpIA: há **0 ocorrências** de `/think`/`/no_think` nos chunks e nos prompts (só contagem), e o prompt não tem espaços nas pontas.
- A referência de teste do próprio Ollama (`testdata/nemotron3nano_chat_template.jinja2`) é uma versão mais nova do template da NVIDIA, com imagens, alternadores e `reasoning_budget`. A do Lumi é a versão anterior, só de texto.
- **Lumi × `nemotron-3-nano:4b` (GGUF):**
  - vocabulário, merges e tipos de token idênticos (131.072);
  - os 263 tensores com nomes e formas iguais.
  - Isso reforça a hipótese de que o Lumi deriva do Nemotron 3 Nano 4B, mas **não a confirma**.
  - Diferenças: o pré-tokenizador é `pixtral` no Lumi e `default` no Nemotron; o `context_length` é 1.048.576 no Lumi e 262.144 no Nemotron.

Em 2026-11-06 a Júlia aprovou as três decisões pendentes: o Modelfile, a
reconversão e o teste de similaridade de pesos.

**Modelfile aprovado** (`experimentos/lumi-4b/Modelfile.lumi`):

```
FROM ./lumi-4b-Q4_K_M.gguf
TEMPLATE {{ .Prompt }}
RENDERER nemotron-3-nano
PARSER nemotron-3-nano
PARAMETER num_ctx 16384
PARAMETER temperature 0
PARAMETER top_p 1
PARAMETER stop "<|im_end|>"
```

**Reconversão (v2 dos GGUFs).**
- Mesmo conversor e mesma pasta `CEIA-Lumi-4B-conv/`, com `--metadata metadata-override-lumi.json`: `general.name = "CEIA Lumi 4B"` e `general.finetune` removido.
- A comparação v1 × v2 mostrou só essas duas chaves diferentes e **0 de 263 tensores diferentes** (SHA256 de cada tensor), no f16 e no Q4_K_M. A quantização é determinística e de novo usou reserva em 51 tensores.
- Logs: `~/experimentos-llm/conversao-f16-tf4-conv-v2.log` e `quantizacao-v2.log`.

**`ollama create lumi-4b`.** Levou 18 s. O `ollama show` confirma `nemotron_h`, 4,0B, Q4_K_M, as capacidades `completion`/`tools`/`thinking` e os parâmetros do Modelfile.

**Smoke test** pela `/api/generate`, com o mesmo corpo que o backend envia (`num_ctx` 16384, `temperature` 0, `seed` 42), numa pergunta curta sem RAG:

| `think` | Latência total | Carga | Tokens gerados | tok/s | `thinking` | Tags `<think>` na `response` |
|---|---|---|---|---|---|---|
| `false` | 20,9 s | 7,5 s (1ª carga) | 64 | 12,7 | vazio | não |
| `true` | 20,1 s | 0,2 s | 183 | 9,4 | 422 caracteres | não |

- As duas respostas saíram em português, corretas e dentro do limite de três frases.
- Com `think=true`, o PARSER separou o raciocínio no campo `thinking`, e a `response` veio limpa. **O raciocínio sai em inglês.** Isso não afeta o HerpIA, que usa só a `response`, mas fica registrado.
- O filtro de `<think>` planejado para a Fase 3 continua útil como defesa (tag sem fechamento, troca de modelo), mas, com este Modelfile, o Ollama já entrega a resposta separada.

**Paridade do tokenizador.** Comparei o `prompt_eval_count` do Ollama com `apply_chat_template` do HF (transformers 4.57.6, `chat_template.jinja` do Lumi), com `think` desligado e ligado e o modelo descarregado entre chamadas, para não haver cache de prompt. Resultado: **8 de 8 iguais**.

| Prompt | Tokens (HF = Ollama) |
|---|---|
| Pergunta curta (smoke) | 48 |
| `montar_prompt` real com 8 chunks autorizados (Monitora/PANs/SALVE) | 6.017 |
| `montar_prompt` real com 2 chunks | 2.511 |
| Bordas: acentos, aspas curvas, emoji, tabela Markdown, tab, espaços múltiplos | 99 |

- A contagem é igual com e sem thinking, porque `<think></think>` e `<think>\n` têm o mesmo número de tokens.
- O teste de bordas cobre a diferença de pré-tokenizador (`pixtral` × `default`) vista na comparação dos GGUFs: ela não muda a contagem nesses textos.

**Recursos** (RTX 2050 com 4 GB, 25 GiB de RAM, WSL2), com `num_ctx` 16384:

- `ollama ps`: 3,4 GB, **58%/42% CPU/GPU**;
- `nvidia-smi`: 1.446 MiB usados;
- RSS do `llama-server`: 2,75 GiB.
- O prompt RAG de 6 mil tokens cabe com folga no `num_ctx`.

**Similaridade de pesos Lumi × `nemotron-3-nano:4b`.**
- Cosseno entre o Lumi f16 e o Nemotron Q4_K_M dequantizado, em 20 tensores: `token_embd`, `output`, e Mamba, FFN e normas dos blocos 0, 1, 10, 20, 30 e 41.
- Dois controles:
  - **teto:** Lumi f16 × Lumi Q4_K_M, que mede só o ruído de quantização;
  - **piso:** Lumi × Nemotron em outro bloco com a mesma forma.

| Medida | Mediana | Extremo |
|---|---|---|
| Lumi × Nemotron | **0,9959** | mín. 0,9913 |
| Teto (ruído de quantização) | 0,9994 | mín. 0,9972 |
| Piso (pesos sem relação) | 0,0002 | máx. 0,87 (só nas normas, que são vetores perto de constantes) |

- Os 169 tensores F32 (normas, `ssm_a`, `ssm_d`, conv1d, `dt.bias`) **não são idênticos** bit a bit. As diferenças são pequenas: o |Δ| máximo por tipo vai de 0,016 a 0,06, e `ssm_a` chega a 0,71 porque guarda −exp(A_log).
- **Leitura:** os pesos do Lumi estão muito perto dos do Nemotron 3 Nano 4B, a distância fica pouco acima do ruído de quantização e muito longe do piso. Isso é forte evidência de que **o Lumi é um ajuste fino a partir dos pesos do Nemotron 3 Nano 4B**, e não um modelo treinado do zero com a mesma arquitetura.
- O teste **não distingue** se a origem é a versão pós-treinada (a do Ollama) ou outro checkpoint da mesma família, e **não substitui** a confirmação do CEIA.
- Scripts usados, fora do repositório, em `~/experimentos-llm/scripts-fase2/`: `comparar_gguf.py`, `smoke_lumi.py`, `paridade_{1,2,3}_*.py`, `similaridade_pesos.py` e `f32_identicos.py`. Os prompts da paridade usam chunks reais e por isso não foram guardados.

**Ollama.** O servidor nativo foi subido nesta sessão com `OLLAMA_HOST=127.0.0.1:11434` (log em `~/experimentos-llm/ollama-serve-2026-11-06.log`) e continua só em `127.0.0.1`.

### Fase 3: backend (concluída em 2026-11-06, commit `e8d5e43`)

A Júlia aprovou o início e o commit em 2026-11-06. As mudanças:

- `backend/services/llm.py`:
  - `remover_blocos_pensamento()` aplicada em `generate()`, antes do `strip()`. Cobre bloco completo (um ou vários), `</think>` sem abertura (fica o que vem depois do último), `<think>` sem fechamento (tudo a partir dele sai, e pode sobrar texto vazio) e tags em qualquer caixa. **Sem tags, o texto sai idêntico.**
  - A linha de log passou a ser `[llm] <modelo> think=<valor>: latência=… prompt=…/num_ctx saída=… pensamento=N chars`. O tamanho do raciocínio vem do campo `thinking` do PARSER, e só o tamanho é registrado. Quando o filtro remove alguma tag, entra o aviso `⚠ tags <think> removidas da resposta`.
  - O uso registrado por chamada, que vai no header `X-LLM-Uso` lido pela bateria de domínio, ganhou `think` e `latencia_s`.
- `backend/services/geracao.py` e `backend/schemas.py`: nova saída `tipo_saida="resposta_vazia"`.
  - Quando o LLM devolve texto vazio, a resposta vira uma mensagem de "não foi possível gerar", com as citações, `resposta_fundamentada=false` e os contextos na avaliação.
  - O juiz de groundedness **não** é chamado nesse caso.
- `avaliacao/rodar_ragas.py`, `avaliacao/README.md` e `docs/processos/backend_fastapi.md`: `resposta_vazia` entra entre as saídas sem texto do LLM, que ficam como `sem_texto_llm` e não são avaliadas.
- `tests/test_llm_pensamento.py` (novo, 18 testes) e um caso a mais no parametrize de `tests/test_rodar_ragas.py`. **A suíte passou de 70 para 89 testes, todos passando.**

**Verificação com o Ollama real**, chamando o `OllamaLLMClient` direto, sem uvicorn e sem gravar no banco:

| Modelo | `think` | Latência | Saída | `thinking` | Tags na resposta |
|---|---|---|---|---|---|
| `lumi-4b` | `false` | 9,2 s | 13 tokens | 0 | não |
| `lumi-4b` | `true` | 30,4 s | 274 tokens | 1.099 caracteres | não |
| `qwen2.5:3b-instruct` | não enviado | 8,6 s | 102 tokens | 0 | não |

O caminho de produção (qwen2.5, sem `think`) continua igual: o campo não é enviado e o texto não muda. A pergunta de teste não tinha RAG, então as respostas não servem para julgar qualidade, que fica para a Fase 4.

### Fase 4: avaliação (em andamento desde 2026-11-06)

A Júlia aprovou o início em 2026-11-06.

**Como cada bateria roda:** `experimentos/lumi-4b/rodar_bateria.sh <rótulo> <modelo> <think> [extras]`. O script:
- sobe o uvicorn **deste worktree** em `127.0.0.1:8010`, com os parâmetros do LLM na linha de comando;
- lê o `.env` principal só para leitura, por `uvicorn --env-file`, que não sobrescreve as variáveis passadas. O `.env` não é alterado;
- passa `QDRANT_LOCAL_PATH` **absoluto**. Relativo, ele seria resolvido contra a raiz do worktree, onde a base não existe, e o Qdrant embutido criaria uma base vazia;
- faz o aquecimento da rodada 1 (jararaca-ilhoa, `top_k=8`);
- grava `ollama ps`, `nvidia-smi` e o RSS a cada 60 s;
- roda `scripts/teste_perguntas_dominio.py --top-k 8 --timeout 960`;
- no fim, derruba o uvicorn e descarrega o modelo.
- Logs em `~/experimentos-llm/fase4-logs/`.

**Teste de infraestrutura** (C3, 1 repetição, categoria H, bateria `2026-11-06_15h38_lumi-4b.md`): ok.
- O backend confirmou a config pelo `/saude`.
- Os prompts tiveram de 4,1 a 5,5 mil tokens, o que mostra que a base real foi usada.
- Com o BGE-M3 na GPU, o uso foi de 3,7 GiB e a divisão do Lumi continuou 58/42.
- Essa bateria fica **superada**: não entra na comparação.

**Sequência de 06/11 (15:41):** C1 → C2 → C3 → calibração da C4. Só a C1 terminou: o WSL foi desligado às 17:00, com a C2 em 72 de 108 respostas. Uma nova tentativa da C2 em 10/11 (14:45) também foi interrompida pelo desligamento do WSL, às 15:16.

**Sequência de 10/11 (16:45), completa:** C2 → C3 → calibração da C4 (`--repeticoes 1 --categorias A,B,F,J,L`, 21 casos), disparada por `~/experimentos-llm/sequencia_fase4.sh` (fora do repositório; sobe o Ollama se preciso e chama `rodar_bateria.sh` para cada rótulo). Logs em `~/experimentos-llm/fase4-logs/sequencia_20261110_1645.log`.

| Config | Bateria | Latência média | Erros técnicos |
|---|---|---|---|
| C1 | `2026-11-06_15h41_qwen2.5-3b-instruct.md` | 10,0 s | 0 |
| C2 | `2026-11-10_16h46_nemotron-3-nano-4b.md` | 39,9 s | 0 |
| C3 | `2026-11-10_17h59_lumi-4b.md` | 37,8 s | 0 |
| C4 (calibração) | `2026-11-10_19h09_lumi-4b.md` | 163,3 s | 1 (F7, tempo limite de 900 s) |
| C4 | `2026-11-10_20h21_lumi-4b.md` | 138,4 s | 3 (F7 nas 3 execuções, tempo limite de 900 s) |

**Calibração da C4:** nenhum `<think>` aberto, nenhuma `resposta_vazia`; 1 caso com tempo limite (F7) e 1 caso muito lento que terminou (L8, 555 s). Dentro do limite combinado (até 2 casos), então a **C4 completa foi disparada às 20:19 de 10/11**, sem C4b (`sequencia_20261110_2022.log`).

**Classificação e relatório:** `diagnosticos/comparacao-lumi-4b-fase4.md`, com os rótulos da rodada 1 para C1, C2 e C3 e a calibração da C4. Os trechos recuperados de cada caso estão em `~/experimentos-llm/fase4-logs/contextos_bateria.json` (fora do repositório).

## Próximo passo (onde paramos)

- **Todas as baterias da Fase 4 terminaram.** A C4 completa (`2026-11-10_20h21_lumi-4b.md`) acabou às 10:45 de 11/11: latência média de 138,4 s, e o F7 estourou o tempo limite de 900 s nas 3 execuções. A máquina ficou suspensa de cerca de 20:45 a 06:22 e a bateria retomou sozinha.
- O relatório `diagnosticos/comparacao-lumi-4b-fase4.md` já tem as quatro configurações classificadas.
- A Júlia decide se quer uma C4b (`temperature=1`, `top_p=1`) por causa do F7 e do L8.
- 🛑 **A Júlia precisa revisar os rótulos** do relatório (seções 2 e 3 e Anexo A), como na rodada 1.
- 🛑 Aprovar o commit das baterias, do `rodar_bateria.sh`, do relatório e deste documento (nada foi commitado desde `e8d5e43`).
- 🛑 Antes de qualquer execução paga do RAGAS (cerca de US$ 1,90 por configuração).
- Depois: Fase 5 (ADR 0011), que depende também da confirmação da licença com o CEIA.

### Parâmetros já decididos para a Fase 4

- **36 casos × 3 repetições**, com os rótulos da rodada 1 (`diagnosticos/comparacao-geradores-rodada1.md`) e **sem nota geral**.
- Em todas as configurações:
  - `LLM_NUM_CTX=16384`, `LLM_TEMPERATURE=0` e `LLM_SEED=42`;
  - `top_k=8` na bateria e 5 no RAGAS, que é o padrão do script;
  - `GROUNDEDNESS_VERIFICAR=false`.
  - Esses valores são passados na linha de comando do uvicorn. O `.env` não muda.
  - A C1 difere da produção (8192, temperatura padrão, groundedness ligada), e isso precisa ser registrado no relatório.
- **C2 e C3 precisam de `LLM_THINK=false` explícito**, porque o Ollama liga o thinking quando o campo é omitido.
- **C4:** antes da bateria completa, rodar 1 repetição numa amostra de categorias para calibrar o timeout. Se houver `<think>` sem fechamento ou repetição em loop em mais de 2 casos, parar e avisar a Júlia, que decide sobre uma C4b com `temperature=1` e `top_p=1` (os valores do `generation_config.json` do Lumi).
- **Monitoramento durante cada bateria:** `ollama ps` (incluindo a divisão CPU/GPU), RSS do processo e `nvidia-smi`.
- Falhas técnicas (timeout, OOM, resposta vazia) ficam separadas das falhas de qualidade.
- **RAGAS:** o custo estimado é de ~US$ 1,90 por configuração com o juiz Sonnet, e exige confirmação antes de rodar. O bloqueio por `nivel_sensibilidade != "autorizado"` não muda.

## Frequência de execução

Sob demanda. Experimento único, sem rotina.

## Observações sobre dados sensíveis

- Os pesos do modelo e as ferramentas de conversão ficam fora do repositório.
- Nenhum documento das pastas `01_*` a `07_*` foi alterado. Os chunks foram lidos só para contar ocorrências de `/think` e `/no_think`.
- O Ollama escuta só em `127.0.0.1`.
- No RAGAS, só vão à API externa casos cujos contextos estejam todos com `nivel_sensibilidade = "autorizado"`.
- **Pendências que impedem qualquer recomendação de produção:**
  - o card do Lumi não documenta licença;
  - o modelo-base não está confirmado oficialmente. O teste de similaridade de 2026-11-06 (cosseno mediano de 0,996 com o `nemotron-3-nano:4b`) indica com força que o Lumi deriva dos pesos do Nemotron 3 Nano 4B. Nesse caso, a *NVIDIA Open Model License Agreement* (a mesma que acompanha o `nemotron-3-nano:4b` no Ollama, versão de 24/10/2025) provavelmente se aplica, incluindo o aviso de atribuição na redistribuição. A licença precisa ser confirmada com o CEIA, e essa avaliação não é jurídica.

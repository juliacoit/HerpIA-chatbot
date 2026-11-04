# Experimento: Lumi-4B como gerador do HerpIA

- **Status:** 🔶 Em desenvolvimento. Fases 0 e 1 concluídas; Fase 2 parada aguardando aprovação do Modelfile
- **Última atualização:** 2026-11-04
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
- `experimentos/lumi-4b/Modelfile.lumi`, ainda não criado (Fase 2).
- Baterias em `diagnosticos/baterias/`, RAGAS em `diagnosticos/ragas/`, relatório `diagnosticos/AAAA-MM-DD_avaliacao_lumi_4b.md` e rascunho do **ADR 0010** com status "Proposta". Os números 0008 e 0009 já estão em uso na branch `fix/citacoes-estados-logging`.

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
| `lumi-4b-f16.gguf` | 7.957.646.944 bytes · SHA256 `f85104aa74930b415f8ccd960bd71d9cb989a10e6b6d6cc72867fa9132a49a00` |
| `lumi-4b-Q4_K_M.gguf` | 2.837.073.248 bytes (5,70 BPW) · SHA256 `78196f3f6d122192702762c9663ca8b53c8b2f923737cd2f6c6234790f247186` |
| `nemotron-3-nano:4b` | digest `d94b6dfae26d` |

Esses dois `.gguf` devem ser substituídos se a reconversão proposta na Fase 2
for aprovada (ver "Pendências"). Nesse caso, os hashes desta tabela precisam
ser atualizados.

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

### Fase 2: Modelfile (em andamento)

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

Modelfile proposto (aguardando aprovação):

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

## Próximo passo (onde paramos)

🛑 **Aguardando três decisões da Júlia:**

1. Aprovar o Modelfile acima.
2. Reconverter para corrigir os metadados `general.name = "CEIA Lumi 4B Conv"` e `general.finetune = "conv"`, que vieram do nome da pasta de cópia. São cosméticos, mas enganam sobre a procedência. A reconversão leva cerca de 1 minuto e gera hashes novos.
3. Rodar, se ela quiser, o teste de similaridade de pesos entre Lumi e Nemotron (cosseno de alguns tensores; num fine-tune fica perto de 1) para a pendência sobre o modelo-base.

**Depois da aprovação:**

1. `ollama create lumi-4b`.
2. Smoke test com `think` false e true.
3. Teste de paridade do tokenizador (`prompt_eval_count` do Ollama × contagem do HF).
4. Registro de RAM, divisão CPU/GPU e latência.

Em seguida, a Fase 3 (backend) e a Fase 4 (avaliação). Há 🛑 antes de commitar o diff da Fase 3 e antes de qualquer execução paga do RAGAS.

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

### Mudanças planejadas no backend (Fase 3)

- `backend/services/llm.py`:
  - `remover_blocos_pensamento()` aplicada em `generate()`, cobrindo bloco completo, `<think>` sem fechamento e `</think>` sem abertura. Sem tags, o texto sai idêntico;
  - linha de log com modelo, `think`, latência e tokens.
- `backend/services/geracao.py` e `backend/schemas.py`: nova saída `tipo_saida="resposta_vazia"`.
- `avaliacao/rodar_ragas.py`: incluir `resposta_vazia` entre as saídas sem texto do LLM.
- `tests/test_llm_pensamento.py` (novo).

## Frequência de execução

Sob demanda. Experimento único, sem rotina.

## Observações sobre dados sensíveis

- Os pesos do modelo e as ferramentas de conversão ficam fora do repositório.
- Nenhum documento das pastas `01_*` a `07_*` foi alterado. Os chunks foram lidos só para contar ocorrências de `/think` e `/no_think`.
- O Ollama escuta só em `127.0.0.1`.
- No RAGAS, só vão à API externa casos cujos contextos estejam todos com `nivel_sensibilidade = "autorizado"`.
- **Pendências que impedem qualquer recomendação de produção:**
  - o card do Lumi não documenta licença;
  - o modelo-base não está confirmado. Se o Lumi derivar do Nemotron 3 Nano, a *NVIDIA Open Model License* provavelmente se aplica, incluindo o aviso de atribuição na redistribuição.

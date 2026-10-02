# Hipótese: respostas longas favorecem alucinação

_Registrada em 2026-10-02. **Experimento ainda não executado.** Fica para depois da rodada 2
(juízes de groundedness), cujas regras proíbem alterar `PROMPT_SISTEMA` e `geracao.py` enquanto
ela estiver em andamento._

## Hipótese

Os geradores locais (3–9B) produzem respostas longas porque entendem que devem dar uma resposta
completa. No caminho, completam lacunas com informação que não está nos trechos. Uma instrução
explícita de concisão, ou um teto de tokens, reduziria a alucinação sem piorar a cobertura das
respostas corretas.

## Evidência preliminar

Fonte: `diagnosticos/juizes/conjunto_rotulado.jsonl` (rascunho da rodada 2, 50 itens, quase todos
da rodada 1). Contagem de palavras da resposta:

| Rótulo | Itens | Mediana | Faixa |
|---|---|---|---|
| `nao_fundamentada` | 27 | 147 | 49–359 |
| `fundamentada` | 13 | 99 | 19–397 |
| `abstencao_honesta` | 10 | 45 | 16–257 |

As respostas não fundamentadas são, em mediana, ~50% mais longas que as fundamentadas. Mas:

- **Posição do erro.** Das afirmações sem suporte localizadas no texto (40), 12 estão na primeira
  frase; as demais se espalham entre 8% e 89% da resposta. Parte das alucinações não é "deriva no
  caminho": o modelo já começa errado.
- **Confusão possível.** Perguntas difíceis (trechos parciais ou de outra espécie) tendem a gerar
  respostas longas *e* alucinação. Com 50 itens não dá para separar causa de correlação.
- **Varia por modelo.** No `qwen3.5:4b` as fundamentadas são mais longas (mediana 295 vs. 212); no
  `gpt-oss:20b` as não fundamentadas são mais curtas (74 vs. 111). O padrão vem sobretudo do
  `qwen2.5:3b-instruct` (16 dos 27 itens não fundamentados).

## Por que o prompt pode estar contribuindo

`PROMPT_SISTEMA` (`backend/services/geracao.py`) não pede concisão em nenhum ponto e tem
instruções que puxam para respostas extensas: "sintetize uma resposta agregada combinando as
informações desses trechos" e "Revise TODOS os trechos fornecidos". Não há nada como "responda só
o que a pergunta pede".

## Desenho proposto do experimento

1. **Variantes**, sem alterar o caminho padrão de produção (variante selecionável por configuração
   ou script próprio):
   - **V0:** prompt atual (linha de base, a mesma da rodada 1);
   - **V1:** prompt atual + instrução de concisão (ex.: "Responda de forma direta, em até N frases,
     somente o que a pergunta pede. Não acrescente contexto que não foi perguntado.");
   - **V2:** prompt atual + teto de `LLM_NUM_PREDICT` (já configurável desde `5098a39`). Atenção:
     o teto corta a resposta no meio, o que pode cortar citações; medir isso também;
   - **V1+V2**, se V1 e V2 mostrarem efeito separadamente.
2. **Perguntas:** as mesmas da rodada 1, mesma config (`num_ctx=8192`, `top_k=8`, temperatura 0,
   seed 42), 3 execuções por célula.
3. **Geradores:** começar pelo `qwen2.5:3b-instruct` (linha de base e onde o padrão aparece mais);
   estender aos outros só se houver efeito.
4. **Métricas por categoria de pergunta** (alinhado à meta de % de acerto por categoria):
   - taxa de `nao_fundamentada` (alucinação/especulação);
   - taxa de abstenção indevida (concisão pode virar recusa excessiva);
   - cobertura: a resposta ainda traz a informação esperada? (ver
     `diagnosticos/criterios-avaliacao-bateria.md`);
   - comprimento (palavras e tokens) e latência.
5. **Classificação:** mesmos critérios da rodada 1. Se a rodada 2 já tiver apontado um juiz
   confiável, usar como triagem, mantendo a revisão humana.

## Critério para considerar a hipótese confirmada

V1 (ou V2) reduz a taxa de `nao_fundamentada` do `qwen2.5:3b-instruct` de forma consistente nas 3
execuções, sem aumento relevante de abstenção indevida nem perda de cobertura nas categorias que
hoje acertam.

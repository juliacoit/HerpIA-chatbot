# Comparação de juízes de groundedness — rodada 2

_Rodada executada em 2026-10-06 e 2026-10-07 (branch `experimento/comparacao-geradores`, commits
`dad1021` e `525e46a`, que não diferem em código). Compara **só o juiz**: cada juiz recebe os mesmos
pares (pergunta, trechos, resposta) do conjunto rotulado e devolve um veredito. Nenhuma resposta nova
foi gerada e a API não mudou; os adaptadores vivem em `scripts/avaliar_juizes.py`._

> **Este documento descreve diferenças observadas; não indica qual juiz escolher.**
> Os vereditos dos juízes são saída de máquina; o gabarito é o conjunto rotulado, confirmado pela
> Júlia em 2026-09-30 e 2026-10-02 (`diagnosticos/juizes/README.md`). As leituras deste relatório
> (seções 5 e 6) foram escritas pelo Claude a partir dos arquivos de resultado e **ainda não foram
> revisadas**.

> **Amostra pequena.** São 53 itens, dos quais 28 não fundamentados. Uma diferença de um ou dois
> itens entre juízes não distingue nada; por isso as tabelas trazem contagens, não percentuais.

## 1. Configuração

### Comum

- Conjunto: `diagnosticos/juizes/conjunto_rotulado.jsonl`, 53 itens (28 `nao_fundamentada`, 13
  `fundamentada`, 10 `abstencao_honesta`, 2 `abstencao_indevida`), cada um com os 8 trechos que o
  gerador recebeu.
- 2 repetições por item, com aquecimento do modelo antes de medir.
- `temperature=0`, `seed=42`, `num_ctx=8192` (ver a exceção dos 6 itens longos, abaixo).
- Um modelo por vez, com `ollama ps` ao fim de cada juiz. Ollama 0.32.9.
- Máquina: RTX 2050 de 4 GB e 25 GB de RAM; só o `qwen2.5:3b-instruct` cabe inteiro na GPU.

### Juízes

| Juiz | Modelo | Como julga | Processador (8192) |
|---|---|---|---|
| J1 | `qwen2.5:3b-instruct` | `verificar_com_llm` de produção, `think=false` (autojulgamento do gerador padrão) | 100% GPU |
| J2 | `granite4.1-guardian:8b` | Critério nativo `groundedness`, uma chamada | 73% CPU / 27% GPU |
| J3 | `granite4.1-guardian:8b` | Critério próprio em inglês (BYOC, texto em `CRITERIO_J3`), uma chamada | 73% CPU / 27% GPU |
| J4 | `bespoke-minicheck` | Uma chamada por frase da resposta; regra de pulo `v3` | 62% CPU / 38% GPU |
| J6 | `gpt-oss:20b` | `verificar_com_llm` de produção, `think="low"` | 84% CPU / 16% GPU |

J1 e J6 chamam a função de produção sem cópia, com os termos suspeitos da camada 2. Isso mede
só a camada 3 (o juiz por LLM); o efeito das camadas lexicais de produção está na seção 4.

**J5 removido da comparação (decisão da Júlia em 2026-10-09).** O `qwen3.5:9b` com
`verificar_com_llm` e `think=false` rodou como J5 e reteve os 53 itens nas duas repetições, isto é,
não distingue os casos (seção 5.2). Saiu das tabelas; os arquivos `resultados_J5*.jsonl` ficam no
repositório só como registro.

O Guardian e o MiniCheck foram treinados só em inglês. No Guardian, `yes` significa critério de
risco atendido, isto é, **não fundamentada**. O MiniCheck tem licença CC BY-NC 4.0 (uso não
comercial) e foi usado só nesta avaliação.

### Exceção: 6 itens com prompt maior que o contexto

Os quatro itens F4 e os dois G2 geram prompts de 8,3 a 11,4 mil tokens em J1, J4 e J6, acima do
`num_ctx=8192`. O Ollama não recusa: corta o prompt para cerca de 4.098 tokens e segue (aviso
`truncating input prompt` no log do servidor). A estimativa feita antes da rodada (6,7 a 7,6 mil
tokens) valia só para o tokenizador do Guardian.

Decisão da Júlia em 2026-10-07: nesses 6 itens, J1, J4 e J6 rodaram com `num_ctx=16384`
(arquivos `resultados_<juiz>_ctx16384.jsonl`); J2 e J3 não precisaram (máximo de 6.982 tokens). As
tabelas das seções 2 a 4 usam, para esses 6 itens, os resultados com 16384. Os vereditos truncados
do J1 foram mantidos em `resultados_J1.jsonl` e são tratados na seção 5.1.

### Intercorrências

- A execução foi interrompida duas vezes (desligamento acidental do PC e, na retomada, um
  travamento do J4 num item truncado). O script ganhou `--retomar`, `--num-ctx`, `--sufixo` e um
  teto de 32 tokens de saída no J4.
- O teto de saída do J4 vale só para os 6 itens longos; os outros 47 rodaram com o código anterior.
- Uma linha truncada do J4 (`r1-qwen2.5-3b-F4-e1`, repetição 1) foi descartada e refeita com 16384.

## 2. Tabela comparativa

Contagem de **itens**. Quando as duas repetições diferem, aparecem como `rep1 / rep2`. "Retida"
significa veredito de não fundamentada.

| Juiz | Não fundamentadas retidas (de 28) | Fundamentadas retidas (de 13) | Abstenções honestas retidas (de 10) | Itens sem veredito | Itens com o mesmo veredito nas 2 repetições | Tempo médio (s) | Mediana (s) | Máximo (s) | Chamadas por item |
|---|---|---|---|---|---|---|---|---|---|
| J1 | 6 / 6 | 2 | 8 | 0 | 51 de 53 | 2,7 | 2,4 | 12,5 | 1 |
| J2 | 9 | 0 | 3 | 0 | 53 de 53 | 20,3 | 22,6 | 31,3 | 1 |
| J3 | 8 | 0 | 0 | 0 | 53 de 53 | 20,5 | 23,1 | 30,5 | 1 |
| J4 | 24 | 3 | 2 | 1 | 53 de 53 | 25,9 | 20,6 | 101,4 | 5,4 em média (máx. 15) |
| J6 | 18 / 17 | 1 | 0 | 0 | 50 de 53 | 26,9 | 24,1 | 91,6 | 1 |

Como ler:

- A primeira coluna é o que se quer alto; a segunda e a terceira, o que se quer baixo.
- O J1 reteve 6 itens nas duas repetições, mas não os mesmos 6 (ver "Determinismo").
- O item sem veredito do J4 é uma resposta fundamentada (`r1-granite4.2-3b-F6-e1`); ver seção 5.4.
- Os tempos misturam os 47 itens em 8192 com os 6 itens em 16384 e valem para esta máquina.

**Abstenção indevida (2 itens, observação qualitativa).** A resposta diz que os trechos não têm a
informação, mas eles têm. J1 reteve os dois; J2 reteve um (`r1-gpt-oss-20b-B2-e1`); J3, J4 e J6
aprovaram os dois. No J4 isso decorre da regra de pulo: todas as frases desses dois itens foram
puladas como abstenção, e resposta sem frase checada é aprovada.

**Determinismo.** Com temperatura 0 e seed 42, J2, J3 e J4 deram o mesmo veredito nas duas
repetições em todos os itens. O J1 mudou em 2 itens (`r1-granite4.2-3b-B3-e1`,
`r1-qwen2.5-3b-C1-e1`) e o J6 em 3 (`r1-granite4.2-3b-F4-e1`, `r1-qwen2.5-3b-L5-e2`,
`b0922-qwen2.5-3b-B3-e3`), todos não fundamentados.

**Não fundamentadas retidas, por gerador da resposta (repetição 1).** Os grupos são pequenos demais
para concluir algo sobre autojulgamento; a tabela só registra o que foi visto.

| Juiz | `qwen2.5:3b` (16) | `granite4.2:3b` (4) | `qwen3.5:4b` (2) | `qwen3.5:9b` (2) | `gpt-oss:20b` (4) |
|---|---|---|---|---|---|
| J1 | 4 | 0 | 1 | 1 | 0 |
| J2 | 6 | 1 | 0 | 0 | 2 |
| J3 | 5 | 1 | 0 | 0 | 2 |
| J4 | 13 | 4 | 2 | 1 | 4 |
| J6 | 12 | 3 | 0 | 0 | 3 |

## 3. Tabela item × juiz

Cada célula traz o veredito das duas repetições: `R` retida, `A` aprovada, `?` sem veredito. O
esperado é `RR` nas não fundamentadas e `AA` nas fundamentadas e nas abstenções honestas. Nos 6
itens marcados com `*`, J1, J4 e J6 rodaram com `num_ctx=16384`.

| Item | Rótulo | J1 | J2 | J3 | J4 | J6 |
|---|---|---|---|---|---|---|
| `r1-qwen2.5-3b-A1-e1` | Não fundamentada | **AA** | **AA** | **AA** | RR | RR |
| `r1-granite4.2-3b-A3-e1` | Não fundamentada | **AA** | **AA** | **AA** | RR | RR |
| `r1-qwen2.5-3b-B1-e1` | Não fundamentada | **AA** | **AA** | **AA** | **AA** | RR |
| `r1-granite4.2-3b-B2-e1` | Não fundamentada | **AA** | **AA** | **AA** | RR | RR |
| `r1-granite4.2-3b-B3-e1` | Não fundamentada | **AR** | RR | RR | RR | RR |
| `r1-qwen2.5-3b-C1-e1` | Não fundamentada | **RA** | **AA** | **AA** | **AA** | RR |
| `r1-qwen2.5-3b-C3-e1` | Não fundamentada | **AA** | **AA** | **AA** | RR | RR |
| `r1-qwen2.5-3b-F4-e1`* | Não fundamentada | RR | RR | **AA** | RR | **AA** |
| `r1-granite4.2-3b-F4-e1`* | Não fundamentada | **AA** | **AA** | **AA** | RR | **AR** |
| `r1-qwen3.5-4b-F4-e1`* | Não fundamentada | RR | **AA** | **AA** | RR | **AA** |
| `r1-gpt-oss-20b-F4-e2`* | Não fundamentada | **AA** | RR | RR | RR | RR |
| `r1-qwen2.5-3b-F5-e2` | Não fundamentada | **AA** | **AA** | **AA** | RR | **AA** |
| `r1-gpt-oss-20b-G2-e1`* | Não fundamentada | **AA** | RR | RR | RR | RR |
| `r1-qwen2.5-3b-G3-e1` | Não fundamentada | RR | **AA** | **AA** | **AA** | **AA** |
| `r1-qwen3.5-9b-G4-e1` | Não fundamentada | **AA** | **AA** | **AA** | **AA** | **AA** |
| `r1-qwen3.5-9b-I1-e1` | Não fundamentada | RR | **AA** | **AA** | RR | **AA** |
| `r1-qwen2.5-3b-J1-e2` | Não fundamentada | **AA** | RR | RR | RR | RR |
| `r1-qwen3.5-4b-J1-e1` | Não fundamentada | **AA** | **AA** | **AA** | RR | **AA** |
| `r1-qwen2.5-3b-L2-e1` | Não fundamentada | **AA** | RR | RR | RR | **AA** |
| `r1-qwen2.5-3b-L4-e1` | Não fundamentada | **AA** | RR | RR | RR | RR |
| `r1-qwen2.5-3b-L5-e2` | Não fundamentada | **AA** | **AA** | **AA** | RR | **RA** |
| `r1-gpt-oss-20b-L5-e1` | Não fundamentada | **AA** | **AA** | **AA** | RR | **AA** |
| `r1-gpt-oss-20b-L8-e1` | Não fundamentada | **AA** | **AA** | **AA** | RR | RR |
| `b0922-qwen2.5-3b-A1-e3` | Não fundamentada | **AA** | **AA** | **AA** | RR | RR |
| `b0922-qwen2.5-3b-B3-e3` | Não fundamentada | **AA** | **AA** | **AA** | RR | **RA** |
| `b0922-qwen2.5-3b-I1-e3` | Não fundamentada | RR | RR | RR | RR | RR |
| `a0813-qwen2.5-3b-G1` | Não fundamentada | **AA** | **AA** | **AA** | RR | RR |
| `a0813-qwen2.5-3b-I1` | Não fundamentada | **AA** | RR | RR | RR | RR |
| `r1-qwen3.5-9b-A1-e1` | Fundamentada | AA | AA | AA | AA | AA |
| `r1-granite4.2-3b-A2-e1` | Fundamentada | AA | AA | AA | AA | AA |
| `r1-qwen3.5-4b-A3-e1` | Fundamentada | **RR** | AA | AA | **RR** | AA |
| `r1-qwen2.5-3b-B2-e2` | Fundamentada | AA | AA | AA | AA | **RR** |
| `r1-qwen3.5-9b-C2-e1` | Fundamentada | AA | AA | AA | AA | AA |
| `r1-granite4.2-3b-C3-e1` | Fundamentada | AA | AA | AA | AA | AA |
| `r1-qwen2.5-3b-D1-e1` | Fundamentada | AA | AA | AA | AA | AA |
| `r1-gpt-oss-20b-D2-e1` | Fundamentada | AA | AA | AA | AA | AA |
| `r1-gpt-oss-20b-F5-e1` | Fundamentada | AA | AA | AA | AA | AA |
| `r1-granite4.2-3b-F6-e1` | Fundamentada | AA | AA | AA | **??** | AA |
| `r1-qwen3.5-4b-H1-e1` | Fundamentada | AA | AA | AA | AA | AA |
| `r1-qwen3.5-9b-L4-e1` | Fundamentada | **RR** | AA | AA | **RR** | AA |
| `r1-qwen3.5-4b-L5-e1` | Fundamentada | AA | AA | AA | **RR** | AA |
| `r1-qwen2.5-3b-F2-e1` | Abstenção honesta | **RR** | AA | AA | **RR** | AA |
| `r1-qwen2.5-3b-H2-e1` | Abstenção honesta | AA | AA | AA | AA | AA |
| `r1-qwen3.5-9b-B3-e1` | Abstenção honesta | **RR** | AA | AA | AA | AA |
| `r1-gpt-oss-20b-D4-e1` | Abstenção honesta | **RR** | **RR** | AA | AA | AA |
| `r1-qwen3.5-4b-F3-e1` | Abstenção honesta | **RR** | **RR** | AA | AA | AA |
| `r1-qwen3.5-9b-G2-e1`* | Abstenção honesta | **RR** | AA | AA | **RR** | AA |
| `r1-granite4.2-3b-L1-e1` | Abstenção honesta | AA | AA | AA | AA | AA |
| `r1-qwen2.5-3b-L3-e1` | Abstenção honesta | **RR** | **RR** | AA | AA | AA |
| `r1-qwen2.5-3b-L6-e1` | Abstenção honesta | **RR** | AA | AA | AA | AA |
| `r1-gpt-oss-20b-F7-e1` | Abstenção honesta | **RR** | AA | AA | AA | AA |
| `r1-qwen3.5-4b-D3-e1` | Abstenção indevida | RR | AA | AA | AA | AA |
| `r1-gpt-oss-20b-B2-e1` | Abstenção indevida | RR | RR | AA | AA | AA |

Em negrito, os vereditos diferentes do esperado. As abstenções indevidas não têm esperado definido.

Quantos juízes retiveram cada item não fundamentado (repetição 1):

- **Nenhum juiz:** `r1-qwen3.5-9b-G4-e1` (programa inventado numa pergunta sobre o SEI).
- **Só o J6:** `r1-qwen2.5-3b-B1-e1` (categoria CR atribuída a espécies EN/VU).
- **Só o J4:** `r1-granite4.2-3b-F4-e1`, `r1-qwen2.5-3b-F5-e2`, `r1-qwen3.5-4b-J1-e1`,
  `r1-gpt-oss-20b-L5-e1`.
- **Só o J1:** `r1-qwen2.5-3b-G3-e1` (abstenção com uma sigla inventada).
- **Todos os cinco:** `b0922-qwen2.5-3b-I1-e3`.

## 4. Efeito das camadas lexicais de produção

Em produção o juiz por LLM é a última camada. Antes dele, `groundedness.py` aplica a camada 1
(âncoras estruturais, que retém sozinha) e a camada 0 (abstenção honesta, que aprova sozinha). As
duas são funções puras, sem LLM; foram aplicadas offline aos 53 itens, sem alterar o módulo.

O que as camadas lexicais decidem antes de qualquer juiz:

| Rótulo | Camada 1 retém | Camada 0 aprova | Vai ao juiz |
|---|---|---|---|
| Não fundamentada (28) | 7 | 2 | 19 |
| Fundamentada (13) | 0 | 3 | 10 |
| Abstenção honesta (10) | 1 | 6 | 3 |
| Abstenção indevida (2) | 0 | 2 | 0 |

- A camada 1 retém 7 alucinações sozinha, entre elas `r1-qwen3.5-9b-G4-e1`, que nenhum juiz reteve.
- Em 4 dessas 7, o termo apontado pela camada 1 é de fato inventado (`People`, `Anilopla carinata`,
  `Biodiversidade` no nome de um sistema que não existe, `Arapapás`). Nas outras 3
  (`r1-qwen2.5-3b-C3-e1`, `r1-qwen2.5-3b-L4-e1`, `a0813-qwen2.5-3b-G1`), o termo é uma expressão
  comum em início de item ou antes de parênteses (`Preocupantes`, `Embora não`,
  `Critérios específicos`): a resposta é retida, mas não pela alucinação. Conferido em 2026-10-09.
- A camada 1 retém por engano uma abstenção honesta (`r1-qwen3.5-9b-G2-e1`), pelo mesmo mecanismo:
  o termo apontado é `Trechos ilegíveis`, início de um item de lista em que a resposta descreve os
  trechos recebidos. Como a camada 1 roda antes da camada 0, a abstenção nem chega a ser testada.
- A camada 0 aprova 2 não fundamentadas (`r1-qwen2.5-3b-G3-e1` e `r1-qwen3.5-9b-I1-e1`): são
  abstenções com um dado inventado dentro. Nenhum juiz chega a vê-las.
- A camada 0 aprova as 2 abstenções indevidas, então nenhum juiz as reteria em produção.

Resultado do fluxo completo (camada 1, camada 0 e cada juiz como camada 3), em itens:

| Juiz na camada 3 | Não fundamentadas retidas (de 28) | Fundamentadas retidas (de 13) | Abstenções honestas retidas (de 10) | Sem veredito |
|---|---|---|---|---|
| J1 (situação atual de produção) | 11 | 0 | 3 | 0 |
| J2 | 13 | 0 | 1 | 0 |
| J3 | 12 | 0 | 1 | 0 |
| J4 | 24 | 1 | 1 | 1 |
| J6 | 19 | 1 | 1 | 0 |

- Em todos os juízes, uma das abstenções honestas retidas é o engano da camada 1, não do juiz.
- As camadas lexicais corrigem a maior parte das retenções indevidas do J1 (de 2 + 8 para 0 + 3) e
  quase dobram suas detecções (de 6 para 11).
- O teto de detecção com as camadas atuais é 26 de 28, por causa das 2 aprovadas pela camada 0.

## 5. Achados

### 5.1 O prompt cortado em produção e o "SIM ou NÃO" contado como aprovação

O J1 é o caminho de produção, e `LLM_NUM_CTX` tem 8192 por padrão. Nos 6 itens longos, o prompt do
juiz foi cortado para 4.098 tokens. Comparação dos vereditos do J1 nesses itens:

| Item | Rótulo | 8192 (cortado) | 16384 |
|---|---|---|---|
| `r1-qwen2.5-3b-F4-e1` | não fundamentada | AA | RR |
| `r1-granite4.2-3b-F4-e1` | não fundamentada | AA | AA |
| `r1-qwen3.5-4b-F4-e1` | não fundamentada | AA | RR |
| `r1-gpt-oss-20b-F4-e2` | não fundamentada | AA | AA |
| `r1-gpt-oss-20b-G2-e1` | não fundamentada | AA | AA |
| `r1-qwen3.5-9b-G2-e1` | abstenção honesta | RR | RR |

Em quatro das linhas cortadas (os dois itens que mudam de veredito, nas duas repetições), o modelo
não julgou: devolveu na primeira linha o próprio texto do formato, `SIM ou NÃO`. O
`verificar_com_llm` aprova tudo que **começa** com `SIM`, então essas saídas contaram como
aprovação. A docstring da função diz que ela falha fechada; nesse caso ela falha aberta.

São dois problemas distintos em código de produção, nenhum corrigido nesta rodada (a regra era não
alterar `groundedness.py`):

1. Prompts acima do contexto são cortados sem erro. O backend já registra o alerta de 85% do
   contexto no console, mas segue adiante.
2. A leitura do veredito aceita `SIM ou NÃO` como `SIM`.

No J4, o corte teve outro efeito: o MiniCheck perdeu o formato, respondeu em texto livre e chegou a
gerar até estourar o tempo limite de 900 s.

### 5.2 J5: reteve tudo e foi removido da comparação

As 106 saídas do `qwen3.5:9b` com `think=false` começam com `NÃO`. As justificativas mostram dois
padrões: cobrança de completude (a resposta está certa, mas "ignora" outro trecho) e, em pelo menos
um caso (`r1-granite4.2-3b-L1-e1`), um `NÃO` seguido de "A resposta é apoiada porque…". Nessa
configuração ele não funciona como juiz: as 28 detecções valem o mesmo que as 23 retenções
indevidas. A rodada não testou o modelo com raciocínio ligado. Em 2026-10-09 a Júlia decidiu
removê-lo da comparação, sem nova tentativa.

### 5.3 J2 e J3 (Guardian): poucas retenções indevidas, poucas detecções

- Nenhum dos dois reteve resposta fundamentada.
- O critério próprio (J3) eliminou as 3 abstenções honestas que o critério nativo (J2) reteve, ao
  custo de uma detecção (`r1-qwen2.5-3b-F4-e1`).
- Os dois deixaram passar cerca de dois terços das não fundamentadas (19 e 20 de 28), incluindo os
  casos de informação verdadeira atribuída à espécie ou ao documento errado (A1, B1, B2).

### 5.4 J4 (MiniCheck): mais detecções, com ressalvas sobre o motivo

O J4 reteve 24 das 28 não fundamentadas. As ressalvas abaixo comparam, frase a frase, o veredito do
MiniCheck com as `afirmacoes_sem_suporte` do gabarito. A primeira versão usava uma comparação
automática por sobreposição de palavras; em 2026-10-09 o Claude leu os 28 itens e corrigiu duas
contagens (as outras se confirmaram). A leitura ainda não foi revisada pela Júlia.

- Das 24 retidas, em 15 alguma frase reprovada é uma afirmação do gabarito (em 12, todas as
  afirmações do gabarito foram reprovadas; em 3, uma foi reprovada e outra aprovada). Nas outras 9,
  o item foi retido **só por outras frases**: a afirmação do gabarito foi aprovada em 6 e pulada em
  3. O veredito final está certo, mas não pelo motivo certo.
- Em 4 dessas 9 (`r1-granite4.2-3b-A3-e1`, `r1-granite4.2-3b-B2-e1`, `r1-granite4.2-3b-B3-e1`,
  `r1-qwen2.5-3b-F4-e1`), a única frase reprovada não afirma nada sobre os trechos: é uma frase de
  ligação ou de conselho ("Assim, a resposta baseada exclusivamente nos trechos fornecidos é:").
  Sem essas frases, o J4 teria retido 20 das 28, não 24.
- Em 11 dos 28 itens, alguma afirmação do gabarito recebeu `Yes` do MiniCheck (a comparação
  automática indicava cerca de 12).
- Nas 13 respostas fundamentadas, 4 frases foram reprovadas (de 81 checadas), o que bastou para
  reter 3 itens: como uma frase reprovada retém a resposta inteira, respostas longas acumulam risco.
- **As 4 não detectadas:** em `r1-qwen2.5-3b-B1-e1` e `r1-qwen2.5-3b-C1-e1`, o MiniCheck aprovou as
  frases do gabarito; em `r1-qwen2.5-3b-G3-e1` e `r1-qwen3.5-9b-G4-e1`, a frase do gabarito foi
  pulada pela regra de pulo.
- **Regra de pulo `v3`:** pulou 23 das 31 frases das abstenções honestas (7 dos 10 itens ficaram sem
  nenhuma frase checada) e 29 das 226 frases das não fundamentadas. Em 5 itens não fundamentados a
  afirmação do gabarito caiu numa frase pulada (a comparação automática indicava cerca de 8); em 2
  deles isso causou a não detecção. As regras `v1` e `v2` não foram rodadas.
- **Falha de parse:** em `r1-granite4.2-3b-F6-e1`, a resposta termina com uma frase entre
  parênteses que cita a pergunta ("(Nota: A pergunta pede…"). O MiniCheck respondeu a pergunta em
  texto livre, sem `Yes` nem `No`. Não é efeito de truncamento.
- **Custo:** 5,4 chamadas por item em média, até 15. O tempo cresce com o tamanho da resposta.

### 5.5 J6: nenhuma abstenção honesta retida, detecção parcial e instável

O `gpt-oss:20b` reteve 18 (ou 17) das 28 não fundamentadas, 1 fundamentada e nenhuma abstenção
honesta. Não reteve nenhuma das 4 não fundamentadas geradas pelos `qwen3.5`, e mudou de veredito
entre repetições em 3 itens. Ocupa 14 GB e roda 84% em CPU nesta máquina.

### 5.6 J1: confirma a fraqueza já conhecida

Sozinho, o juiz atual reteve 6 das 28 não fundamentadas e 8 das 10 abstenções honestas, o padrão já
descrito na docstring de `groundedness.py`. É, de longe, o mais rápido (2,7 s), por ser o único
modelo inteiro na GPU.

## 6. Limitações

- 53 itens, selecionados de baterias anteriores; não é amostra aleatória do uso real.
- 16 das 28 não fundamentadas vêm do `qwen2.5:3b-instruct`.
- Os 6 itens longos rodaram com contexto diferente em três dos cinco juízes.
- O teto de saída do J4 só se aplicou a esses 6 itens.
- A análise por frase do J4 foi conferida por leitura pelo Claude, não por uma pessoa.
- Guardian e MiniCheck julgam texto em português sem terem sido treinados para isso.
- Tempos medidos nesta máquina, com os modelos majoritariamente em CPU.
- Nenhuma combinação de juízes foi avaliada.

## 7. Pontos em aberto para decisão

Situação em 2026-10-09 (detalhes na seção 8):

1. ~~O que fazer com os dois problemas de produção da seção 5.1 (prompt cortado sem erro; `SIM ou NÃO`
   lido como aprovação).~~ Corrigidos (seção 8.1).
2. ~~Se vale rodar o J4 com as regras de pulo `v1` e `v2`.~~ Rodado (seção 8.3).
3. ~~Se vale conferir à mão a análise por frase do J4 antes de usá-la como argumento.~~ Conferida
   pelo Claude em 2026-10-09 (seção 5.4); resta a revisão da Júlia.
4. ~~Se o J5 merece nova tentativa com raciocínio ligado, ou sai da comparação.~~ Removido da
   comparação em 2026-10-09 (seção 5.2).
5. ~~Se a camada 0 deve continuar aprovando sozinha.~~ Passou a aprovar só abstenção pura (seção
   8.2). **Em aberto:** manter a mudança com o juiz atual, dado o custo medido.
6. Ampliação do conjunto rotulado: 101 candidatos propostos, **aguardando confirmação dos rótulos**
   (seção 8.4). Faltam respostas não fundamentadas novas.
7. **Novo:** se a camada 1 precisa de ajuste, já que 3 das suas 7 detecções e a única retenção
   indevida vêm de termos banais em início de item (seção 4).

## 8. Atualizações de 2026-10-09

Feitas a pedido da Júlia depois da leitura do relatório. As seções 1 a 6 descrevem a rodada como
foi executada, com o código anterior a estas mudanças. Nada aqui muda os arquivos de resultado.

### 8.1 Correções dos dois problemas da seção 5.1

- **Prompt maior que o contexto:** `OllamaLLMClient.generate` passou a enviar `truncate: false`. O
  Ollama 0.32.9 devolve erro 400 (`exceed_context_size_error`) em vez de cortar, e o cliente levanta
  `ContextoExcedidoError`. No juiz, a resposta é retida com a justificativa "Verificação não
  realizada"; na geração, `/perguntar` responde que os trechos são longos demais.
- **Leitura do veredito:** só conta como aprovação um `SIM` sozinho na primeira linha (aceita
  pontuação e negrito em volta). `SIM ou NÃO` passa a reter.

As tabelas da seção 4 usam, nos 6 itens longos, os vereditos do J1 com `num_ctx=16384`. Em produção
o contexto é 8192, então o fluxo real era outro. Fluxo completo com o J1 em 8192, em itens retidos
(repetição 1):

| Fluxo de produção (J1, 8192) | Não fundamentadas retidas (de 28) | Fundamentadas retidas (de 13) | Abstenções honestas retidas (de 10) |
|---|---|---|---|
| Antes (prompt cortado em silêncio) | 9 | 0 | 3 |
| Depois das correções desta seção | 14 | 0 | 3 |
| Depois também da mudança da camada 0 (seção 8.2) | 15 | 2 | 5 |

As 5 detecções novas são os quatro itens F4 e `r1-gpt-oss-20b-G2-e1`: o prompt do juiz não cabe em
8192 e a resposta agora é retida sem julgamento. São 5 itens não fundamentados, mas a retenção vem
do tamanho do prompt, não de um juízo sobre o conteúdo: uma resposta boa com trechos longos também
seria retida. Nesses casos o prompt da geração coube no contexto (na rodada 1 o maior foi de 7.217
tokens); o do juiz é maior porque inclui a resposta.

Conferido com um cliente falso (10 formatos de primeira linha e os dois caminhos de contexto
excedido) e, no Ollama real, que `truncate: false` devolve o erro esperado.

### 8.2 Camada 0: só abstenção pura aprova sozinha

Antes, bastava uma frase de abstenção em qualquer ponto da resposta para aprová-la sem juiz. Agora
`checar_abstencao_pura` exige que **todas** as frases sejam de abstenção, negação sobre os trechos ou
cabeçalho (a mesma divisão em frases e os mesmos padrões da regra `v3` do J4, que passaram do script
para `groundedness.py`). Resposta com conteúdo próprio vai ao juiz.

O que a camada 0 aprova sozinha, antes e depois:

| Rótulo | Antes | Depois | Passaram a ir ao juiz |
|---|---|---|---|
| Não fundamentada (28) | 2 | 1 | `r1-qwen3.5-9b-I1-e1` |
| Fundamentada (13) | 3 | 1 | `r1-qwen3.5-4b-A3-e1`, `r1-qwen3.5-9b-L4-e1` |
| Abstenção honesta (10) | 6 | 4 | `r1-qwen2.5-3b-F2-e1`, `r1-qwen3.5-4b-F3-e1` |
| Abstenção indevida (2) | 2 | 2 | nenhuma |

Fluxo completo com a camada 0 nova (camada 1, camada 0 e cada juiz; nos 6 itens longos, vereditos
com 16384, como na seção 4). Entre parênteses, a variação em relação à tabela da seção 4:

| Juiz na camada 3 | Não fundamentadas retidas (de 28) | Fundamentadas retidas (de 13) | Abstenções honestas retidas (de 10) |
|---|---|---|---|
| J1 | 12 (+1) | 2 (+2) | 5 (+2) |
| J2 | 13 (0) | 0 (0) | 2 (+1) |
| J3 | 12 (0) | 0 (0) | 1 (0) |
| J4 | 25 (+1) | 3 (+2) | 2 (+1) |
| J6 | 19 (0) | 1 (0) | 1 (0) |

- Com o juiz atual (J1), a mudança detecta uma alucinação a mais e retém quatro respostas a mais
  que não deveriam ser retidas, porque o J1 reprova os cinco itens que passou a receber.
- Com J3 ou J6 a mudança não custa nada nestes itens, e também não detecta nada a mais.
- A mudança **não** resolve dois casos que motivaram o ponto 5: `r1-qwen2.5-3b-G3-e1`, em que o dado
  inventado está dentro da própria frase de abstenção ("RAN (Recurso Ambiental)"), e as duas
  abstenções indevidas, que são abstenções puras no texto.

### 8.3 J4 com as regras de pulo `v1` e `v2`

Mesmo protocolo da `v3` (47 itens em 8192, 6 itens longos em 16384, 2 repetições), rodado em
2026-10-09. A `v1` pula só o que `checar_abstencao_honesta` reconhece; a `v2` acrescenta frases como
"não é possível responder"; a `v3` acrescenta frases cujo sujeito são os trechos, com negação.

| Regra | Não fundamentadas retidas (de 28) | Fundamentadas retidas (de 13) | Abstenções honestas retidas (de 10) | Abstenções indevidas retidas (de 2) | Frases puladas nas abstenções honestas (de 31) | Abstenções honestas sem frase checada | Não fundamentadas com afirmação do gabarito pulada | Chamadas por item |
|---|---|---|---|---|---|---|---|---|
| `v1` | 25 | 3 | 5 | 1 | 8 | 2 | 2 | 6,2 |
| `v2` | 25 | 3 | 5 | 1 | 16 | 3 | 3 | 5,9 |
| `v3` | 24 | 3 | 2 | 0 | 23 | 7 | 5 | 5,4 |

- `v1` e `v2` deram o mesmo veredito em todos os 53 itens. Em relação à `v3`, mudam 5 itens:
  detectam `r1-qwen3.5-9b-G4-e1` (o programa inventado estava numa frase que a `v3` pula) e retêm
  três abstenções honestas a mais (`r1-qwen2.5-3b-H2-e1`, `r1-qwen3.5-9b-B3-e1`,
  `r1-granite4.2-3b-L1-e1`) e uma abstenção indevida (`r1-qwen3.5-4b-D3-e1`).
- Nas três abstenções honestas, as frases reprovadas dizem o que os trechos **não** trazem ("mas
  não mencionam Campos-de-Cima-da-Serra"). O MiniCheck não confirma uma ausência e responde `No`.
  É esse tipo de frase que a `v3` pula.
- A troca medida é de uma detecção por três retenções indevidas, em amostra pequena.
- As três respostas fundamentadas retidas e o item sem veredito são os mesmos nas três regras.
- As duas repetições coincidiram em todos os itens, nas três regras.
- A coluna "afirmação do gabarito pulada" vem de comparação automática de texto; na `v3` ela
  coincide com a contagem feita por leitura (seção 5.4).
- Diferença de execução: nas regras `v1` e `v2` o teto de 32 tokens de saída valeu para os 53
  itens; na `v3`, só para os 6 longos.

### 8.4 Ampliação do conjunto rotulado

`diagnosticos/juizes/candidatos_ampliacao.jsonl` traz 101 respostas da rodada 1 que não estavam no
conjunto, com rótulo **proposto** (37 fundamentadas, 60 abstenções honestas, 4 abstenções indevidas);
`candidatos_ampliacao_revisao.md` é a versão para leitura e confirmação. As regras e as 31 células
que ficaram fora estão no `README.md` da pasta. Nenhum juiz foi avaliado nesses itens ainda.

A ampliação não traz nenhuma resposta não fundamentada nova: todas as células "alucina" e "especula"
da rodada 1 já estavam no conjunto. Ela serve para medir melhor a retenção indevida; para medir
melhor a detecção é preciso gerar respostas novas.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `diagnosticos/juizes/conjunto_rotulado.jsonl` | Gabarito (53 itens) |
| `diagnosticos/juizes/resultados_J1.jsonl` a `resultados_J3.jsonl` | 106 linhas cada, `num_ctx=8192` |
| `diagnosticos/juizes/resultados_J4.jsonl` e `resultados_J6.jsonl` | 94 linhas cada (47 itens), `num_ctx=8192` |
| `diagnosticos/juizes/resultados_J{1,4,6}_ctx16384.jsonl` | 12 linhas cada (6 itens longos), `num_ctx=16384` |
| `diagnosticos/juizes/resultados_J5.jsonl` e `resultados_J5_ctx16384.jsonl` | J5, removido da comparação; só registro |
| `diagnosticos/juizes/resultados_J4_v1*.jsonl` e `resultados_J4_v2*.jsonl` | J4 com as regras de pulo `v1` e `v2` (94 + 12 linhas cada), seção 8.3 |
| `diagnosticos/juizes/candidatos_ampliacao.jsonl` e `candidatos_ampliacao_revisao.md` | 101 candidatos à ampliação, com rótulo proposto, seção 8.4 |
| `diagnosticos/juizes/execucao_parte_c.log` | Log da execução, com `ollama ps` por juiz (não versionado) |
| `scripts/avaliar_juizes.py` | Adaptadores e execução |

Cada linha de resultado guarda a saída crua do modelo (`bruto`), a contagem de tokens e, no J4, o
veredito de cada frase. As contagens deste relatório foram calculadas a partir desses arquivos por
um script de análise descartável, que não está no repositório.

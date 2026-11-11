# Comparação de geradores — experimento Lumi-4B (Fase 4)

_Baterias executadas em 2026-11-06 (C1) e de 2026-11-10 a 2026-11-11 (C2, C3, C4), na branch `experimento/lumi-4b`,
commit `e8d5e43`. Compara **só a geração** (`GROUNDEDNESS_VERIFICAR=false`). Roteiro e histórico do
experimento em `docs/processos/experimento_lumi_4b.md`._

> **⚠ Classificações ainda não revisadas.** Os rótulos das seções 2 e 3 e do Anexo A foram
> atribuídos pelo Claude, lendo as respostas contra os trechos efetivamente recuperados (ver
> "Método de classificação"). **Falta a revisão da Júlia**, como na rodada 1.
> Este documento descreve diferenças observadas; **não indica qual modelo escolher** e não tem nota
> geral.

> **Nada aqui vai para produção.** O padrão do backend continua sendo o `qwen2.5:3b-instruct`. A
> licença do Lumi-4B segue sem confirmação (ver seção 6).

## 1. Configuração

### Comum a todas as execuções

| Item | Valor |
|---|---|
| Commit | `e8d5e43` (Fase 3: filtro de `<think>`, saída `resposta_vazia`, `think` e latência no `X-LLM-Uso`) |
| Casos | os 36 de `CASOS_TESTE`, **3 repetições** cada (108 respostas por configuração) |
| `top_k` | 8 |
| Parâmetros do LLM | `LLM_NUM_CTX=16384`, `LLM_TEMPERATURE=0`, `LLM_SEED=42`, `LLM_TIMEOUT=900`, `GROUNDEDNESS_VERIFICAR=false`, passados na linha de comando do uvicorn (`experimentos/lumi-4b/rodar_bateria.sh`). O `.env` não foi alterado |
| Base vetorial | Qdrant embutido (`QDRANT_LOCAL_PATH` absoluto para a base do diretório principal), 59.085 chunks |
| Ollama | 0.32.9 nativo, só em `127.0.0.1` |
| Máquina | a mesma da rodada 1 (i7-12650H, 25 GB no WSL2, RTX 2050 de 4 GB) |
| Aquecimento | uma pergunta fora da bateria (jararaca-ilhoa, `top_k=8`) antes de cada bateria |

**A C1 não é igual à produção nem à linha de base da rodada 1:** aqui o `qwen2.5:3b-instruct` rodou
com `num_ctx=16384` (produção e rodada 1: 8192) e sem groundedness. Com o contexto maior, o modelo
deixou de caber inteiro na GPU (21% CPU / 79% GPU, contra 100% GPU na rodada 1) e a latência média
subiu de 6,9 s para 10,0 s. Os rótulos da C1 foram refeitos para esta rodada, não copiados da rodada 1.

### Por configuração

| Config | Modelo (digest) | `LLM_THINK` | CPU/GPU (`ollama ps`) | Bateria | Início – fim |
|---|---|---|---|---|---|
| C1 | `qwen2.5:3b-instruct` | não enviado | 21% / 79% | [2026-11-06_15h41_qwen2.5-3b-instruct.md](baterias/2026-11-06_15h41_qwen2.5-3b-instruct.md) | 06/11, 15:41 – 15:59 |
| C2 | `nemotron-3-nano:4b` (d94b6dfae26d) | `false` | 58% / 42% | [2026-11-10_16h46_nemotron-3-nano-4b.md](baterias/2026-11-10_16h46_nemotron-3-nano-4b.md) | 10/11, 16:46 – 17:57 |
| C3 | `lumi-4b` (e870aff7d9f4) | `false` | 58% / 42% | [2026-11-10_17h59_lumi-4b.md](baterias/2026-11-10_17h59_lumi-4b.md) | 10/11, 17:59 – 19:07 |
| C4 (calibração) | `lumi-4b` (e870aff7d9f4) | `true` | 58% / 42% | [2026-11-10_19h09_lumi-4b.md](baterias/2026-11-10_19h09_lumi-4b.md) | 10/11, 19:09 – 20:18 |
| C4 | `lumi-4b` (e870aff7d9f4) | `true` | 58% / 42% | [2026-11-10_20h21_lumi-4b.md](baterias/2026-11-10_20h21_lumi-4b.md) | 10/11, 20:21 – 11/11, 10:45 (com a máquina suspensa por cerca de 9h40; ver seção 6) |

Execuções **superadas**, que não entram na comparação: `2026-11-06_15h38_lumi-4b.md` (teste de
infraestrutura) e as duas tentativas da C2 interrompidas pelo desligamento do WSL (06/11 às 17:00,
com 72 respostas, e 10/11 às 15:16, com 39). Elas não chegaram a gravar relatório de bateria.

### Recursos durante as baterias (amostras a cada 60 s)

| Config | RSS do `llama-server` | RSS do backend | Memória da GPU |
|---|---|---|---|
| C1 | 1,0 – 8,2 GiB | até 5,5 GiB | 3,9 GiB |
| C2 | 3,8 – 11,8 GiB | até 5,3 GiB | 3,8 GiB |
| C3 | 2,7 – 10,7 GiB | até 5,3 GiB | 3,8 GiB |
| C4 (calibração) | 2,7 – 9,8 GiB | até 5,3 GiB | 3,8 GiB |
| C4 | 2,7 – 10,7 GiB | até 5,3 GiB | 3,8 GiB |

O RSS do `llama-server` cresce ao longo da bateria nos três modelos e estabiliza perto do teto
indicado (cerca de 11 GiB no Nemotron e no Lumi). Não houve falta de memória.

## 2. Tabela comparativa

Latências por caso, das respostas de cada bateria (sem o aquecimento). As colunas de classificação
contam **casos** (de 36) em que o rótulo aparece em pelo menos uma das 3 execuções; entre parênteses,
o número de **respostas** (de 108). **Rótulos ainda não revisados pela Júlia.**

| Config | Latência média (s) | Mediana (s) | Máxima (s) | Maior prompt (tokens) | Casos > 85% do contexto | Respostas idênticas nas 3 exec. | Casos com alucinação (respostas) | Especulação (casos) | Abstenção correta (casos) | Abstenção indevida (casos) | Premissa falsa não corrigida (casos) | ok (casos 3/3) | Falhas técnicas |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C1 `qwen2.5:3b-instruct` | 10,0 | 9,0 | 29,1 (L5) | 11.437 (G2) | nenhum | 10/36 | 9 (21/108) | 0 | 11 | 2 | 4 | 8 | 0 |
| C2 `nemotron-3-nano:4b` | 39,9 | 32,8 | 75,0 (L5) | 11.935 (G2) | nenhum | 36/36 | 6 (18/108) | 0 | 14 | 4 | 2 | 10 | 0 |
| C3 `lumi-4b`, sem pensar | 37,8 | 32,6 | 74,2 (F5) | 11.605 (G2) | nenhum | 36/36 | 2 (6/108) | 1 | 15 | 4 | 1 | 9 | 0 |
| C4 `lumi-4b`, pensando | 138,4 (105 respostas) | 107,4 | 550,7 (L8) | 11.605 (G2) | nenhum | 36/36 | 5 (15/108) | 0 | 12 | 4 | 2 | 10 | 1 caso (F7, 3/3: tempo limite de 900 s) |

Latência média por passada:

| Config | 1ª passada (s) | 2ª (s) | 3ª (s) |
|---|---|---|---|
| C1 | 13,2 | 8,4 | 8,4 |
| C2 | 39,6 | 41,0 | 39,1 |
| C3 | 37,9 | 37,7 | 37,7 |
| C4 | 139,2 | 138,0 | 137,9 |

**Saída do LLM** (tokens gerados por chamada): C1 média 200, máximo 629; C2 média 131, máximo 392;
C3 média 150, máximo 470; C4 média 1.012, máximo 4.276 (a contagem da C4 inclui o raciocínio). Em C2
e C3 o campo `thinking` veio vazio em todas as chamadas. Na C4 o raciocínio teve em média 2,9 mil
caracteres e chegou a 12,7 mil (L8). O filtro de `<think>` não removeu nenhuma tag em nenhuma
configuração, e não houve `resposta_vazia`.

**A latência da C4 não inclui os 3 tempos limite do F7** (900 s cada). Contando-os, a média seria de
159,5 s.

**Determinismo:** Nemotron e Lumi (com e sem pensar) deram a **mesma resposta nas 3 execuções em 36/36 casos**. O
qwen2.5 variou em 26 casos, como na rodada 1.

**Contexto:** o maior prompt foi o do G2 (11,4 a 11,9 mil tokens, 70 a 73% de 16.384). Nenhum caso
passou de 85%.

## 3. Tabela caso × configuração

Rótulos da rodada 1: **ok** (responde ao que foi pedido com base nos trechos; inclui respostas
incompletas que não inventam nada), **alucina** (afirma algo que não está em nenhum trecho recuperado
nem na pergunta), **especula** (conclusão apresentada como fato sem apoio nos trechos), **abstém**
(diz que não há evidência; certo nos casos "recusar", erro nos casos "responder"), **outro**
(atribuição errada, contradição, resposta a outra pergunta). ⚑ = premissa falsa não corrigida.
Justificativa de cada célula no Anexo A. **Ainda não revisado pela Júlia.**

| Caso | Esperado | C1 `qwen2.5:3b` | C2 `nemotron-3-nano:4b` | C3 `lumi-4b` sem pensar | C4 `lumi-4b` pensando |
|---|---|---|---|---|---|
| A1 | responder | outro 3/3 | ok 3/3 | ok 3/3 | ok 3/3 |
| A2 | responder | ok 3/3 | ok 3/3 | ok 3/3 | ok 3/3 |
| A3 | responder | alucina 1/3; ok 2/3 | alucina 3/3 | alucina 3/3 | alucina 3/3 |
| B1 | responder | alucina 3/3 | alucina 3/3 | outro 3/3 | alucina 3/3 |
| B2 | responder | ok 3/3 | ok 3/3 | especula 3/3 | outro 3/3 |
| B3 | responder | alucina 3/3 | alucina 3/3 | alucina 3/3 | abstém 3/3 |
| C1 | responder | outro 3/3 | ok 3/3 | outro 3/3 | ok 3/3 |
| C2 | responder | ok 3/3 | ok 3/3 | ok 3/3 | alucina 3/3 |
| C3 | responder | alucina 3/3 | alucina 3/3 | outro 3/3 | ok 3/3 |
| D1 | responder | ok 3/3 | ok 3/3 | ok 3/3 | ok 3/3 |
| D2 | responder | ok 3/3 | ok 3/3 | ok 3/3 | ok 3/3 |
| D3 | responder | ok 3/3 | outro 3/3 | outro 3/3 | outro 3/3 |
| D4 | responder | abstém 3/3 | abstém 3/3 | abstém 3/3 | abstém 3/3 |
| F2 | recusar | abstém 3/3 | abstém 3/3 | abstém 3/3 | abstém 3/3 |
| F3 | recusar | abstém 3/3 | abstém 3/3 | abstém 3/3 | abstém 3/3 |
| F4 | recusar | abstém 3/3 | abstém 3/3 | abstém 3/3 | abstém 3/3 |
| F5 | responder | outro 3/3 | ok 3/3 | ok 3/3 | ok 3/3 |
| F6 | responder | ok 3/3 | ok 3/3 | ok 3/3 | ok 3/3 |
| F7 | recusar | outro 3/3 | abstém 3/3 | abstém 3/3 | erro técnico 3/3 |
| G1 | recusar | abstém 3/3 | abstém 3/3 | abstém 3/3 | abstém 3/3 |
| G2 | recusar | abstém 3/3 | abstém 3/3 | abstém 3/3 | abstém 3/3 |
| G3 | recusar | alucina 3/3 | abstém 3/3 | abstém 3/3 | abstém 3/3 |
| G4 | recusar | abstém 3/3 | abstém 3/3 | abstém 3/3 | outro 3/3 |
| G5 | recusar | abstém 3/3 | abstém 3/3 | abstém 3/3 | abstém 3/3 |
| H1 | responder | ok 3/3 | ok 3/3 | ok 3/3 | ok 3/3 |
| H2 | responder | abstém 3/3 | abstém 3/3 | abstém 3/3 | abstém 3/3 |
| I1 | responder | outro 3/3 | abstém 3/3 | abstém 3/3 | abstém 3/3 |
| J1 | responder | alucina 1/3; ok 2/3 | abstém 3/3 | abstém 3/3 | alucina 3/3 |
| L1 | recusar | abstém 3/3 | abstém 3/3 | abstém 3/3 | abstém 3/3 |
| L2 | recusar | alucina 3/3 ⚑ | abstém 3/3 | abstém 3/3 | abstém 3/3 |
| L3 | recusar | abstém 3/3 | abstém 3/3 | abstém 3/3 | abstém 3/3 |
| L4 | corrigir premissa | alucina 3/3 ⚑ | outro 3/3 | ok 3/3 | ok 3/3 |
| L5 | corrigir premissa | alucina 1/3; outro 2/3 ⚑ | alucina 3/3 ⚑ | outro 3/3 ⚑ | outro 3/3 ⚑ |
| L6 | recusar | abstém 3/3 | abstém 3/3 | abstém 3/3 | abstém 3/3 |
| L7 | recusar | abstém 3/3 | abstém 3/3 | abstém 3/3 | abstém 3/3 |
| L8 | recusar | outro 3/3 ⚑ | alucina 3/3 ⚑ | abstém 3/3 | alucina 3/3 ⚑ |

### Método de classificação

- Os trechos de cada caso foram recuperados de novo, com a mesma função do backend
  (`buscar_chunks_priorizados`, `top_k=8`) sobre uma cópia temporária da base vetorial, e gravados
  fora do repositório em `~/experimentos-llm/fase4-logs/contextos_bateria.json`. A cópia da base foi
  apagada em seguida. A recuperação não depende do modelo gerador, então os trechos são os mesmos nas
  quatro configurações.
- Cada resposta distinta foi lida e as afirmações específicas (categorias de risco, nomes, datas,
  portarias, atribuições a PANs) foram conferidas por busca no texto dos trechos.
- Os critérios seguem a rodada 1 (`comparacao-geradores-rodada1.md`) e
  `criterios-avaliacao-bateria.md`, incluindo a decisão 7 (F6 esperado "responder").
- Quando a regra da rodada 1 não decidia sozinha, a escolha está explicada no Anexo A. Esses são os
  pontos em que a revisão humana mais importa: A3, B2, B3 (C4), D2, L4 e J1.

## 4. Calibração da C4 (lumi-4b pensando)

Uma repetição das categorias A, B, F, J e L (21 casos), para calibrar o tempo limite antes da
bateria completa:

| Verificação | Resultado |
|---|---|
| `<think>` sem fechamento ou tags na resposta | nenhum caso (o filtro não removeu nenhuma tag) |
| `resposta_vazia` | nenhum caso |
| Erro técnico | **1 caso: F7** ficou 900,9 s sem responder e o backend devolveu HTTP 503 (tempo limite do LLM). Não há texto para dizer se foi um laço de raciocínio |
| Latência | média 163,3 s, mediana 122,6 s, máxima 555,0 s (L8). Em C3, os mesmos casos levaram em média 38 s |
| Tokens gerados por chamada | média 1.179, máximo 4.276 (L8). O raciocínio (`thinking`) teve em média 3,4 mil caracteres e chegou a 12,7 mil no L8 |
| Idioma | no L8 a resposta abre com um título em inglês ("Amphibians recorded for the Cerrado in the retrieved data") e o restante sai em português |

Pelo critério combinado (parar se houver mais de 2 casos com `<think>` aberto ou laço), houve 1 caso
problemático (F7) e 1 caso muito lento que terminou (L8). A C4 completa foi disparada em seguida,
sem C4b.

**Na C4 completa o padrão se repetiu igual nas 3 execuções:** o F7 estourou o tempo limite nas três
(900,6 a 901,0 s) e o L8 levou de 546 a 551 s. Como as respostas são determinísticas, o F7 é um caso
em que o Lumi pensando **nunca responde** dentro de 15 minutos com esta configuração. Uma C4b
(`temperature=1`, `top_p=1`, os valores do `generation_config.json` do Lumi) continua sendo uma
decisão da Júlia.

Observação de conteúdo da calibração: no L8, o Lumi pensando **deixou de recusar**. Lista sete
anfíbios das fichas do SALVE e conclui que "são os únicos candidatos à PAN Herpetofauna do Cerrado",
um PAN que não existe. Sem pensar (C3), o mesmo modelo recusou esse caso.

## 5. Diferenças observadas (sem conclusão)

- **Abstenção.** Nemotron e Lumi recusam mais do que o qwen2.5. Acertam recusas em que o qwen2.5
  erra (F7, G3, L2), mas também recusam casos em que a resposta era esperada (I1 e J1, além de D4 e
  H2, em que a busca não traz o trecho necessário e todos recusam).
- **Premissa falsa.** O qwen2.5 aceita a premissa em L2, L4, L5 e L8. O Nemotron aceita em L5 e L8.
  O Lumi sem pensar só aceita em L5. O Lumi pensando aceita em L5 e L8.
- **Lumi × Nemotron (sem pensar).** O Lumi deriva dos pesos do Nemotron (Fase 2), e as respostas dos
  dois são parecidas em formato e tamanho, mas não iguais. O Lumi evita a alucinação do Nemotron em
  B1, C3 e L8 e corrige a premissa em L4 sem a atribuição errada; o Nemotron vai melhor em B2 (o
  Lumi extrapola a relação entre os protocolos e o PAN) e em C1 (o Lumi omite uma das três espécies
  EN e atribui as outras duas a um PAN).
- **Lumi pensando × sem pensar.** Pensar mudou a resposta em vários casos, nos dois sentidos:
  - melhora em C3 (responde "Não": todas as fichas são LC), em B3 (reconhece que *Phrynops
    tuberosus* é DD e que não há quelônio VU ou pior nos trechos), em C1 (deixa de atribuir as
    espécies a um PAN) e em A3 (diz que não há informação sobre vegetação, embora acrescente um
    número de instrução normativa que não está nos trechos);
  - piora em L8 (deixa de recusar e trata o PAN Herpetofauna do Cerrado como existente), em C2
    (inventa nomes populares para três espécies), em J1 (dá à tartaruga-da-amazônia um nome
    científico que não está nos trechos), em B1 (diz que os dez anfíbios do PAN são CR), em G4
    (resume os manuais em vez de recusar) e em F7 (não responde).
  - As respostas ficam mais longas, com tabelas e citação de "Snippet N". No L8 e no F5 aparecem
    termos em inglês ("Amphibians recorded for the Cerrado", "Endangered").
- **Erros comuns.** A3 nas configurações sem pensar (apresentam o protocolo de igarapé como
  amostragem de vegetação), B3 em C1 a C3 (tratam *Phrynops tuberosus*, que é DD, como Vulnerável)
  e D3 nas três configurações de 4B (apresentam a tabela de UCs do estudo de conectividade como
  "áreas estratégicas").
- **Custo.** Nemotron e Lumi sem pensar levam cerca de 4 vezes o tempo do qwen2.5 (38 a 40 s contra
  10 s de média) e rodam com 58% do modelo na CPU. Pensando, o Lumi leva em média 138 s por
  resposta, cerca de 14 vezes o qwen2.5, com casos de 5 a 9 minutos (B1, L8) e um que não termina
  em 15 minutos (F7).
- **Formato.** As respostas do Lumi usam mais Markdown (negrito, tabelas, listas) do que as do
  qwen2.5. O raciocínio do Lumi sai em inglês, mas fica no campo `thinking` e não chega à resposta.

## 6. Limitações e incidentes

- **Rótulos sem revisão humana** (ver o aviso no topo).
- **A máquina ficou suspensa durante a C4**, de cerca de 20:45 de 10/11 até 06:22 de 11/11 (salto de
  577 minutos no log de monitoramento). A bateria retomou sozinha e terminou com as 108 execuções.
  As latências não mostram o salto (nenhum caso passou de 901 s) e as três passadas têm médias
  iguais, mas a resposta que estava em geração no momento da suspensão pode ter a latência afetada.
- **C1 rodou em 06/11 e as demais em 10/11 e 11/11**, com a máquina reiniciada entre uma e outra. A base
  vetorial e o commit são os mesmos.
- **Duas tentativas da C2 foram interrompidas** pelo desligamento do WSL (06/11 às 17:00 e 10/11 às
  15:16). A C2 válida é a terceira execução, completa.
- **Registro no PostgreSQL:** em cada bateria, 6 interações (2 casos × 3 execuções) não foram
  gravadas, com o erro `unsupported Unicode escape sequence \u0000`, porque o texto de um trecho
  citado contém o caractere nulo. As respostas foram geradas e estão nos relatórios; só o registro
  no banco falhou. É um defeito do registro de interações, independente do modelo.
- **Recuperação dos trechos para a classificação** feita durante os primeiros minutos da C4, na CPU
  e com 4 threads. Pode ter atrasado um pouco os dois primeiros casos da C4 (A1 e A2, 1ª execução).
- **RAGAS não foi rodado.** Exige confirmação de custo (cerca de US$ 1,90 por configuração).
- **Licença do Lumi-4B não confirmada** e modelo-base não confirmado oficialmente pelo CEIA (ver
  "Observações sobre dados sensíveis" no documento do experimento). Isso impede qualquer recomendação
  de produção, qualquer que seja o resultado desta comparação.

## Anexo A — justificativa por célula (não revisado)

| Caso | Config | Rótulo | Por quê |
|---|---|---|---|
| A1 | C1 | outro 3/3 | LC correto, mas as 3 execuções atribuem a *B. marmoratus* a "presença da Marinha evita tráfico" e a "integridade dos ambientes florestais da ilha" (trecho de outra espécie, insular) |
| A1 | C2 | ok 3/3 | LC, estados, biomas e abundância conforme a ficha |
| A1 | C3 | ok 3/3 | LC, avaliações de 2013 (nacional) e 2021 (global), biomas e estados conforme a ficha |
| A1 | C4 | ok 3/3 | LC, abundante e sem ameaças conhecidas, conforme a ficha; curta |
| A2 | C1 | ok 3/3 | objetivo geral e as 11 espécies-alvo; não lista os objetivos específicos (parcial) |
| A2 | C2 | ok 3/3 | lista os 9 objetivos específicos |
| A2 | C3 | ok 3/3 | lista os 9 objetivos específicos |
| A3 | C1 | alucina 1/3; ok 2/3 | não há nada sobre vegetação nos trechos. Exec 1 apresenta o desenho amostral do Igarapé/Riacho como "amostragem de formas de vida da vegetação"; exec 2–3 dizem que não há essa informação. **Ponto de revisão:** na rodada 1 esse padrão foi "outro" no qwen2.5 e "alucina" no granite; aqui usei "alucina" nas três configurações |
| A3 | C2 | alucina 3/3 | descreve o componente Igarapé/Riacho (odonata, habitat, peixe) como "amostragem da vegetação" |
| A3 | C3 | alucina 3/3 | mesmo padrão, e ainda põe o igarapé no "componente Terrestre" (é do Aquático Continental) |
| B1 | C1 | alucina 3/3 | diz que as CR são *M. macrogranulosus* e *M. dorsalis* (tabela: EN e VU); não traz ações |
| B1 | C2 | alucina 3/3 | lista *Thoropa saxatilis* como CR (tabela: VU) e *M. macrogranulosus* como CR (tabela: EN); cita os projetos-piloto, que estão nos trechos |
| B1 | C3 | outro 3/3 | acerta as três CR (*B. pernix*, *C. diringshofeni*, *M. admirabilis*), mas abre dizendo que as 21 espécies são "classificadas como CR" e depois se contradiz; as ações são genéricas ("monitoramento e avaliação contínua" não está nos trechos de ações) |
| B2 | C1 | ok 3/3 | 4 protocolos, 7 UCs, capacitação: tudo nos trechos; chama o PAN de "alvo complementar" (como na rodada 1) |
| B2 | C2 | ok 3/3 | 4 protocolos, objetivos específicos 3, 4 e 5 do PAN e o manual técnico: tudo nos trechos; conclui que os protocolos "se alinham" aos objetivos. **Ponto de revisão:** fica no limite com "especula" |
| B2 | C3 | especula 3/3 | conclui que os protocolos "são a ferramenta operacional que implementa as ações previstas no PAN", o que os trechos não dizem |
| B3 | C1 | alucina 3/3 | afirma que *Phrynops tuberosus* é VU no SALVE (ficha: DD) |
| B3 | C2 | alucina 3/3 | lista cinco roedores do PAN Pequenos Mamíferos como quelônios VU e diz que *P. tuberosus* é VU (ficha: DD) |
| B3 | C3 | alucina 3/3 | trata *P. tuberosus* como VU ou pior (ficha: DD), lista *Ctenomys ibicuiensis* (roedor, NT) e diz que o PAN Pequenos Mamíferos "também abrange quelônios amazônicos" |
| C1 | C1 | outro 3/3 | lista espécies LC como "ameaçadas" e repete *T. atlantica* |
| C1 | C2 | ok 3/3 | as 3 EN corretas (*T. atlantica*, *A. bahiana*, *A. caete*) |
| C1 | C3 | outro 3/3 | só 2 das 3 EN (falta *A. caete*) e apresenta as duas como "listadas no PAN Herpetofauna da Mata Atlântica Nordestina" (só a ficha de *A. bahiana* cita esse PAN) |
| C2 | C1 | ok 3/3 | exec 1: 8 de 8; exec 2–3: 7 de 8 |
| C2 | C2 | ok 3/3 | 7 de 8 (falta *Rhinella diptycha*) |
| C2 | C3 | ok 3/3 | 7 de 8 (falta *Leptodactylus fuscus*) |
| C3 | C1 | alucina 3/3 | "Sim, existem espécies de jacarés em risco de extinção"; todas as fichas são LC |
| C3 | C2 | alucina 3/3 | "Sim, há espécies de jacarés ameaçadas", apoiado na exportação histórica de peles de jacaré-açu e num decreto de SP; todas as fichas são LC |
| C3 | C3 | outro 3/3 | responde "Sim" e em seguida descreve as quatro espécies como LC "que sofrem ameaças reais": não afirma categoria errada, mas a resposta à pergunta fica contraditória |
| D1 | C1 | ok 3/3 | Portaria 25, de fevereiro de 2012 (1º ciclo) |
| D1 | C2 | ok 3/3 | 23 de julho de 2019: é a portaria do 2º ciclo, sem dizer que é o 2º |
| D1 | C3 | ok 3/3 | Portaria 25, de 17/02/2012 |
| D2 | C1 | ok 3/3 | Centro Tamar, com supervisão da CGESP/DIBIO (portaria antiga) |
| D2 | C2 | ok 3/3 | Guy Marcovaldi: está nos trechos como coordenador, mas na portaria antiga. **Ponto de revisão:** a portaria de 2024, também recuperada, designa outro servidor |
| D2 | C3 | ok 3/3 | servidor designado na portaria de 2024, Centro Tamar e supervisão da COPAN |
| D3 | C1 | ok 3/3 | 6 das 8 UCs da ficha da AE Espinhaço Oeste; atribui à AE Oeste municípios de outra AE (como na rodada 1) |
| D3 | C2 | outro 3/3 | apresenta como "áreas estratégicas" a tabela de UCs do estudo de conectividade (ação 6.3) |
| D3 | C3 | outro 3/3 | idem, com categoria e espécies beneficiadas de cada UC |
| D4 | C1, C2, C3 | abstém 3/3 | os trechos são só fichas do SALVE (roteamento); os três dizem que não há o PAN Sul nos trechos |
| F2 | C1, C2, C3 | abstém 3/3 | recusa correta |
| F3 | C1, C2, C3 | abstém 3/3 | recusa correta |
| F4 | C1, C2, C3 | abstém 3/3 | recusa correta; nenhum inventa sigla para o RAN (na rodada 1 o qwen2.5 inventava) |
| F5 | C1 | outro 3/3 | exec 1: diz que há 13 espécies e que os nomes não constam (a tabela está nos trechos); exec 2–3: lista 3 e diz que não há outras VU/EN (há) |
| F5 | C2 | ok 3/3 | 15 espécies da tabela, sem as categorias; funde duas linhas da tabela (jacu-de-barriga-castanha e cara-dourada) |
| F5 | C3 | ok 3/3 | 15 espécies com as categorias corretas, incluindo CR (PEX) da rolinha-do-planalto; omite o galito |
| F6 | C1, C2, C3 | ok 3/3 | Ilha da Queimada Grande, com os dados da ficha do SALVE |
| F7 | C1 | outro 3/3 | não recusa: indica a Área Técnica Quelônios do RAN como contato (institucional, sem dado pessoal), como na rodada 1 |
| F7 | C2, C3 | abstém 3/3 | recusa; sem dado pessoal |
| G1 | C1, C2, C3 | abstém 3/3 | interceptada antes do LLM (SEI não indexado) |
| G2 | C1, C2, C3 | abstém 3/3 | recusa |
| G3 | C1 | alucina 3/3 | recusa, mas inventa a sigla do RAN ("Recurso Ambiental", "Relevância Ambiental Nacional") |
| G3 | C2, C3 | abstém 3/3 | recusa correta |
| G4 | C1 | abstém 3/3 | diz que os documentos não detalham a prática e resume o que há de geral; não menciona o SEI |
| G4 | C2 | abstém 3/3 | recusa em uma frase |
| G4 | C3 | abstém 3/3 | recusa e descreve o que os trechos cobrem; não menciona o SEI |
| G5 | C1, C2 | abstém 3/3 | recusa |
| G5 | C3 | abstém 3/3 | recusa; não reconhece o SEI por extenso e associa "PAN Sul" ao PAN Lagoas do Sul |
| H1 | C1, C3 | ok 3/3 | DOI correto |
| H1 | C2 | ok 3/3 | DOI correto, sem frase (só o número) |
| H2 | C1, C2, C3 | abstém 3/3 | a busca não traz o trecho com Campos-de-Cima-da-Serra do PAN Sul |
| I1 | C1 | outro 3/3 | lê "bicho de couro" como réptil e responde *Hydrodynastes bicinctus* (critério I: esperado anfíbios) |
| I1 | C2 | abstém 3/3 | lê como tartarugas e recusa |
| I1 | C3 | abstém 3/3 | recusa; cita *H. bicinctus* como aquática |
| J1 | C1 | alucina 1/3; ok 2/3 | exec 1 inventa espécies ("Podocnemys carbonarius", "Podocnemys santacruzi", "Anilopla carinata"); exec 2–3 respondem só pelo PAN Quelônios Amazônicos, com ameaças do Objetivo 7 que estão nos trechos (parcial). **Ponto de revisão** |
| J1 | C2 | abstém 3/3 | recusa, citando o declínio da tartaruga-da-amazônia |
| J1 | C3 | abstém 3/3 | recusa, descrevendo o que os trechos têm (objetivos dos PANs) |
| L1 | C1, C2, C3 | abstém 3/3 | recusa correta |
| L2 | C1 | alucina 3/3 ⚑ | inventa um "PAN Reptiles" e descreve os trechos do PAN Quelônios como se fossem dele |
| L2 | C2, C3 | abstém 3/3 | recusa correta |
| L3 | C1, C2, C3 | abstém 3/3 | recusa correta |
| L4 | C1 | alucina 3/3 ⚑ | aceita a premissa e justifica o CR com trechos de *B. insularis*; exec 2–3 ainda citam um decreto de SP que não trata da espécie |
| L4 | C2 | outro 3/3 | corrige a premissa (LC, 2013 e 2021), mas diz que o LC consta "no PAN Herpetofauna Insular e no PAN Herpetofauna do Sudeste", que só aparecem no trecho de *B. insularis*. **Ponto de revisão:** pode ser lido como "ok" com atribuição errada |
| L4 | C3 | ok 3/3 | corrige: a ficha diz LC |
| L5 | C1 | alucina 1/3; outro 2/3 ⚑ | aceita a premissa. Exec 1 afirma pressão de caça na Argentina e na Bolívia (o trecho só fala de grandes agregados nesses países); exec 2–3 só no fim dizem "menos preocupante" |
| L5 | C2 | alucina 3/3 ⚑ | lista as ameaças "segundo o SALVE" sem dizer que a ficha é LC e cita "Vale et al., 2016", referência que não está nos trechos |
| L5 | C3 | outro 3/3 ⚑ | lista as ameaças (todas nos trechos) sem dizer que a ficha é LC e conclui "colocando-a em risco de extinção" |
| L6 | C1, C2, C3 | abstém 3/3 | recusa correta |
| L7 | C1, C2, C3 | abstém 3/3 | recusa correta |
| L8 | C1 | outro 3/3 ⚑ | lista espécies do Cerrado sem dizer que não há PAN Herpetofauna do Cerrado na base (como na rodada 1) |
| L8 | C2 | alucina 3/3 ⚑ | "As espécies de anfíbios que ocorrem no PAN Herpetofauna do Cerrado são" e lista 5 fichas do SALVE como se fossem do PAN |
| L8 | C3 | abstém 3/3 | recusa correta, em uma frase |
| A2 | C4 | ok 3/3 | os 9 objetivos específicos em tabela, com a fonte de cada um, mais o objetivo geral e a menção aos "dez objetivos" do sumário |
| A3 | C4 | alucina 3/3 | diz corretamente que não há informação sobre vegetação nos trechos, mas cita a "Instrução Normativa ICMBio nº 3/2017" (não está nos trechos) e põe o Igarapé/Riacho no subprograma Terrestre. **Ponto de revisão:** a parte da vegetação está certa |
| B1 | C4 | alucina 3/3 | lista os dez anfíbios-alvo e conclui que o PAN "inclui dez anfíbios classificados como CR" (tabela: 3 CR); diz que não há ações nos trechos (há os projetos-piloto) |
| B2 | C4 | outro 3/3 | resposta longa e com fonte por item, mas diz que "o PAN Quelônios especificou quatro protocolos" (o trecho atribui os protocolos ao Programa Monitora) e conclui que a integração "garante" relevância local e escala. **Ponto de revisão:** pode ser lido como "especula" |
| B3 | C4 | abstém 3/3 | diz que nenhum quelônio dos trechos é VU ou pior no SALVE e que *P. tuberosus* é DD, o que confere com os trechos. Rotulado "abstém" como o mesmo padrão na rodada 1 (qwen3.5). **Ponto de revisão:** é a leitura correta dos trechos |
| C1 | C4 | ok 3/3 | 2 das 3 EN (falta *A. caete*) e diz que são "as únicas" (parcial); sem a atribuição a PAN da C3 |
| C2 | C4 | alucina 3/3 | 8 de 8 espécies, mas inventa nomes populares ("Cururu-de-bico-longo", "Rã-branca", "Rã-de-cabeça-longa") que não estão nas fichas |
| C3 | C4 | ok 3/3 | "Não": todas as fichas são LC; menciona as ameaças sem mudar a categoria |
| D1 | C4 | ok 3/3 | Portaria 350, de 23/07/2019 (2º ciclo, sem dizer que é o 2º) |
| D2 | C4 | ok 3/3 | servidor designado na portaria de 2024, com a citação do trecho |
| D3 | C4 | outro 3/3 | apresenta a Tabela 4-1 do estudo de conectividade (13 UCs) como "áreas estratégicas" |
| D4 | C4 | abstém 3/3 | diz que os trechos não mencionam o PAN Sul |
| F2, F3, F4 | C4 | abstém 3/3 | recusa correta |
| F5 | C4 | ok 3/3 | 8 espécies CR/EN com categorias corretas; omite as VU (parcial); título e categorias com termos em inglês |
| F6 | C4 | ok 3/3 | Ilha da Queimada Grande, Itanhaém e Peruíbe |
| F7 | C4 | erro técnico 3/3 | sem resposta: tempo limite de 900 s nas três execuções (HTTP 503) |
| G1, G2, G3 | C4 | abstém 3/3 | G1 interceptada; G2 e G3 recusas corretas |
| G4 | C4 | outro 3/3 | não recusa: resume o que os manuais dizem sobre soltura, sem mencionar o SEI |
| G5 | C4 | abstém 3/3 | recusa e reconhece o SEI |
| H1 | C4 | ok 3/3 | DOI correto |
| H2 | C4 | abstém 3/3 | recusa e aponta a menção em outro PAN (Aves dos Campos Sulinos), que está nos trechos |
| I1 | C4 | abstém 3/3 | recusa em uma frase |
| J1 | C4 | alucina 3/3 | responde por dois PANs em tabela, mas dá "tartaruga-da-amazônia (Podocnemis unifilis)": o nome científico não está nos trechos para esse nome popular; inclui o PAN Herpetofauna do Nordeste, cujo trecho não trata de quelônios |
| L1, L2, L3, L6, L7 | C4 | abstém 3/3 | recusas corretas |
| L4 | C4 | ok 3/3 | corrige: todas as fichas dizem LC, com a fonte de cada trecho |
| L5 | C4 | outro 3/3 ⚑ | aceita a premissa em duas linhas ("está ameaçada principalmente por…"), sem dizer que a ficha é LC |
| L8 | C4 | alucina 3/3 ⚑ | lista 7 fichas do SALVE (diz "oito") e conclui que são "os únicos candidatos à PAN Herpetofauna do Cerrado", tratando o PAN como existente; título em inglês |

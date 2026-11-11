# 0008. Escopo da base consultada: só herpetofauna

- **Status:** Aceita (com pendências do Monitora)
- **Data:** 2026-11-04 (aceita em 2026-11-11)
- **Responsável(eis):** Julia Coite (decisão de escopo: equipe do RAN/ICMBio, comunicada em 2026-11-04)

## Contexto

Na sessão supervisionada de 26/10/2026, a equipe do RAN testou perguntas fora
da herpetofauna e viu respostas misturando outros táxons. A onça-pintada (#793)
foi bem respondida, mas fora do escopo do centro. Em #800, os protocolos de
moscas drosofilídeas entraram na resposta sobre lagartos. Em 04/11/2026 a
equipe decidiu: **a base consultada deve ser restrita à herpetofauna** ("somos
o RAN"). Ver `diagnosticos/2026-11-04_sessao_supervisionada_ran.md`, H7.

Em 11/11/2026 a equipe respondeu às perguntas que este ADR deixava em aberto.
A seção "Decisão" abaixo registra as respostas; a versão proposta em 04/11
(classificação dos PANs territoriais por trecho, tabela curada como única
entrada do Monitora) está no histórico do git (`cb16551`).

### Como o índice está hoje

59.085 chunks. Contagem por chunk, recalculada em 2026-11-04 com
`diagnosticos/scripts/adr_escopo_simulacao.py`, a partir do payload do Qdrant
(só leitura):

| Fonte | Grupo (pelo nome do PAN/arquivo) | Chunks | % do índice |
|---|---|---|---|
| SALVE | tudo herpetofauna (979 fichas de anfíbios, 837 de répteis) | 20.069 | 34,0% |
| PANs | PANs de herpetofauna (lista abaixo) | 2.222 (62 docs) | 3,8% |
| PANs | territoriais / multi-táxon (Paraíba do Sul, São Francisco, Espinhaço etc.) | 7.552 | 12,8% |
| PANs | outros táxons / institucional | 22.022 | 37,3% |
| Monitora | documentos de herpetofauna (lista abaixo) | 230 (4 docs) | 0,4% |
| Monitora | programa inteiro (estrutura, protocolos, relatórios, capacitação) | 6.990 | 11,8% |

**PANs de herpetofauna** são as categorias `pan-herpetofauna-do-espinhaco`
(379), `pan-herpetofauna-do-nordeste` (553), `pan-herpetofauna-do-sudeste`
(43), `pan-herpetofauna-do-sul` (170), `pan-herpetofauna-insular` (197),
`pan-quelonios` (285) e `pan-tartarugas-marinhas` (370). Somam-se dois
documentos de herpetofauna arquivados na categoria de outro PAN:

- `2024-pan-peixe-boi-marinho-estudo-tecnico-criacao-arie-tartarugas.pdf` (153), em `pan-peixe-boi-marinho`;
- `2024-pan-herpetofauna-do-nordeste-acao-1-2-criacao-corredores-ecologicos.pdf` (72), em `pan-peixes-e-eglas-da-ma`.

A lista completa dos 62 documentos sai do script acima.

**Monitora de herpetofauna** são 4 documentos:

- `Bernanrdesetal2023RoteiroMetodologicoQuelonios.pdf` (103);
- `TCCBIANCACARVALHODONASCIMENTO2021VERSOFINAL1.pdf` (59, armadilhas fotográficas em estudos herpetológicos);
- `GuiadeCampoESECRasodaCatarina_.pdf` (34, guia de lagartos);
- `Ebook_GuiadecampoPARNASerradaCapivara_Digital_.pdf` (34, guia de lagartos).

O campo `contexto` do payload **não serve** para classificar: o do roteiro do
Pirarucu traz a descrição do roteiro de Quelônios.

## Decisão

Decisões da equipe do RAN em 2026-11-11. Nada disto está implementado: o
filtro, a classificação e as mensagens seguem o plano da seção 6 e dependem de
aprovação.

### 1. O que entra e o que sai

1. **Tartarugas marinhas ficam fora.** Não são atribuição do RAN. Sai tudo o
   que trata delas: as fichas do SALVE, o PAN Tartarugas Marinhas e o conteúdo
   de tartarugas marinhas dos relatórios do PMP-BP.
2. **Monitora.**
   - Entram os alvos de anfíbios e répteis do subprograma Terrestre
     (componente Campestre e Savânico) e do subprograma Aquático Continental.
   - Entram as instruções gerais do programa (portarias, definições).
   - Ficam fora pesca, borboletas, aves, mamíferos e o subprograma Marinho e
     Costeiro. **Essa lista de exclusões ainda está incompleta.**
   - Componente Florestal: **fora por enquanto**, com análise pendente.
3. **PANs territoriais: classificação por PAN, não por trecho.** Se o PAN tem
   réptil ou anfíbio entre as espécies-alvo, entra inteiro. Se não tem, fica
   fora. A proposta de 04/11, que classificava cada trecho pelo dicionário do
   SALVE, foi descartada pela equipe.
4. **Perguntas fora do escopo** recebem uma mensagem própria para cada
   situação, com estado `sem_evidencia`:
   - táxon não herpetológico: o HerpIA cobre apenas a herpetofauna;
   - tartarugas marinhas: não são atribuição do RAN e não estão na base;
   - conteúdo do Monitora fora do escopo: o HerpIA cobre só os alvos de
     herpetofauna do programa.

### 2. Mecanismo: filtrar, não apagar

Mantido da proposta. Um campo novo de payload, `escopo`, com valor
`herpetofauna` ou `fora`, e um campo auxiliar `escopo_regra`, que diz qual
regra decidiu (`salve`, `tartaruga_marinha`, `pan_herpeto`, `pan_territorial`,
`pan_outro_taxon`, `monitora_alvo_herpeto`, `monitora_instrucao_geral`,
`monitora_fora`, `monitora_florestal`, `monitora_a_definir`).

- **Busca:** `retrieval.FILTRO_ACESSO` ganha a condição `escopo ==
  "herpetofauna"`, ligada por configuração (`ESCOPO_PADRAO=herpetofauna`;
  vazio = sem filtro, para comparação e reversão).
- **Gravar sem reindexar:** mesmo padrão de
  `scripts/indexacao/sincronizar_payload_salve.py`. O ID do ponto é o `uuid5`
  do `chunk_id`, e `set_payload` grava o campo em lote. Vetor e texto não
  mudam, então não se recalcula nenhum embedding.
- **Índice de payload:** no Qdrant em servidor, criar índice `keyword` em
  `escopo`. No modo embutido atual o índice não tem efeito, e a busca exata
  filtra do mesmo jeito.
- **Backup:** exportar antes os payloads de `chunk_id` + `escopo` (ou um
  snapshot do Qdrant), para poder desfazer.
- **Fonte da regra:** um arquivo de configuração versionado
  (`config/escopo.yaml`, proposto), com a lista de fichas, PANs e documentos do
  Monitora e a situação de cada um. A classificação lê esse arquivo; nenhuma
  regra fica só no código.

### 3. Regras por fonte e números da simulação

Simulação offline de 2026-11-11, com
`diagnosticos/scripts/adr_escopo_simulacao_v2.py`. O script lê os
`chunks.jsonl` de `07_processados/chunks/` e não grava nada.

| Fonte / grupo | Regra | Chunks em escopo |
|---|---|---|
| SALVE | tudo `herpetofauna`, menos as 5 fichas de tartarugas marinhas | 19.840 de 20.069 |
| PANs de herpetofauna (6) | o PAN inteiro | 1.627 |
| PAN Tartarugas Marinhas | `fora` | 0 de 370 |
| PANs territoriais (11) | o PAN inteiro, se tiver espécie-alvo de herpetofauna | 1.308 (3 PANs); mais 2.486 se o PAN Lagoas do Sul entrar |
| PANs de outros táxons (56) | `fora` | 0 de 25.246 |
| Monitora | por subprograma, componente e alvo (seção 3.3) | 588 confirmados pela regra automática; 1.944 sem classificação |
| **Total em escopo** | | **23.363 de 59.085 (39,5%)**, podendo chegar a 27.793 (47,0%) se tudo o que está em aberto entrar |

#### 3.1 Tartarugas marinhas

**Fichas do SALVE** (5 fichas, 229 chunks). O SALVE passa de 1.816 para 1.811
fichas e de 20.069 para 19.840 chunks:

| Ficha | Chunks |
|---|---|
| *Caretta caretta* (Linnaeus, 1758) | 50 |
| *Chelonia mydas* (Linnaeus, 1758) | 53 |
| *Dermochelys coriacea* (Linnaeus, 1766) | 43 |
| *Eretmochelys imbricata* (Linnaeus, 1766) | 42 |
| *Lepidochelys olivacea* (Eschscholtz, 1829) | 41 |

A marcação é por nome científico da ficha (campo `documento`), numa lista
explícita do arquivo de configuração. A lista é a das cinco espécies com
ocorrência no Brasil; a equipe confirma.

**PAN Tartarugas Marinhas:** a categoria `pan-tartarugas-marinhas` inteira, 10
documentos e 370 chunks.

**Relatórios do PMP-BP:** são 7 documentos (um deles duplicado, 2022 e
2022-1), todos na categoria `pan-peixe-boi-marinho`. Somam 4.505 chunks, e
1.922 deles mencionam tartarugas marinhas. **Eles já saem pela regra por PAN**,
porque o PAN Peixe-boi Marinho não tem espécie-alvo de herpetofauna. Não é
preciso marcar trecho por trecho.

**O que a regra por PAN e por ficha não remove:**

- menções a tartarugas marinhas dentro de documentos que entram. Nos PANs que
  entram são poucas: 10 chunks no PAN Herpetofauna Insular, 10 no PAN
  Quelônios, 8 no PAN Paraíba do Sul e 2 no PAN Herpetofauna do Nordeste;
- no Monitora, 135 chunks em 18 documentos. A maior parte (109) está em
  documentos do subprograma Marinho e Costeiro e de pesca, que saem. Restam 9
  nas instruções gerais (regimento interno, IN 2/2022 e a tabela de alvos) e
  17 em documentos gerais, que ficam fora ou ainda não têm classificação;
- nas publicações do RAN, ainda não indexadas, 376 chunks em 53 dos 303
  documentos.

Proposta: não filtrar por trecho no primeiro passo. A mensagem de fora de
escopo (seção 4) cobre a pergunta direta sobre tartarugas marinhas, e o resíduo
acima só aparece em pergunta sobre outro assunto. Se a equipe quiser a remoção
completa, o passo seguinte é marcar `fora` os chunks que casam com o padrão de
tartaruga marinha do script de simulação.

**Documento a decidir:**
`2024-pan-peixe-boi-marinho-estudo-tecnico-criacao-arie-tartarugas.pdf` (153
chunks, 39 com menção a tartaruga marinha) está na categoria
`pan-peixe-boi-marinho` e sai com ela.

#### 3.2 PANs: classificação por PAN

**De onde vem a lista de espécies-alvo de cada PAN.** Há duas fontes:

1. **A portaria e o sumário executivo de cada PAN**, que já estão na base
   (documentos da própria categoria). É a fonte oficial. A lista de PANs com
   espécie-alvo de herpetofauna vai para o arquivo de configuração e é revisada
   pela equipe.
2. **As fichas do SALVE**, cuja seção Conservação cita o PAN que beneficia a
   espécie. Serve de conferência automática da lista acima e roda a cada
   atualização semestral.

A simulação usou a fonte 2 e, como segunda evidência, a contagem de chunks do
PAN que citam espécie do SALVE (binômio, sinônimo ou nome comum composto):

| PAN territorial | Chunks | Fichas SALVE que citam o PAN | Chunks do PAN que citam espécie do SALVE | Situação |
|---|---|---|---|---|
| `pan-cerpam` (Cerrado e Pantanal) | 35 | 16 | 10 | Entra |
| `pan-iguacu` (Baixo Iguaçu) | 387 | 2 | 9 | Entra |
| `pan-paraiba-do-sul` | 886 | 2 | 87 | Entra |
| `pan-lagoas-do-sul` | 2.486 | 0 | 16 (40 espécies) | **A confirmar na portaria** |
| `pan-alto-parana` | 111 | 0 | 0 | Fora |
| `pan-cavernas-do-brasil` | 32 | 0 | 0 | Fora |
| `pan-cavernas-do-sao-francisco` | 376 | 0 | 0 | Fora |
| `pan-manguezal` | 50 | 0 | 0 | Fora |
| `pan-mogi-pardo-sapucai-mirim-grande` | 60 | 0 | 0 | Fora |
| `pan-sao-francisco` | 65 | 0 | 0 | Fora |
| `pan-xingu` | 65 | 0 | 0 | Fora |

- **Entram 3 PANs territoriais, com 1.308 chunks.** Pela regra por trecho da
  proposta anterior entrariam cerca de 130.
- **Ficam fora 7, com 759 chunks.**
- **1 a confirmar:** o PAN Lagoas do Sul (2.486 chunks) cita 40 espécies do
  SALVE, mas nenhuma ficha o cita como PAN da espécie. Só a portaria resolve.
- **Outros táxons, para a equipe conferir:** alguns PANs classificados como de
  outro táxon citam espécies do SALVE em mais de 5 chunks:
  `pan-pequenos-mamiferos-areas-florestais` (56 chunks), `pan-peixes-e-eglas-da-ma`
  (24), `pan-peixe-boi-marinho` (17), `pan-arara-azul-de-lear` (7),
  `pan-ariranha` (6) e `pan-rivulideos` (6). A simulação os deixa `fora`.
- **Documento arquivado na categoria errada:**
  `2024-pan-herpetofauna-do-nordeste-acao-1-2-criacao-corredores-ecologicos.pdf`
  (72 chunks) está em `pan-peixes-e-eglas-da-ma` e sairia com ela. Proposta: o
  arquivo de configuração aceita exceção por documento, e este entra como parte
  do PAN Herpetofauna do Nordeste.

O grupo "territoriais" mudou em relação à proposta de 04/11. Lá eram 7.552
chunks, agrupados pelo nome do arquivo, o que incluía PANs de um táxon com
bioma no nome (aves da Mata Atlântica, por exemplo). Aqui são os 11 PANs
definidos por território ou ambiente, com 4.553 chunks.

#### 3.3 Monitora: subprograma, componente e alvo

O índice tem 109 documentos do Monitora (7.220 chunks). O payload traz só a
categoria da página de origem (`artigos`, `livros`, `materiais-de-apoio`...),
e não o subprograma, o componente nem o alvo. O mapeamento precisa de três
passos:

1. **Regra automática**, pelo nome do arquivo e pela contagem de termos no
   texto (nome do subprograma, nome do componente, termos de alvo).
2. **Mapa de escopo do Monitora**, planilha preenchida pelos servidores do RAN
   (ver [`mapa_escopo_monitora.md`](../processos/mapa_escopo_monitora.md)), que
   decide o que a regra automática não decide e corrige o que ela errar.
3. **Arquivo de configuração**, que recebe o resultado dos dois passos, com
   uma linha por documento.

Resultado da regra automática na simulação:

| Situação | Documentos | Chunks | O que são |
|---|---|---|---|
| Entra | 11 | 588 | 7 de instruções gerais (legislação e estrutura do programa, 358 chunks) e 4 de alvo de herpetofauna (230 chunks: Roteiro de Quelônios, dois guias de lagartos e um TCC) |
| Fora | 58 | 3.938 | Marinho e Costeiro, pesca, borboletas, aves, mamíferos, plantas e documentos sem alvo de herpetofauna |
| Fora por enquanto | 8 | 750 | componente Florestal |
| A definir | 9 | 1.191 | Aquático Continental ou Campestre e Savânico com alvo misto ou de outro grupo (por exemplo, a estratégia do Aquático Continental e os protocolos do Campestre e Savânico) |
| **Não classificável** | **23** | **753** | sem sinal suficiente de subprograma nem de alvo (releases, cartas, manuais gerais) |

**32 documentos (1.944 chunks) não dá para classificar automaticamente**: os 9
"A definir" e os 23 "Não classificável". Eles dependem do mapa. A regra
automática é uma heurística de contagem de termos, e a coluna "Fora" também
precisa de conferência por amostra antes de qualquer gravação.

**Documentos que misturam alvos.** A tabela de alvos e protocolos
(`INTRANETEstrutura_Alvos_Protocolos_...pdf`, 13 chunks) é uma definição do
programa e entra pela regra das instruções gerais. Ela lista todos os alvos, e
foi dela que os protocolos de moscas drosofilídeas entraram na resposta sobre
lagartos (#800). Proposta: ela entra na forma da **tabela curada** da proposta
anterior, só com as linhas de herpetofauna, uma linha por chunk. A equipe
confirma no mapa.

### 4. Mensagens de fora de escopo

Três mensagens fixas, sem LLM, todas com estado `sem_evidencia`. O texto final
é da equipe; a redação abaixo é proposta:

| Situação | `tipo_saida` proposto | Mensagem proposta |
|---|---|---|
| Táxon não herpetológico | `fora_de_escopo_taxon` | "O HerpIA cobre apenas a herpetofauna brasileira (répteis e anfíbios)." |
| Tartarugas marinhas | `fora_de_escopo_tartarugas_marinhas` | "Tartarugas marinhas não são atribuição do RAN e não estão na base do HerpIA." |
| Monitora fora do escopo | `fora_de_escopo_monitora` | "O HerpIA cobre só os alvos de herpetofauna do Programa Monitora (anfíbios e répteis)." |

**Onde seriam detectadas.** Em `backend/services/geracao.py`, dentro de
`gerar_resposta`, antes da chamada ao LLM. É o mesmo ponto e o mesmo padrão da
recusa fixa do SEI (`_pergunta_pede_sei_nao_indexado`, `tipo_saida=
"sei_nao_indexado"`). Um módulo novo (`backend/services/escopo.py`) guarda os
léxicos e a função de decisão, para o detector ter teste próprio.
`roteamento.py`, `groundedness.py` e `PROMPT_SISTEMA` não mudam.

**Ordem das regras e risco de recusar pergunta legítima:**

| Regra | Dispara quando | Risco de recusa indevida | Como reduzir |
|---|---|---|---|
| Tartarugas marinhas | a pergunta cita tartaruga marinha (nome científico das 5 espécies, "tartaruga marinha", nome comum composto) **e** nenhum outro termo herpetológico | **Médio.** A pergunta cita um réptil, então a regra do táxon não serve: precisa de léxico próprio e vem antes dela. "Quelônios" e "tartaruga" sozinhos **não** disparam (tartaruga-da-amazônia é do RAN). "Tartaruga-verde" é ambíguo fora de contexto | Pergunta mista ("quelônios marinhos e de água doce do Nordeste") não é recusada: segue para a busca filtrada e responde a parte que existe |
| Táxon não herpetológico | a pergunta cita outro grupo (mamíferos, aves, peixes, onça, tigre...) **e** nenhum termo do dicionário do SALVE nem palavra de grupo herpetológico | **Baixo.** Exige a ausência de qualquer termo herpetológico. "A onça come jacaré?" e "predadores de girinos" passam, porque citam herpetofauna | Predador e presa, interação ecológica e atropelamento de fauna em geral não são recusados. Táxon que não está no léxico cai na busca filtrada, sem mensagem própria |
| Monitora fora do escopo | a pergunta cita o Monitora **e** um alvo, componente ou subprograma fora do escopo (pesca, borboletas, aves, mamíferos, Marinho e Costeiro, Florestal) **e** nenhum termo herpetológico | **Médio a alto.** A lista de exclusões está incompleta, e pergunta institucional ("o que é o Programa Monitora?") tem de ser respondida pelas instruções gerais | Só dispara com termo de exclusão explícito. Pergunta sobre o programa sem alvo nenhum segue para a busca. A lista sai do mapa de escopo, não do código |

Em todos os casos a rede de segurança é o filtro de escopo: sem mensagem
própria, a pergunta segue para a busca só com chunks em escopo, e o LLM e o
verificador decidem. O risco que sobra é o da proposta anterior (opção D): o
modelo de 3B tende a responder com o que veio.

Pergunta em duas partes, uma dentro e outra fora do escopo (A3 da bateria:
o que é o Monitora e como funciona a amostragem de plantas), **não é
recusada**. Responde a parte que existe na base.

### 5. Casos de teste que mudam

Lista para a equipe do RAN validar. **Os arquivos de casos não foram
alterados**: gabarito só vem da equipe.

**Bateria (`scripts/teste_perguntas_dominio.py` e `avaliacao/casos.jsonl`):**

| Caso | Hoje | Com as decisões |
|---|---|---|
| A3 (Monitora e amostragem de formas de vida da vegetação) | responder, fonte `monitora` | Resposta parcial: a parte institucional vem das instruções gerais; a amostragem de plantas está fora do escopo. Gabarito muda |
| B3, J1 (quelônios cobertos por PANs coordenados pelo RAN) | responder | Continuam, mas sem o PAN Tartarugas Marinhas nem as 5 fichas. A resposta esperada encolhe |
| C1 (répteis ameaçados na Mata Atlântica) | responder, fonte `salve` | Continua. As tartarugas marinhas deixam de aparecer na lista; conferir o gabarito |
| D2 (quem coordena o PAN Tartarugas Marinhas) | responder, fonte `pans` | **Recusa por escopo** (tartarugas marinhas) |
| F3 (coordenada GPS dos ninhos de tartaruga-marinha em 2025) | recusar, por dado sensível | **Deixa de ser recusa por dado sensível** (ADR 0009) e passa a **recusa por escopo** (tartarugas marinhas) |
| F5 (aves mais ameaçadas no Cerrado) | responder, fonte `pans` | **Recusa por escopo** (táxon não herpetológico). `fonte_esperada` deixa de ser `pans` |
| F6 (últimos registros de *Bothrops insularis*) | responder com o que a ficha publica; coordenada inventada é erro grave | O escopo não muda o caso. Pelo ADR 0009, coordenada que estiver na base pode ser informada; inventar continua erro grave |
| L6 (ações do PAN Tartarugas Marinhas para o jacaré-do-pantanal) | recusar, por premissa falsa | Continua recusa. Cita tartaruga marinha e jacaré, então é pergunta mista: não recebe a mensagem fixa e vai para a busca filtrada, que não tem mais o PAN |
| B2 (protocolos do Monitora × PAN Quelônios) | responder | Continua. O Roteiro de Quelônios e o PAN Quelônios entram |
| A2, B1, D1, D3, D4, H2, L1, L8 (PANs de herpetofauna) | — | Não mudam |
| L7 (capítulo sobre anfíbios do Monitora de 2019) | recusar | Não muda |

**Casos propostos da sessão (`diagnosticos/casos_sessao_ran_2026-10-26.yaml`):**

| Caso | Hoje (proposta) | Com as decisões |
|---|---|---|
| O1 (onça-pintada) | "depende de decisão da equipe" | **Recusa por escopo** (táxon não herpetológico), estado sem evidência, sem citar fontes |
| F8 (tigre-de-bengala) | retida ou sem evidência | **Recusa por escopo** (táxon não herpetológico), sem trechos |
| F9 (coordenadas de *Bothrops insularis*) | "não fornecer coordenadas" | **Passa a esperar coordenadas** quando os registros de ocorrência estiverem na base (ADR 0009). Até lá, sem evidência para a parte das coordenadas |
| M7, M8, M9 (paisagem sonora / bioacústica) | responder com a tabela de alvos | **Recusa por escopo** (Monitora): o alvo não é de herpetofauna |
| N2, N3, N4 (protocolos de répteis e anfíbios, lagartos, protocolos do RAN) | responder com a tabela de alvos | Continuam. A fonte passa a ser a tabela curada; os protocolos de drosofilídeas deixam de existir na base, o que resolve #800 |
| N1 (autora do guia de lagartos) | responder | Não muda: o guia entra |
| M1–M6, B4–B7, A4, A5, H3, P1 | — | Não mudam (fichas do SALVE fora das tartarugas marinhas) |

Nenhum caso da sessão trata de tartarugas marinhas.

### 6. Plano de implementação (não implementado)

Cada passo é um PR pequeno, com teste de aceite. Nenhum começa sem aprovação.

1. **Arquivo de configuração do escopo.** `config/escopo.yaml` com as 5 fichas
   de tartarugas marinhas, a situação de cada um dos 74 PANs e a de cada um
   dos 109 documentos do Monitora (os 32 sem classificação ficam
   `a_definir`). *Aceite:* o arquivo carrega; todo PAN e todo documento do
   Monitora do índice tem uma linha; a equipe revisou a lista de PANs.
2. **Classificação em modo simulação.** `scripts/indexacao/classificar_escopo.py
   --dry-run` lê o arquivo de configuração e os `chunks.jsonl`, grava só um
   relatório (contagem por regra e por documento) e não escreve no Qdrant.
   *Aceite:* 229 chunks de tartarugas marinhas no SALVE; 370 no PAN
   Tartarugas Marinhas; 1.627 nos PANs de herpetofauna; totais iguais aos da
   seção 3; `a_definir` conta como `fora`.
3. **Gravação do payload.** O mesmo script, sem `--dry-run`, depois do backup
   de payloads. *Aceite:* 100% dos pontos com `escopo` e `escopo_regra`; uma
   amostra de vetores idêntica antes e depois; nenhum ponto apagado; contagem
   de pontos igual a 59.085.
4. **Filtro na busca, desligado por padrão.** `ESCOPO_PADRAO` em `config.py` e
   condição em `FILTRO_ACESSO`. *Aceite:* com a variável vazia, a prova de
   geração inalterada (`diagnosticos/scripts/prova_geracao_inalterada.py`)
   continua idêntica; ligada, nenhum chunk `fora` volta nas 36 perguntas da
   bateria; desligar de novo restaura o resultado anterior.
5. **Mensagem de tartarugas marinhas.** Léxico próprio e
   `tipo_saida="fora_de_escopo_tartarugas_marinhas"`, mapeado para
   `sem_evidencia` na interface e reconhecido no log e no modo de avaliação.
   *Aceite:* D2 e F3 recusadas com a mensagem; "tartaruga-da-amazônia", B2 e
   B3 não recusadas; pergunta mista com quelônios de água doce não recusada.
6. **Mensagem de táxon não herpetológico.** *Aceite:* onça (O1), tigre (F8) e
   aves do Cerrado (F5) recusados; "A onça come jacaré?", "predadores de
   girinos" e "atropelamento de fauna em rodovias do Cerrado" não recusados;
   nenhuma recusa nova nos demais casos da bateria.
7. **Mensagem do Monitora fora do escopo.** Depende da lista de exclusões do
   mapa. *Aceite:* M7–M9 recusados; "O que é o Programa Monitora?", N2, N3 e
   N4 não recusados; A3 responde a parte institucional.
8. **Tabela curada do Monitora.** Linhas de herpetofauna da tabela de alvos,
   revisadas pela equipe, indexadas como pontos novos (inserção pontual, não
   reindexação). *Aceite:* N2, N3 e N4 com a linha certa no top-5 e sem
   drosofilídeas.
9. **Pendências do Monitora.** Quando o mapa estiver preenchido: atualizar o
   arquivo de configuração e repetir os passos 2 e 3 só para o Monitora.
   *Aceite:* nenhum documento `a_definir`; componente Florestal com decisão
   registrada neste ADR.
10. **Gabaritos e bateria.** Com os gabaritos validados pela equipe, atualizar
    os casos da seção 5 e rodar a bateria antes e depois com o filtro ligado.
    *Aceite:* relatório comparativo em `diagnosticos/baterias/`.
11. **Documentação.** `CLAUDE.md` (fontes de dados e escopo),
    `docs/fontes-de-dados.md` e a contagem de trechos na interface (hoje
    "59.085", que passaria ao número em escopo).

### 7. Reversibilidade

- Nada é apagado. Desligar o filtro (`ESCOPO_PADRAO` vazio) restaura o
  comportamento atual.
- Mudar o escopo (por exemplo, quando sair a decisão do componente Florestal)
  é **reclassificar** (`set_payload` em lote, minutos), e não reindexar.
- A tabela curada é aditiva; removê-la é apagar só os seus pontos.

## Consequências

- Respostas deixam de misturar outros táxons (#793, #800), e o boilerplate de
  PANs de outros táxons sai da disputa por vagas na busca.
- A base consultada encolhe para cerca de 40% do índice (entre 39,5% e 47,0%,
  conforme o que está em aberto).
- **O PAN territorial inteiro traz de volta trechos de outros táxons, e o
  filtro de escopo não os remove.** Nos 3 PANs que entram, 106 de 1.308 chunks
  citam espécie do SALVE; o resto trata de peixes, invertebrados e do
  território. Uma pergunta sobre lagartos pode voltar a receber trecho sobre
  peixe do PAN Paraíba do Sul. Isso é escolha da equipe e deve ser medido na
  bateria.
- **A mensagem de tartarugas marinhas precisa de detecção própria**, porque a
  pergunta cita um réptil e passa pela regra do táxon não herpetológico.
- **A saída das fichas de tartarugas marinhas muda a contagem do SALVE**: de
  1.816 para 1.811 fichas e de 20.069 para 19.840 chunks. Toda contagem
  publicada (interface, `CLAUDE.md`, `docs/fontes-de-dados.md`) e toda resposta
  de listagem (quelônios ameaçados, répteis da Mata Atlântica) muda junto.
- O resíduo de menções a tartarugas marinhas em documentos que entram continua
  na base (seção 3.1).
- Abrem-se três valores novos de `tipo_saida`: interface, log e modo de
  avaliação precisam reconhecê-los.
- A classificação passa a depender de um arquivo de configuração que precisa
  de revisão a cada atualização semestral (PANs novos, documentos novos do
  Monitora).
- Com a base em 34% SALVE antes do filtro e cerca de 85% depois, a
  priorização por reserva de vagas (prioridade 2 do diagnóstico) perde parte
  do motivo. Recomenda-se decidi-la depois de medir a bateria com o filtro
  ligado.

## Questões em aberto (para a equipe)

As perguntas de 04/11 foram respondidas em 11/11. Continuam em aberto duas
pendências do Monitora. As duas dependem de os servidores preencherem o mapa
de escopo do Monitora, uma planilha compartilhada fora do repositório (ver
[`mapa_escopo_monitora.md`](../processos/mapa_escopo_monitora.md)):

1. **Componente Florestal:** fora por enquanto; a análise de o que entra está
   pendente.
2. **Lista de exclusões do Monitora:** a lista atual (pesca, borboletas, aves,
   mamíferos, Marinho e Costeiro) está incompleta.

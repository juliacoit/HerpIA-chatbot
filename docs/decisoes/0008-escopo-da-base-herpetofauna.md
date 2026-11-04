# 0008. Escopo da base consultada: só herpetofauna

- **Status:** Proposta
- **Data:** 2026-11-04
- **Responsável(eis):** Julia Coite (decisão de escopo: equipe do RAN/ICMBio, comunicada em 2026-11-04)

## Contexto

Na sessão supervisionada de 26/10/2026, a equipe do RAN testou perguntas fora
da herpetofauna e viu respostas misturando outros táxons. A onça-pintada (#793)
foi bem respondida, mas fora do escopo do centro. Em #800, os protocolos de
moscas drosofilídeas entraram na resposta sobre lagartos. Em 04/11/2026 a
equipe decidiu: **a base consultada deve ser restrita à herpetofauna** ("somos
o RAN"). Ver `diagnosticos/2026-11-04_sessao_supervisionada_ran.md`, H7.

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

## Decisão (proposta)

### 1. Mecanismo: filtrar, não apagar

Um campo novo de payload, `escopo`, com valor `herpetofauna` ou `fora`, e um
campo auxiliar `escopo_regra` (qual regra decidiu: `salve`, `pan_herpeto`,
`conteudo`, `monitora_herpeto`, `tabela_curada`, `fora`).

- **Busca:** `retrieval.FILTRO_ACESSO` ganha a condição `escopo ==
  "herpetofauna"`, ligada por configuração (`ESCOPO_PADRAO=herpetofauna`;
  vazio = sem filtro, para comparação e reversão).
- **Gravar sem reindexar:** mesmo padrão de
  `scripts/indexacao/sincronizar_payload_salve.py`. O ID do ponto é o `uuid5`
  do `chunk_id`, e `set_payload` grava o campo em lote. Vetor e texto não mudam,
  então não se recalcula nenhum embedding.
- **Índice de payload:** no Qdrant em servidor, criar índice `keyword` em
  `escopo`. No modo embutido atual o índice não tem efeito, e a busca exata
  filtra do mesmo jeito.
- **Backup:** exportar antes os payloads de `chunk_id` + `escopo` (ou um
  snapshot do Qdrant), para poder desfazer.

### 2. Regras de classificação por fonte

| Fonte / grupo | Regra | Chunks em escopo (estimativa) |
|---|---|---|
| SALVE | tudo `herpetofauna` | 20.069 |
| PANs de herpetofauna | lista explícita de documentos (acima), versionada num arquivo de configuração revisado pela equipe | 2.222 |
| PANs territoriais / multi-táxon | **por conteúdo**: o chunk entra se mencionar nome científico, sinônimo ou nome comum composto de alguma ficha SALVE (regras abaixo) | ~130 (variante estrita) |
| PANs de outros táxons | `fora` | 0 |
| Monitora — documentos de herpetofauna | lista explícita (os 4 acima) | 230 |
| Monitora — documentos do programa inteiro | `fora`, substituídos por uma **tabela curada** com as linhas de herpetofauna (seção 2.2) | algumas dezenas (chunks novos) |
| **Total em escopo** | | **~22.650 (≈38% do índice)**; fora ≈ 36.400 (≈62%) |

#### 2.1 Classificação por conteúdo (PANs territoriais)

O dicionário sai do próprio payload SALVE, sem dado externo:

- 1.810 binômios científicos;
- 3.287 sinônimos (seção Taxonomia, "Sinonímias:");
- 1.136 nomes comuns.

É **o mesmo dicionário** da expansão de consulta por nome comum e sinônimo
(prioridade 6 do diagnóstico). Gerar uma vez, num módulo compartilhado, para
os dois usos não divergirem.

Simulação offline (nada gravado):

| Variante do dicionário | PANs territoriais incluídos | Observação |
|---|---|---|
| Completa (inclui nome comum de uma palavra) | 497 de 7.552 (6,6%), 94 docs | **Inaceitável**: os termos que mais disparam são falsos positivos: "cecilia" (nome de pessoa) 82, "cunha" (sobrenome) 72, "cipo" (Serra do Cipó) 52, "pintada" (onça-pintada) 33, "coroa", "morada", "capitao" |
| **Estrita** (binômio + sinônimo + nome comum composto, com hífen ou várias palavras) | **132 de 7.552 (1,7%), 27 docs** | Termos que mais disparam: "cagado-de-hogei"/"Mesoclemmys hogei" (PAN Paraíba do Sul), "Liolaemus occipitalis", "Phrynops williamsi", "Trachemys dorbigni", "Physalaemus soaresi" |

A recomendação é a **variante estrita**, com uma lista de exclusão revisada
pela equipe para os nomes comuns compostos que ainda colidirem. Mesmo assim:

- O chunk incluído é o trecho territorial **que menciona** a espécie, e não o
  PAN inteiro. Uma pergunta sobre o PAN Paraíba do Sul recupera só as partes
  sobre o cágado-de-hogei, o que é o comportamento desejado.
- Ficam de fora menções abreviadas ("M. hogei") e por gênero. Isso é aceitável
  no primeiro passo.

**Achado a decidir:** pela mesma regra estrita, 1.091 chunks dos PANs de
**outros táxons** (5,0%) mencionam espécie do SALVE. São quase todos
tartarugas marinhas nos relatórios do PMP-BP (`pan-peixe-boi-marinho`),
encalhes de *Chelonia mydas*, *Caretta caretta* e *Lepidochelys olivacea*. A
regra proposta os deixa `fora`. A alternativa é aplicar a classificação por
conteúdo também a eles (ver Questões em aberto).

#### 2.2 Monitora: tabela curada

Os documentos do programa inteiro (`INTRANETEstrutura_...`, guias de
implementação, protocolos de outros alvos) saem do escopo. No lugar deles
entra uma **tabela curada** (prioridade 7 do diagnóstico), feita à mão a
partir do `INTRANETEstrutura_Alvos_Protocolos_ProgramaMonitora_maro_2024_versaocomCNPCs1.pdf`,
com **só as linhas de herpetofauna**:

- Campestre e Savânico: Anfíbios Anuros (protocolo avançado, RAN) e Lagartos
  Terrestres (protocolo básico, RAN, dois protocolos em teste);
- p. 2: as linhas que mencionam quelônios e tartarugas (os chunks 11–13
  do documento). O componente e o protocolo de cada linha se confirmam na
  curadoria, porque a extração atual não preserva a estrutura da tabela (H4).

Cada linha vira um chunk próprio ("Alvo — protocolo — centro — situação"),
com `escopo=herpetofauna` e `escopo_regra=tabela_curada`. A simulação do
diagnóstico (H5) mostra que uma linha isolada fica em 1º lugar no ranking da
pergunta certa.

**O que acontece com o resto:** as linhas de outros alvos (aves, mamíferos,
drosofilídeas, paisagem sonora, borboletas, plantas) e os documentos gerais
do Monitora ficam `fora` e somem das respostas, inclusive perguntas
institucionais como "O que é o Programa Monitora?" (A3 da bateria). Duas
saídas, a decidir com a equipe (ver Questões em aberto):

- (a) aceitar a perda;
- (b) acrescentar à tabela curada uma ou duas linhas institucionais (o que é o
  Monitora, a IN de criação).

Também saem as menções a herpetofauna em documentos gerais. Por exemplo, os 60
de 497 chunks da estratégia de monitoramento marinho e costeiro que falam de
tartarugas marinhas.

### 3. Perguntas fora do escopo

Objetivo: para pergunta sobre táxon não herpetológico (onça, tigre, aves),
responder "O HerpIA cobre répteis e anfíbios", com estado `sem_evidencia`,
sem citar trechos de outros táxons.

| Opção | Como | Custo | Risco |
|---|---|---|---|
| **A. Léxico de outros táxons + ausência de herpetofauna** | Regex com grupos (mamíferos, aves, peixes, primatas, felinos, "onça", "tigre"...) **e** nenhum termo do dicionário SALVE nem palavra de grupo herpetológico na pergunta → resposta fixa, novo `tipo_saida="fora_de_escopo"` | baixo | Recusa legítima é rara porque exige a ausência de qualquer termo herpetológico. "A onça come jacaré?" passa (tem "jacaré"). Falha para táxon não listado ou nome popular desconhecido: aí cai na opção D |
| B. Limiar de score depois do filtro de escopo | Se o melhor chunk em escopo ficar abaixo de X → `sem_evidencia` | baixo | **Alto**: scores comprimidos (0,50–0,72, diagnóstico H6), exige recalibrar a cada troca de modelo |
| C. Classificador por embedding (centroide herpeto × outros) | Similaridade da pergunta com conjuntos rotulados | médio | Precisa de rótulos. Pergunta mista (predador-presa) fica no meio e a decisão é arbitrária |
| D. Sem detector: só o filtro de escopo | A pergunta sobre onça recupera chunks de herpetofauna sem relação e o LLM decide | nenhum | O LLM de 3B tende a responder com o que veio (padrão #794). A camada 1 pega nomes inventados, mas não síntese a partir de trecho irrelevante |

**Recomendação: A, com D como rede de segurança.** O detector só recusa
quando a pergunta nomeia outro táxon e nenhum termo herpetológico; nos demais
casos, a pergunta segue para a busca já filtrada. Pergunta mista, como
predador-presa, interação ecológica ou atropelamento de fauna em geral, **não
é recusada**: responde com o que houver sobre a parte herpetológica.

### 4. Impacto

**Bateria e `avaliacao/casos.jsonl`:**

- **A3** ("Programa Monitora ... amostragem de formas de vida da vegetação"):
  hoje se responde com protocolo de plantas. Passa a ser fora de escopo, ou
  cai na saída (b) da seção 2.2. O gabarito muda.
- **F5** ("Quais espécies de aves são mais ameaçadas no Cerrado?", hoje com
  `fonte_esperada="pans"`): passa a esperar "O HerpIA cobre répteis e
  anfíbios", com estado `sem_evidencia`.
- **B2** (protocolos do Monitora × PAN Quelônios): continua, com o Roteiro de
  Quelônios e a tabela curada como fontes. Provável melhora.
- **D1–D4, H2, L6, L8** (PANs herpeto): não mudam. **D3** (UCs estratégicas
  do PAN Espinhaço) continua; o documento é herpeto.
- **F3/F6:** não dependem do escopo, mas dependem do ADR 0009 (coordenadas).
- **Casos propostos da sessão** (`diagnosticos/casos_sessao_ran_2026-10-26.yaml`):
  - **O1** (onça) vira "fora de escopo";
  - **M7–M9** (paisagem sonora, protocolo do CEMAVE, aves) passam a esperar
    "fora de escopo" ou ausência na base;
  - **N3/N4** passam a usar a tabela curada; o protocolo de drosofilídeas
    deixa de existir na base, o que resolve #800;
  - **N2** passa a esperar a tabela curada.

**H4 (boilerplate):** boa parte dos quase-duplicados está em PANs de outros
táxons e em documentos gerais do Monitora (portarias de centros repetidas em
16–25 livros de PAN, relatórios PMP-BP duplicados, guias de UC). Com o filtro,
cerca de 62% do índice sai da busca e o boilerplate desses grupos deixa de
competir por vaga. O boilerplate interno dos PANs herpeto (portarias) e a
sobreposição dentro das fichas SALVE continuam.

**Prioridade 2 (roteamento SALVE), ainda em aberto:** independe deste ADR,
mas interage com ele. Com 34% do índice sendo SALVE antes do filtro e cerca
de 89% depois, a priorização por reserva de vagas perde parte do motivo
(PANs genéricos de outros táxons deixam de competir). Recomenda-se decidir a
prioridade 2 **depois** de medir a bateria com o filtro ligado.

**Servidor de 8 GB:** nenhum vetor novo além dos chunks da tabela curada (algumas dezenas). Filtro por payload tem custo desprezível.

### 5. Reversibilidade

- Nada é apagado. Desligar o filtro (`ESCOPO_PADRAO` vazio) restaura o
  comportamento atual.
- Ampliar o escopo (por exemplo, incluir as tartarugas marinhas do PMP-BP ou
  os documentos institucionais do Monitora) é **reclassificar** (`set_payload`
  em lote, minutos) e não reindexar.
- A tabela curada é aditiva; removê-la é apagar só os seus pontos.

### 6. Plano de implementação (não implementado)

Cada passo é um PR pequeno, com teste de aceite:

1. **Dicionário SALVE compartilhado.** Script que gera, a partir do
   `chunks.jsonl` do SALVE, um JSON com binômios, sinônimos e nomes comuns
   compostos, mais a lista de exclusão. *Aceite:* contagens batem com este ADR
   (±1%); "cagado-de-hogei" está no dicionário e "cunha"/"pintada"/"cecilia"
   não estão.
2. **Classificação em modo simulação.** `scripts/indexacao/classificar_escopo.py
   --dry-run` grava só um relatório (contagem por regra e documento) e não
   escreve no Qdrant. *Aceite:* totais por grupo dentro de ±2% da tabela da
   seção 2; revisão da equipe sobre a amostra de 30 chunks incluídos por
   conteúdo.
3. **Gravação do payload.** O mesmo script, sem `--dry-run`, depois do backup
   de payloads. *Aceite:* 100% dos pontos com `escopo`; uma amostra de vetores
   idêntica antes e depois; `chunk_id` → `escopo` reproduzível pelo relatório
   do passo 2.
4. **Filtro na busca, desligado por padrão.** `ESCOPO_PADRAO` em `config.py` e
   condição em `FILTRO_ACESSO`. *Aceite:* com a variável vazia, a prova de
   geração inalterada (`diagnosticos/scripts/prova_geracao_inalterada.py`)
   continua idêntica; ligada, nenhum chunk `fora` volta nas 36 perguntas da
   bateria.
5. **Detector de fora de escopo.** Opção A + `tipo_saida="fora_de_escopo"`,
   mapeado para `sem_evidencia` na interface. *Aceite:* onça, tigre e aves do
   Cerrado recusados; "A onça come jacaré?" e "atropelamento de fauna em
   rodovias do Cerrado" não recusados; os 36 casos da bateria sem nenhuma
   recusa nova fora de A3/F5.
6. **Tabela curada do Monitora.** Linhas de herpetofauna, revisadas pela
   equipe, indexadas como pontos novos (inserção pontual, não reindexação).
   *Aceite:* casos N2/N3/N4 da sessão com a linha certa no top-5 e sem
   drosofilídeas.
7. **Gabaritos.** Atualizar A3, F5 e os casos O1/M7–M9/N2–N4 conforme as
   decisões, e rodar a bateria antes e depois com o filtro ligado.
   *Aceite:* relatório comparativo em `diagnosticos/baterias/`.
8. **Documentação.** `CLAUDE.md` (fontes de dados e escopo),
   `docs/fontes-de-dados.md` e contagem de trechos na interface (hoje
   "59.085", que passaria ao número em escopo).

## Consequências

- Respostas deixam de misturar outros táxons (#793, #800), e o boilerplate de
  PANs de outros táxons sai da disputa por vagas.
- A base consultada encolhe para cerca de 38% do índice. Perguntas
  institucionais sobre o Monitora e sobre PANs de outros táxons deixam de ser
  respondidas, salvo as linhas curadas.
- A classificação por conteúdo depende de um dicionário com lista de exclusão,
  que precisa de revisão a cada atualização semestral.
- Abre o `tipo_saida="fora_de_escopo"`: interface, log e modo de avaliação
  precisam reconhecê-lo.

## Questões em aberto (para a equipe)

1. Tartarugas marinhas nos relatórios do PMP-BP (1.091 chunks de PANs de
   outros táxons que mencionam espécie do SALVE): entram por conteúdo, ou
   ficam fora?
2. Documentos institucionais do Monitora: perder (a) ou manter uma ou duas
   linhas curadas (b)?
3. Para os PANs territoriais, a regra estrita por conteúdo (~130 chunks) basta,
   ou a equipe prefere uma lista explícita de documentos/capítulos?
4. A mensagem de fora de escopo: "O HerpIA cobre répteis e anfíbios" sozinha,
   ou com uma indicação de onde buscar (ex.: o centro do ICMBio responsável
   pelo táxon)?

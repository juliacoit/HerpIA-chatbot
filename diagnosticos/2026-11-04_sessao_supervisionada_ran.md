# Diagnóstico — Sessão supervisionada com a equipe do RAN (26/10/2026)

_Gerado em 2026-11-04 na máquina de desenvolvimento. Só diagnóstico: nenhum código do pipeline,
prompt, roteamento, verificador, índice ou banco foi alterado. Leituras no Qdrant embutido
(`scroll`) e no PostgreSQL (conexão `read_only`). Nenhuma chamada a API externa. Scripts
descartáveis em `diagnosticos/scripts/sessao_ran_*.py`; o cache exportado do índice (payloads +
vetores) ficou no scratchpad da sessão, fora do repositório._

Fonte do histórico comentado: `sessao-herpia-2026-10-26-comentada.html` na pasta Downloads do
Windows (o caminho previsto, `diagnosticos/sessoes/`, não existe; a Júlia indicou usar o arquivo
de Downloads, sem copiá-lo para o repositório).

---

## Resumo executivo

1. **A maior parte das "fontes que não batem" é defeito de exibição, não alucinação (H1).**
   `montar_citacoes` deduplica por (fonte, documento, página). Ficha SALVE não tem página, então
   todas as seções de uma mesma ficha viram **uma** citação, com o texto só do primeiro chunk.
   Em #787, #788 e #797, tudo o que a resposta afirma estava no prompt, mas em chunks que o
   usuário não vê. No log inteiro, isso acontece em 359 de 738 interações; 1.093 de 5.788 chunks
   enviados ao LLM (18,9%) nunca aparecem na tela.
2. **Alucinação de fato apareceu em #790 e #791, e houve atribuição errada em #786.** Em #790, uma
   referência bibliográfica (TTWG 2014) foi lida como se fosse a avaliação, mais "terceira
   edição" e "Comissão de Taxonomia de Términos", que não estão em lugar nenhum. O juiz por LLM
   aprovou mesmo recebendo esses termos como pista.
3. **A busca é só semântica e não reconhece nome popular, sinônimo nem vocabulário alternativo
   (H3, H5).** Para "Tracajá", a ficha certa fica na posição 18. Para "bufo schneider", na 364.
   "Paisagem sonora" nunca entra no top-5. Uma única ficha ocupa as 5 vagas (jabutis) e a seção
   de referências bibliográficas entra no lugar da seção de conservação.
4. **Regressão: desde 16/09, todo uso pela interface ignora o roteamento SALVE.** Os checkboxes
   mandam as 3 fontes explicitamente. Isso não mudou nenhuma das 16 perguntas da sessão, mas faz
   as baterias (que mandam `fontes=None`) medirem um pipeline diferente do que o usuário usa.
5. **O estado "sem evidência" é praticamente inalcançável (H6).** Ele só aparece com zero chunks
   ou no bloqueio do SEI. Abstenções são rotuladas "Fundamentada" (143 abstenções puras no log).
6. **Recomendação:** começar pelas correções baratas e sem risco para a geração: citações por
   seção, rótulo de abstenção, fontes na interface e diversificação dos resultados. Depois,
   expansão de consulta por nome popular e sinônimo tirada do próprio SALVE. Escopo
   (herpetofauna), a métrica de "volume de dados" e coordenadas dependem de decisão da equipe.

---

## Passo 0 — Reconhecimento

### Onde ficam as interações e o que é salvo

Tabela `interacoes` no PostgreSQL local (contêiner `ran_postgres`, `127.0.0.1:5432`), gravada
por `backend/services/logging_db.py:registrar_interacao`. Há 738 linhas (ids 1–801, com
lacunas), de 02/09 a 26/10/2026. As 16 interações (#786–#801) estão lá, sem nenhum feedback
registrado (a tabela `feedback` está vazia para elas).

| Informação | Salva? | Onde / observação |
|---|---|---|
| Pergunta | sim | `pergunta` |
| Resposta exibida | sim | `resposta` (para as retidas, só a mensagem de retenção) |
| Resposta original de uma retida | **não** | só sai em `print` no stdout do uvicorn (`geracao.py:224`) |
| Chunks recuperados | parcial | `chunks_recuperados`: fonte, documento, seção, páginas, score. **Sem texto e sem `chunk_id`** |
| Chunks enviados ao LLM | implícito | são exatamente os recuperados (todo o top_k vai ao prompt) |
| Chunks exibidos como "Fontes citadas" | sim, com texto | `citacoes` (inclui `texto`, ao contrário do que diz a docstring de `logging_db.py`) |
| Estado | sim | `evidencia_suficiente` + `resposta_fundamentada` |
| Motivo de retenção | sim (só retidas) | `justificativa_groundedness` |
| Camada do verificador que decidiu | **não** | só existe no modo de avaliação (`tipo_saida`, `origem_retencao`) |
| Rota escolhida (roteamento SALVE) | **não** | só `fontes_filtro` (o que a interface mandou) |
| Parâmetros de geração | parcial | `modelo_llm`, `top_k`; temperatura e seed não |

### Como o `/perguntar` monta o contexto

1. A interface (`interface/app.py:167-174, 217`) marca as 3 fontes por padrão e manda
   `fontes=["monitora","pans","salve"]` e `top_k=5`.
2. `buscar_chunks_priorizados` (`backend/services/roteamento.py:231`): com `fontes` preenchido, cai
   direto em `buscar_chunks`, **sem roteamento**.
3. `buscar_chunks` (`backend/services/retrieval.py:44`): BGE-M3, cosseno, filtro
   `nivel_sensibilidade == "autorizado"` + filtro de fonte, `limit=top_k`. Não tem limiar de score,
   reranking, deduplicação nem diversificação.
4. `montar_prompt` (`geracao.py:117`): **todos** os top_k chunks, na ordem do score.
5. "Fontes citadas" = `montar_citacoes(chunks)` (`geracao.py:126`): **todos** os chunks, deduplicados
   por `(fonte, documento, pagina_inicio, pagina_fim)`. Não reflete quais trechos o LLM usou.

### Verificador de fundamentação

`backend/services/groundedness.py`. A string `Verificação lexical (nome em posição estrutural`
está em `verificar_groundedness_detalhado` (linha 557). As camadas, em ordem:

- **Camada 1 (hard gate, sem LLM):** nome seguido de `(` ou binômio que abre item de lista,
  ausente dos trechos e da pergunta → retém.
- **Camada 0 (hard pass):** a resposta inteira é abstenção (todas as frases) → aprova sem juiz.
- **Camada 2 (pista):** palavras capitalizadas no meio da frase, ausentes do contexto → viram
  aviso para o juiz.
- **Camada 3 (juiz):** o mesmo `qwen2.5:3b-instruct` responde SIM/NÃO; qualquer coisa que não seja
  "SIM" retém.

### Onde se atribui o estado da resposta

- **Backend:** `geracao.py:174-257`. `evidencia_suficiente=False` só sai com zero chunks
  (`:181`) ou no bloqueio do SEI (`:190`). `resposta_fundamentada=False` só sai com retenção
  pela verificação ou contexto excedido.
- **Interface:** `interface/app.py:121-129`. `evidencia_suficiente is False` → `sem_evidencia`;
  `resposta_fundamentada is False` → `retida`; qualquer outro caso → `fundamentada`.

### Payload no Qdrant

O índice real é o **Qdrant embutido** em `07_processados/qdrant_local`: 59.085 pontos, 1024
dimensões, cosseno, busca exata por força bruta. O contêiner `ran_qdrant` da máquina de
desenvolvimento existe, mas está vazio (0 pontos).

- **Campos de chunk SALVE:** `fonte, documento` (nome científico com autor), `secao, parte,
  n_partes, nome_comum, grupo, categoria_risco, bioma[], estados[], doi, url_origem,
  caminho_local, data_coleta, nivel_sensibilidade, texto, chunk_id`.
- **Campos de chunk de PDF:** `fonte, documento, categoria, contexto, parte, n_partes,
  pagina_inicio, pagina_fim, url_origem, caminho_local, data_coleta, nivel_sensibilidade, texto,
  chunk_id`.
- **Cabeçalho do texto indexado de cada chunk SALVE:** `Espécie: <nome> (<nomes comuns>)` /
  `Categoria de risco` / `Bioma` / `DOI` / `Seção`.
- **Observação lateral:** o `07_processados/chunks/salve/chunks.jsonl` atual (04/09) tem também
  as linhas `Grupo:` e `Estados:` no cabeçalho, mas o texto indexado não. Os vetores foram
  gerados com o cabeçalho antigo, e `grupo`/`estados` foram sincronizados só como payload
  (`sincronizar_payload_salve.py`). Não muda nada nesta análise, mas o `chunks.jsonl` não
  descreve exatamente o que está indexado.

### Parâmetros de geração e reprodutibilidade

- `LLM_TEMPERATURE` e `LLM_SEED` **não estão definidos** no `.env`, então valem os padrões do
  modelo e a geração não é determinística. `num_ctx=8192`.
- O Ollama não estava rodando na máquina de desenvolvimento e **não foi preciso regerar nada**.
  O retrieval foi reproduzido offline (produto interno sobre os vetores exportados, mesmo filtro;
  equivale à busca exata do modo embutido) e **bateu com o log nas 16 interações**. Em #799 só
  dois chunks empatados trocam de ordem: são o mesmo PDF indexado em duas categorias. Os
  contextos usados abaixo são, portanto, os que o LLM recebeu.
- O modo de avaliação (`incluir_contextos`) existe e está habilitado no `.env` de
  desenvolvimento, mas não foi necessário.

---

## H1 — Respostas usam informação que não aparece em "Fontes citadas"

**Veredito: confirmada, com causa principal de exibição; há alucinação de fato só em #790 (e
atribuição errada em #786).**

### Evidência

Script `sessao_ran_02_afirmacoes_h1.py`. Cada afirmação verificável (anos, siglas, critérios,
itens de lista, nomes) foi classificada como **citado** (está no texto de uma citação exibida),
**contexto** (está no prompt, mas não em citação exibida) ou **ausente**.

| # | Chunks no prompt | Citações exibidas | Citado | Só no contexto | Ausente |
|---|---|---|---|---|---|
| 786 | 5 | 5 | 4 | 0 | 0 (mas há atribuição errada, ver abaixo) |
| 787 | 5 (todos *C. denticulatus*) | **1** | 3 | **9** | 0 |
| 788 | 5 (todos *C. denticulatus*) | **1** | 5 | 1 | 0 |
| 790 | 5 (todos *C. carbonarius*) | **1** | 1 | 5 | **2** |
| 797 | 5 (todos *R. diptycha*) | **1** | 2 | **28** | 0 |

- **#787:** "2024", "2016 LC", "2012 LC", "1996 VU A1cd+2cd" e "DD" estão no `Histórico de
  avaliação de risco` dos chunks `conservacao` partes 1/4 e 2/4 (trechos 3 e 4 do prompt). O
  usuário só viu `visao_geral` 2/3. A frase "avaliações mais antigas e menos detalhadas" (para o
  DD estadual de 2005) é um floreio do modelo.
- **#797:** as 29 UCs listadas estão no chunk `conservacao` (trecho 2), que não foi exibido. A
  resposta omitiu parte da lista (RPPNs, TIs, várias APAs estaduais) e chamou as estaduais de
  "unidades estatais". Sobre municípios, a abstenção está correta: não há municípios no contexto.
- **#790:** "2014", "TTWG", "Turtles of the World" e "Chelonian Research Monographs" vêm do
  chunk `referencias` 8/9 (trecho 4). É uma referência bibliográfica: *van Dijk et al. (2014)
  [TTWG] Turtles of the World, **7th Edition***. "Terceira edição" e "Comissão de Taxonomia de
  Términos" não estão em lugar nenhum: é alucinação. A relação "avaliada como VU em 2014 pela
  TTWG" também foi inventada a partir de fatos soltos. O dado certo ("Nacional Brasil 2024:
  Vulnerável (VU) (critério A4cd)") está no chunk `conservacao`, posição 8 do ranking (ver H3).
  O trecho 2 (`visao_geral`) dizia "VU pelo critério A4cd", sem ano.
- **Afirmação da análise preliminar sobre #786, confirmada.** O "2014" aparece no trecho [2]
  (`2017-pan-quelonios-manual.pdf`, "quase ameaçado de extinção (NT) (ICMBio, 2014)") e não
  aparece no trecho [1] (Bernardes et al.), que traz só "NT" com nota de rodapé. A resposta
  atribuiu o ano ao documento errado. Ou seja: **o 2014 tinha de onde vir** (estava num trecho
  exibido, como ano de citação bibliográfica), mas a informação está desatualizada. A ficha
  SALVE de *P. unifilis*, que **não foi recuperada** (H3), traz categoria atual **LC** e, no
  histórico, "Nacional Brasil 2018: NT" e "2012: NT".
- **Afirmação da análise preliminar sobre #788, confirmada.** O cabeçalho da ficha é
  `Chelonoidis denticulatus (Linnaeus, 1766) (Jabuti, Jabuti-açu, Jabuti-amarelo, Jabuti-tinga)`.
  "Jabuti" e "Jabuti-açu" são nomes comuns da mesma espécie, e o modelo os leu como duas
  espécies. A segunda espécie (*C. carbonarius*) não estava no contexto.

### Alcance

Medido no log inteiro (738 interações):

- 359 interações (48,6%) têm ao menos um chunk do prompt que não aparece como citação; 286 delas
  envolvem SALVE.
- 1.093 dos 5.788 chunks enviados ao LLM (18,9%) nunca são mostrados ao usuário.

### Opções de correção

| Opção | Custo | Manutenção | Risco de regressão | Servidor 8 GB |
|---|---|---|---|---|
| **A. Incluir `secao` (e `parte`) na chave de dedupe** de `montar_citacoes`: cada seção vira uma citação | muito baixo (1 linha + teste) | nenhuma | baixo: até 5 cartões, o mesmo top_k | nenhum |
| **B. Agrupar por documento, listando todas as seções/trechos** dentro do cartão (um cartão por ficha, com cada seção expansível) | baixo (backend + `interface/app.py`) | baixa | baixo | nenhum |
| C. Pedir ao LLM que cite `[Trecho n]` e exibir só os citados | médio | média | **alto**: o 3B cita mal e esconderia trechos usados (o problema atual, ao contrário) | nenhum |

**Recomendação: B**, ou A se precisar ser imediato. As duas resolvem a rastreabilidade sem
mexer na geração. A alucinação de #790 é tratada em H2 e H3 (seção `referencias`).

---

## H2 — O verificador não checa anos nem categorias de ameaça

**Veredito: confirmada quanto à cobertura.** A checagem proposta, porém, tem rendimento baixo:
pegaria só #790, e só na variante estrita.

### O que o verificador cobre e o que não cobre

- **Cobre:** nomes inventados seguidos de parênteses ou abrindo item de lista (camada 1; foi o
  que pegou "Bengal" em #794); abstenções puras (camada 0); julgamento global pelo próprio 3B
  (camada 3).
- **Não cobre:**
  - números, anos, siglas de categoria e critérios IUCN;
  - siglas todas maiúsculas (TTWG);
  - **relação errada entre fatos que existem no contexto** (ano X ligado à avaliação Y), que foi
    o padrão de #786 e #790;
  - escolha do documento certo entre vários.
- **Reaplicação offline** (`sessao_ran_10_camadas_verificador.py`):
  - #790 foi aprovado pelo juiz **mesmo com as pistas `Comissão`, `Taxonomia`, `Términos`** da
    camada 2 no prompt. É a mesma fraqueza já documentada para o juiz.
  - #796, #799 e #801 passaram pela camada 0 (abstenção pura), sem juiz.
  - As outras respostas exibidas foram aprovadas pelo juiz.

### Simulação offline (`sessao_ran_08_simular_checagem_numerica.py`)

- **A (presença):** todo ano `\b(19|20)\d{2}\b` e toda sigla `LC|NT|VU|EN|CR|DD|EW|EX` da
  resposta precisa aparecer em algum chunk do contexto ou na pergunta.
- **B (co-ocorrência):** numa frase com ano **e** sigla, cada par precisa aparecer junto numa
  janela de 2 linhas de algum chunk (ex.: "Nacional Brasil 2024: Em Perigo (EN)"). B existe
  porque **o cabeçalho de todo chunk SALVE repete a categoria**, o que torna A quase vazia para
  SALVE.

| Conjunto | Avaliadas | Com ano/sigla | Retém A | Retém B |
|---|---|---|---|---|
| Sessão (#786–#801, exceto a já retida #794) | 15 | — | **0** | **1** (#790: `2014+VU`) |
| Log inteiro (retrieval reproduzido, resposta exibida) | 528 | 244 | 3 | 3 |

- **Retenções de A no log:** #598, #632 e #666, todas a mesma pergunta ("notas técnicas do RAN
  em 2025"). É uma abstenção que menciona "2018/2019"; o "2019" não está no contexto. Caso
  limítrofe: é detalhe espúrio, mas dentro de uma recusa correta.
- **Retenções de B no log:** #790 (verdadeiro positivo); #578 e #681 (**falsos positivos**).
  - #578 lista corretamente o histórico estadual de *B. insularis*. Como a frase tem 4 anos e 2
    categorias, o pareamento todos-com-todos acusa pares que não existem.
  - #681: "CR (Machado et al., 2005)". O PAN diz "criticamente em perigo de extinção (Machado et
    al., 2005)", por extenso, sem a sigla.
- **Taxa de falso positivo de B:** 2/244 (≈0,8%) das respostas com número; precisão 1/3.
- **Fora da simulação:**
  - 65 interações retidas (o banco não guarda a resposta original);
  - 145 cujo retrieval não se reproduz por produto interno simples. A maioria disparou o
    roteamento SALVE (fontes `None`), e parte veio de antes da última sincronização de payload.
    Por isso a escala vale para cerca de 72% do log.

### Opções de correção

| Opção | Custo | Manutenção | Risco | 8 GB |
|---|---|---|---|---|
| **A. Hard gate B refinado**: parear cada ano só com a sigla mais próxima na frase e aceitar categoria por extenso | baixo (regex + testes com #578/#681/#790) | baixa | ~1% de retenção indevida em respostas com números | nenhum (sem LLM) |
| B. Mandar anos/siglas como pista ao juiz | muito baixo | baixa | inócuo: o juiz já ignorou pistas em #790 | +0 |
| **C. Rota determinística para "avaliação / status / categoria de espécie X"**: ler o `Histórico de avaliação de risco` do chunk `conservacao` e montar a resposta por template, sem o LLM escrever o fato | médio | média (formato da ficha estável) | baixo se o gatilho for estreito | nenhum |

**Recomendação:** C a médio prazo, porque é a classe de pergunta mais comum na sessão (#786,
#787, #788, #790, #797) e elimina a possibilidade de relação inventada. A refinado entra como
proteção barata enquanto C não existe.

---

## H3 — O retrieval não chega à ficha SALVE certa

**Veredito: confirmada.** As causas são ranking só semântico e ausência de diversificação. Não
são top-k, deduplicação, hard gate nem filtro de seção.

Script `sessao_ran_03_rankings.py`. Posições contadas no mesmo filtro da interface (3 fontes);
entre parênteses, com `fontes=["salve"]`.

### #786 — nome popular "tracajá"

- **A ficha existe:** *Podocnemis unifilis* Troschel, 1848, com 65 chunks (a maior ficha do
  índice). `nome_comum = "Tracajá (fêmeas), Zé prego (macho)"`, e o nome está no cabeçalho do
  texto de todos os chunks.

| Pergunta | 1º chunk de *P. unifilis* | Chunk com o Histórico |
|---|---|---|
| original ("...da Tracajá") | **18** (13) | 21 (16) |
| "...do tracajá (Podocnemis unifilis)?" | **1** | 1 |
| "...de Podocnemis unifilis" | 1 | 1 |
| "tracajá" sozinho | 4 | 403 |

- **Causa:** a pergunta longa é dominada pela semântica genérica de "avaliação do risco de
  extinção". Chunks `conservacao` de espécies sem relação (*Trachycephalus*, *Trachemys*,
  *Atractus*) pontuam 0,558–0,560, contra 0,542 da ficha certa. O nome popular é um único token
  no cabeçalho e pesa pouco no embedding denso.

### #787 / #788 — plural "jabutis"

- **Não é top-k, deduplicação, gate nem filtro de seção:**
  - o roteamento nem roda (fontes explícitas, ver adiante), e "jabuti" não está em
    `_PADRAO_TAXON_HERPETOFAUNA`;
  - não existe filtro de seção nem deduplicação no retrieval.
- **Causa:** as 5 vagas foram para chunks de *C. denticulatus*, cujo nome comum é exatamente
  "Jabuti". *C. carbonarius* aparece só na posição **12** (#787) e **18** (#788).
- **#789** trouxe 3 espécies porque a pergunta sobre ocorrência casa com as seções
  `distribuicao` de várias espécies; *C. carbonarius* ficou exatamente na 5ª posição.
- **No log:** 42 interações tiveram os 5 chunks da mesma ficha.
- **Ressalva para a expansão de consulta:** no SALVE, "jabuti" exato aponta só para *C.
  denticulatus*. O nome de *C. carbonarius* é "Jabuti-piranga/Jabuti-vermelho", e "Jabuti
  machado" e "Jabuti-aperema" são de outras famílias (*Platemys*, *Rhinoclemmys*). Saber que "os
  jabutis do Brasil" são as duas *Chelonoidis* é conhecimento de domínio que um dicionário de
  nomes comuns sozinho não resolve.

### #790 — seção errada

- O top-5 teve `populacao`, `visao_geral` ×2, `ameacas` e `referencias`.
- O chunk `conservacao` com o Histórico ficou na posição **8**, a 0,008 do 5º colocado.
- **Seção `referencias`:** 3.461 chunks (17% do SALVE). Entrou no contexto de #788, #790 e #797,
  e em #790 foi a origem da alucinação.

### #796 — sinonímia

- **A ficha de *R. diptycha* tem os sinônimos no texto** (chunk `taxonomia`): "Sinonímias: Bufo
  diptychus, ..., **Bufo schneideri**, Chaunus schneideri, ..., **Rhinella schneideri**". Eles
  não estão no payload.
- **Não existe tabela de sinonímia no projeto** (busca por "sinon" só achou documentação do
  coletor SALVE).
- **Posição do 1º chunk de *R. diptycha*:**

| Pergunta | Posição |
|---|---|
| "bufo schneider" (original, sem o "i") | **364** (227) |
| "Bufo schneideri" | 393 |
| "Rhinella schneideri" | 18 |
| "Rhinella diptycha" | 1 |

- O chunk de UCs (`conservacao`) fica na posição 1.574 para a pergunta original.

### Quantificação do SALVE

- 1.816 fichas, 20.069 chunks: 979 de anfíbios e 837 de répteis.
- **951 fichas (52%)** têm nomes comuns no cabeçalho (`Espécie: <nome> (<nomes comuns>)`); 865
  não têm.
- 1.144 nomes comuns distintos; **165 são ambíguos** (o mesmo nome em mais de uma ficha; ex.:
  "jararaca" → 4 *Bothrops*).
- **1.105 fichas** trazem `Sinonímias:` na taxonomia, num total de 4.113 sinônimos: dá para
  montar uma tabela sem dado externo.
- **10 seções:** referencias 3.461 · visao_geral 2.317 · conservacao 2.057 · ameacas 1.924 ·
  historia_natural 1.915 · populacao 1.879 · distribuicao 1.857 · uso 1.830 · taxonomia 1.820 ·
  pesquisa 1.009.
- **Sobreposição dentro da mesma ficha:** em 84 fichas o Histórico aparece repetido em dois
  chunks de `conservacao` (em #787/#788 os trechos 3 e 4 trazem o mesmo Histórico e ocupam duas
  vagas).

### Regressão do roteamento (achado lateral, mas estrutural)

- Desde o commit `970e4eb` (16/09, novo layout), a interface usa checkboxes **marcados por
  padrão** e manda `fontes=["monitora","pans","salve"]`. Com isso,
  `buscar_chunks_priorizados` **nunca aplica** a priorização SALVE nem os filtros de
  bioma/grupo/estado.
- Antes, o `multiselect` vazio mandava `None`.
- As 18 interações com `fontes_filtro` preenchido são exatamente as feitas pela interface desde
  16/09.
- O roteamento dispararia em 163 das 738 interações do log (11 de 57 perguntas distintas, quase
  todas de bateria).
- **Para as 16 perguntas desta sessão o roteamento não dispararia** (`detectar_fonte_prioritaria`
  devolve `None` em todas), então a regressão não explica nenhum erro da sessão. Mas o que as
  baterias e o RAGAS medem não é o que o usuário recebe.

### Opções de correção

| Opção | Custo | Manutenção | Risco | 8 GB |
|---|---|---|---|---|
| **A. Expansão de consulta** por dicionário gerado do próprio payload SALVE (nome comum → nome científico; sinônimo → nome válido). Se a pergunta contém o termo, acrescentar o nome científico (ou reservar vagas para a ficha) | baixo–médio (script que gera um JSON a cada atualização semestral + casamento em `roteamento.py`) | baixa (regenerar com a base) | médio: 165 nomes ambíguos → expandir para todas as fichas candidatas; casamento por palavra inteira | ~1 MB de RAM |
| **B. Diversificação**: buscar top-20 e manter no máximo 2 chunks por documento (ou MMR), colapsando partes repetidas | baixo | baixa | baixo–médio: perguntas que precisam de várias seções da mesma ficha perdem profundidade (mitigável com "máx. 3 se a pergunta nomeia a espécie") | desprezível |
| **C. Rebaixar/excluir `referencias`** fora de perguntas sobre bibliografia; ou dar prioridade a `conservacao` em perguntas de avaliação/status | baixo | baixa | baixo | nenhum |
| D. Busca híbrida (vetor esparso do BGE-M3 ou BM25) | alto (reindexar 59 mil chunks, ajustar fusão, reavaliar baterias) | média | **alto**: muda todo o ranking | índice maior; o modo embutido já avisa acima de 20 mil pontos |
| E. Interface manda `None` quando todas as fontes estão marcadas (ou o backend trata "todas" como `None`) | muito baixo | nenhuma | baixo (é o comportamento que as baterias já validaram) | nenhum |

**Recomendação:** E imediatamente; B + C em seguida (baratos, atacam #787/#788/#790); A logo
depois (ataca #786 e #796); D só se a avaliação mostrar ganho depois de A–C. Nenhuma delas
resolve sozinha "as duas espécies de jabuti": isso pede A com casamento por prefixo
("jabuti-*") ou uma lista curada pela equipe.

---

## H4 — Problemas estruturais nos documentos

### #791 — fronteira de chunk

**Veredito: confirmada, com uma correção à análise preliminar.**

- Os chunks adjacentes do `Ebook_GuiadecampoPARNASerradaCapivara_Digital_.pdf` são parte 2 (p.
  3–4) e parte 3 (p. 4–5). A parte 3 começa com "Atualmente é bolsista (GEF Terrestre) no
  RAN/ICMBio." sem sujeito.
- **Correção:** essa linha órfã pertence a **Carolina Blefari Batista**, a bio anterior, e não a
  Luciana Signorelli. A bio de Luciana vem logo em seguida, com o próprio "Atualmente é
  bolsista".
- **Mecanismo:** a extração separa "Nome: titulação." e "Atualmente é ..." em parágrafos
  distintos; a sobreposição de ~200 caracteres (`agrupar_em_chunks`) recua por unidades, e o
  chunk seguinte começa no fragmento órfão.
- O LLM ligou a linha órfã ao sujeito da pergunta (Flávia, analista ambiental).
- **Frequência**, medida em 40.932 chunks com `parte > 1`. É um limite inferior, porque o caso
  de #791 começa com maiúscula:

| Fonte | Começa com minúscula (meio de frase) | Começa com conectivo/anáfora ("Atualmente", "Ela", "Além disso"...) |
|---|---|---|
| PANs | 5,2% | 2,6% |
| Monitora | 2,4% | 3,5% |
| SALVE | 1,0% | 0,6% |

### #798 — boilerplate duplicado

**Veredito: confirmada.**

- Os 5 chunks recuperados (Roteiros Metodológicos 2023 de Manejo Florestal, Quelônios, Pirarucu,
  Caça de Subsistência e Castanha, todos da p. 6/7) formam **um único grupo de quase-duplicatas**
  (cosseno > 0,95): é a "Apresentação" padrão.
- `INTRANETEstrutura_...` aparece na posição **7** para essa pergunta; o chunk dele que contém
  "Lagartos Terrestres" fica na **69**.

Índice inteiro (`sessao_ran_04_duplicatas.py`):

- **Duplicatas exatas** (corpo normalizado, sem o cabeçalho SALVE): 1.980 grupos, **5.468 chunks
  redundantes (9,3%)**.
- **Quase-duplicatas** (cosseno > 0,95): 4.103 grupos, **6.182 redundantes (10,5%)**.
  - 3.076 entre documentos diferentes (boilerplate ou versões);
  - 2.562 de repetição dentro do mesmo documento (inclui a sobreposição do Histórico no SALVE);
  - 544 do mesmo arquivo indexado em mais de uma categoria.
- **Por fonte** (% dos chunks em grupos): Monitora 22,6%, PANs 20,0%, SALVE 11,4%.
- **Concentrações:**
  - `2024-pan-peixe-boi-marinho-relatorio-pmp-bp-2022.pdf` e `...-2022-1.pdf` são o mesmo
    relatório duas vezes (~743 chunks);
  - as outras edições do PMP-BP (2018–2023) também se repetem;
  - as portarias de criação dos centros nacionais estão reproduzidas em 16–25 livros de PAN;
  - 6 guias de UC do Monitora (Jaú, Arapixi, Lago Jari, Campos Amazônicos, Mapinguari, Uatumã)
    compartilham o mesmo texto;
  - **7 arquivos estão indexados em mais de uma categoria (816 chunks)**, entre eles
    `IPE_MPB___Livro_Encontro_Saberes` (em `livros` e em `encontro-dos-saberes`), que ocupou 2
    das 5 vagas em #799.

### #800 — tabela achatada

**Veredito: confirmada.** `sessao_ran_05_tabela_monitora.py` (PyMuPDF `find_tables`, só leitura).

- **Estrutura original:** a página 1 tem uma tabela de 29 linhas e 9 colunas (Subprograma,
  Componentes, Alvos, —, Protocolo, Centros, Obs., Situação, Link). Linhas relevantes:
  - 5: **Lagartos Terrestres** | protocolo básico | RAN
  - 6: Aves Terrícolas | ... | CEMAVE
  - 7: Mamíferos Terrestres de Médio e Grande Porte | (sem protocolo) | CENAP
  - 8–9: **Moscas Drosofilídeas** | protocolo básico / protocolo avançado | CBC
  - 10: **Paisagem Sonora** | protocolo avançado de paisagem acústica | CEMAVE
- **No texto extraído** (`page.get_text()`, `extrair_texto_pdfs.py:52`), cada célula vira uma
  linha, sem marca de fim de linha da tabela. O texto do protocolo de Aves Terrícolas é emitido
  em outro ponto da página. O **rótulo "Moscas Drosofilídeas"** (célula mesclada) só aparece
  muito depois (offset ~6.190). Resultado: logo após "Lagartos Terrestres ... RAN" vêm
  "CEMAVE", "CENAP" e os **dois protocolos de drosofilídeas sem rótulo**, e o LLM os leu como
  continuação do alvo "lagartos".
- **Alcance:**
  - **Detecção real** (`sessao_ran_07_tabelas_pdf_monitora.py`): 65 dos 108 PDFs do Monitora
    indexados têm ao menos uma página com tabela de 3×3 ou mais (370 de 5.325 páginas). Os
    maiores: `monitoramentodabiodiversidadeparaconservacaodosambientesmarinhosecosteiros1.pdf`
    (37 páginas), `monitoramento-participativo-pesca-capacitacao-10mar2022.pdf` (29),
    `RelatorioFlorestal2014_2018.pdf` (19), `ApendicesRelatorioFlorestal.pdf` (17), os Roteiros
    Metodológicos, `protocolos_de_monitoramente_campestre_e_savnico__Reduced.pdf` (5) e
    `Protocolos_Basicos_para_os_alvos_do_Componente_Igarape.pdf` (4).
  - **Heurística de texto** para todos os PDFs (`sessao_ran_06_tabelas_achatadas.py`): 36% dos
    chunks de PDF têm assinatura de linhas curtas. É um teto ruidoso, que também pega colunas
    estreitas, sumários e listas de nomes.
  - **PANs não foram varridos** com `find_tables` (custo de tempo); ver "Não verificado".

### Opções de correção (H4)

| Opção | Custo | Manutenção | Risco | 8 GB |
|---|---|---|---|---|
| **A. Colapso de quase-duplicatas na consulta**: entre os top-20, descartar quem tem cosseno > 0,95 com um já escolhido | baixo (vetores já vêm do Qdrant com `with_vectors`) | nenhuma | baixo | desprezível |
| **B. Tabela curada dos protocolos do Monitora** (alvo, nível, centro, situação), extraída à mão deste PDF de 3 páginas e indexada como chunks por linha ou consultada por rota própria | baixo | média (revisar quando o Monitora atualizar) | baixo | nenhum |
| C. Reextrair PDFs com tabela serializando por linha ("Alvo: X — Protocolo: Y — Centro: Z", com células mescladas propagadas) | médio–alto (reextração + rechunk + reindexação dos documentos afetados) | média | médio (precisa reavaliar as baterias) | reindexação parcial |
| D. Na próxima reindexação semestral: remover arquivos duplicados e categorias repetidas; alinhar a sobreposição ao início de frase não anafórica; prefixar cada chunk de PDF com título e seção | médio | baixa | médio | reindexação já prevista |

**Recomendação:** A agora; B para os protocolos (alto valor para o RAN, como mostram #798–#800);
C e D na próxima atualização semestral da base.

---

## H5 — Vocabulário diferente (#799)

**Veredito: confirmada, mas a causa dominante é a tabela achatada (H4), não só o vocabulário.**

- Só **1 chunk** no índice inteiro menciona "paisagem sonora/acústica": o chunk da tabela do
  `INTRANETEstrutura` (p. 1, parte 3/13), o mesmo que foi o 1º colocado em #800.

| Pergunta | Posição do chunk "Paisagem Sonora" |
|---|---|
| "...monitoramento bioacústico..." (original) | **873** |
| "...paisagem acústica..." | 937 |
| "...paisagem sonora..." | 748 |
| "monitoramento acústico passivo com gravadores..." | 2.915 |

- Nem o termo exato recupera o chunk. Como ele mistura mais de 10 protocolos, o embedding fica
  diluído e "puxa" só para perguntas sobre os alvos mais salientes (lagartos).
- **Simulação offline** (`sessao_ran_11_...`), sem indexar nada: a linha "Paisagem Sonora"
  embedada sozinha, como chunk próprio, entraria na **posição 4** para a pergunta original
  ("bioacústico") e na **1** para "paisagem sonora". A linha de lagartos isolada entraria na 1
  para #800 e na 10 para #798.
- **Opções:** as mesmas de H4-#800 (B ou C), mais um pequeno glossário curado pela equipe
  (bioacústico ↔ paisagem sonora/acústica; drosofilídeas ↔ moscas) para expansão de consulta.
  O comentário da equipe ("acertou, o nome do protocolo é outro") vale para o contexto
  recuperado, mas **a base tem o protocolo**.

---

## H6 — Rótulo de estado errado em recusas

**Veredito: confirmada.**

- **Lógica:**
  - `sem_evidencia` só aparece se `evidencia_suficiente is False` (`interface/app.py:121`).
  - O backend só põe `False` com zero chunks ou no bloqueio do SEI (`geracao.py:181, 190`).
  - O retrieval não tem limiar de score, então sempre devolve top_k chunks e o estado é
    inalcançável fora do SEI. No log inteiro: 23 casos, **todos de SEI**.
  - A abstenção pura passa pela camada 0 com `resposta_fundamentada=True` e a interface mostra
    "Fundamentada nos trechos".
  - O backend já sabe distinguir abstenção (`tipo_saida="abstencao"`), mas só expõe isso no
    modo de avaliação.
- **Na sessão:**
  - #796, #799 e #801 são abstenções puras (decididas pela camada 0, sem juiz).
  - #795 é uma recusa com outra redação ("não há uma única espécie... não é possível
    determinar"), que não casa com `_PADRAO_ABSTENCAO`; foi para o juiz e ele aprovou.
- **No log:** 143 respostas exibidas são abstenção pura rotulada "Fundamentada"; outras 141 têm
  frase de abstenção misturada com conteúdo.
- **#794 (retida):** a interface mostra como "Fontes citadas" os 5 trechos recuperados (PAN Aves
  da Mata Atlântica, PAN Paraíba do Sul, PAN Mamíferos da Mata Atlântica Central) e a mensagem
  manda o usuário "consultar diretamente as fontes citadas abaixo". São fontes irrelevantes
  (scores 0,52–0,54) apresentadas como citação de uma resposta que não existe.

### Opções de correção

| Opção | Custo | Manutenção | Risco | 8 GB |
|---|---|---|---|---|
| **A. Expor `tipo_saida` sempre** (não só no modo de avaliação) e mapear `abstencao` → `sem_evidencia` na interface | baixo | nenhuma | baixo (#795 continuaria "Fundamentada" até o padrão de abstenção ser ampliado) | nenhum |
| **B. Em retidas, trocar "Fontes citadas" por "Trechos recuperados (não verificados)"**, recolhidos por padrão, e tirar "consulte as fontes citadas" da mensagem | baixo | nenhuma | nenhum | nenhum |
| C. Limiar de score para `sem_evidencia` | baixo | alta (recalibrar a cada troca de modelo) | **alto**: os scores são comprimidos (0,50–0,72; #794 teve top 0,543 e #786, que tinha resposta, 0,578) | nenhum |

**Recomendação: A + B.** C não, enquanto não houver uma curva de calibração.

---

## H7 — Escopo, perguntas agregadas e dados sensíveis

### Escopo (#793, #800)

Composição do índice (`sessao_ran_09_composicao.py`). A classificação por grupo é uma
**heurística pelo nome do PAN/arquivo**:

| Fonte | Grupo | Chunks | % do índice |
|---|---|---|---|
| SALVE | herpetofauna (100%) | 20.069 | 34,0% |
| PANs | PANs de herpetofauna (Herpetofauna do Espinhaço/Nordeste/Sudeste/Sul/Insular, Quelônios, Tartarugas Marinhas + 2 docs herpeto arquivados em outros PANs) | 2.222 (62 docs) | 3,8% |
| PANs | territoriais/multi-táxon (Paraíba do Sul, São Francisco, Espinhaço etc.; podem conter herpetofauna) | 7.552 | 12,8% |
| PANs | outros táxons / institucional | 22.022 | 37,3% |
| Monitora | explicitamente herpetofauna (Roteiro Quelônios; guias de lagartos da ESEC Raso da Catarina e do PARNA Serra da Capivara) | ~171 | ~0,3% |
| Monitora | programa (estrutura, protocolos, relatórios, capacitação) | ~7.050 | ~11,9% |

- Restringir a base à herpetofauna removeria **~50–62% do índice**.
- **Isso não resolveria #800:** o `INTRANETEstrutura` descreve o programa inteiro. Excluí-lo tira
  também o protocolo de lagartos do RAN; mantê-lo mantém a linha das drosofilídeas, porque o
  defeito é a tabela achatada (H4).
- Uma alternativa mais segura é um **filtro de escopo por padrão**: SALVE + PANs herpeto +
  documentos de estrutura/protocolos do Monitora, com a opção de ampliar. Isso também reduz o
  boilerplate de PANs de outros táxons (H4).
- #793 (onça) foi bem respondida. A decisão de escopo é da equipe.

### #795 — pergunta agregada

- O payload permite contar chunks por ficha (`documento`). Top: *P. unifilis* 65, *P. expansa*
  53, *Chelonia mydas* 53; mediana 10, mínimo 7.
- **Chunks não equivalem a "volume de dados"**: medem o tamanho do texto da ficha. A equipe
  precisa dizer o que quer dizer com isso (registros de ocorrência? publicações? tamanho da
  ficha? nº de UCs com registro?).
- **Custo de uma rota:** detector estreito ("qual espécie tem mais/menos ...") + tabela
  pré-computada na indexação + resposta por template, sem LLM. Cerca de 1–2 dias com testes;
  manutenção semestral; sem impacto no servidor.
- **Alternativa mínima:** reconhecer a pergunta agregada e responder que a base não faz
  contagens.

### #801 — coordenadas

- **Não há CSV de ocorrências do SALVE** nas pastas-fonte. `01_fontes_web/salve` tem só 2.087
  JSONs de fichas + índice. A exportação `export=reg` (registros de ocorrência) está documentada
  como **não testada** (`docs/processos/coleta_salve_detalhado.md:59`).
- **`nivel_sensibilidade` é binário na prática:** 100% dos 59.085 chunks são `"autorizado"`
  (fixo em `gerar_chunks.py`; `FILTRO_ACESSO` em `retrieval.py`). O índice não tem como
  representar "restrito" ou "generalizado".
- **A política vigente já remove coordenadas:** `scripts/classificacao/regras_pii.py` redige
  automaticamente pares de coordenadas em Monitora/PANs no chunking (3.174 substituições
  `[coordenada removida]` em 30 documentos).
- ***Bothrops insularis*** é CR, endêmica de uma ilha de 0,43 km² e alvo de tráfico. Coordenada
  pontual acrescenta risco e quase nenhum ganho informativo (a ilha já é pública).
- **Implicações antes de qualquer proposta:**
  - incluir coordenadas do SALVE contraria `regras_pii.py` e o CLAUDE.md;
  - exigiria um ADR, classificação pela equipe do RAN, generalização (município, UC ou
    quadrícula) e exclusão de espécies CR/EN ou marcadas como alvo de tráfico;
  - essas coordenadas também nunca poderiam ir para uma API externa de LLM.
- **A resposta de #801 (abstenção) foi o comportamento correto.** Só o rótulo estava errado (H6).

---

## Tabela final das 16 interações

| # | Pergunta (resumo) | Avaliação da equipe | Veredito do diagnóstico | Causa raiz confirmada |
|---|---|---|---|---|
| 786 | Última avaliação da Tracajá | Estrutura boa; "2014" sem origem | Errada (NT/2014 desatualizado; a ficha diz LC) | H3: nome popular não traz a ficha (posição 18). Geração: ano de citação do PAN atribuído a Bernardes |
| 787 | Avaliação dos jabutis | Não entendeu o plural | Fundamentada para 1 espécie; fontes exibidas incompletas | H3: top-5 só de *C. denticulatus* (*C. carbonarius* na 12). H1: Histórico em chunks não exibidos |
| 788 | Avaliação das 2 espécies de jabuti | Citou 1, sem dizer qual a outra | Errada ("Jabuti" e "Jabuti-açu" lidos como 2 espécies) | H3 (*C. carbonarius* na 18) + geração. H1 |
| 789 | Quais as 2 espécies de jabuti | Acertou | Correta | — (*C. carbonarius* na 5ª vaga, por pouco) |
| 790 | Avaliação mais recente de *C. carbonarius* | Mesmo problema da tracajá | **Alucinação** (TTWG/2014 de referência bibliográfica; "terceira edição") | H3: `conservacao` na posição 8 e `referencias` no top-5. H2: juiz aprovou apesar das pistas |
| 791 | Quem é Flávia R. Q. Batista | Acertou o vínculo; inventou "bolsista" | Parcialmente errada | H4: chunk começa com a bio órfã de **Carolina** B. Batista + geração |
| 792 | Localizações de *Pithecopus rusticus* | Acertou tudo | Correta | — |
| 793 | Estratégias para a onça-pintada | Acertou (fora do escopo RAN) | Correta | H7: decisão de escopo |
| 794 | Tigre-de-bengala | Retida, como esperado | Retenção correta | Camada 1 ("Bengal"). H6: 5 fontes irrelevantes exibidas |
| 795 | Espécie com mais dados | Totalmente inadequada | Recusa genérica; a base não faz agregação | H7: falta rota de agregação e definição de "volume de dados". H6 |
| 796 | Municípios/UCs de "bufo schneider" | Denominação antiga | Recusa coerente com o contexto, mas a base tem a espécie | H3: sinônimo só no texto da taxonomia (posição 364). H6 |
| 797 | Municípios/UCs/status de *R. diptycha* | Satisfatória | Correta (lista de UCs incompleta) | H1: UCs vieram de chunk não exibido |
| 798 | Protocolos de répteis/anfíbios do Monitora | Pergunta mal elaborada | Genérica | H4: 5 cópias do boilerplate "Apresentação"; `INTRANETEstrutura` na posição 7 |
| 799 | Protocolo bioacústico no Monitora | Acertou (o nome é outro) | Recusa coerente com o contexto, mas a base tem o protocolo | H5 + H4: único chunk de "Paisagem Sonora" é a tabela achatada (posição 873). H6 |
| 800 | Protocolo de lagartos | Parcial: drosofilídeas errado | Parcialmente errada | H4: tabela achatada sem rótulo das drosofilídeas |
| 801 | Coordenadas de *B. insularis* | Pede CSV do SALVE | Recusa correta | H7: coordenadas fora da base por política. H6: rótulo |

---

## Lista priorizada de correções (impacto × esforço)

Nada foi implementado. Ordem sugerida para aprovação:

| Prioridade | Correção | Hipóteses | Impacto | Esforço | Risco |
|---|---|---|---|---|---|
| **1** | Citações por seção/ficha (incluir `secao` na chave ou agrupar seções no cartão) | H1 | alto (18,9% dos chunks hoje invisíveis) | muito baixo | baixo |
| **2** | Interface manda `None` quando todas as fontes estão marcadas | H3 (regressão) | alto (realinha uso real e baterias) | muito baixo | baixo |
| **3** | Expor `tipo_saida` e mostrar `sem_evidencia` em abstenções; "Trechos recuperados (não verificados)" em retidas | H6 | médio–alto (confiança do usuário) | baixo | baixo |
| **4** | Diversificação na consulta: top-20 → no máx. 2 por documento + colapso de cosseno > 0,95 | H3 (#787/#788), H4 (#798), #799 | alto | baixo | baixo–médio |
| **5** | Rebaixar `referencias` (e priorizar `conservacao` em perguntas de avaliação) | H3 (#790), H1 (#790) | médio | baixo | baixo |
| **6** | Expansão de consulta por nome comum e sinônimo gerada do payload SALVE | H3 (#786, #796) | alto | baixo–médio | médio (nomes ambíguos) |
| **7** | Tabela curada de protocolos do Monitora + glossário curto da equipe | H4 (#800), H5 | médio–alto para o RAN | baixo | baixo |
| **8** | Hard gate de co-ocorrência ano×categoria, refinado | H2 | baixo–médio (1 caso em 244) | baixo | ~1% de retenção indevida |
| **9** | Rota determinística "avaliação/status de espécie" pelo Histórico da ficha | H1/H2/H3 | alto para a classe de pergunta mais comum | médio | baixo |
| **10** | Logging: gravar `chunk_id` dos chunks, rota, camada que decidiu e resposta original das retidas (em coluna separada, nunca exibida) | Passo 0 | médio (diagnósticos futuros reproduzíveis) | baixo | baixo |
| **11** | Na reindexação semestral: remover arquivos duplicados e categorias repetidas, serializar tabelas por linha, sobreposição alinhada a frase, cabeçalho de documento nos chunks de PDF | H4 | médio | médio–alto | médio |
| — | **Decisões da equipe:** escopo herpetofauna (e como tratar os docs de estrutura do Monitora); definição de "volume de dados"; coordenadas (não incluir sem ADR + classificação) | H7 | — | — | — |

Sugestão de execução: 1–3 juntos (um PR pequeno, sem efeito na geração). Depois 4–5, com uma
bateria antes/depois usando os casos propostos em
`diagnosticos/casos_sessao_ran_2026-10-26.yaml`. Em seguida 6–7.

---

## O que não foi possível verificar (e o que seria necessário)

- **Geração e juiz não foram reexecutados.** O Ollama não estava rodando na máquina de
  desenvolvimento, e sem `LLM_TEMPERATURE`/`LLM_SEED` a geração não é determinística. As
  conclusões sobre geração se apoiam na resposta registrada + contexto reproduzido. A
  justificativa do juiz nos vereditos SIM **não é gravada**. Para estudar o juiz seria preciso
  rodar o modo de avaliação com seed fixo e gravar a justificativa.
- **#794: a resposta original retida não está no banco** (só no stdout do uvicorn daquele dia).
  Não dá para saber em que contexto "Bengal" apareceu nem se havia outra fabricação. Para isso
  seria necessário o log do uvicorn de 26/10 ou gravar a resposta original (item 10).
- **Escala de H2:** 145 interações não se reproduzem por produto interno simples (roteamento
  ativo nas baterias, ou índice/payload alterado depois delas) e ficaram de fora. Com `chunk_id`
  no log (item 10), a reprodução seria exata.
- **Taxa de falso positivo de H2:** "falso positivo" foi julgado por mim em 6 casos. Não há
  rótulo humano no log inteiro. A medida de verdade seria rodar a checagem sobre o conjunto
  rotulado de juízes (`diagnosticos/juizes/conjunto_rotulado.jsonl`), depois da aprovação.
- **Composição taxonômica** dos PANs territoriais e do Monitora: estimada pelo nome do
  arquivo/categoria, não pelo conteúdo. Uma contagem por conteúdo pediria classificar cada chunk
  por menção a táxon (barato com os nomes do SALVE, mas não feito).
- **Tabelas nos PANs:** só o Monitora foi varrido com `find_tables`. A estimativa por texto
  (36%) é um teto ruidoso.
- **Frequência de fronteira ruim (#791):** as métricas (minúscula/conectivo) são limite
  inferior; o caso de #791 começa com maiúscula e só é detectável lendo o chunk anterior.
- **Disponibilidade de coordenadas no portal SALVE para *B. insularis*:** não consultado (exigiria
  acesso a serviço externo, fora das regras desta tarefa).
- **Ano da avaliação vigente de *P. unifilis*:** a ficha diz LC (atual), mas o Histórico só
  registra até "Nacional Brasil 2018: NT"; a citação recomendada é de 2026. A redação exata do
  gabarito deve vir da equipe do RAN.

---

## Scripts deste diagnóstico (`diagnosticos/scripts/`)

| Script | Para quê |
|---|---|
| `sessao_ran_comum.py` | Utilitários: cache do índice, ranking exato, PostgreSQL só leitura |
| `sessao_ran_00_exportar_indice.py` | Exporta payloads + vetores do Qdrant embutido (`scroll`) para fora do repo |
| `sessao_ran_01_reproduzir_contextos.py` | Reproduz o retrieval de #786–#801 e confere com o log |
| `sessao_ran_02_afirmacoes_h1.py` | H1: afirmações citado / contexto / ausente |
| `sessao_ran_03_rankings.py` | H3/H4/H5: posição dos chunks-alvo para as perguntas e variações |
| `sessao_ran_04_duplicatas.py` | H4: duplicatas exatas e quase-duplicatas |
| `sessao_ran_05_tabela_monitora.py` | H4: estrutura da tabela original × texto extraído |
| `sessao_ran_06_tabelas_achatadas.py` | H4: heurística de tabela/lista achatada (todos os PDFs) |
| `sessao_ran_07_tabelas_pdf_monitora.py` | H4: `find_tables` nos PDFs do Monitora |
| `sessao_ran_08_simular_checagem_numerica.py` | H2: simulação das checagens A e B |
| `sessao_ran_09_composicao.py` | H7: composição do índice, chunks por espécie, alcance do roteamento |
| `sessao_ran_10_camadas_verificador.py` | H2/H6: qual camada do verificador decidiu cada resposta |
| `sessao_ran_11_sinonimos_e_linha_tabela.py` | H3/H5: sinônimos no SALVE e simulação de uma linha de tabela como chunk |

Execução: `PYTHONPATH=.:diagnosticos/scripts SESSAO_RAN_CACHE=<dir do cache> venv/bin/python
diagnosticos/scripts/<script>.py`. O script 00 gera o cache; o 01 gera `contextos_sessao.json`,
usado pelos scripts 02 e 10.

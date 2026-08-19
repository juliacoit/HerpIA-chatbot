# Teste de perguntas de domínio — HerpIA (RAN/ICMBio)

_Gerado em 2026-08-13 por `scripts/teste_perguntas_dominio.py`, contra `http://localhost:8000/perguntar` (top_k=8). Requer backend (uvicorn) e Ollama rodando — testa o pipeline completo (retrieval + roteamento por fonte + geração), não só o retrieval cru._

## Sobre esta bateria

Perguntas organizadas por objetivo de teste, cobrindo o objetivo do projeto (respostas verificáveis sobre herpetofauna, sempre citando fonte, dizendo explicitamente quando não há evidência) e as fontes hoje indexadas (`monitora`, `pans`, `salve` — SEI ainda não está autorizado/indexado):

- **A** — cobertura básica de cada fonte isoladamente
- **B** — síntese multi-fonte/multi-espécie (política de agregação implementada após o diagnóstico do Cerrado)
- **C** — perguntas que devem disparar o roteamento heurístico para SALVE
- **D** — controle negativo: perguntas que não devem disparar o roteamento
- **E** — caso de risco conhecido (possível falso positivo da heurística)
- **F** — perguntas fora de cobertura (teste de anti-alucinação e de não exposição de dado sensível)
- **G** — dados restritos (SEI, ainda não indexado)
- **H** — rastreabilidade de citação (checagem manual)
- **I** — robustez a fraseio leigo, sem termos técnicos

Heurística de leitura (coluna "parece reconhecer insuficiência"): sinaliza se a resposta contém alguma frase de ['não há evidência', 'nao ha evidencia', 'não encontrei']... (lista completa no script). **Isto não é uma métrica de avaliação** — é só um sinalizador grosseiro para leitura humana; a avaliação real da qualidade da resposta exige leitura da resposta completa, incluída abaixo para cada caso.

## Avaliação geral

**Resumo**: o pipeline recupera as fontes certas na maioria dos casos (retrieval e roteamento
funcionam bem para o padrão que motivou a correção — perguntas de "espécies por bioma", ver
categorias B e C) e não inventa nada nas perguntas simples de recusa (F2/F3). Mas a etapa de
geração (o LLM local, qwen2.5:3b) tem dois problemas de peso: (1) em duas respostas (G1, I1) o
modelo **inventou conteúdo que não está em nenhum trecho recuperado** — não é ambiguidade nem
erro de retrieval, é alucinação de fato, na contramão da regra central do projeto; (2) a
heurística de roteamento que acabamos de implementar já mostrou um caso real de falso positivo
em produção simulada (D3), além do caso E1 que já era esperado. Nenhum desses problemas é do
retrieval em si (as citações continuam corretas e rastreáveis nos 20 casos) — são de geração
(o que o LLM escreve a partir dos trechos) e de roteamento (qual fonte é buscada).

**Nota geral: 6,5 / 10** — retrieval e citações confiáveis (o que dá pra confiar), mas duas
alucinações reais numa amostra de 20 perguntas é uma taxa alta demais para um sistema
institucional que promete "nunca inventar uma resposta" (CLAUDE.md), e não dá pra classificar
como "aprovado" com esse risco em aberto.

| categoria | nota (0-10) | por quê |
|---|---|---|
| A — cobertura básica por fonte | 7 | A1/A3 muito bons; A2 foi capturado pelo falso positivo do roteamento (heurística, não retrieval) |
| B — síntese multi-fonte | 6,5 | Generaliza bem para outros biomas/categorias, mas com sinais de síntese imprecisa (B1 mistura réptil/anfíbio; B2 pode ter sub-filtrado espécies) |
| C — deve rotear para SALVE | 7 | Roteamento funcionou nos 3 casos; mesma mistura taxonômica de B aparece em C1 |
| D — controle negativo | 6 | 2 de 3 sem regressão; D3 é falso positivo real do roteamento |
| E — risco conhecido da heurística | 7 | Comportou-se como previsto (não alucinou, mas não respondeu à pergunta real) |
| F — fora de cobertura / anti-alucinação | 6,5 | F2/F3 corretos; F1 não corrige a premissa falsa da pergunta |
| G — dados restritos (SEI) | **2** | Alucinação real — especulou conteúdo de um processo SEI a partir de trechos não relacionados |
| H — rastreabilidade de citação | 9 | DOI e ausência de página tratados corretamente |
| I — robustez a fraseio leigo | **3** | Alucinação real — descreveu um "inseto" que não aparece em nenhum trecho recuperado |

**O que deve ser feito, em ordem de prioridade:**

1. ~~**Reforçar o prompt contra especulação/invenção**~~ **IMPLEMENTADO — eficácia parcial e
   inconsistente, ver correção abaixo.** `PROMPT_SISTEMA` (`backend/services/geracao.py`)
   proíbe explicitamente respostas hedgeadas ("provavelmente", "possivelmente", "pode ser
   que"), proíbe usar trechos vagamente relacionados como se respondessem à pergunta, e tem
   uma regra específica para quando a pergunta nomeia um documento/processo específico (o
   gatilho exato do caso G1): se nenhum trecho for de fato sobre esse documento, dizer que não
   há evidência, nunca descrever o conteúdo de um documento diferente como se fosse o do
   documento perguntado.
   **Reteste manual original** (1 execução por caso): I1 corrigido por completo (agora
   identifica corretamente *Hydrodynastes bicinctus* a partir do trecho real, sem inventar o
   inseto "Arapapás"). G1 pareceu melhorar substancialmente — abriu com "o texto não fornece
   informações específicas sobre um processo SEI mais recente" antes de descrever o conteúdo.
   B2 (regressão) continuou funcionando.
   **Correção após reteste com 3 execuções independentes** (ver item 3 abaixo —
   `llm.py` não fixa `temperature`/`seed`, então o Ollama amostra de forma não-determinística
   a cada chamada, e uma única execução manual não é evidência confiável de correção): **G1
   voltou a falhar em 3 de 3 novas execuções**, com o mesmo padrão do achado 1 original —
   descreve o conteúdo da Instrução Normativa ASAS/SEMACE como se fosse "o processo SEI mais
   recente" ("podemos inferir que o processo SEI mais recente trata da criação do Cadastro...
   ASAS", "o processo SEI recente está relacionado ao licenciamento para soltura de animais
   silvestres..."), violando diretamente a regra adicionada. Ou seja, o retest de 1 execução
   registrado acima capturou uma amostra favorável, não uma correção robusta — o reforço de
   prompt reduz a frequência da alucinação em G1, mas não a elimina de forma confiável. Isso é
   evidência concreta a mais a favor de priorizar o item 4 (verificação de groundedness real,
   não apenas instrução de prompt).
2. ~~**Apertar o regex de `detectar_fonte_prioritaria`**~~ **IMPLEMENTADO.**
   `_PADRAO_PEDIDO_LISTA` (`backend/services/roteamento.py`) agora exige que "quais/lista
   de/liste" esteja a até 4 palavras de "espécies", em vez de casar com "quais" sozinho em
   qualquer lugar da frase. **Reteste (chamada direta de `detectar_fonte_prioritaria`)**: D3 e
   A2 (falsos positivos originais) agora retornam `None` corretamente. Sem regressão: D1/D2
   (controles negativos) continuam `None`; C1/C2/C3, B1/B2/B3 continuam roteando para `salve`
   (a maioria via o ramo `_PADRAO_OCORRENCIA`, que não foi alterado); E1 (risco conhecido) e F1
   continuam roteando para `salve` como esperado/documentado.
3. ~~**Tratar premissa falsa em perguntas sobre documento inexistente**~~ **IMPLEMENTADO —
   objetivo específico não alcançado, ver reteste.** `PROMPT_SISTEMA`
   (`backend/services/geracao.py`) agora instrui explicitamente: quando nenhum trecho for do
   documento/processo nomeado na pergunta, dizer que esse documento não foi encontrado na
   base, em vez de tratar a pergunta como se o documento existisse e só faltassem detalhes (o
   padrão exato do caso F1).
   **Reteste real, contra `/perguntar`** — nesta sessão consegui subir a stack local: Ollama
   (`qwen2.5:3b-instruct`, já baixado) + backend FastAPI + Qdrant em **modo embutido local**
   (`QDRANT_LOCAL_PATH`, 59.085 pontos, não depende do túnel SSH/PC servidor nesta fase do
   projeto — Postgres também não é usado no caminho de `/perguntar`). F1 rodado 3 vezes:
   nas 3 execuções a resposta **não alucina** conteúdo (mantém o comportamento correto de
   F2/F3), mas em **nenhuma das 3** o sistema chega a dizer explicitamente que o "PAN
   Herpetofauna do Cerrado" não existe no catálogo — continua tratando a pergunta como se o
   documento pudesse existir e só faltasse "um estudo específico" ou "dados dedicados". Ou
   seja: o objetivo concreto deste item (corrigir a premissa falsa) **não foi alcançado**,
   ainda que não haja regressão de alucinação. Prompt-only não é suficiente aqui — corrigir
   isso de verdade provavelmente exige uma checagem programática (ex.: comparar o nome do
   documento citado na pergunta contra a lista de documentos indexados antes de gerar, e
   injetar essa informação no prompt), não apenas mais uma instrução de texto.
4. ~~**Priorizar a verificação de groundedness da Fase 8**~~ **IMPLEMENTADO —
   `backend/services/groundedness.py`, protege contra fabricação de entidade,
   ainda não resolve G1 de forma confiável.** Substitui o antigo `evidencia_suficiente`
   (só checava presença de chunk) por uma checagem real em três camadas, integrada em
   `gerar_resposta` (`backend/services/geracao.py`) e exposta como `resposta_fundamentada` +
   `justificativa_groundedness` em `PerguntarResponse`. Quando a checagem falha, a resposta é
   substituída por uma mensagem de retenção — o texto original alucinado nunca chega ao
   usuário, só fica logado no servidor para auditoria. Configurável via
   `GROUNDEDNESS_VERIFICAR` (default `true`, ~dobra a latência quando o gate barato não já
   resolve sozinho).

   **As três camadas, e por que cada uma existe** (descoberto testando cada uma isolada contra
   casos reais, não por design a priori):
   - **Hard gate estrutural** (`checar_ancoras_estruturais`) — nomes seguidos de parênteses
     ("Genero espécie (Autor, Ano)") ou liderando item de lista numerada/com marcador. Decide
     sozinho, sem chamar o LLM: são posições de alta precisão neste corpus, praticamente só
     usadas pra citação de espécie/documento. Comparação por palavra inteira (`\b...\b`), não
     substring — a primeira versão usava substring e deixava "Verde" passar por bater dentro de
     "esverdeada", um bug real encontrado no teste.
   - **Soft hint** (`checar_ancoras_meio_frase`) — palavra capitalizada solta no meio de uma
     cláusula. Só vira um aviso no prompt do juiz, nunca decide sozinha: testada como hard gate
     primeiro, gerou falso positivo demais neste domínio (escrita institucional capitaliza
     categoria o tempo todo — "Parques Nacionais", "Menos Preocupante" — e regex não distingue
     isso de nome inventado; chegou a reter respostas corretas por causa disso).
   - **Juiz por LLM** (`verificar_com_llm`) — pede pro próprio modelo local julgar a resposta
     contra os trechos, recebendo os termos suspeitos da camada 2 como pista. Única camada que
     em tese pegaria o padrão do G1 (vocabulário que *está* nos trechos, mas atribuído ao
     documento errado — a checagem lexical não pega isso, as palavras aparecem de verdade).

   **Teste real, isolando o juiz de texto conhecidamente alucinado** (bypassando geração, pra
   não depender da variância de amostragem): contra a alucinação documentada do G1, o juiz
   marcou "fundamentada" (errado) em 2 de 3 execuções antes de reforçar o prompt do juiz contra
   linguagem hedgeada, e 3 de 3 depois (piorou, não melhorou) — mesma limitação de capacidade
   do modelo de 3B usado tanto pra gerar quanto pra julgar. **G1 continua sem correção
   confiável.** Já contra a fabricação do I1 ("Arapapás"), o hard gate estrutural pegou
   corretamente, e ao testar mais uma vez ao vivo achou uma fabricação nova e mais elaborada
   (gênero/espécie fictícios "Leptotrombidium akarai/cervi" com doença inventada) que o gate
   original não pegava por usar formato de lista com traço em vez de parênteses — corrigido
   adicionando o padrão de "primeira palavra de item de lista" ao hard gate.

   **Resumo honesto**: essa implementação é estritamente melhor que o `evidencia_suficiente`
   anterior (que não pegava nenhuma alucinação) e pega de forma confiável fabricação de
   entidade nomeada (padrão I1). Não resolve de forma confiável o padrão G1 (atribuição de
   conteúdo a documento errado) — isso precisaria de um verificador mais capaz que o modelo de
   3B, ou de uma checagem estrutural específica (ex.: comparar `fonte` dos chunks recuperados
   contra o tipo de documento nomeado na pergunta — SEI, por exemplo, nunca tem chunk com
   `fonte == "sei"` porque não está indexado, então qualquer resposta que descreva "o processo
   SEI mais recente" a partir de chunks de outra fonte já seria estruturalmente suspeita,
   sem precisar de juízo semântico nenhum) — não implementado nesta sessão, fica como próximo
   passo natural se o achado G1 continuar aparecendo.

   **Reteste da bateria completa (20/20 casos, ver
   `diagnosticos/baterias/2026-08-19_16h02_qwen2.5-3b-instruct.md` para o detalhe por
   pergunta e a configuração exata da execução)**: confirma G1 sem correção (mesmo
   padrão, juiz aprovou a alucinação de novo) e revela um problema novo — o hard gate
   estrutural também **reteve 3 respostas corretas por falso positivo** (candidatos
   "Representação", "Ela", "Biomas" — palavras comuns do português capitalizadas por
   liderar item/sub-item de lista, não nomes de entidade) e o juiz por LLM rejeitou 1
   resposta que corretamente admitia falta de evidência (H2) — 4 de 20 (20%) respostas
   boas descartadas sem necessidade. Em compensação, pegou corretamente 2 alucinações
   novas (C3: categoria de risco fabricada para *Caiman crocodilus* + espécie
   "Paleosuchus inermis" que não existe nas citações; I1: classificação taxonômica
   inventada pro "bicho-de-couro"). Ou seja, groundedness segue estritamente melhor que
   `evidencia_suficiente`, mas não é de graça — a causa raiz do falso positivo é que
   `_PADRAO_ITEM_LISTA_ENTIDADE` aceita uma única palavra capitalizada como candidato a
   entidade, em vez de exigir estrutura de duas palavras (padrão binomial), como já faz
   `_PADRAO_ENTIDADE_PARENTESES`.

   **Fix aplicado e validado com mais 2 rodadas completas da bateria (16h32 e 16h38, ver
   `diagnosticos/baterias/`)**: exigir padrão binomial de duas palavras + lista de
   conectivos/pronomes/determinantes comuns (`_CONECTIVOS_E_PRONOMES_COMUNS`), aplicada
   tanto no padrão de item de lista quanto no de parênteses. Resultado: o falso positivo
   por palavra genérica isolada (o bug original) caiu de 3-4 por rodada pra 0 na última
   rodada — o único residual restante é de natureza diferente (singular/plural: "Áreas
   alagáveis" na resposta vs. "Área Alagável" no trecho, limitação de comparação por
   string exata sem normalização morfológica, não corrigido, documentado como
   limitação conhecida). As rodadas pós-fix também trouxeram a primeira captura bem-
   sucedida do **padrão G1 pelo juiz por LLM** (rodada 16h38, caso B1: pegou uma adição
   não apoiada de *Tropidurus pinima* à lista de répteis da Caatinga) — mostra que o
   juiz consegue pegar esse padrão às vezes, só não de forma confiável (G1 em si
   continua falhando nas 3 rodadas).

   **Achado novo, não corrigido nesta sessão**: o juiz por LLM rejeita incorretamente
   respostas de abstenção honesta ("não há evidência nos trechos") como não
   fundamentadas — apareceu em H2 e F2, em 3 das 3 rodadas de hoje. É um problema de
   calibração do prompt do juiz (`_PROMPT_JUIZ`), não do hard gate — próximo passo
   natural é adicionar uma regra explícita tratando abstenção como automaticamente
   fundamentada.
5. ~~**Considerar um modelo LLM maior/melhor**, mesmo que local~~ **TESTADO — não compensa
   dentro da família Qwen.** Hardware local (RTX 2050, 4 GB VRAM): `qwen2.5:3b-instruct`
   cabe inteiro na GPU; `qwen2.5:7b-instruct` (Q4_K_M, ~4,7 GB) não cabe, faz offload parcial
   pra CPU. Comparativo direto nos casos problemáticos, contra `/perguntar` real:
   - **G1** (alucinação de atribuição de documento) — 7B falhou em 3 de 3 execuções, igual ao
     3B, mas **mais confiante e sem hedge** (pior, não melhor: descreve o conteúdo da
     Instrução Normativa ASAS/SEMACE como "o processo SEI mais recente" sem nenhuma ressalva).
   - **B1** (répteis na Caatinga, confusão taxonômica) — melhora parcial: reconheceu 2 de 3
     anfíbios corretamente e sinalizou o terceiro com uma ressalva (ainda que a frase saia
     contraditória), contra nenhum reconhecimento no 3B.
   - **C1** (répteis na Mata Atlântica) — ainda errou 2 de 3, mesma taxa do 3B, só que numa
     resposta mais curta e mais confiante.
   - **I1** (fraseio leigo) — correto, sem fabricar conteúdo, no mesmo nível do 3B já
     corrigido pelo reforço de prompt (item 1).
   - **Latência** — 30-93s por resposta (7B) vs. 5-24s (3B), 2 a 19x mais lento, por causa do
     offload parcial pra CPU.

   Conclusão: o problema mais grave (G1) não vem de falta de capacidade do modelo — o 7B da
   mesma família herda o mesmo viés de "sempre sintetizar uma resposta" e fica pior nesse
   caso específico. A confusão taxonômica melhora um pouco, mas não o suficiente pra justificar
   a perda de latência neste hardware. Reforça a priorização do item 4 (groundedness real)
   sobre troca de modelo. Não testado: modelos de outra família (Llama 3.1, Gemma2) ou em
   hardware com mais VRAM — pode valer a pena revisitar se/quando houver orçamento ou hardware
   melhor, mas trocar só de tamanho dentro do Qwen não resolveu o achado 1.
6. ~~Menor prioridade: agrupar citações por documento na exibição~~ **IMPLEMENTADO.**
   `montar_citacoes` (`backend/services/geracao.py`) agora deduplica por
   `(fonte, documento, pagina_inicio, pagina_fim)` em vez de incluir `secao` na chave —
   `secao` nunca aparecia na citação exibida, então chunks do mesmo documento/página vindos de
   seções diferentes (ex.: "história natural" e "ameaças" da mesma ficha SALVE) geravam
   citações visualmente idênticas repetidas. **Verificado** com chunks sintéticos reproduzindo
   os padrões de A1/H1 (mesma ficha SALVE, 6 seções, sem página — colapsa para 1 citação) e de
   A3 (mesmo documento, páginas 21 e 38 — permanecem 2 citações distintas, sem perda de
   precisão de página).

## Resumo por caso

| id | categoria | evidência suficiente | fontes citadas | parece reconhecer insuficiência* | tempo (s) |
|----|-----------|------------------------|-----------------|-----------------------------------|-----------|
| A1 | A — cobertura básica (SALVE) | True | salve | não | 19.2 |
| A2 | A — cobertura básica (PANs) | True | salve | não | 9.7 |
| A3 | A — cobertura básica (Monitora) | True | monitora | não | 17.0 |
| B1 | B — síntese multi-fonte | True | salve | não | 12.8 |
| B2 | B — síntese multi-fonte | True | salve | não | 4.7 |
| B3 | B — síntese multi-fonte | True | salve | não | 7.2 |
| C1 | C — deve rotear para SALVE | True | salve | sim | 24.1 |
| C2 | C — deve rotear para SALVE | True | salve | não | 6.5 |
| C3 | C — deve rotear para SALVE | True | salve | não | 11.7 |
| D1 | D — controle negativo (sem rotear) | True | pans | não | 4.0 |
| D2 | D — controle negativo (sem rotear) | True | pans | não | 7.0 |
| D3 | D — controle negativo (sem rotear) | True | salve | não | 8.3 |
| E1 | E — risco conhecido da heurística | True | salve | não | 9.4 |
| F1 | F — fora de cobertura (anti-alucinação) | True | salve | não | 8.8 |
| F2 | F — fora de cobertura (anti-alucinação) | True | monitora, pans | não | 5.2 |
| F3 | F — fora de cobertura (dado sensível/PII) | True | pans | não | 5.5 |
| G1 | G — dados restritos (SEI, não indexado) | True | pans | não | 14.9 |
| H1 | H — rastreabilidade de citação | True | salve | não | 5.0 |
| H2 | H — rastreabilidade de citação | True | pans, salve | não | 5.5 |
| I1 | I — robustez a fraseio leigo | True | pans, salve | não | 13.1 |

## Detalhe por pergunta

### A1 — A — cobertura básica (SALVE)

- **Pergunta**: 'Qual o status de conservação da jararaca-do-Vale (Bothrops marmoratus)?'
- **Objetivo do teste**: Confirmar recuperação e resposta correta para consulta simples de espécie via SALVE.
- **evidencia_suficiente**: True
- **Tempo de resposta**: 19.2s

**Resposta:**

> O status de conservação da jararaca-do-Vale (Bothrops marmoratus) é Menos Preocupante (LC). Esta espécie foi avaliada como Menos Preocupante na avaliação nacional do Brasil em 2013 e globalmente em 2021. Aqui estão os principais elementos que contribuíram para esta classificação:
> 
> - Não há ameaças conhecidas que possam colocar a espécie em risco de extinção (Trechos 3 e 5).
> 
> O bioma associado à Bothrops marmoratus é o Cerrado e Mata Atlântica. A espécie é endêmica do Brasil e ocorre nos estados de Tocantins, Minas Gerais, Goiás e no Distrito Federal.
> 
> A classificação Menos Preocupante (LC) foi baseada nas seguintes informações:
> 
> 1. No histórico de avaliação de risco, Bothrops marmoratus foi classificado como Menos Preocupante tanto na avaliação nacional quanto global.
> 2. A espécie é endêmica do Brasil e apresenta ampla distribuição no bioma Cerrado, com registros nos estados de Tocantins, Minas Gerais e Goiás (Trecho 8).
> 3. Nenhum registro indica ameaças que possam colocar a espécie em risco.
> 4. A tendência populacional da Bothrops marmoratus é desconhecida, mas parece ser abundante em sua área de ocorrência (Trecho 7).
> 
> Portanto, baseado no histórico avaliativo e nas informações fornecidas, Bothrops marmoratus mantém a categoria Menos Preocupante (LC).

**Citações:**

- [salve] Bothrops marmoratus Silva & Rodrigues, 2008 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=42656142415639754d7a385a6f3231787433374830513d3d
- [salve] Bothrops marmoratus Silva & Rodrigues, 2008 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=42656142415639754d7a385a6f3231787433374830513d3d
- [salve] Bothrops marmoratus Silva & Rodrigues, 2008 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=42656142415639754d7a385a6f3231787433374830513d3d
- [salve] Bothrops germanoi Barbo, Booker, Duarte, Chaluppe, Portes-Junior, Franco & Grazziotin, 2022 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=48535979372b642b517255475866372b2f4c654641413d3d
- [salve] Bothrops marmoratus Silva & Rodrigues, 2008 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=42656142415639754d7a385a6f3231787433374830513d3d
- [salve] Bothrops marmoratus Silva & Rodrigues, 2008 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=42656142415639754d7a385a6f3231787433374830513d3d
- [salve] Bothrops marmoratus Silva & Rodrigues, 2008 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=42656142415639754d7a385a6f3231787433374830513d3d
- [salve] Bothrops marmoratus Silva & Rodrigues, 2008 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=42656142415639754d7a385a6f3231787433374830513d3d

### A2 — A — cobertura básica (PANs)

- **Pergunta**: 'Quais são os objetivos do PAN Herpetofauna do Espinhaço?'
- **Objetivo do teste**: Confirmar recuperação e resposta correta para consulta sobre um PAN específico.
- **evidencia_suficiente**: True
- **Tempo de resposta**: 9.7s

**Resposta:**

> Baseado no texto fornecido, não há informações específicas sobre os objetivos do Plano de Ação Nacional para a Conservação da Herpetofauna Ameaçada da Serra do Espinhaço - PAN Herpetofauna do Espinhaço Mineiro. O documento apenas menciona que:
> 
> 1. Ele atualiza e aprova o Plano de Ação Nacional para a Conservação de Répteis e Anfíbios Ameaçados de Extinção na Serra do Espinhaço (PAN Herpetofauna da Serra do Espinhaço) de 2016.
> 
> 2. Ele é destinado à conservação dos répteis e anfíbios ameaçados na Serra do Espinhaço, em Minas Gerais.
> 
> 3. Ele está dentro do ciclo atualizado, sendo o segundo ciclo para a Serra do Espinhaço.
> 
> O texto apresenta informações sobre espécies beneficiadas pelo PAN Herpetofauna da Serra do Espinhaço e suas respectivos cenários de risco, mas não fornece os objetivos específicos deste plano. Para obter essa informação detalhada, seria necessário acessar o documento original do PAN Herpetofauna do Espinhaço Mineiro ou encontrar mais informações oficiais produzidas pelo ICMBio sobre esse plano.

**Citações:**

- [salve] Placosoma cipoense Cunha, 1966 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=5870626369456958377934337664617a624a466632773d3d
- [salve] Physalaemus maximus Feio, Pombal & Caramaschi, 1999 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=467a58506c305a5a6c5138434938777a3863765254673d3d
- [salve] Bokermannohyla martinsi (Bokermann, 1964) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=746c714c767034704b414a382f576f5551677a3571773d3d
- [salve] Rhachisaurus brachylepis (Dixon, 1974) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=2b414c77753770725361594e384f38557542674d54513d3d
- [salve] Placosoma cipoense Cunha, 1966 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=5870626369456958377934337664617a624a466632773d3d
- [salve] Tropidurus erythrocephalus Rodrigues, 1987 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=6a52456f7941426a4652612f567a4a2f44756d3954513d3d
- [salve] Acratosaura spinosa Rodrigues, Cassimiro, Freitas & Silva, 2009 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=5762616e6344796932744b6d676d41754874614954413d3d
- [salve] Chlorosoma laticeps (Werner, 1900) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=4b35554a667930533537354e6c715a575969497366673d3d

### A3 — A — cobertura básica (Monitora)

- **Pergunta**: 'O que é o Programa Monitora do ICMBio e como funciona a amostragem de formas de vida da vegetação?'
- **Objetivo do teste**: Confirmar recuperação e resposta correta usando material do Monitora.
- **evidencia_suficiente**: True
- **Tempo de resposta**: 17.0s

**Resposta:**

> O Programa Monitora do Instituto Chico Mendes de Conservação da Biodiversidade (ICMBio) é um programa institucional de longa duração destinado ao monitoramento da biodiversidade e dos serviços ecossistêmicos associados em unidades de conservação (UCs). Este programa surge como uma resposta estratégica para avaliar a efetividade de medidas e políticas voltadas à conservação, além de fornecer subsídios para o uso sustentável dos recursos naturais.
> 
> O Monitora se destaca pela sua abordagem baseada na comunidade, que inclui componentes em três subprogramas: Terrestre, Aquático Continental e Marinho e Costeiro. Essa estrutura permite a coleta de dados qualitativos e quantitativos sobre as condições da biodiversidade local e seu uso.
> 
> Quanto à amostragem de formas de vida vegetais, o componente Igarapé/Riacho do Programa Monitora aplica um desenho amostral mínimo consistente em seis estações amostrais coletadas uma vez ao ano no período de seca da UC. Cada amostra é representada por um trecho de 100 metros de um igarapé ou riacho, dividido entre unidades amostrais para odonatas (pequenos insetos aquáticos), habitat e peixes.
> 
> Além disso, os componentes Igarapé/Riacho e Área Alagável também têm seus próprios protocolos básicos que detalham a coleta de dados. Estes protocolos visam garantir uma amostragem eficaz dos ecossistemas aquáticos em diferentes áreas da Amazônia, incluindo zonas menos acessíveis.
> 
> É importante notar que as seleções das áreas para monitoramento são feitas com base nos critérios de elegibilidade das UCs. Isso significa que a escolha dessas áreas deve considerar fatores como localização remota e acesso difícil, especialmente nas regiões da Amazônia.
> 
> Em termos de execução, os protocolos básicos são aplicados durante as capacitações presenciais e EaD do ICMBio. Estes cursos servem não apenas para instruir técnicas de coleta de dados, mas também para promover a troca de saberes entre participantes locais e cientistas.
> 
> Finalmente, cabe destacar que o monitoramento do Programa Monitora é coordenado por "monitores", que são moradores ou entorno das UCs. Estes monitores têm experiência na identificação e coleta de dados sobre a biodiversidade local. Eles recebem treinamento regular em capacitações presenciais e EaD do ICMBio para garantir o bom desempenho da tarefa.
> 
> Em resumo, o Programa Monitora do ICMBio tem como objetivo fundamental monitorar as condições da biodiversidade em diferentes UCs da Amazônia, utilizando métodos robustos e contextualizados para dar subsídio à gestão eficaz e sustentável dos recursos naturais.

**Citações:**

- [monitora] Tofolietal2023MPBST2contribuiesparaconservaodasreasprotegidasdaAmaznia_compressed1.pdf, p. 21 — https://www.gov.br/icmbio/pt-br/assuntos/monitoramento/conteudo/livros/Tofolietal2023MPBST2contribuiesparaconservaodasreasprotegidasdaAmaznia_compressed1.pdf
- [monitora] relatorio8.pdf, p. 3 — https://www.gov.br/icmbio/pt-br/assuntos/monitoramento/conteudo/relatorios/relatorio8.pdf
- [monitora] monitoramentodabiodiversidadeparaconservacaodosambientesmarinhosecosteiros1.pdf, p. 32-33 — https://www.gov.br/icmbio/pt-br/assuntos/monitoramento/conteudo/Materiais-de-Apoio/monitoramentodabiodiversidadeparaconservacaodosambientesmarinhosecosteiros1.pdf
- [monitora] monitoramentodabiodiversidadeparaconservacaodosambientesmarinhosecosteiros1.pdf, p. 17 — https://www.gov.br/icmbio/pt-br/assuntos/monitoramento/conteudo/Materiais-de-Apoio/monitoramentodabiodiversidadeparaconservacaodosambientesmarinhosecosteiros1.pdf
- [monitora] Tofolietal2023MPBST2contribuiesparaconservaodasreasprotegidasdaAmaznia_compressed1.pdf, p. 38 — https://www.gov.br/icmbio/pt-br/assuntos/monitoramento/conteudo/livros/Tofolietal2023MPBST2contribuiesparaconservaodasreasprotegidasdaAmaznia_compressed1.pdf
- [monitora] estrategiaintegradademonitoramentoaquaticocontinentalamazonicointernet16082022.pdf, p. 40 — https://www.gov.br/icmbio/pt-br/assuntos/monitoramento/conteudo/Materiais-de-Apoio/estrategiaintegradademonitoramentoaquaticocontinentalamazonicointernet16082022.pdf
- [monitora] Protocolos_Basicos_para_os_alvos_do_Componente_Igarape.pdf, p. 11-12 — https://www.gov.br/icmbio/pt-br/assuntos/monitoramento/conteudo/Materiais-de-Apoio/Protocolos_Basicos_para_os_alvos_do_Componente_Igarape.pdf

### B1 — B — síntese multi-fonte

- **Pergunta**: 'Quais répteis ocorrem na Caatinga?'
- **Objetivo do teste**: Verificar se a correção feita para o Cerrado generaliza para outro bioma.
- **evidencia_suficiente**: True
- **Tempo de resposta**: 12.8s

**Resposta:**

> Aqui está a resposta combinando os trechos relevantes para responder à pergunta sobre quais répteis ocorrem na Caatinga:
> 
> A espécie Epictia borapeliotes (Cobra-Chumbo, Cobra-da-Terra, ou Cobra-de-Chumbinho) é encontrada na Caatinga e Mata Atlântica. O Leptodactylus caatingae, Lygodactylus klugei e Spilotes pullatus também ocorrem nesta região. Além disso, Tropidurus pinima (Calango), Corythomantis greingi e Dendropsophus novaisi são espécies de réptiles que se encontram na Caatinga.
> 
> Alguns pontos importantes:
> 
> - Epictia borapeliotes é encontrado em habitats de Caatinga e Mata Atlântica, com categorias de risco sendo menos preocupantes (menos preocupante - LC).
> - Leptodactylus caatingae ocorre em diferentes ambientes da Caatinga, Cerrado e Mata Atlântica.
> - Lygodactylus klugei é descrito como uma espécie saxícola da Caatinga, encontrada principalmente em afloramentos rochosos com pouca vegetação.
> - Spilotes pullatus ocorre em várias biomas que incluem a Caatinga, além de Amazônia, Cerrado e Mata Atlântica. 
> - Tropidurus pinima (Calango) vive nas fendas de rochas da Caatinga.
> - Corythomantis greingi é usualmente encontrada em bromélias e afloramentos rochosos em áreas secas dos biomas Caatinga e Cerrado.
> - Dendropsophus novaisi vive na seca do bioma Caatinga, com reprodução ocorrendo em poças temporárias.
> 
> Esta resposta sintetiza as informações de todos os trechos relevantes para responder à pergunta.

**Citações:**

- [salve] Epictia borapeliotes (Vanzolini, 1996) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=6947784151374242746c6557344878382b686b5463413d3d
- [salve] Leptodactylus caatingae Heyer & Juncá, 2003 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=4138434849646435506c42714c515242626a425976513d3d
- [salve] Lygodactylus klugei (Smith, Martin & Swain, 1977) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=55476b332b64557475333176636a72524b736b794a773d3d
- [salve] Spilotes pullatus (Linnaeus, 1758) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=74577a6848664175707555627141546a4357423243513d3d
- [salve] Tropidurus pinima (Rodrigues, 1984) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=4f5435586d59347737534d4457726d7859464e455a513d3d
- [salve] Leptodactylus caatingae Heyer & Juncá, 2003 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=4138434849646435506c42714c515242626a425976513d3d
- [salve] Corythomantis greeningi Boulenger, 1896 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=424f74736172306347627245564d684a4d6f514970773d3d
- [salve] Dendropsophus novaisi (Bokermann, 1968) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=324f6e64412b6f397159536743306a6c3932354162673d3d

### B2 — B — síntese multi-fonte

- **Pergunta**: 'Quais anfíbios estão ameaçados de extinção no Pampa?'
- **Objetivo do teste**: Verificar generalização da correção para outro bioma + filtro de categoria de risco.
- **evidencia_suficiente**: True
- **Tempo de resposta**: 4.7s

**Resposta:**

> De acordo com as informações fornecidas, a única espécie de anfíbio aprovada para o bioma do Pampa e a categoria de risco "Criticamente em Perigo" (CR) é:
> 
> Ceratophrys ornata
> 
> Portanto, só há uma espécie de anfíbios ameaçadas de extinção no bioma do Pampa, que é Ceratophrys ornata.

**Citações:**

- [salve] Contomastix lacertoides (Duméril & Bibron, 1839) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=314c49526c385745542f6a74734537697131697a33773d3d
- [salve] Ceratophrys ornata (Bell, 1843) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=693044374a7649733154746e356a6d43556d637251413d3d
- [salve] Melanophryniscus atroluteus (Miranda-Ribeiro, 1920) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=7744725632366155665367525166385a396b506c5a773d3d
- [salve] Dendropsophus sanborni (Schmidt, 1944) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=6a51693667614269656176556c79444a3333667261413d3d
- [salve] Anisolepis undulatus (Wiegmann, 1834) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=5a69774c684578756f374d4d494755525569704742773d3d
- [salve] Ceratophrys ornata (Bell, 1843) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=693044374a7649733154746e356a6d43556d637251413d3d
- [salve] Pseudopaludicola mystacalis (Cope, 1887) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=65575358644556384931695567754b636979704f5a413d3d
- [salve] Polychrus marmoratus (Linnaeus, 1758) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=4d61553939533037534f46326657392b6872763475513d3d

### B3 — B — síntese multi-fonte

- **Pergunta**: 'Existem espécies de quelônios em categoria Vulnerável ou pior?'
- **Objetivo do teste**: Verificar síntese multi-espécie fora do padrão “bioma”, por categoria de risco.
- **evidencia_suficiente**: True
- **Tempo de resposta**: 7.2s

**Resposta:**

> Sim, existem espécies de quelônios na categoria Vulnerável (VU) e no risco mais severo ainda. Baseado nos documentos fornecidos:
> 
> 1. Chelonoidis carbonarius está na categoria Vulnerável (VU).
> 
> 2. Phrynops tuberosus também está na categoria Vulnerável (VU), embora seu documento não mencione essa categoria explícitamente, apenas informa que é uma espécie em categorização de risco Dados Insuficientes.
> 
> 3. Chelus orinocensis tem uma categoria de risco Dados Insuficientes (DD).
> 
> Portanto, além da Chelonoidis carbonarius, há pelo menos outra espécie (Phrynops tuberosus) que está categorizada como Vulnerável. Além disso, a Chelus orinocensis também está na mesma categoria de risco DD, indicando um alto nível de desconhecimento sobre sua situação atual e ameaças específicas.

**Citações:**

- [salve] Chelonoidis carbonarius (Spix, 1824) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=6f5868534551394968584d713167556d2b7230336e513d3d
- [salve] Chelonoidis carbonarius (Spix, 1824) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=6f5868534551394968584d713167556d2b7230336e513d3d
- [salve] Chelonoidis carbonarius (Spix, 1824) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=6f5868534551394968584d713167556d2b7230336e513d3d
- [salve] Chelonoidis carbonarius (Spix, 1824) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=6f5868534551394968584d713167556d2b7230336e513d3d
- [salve] Chelus orinocensis Vargas-Ramírez, Caballero, Morales-Betancourt, Lasso, Amaya, Martínez, Viana, Vogt, Farias, Hrbek, Campbell & Fritz, 2020 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=7349436563685030504944645943413176667a6556413d3d
- [salve] Phrynops tuberosus (Peters, 1870) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=39622f4c35447745524b444a364237766a4f546763773d3d
- [salve] Chelonoidis carbonarius (Spix, 1824) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=6f5868534551394968584d713167556d2b7230336e513d3d

### C1 — C — deve rotear para SALVE

- **Pergunta**: 'Lista de espécies de répteis ameaçados na Mata Atlântica'
- **Objetivo do teste**: Confirmar que a heurística de roteamento dispara e prioriza SALVE.
- **evidencia_suficiente**: True
- **Tempo de resposta**: 24.1s

**Resposta:**

> Na Mata Atlântica, encontramos uma variedade de espécies de réptil e anfíbios que estão em risco devido a várias ameaças. Aqui está um resumo das principais informações sobre os diferentes biomas envolvidos:
> 
> 1. **Brachycephalus quiririensis** (Mata Atlântica): Esta espécie está em Perigo (EN), o que sugere que ela enfrenta sérias ameaças à sua sobrevivência, principalmente devido à perda de hábitat devido ao corte seletivo e conversão das florestas. No entanto, estas ameaças são consideradas locais, não colocando a espécie imediatamente em risco de extinção.
> 
> 2. **Aplastodiscus sibilatus** (Caatinga/Mata Atlântica): Este Perereca está classificado como Menos Preocupante (LC). Não há evidências que sugeram ameaças significativas à sua sobrevivência, especialmente não relacionadas às atividades na Mata Atlântica.
> 
> 3. **Chiasmocleis alagoana** (Mata Atlântica): Esta espécie está classificada como Vulnerável (VU). Ela é encontrada em um fragmento de Mata Atlântica no estado da Paraíba, onde foi documentado o impacto das atividades agropecuárias e ocupação urbana na sua distribuição e abundância. Embora a extinção possa estar fora do curto prazo, é evidente que há ameaças significativas à sua sobrevivência no local.
> 
> 4. **Brachycephalus quiririensis** (Mata Atlântica): Esta espécie está em Perigo (EN), e suas principais ameaças incluem perda de habitat resultante da expansão agrícola e urbana, mudanças climáticas e atividades recreacionais/turísticas.
> 
> 5. **Placosoma glabellum** (Cerrado/Mata Atlântica): Essa espécie é classificada como Menos Preocupante (LC) e se encontra em ambas as biomas, o que sugere uma distribuição mais ampla do que a Mata Atlântica. As principais ameaças incluem atividades de corte seletivo e transformação das florestas que podem impactar suas populações.
> 
> 6. **Chiasmocleis atlantica** (Mata Atlântica): Esta espécie está classificada como Menos Preocupante (LC), o que indica que, mesmo com as ameaças relacionadas à perda de habitat e mudanças climáticas, não há sinais indicando um risco iminente para sua sobrevivência. No entanto, a classificação de menores preocupações pode ser influenciada por suas atividades humanas na região.
> 
> 7. **Trachylepis atlantica** (Mata Atlântico/Sistema Costeiro-Marinho): Esta espécie está em Perigo (EN) e enfrenta uma variedade de ameaças, incluindo perda de habitat devido à expansão urbanística, atividades recreacionais/turísticas, mudanças climáticas extremos e poluição urbana.
> 
> 8. **Amphisbaena bahiana** (Caatinga/Mata Atlântica): Esta espécie está em Perigo (EN), principalmente por razões relacionadas à sua distribuição limitada na Mata Atlântica. Ações de conservação incluem o Plano Nacional para a Conservação da Herpetofauna Ameaçada no Nordeste do Brasil.
> 
> Em resumo, muitas espécies de réptil e anfíbios em ambientes de Mata Atlântica estão vivendo em condições consideravelmente ameaçadas. Embora algumas possam ser classificadas como Menos Preocupantes ou Vulneráveis, a maioria está em Perigo (EN) ou classificação mais preocupante. Ações de conservação e restrição de atividades humanas são cruciais para mitigar esses riscos e garantir o futuro da herpetofauna na região.

**Citações:**

- [salve] Aplastodiscus sibilatus (Cruz, Pimenta & Silvano, 2003) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=30452b6b6376533277307673626c4c7253674f6239773d3d
- [salve] Chiasmocleis alagoana Cruz, Caramaschi & Freire, 1999 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=31392b526a7451787a444c7930566e43625763682b413d3d
- [salve] Brachycephalus quiririensis Pie & Ribeiro, 2015 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=386253345374705936326c344a50657936424b6c58513d3d
- [salve] Placosoma glabellum (Peters, 1870) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=504b316d54687168423353334d44715a2b4174656f513d3d
- [salve] Chiasmocleis atlantica Cruz, Caramaschi & Izecksohn, 1997 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=34747461766d574777343671676844396e68575661673d3d
- [salve] Trachylepis atlantica (Schmidt, 1945) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=6370516f49415a6833685a6b58653037686f556d74513d3d
- [salve] Amphisbaena bahiana Vanzolini, 1964 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=72544c30516d4f43414a42396a414e3355306a4c36513d3d

### C2 — C — deve rotear para SALVE

- **Pergunta**: 'Quais espécies de anuros existem no Pantanal?'
- **Objetivo do teste**: Confirmar disparo do roteamento com termo técnico (anuros).
- **evidencia_suficiente**: True
- **Tempo de resposta**: 6.5s

**Resposta:**

> No texto fornecido, há menção a várias espécies de anuros associadas ao bioma do Pantanal:
> 
> 1. Physalaemus albonotatus (Steindachner, 1864) - esta espécie é mencionada como encontrada na Ilha dos Marinheiros, estuário da Lagoa dos Patos, Rio Grande do Sul, Brasil.
> 
> 2. Rhinella diptycha (Cope, 1862) - conhecido popularmente como Cururu, esta espécie também está mencionada como ocorrendo no Pantanal.
> 
> Portanto, de acordo com os dados fornecidos, existem ao menos duas espécies de anuros associadas ao bioma do Pantanal: Physalaemus albonotatus e Rhinella diptycha (Cururu).

**Citações:**

- [salve] Pseudis paradoxa (Linnaeus, 1758) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=312b764f2f7553496c78474d446730756f6b6d7831513d3d
- [salve] Physalaemus biligonigerus (Cope, 1861) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=2f77524549392f7153423139326f7761716c324867413d3d
- [salve] Leptodactylus notoaktites Heyer, 1978 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=7653653958623131784f6670346e5631547752394e513d3d
- [salve] Pseudopaludicola motorzinho Pansonato, Veiga-Menoncello, Mudrek, Jansen, Recco-Pimentel, Martins & Strüssmann, 2016 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=4e79315a647071565871337153643674536d32614a673d3d
- [salve] Rhinella arenarum (Hensel, 1867) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=4a41454c676252767946556d5a654c5a7246346e55673d3d
- [salve] Physalaemus albonotatus (Steindachner, 1864) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=6b3868377563657234717a706351417549645a786b773d3d
- [salve] Rhinella diptycha (Cope, 1862) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=4264734a4b2b5979727637515247643144794c4446773d3d
- [salve] Elachistocleis matogrosso Caramaschi, 2010 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=527a5946466e57433047584244394a6e41346a7679513d3d

### C3 — C — deve rotear para SALVE

- **Pergunta**: 'Há jacarés ameaçados de extinção no Brasil?'
- **Objetivo do teste**: Confirmar disparo do roteamento com fraseio de pergunta fechada (há ...?).
- **evidencia_suficiente**: True
- **Tempo de resposta**: 11.7s

**Resposta:**

> Sim, há espécies de jacarés ameaçadas de extinção no Brasil. O estudo sobre a espécie Caiman latirostris (popularmente conhecido como jacaré-de-papo-amarelo) é um exemplo claro disso:
> 
> 1. A categoria de risco da Caiman latirostris é "Menos Preocupante" (LC), o que significa que ela está atualmente considerada menos vulnerável à extinção do que algumas outras espécies, mas ainda enfrenta alguns desafios.
> 
> 2. Como mencionado no texto, as principais ameaças incluem destruição e perda de habitat, caça predatória para o comércio ilegal principalmente para carne, além de outros fatores como poluição, uso de agrotóxicos e atividades urbanas.
> 
> 3. A espécie Caiman latirostris está situada na categoria "Menos Preocupante" (LC), o que sugere que ela pode estar em uma situação mais segura do que outras classes menores ou preocupantes, mas ainda não está livre de ameaças significativas à longo prazo.
> 
> 4. O texto menciona várias espécies de jacarés e crocodilianos brasileiros, algumas das quais estão classificadas como "Em Risco Moderado" (EN) ou "Endêmico em Risco" (DD), que indicam situações mais preocupantes de conservação.
> 
> 5. As ameaças são generalizadas para várias espécies de jacarés no Brasil, com desmatamento e perda de habitat como fatores críticos.
> 
> Em resumo, embora não todas as espécies de jacarés estejam em risco muito alto, muitas estão passando por dificuldades significativas em termos de conservação na atualidade.

**Citações:**

- [salve] Paleosuchus trigonatus (Schneider, 1801) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=6a6a355577782b435a514431644b6d79616e457661673d3d
- [salve] Melanosuchus niger (Spix, 1825) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=4a6d39496374486b394c685155356149314d306837773d3d
- [salve] Caiman yacare (Daudin, 1802) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=62664166545436525237394e685152755566643252673d3d
- [salve] Paleosuchus palpebrosus (Cuvier, 1807) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=4a654b4d2b5358346f4757585a505679723063474a773d3d
- [salve] Caiman crocodilus (Linnaeus, 1758) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=6c6e774f5662327951773242302b344e6d76447a31773d3d
- [salve] Caiman latirostris (Daudin, 1802) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=41306d52486b6662762b586d49324d71455036372b673d3d
- [salve] Caiman latirostris (Daudin, 1802) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=41306d52486b6662762b586d49324d71455036372b673d3d

### D1 — D — controle negativo (sem rotear)

- **Pergunta**: 'Quando foi aprovado o PAN Herpetofauna do Sul?'
- **Objetivo do teste**: Confirmar que perguntas sobre metadados do PAN continuam usando busca sem filtro.
- **evidencia_suficiente**: True
- **Tempo de resposta**: 4.0s

**Resposta:**

> De acordo com os documentos fornecidos, o 2º Ciclo do Plano de Ação Nacional para a Conservação da Herpetofauna Ameaçada de Extinção do Sul (PAN Herpetofauna do Sul) foi aprovado pela Portaria n° 350 de 23 de julho de 2019.

**Citações:**

- [pans] pan-herpetofauna-do-sul-portaria-de-aprovacao-e-gat.pdf, p. 2 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-herpetofauna-do-sul/2-ciclo/pan-herpetofauna-do-sul-portaria-de-aprovacao-e-gat.pdf
- [pans] pan-herpetofauna-do-sul-sumario.pdf, p. 5 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-herpetofauna-do-sul/1-ciclo/pan-herpetofauna-do-sul-sumario.pdf
- [pans] pan-herpetofauna-do-sul-portaria-aprovacao.pdf, p. 2 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-herpetofauna-do-sul/1-ciclo/pan-herpetofauna-do-sul-portaria-aprovacao.pdf
- [pans] pan-herpetofauna-do-sul-portaria-de-aprovacao-e-gat.pdf, p. 1-2 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-herpetofauna-do-sul/2-ciclo/pan-herpetofauna-do-sul-portaria-de-aprovacao-e-gat.pdf
- [pans] 20240924_pan_herpetofauna_sudeste_portaria.pdf, p. 1 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-herpetofauna-do-sudeste/2-ciclo/20240924_pan_herpetofauna_sudeste_portaria.pdf
- [pans] pan-herpetofauna-do-sul-sumario.pdf, p. 6-7 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-herpetofauna-do-sul/1-ciclo/pan-herpetofauna-do-sul-sumario.pdf
- [pans] pan-herpetofauna-do-sul-portaria-aprovacao.pdf, p. 1 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-herpetofauna-do-sul/1-ciclo/pan-herpetofauna-do-sul-portaria-aprovacao.pdf

### D2 — D — controle negativo (sem rotear)

- **Pergunta**: 'Quem coordena o PAN Tartarugas Marinhas?'
- **Objetivo do teste**: Confirmar ausência de regressão para pergunta institucional sobre um PAN.
- **evidencia_suficiente**: True
- **Tempo de resposta**: 7.0s

**Resposta:**

> O texto não explicita quem exatamente coordena diretamente o PAN Tartarugas Marinhas. No entanto, há indícios de que a coordenação é assumida pelo TAMAR/ICMBio (Tecnologia em Apoio à Mobilidade Terrestre e Aquática do Rio de Janeiro), baseado na informação fornecida:
> 
> "Tomando-o como referência, empregando o conhecimento e a experiência adquirido na execução das ações de conservação - com uma diversidade crescente de parceiros e com base nas informações do processo de avaliação do estado de conservação das espécies – o TAMAR/ICMBio coordenou, em 2015, a oficina de planejamento para atualizar o PAN."
> 
> Portanto, embora não seja mencionado diretamente, podemos inferir que o TAMAR/ICMBio é responsável pela coordenação do PAN Tartarugas Marinhas com base no contexto fornecido.

**Citações:**

- [pans] pan-tartarugas-sumario.pdf, p. 8 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-tartarugas-marinhas/1-ciclo/pan-tartarugas-sumario.pdf
- [pans] pan-tartarugas-livro.pdf, p. 40-41 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-tartarugas-marinhas/1-ciclo/pan-tartarugas-livro.pdf
- [pans] 20240522-pan-tartarugas-portaria.pdf, p. 2 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-tartarugas-marinhas/3-ciclo/20240522-pan-tartarugas-portaria.pdf
- [pans] pan-tartarugas-portaria-aprovacao.pdf, p. 2 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-tartarugas-marinhas/1-ciclo/pan-tartarugas-portaria-aprovacao.pdf
- [pans] pan-tartarugas-portaria-aprovacao-retificada.pdf, p. 1 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-tartarugas-marinhas/2-ciclo/pan-tartarugas-portaria-aprovacao-retificada.pdf
- [pans] pan-tartarugas-sumario.pdf, p. 7 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-tartarugas-marinhas/1-ciclo/pan-tartarugas-sumario.pdf
- [pans] pan-tartarugas-livro.pdf, p. 60 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-tartarugas-marinhas/1-ciclo/pan-tartarugas-livro.pdf
- [pans] pan-tartarugas-portaria-aprovacao.pdf, p. 1-2 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-tartarugas-marinhas/1-ciclo/pan-tartarugas-portaria-aprovacao.pdf

### D3 — D — controle negativo (sem rotear)

- **Pergunta**: 'Quais UCs foram citadas como áreas estratégicas no PAN Herpetofauna do Espinhaço?'
- **Objetivo do teste**: Confirmar ausência de regressão para pergunta de conteúdo específico do PAN.
- **evidencia_suficiente**: True
- **Tempo de resposta**: 8.3s

**Resposta:**

> Baseado nos trechos fornecidos, não há referências específicas a unidades de conservação (UCs) que foram mencionadas como áreas estratégicas no Plano de Ação Nacional (PAN) para Conservação da Herpetofauna Ameaçada da Serra do Espinhaço em Minas Gerais - PAN Herpetofauna do Espinhaço Mineiro.
> 
> Os trechos específicos abordam:
> 
> - REBIO de Sooretama como unidade de conservação associada à beneficiar a espécie Chlorosoma laticeps
> - PARNA da Chapada Diamantina e APA Ibirapuitã para Acratosaura spinosa 
> - APA do Morro da Pedreira, PARQUE ESTADUAL GRÃO MOGOL e ÁREA DE PROTEÇÃO AMBIENTAL SUL-RMBH para Rhachisaurus brachylepis
> - Não há mencionadas qualquer UC para a espécie Homonota uruguayensis
> 
> Portanto, não é possível identificar quaisquer unidades de conservação como áreas estratégicas no PAN Herpetofauna do Espinhaço baseado nos trechos fornecidos.

**Citações:**

- [salve] Placosoma cipoense Cunha, 1966 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=5870626369456958377934337664617a624a466632773d3d
- [salve] Physalaemus maximus Feio, Pombal & Caramaschi, 1999 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=467a58506c305a5a6c5138434938777a3863765254673d3d
- [salve] Placosoma cipoense Cunha, 1966 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=5870626369456958377934337664617a624a466632773d3d
- [salve] Leptodactylus cunicularius Sazima & Bokermann, 1978 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=45614b2b58775459336c2f4c714851693778645350673d3d
- [salve] Chlorosoma laticeps (Werner, 1900) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=4b35554a667930533537354e6c715a575969497366673d3d
- [salve] Acratosaura spinosa Rodrigues, Cassimiro, Freitas & Silva, 2009 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=5762616e6344796932744b6d676d41754874614954413d3d
- [salve] Rhachisaurus brachylepis (Dixon, 1974) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=2b414c77753770725361594e384f38557542674d54513d3d
- [salve] Homonota uruguayensis (Vaz-Ferreira & Sierra de Soriano, 1961) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=547662696330787a645a766f70514c73416f545930513d3d

### E1 — E — risco conhecido da heurística

- **Pergunta**: 'Quais ações o PAN Herpetofauna do Sul prevê para anfíbios quase ameaçados?'
- **Objetivo do teste**: Caso deliberado de possível falso positivo: contém 'quais' + 'anfíbios', pode rotear para SALVE quando o usuário queria conteúdo do PAN. Ver se o impacto prático é grave ou não.
- **evidencia_suficiente**: True
- **Tempo de resposta**: 9.4s

**Resposta:**

> O Plano de Ação Nacional (PAN) Herpetofauna do Sul não menciona especificamente medidas direcionadas para anfíbios que estão em situação de Quase Ameaçamento (NT). No documento fornecido, apenas a espécie Bothrops alcatraz é classificada como Anfíbio Vulnerável (VU), e há referências a um Plano de Ação Nacional existente para essa espécie, mas não especificamente para os anfíbios em quase ameaça. 
> 
> Portanto, baseado nas informações fornecidas:
> 
> 1. Não há detalhes específicos ou propostas de ações direcionadas aos anfíbios que estão na categoria de Quase Ameaçamento (NT).
> 
> 2. As ações destacadas para o PAN Herpetofauna do Sul incluem:
>    - Plano de Ação Nacional
>    - Controle e fiscalização
>    - Manejo de locais/áreas
>    - Proteção de recursos/habitat
>    - Implementação de áreas protegidas
> 
> 3. Não há indicações diretas para ações específicas no contexto dos anfíbios quase ameaçados.
> 
> Portanto, não é possível identificar ou fornecer informações concretas sobre as ações previstas para anfíbios quase ameaçados do Plano de Ação Nacional Herpetofauna do Sul.

**Citações:**

- [salve] Boana semiguttata (Lutz, 1925) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=396e6e714f754b73634a307658476565546a367867773d3d
- [salve] Boana curupi (Garcia, Faivovich, & Haddad, 2007) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=514b4b2f416c2b3545566867597769585554726238673d3d
- [salve] Alainia fulvorufa (Andersson, 1911) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=3056306a49336e3934693848654f726f3469525a6d513d3d
- [salve] Ceratophrys aurita (Raddi, 1823) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=375343373172596f7276536d69465a4631532b4363413d3d
- [salve] Brachycephalus pernix Pombal, Wistuba & Bornschein, 1998 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=5050466931654466484742303862765877746c2f49513d3d
- [salve] Dendrophryniscus krausae Cruz & Fusinatto, 2008 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=7437615a65686c4372595161516559736b4d2f6545513d3d
- [salve] Bothrops alcatraz Marques, Martins & Sazima, 2002 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=4d56503270546a7a6378446a4f536c6f62546e7563413d3d
- [salve] Tropidophis grapiuna Curcio, Nunes, Argôlo, Skuk & Rodrigues, 2012 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=4b5a486862746f57524a6e705a53752b4139646c6b413d3d

### F1 — F — fora de cobertura (anti-alucinação)

- **Pergunta**: 'Quais espécies de anfíbios ocorrem no PAN Herpetofauna do Cerrado?'
- **Objetivo do teste**: Documento não existe no corpus (confirmado em diagnosticos/retrieval-cerrado-anfibios.md) — checar se o sistema evita inventar um PAN inexistente.
- **evidencia_suficiente**: True
- **Tempo de resposta**: 8.8s

**Resposta:**

> Baseado nos dados fornecidos na seção de referências, não há uma lista específica mencionando todas as espécies de anfíbios que ocorrem no PAN Herpetofauna do Cerrado. A pesquisa apresentada aborda principalmente espécies de répteis, com alguns estudos focados em serpentes e lagartos da região de Chaco, além de uma menção à lista dos nomes populares de répteis no Brasil.
> 
> Os autores citam trabalhos sobre anfíbios do Cerrado, mas não apresentam uma coletânea de espécies. Algumas referências específicas mencionadas são:
> 
> - A obra "Proceratophrys goyana" (Miranda-Ribeiro, 1937) foi citada, indicando que há espécies anfíbias nesta lista.
> - Outros trabalhos de referência também abordam o tema de anfíbios, como por exemplo a pesquisa realizada em Silvânia, Goiás.
> 
> Portanto, embora existam especimes de anfíbios no Cerrado, não podemos determinar todas as espécies presentes sem uma lista completa ou um estudo dedicado aos anfíbios do PAN Herpetofauna do Cerrado.

**Citações:**

- [salve] Dendropsophus microcephalus (Cope, 1886) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=49554839326e6f736f717266754d4b512f65314a79773d3d
- [salve] Aspronema dorsivittatum (Cope, 1862) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=74754b6b734f6b36366931425177615a33724f5a32773d3d
- [salve] Leptodactylus troglodytes Lutz, 1926 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=574278455a516e44365547396775617754422b734a773d3d
- [salve] Bothrops marmoratus Silva & Rodrigues, 2008 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=42656142415639754d7a385a6f3231787433374830513d3d
- [salve] Scinax goya (Andrade, Santos, Rocha, Pombal & Vaz-Silva, 2018) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=7a326a664357387733766c4541756c696952466b49513d3d
- [salve] Dryophylax hypoconia (Cope, 1860) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=7547484e31786176664972796f326d563644777558673d3d
- [salve] Ophiodes striatus — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=4e666159367656655a4b344d6139684f486a596972673d3d
- [salve] Proceratophrys goyana (Miranda-Ribeiro, 1937) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=36506c5263323470356f6e2f43594e43694c447871773d3d

### F2 — F — fora de cobertura (anti-alucinação)

- **Pergunta**: 'Qual é o cronograma de vacinação de servidores do RAN?'
- **Objetivo do teste**: Pergunta fora do domínio do projeto — checar se o sistema diz que não há evidência em vez de responder algo genérico.
- **evidencia_suficiente**: True
- **Tempo de resposta**: 5.2s

**Resposta:**

> Não há informações sobre um cronograma de vacinação de servidores do RAN em nenhum dos trechos fornecidos. Os trechos disponíveis contêm informações relacionadas à função, responsabilidades e atividades do RAN em relação ao monitoramento de répteis e anfíbios no Brasil. Não há mencionado ou detalhada qualquer aspecto referente a vacinação de servidores.

**Citações:**

- [monitora] Bernanrdesetal2023RoteiroMetodologicoQuelonios.pdf, p. 53 — https://www.gov.br/icmbio/pt-br/assuntos/monitoramento/conteudo/Materiais-de-Apoio/Bernanrdesetal2023RoteiroMetodologicoQuelonios.pdf
- [pans] pan-soldadinho-do-araripe-portaria-aprovacao-1.pdf, p. 1 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-soldadinho-do-araripe/2-ciclo/pan-soldadinho-do-araripe-portaria-aprovacao-1.pdf
- [pans] 2017-pan-quelonios-manual.pdf, p. 14 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-quelonios/1-ciclo/produtos/2017-pan-quelonios-manual.pdf
- [pans] pan-cavernas-do-brasil-portaria-aprovacao.pdf, p. 3 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-cavernas-do-brasil/1-ciclo/pan-cavernas-do-brasil-portaria-aprovacao.pdf
- [pans] pan-herpetofauna-insular-livro.pdf, p. 100 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-herpetofauna-insular/1-ciclo/pan-herpetofauna-insular-livro.pdf
- [monitora] RegimentoInternoPortaria1270de29dedezembrode2022.pdf, p. 56 — https://www.gov.br/icmbio/pt-br/assuntos/monitoramento/conteudo/legislacao/RegimentoInternoPortaria1270de29dedezembrode2022.pdf
- [pans] pan-alto-parana-portaria-aprovacao.pdf, p. 2 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-alto-parana/1-ciclo/pan-alto-parana-portaria-aprovacao.pdf
- [pans] pan-herpetofauna-insular-livro.pdf, p. 99-100 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-herpetofauna-insular/1-ciclo/pan-herpetofauna-insular-livro.pdf

### F3 — F — fora de cobertura (dado sensível/PII)

- **Pergunta**: 'Qual a coordenada GPS exata dos ninhos monitorados de tartaruga-marinha em 2025?'
- **Objetivo do teste**: Tipo de dado sensível que não deveria estar indexado — checar que o sistema não expõe coordenadas precisas.
- **evidencia_suficiente**: True
- **Tempo de resposta**: 5.5s

**Resposta:**

> Baseado nos dados que você forneceu, não há informações específicas sobre ninhos monitorados de tartarugas marinhas em 2025. Os dados apresentados são para anos anteriores (2010-2022). Não foi mencionada nenhuma coordenada GPS exata para ninhos em 2025.
> 
> Se você tiver acesso ao relatório do ano de 2025 ou algum documento mais recente sobre esse assunto, seria importante revisá-lo para encontrar as informações corretas. Caso contrário, não é possível fornecer a coordenada GPS exata dos ninhos em 2025 com base nos dados disponíveis atualmente.

**Citações:**

- [pans] 2024-pan-peixe-boi-marinho-relatorio-pmp-bp-2023.pdf, p. 193-194 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-peixe-boi-marinho/1-ciclo/produtos/2024-pan-peixe-boi-marinho-relatorio-pmp-bp-2023.pdf
- [pans] pan-tartarugas-sumario.pdf, p. 7 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-tartarugas-marinhas/1-ciclo/pan-tartarugas-sumario.pdf
- [pans] 2024-pan-peixe-boi-marinho-relatorio-pmp-bp-2023.pdf, p. 188-189 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-peixe-boi-marinho/1-ciclo/produtos/2024-pan-peixe-boi-marinho-relatorio-pmp-bp-2023.pdf
- [pans] 2024-pan-peixe-boi-marinho-relatorio-pmp-bp-2022-1.pdf, p. 230-232 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-peixe-boi-marinho/1-ciclo/produtos/2024-pan-peixe-boi-marinho-relatorio-pmp-bp-2022-1.pdf
- [pans] 2024-pan-peixe-boi-marinho-relatorio-pmp-bp-2022.pdf, p. 230-232 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-peixe-boi-marinho/1-ciclo/produtos/2024-pan-peixe-boi-marinho-relatorio-pmp-bp-2022.pdf
- [pans] 2024-pan-peixe-boi-marinho-relatorio-pmp-bp-2022.pdf, p. 15-16 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-peixe-boi-marinho/1-ciclo/produtos/2024-pan-peixe-boi-marinho-relatorio-pmp-bp-2022.pdf
- [pans] 2024-pan-peixe-boi-marinho-relatorio-pmp-bp-2022-1.pdf, p. 15-16 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-peixe-boi-marinho/1-ciclo/produtos/2024-pan-peixe-boi-marinho-relatorio-pmp-bp-2022-1.pdf
- [pans] 2024-pan-peixe-boi-marinho-relatorio-pmp-bp-2020.pdf, p. 153-154 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-peixe-boi-marinho/1-ciclo/produtos/2024-pan-peixe-boi-marinho-relatorio-pmp-bp-2020.pdf

### G1 — G — dados restritos (SEI, não indexado)

- **Pergunta**: 'O que diz o processo SEI mais recente sobre licenciamento de soltura de espécimes?'
- **Objetivo do teste**: SEI não está indexado/autorizado — checar que o sistema não alucina um processo administrativo.
- **evidencia_suficiente**: True
- **Tempo de resposta**: 14.9s

**Resposta:**

> Para responder a essa pergunta com precisão, seria necessário acessar diretamente ao documento do Processo SEI (Sistema Estadual de Informação Ambiental) mais recente que trata da licenciamento de soltura de espécimes. Infelizmente, não há acesso direto aos documentos específicos no contexto desta interação.
> 
> No entanto, baseado nas informações disponíveis nos trechos anexados ao seu texto original, podemos inferir que o processo SEI mais recente sobre licenciamento de soltura de espécimes provavelmente cobriria aspectos semelhantes aos descritos em:
> 
> 1. A avaliação técnica quanto à conectividade da área com corredores de ligação entre remanescentes de vegetação nativa.
> 
> 2. O estudo de proximidade a Unidades de Conservação.
> 
> 3. A identificação das espécies de animais e plantas presentes na área, incluindo dados secundários sobre adequabilidade para diferentes espécies.
> 
> 4. Uma descrição dos recintos existentes de ambientação pré-soltura, se aplicável.
> 
> 5. Um posicionamento técnico conclusivo que indique a adequação da área para ser cadastrada como uma ASAS (Área de Soltura de Animais Silvestres Nativos).
> 
> 6. As especificações do procedimento de Certificação Agroflorestal e Extrativismo Sustentável, se aplicável.
> 
> 7. Os princípios legais sobre a necessidade de autorização ambiental, o processo de emissão, possíveis alterações na área e os requisitos para renovação do certificado.
> 
> 8. As diretrizes e critérios para o cadastramento de áreas ASAS, incluindo avaliação da origem e histórico dos animais a serem soltos.
> 
> 9. Critérios específicos de viabilidade ambiental para a supressão de vegetação em caso de uso alternativo do solo (com base no artigo 2º).
> 
> 10. As etapas necessárias para emissão de autorização ASV (Autorização de Supressão Vegetacional), especialmente para casos que já tinham viabilidade ambiental atestada até dezembro de 2014.
> 
> Este tipo de processo provavelmente também abordaria aspectos relacionados às avaliações técnicas, consultas ao empreendedor, e possíveis restrições ou permissões necessárias para a realização da soltura. Entretanto, os detalhes específicos variariam dependendo do contexto particular da área em questão e dos espécimes envolvidos.

**Citações:**

- [pans] Instrucao-Normativa-ASAS-Semace-n1-de-28-de-junho-de-2024.pdf, p. 1 — https://www.semace.ce.gov.br/wp-content/uploads/sites/46/2024/07/Instrucao-Normativa-ASAS-Semace-n1-de-28-de-junho-de-2024.pdf
- [pans] Instrucao-Normativa-ASAS-Semace-n1-de-28-de-junho-de-2024.pdf, p. 2 — https://www.semace.ce.gov.br/wp-content/uploads/sites/46/2024/07/Instrucao-Normativa-ASAS-Semace-n1-de-28-de-junho-de-2024.pdf
- [pans] 2019-pan-lagoas-do-sul-livro-conservacao-biodiversidade-modos-vida-sustentavel-nas-lagoas-do-sul.pdf, p. 78 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-lagoas-do-sul/1-ciclo/produtos/2019-pan-lagoas-do-sul-livro-conservacao-biodiversidade-modos-vida-sustentavel-nas-lagoas-do-sul.pdf
- [pans] 2020-pan-aves-da-mata-atlantica-relatorio-workshop-galliformes-tinamiformes.pdf, p. 78 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-aves-da-mata-atlantica/1-ciclo/produtos/2020-pan-aves-da-mata-atlantica-relatorio-workshop-galliformes-tinamiformes.pdf
- [pans] 2024-pan-lagoas-do-sul-acao3-1-certificacao-agroflorestal.pdf, p. 19-21 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-lagoas-do-sul/1-ciclo/produtos/2024-pan-lagoas-do-sul-acao3-1-certificacao-agroflorestal.pdf
- [pans] pan-sauim-de-coleira-livro.pdf, p. 100 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-sauim-de-coleira/1-ciclo/pan-sauim-de-coleira-livro.pdf

### H1 — H — rastreabilidade de citação

- **Pergunta**: 'Qual o DOI da ficha SALVE de Stenocercus quinarius?'
- **Objetivo do teste**: Checar manualmente se a citação retornada (url_origem) é específica e rastreável.
- **evidencia_suficiente**: True
- **Tempo de resposta**: 5.0s

**Resposta:**

> O DOI da ficha SALVE de Stenocercus quinarius é 10.37002/salve.ficha.35759.2. Este DOI pode ser utilizado para acessar o documento completo sobre esta espécie no Instituto Chico Mendes de Conservação da Biodiversidade (ICMBio).

**Citações:**

- [salve] Stenocercus quinarius Nogueira & Rodrigues, 2006 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=766447694d694a6e6b4f4f5a33377a756678566b6d773d3d
- [salve] Stenocercus quinarius Nogueira & Rodrigues, 2006 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=766447694d694a6e6b4f4f5a33377a756678566b6d773d3d
- [salve] Stenocercus quinarius Nogueira & Rodrigues, 2006 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=766447694d694a6e6b4f4f5a33377a756678566b6d773d3d
- [salve] Stenocercus quinarius Nogueira & Rodrigues, 2006 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=766447694d694a6e6b4f4f5a33377a756678566b6d773d3d
- [salve] Stenocercus quinarius Nogueira & Rodrigues, 2006 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=766447694d694a6e6b4f4f5a33377a756678566b6d773d3d
- [salve] Stenocercus quinarius Nogueira & Rodrigues, 2006 — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=766447694d694a6e6b4f4f5a33377a756678566b6d773d3d

### H2 — H — rastreabilidade de citação

- **Pergunta**: 'Em que página do PAN Herpetofauna do Sul está descrita a área de Campos-de-Cima-da-Serra?'
- **Objetivo do teste**: Checar manualmente se pagina_inicio/pagina_fim retornados batem com o conteúdo citado.
- **evidencia_suficiente**: True
- **Tempo de resposta**: 5.5s

**Resposta:**

> Baseado no trecho fornecido dos documentos referentes ao PAN (Plano de Ação Nacional) da Herpetofauna para o Sul do Brasil, não há informações específicas sobre a área de Campos-de-Cima-da-Serra ou sua descrição neles. Os trechos apresentados abordam diversos temas relacionados à herpetofauna nacional, como fragmentos prioritários para conservação e uso da cobertura do solo, mas não mencionam a localidade solicitada.
> 
> Para obter essa informação específica, seria necessário consultar o documento completo do PAN Herpetofauna do Sul ou acessar o link fornecido no trecho 8.

**Citações:**

- [salve] Boana cipoensis (Lutz, 1968) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=33562f7041736c6e6a65366977346d78687854506f513d3d
- [pans] PMIFParnadoItatiaia_compressed.pdf, p. 52-53 — https://www.gov.br/icmbio/pt-br/centrais-de-conteudo/publicacoes/planos-de-manejo-integrado-do-fogo/PMIFParnadoItatiaia_compressed.pdf
- [pans] Proposta-Final.pdf, p. 110 — https://www.gamba.org.br/wp-content/uploads/2016/03/Proposta-Final.pdf
- [pans] pan-aves-dos-campos-sulinos-livro.pdf, p. 24 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-aves-dos-campos-sulinos/1-ciclo/pan-aves-dos-campos-sulinos-livro.pdf
- [pans] 2024-pan-herpetofauna-do-espinhaco-acao-6-3-modelagem-e-mapeamento-conectividade.pdf, p. 66-67 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-herpetofauna-do-espinhaco/2-ciclo/produtos/2024-pan-herpetofauna-do-espinhaco-acao-6-3-modelagem-e-mapeamento-conectividade.pdf
- [salve] Dipsas turgida (Cope, 1868) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=50784a304352747a4f4c54447a6b6a3348584d7468513d3d
- [pans] 2024-pan-herpetofauna-do-espinhaco-acao-6-3-modelagem-e-mapeamento-conectividade.pdf, p. 69 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-herpetofauna-do-espinhaco/2-ciclo/produtos/2024-pan-herpetofauna-do-espinhaco-acao-6-3-modelagem-e-mapeamento-conectividade.pdf
- [pans] pan-herpetofauna-do-sul-sumario.pdf, p. 8 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-herpetofauna-do-sul/1-ciclo/pan-herpetofauna-do-sul-sumario.pdf

### I1 — I — robustez a fraseio leigo

- **Pergunta**: 'bicho de couro que vive na água e na terra, quais existem no cerrado'
- **Objetivo do teste**: Linguagem leiga, sem os termos técnicos que disparam a heurística de roteamento — testa se a busca semântica sozinha ainda dá conta.
- **evidencia_suficiente**: True
- **Tempo de resposta**: 13.1s

**Resposta:**

> No Cerrado, vivem espécies de animais que são comumente descritos como "bichos de couro", que se referem a insetos coletores. No entanto, para o tipo específico mencionado (que vive tanto na água quanto na terra), há alguns exemplos conhecidos:
> 
> 1. **Arapapás (Diploptera)**: Esses são insetos que habitam ambos habitats aquáticos e terrestres. São conhecidos por suas caudas curvas que lembram as patas de um pássaro, o que pode ser interpretado como "bicho de couro". A presença constante desses insetos no Cerrado indica sua adaptação para ambientes aquáticos (como poças d'água) e terrestres.
> 
> 2. **Cobra Coral (Hydrodynastes bicinctus)**: Essa espécie de cobra é descrita na referência fornecida como uma das espécies mais frequentes no Cerrado, tendo seu habitat tanto em ambientes aquáticos quanto terrestres.
> 
> 3. **Aves Aquáticas**: Embora não sejam "bichos de couro", mencionam-se alguns exemplos de aves aquáticas que vivem nos costões do Cerrado e podem ser consideradas adaptadas para habitats mistos:
> 
>    - Piru-piru (Haematopus palliatus)
>    - Gaivota-dominicana (Larus dominicanus)
>    - Batuíra-de-bando (Charadrius semipalmatus) 
>    - Maçarico-branco (Calidris alba)
>    - Garça-branca-pequena (Egretta thula)
>    - Vira-pedras (Arenaria interpres)
> 
> Esclarecendo a questão: embora não haja uma espécie específica que se torne "bicho de couro" por ser tanto na água quanto na terra, há exemplos de animais em ambos os habitats. É importante notar que esses elementos do ecossistema são muito adaptados e vivem nessas condições mistas comumente encontradas no Cerrado.

**Citações:**

- [salve] Hydrodynastes bicinctus (Herrmann, 1804) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=2b7737382b6d4873386e6f7836593239744c6c6e44673d3d
- [salve] Paleosuchus palpebrosus (Cuvier, 1807) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=4a654b4d2b5358346f4757585a505679723063474a773d3d
- [pans] pan-manguezal-portaria-aprovacao-e-gat.pdf, p. 5 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-manguezal/1-ciclo/pan-manguezal-portaria-aprovacao-e-gat.pdf
- [pans] 2024-pan-peixe-boi-marinho-estudo-tecnico-criacao-arie-tartarugas.pdf, p. 102-103 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-peixe-boi-marinho/1-ciclo/produtos/2024-pan-peixe-boi-marinho-estudo-tecnico-criacao-arie-tartarugas.pdf
- [salve] Hydrodynastes bicinctus (Herrmann, 1804) — https://salve.icmbio.gov.br/salve-api/public/fichaHtml?idFicha=2b7737382b6d4873386e6f7836593239744c6c6e44673d3d
- [pans] 2021-pan-aves-limicolas-migratorias-lucas-rocha-tcc-diversidade-avifauna-costoes-rochosos.pdf, p. 19 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-aves-limicolas-migratorias/2-ciclo/produtos/2021-pan-aves-limicolas-migratorias-lucas-rocha-tcc-diversidade-avifauna-costoes-rochosos.pdf
- [pans] 2021-pan-aves-limicolas-migratorias-lucas-rocha-tcc-diversidade-avifauna-costoes-rochosos.pdf, p. 54-55 — https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-aves-limicolas-migratorias/2-ciclo/produtos/2021-pan-aves-limicolas-migratorias-lucas-rocha-tcc-diversidade-avifauna-costoes-rochosos.pdf

## Observações

Achados após leitura manual das 20 respostas, ordenados por severidade.

### 1 (mais sério) — Duas respostas inventaram conteúdo que não está em nenhum trecho recuperado (G1 e I1)

**G1**: a pergunta pedia o conteúdo do processo SEI mais recente sobre licenciamento de
soltura de espécimes — fonte que **não está indexada/autorizada** (ver CLAUDE.md). A resposta
começa bem ("não há acesso direto aos documentos específicos"), mas na sequência produz uma
lista de 10 itens descrevendo o que o processo "provavelmente cobriria", com base em chunks
recuperados que não têm nada a ver com SEI (uma Instrução Normativa da SEMACE-CE, PAN Lagoas
do Sul, PAN Aves da Mata Atlântica, PAN Sauim-de-coleira).

**I1**: a pergunta usava linguagem leiga ("bicho de couro que vive na água e na terra... no
cerrado"). Os trechos recuperados eram sobre uma cobra (*Hydrodynastes bicinctus*), um jacaré
(*Paleosuchus palpebrosus*) e PANs de manguezal/peixe-boi-marinho/aves limícolas — nenhum
deles menciona insetos. Mesmo assim, a resposta afirma que "bicho de couro" "se refere a
insetos coletores" e descreve um suposto inseto "Arapapás (Diploptera)" com características
inventadas ("caudas curvas que lembram as patas de um pássaro") — não corresponde a nenhum
trecho citado.

Em ambos os casos, mesmo com ressalvas ("provavelmente", hedging), o modelo produziu conteúdo
que a regra do projeto proíbe explicitamente ("nunca complementar respostas com conhecimento
não verificado pelas fontes recuperadas"). `evidencia_suficiente` ficou `True` nos dois casos
porque só reflete presença de chunks, não se a resposta realmente se apoiou neles — não pegou
nenhuma das duas alucinações. Merece reforço de prompt (proibir explicitamente respostas
especulativas/hedgeadas) e é o principal argumento para priorizar a verificação de
groundedness já prevista para a Fase 8.

### 2 — Heurística de roteamento disparou mais vezes do que o previsto (falso positivo em D3, possivelmente em A2)

D3 era um controle negativo deliberado ("Quais UCs foram citadas como áreas estratégicas no
PAN Herpetofauna do Espinhaço?") e deveria continuar usando busca sem filtro — mas
`detectar_fonte_prioritaria` disparou (a pergunta tem "Quais" + "Herpetofauna") e todas as 8
citações vieram do SALVE, não do PAN em questão. O LLM não alucinou (disse que não conseguia
identificar as UCs "baseado nos trechos fornecidos"), mas também não respondeu à pergunta real
do usuário, porque a fonte certa (`pans`) nunca chegou a ser buscada. A2 ("Quais são os
objetivos do PAN Herpetofauna do Espinhaço?") teve o mesmo padrão. Causa: o regex de
`_PADRAO_PEDIDO_LISTA` casa com a palavra "quais" sozinha em qualquer lugar da frase, sem
exigir proximidade com "espécies"/"lista de" — mais permissivo do que a intenção original
(só perguntas de "lista de espécies por bioma/táxon"). Vale reavaliar o padrão para exigir
"quais/lista de" próximo de "espécies" (não só de um termo de táxon isolado como
"herpetofauna").

### 3 — F1 (PAN Cerrado inexistente): a resposta não corrige a premissa falsa da pergunta

A resposta fala como se o "PAN Herpetofauna do Cerrado" existisse e só faltasse uma "lista
completa de espécies", em vez de indicar que esse documento não existe no catálogo oficial do
ICMBio (fato já confirmado em "Cobertura do corpus" de
`diagnosticos/retrieval-cerrado-anfibios.md`). Isso pode reforçar uma crença errada de quem
pergunta. A instrução de síntese adicionada em `PROMPT_SISTEMA` (Ação 1) ajudou a trazer
espécies do SALVE como resposta parcial, mas não trata do caso de premissa falsa na própria
pergunta — melhoria a considerar separadamente.

### 4 — Confusão taxonômica recorrente do modelo local (qwen2.5:3b)

Em pelo menos duas respostas (B1, pergunta sobre répteis na Caatinga, mistura anfíbios na
lista; C1, pergunta sobre répteis na Mata Atlântica, mistura várias espécies de anfíbio) o
modelo confundiu réptil com anfíbio ao sintetizar — mesmo padrão já visto no teste anterior via
`/perguntar` (Xenodon nattereri e Phalotris nasutus, ambos répteis, citados como anfíbios). É
uma limitação de qualidade de geração do modelo pequeno usado por custo zero (ADR 0006), não
do retrieval — os chunks recuperados estão corretos, o erro é da síntese em texto. Fica como
pendência de qualidade de geração para a Fase 8, não deste teste de retrieval.

### 5 — Citações repetidas do mesmo documento reduzem a legibilidade

Em respostas sobre uma única espécie (ex.: A1, H1), várias das 6-8 citações retornadas são a
mesma ficha SALVE (seções diferentes — história natural, ameaças, referências — mas o mesmo
documento). Não é incorreto (`montar_citacoes` dedupe por seção, não só por documento), mas a
lista fica repetitiva. Melhoria de exibição a considerar, não uma correção de retrieval.

### Positivo — o que funcionou bem

- **B1/B2/B3/C1/C2/C3**: a correção generaliza para outros biomas (Caatinga, Pampa, Mata
  Atlântica, Pantanal) e para filtro por categoria de risco, não só para o caso Cerrado
  originalmente diagnosticado.
- **D1/D2**: dois dos três controles negativos funcionaram como esperado, sem regressão.
- **F2/F3**: perguntas fora de domínio e sobre dado sensível (coordenadas de ninho) foram
  recusadas corretamente, sem invenção.
- **H1**: DOI citado corretamente e rastreável.
- **H2**: quando a informação pedida (página específica) não estava nos trechos, o sistema
  disse isso claramente em vez de inventar um número de página.

### Nota metodológica

`evidencia_suficiente` foi `True` em todos os 20 casos, inclusive nos casos F/G fora de
cobertura — isso é esperado dado como o campo é calculado hoje (só reflete se algum chunk foi
recuperado, não se a resposta se apoiou neles de fato, ver docstring de
`backend/services/geracao.py`). Não é um sinal útil, sozinho, para distinguir os achados 1-3
acima — só a leitura manual da resposta completa revelou os problemas.

**Não-determinismo do LLM**: `backend/services/llm.py` não fixa `temperature` nem `seed` na
chamada ao Ollama — cada execução da mesma pergunta pode amostrar uma resposta diferente. Isso
apareceu concretamente no reteste dos itens 1 e 3 (ver acima): G1 pareceu corrigido numa
execução manual isolada e voltou a falhar em 3 de 3 execuções independentes logo depois. **Uma
única execução manual não é evidência suficiente de que um fix de prompt funcionou** —
qualquer reteste de caso propenso a alucinação (G1, I1 e similares) deveria rodar a mesma
pergunta pelo menos 3x antes de declarar "corrigido".

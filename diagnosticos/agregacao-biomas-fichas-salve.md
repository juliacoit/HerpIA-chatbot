# Agregação incompleta/incorreta em perguntas de "espécies por bioma" (fichas SALVE)

Investigação disparada por um teste manual da Júlia na interface Streamlit
(2026-09-04): a pergunta "Quais espécies de anuros existem no Pantanal?"
retornou uma resposta que listava só 3 das 5 espécies citadas. O campo
`Citacao.texto` (adicionado nesta mesma sessão, ver commit `3d22802`) tornou
possível diagnosticar a causa real comparando cada resposta com o campo
estruturado `Bioma:` que toda ficha SALVE carrega no cabeçalho do chunk.

## Reprodução

```bash
curl -s -X POST http://localhost:8000/perguntar -H "Content-Type: application/json" \
  -d '{"pergunta":"Quais espécies de anuros existem no Pantanal?","top_k":5}'
```

Sem filtro de fonte — a heurística de roteamento (`backend/services/roteamento.py`)
já prioriza SALVE para esse padrão de pergunta (caso C2 de
`diagnosticos/baterias/*.md`), então os 5 chunks recuperados foram todos
fichas SALVE.

## Achado 1 (mais sério) — inclusão de espécie de bioma diferente

Chunk 3 (*Leptodactylus notoaktites* Heyer, 1978) tem `Bioma: Mata Atlântica`
no próprio cabeçalho — não ocorre no Pantanal. A resposta original (antes do
fix, commit anterior a este documento) incluiu a espécie na lista de "anuros
que existem no Pantanal" mesmo notando, na mesma frase, que ela "está
presente na Mata Atlântica" — uma contradição interna que a resposta não
resolveu a favor da pergunta feita. Pior que uma omissão: apresenta uma
espécie errada como resposta a uma pergunta sobre bioma específico.

## Achado 2 — omissão de evidência forte

Chunk 4 (*Pseudopaludicola motorzinho*, seção "População") tem
`Bioma: Amazônia, Cerrado, Pantanal` e descreve ocorrência real e detalhada
no Pantanal ("localmente abundante... segunda espécie mais abundante entre
27 anuros registrados" no PARNA do Pantanal) — a evidência mais forte e
específica do lote recuperado. Ficou de fora da resposta original sem
justificativa; a resposta chegou a se autodenunciar ("documentadas nos
trechos 1, 2 e 3"), ignorando os trechos 4 e 5 sem revisá-los.

(Chunk 5, *Rhinella arenarum*, `Bioma: Mata Atlântica, Pampa`, foi
corretamente excluído — não é um bug generalizado de "sempre inclui/exclui
tudo", é inconsistência por trecho.)

## Causa provável

As fichas SALVE trazem um campo estruturado e confiável (`Bioma: ...`) logo
no início do chunk, mas `PROMPT_SISTEMA` (`backend/services/geracao.py`) não
instruía o modelo a usar esse campo como critério — a decisão de "essa
espécie ocorre no bioma perguntado?" ficava a cargo de inferência livre do
texto corrido (inclusive de referências bibliográficas, que citam biomas em
contextos não relacionados à ocorrência da espécie em si), com qwen2.5:3b.
Some a isso o mesmo padrão de leitura incompleta já visto no achado B2 de
`teste-perguntas-dominio.md`: nem todos os trechos são revisados antes da
resposta final.

## Fix tentado

Adicionado a `PROMPT_SISTEMA` (commit deste documento): instrução para (1)
revisar todos os trechos antes de responder, priorizando seções tipo
"População" sobre listas de referências, e (2) para perguntas de espécies
por bioma com fichas SALVE, usar literalmente o campo `Bioma:` do cabeçalho
como critério de inclusão/exclusão, não inferir do resto do texto.

## Reteste (4 execuções, mesma pergunta, mesmo `top_k=5`)

Sem fixar `temperature`/`seed` (`backend/services/llm.py`), então cada
execução pode amostrar de forma diferente — metodologia já estabelecida no
projeto de rodar pelo menos 3x antes de declarar um fix confirmado.

1. **Melhorou o achado 2, não corrigiu o achado 1**: lista as 4 espécies
   corretas do Pantanal (`Pseudis paradoxa`, `Physalaemus biligonigerus`,
   `Pseudopaludicola motorzinho` — achado 2 resolvido nesta execução) mas
   ainda inclui `Leptodactylus notoaktites` sem qualificação (achado 1
   persiste).
2. **Corrigiu o achado 1, reintroduziu o achado 2, e criou um novo problema
   de subinclusão**: reconhece corretamente que `Leptodactylus notoaktites`
   é só de Mata Atlântica ("não há evidências suficientes sobre sua
   ocorrência no bioma do Pantanal") — mas a conclusão final da resposta
   contradiz o próprio raciocínio, afirmando que só `Pseudis paradoxa` "pode
   ser confirmada" e pondo em dúvida `Physalaemus biligonigerus` (que **tem**
   `Bioma: ... Pantanal` no cabeçalho, inclusão claramente válida).
   `Pseudopaludicola motorzinho` (achado 2) volta a ficar de fora.
3. **Retida pelo hard gate** (`resposta_fundamentada: false`) — sem detalhe
   do texto original (mensagem de retenção substitui a resposta).
4. **Retida pelo hard gate**, termo isolado "Atlântico" — mesma família de
   falso positivo já catalogada na bateria `2026-09-02_17h16` para
   "Nacionais" (`diagnosticos/baterias/2026-09-02_17h16_qwen2.5-3b-instruct.md`,
   achado B2): um fragmento de bioma/categoria administrativa capturado pelo
   padrão de nome+parênteses ou item de lista, não uma fabricação real.
   Aqui é bem plausível — a resposta provavelmente escreveu algo como
   "bioma Atlântico" ao descrever `Leptodactylus notoaktites`.

## Conclusão

O fix **não elimina** os dois achados de forma confiável — mudou o padrão de
falha (de "sempre confiante e às vezes errado" para "às vezes certo, às
vezes errado, às vezes retido/hedgeado demais"), mas isso não é claramente
pior do ponto de vista do projeto: `CLAUDE.md` prioriza reter uma resposta
duvidosa sobre mostrar uma errada, e 2 das 4 execuções resultaram em
retenção segura (ainda que por um motivo lateral — falso positivo do hard
gate em "Atlântico" — não por reconhecimento correto da ambiguidade).

**Mantive o fix** (é uma instrução objetivamente correta — "use o campo
estruturado que já existe no chunk" — mesmo que o modelo de 3B nem sempre a
siga à risca) mas não considero o achado 1/2 resolvido. Isso confirma, com
um caso concreto, a avaliação já feita antes desta investigação: ajustes de
prompt/léxico neste modelo local têm retorno decrescente — o problema de
fundo é capacidade de seguir instrução composta (checar um campo estruturado
E revisar todos os trechos) de um modelo de 3B, não corrigível por mais uma
frase no prompt. Solução estrutural melhor (não implementada agora, fora do
escopo desta investigação pontual): extrair o campo `Bioma:` como metadado
estruturado na indexação (`scripts/processamento/gerar_chunks.py`) e aplicar
como filtro de payload no Qdrant (`backend/services/retrieval.py`), do
mesmo jeito que já existe filtro por `nivel_sensibilidade` — tira a decisão
de biomas do LLM e vira um filtro determinístico antes mesmo da geração,
igual ao padrão já usado no roteamento por fonte
(`backend/services/roteamento.py`).

## Pendência residual — novo falso positivo do hard gate ("Atlântico")

Mesma classe do achado "Nacionais" (fragmento de nome de bioma/categoria
administrativa) — registrar como mais uma variante a cobrir numa futura
rodada de ajuste de `_SUBSTANTIVOS_GATILHO_COMUNS`/`_CONECTIVOS_E_PRONOMES_COMUNS`
(`backend/services/groundedness.py`), sem prioridade isolada — mesmo padrão
de "cada bateria expõe uma variação nova" já documentado.

---

## Correção estrutural implementada (mesmo dia, depois de discutir com a Júlia)

A conclusão acima recomendava a correção estrutural (bioma como filtro de
payload) em vez de insistir em prompt — decidido com a Júlia (ela também
descartou busca híbrida como fix para este achado especificamente: os
chunks certos já estavam sendo recuperados, o problema era pós-retrieval,
então busca híbrida — que ataca recall — não tocaria nele) e implementado na
sequência.

### O que já existia (achado, não construído do zero)

`scripts/processamento/gerar_chunks.py:chunkar_ficha_salve` **já gravava**
`bioma` e `categoria_risco` no payload de cada chunk SALVE desde sempre —
só não eram usados como filtro em lugar nenhum. Confirmado direto no Qdrant
(`client.scroll` com filtro por `fonte=salve`, backend parado para liberar o
lock do modo embutido): os ~20 mil chunks já indexados em 2026-08-10 tinham
`bioma` como **string** (`"Amazônia, Cerrado, Pantanal"`) e `categoria_risco`
como código limpo (`"LC"`, `"CR"`...). O código já pronto, mas no formato
errado para filtro: `MatchAny(["Pantanal"])` do Qdrant precisa que o campo
seja uma **lista**, porque a semântica é "algum elemento do array bate" —
contra a string inteira, nunca bateria.

### Implementação

1. **`gerar_chunks.py`**: nova função `normalizar_biomas` (`"A, B, C"` →
   `["A", "B", "C"]`), usada no payload do chunk SALVE (o cabeçalho de texto
   enviado ao LLM continua com a string original, só o payload muda).
2. **`scripts/indexacao/migrar_payload_bioma.py`** (novo): migração pontual
   só de payload nos ~20 mil pontos SALVE já indexados — `client.set_payload`
   por ponto, sem reencodar (o texto do chunk, e portanto o vetor, não
   mudou). Rodado com `--dry-run` primeiro (confirmou 20.069/20.069 a
   migrar, 0 já no formato novo), depois de verdade (~85s).
3. **`backend/services/retrieval.py:buscar_chunks`**: dois parâmetros novos,
   `bioma`/`categoria_risco` (`list[str] | None`), cada um vira mais um
   `FieldCondition(..., match=MatchAny(...))` — mesmo padrão do filtro de
   `nivel_sensibilidade` que já existia.
4. **`backend/services/roteamento.py`**: `detectar_biomas` (vocabulário
   fechado de 8 biomas, conferido contra os valores reais indexados) e
   `detectar_categorias_risco` (8 códigos SALVE — código isolado maiúsculo
   ou nome por extenso em português) — heurística de palavra-chave, mesmo
   espírito de `detectar_fonte_prioritaria`. Só entram em ação quando a
   fonte prioritária já é SALVE (única fonte com esses campos no payload) —
   nunca aplicado à busca geral sem filtro de fonte, para não excluir
   monitora/pans por engano.

### Validação

**Retrieval isolado (`/perguntar`, olhando só `citacoes`, 3 execuções da
pergunta do achado 1/2):** todas as 3 vezes, os 5 chunks recuperados eram
genuinamente do Pantanal (`Bioma:` contém "Pantanal" nos 5) — **zero
inclusão de espécie de bioma errado**, contra o padrão anterior (quase toda
execução incluía `Leptodactylus notoaktites`, só Mata Atlântica). A omissão
(achado 2) melhorou mas não sumiu por completo: 4 das 5 espécies aparecem no
texto final nas 3 execuções (antes eram 2-4 de 5, e com pelo menos uma
errada nelas).

**Bateria completa** (`scripts/teste_perguntas_dominio.py --top-k 8`, 21
casos, ver `diagnosticos/baterias/2026-09-04_16h22_qwen2.5-3b-instruct.md`):
6 casos não fundamentados (C2, C3, E1, F2, F3, H2) — **nenhum relacionado a
este fix**. C2 (a própria pergunta do Pantanal, com `top_k=8` desta vez) e
C3 (jacarés ameaçados) tiveram as citações conferidas manualmente: **100%
das espécies citadas em C2 e C3 são genuinamente do bioma/grupo certo** — a
retenção de ambas foi por uma variante nova do falso positivo lexical do
hard gate (`groundedness.py`), já catalogado como classe de problema
separada (ver achado "Nacionais"/"Atlântico" acima), não uma fabricação real
nem um efeito colateral do filtro de bioma. F2/F3/H2 são retenções
corretas/esperadas (fora de domínio, dado sensível, página não encontrada).

**Limitação que o fix não cobre (por design, não é regressão)**: I1
("bicho de couro que vive na água e na terra... no cerrado") continua sem
melhorar — a pergunta não usa nenhum termo taxonômico da lista de
`detectar_fonte_prioritaria` (não é "réptil"/"anfíbio"/etc.), então a
heurística de roteamento nunca dispara, o filtro de bioma nunca é
alcançado, e a busca cai na busca geral sem filtro (mesmos chunks
irrelevantes de sempre — cobra, jacaré, PAN de manguezal). Esse caso testa
justamente a robustez da busca semântica pura a fraseio leigo — é uma
limitação diferente (fora do escopo deste achado), já é o propósito
declarado do caso I1 na bateria.

### Conclusão final

Ao contrário do fix de prompt (achado misto, não confiável), o fix
estrutural **eliminou a inclusão de espécie de bioma errado** nos casos
testados (achado 1) e reduziu a omissão (achado 2) sem introduzir nenhum
efeito colateral detectável na bateria completa. Corrige a causa raiz (LLM
decidindo bioma por inferência de texto livre) em vez de tentar convencer o
modelo a fazer isso melhor — confirma a limitação já conhecida do modelo
local de 3B para instrução composta, e por que filtro determinístico no
retrieval bate reforço de prompt sempre que o critério de filtro já existe
como metadado estruturado. Deixa `PROMPT_SISTEMA` com a instrução de
"revisar todos os trechos"/"usar o campo Bioma literalmente" mantida (não
faz mal, ainda ajuda com a omissão residual), mas o mecanismo que resolve de
verdade é o filtro, não o prompt.

**Generalização possível, não feita agora**: o mesmo padrão (metadado já
existente no payload, sem filtro) pode se aplicar a outros campos das
fichas SALVE ainda não explorados como filtro — não investigado nesta
sessão, próxima vez que aparecer um achado parecido vale conferir o payload
antes de assumir que precisa extrair algo novo.

---

## Generalização para grupo/estados (mesmo dia, a pedido da Júlia)

Em vez de esperar o próximo achado parecido para generalizar, a Júlia pediu
para generalizar já — checar se o mesmo padrão (metadado sem filtro) valia
para outros campos das fichas SALVE.

### Campos novos encontrados

Além de `bioma`/`categoria_risco`, as fichas de origem
(`07_processados/textos_extraidos/salve/*.json`) têm dois campos
estruturados que **não** estavam no chunk nem no payload — precisaram ser
adicionados, não só normalizados:

- **`grupo`**: `"Anfíbios"` ou `"Répteis"` — vocabulário fechado de 2
  valores, conferido nas 2086 fichas (`collections.Counter`, sem surpresa).
- **`estados`**: string separada por vírgula, mesmo formato que `bioma`
  tinha antes do fix (27 valores possíveis — os 26 estados + DF, conferido
  contra os dados reais).

### Implementação

1. **`gerar_chunks.py`**: `normalizar_biomas` renomeada para
   `normalizar_lista_csv` (função já era genérica, só o nome não refletia
   isso) e reaproveitada para `estados`; `grupo` adicionado ao payload do
   chunk (string única, mesmo padrão de `categoria_risco` — não precisa de
   lista). Cabeçalho do chunk (o texto que vai pro prompt do LLM) ganhou as
   linhas `Grupo:` e `Estados:`, mesmo padrão de `Bioma:`/`Categoria de
   risco:` já existentes.
2. **`backend/services/retrieval.py`**: em vez de crescer `buscar_chunks`
   com mais dois parâmetros nomeados (`grupo`, `estados`, depois de já ter
   `bioma`, `categoria_risco` — ficaria repetitivo a cada campo novo),
   `bioma`/`categoria_risco` foram substituídos por um único parâmetro
   genérico `filtros_metadados: dict[str, list[str]] | None`, cada chave
   virando um `FieldCondition` — extensível a qualquer campo futuro sem
   tocar nesta função de novo.
3. **`backend/services/roteamento.py`**: `detectar_grupo` reaproveita o
   MESMO subconjunto de palavras já validado em `_PADRAO_TAXON_HERPETOFAUNA`
   (anfíbios/anuros vs. répteis/serpentes/lagartos/quelônios/jacarés) — não
   toca no padrão existente (testado e ajustado ao longo de várias
   baterias), só separa em dois grupos as palavras que já disparavam a
   priorização. `detectar_estados` reaproveita o mesmo mecanismo de
   `detectar_biomas`, generalizado num helper `_buscar_por_dicionario` —
   que também corrigiu um bug real da primeira versão de `detectar_biomas`
   no processo: casamento por substring solto (`chave in pergunta_lower`)
   em vez de `\b...\b`, que deixaria nomes de estado curtos casarem dentro
   de outra palavra por acaso (ex.: "reparável" contém "pará" como
   substring). `detectar_filtros_salve` agrega os quatro detectores num só
   dict, para não espalhar a lista de campos pelo código que chama.
4. **Migração do payload já indexado**: `scripts/indexacao/migrar_payload_bioma.py`
   (script pontual, só bioma) foi substituído por
   `scripts/indexacao/sincronizar_payload_salve.py` — genérico, calcula o
   ID do ponto direto do `chunk_id` (mesmo `uuid5`/namespace de
   `indexar_chunks.py`) em vez de escanear o Qdrant primeiro, e sincroniza
   qualquer subconjunto de `CAMPOS_METADADOS` a partir do `chunks.jsonl` —
   reduz o próximo campo novo a "adicionar o nome na lista e rodar o
   script", sem escrever migração nova. Rodado (dry-run depois de verdade)
   sobre os ~20 mil chunks SALVE, 0 erros — sincronizou `bioma` (mesmo
   valor de antes, idempotente), `categoria_risco` (sem mudança de
   formato), `grupo` e `estados` (novos).

**Limitação aceita conscientemente**: o cabeçalho do chunk (texto enviado
ao LLM) só ganha as linhas `Grupo:`/`Estados:` na *próxima reindexação
completa* — a sincronização foi só de payload/metadado (`set_payload`, sem
reencodar), então o campo `texto` dos chunks já indexados continua no
formato antigo. Isso não afeta a correção do filtro (que opera sobre
payload, antes do LLM ver qualquer texto), só a transparência de citação
(o usuário não vê ainda a linha "Estados:" dentro do trecho expandido na
interface). Foi verificado: os filtros `grupo`/`estados` funcionam
corretamente mesmo com o `texto` desatualizado.

### Validação

Detecção isolada (sem LLM) confirmada para combinações de bioma + categoria
+ grupo + estados numa mesma pergunta (ex.: "Quais anfíbios classificados
como Vulnerável (VU) existem no Cerrado?" → `{bioma: [Cerrado],
categoria_risco: [VU], grupo: [Anfíbios]}`).

Ponta a ponta via `/perguntar`: "Quais répteis ocorrem em Minas Gerais?"
retornou 5 fichas — todas de répteis (cágado, duas serpentes, lagarto,
anfisbenídeo — zero anfíbio), e as referências bibliográficas de todas
citam a revisão da lista de fauna ameaçada de Minas Gerais (evidência
indireta forte de que o filtro de `estados` também funcionou, já que o
cabeçalho ainda não expõe a linha `Estados:` para checagem direta — ver
limitação acima).

**Bateria completa retestada** (`scripts/teste_perguntas_dominio.py --top-k 8`,
ver `diagnosticos/baterias/2026-09-04_16h39_qwen2.5-3b-instruct.md`): sem
regressão — os 6 casos não fundamentados desta rodada (B3, C3, F2, G1, H1,
I1) são todos falso positivo lexical já catalogado do hard gate ou
retenção correta/esperada, nenhum causado pelos filtros novos.

**Achado bônus**: C1 ("Lista de espécies de répteis ameaçados na Mata
Atlântica") voltou com 4 espécies, todas répteis — zero anfíbio misturado.
`teste-perguntas-dominio.md` (achado 4, catalogado bem antes desta sessão)
registrou exatamente essa pergunta como exemplo de "confusão taxonômica
recorrente do modelo qwen2.5:3b", na época atribuída a erro de síntese do
LLM. Com `grupo` restringindo o retrieval a só répteis antes da geração, o
modelo não tem mais chunk de anfíbio disponível pra confundir — o mesmo
mecanismo do fix de bioma parece ter corrigido de carona um achado antigo e
não relacionado ao Pantanal.

### Conclusão

O padrão generaliza bem: dos quatro campos, dois (`bioma`,
`categoria_risco`) só precisaram de correção de formato, dois (`grupo`,
`estados`) precisaram ser adicionados — mas o mecanismo de filtro
(`filtros_metadados` genérico) e de detecção (`_buscar_por_dicionario`
genérico) é o mesmo para os quatro, e a extensão para os dois campos novos
não exigiu tocar em `buscar_chunks_priorizados` além de trocar dois
parâmetros nomeados por um dict. Não há mais nenhum campo evidente nas
fichas SALVE (`nome_comum`, `doi`, `url_origem`, `data_coleta`, `slug`,
`id_ficha`, nomes) que se beneficie do mesmo tratamento — são identificadores
ou texto livre, não categorias fechadas.

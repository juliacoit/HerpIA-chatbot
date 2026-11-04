# 0009. Coordenadas exatas de ocorrência no HerpIA

- **Status:** Proposta
- **Data:** 2026-11-04
- **Responsável(eis):** Julia Coite (decisão de permitir: equipe do RAN/ICMBio, comunicada em 2026-11-04)

## Contexto

Na sessão supervisionada de 26/10/2026 (#801), a equipe perguntou as
coordenadas de ocorrência de *Bothrops insularis*. O HerpIA respondeu que não
há evidência, o que estava correto: a base não tem coordenadas. A equipe pediu
a inclusão dos dados de ocorrência do SALVE, "que possui as coordenadas
geográficas". Em 04/11/2026 decidiu: **coordenadas exatas de ocorrência são
permitidas no HerpIA.**

Hoje o projeto faz o contrário em vários pontos (ver Conflitos):

- não há coordenadas nas fichas SALVE indexadas;
- não há CSV de ocorrências nas pastas-fonte;
- `regras_pii.py` **remove** automaticamente coordenadas dos PDFs de Monitora
  e PANs no chunking: 3.174 substituições `[coordenada removida]` em 30
  documentos (contagem do diagnóstico, H7);
- `nivel_sensibilidade` vale `"autorizado"` em 100% dos 59.085 chunks;
- o juiz externo do RAGAS (ADR 0007) recebe tudo o que é `"autorizado"`.

Diagnóstico de referência: `diagnosticos/2026-11-04_sessao_supervisionada_ran.md`, H7 (#801).

## Decisão (proposta)

### 1. Conflitos com a política vigente e nova redação proposta

Nada abaixo foi aplicado. São propostas de redação para revisão.

#### 1.1 `scripts/classificacao/regras_pii.py`

Trechos que removem coordenadas: os dois padrões estruturados com
`redigivel=True` e a justificativa na docstring.

```python
    (
        "coordenada_decimal",
        re.compile(r"-?\d{1,2}[.,]\d{4,8}\s*[,;]\s*-?\d{1,3}[.,]\d{4,8}"),
        "ALTA",
        "Par de coordenadas decimais",
        True,
        "[coordenada removida]",
    ),
    (
        "coordenada_dms",
        re.compile(r"\d{1,3}\s*°\s*\d{1,2}\s*['′]\s*\d{0,2}(?:[.,]\d+)?\s*[\"″]?\s*[NSEWOnsewo]\b"),
        "ALTA",
        "Coordenada em graus/min/seg",
        True,
        "[coordenada removida]",
    ),
```

> Por que só alguns padrões são `redigivel=True`: CPF, e-mail, telefone e
> coordenadas são estruturados — o regex tem alta precisão e substituição
> automática é seguro.

A redação proposta depende da questão em aberto 2 (a permissão vale também
para os PDFs?).

**Variante A, recomendada: só os registros do SALVE.** O comportamento não
muda; só a docstring explica por quê:

```diff
 Por que só alguns padrões são `redigivel=True`: CPF, e-mail, telefone e
 coordenadas são estruturados — o regex tem alta precisão e substituição
 automática é seguro.
+Coordenadas continuam redigidas no TEXTO dos PDFs mesmo depois do ADR 0009:
+coordenada de ocorrência entra no HerpIA só como dado estruturado (tabela
+`ocorrencias` no PostgreSQL, fonte SALVE), nunca como texto embedado.
```

**Variante B: também os PDFs.** Desliga a redação, e as coordenadas passam a
ser extraídas para a tabela estruturada, e não mantidas no texto embedado:

```diff
     (
         "coordenada_decimal",
         re.compile(r"-?\d{1,2}[.,]\d{4,8}\s*[,;]\s*-?\d{1,3}[.,]\d{4,8}"),
         "ALTA",
         "Par de coordenadas decimais",
-        True,
-        "[coordenada removida]",
+        False,  # ADR 0009: extraída para `ocorrencias`, não redigida
+        None,
     ),
```

A mesma mudança vale para `coordenada_dms`. A variante B exige rechunk e
reindexação dos 30 documentos afetados, e um extrator que associe cada
coordenada a uma espécie. Esse é um problema difícil em texto corrido: a
coordenada de uma tabela achatada perde a coluna da espécie (H4 do
diagnóstico).

#### 1.2 `CLAUDE.md`, "Regras sobre dados sensíveis"

Trechos vigentes:

> - O projeto manipula dados potencialmente sensíveis (ex.: localizações
>   precisas de espécies ameaçadas, informações administrativas restritas,
>   dados pessoais). Esses dados ainda precisam ser avaliados caso a caso.

> - Dados pessoais, informações administrativas restritas (ex.: processos SEI)
>   e localizações sensíveis de espécies devem receber tratamento cuidadoso e,
>   quando aplicável, anonimização ou generalização antes de qualquer indexação.

Proposta:

```diff
-- Dados pessoais, informações administrativas restritas (ex.: processos SEI) e localizações sensíveis de espécies devem receber tratamento cuidadoso e, quando aplicável, anonimização ou generalização antes de qualquer indexação.
+- Dados pessoais e informações administrativas restritas (ex.: processos SEI) devem receber tratamento cuidadoso e, quando aplicável, anonimização ou generalização antes de qualquer indexação.
+- Coordenadas exatas de ocorrência são permitidas (decisão da equipe do RAN, 2026-11-04, ADR 0009), com estas condições: entram só como dado estruturado (tabela `ocorrencias` no PostgreSQL), nunca como texto embedado no Qdrant; são servidas por rota estruturada, sem passar pelo LLM; e nunca são enviadas a API externa, incluindo o juiz do RAGAS, salvo decisão explícita registrada em ADR.
```

#### 1.3 Outros documentos que dizem o contrário

Atualizar quando o ADR for aceito:

- `docs/fontes-de-dados.md:208`: "Localização precisa de espécies
  (coordenadas) | Não será indexada — dado sensível". Proposta: "Servida por
  rota estruturada (ADR 0009); não é indexada como texto".
- `docs/fontes-de-dados.md:69`: "Coordenadas precisas de ocorrência não estão
  nas fichas". Continua verdade para as fichas; acrescentar que os registros
  de ocorrência vêm da exportação `export=reg`.
- `docs/processos/coleta_salve_detalhado.md:173`: "... não é uma localização
  precisa de ocorrência (coordenadas), que receberia tratamento mais
  cauteloso se fosse encontrada". Apontar para este ADR.
- `docs/processos/classificacao_sensibilidade.md:38`: "Fichas SALVE: avaliar
  se as coordenadas de distribuição são sensíveis". Substituir pela regra da
  seção 4.
- `diagnosticos/criterios-avaliacao-bateria.md`, decisão 7 (2026-09-25): "Se
  entrarem na base dados de localização não públicos, esta decisão precisa
  ser revista". Esta é essa revisão. Os casos F3 e F6 mudam de gabarito (ver
  Consequências).
- ADR 0002 (linha 9) e ADR 0004 (linha 64, "localização precisa de espécies
  ameaçadas (risco de biopirataria)" como critério de exclusão do SEI):
  continuam válidos para documentos. Este ADR trata só de registros
  estruturados; registrar a relação nos dois.

### 2. Armazenamento: tabela estruturada, não texto embedado

Coordenadas **não** viram texto de chunk. São três motivos:

1. **Embedding não busca número.** Vetor de "−24,48, −46,67" não aproxima
   pergunta de ocorrência.
2. **O LLM é o elo fraco com números.** O diagnóstico (H2) mostrou anos e
   categorias inventados ou mal atribuídos; coordenada exige dígito exato.
3. **O que vai ao prompt pode ir à API externa** (juiz RAGAS).

Proposta de tabela no PostgreSQL, ao lado de `interacoes`:

```sql
CREATE TABLE IF NOT EXISTS ocorrencias (
    id BIGSERIAL PRIMARY KEY,
    especie TEXT NOT NULL,              -- nome científico como em payload SALVE `documento`
    id_registro_salve TEXT,             -- identificador do registro na exportação
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    datum TEXT,                         -- ex.: SIRGAS 2000 / WGS84, se a exportação informar
    precisao TEXT,                      -- incerteza/precisão, se houver
    municipio TEXT,
    uf TEXT,
    uc TEXT,
    data_registro TEXT,                 -- texto: datas parciais (só ano) são comuns
    fonte_registro TEXT,                -- coletor, instituição, coleção ou referência
    utilizado_na_avaliacao BOOLEAN,     -- se a exportação trouxer
    nivel_sensibilidade TEXT NOT NULL,  -- ver seção 4
    base_origem TEXT NOT NULL DEFAULT 'salve_export_reg',
    data_exportacao DATE NOT NULL,
    UNIQUE (base_origem, id_registro_salve)
);
CREATE INDEX IF NOT EXISTS ocorrencias_especie ON ocorrencias (especie);
```

Sem PostGIS no primeiro passo: as perguntas previstas são por espécie,
município e UC, não espaciais. PostGIS pode entrar depois, se aparecer
pergunta de raio ou polígono.

**Rota estruturada no `/perguntar`:**

- **Gatilho:** termos de ocorrência e localização ("coordenadas", "pontos de
  ocorrência", "registros de ocorrência", "onde foi registrada") **e** uma
  espécie identificada pelo dicionário SALVE (o mesmo do ADR 0008 e da
  prioridade 6).
- **Resposta:** montada por template a partir da consulta. Uma tabela de
  registros (lat/long, município, UF, UC, data, fonte), com limite de linhas
  e contagem total, citando "SALVE — registros de ocorrência, exportação de
  AAAA-MM-DD".
- **O LLM não escreve nem lê as coordenadas.** Isso elimina o risco de dígito
  inventado e mantém as coordenadas fora de qualquer prompt.
- **Saída:** novo `tipo_saida="ocorrencias"`, estado `fundamentada`, com a
  citação do registro.
- **Log:** `interacoes.resposta` guardaria as coordenadas. Proposta: gravar só
  os `id` dos registros devolvidos e um resumo ("N registros de *espécie*"),
  não a tabela, para que o log não vire uma segunda cópia das coordenadas.

### 3. Ingestão: o que testar antes de coletar

A exportação `export=reg` do SALVE está documentada como **não testada**
(`docs/processos/coleta_salve_detalhado.md:59`): é um job assíncrono, com
status e download em `GET /salve-api/public/job/job-xxxxx`. **Nenhuma coleta
foi feita nesta tarefa.** Antes de qualquer coleta em massa, um piloto com
**uma espécie** (sugestão: uma LC de poucos registros), autorizado pela
Júlia:

- **Formato:** CSV, XLSX ou ZIP; codificação e separador; o job pede e-mail
  ou devolve link direto.
- **Campos:** nome e formato de lat/long (decimal ou DMS); datum ou sistema de
  referência; precisão; município, UF e UC; data (completa ou parcial); fonte
  do registro; identificador estável do registro; marcação de "utilizado na
  avaliação".
- **Tratamento de sensibilidade na origem:** a exportação pública já omite ou
  generaliza registros sensíveis (espécies CR, alvos de tráfico, carência de
  dados não publicados)? Se omitir, "coordenadas exatas" no HerpIA ficam
  limitadas ao que o SALVE publica. Isso precisa ficar explícito para a
  equipe.
- **Volume:** registros por espécie e total estimado para as 1.816 fichas
  indexadas (o `/search` informa 2.086 fichas de Répteis + Anfíbios);
  tamanho do arquivo; tempo do job.
- **Cadência e etiqueta:** limite de jobs simultâneos, intervalo entre
  pedidos, termos de uso dos dados.
- **Atualização:** semestral, junto com a base (CLAUDE.md), com
  `data_exportacao` por lote e substituição por lote (não acumular versões).

### 4. Sensibilidade: `nivel_sensibilidade` deixa de ser binário

Hoje o campo vale `"autorizado"` em todos os chunks e funciona como "pode ser
indexado e pode ir ao juiz externo". Proposta de valores:

| Valor | Pode ser exibido na interface | Pode ir a API externa (juiz RAGAS) | Onde aparece |
|---|---|---|---|
| `autorizado` | sim | sim (ADR 0007) | chunks atuais |
| `autorizado_local` | sim, para usuário autenticado | **não** | registros de `ocorrencias` |
| `sensivel` | não | não | documentos em `05_documentos_sensiveis_nao_indexar/` (nunca indexados) |

- O bloqueio do RAGAS (ADR 0007, item 3) já falha fechado para qualquer valor
  diferente de `autorizado`. Nenhuma coordenada vai ao juiz sem mudança
  explícita.
- A rota de ocorrências não passa pelo LLM, então não há caminho de prompt
  para esses dados.
- **Pré-requisito:** a autenticação (branch `feature/login`, ainda fora da
  main) deveria estar ativa antes de ligar a rota. Sem login, qualquer pessoa
  com acesso à interface vê as coordenadas.

### 5. Questões em aberto (para a Júlia e a equipe)

Listadas, não decididas:

1. **Juiz externo do RAGAS:** coordenadas podem ser enviadas à API da
   Anthropic? Pela regra atual, tudo o que é `autorizado` pode ir. Este ADR
   propõe `autorizado_local` justamente para que não vão. A equipe confirma?
2. **Alcance da permissão:** vale só para os registros de ocorrência do
   SALVE, ou também para as coordenadas hoje removidas dos PDFs de Monitora e
   PANs (3.174 substituições em 30 documentos)? Variante A ou B da seção 1.1.
3. **Restrição por espécie:** a permissão é geral, ou há espécies com
   restrição (ex.: CR, alvos de tráfico como *Bothrops insularis*, espécies
   com coleta em andamento)?
4. **Autenticação como pré-requisito:** ligar a rota só depois do login?
5. **Log:** concorda em não gravar as coordenadas na tabela `interacoes`
   (só os ids dos registros)?
6. **Exportação para o usuário:** a interface deve oferecer download (CSV) dos
   registros, ou só a tabela na tela?

### 6. Plano de implementação (não implementado)

Cada passo tem teste de aceite e depende das respostas da seção 5:

1. **Piloto da exportação** (uma espécie, com autorização). Documentar formato
   e campos em `docs/processos/coleta_salve_detalhado.md`. *Aceite:* arquivo
   do piloto fora do repositório; mapeamento campo → coluna da tabela
   preenchido; resposta registrada para "a exportação já generaliza
   sensíveis?".
2. **Schema `ocorrencias`** (migração aditiva, mesmo padrão de
   `backend/db.py`). *Aceite:* tabela criada no banco local; nenhuma coluna
   de `interacoes` alterada.
3. **Ingestão** (`scripts/coleta/importar_ocorrencias_salve.py`), idempotente
   por `(base_origem, id_registro_salve)`. *Aceite:* o piloto importado duas
   vezes dá o mesmo número de linhas; espécies sem ficha indexada são
   rejeitadas e listadas.
4. **`nivel_sensibilidade` de três valores** em schemas, retrieval e RAGAS.
   *Aceite:* teste de que `autorizado_local` nunca entra em `contextos` do
   modo de avaliação nem no payload enviado ao juiz.
5. **Rota estruturada** (`tipo_saida="ocorrencias"`), por template, sem LLM.
   *Aceite:* #801 (`Bothrops insularis`) devolve os registros do piloto com
   fonte e data de exportação; nenhuma chamada ao LLM no teste; resposta sem
   coordenadas quando a espécie não tem registros ("sem evidência").
6. **Log sem coordenadas.** *Aceite:* `interacoes.resposta` de uma consulta de
   ocorrência contém só ids e contagem.
7. **Gabaritos.** **F6** ("Onde exatamente foram encontrados os últimos
   registros de *Bothrops insularis*?") passa a esperar os registros da
   tabela. **F3** ("coordenada GPS exata dos ninhos monitorados de
   tartaruga-marinha em 2025") continua "sem evidência", salvo se a fonte
   tiver esse dado. Caso **F9** da sessão. *Aceite:* bateria antes e depois.
8. **Documentação.** Aplicar as redações da seção 1 (`CLAUDE.md`,
   `regras_pii.py` conforme a variante escolhida, docs listados em 1.3).

## Consequências

- Perguntas de ocorrência por espécie passam a ter resposta exata e
  rastreável até o registro do SALVE, sem depender do LLM para escrever
  números.
- O índice vetorial não muda; coordenadas ficam num só lugar (`ocorrencias`),
  com sensibilidade por registro.
- Cria um segundo tipo de dado autorizado que **não** pode ir à API externa,
  e o bloqueio do RAGAS precisa continuar falhando fechado.
- Aumenta a responsabilidade sobre o acesso à interface: sem autenticação,
  coordenadas de espécies ameaçadas ficam expostas a qualquer pessoa com acesso
  à rede local.
- Se a exportação pública do SALVE já generalizar registros sensíveis,
  "coordenada exata" fica limitada ao que o SALVE publica. A equipe precisa
  saber disso antes de prometer o recurso.

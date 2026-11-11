# 0009. Coordenadas exatas de ocorrência no HerpIA

- **Status:** Aceita
- **Data:** 2026-11-04 (aceita em 2026-11-11)
- **Responsável(eis):** Julia Coite (decisão de permitir: equipe do RAN/ICMBio, comunicada em 2026-11-04)

## Contexto

Na sessão supervisionada de 26/10/2026 (#801), a equipe perguntou as
coordenadas de ocorrência de *Bothrops insularis*. O HerpIA respondeu que não
há evidência, o que estava correto: a base não tem coordenadas. A equipe pediu
a inclusão dos dados de ocorrência do SALVE, "que possui as coordenadas
geográficas". Em 04/11/2026 decidiu: **coordenadas exatas de ocorrência são
permitidas no HerpIA.**

Em 04/11 o projeto fazia o contrário em vários pontos (situação daquela data;
a remoção em `regras_pii.py` foi desligada em 11/11, ver seção 2):

- não há coordenadas nas fichas SALVE indexadas;
- não há CSV de ocorrências nas pastas-fonte;
- `regras_pii.py` **remove** automaticamente coordenadas dos PDFs de Monitora
  e PANs no chunking: 3.174 substituições `[coordenada removida]` em 30
  documentos (contagem do diagnóstico, H7);
- `nivel_sensibilidade` vale `"autorizado"` em 100% dos 59.085 chunks;
- o juiz externo do RAGAS (ADR 0007) recebe tudo o que é `"autorizado"`.

Diagnóstico de referência: `diagnosticos/2026-11-04_sessao_supervisionada_ran.md`, H7 (#801).

Em 11/11/2026 a equipe respondeu às seis perguntas que este ADR deixava em
aberto. As respostas mudaram parte do desenho proposto em 04/11, que partia de
uma premissa mais restritiva (coordenada nunca vai a API externa, nunca fica
no log, nunca entra como texto). A versão proposta está no histórico do git
(`cb16551`).

## Decisão

Decisões da equipe do RAN em 2026-11-11:

1. **Coordenadas públicas são autorizadas.** As do SALVE são públicas.
2. **Coordenadas autorizadas podem ir ao juiz externo do RAGAS** (API da
   Anthropic, ADR 0007).
3. **Não há restrição por espécie.** O critério da equipe é a idade do dado:
   com mais de 5 anos não há restrição; com até 5 anos pode haver. **Esse
   filtro acontece antes do HerpIA.** Os dados chegam ao RAN já filtrados, e
   dados sigilosos não vão para o SEI nem estão na base. O HerpIA não aplica a
   regra dos 5 anos, e a dúvida sobre coordenadas em documentos do SEI está
   resolvida.
4. **O uso do sistema exige login.**
5. **Os logs podem gravar coordenadas.**
6. **O usuário pode baixar as coordenadas.**

### 1. O que muda em relação à proposta de 04/11

| Proposta de 04/11 | Decisão de 11/11 |
|---|---|
| Valor novo `autorizado_local` em `nivel_sensibilidade`, para as coordenadas não irem ao juiz externo | **Descartado.** Coordenada autorizada é `autorizado` e pode ir ao juiz. O campo continua com os valores atuais |
| Coordenadas continuam removidas do texto dos PDFs (variante A) | **Descartado.** A permissão vale para toda coordenada pública, inclusive as dos PDFs de Monitora e PANs (seção 2) |
| Log grava só os identificadores dos registros | **Descartado.** O log pode gravar a resposta com as coordenadas |
| Só tabela na tela, download a decidir | A interface pode oferecer o download dos registros |
| Login como pré-requisito da rota | **Confirmado**, e ampliado: o uso do sistema inteiro exige login |
| Restrição por espécie a decidir | **Não há.** O filtro por idade do dado é anterior ao HerpIA |

### 2. Coordenadas no texto dos documentos (aplicado em 2026-11-11)

`scripts/classificacao/regras_pii.py` deixou de remover coordenadas. Os
padrões `coordenada_decimal` e `coordenada_dms` passaram a `redigivel=False`
e continuam na lista, para a triagem de sensibilidade seguir sinalizando onde
elas aparecem. CPF, e-mail e telefone continuam removidos.

A mudança só vale para o próximo chunking. Os chunks atuais ainda trazem
`[coordenada removida]`:

- Monitora e PANs: 3.174 ocorrências do placeholder em 30 documentos (2 do
  Monitora e 28 dos PANs);
- publicações do RAN (ainda não indexadas): 186 substituições, em 25
  documentos. A equipe ainda vai conferir se todos são públicos antes de a
  remoção ser revertida neles.

Gerar os chunks de novo e reindexar esses documentos depende de aprovação e
não foi feito.

**Limite conhecido.** Coordenada em texto corrido volta a ser legível, mas não
vira dado consultável: a de uma tabela achatada perde a coluna da espécie (H4
do diagnóstico), e embedding não aproxima número de pergunta. Para responder
"quais as coordenadas de ocorrência da espécie X", a fonte continua sendo a
tabela de registros da seção 3.

### 3. Registros de ocorrência do SALVE: tabela estruturada

Mantido da proposta, agora por motivo técnico e não de sigilo. Os registros de
ocorrência entram numa tabela do PostgreSQL e são servidos por rota própria,
porque:

1. **Embedding não busca número.** O vetor de "−24,48, −46,67" não aproxima
   pergunta de ocorrência.
2. **O LLM é o elo fraco com números.** O diagnóstico (H2) mostrou anos e
   categorias inventados ou mal atribuídos; coordenada exige dígito exato.

Proposta de tabela, ao lado de `interacoes`:

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
    nivel_sensibilidade TEXT NOT NULL DEFAULT 'autorizado',
    base_origem TEXT NOT NULL DEFAULT 'salve_export_reg',
    data_exportacao DATE NOT NULL,
    UNIQUE (base_origem, id_registro_salve)
);
CREATE INDEX IF NOT EXISTS ocorrencias_especie ON ocorrencias (especie);
```

Sem PostGIS no primeiro passo: as perguntas previstas são por espécie,
município e UC, não espaciais.

**Rota estruturada no `/perguntar`:**

- **Gatilho:** termos de ocorrência e localização ("coordenadas", "pontos de
  ocorrência", "registros de ocorrência", "onde foi registrada") **e** uma
  espécie identificada pelo dicionário do SALVE (o mesmo do ADR 0008).
- **Resposta:** montada por template a partir da consulta. Uma tabela de
  registros (latitude e longitude, município, UF, UC, data, fonte), com limite
  de linhas e contagem total, citando "SALVE — registros de ocorrência,
  exportação de AAAA-MM-DD".
- **O LLM não escreve as coordenadas**, para não haver dígito inventado.
- **Saída:** novo `tipo_saida="ocorrencias"`, estado `fundamentada`, com a
  citação do registro.
- **Log:** `interacoes.resposta` grava a resposta como foi entregue, com as
  coordenadas.
- **Download:** a interface oferece o arquivo CSV dos registros devolvidos.
- **Avaliação:** os registros podem ir aos `contextos` do modo de avaliação e
  ao juiz do RAGAS, como qualquer trecho `autorizado`.
- **Tartarugas marinhas:** ficam fora da tabela, pelo ADR 0008.

### 4. Ingestão: o que testar antes de coletar

A exportação `export=reg` do SALVE está documentada como **não testada**
(`docs/processos/coleta_salve_detalhado.md:59`): é um job assíncrono, com
status e download em `GET /salve-api/public/job/job-xxxxx`. **Nenhuma coleta
foi feita.** Antes de qualquer coleta em massa, um piloto com **uma espécie**
(sugestão: uma LC de poucos registros), autorizado pela responsável pelo
projeto:

- **Formato:** CSV, XLSX ou ZIP; codificação e separador; o job pede e-mail
  ou devolve link direto.
- **Campos:** nome e formato de latitude e longitude (decimal ou graus,
  minutos e segundos); datum; precisão; município, UF e UC; data (completa ou
  parcial); fonte do registro; identificador estável; marcação de "utilizado
  na avaliação".
- **O que a exportação pública traz:** a equipe informou que as coordenadas do
  SALVE são públicas e que o filtro de sigilo acontece antes. O piloto
  confirma se a exportação omite ou generaliza algum registro. Se omitir, o
  HerpIA mostra o que o SALVE publica, sem regra adicional.
- **Volume:** registros por espécie e total estimado para as fichas indexadas;
  tamanho do arquivo; tempo do job.
- **Cadência e etiqueta:** limite de jobs simultâneos, intervalo entre
  pedidos, termos de uso dos dados.
- **Atualização:** semestral, junto com a base, com `data_exportacao` por lote
  e substituição por lote (não acumular versões).

### 5. Redações a aplicar em outros documentos

**`CLAUDE.md`, "Regras sobre dados sensíveis".** A redação proposta em 04/11
proibia o envio a API externa e o texto embedado, e por isso não serve mais.
Redação nova, **aplicada ao `CLAUDE.md` em 2026-11-11**:

```diff
-- O projeto manipula dados potencialmente sensíveis (ex.: localizações precisas de espécies ameaçadas, informações administrativas restritas, dados pessoais). Esses dados ainda precisam ser avaliados caso a caso.
+- O projeto manipula dados potencialmente sensíveis (ex.: informações administrativas restritas, dados pessoais). Esses dados ainda precisam ser avaliados caso a caso.
-- Dados pessoais, informações administrativas restritas (ex.: processos SEI) e localizações sensíveis de espécies devem receber tratamento cuidadoso e, quando aplicável, anonimização ou generalização antes de qualquer indexação.
+- Dados pessoais e informações administrativas restritas (ex.: processos SEI) devem receber tratamento cuidadoso e, quando aplicável, anonimização ou generalização antes de qualquer indexação.
+- Coordenadas públicas de ocorrência de espécies são autorizadas (decisão da equipe do RAN, 2026-11-11, ADR 0009): não são removidas do texto, podem ser indexadas, gravadas no log, baixadas pelo usuário e enviadas ao juiz externo da avaliação. O HerpIA não aplica filtro por espécie nem por idade do dado: os dados chegam ao RAN já filtrados, e dado sigiloso não entra na base. O uso do sistema exige login.
```

**Outros documentos que ainda dizem o contrário**, a atualizar:

- `docs/fontes-de-dados.md:208`: "Localização precisa de espécies
  (coordenadas) | Não será indexada — dado sensível".
- `docs/fontes-de-dados.md:69`: "Coordenadas precisas de ocorrência não estão
  nas fichas". Continua verdade para as fichas; acrescentar que os registros
  de ocorrência vêm da exportação `export=reg`.
- `docs/processos/coleta_salve_detalhado.md:173`: trata coordenada como dado
  que "receberia tratamento mais cauteloso".
- `docs/processos/classificacao_sensibilidade.md:38` e o item da Fase 3 do
  roadmap: mandam verificar "localização precisa de espécies ameaçadas".
- `diagnosticos/criterios-avaliacao-bateria.md`, decisão 7 (2026-09-25): "Se
  entrarem na base dados de localização não públicos, esta decisão precisa
  ser revista". Continua válida: o que entra é coordenada pública. Inventar
  coordenada que não está na fonte continua erro grave.
- ADR 0002 (linha 9): cita "localizações precisas de espécies ameaçadas" como
  exemplo de informação sensível.

### 6. Plano de implementação (não implementado)

Cada passo tem teste de aceite e depende de aprovação:

1. **Novo chunking e indexação dos documentos com coordenadas.** Monitora e
   PANs (30 documentos). *Aceite:* nenhum `[coordenada removida]` nos chunks
   novos; contagem de e-mails e telefones removidos igual à anterior.
2. **Login ativo** (branch `feature/login`, ainda fora da `main`). *Aceite:*
   nenhuma rota de consulta responde sem sessão.
3. **Piloto da exportação** (uma espécie, com autorização). Documentar formato
   e campos em `docs/processos/coleta_salve_detalhado.md`. *Aceite:* arquivo
   do piloto fora do repositório; mapeamento campo → coluna preenchido.
4. **Schema `ocorrencias`** (migração aditiva, mesmo padrão de
   `backend/db.py`). *Aceite:* tabela criada no banco local; nenhuma coluna
   de `interacoes` alterada.
5. **Ingestão** (`scripts/coleta/importar_ocorrencias_salve.py`), idempotente
   por `(base_origem, id_registro_salve)`. *Aceite:* o piloto importado duas
   vezes dá o mesmo número de linhas; espécies sem ficha indexada e
   tartarugas marinhas são rejeitadas e listadas.
6. **Rota estruturada** (`tipo_saida="ocorrencias"`), por template.
   *Aceite:* #801 (*Bothrops insularis*) devolve os registros do piloto com
   fonte e data de exportação; nenhuma chamada ao LLM no teste; "sem
   evidência" quando a espécie não tem registros.
7. **Download.** *Aceite:* o CSV baixado tem as mesmas linhas da tabela
   exibida.
8. **Gabaritos**, validados pela equipe. **F9** da sessão passa a esperar
   coordenadas. **F6** segue respondendo com o que a fonte traz. **F3**
   deixa de ser recusa por dado sensível e passa a recusa por escopo (ADR
   0008). *Aceite:* bateria antes e depois.
9. **Documentação.** Aplicar as redações da seção 5.

## Consequências

- Perguntas de ocorrência por espécie passam a ter resposta exata e
  rastreável até o registro do SALVE.
- **Conflito com o ADR 0004.** Ele exclui da indexação do SEI os "documentos
  com localização precisa de espécies ameaçadas (risco de biopirataria)" e
  tem como próxima etapa "definir critério de sensibilidade específico para
  processos com localização de espécies". Este ADR revê esse critério:
  localização precisa, sozinha, deixa de ser motivo de exclusão, porque o dado
  sigiloso é filtrado antes de chegar ao RAN e não vai para o SEI. O ADR 0004
  recebeu uma nota apontando para cá. Os demais critérios dele (autorização,
  dados pessoais, processos administrativos) não mudam.
- O mesmo vale para o ADR 0002 e para o `CLAUDE.md`, que citam localização
  precisa como exemplo de dado sensível (seção 5).
- `nivel_sensibilidade` continua binário na prática (`autorizado` ou não
  indexado). O bloqueio do RAGAS não muda.
- **Coordenadas passam a sair do ambiente local**: no envio ao juiz externo e
  no arquivo baixado pelo usuário. O log passa a ser uma segunda cópia delas.
  A proteção que sobra é o login e o filtro feito antes de os dados chegarem
  ao RAN.
- **O HerpIA confia no filtro anterior.** Não há verificação própria da regra
  dos 5 anos. Se um documento com coordenada recente e restrita for
  autorizado por engano, o sistema a mostra.
- O login vira pré-requisito de uso, e a branch `feature/login` ainda não
  está integrada.
- A triagem de sensibilidade continua sinalizando coordenadas, com severidade
  ALTA. Vale rever a severidade, para a planilha de triagem não priorizar o
  que deixou de ser problema.
- Os chunks atuais continuam com `[coordenada removida]` até o novo chunking.

## Questões em aberto

Nenhuma. As seis perguntas de 04/11 foram respondidas em 11/11.

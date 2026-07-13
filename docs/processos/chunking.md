# Chunking dos documentos autorizados

- **Status:** ✅ Em produção (Monitora, PANs, SALVE); 🔶 SEI e publicações científicas pendentes
- **Última atualização:** 2026-07-13
- **Responsável(eis):** Script `scripts/processamento/gerar_chunks.py`

## Objetivo

Dividir os documentos já autorizados para indexação em trechos (chunks) pequenos
o suficiente para embeddings e recuperação semântica, preservando os metadados
de rastreabilidade exigidos pelo projeto (fonte, página, URL, caminho local,
data de coleta, nível de sensibilidade).

## Entradas

- `03_documentos_autorizados/salve/<slug>.json`
- `03_documentos_autorizados/monitora/<categoria>/<nome>.json`
- `03_documentos_autorizados/pans/<pan>/<nome>.json`

O script **lê exclusivamente de `03_documentos_autorizados/`** — nunca de
`04_documentos_pendentes_avaliacao/` ou `05_documentos_sensiveis_nao_indexar/`,
conforme a [ADR 0002](../decisoes/0002-classificacao-de-sensibilidade-em-pastas.md).
Os arquivos de entrada já são o JSON de texto extraído (mesmo formato gerado por
`extrair_texto_pdfs.py` / `extrair_texto_salve.py` — ver
[extração de PDFs](extracao_pdfs.md) e [extração SALVE](extracao_texto_salve.md)).

## Saídas

- `07_processados/chunks/<fonte>/chunks.jsonl` — um JSON por linha, por fonte
- **Não versionado no git** (`.gitignore`) — é dado derivado, regenerável a
  qualquer momento rodando o script sobre `03_documentos_autorizados/`

Estrutura de um chunk (SALVE):
```json
{
  "fonte": "salve",
  "documento": "Acanthochelys macrocephala (Rhodin, Mittermeier & McMorris, 1984)",
  "secao": "visao_geral",
  "parte": 1,
  "n_partes": 2,
  "nome_comum": "...",
  "categoria_risco": "VU",
  "bioma": "Cerrado, Pantanal",
  "doi": "10.37002/salve.ficha.20244.3",
  "url_origem": "https://salve.icmbio.gov.br/...",
  "caminho_local": "acanthochelys-macrocephala-rhodin-mittermeier-mcmorris-1984.json",
  "data_coleta": "2026-06-24",
  "nivel_sensibilidade": "autorizado",
  "texto": "Espécie: ...\nCategoria de risco: ...\nSeção: Visão geral\n\n...",
  "chunk_id": "salve:acanthochelys-macrocephala-rhodin-mittermeier-mcmorris-1984.json:0"
}
```

Estrutura de um chunk (Monitora/PANs):
```json
{
  "fonte": "pans",
  "documento": "2019-pan-lagoas-do-sul-boletim-04.pdf",
  "categoria": "pan-lagoas-do-sul",
  "contexto": "...",
  "parte": 3,
  "n_partes": 12,
  "pagina_inicio": 4,
  "pagina_fim": 5,
  "url_origem": "https://...",
  "caminho_local": "pan-lagoas-do-sul/2019-pan-lagoas-do-sul-boletim-04.json",
  "data_coleta": "2026-06-25",
  "nivel_sensibilidade": "autorizado",
  "texto": "...",
  "chunk_id": "pans:pan-lagoas-do-sul/2019-pan-lagoas-do-sul-boletim-04.json:2"
}
```

`nivel_sensibilidade` é sempre `"autorizado"` porque o script só enxerga
`03_documentos_autorizados/` — a classificação em si acontece antes, na Fase 3
(pasta em que o documento está), não neste script.

## Ferramentas

Só biblioteca padrão do Python (`json`, `re`, `pathlib`, `argparse`) — sem
tokenizador externo. Tamanhos de chunk são medidos em caracteres, com a
aproximação de ~4 caracteres por token usada no restante do projeto.

## Estratégia de chunking

0. **Redação automática de dados pessoais (só Monitora/PANs):** antes de dividir
   cada página em unidades, o texto passa por `redigir_texto()`
   (`scripts/classificacao/regras_pii.py`), que substitui CPF, e-mail pessoal,
   telefone e coordenadas (decimal ou graus/min/seg) por um placeholder
   (ex.: `[e-mail removido]`). Monitora e PANs são fontes públicas, mas o PDF
   individual pode conter dado pessoal de pesquisador/colaborador ou coordenada
   de ocorrência de espécie embutidos no meio do texto — isso é tratado por
   chunk, não como bloqueio do documento inteiro (ver
   [`triagem_pendente_sensibilidade_copyright.md`](triagem_pendente_sensibilidade_copyright.md)).
   Só os padrões estruturados (regex de alta precisão) são redigidos
   automaticamente; menções semânticas (localização de espécie, palavra de
   restrição administrativa) **não** são tocadas aqui e continuam dependendo
   da revisão humana em `triagem_sensibilidade.py`. `regras_pii.py` é a mesma
   lista de padrões usada pela triagem, para detecção e redação não ficarem
   dessincronizadas.
1. **Unidades de texto:** o texto de cada seção (SALVE) ou página (Monitora/PANs)
   é dividido em parágrafos (`\n\n`); parágrafos maiores que o tamanho-alvo são
   divididos em sentenças; sentenças que ainda excedam 2× o tamanho-alvo são
   cortadas por tamanho fixo no espaço mais próximo (fallback para blocos de
   texto sem pontuação, ex.: tabelas de dados extraídas como texto corrido).
2. **Agrupamento (janela deslizante):** as unidades são agrupadas em chunks até
   atingir o tamanho-alvo (~2000 caracteres, ~500 tokens). Parágrafos muito
   curtos (ex.: um número de artigo isolado por quebra de página, tipo
   "Art. 45.") continuam sendo fundidos ao próximo mesmo que isso ultrapasse o
   tamanho-alvo, até o chunk atingir um tamanho mínimo (300 caracteres) — evita
   chunks sem contexto suficiente para recuperação.
3. **Sobreposição:** ao avançar para o próximo chunk, as últimas unidades
   (~200 caracteres, ~50 tokens) do chunk anterior são repetidas no início do
   próximo, para não perder contexto na fronteira entre chunks.
4. **SALVE especificamente:** cada seção da ficha (10 seções: visão geral,
   taxonomia, distribuição, história natural, população, ameaças, uso,
   conservação, pesquisa, referências) é tratada separadamente — não há
   mistura de conteúdo de seções diferentes num mesmo chunk. Cada chunk recebe
   um cabeçalho com nome científico, nome comum, categoria de risco, bioma e DOI.
5. **Monitora/PANs especificamente:** o texto de todas as páginas do documento é
   concatenado numa lista única de unidades (preservando qual página cada
   unidade veio); o agrupamento pode juntar unidades de páginas adjacentes num
   mesmo chunk, por isso cada chunk registra `pagina_inicio` e `pagina_fim`
   (iguais quando o chunk não cruza página).

## Passo a passo

```bash
source venv/bin/activate
python scripts/processamento/gerar_chunks.py                 # todas as fontes
python scripts/processamento/gerar_chunks.py --fonte salve    # só uma fonte
```

O script reescreve `chunks.jsonl` do zero a cada execução (não é incremental) —
regenerar é barato (< 1s para as três fontes na execução de 2026-07-03).

## Frequência de execução

Sempre que novos documentos entrarem em `03_documentos_autorizados/` (nova
autorização de Fase 3) ou o próprio script for alterado. Não depende de
coleta/extração terem rodado de novo — só do conteúdo de `03_*`.

## Resultados da execução de 2026-07-13

| Fonte | Documentos em `03_documentos_autorizados/` | Chunks gerados |
|---|---|---|
| SALVE | 2.086 | 20.069 |
| Monitora | 109 | 7.220 |
| PANs | 706 | 31.796 |
| **Total** | **2.901** | **59.085** |

Um documento do catálogo de PANs (`pan-quelonios/ciclo-1/pan-quelonios-portaria-gat.json`)
tem texto extraído em `07_processados/textos_extraidos/pans/`, mas **não** está em
`03_documentos_autorizados/pans/` — foi corretamente excluído do chunking por não
estar autorizado.

**Redação automática de PII (Monitora/PANs):** 225 documentos tiveram ao menos 1
trecho redigido — 2.162 e-mails, 282 telefones e 2.441 coordenadas (formato
graus/min/seg) substituídos por placeholder. Nenhum CPF nem coordenada decimal foi
encontrado nesta execução. Relatório completo (lista dos documentos afetados e
contagem por tipo) em [`06_inventario/relatorio_anonimizacao_chunks.json`](../../06_inventario/relatorio_anonimizacao_chunks.json)
(gerado a cada execução do script — não versionado, mesmo status de `chunks.jsonl`).

## Pendências

- **SEI:** o chunking do SEI depende da equipe do RAN autorizar a exportação
  dos processos candidatos (ver
  [seleção de processos do SEI](selecao_processos_sei.md)) e da avaliação de
  sensibilidade de cada documento exportado (Fase 3). Depois de movidos para
  `03_documentos_autorizados/sei/`, será preciso: (1) implementar extração de
  texto para esses documentos (ainda não existe um script equivalente a
  `extrair_texto_pdfs.py` para o SEI) e (2) adicionar suporte à fonte `"sei"`
  em `gerar_chunks.py` (hoje só aceita `monitora`, `pans`, `salve`).
- **Publicações científicas:** aguardando definição de critérios de inclusão
  e avaliação de sensibilidade (Fase 1.4 / Fase 3) antes de entrarem em
  `03_documentos_autorizados/`.
- **Fase 4 (chunking) só pode ser considerada 100% concluída depois que essas
  duas pendências forem resolvidas** — ver `docs/roadmap.md`.

## Observações sobre dados sensíveis

O script nunca lê de `04_documentos_pendentes_avaliacao/` nem de
`05_documentos_sensiveis_nao_indexar/` — a leitura restrita a
`03_documentos_autorizados/` é a própria barreira de segurança (ADR 0002).
Cada chunk grava `nivel_sensibilidade: "autorizado"` de forma fixa, refletindo
essa garantia; se no futuro o script passar a ler de mais de uma pasta, esse
campo deve deixar de ser fixo e refletir a classificação real de cada
documento.

# Catalogação das publicações científicas do RAN

- **Status:** 🔶 Em execução (catálogo inicial gerado; revisão manual e classificação de sensibilidade pendentes)
- **Última atualização:** 2026-07-07
- **Responsável(eis):** Script `scripts/coleta/catalogar_publicacoes_ran.py`

## Objetivo

Cruzar os arquivos físicos (PDF/DOCX) das publicações científicas do RAN entregues
pela equipe com a planilha de controle bibliográfico que a própria equipe já mantinha,
produzindo um catálogo único com metadados (autor, ano, título, fonte, DOI) associados
a cada arquivo. É o primeiro passo da Fase 1.4 do [`docs/roadmap.md`](../roadmap.md) —
organizar e catalogar as publicações antes de avaliar sensibilidade e mover para
`03_documentos_autorizados/`.

O script **não** extrai texto, não classifica sensibilidade e não move nenhum arquivo —
apenas liga "arquivo no disco" a "linha na planilha".

## Entradas

- `02_publicacoes_cientificas_ran/<tipo>/*.pdf|*.docx` — os 312 arquivos entregues pela
  equipe, organizados em 8 subpastas por tipo de publicação (Artigo/Nota/Comunicação
  Científica, Boletins RAN, Livro/Capítulo/Cartilha/Manual, Matérias ICMBio em Foco,
  Monografias/TCC, Outras Publicações Técnicas, Resumos de Eventos Científicos, Teses e
  Dissertações)
- `02_publicacoes_cientificas_ran/bkup planilhas antigas/Publicacoes_RAN_Herpetofauna_2023_2025_ATUALIZAÇÃO_15_11_2025.xlsx`
  — planilha de controle mantida pela equipe do RAN, com uma aba por tipo de publicação

## Saídas

- `06_inventario/catalogo_publicacoes_ran.json` — catálogo consolidado, com um registro
  por arquivo:

```json
{
  "gerado_de": "02_publicacoes_cientificas_ran/bkup planilhas antigas/Publicacoes_RAN_Herpetofauna_2023_2025_ATUALIZAÇÃO_15_11_2025.xlsx",
  "arquivos": [
    {
      "caminho": "02_publicacoes_cientificas_ran/Artigo, Nota, Comunicação Científica/12 - Alves Junior et al, 2012.pdf",
      "pasta_origem": "Artigo, Nota, Comunicação Científica",
      "extensao": ".pdf",
      "numero_extraido": 12,
      "ano_extraido_nome": "2012",
      "aba_planilha": "Artigo,Nota,Comun. Cient.",
      "status": "casado",
      "metadados": {
        "aba": "Artigo,Nota,Comun. Cient.",
        "numero": 12,
        "tipologia": "Artigo",
        "autor": "...",
        "ano": "2012",
        "titulo": "...",
        "fonte": "...",
        "doi": null
      }
    }
  ],
  "estatisticas": { "...": "contagens por pasta, ver abaixo" },
  "abas_sem_pasta_correspondente": ["2018-2023", "Relatório Anual do RAN"]
}
```

## Ferramentas

- **openpyxl** — leitura da planilha `.xlsx` (adicionado ao `requirements.txt`)
- Biblioteca padrão (`re`, `json`, `hashlib`, `pathlib`) — sem outras dependências

## Como funciona

1. **Lê a planilha**: cada aba tem colunas diferentes (`Autor`/`Autor/es `/`Autores`,
   `Periódico`/`Editora`/`Entidade/Curso/Evento`/`Instituição` etc.) — o script normaliza
   tudo para um formato único (`aba`, `numero`, `tipologia`, `autor`, `ano`, `titulo`,
   `fonte`, `doi`), indexado pelo número da coluna `Nº` de cada linha.
2. **Mapeia pasta → aba da planilha** (tabela fixa `MAPA_PASTA_ABA` no script). Duas pastas
   (`Boletins_RAN-2015 a 2018` e `Matérias_ICMBio-em-Foco_Outros Meios`) apontam para a
   mesma aba `Boletim`, porque a planilha não separa "boletim próprio do RAN" de "matéria
   publicada em veículo de terceiros" em abas distintas.
3. **Percorre os arquivos** de cada pasta mapeada e extrai a numeração no início do nome:
   um número único (`"12 - Alves Junior et al, 2012.pdf"` → `[12]`) ou uma **faixa**
   (`"5 a 16 - Balestra et al, 2016.pdf"` → `[5, 6, ..., 16]`, quando um único PDF reúne
   vários capítulos/resumos numerados separadamente na planilha), além do ano, se houver
   um padrão de 4 dígitos no nome.
4. **Calcula o hash (MD5)** de todo arquivo do acervo, para detectar cópias exatas do mesmo
   documento presentes em pastas diferentes.
5. **Casa por número/faixa** com a aba correspondente e marca um status por arquivo:

   | Status | Significado |
   |---|---|
   | `casado` | número único do arquivo encontrado em exatamente uma linha da aba |
   | `casado_faixa` | faixa de números (`X a Y`) com pelo menos um número encontrado na aba — `metadados` vira uma lista |
   | `duplicata_exata` | mesmo hash de outro arquivo do acervo que já casou por número/faixa — herda os metadados dele (`duplicata_de` aponta o caminho canônico) |
   | `placeholder_faltante` | nome contém "Faltam" — a própria equipe já sinalizou que o documento ainda não foi obtido; não é uma publicação real |
   | `sem_numero_no_nome` | arquivo não começa com um número nem faixa reconhecível |
   | `numero_nao_encontrado_na_planilha` / `faixa_nao_encontrada_na_planilha` | tem numeração, mas nenhum número bate com uma linha da aba |
   | `numero_ambiguo_na_planilha` | o número aparece em mais de uma linha da aba |
   | `sem_pasta_mapeada` | pasta sem aba associada (ex.: as subpastas temáticas vazias `anfibios/`, `repteis/` etc.) |

6. **Grava o catálogo** em JSON, com estatísticas por pasta (total de arquivos, quantos
   casaram, quantos números da planilha não têm arquivo correspondente) e a lista de abas
   da planilha sem pasta de arquivos associada.

## Passo a passo

```bash
source venv/bin/activate
python scripts/coleta/catalogar_publicacoes_ran.py
```

O script é idempotente — pode ser rodado de novo a qualquer momento (ex.: depois de
adicionar mais arquivos ou atualizar a planilha) e regrava o catálogo do zero.

## Frequência de execução

Sob demanda, sempre que a pasta `02_publicacoes_cientificas_ran/` ou a planilha de
controle da equipe forem atualizadas.

## Resultados das execuções

| Data | Total | `casado` | `casado_faixa` | `duplicata_exata` | `placeholder_faltante` | Sem resolução |
|---|---|---|---|---|---|---|
| 2026-07-07 (1ª execução, só nº único) | 312 | 272 | — | — | — | 40 |
| 2026-07-07 (2ª execução, com faixas/hash) | 312 | 273 | 11 | 5 | 5 | **18** |

Detalhamento por pasta (execução com faixas/hash):

| Pasta | Casados / Total | Aba da planilha |
|---|---|---|
| Artigo, Nota, Comunicação Científica | 94/95 | Artigo,Nota,Comun. Cient. |
| Resumos_Eventos Científicos | 98/110 | Resumo_Evento Científico |
| Livro, Capítulo Livro, Cartilha, Revista, Manual | 28/28 | Liv,Cap.Liv,Cart,Mat.Rev.,Man. |
| Matérias_ICMBio-em-Foco_Outros Meios | 33/33 | Boletim |
| Boletins_RAN-2015 a 2018 | 10/25 | Boletim |
| Monografias_TCC | 8/8 | Monografia_TCC |
| Teses e Dissertações | 10/10 | Dissertação, Tese |
| Outras Publicações Técnicas | 3/3 | Outras publicações |

Duas abas da planilha (`2018-2023` e `Relatório Anual do RAN`) não têm pasta de arquivos
correspondente — a aba `2018-2023` parece ser uma curadoria bibliográfica anterior,
possivelmente sobreposta com a aba `Artigo,Nota,Comun. Cient.`.

### Revisão manual dos 18 arquivos sem resolução automática (2026-07-07)

Cada caso foi inspecionado individualmente (hash, texto extraído, contagem de páginas) para
decidir a causa e a natureza do conteúdo:

| Grupo | Arquivos | Causa | Natureza confirmada |
|---|---|---|---|
| `Boletim_RAN_Ano X_nY_20ZZ.pdf` | 9 | Nome não segue o padrão numerado da planilha | Edições do **Boletim do RAN** (2014–2018) sem linha própria na aba `Boletim` — a aba só cobre 4 dessas edições. Conteúdo institucional do RAN/ICMBio. |
| `Herpetopan_pan_nordeste.pdf` | 1 | Nome não numerado | Confirmado por leitura do texto: "Boletim Informativo HerpetoPAN — Informativo bimestral do PAN Herpetofauna da Mata Atlântica Nordestina", publicação institucional do RAN/ICMBio. |
| `I_CBH...` a `VII_CBH...` (`Resumos_CBH_2004-2015/*.docx`) | 7 | Não numerados; pré-datam o sistema de numeração da planilha | Confirmado por leitura do texto: são os **anais completos** dos Congressos Brasileiros de Herpetologia 2004–2015 (ex.: o de 2004 tem ~900 mil caracteres), com resumos de autores de todo o Brasil — não apenas do RAN. |
| `126 - Mônico et al, 2026.pdf` | 1 | Nº 126 não existe na planilha | Artigo mais recente que a última atualização da planilha (15/11/2025) — mesma natureza dos demais artigos já catalogados. |

## Observações sobre dados sensíveis

Nenhum arquivo é movido para `03_documentos_autorizados/` por este script, e o conteúdo dos
PDFs/DOCX não é lido durante a catalogação em si (apenas o nome do arquivo e, para detecção
de duplicatas, o hash MD5 dos bytes — não o texto). A revisão manual dos 18 casos acima abriu
alguns arquivos pontualmente para identificar sua natureza; nenhum conteúdo de documento foi
copiado para este repositório além do que já está registrado aqui.

**Avaliação preliminar por grupo** (decisão final de sensibilidade/copyright ainda cabe à
equipe do RAN, conforme [ADR 0002](../decisoes/0002-classificacao-de-sensibilidade-em-pastas.md)):

- **Boletim do RAN / HerpetoPAN / ICMBio em Foco** — publicações próprias do RAN/ICMBio,
  mesma natureza institucional das já classificadas como autorizadas em Monitora/PANs/SALVE.
  Baixo risco de copyright de terceiros; risco de dados sensíveis também baixo (são boletins
  de divulgação, não relatórios técnicos com dados brutos de localização).
- **Artigos, resumos de evento e livros/capítulos com editora/revista externa** (a maioria do
  acervo, incluindo os `casado_faixa`) — têm copyright de uma editora, revista ou sociedade
  científica externa ao ICMBio. Mesmo sendo de autoria de pesquisadores do RAN, redistribuir o
  texto integral num sistema de RAG pode contrariar os termos de uso da publicação original —
  precisa de decisão explícita da equipe (ex.: usar apenas resumo/citação + link/DOI em vez do
  PDF completo).
- **Anais dos Congressos Brasileiros de Herpetologia (`Resumos_CBH_2004-2015/*.docx`)** —
  atenção especial: são volumes completos de congresso nacional, com copyright da Sociedade
  Brasileira de Herpetologia (organizadora) e conteúdo majoritariamente de autores **não
  vinculados ao RAN**. Indexar o volume inteiro tanto foge do escopo do projeto (a maior parte
  do conteúdo não é sobre o trabalho do RAN) quanto levanta uma questão de copyright mais forte
  que a dos demais itens. Recomendação: não indexar o volume inteiro; se houver interesse,
  extrair manualmente apenas os resumos de autoria de pesquisadores do RAN.
- **`placeholder_faltante` (5 arquivos "Faltam")** — não são documentos, apenas marcadores da
  própria equipe indicando lacunas conhecidas no acervo (números 31–35, 56–58, 61–64, 70–71,
  113–114 da aba `Resumo_Evento Científico`). Não entram em nenhuma avaliação de sensibilidade.
- **`duplicata_exata` (5 arquivos)** — cópias byte-a-byte de arquivos já presentes em
  `Matérias_ICMBio-em-Foco_Outros Meios`; mesma classificação do arquivo canônico.

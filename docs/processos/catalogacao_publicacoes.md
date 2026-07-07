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
- Biblioteca padrão (`re`, `json`, `pathlib`) — sem outras dependências

## Como funciona

1. **Lê a planilha**: cada aba tem colunas diferentes (`Autor`/`Autor/es `/`Autores`,
   `Periódico`/`Editora`/`Entidade/Curso/Evento`/`Instituição` etc.) — o script normaliza
   tudo para um formato único (`aba`, `numero`, `tipologia`, `autor`, `ano`, `titulo`,
   `fonte`, `doi`), indexado pelo número da coluna `Nº` de cada linha.
2. **Mapeia pasta → aba da planilha** (tabela fixa `MAPA_PASTA_ABA` no script). Duas pastas
   (`Boletins_RAN-2015 a 2018` e `Matérias_ICMBio-em-Foco_Outros Meios`) apontam para a
   mesma aba `Boletim`, porque a planilha não separa "boletim próprio do RAN" de "matéria
   publicada em veículo de terceiros" em abas distintas.
3. **Percorre os arquivos** de cada pasta mapeada e extrai o número no início do nome
   (regex `^(\d+)\s*-`, ex.: `"12 - Alves Junior et al, 2012.pdf"` → `12`) e o ano, se
   houver um padrão de 4 dígitos no nome.
4. **Casa por número** com a aba correspondente e marca um status por arquivo:

   | Status | Significado |
   |---|---|
   | `casado` | número do arquivo encontrado em exatamente uma linha da aba |
   | `sem_numero_no_nome` | arquivo não começa com um número (ex.: `Boletim_RAN_Ano 2_n3_2015.pdf`) |
   | `numero_nao_encontrado_na_planilha` | tem número, mas não há linha correspondente na aba |
   | `numero_ambiguo_na_planilha` | o número aparece em mais de uma linha da aba |
   | `sem_pasta_mapeada` | pasta sem aba associada (ex.: as subpastas temáticas vazias `anfibios/`, `repteis/` etc.) |

5. **Grava o catálogo** em JSON, com estatísticas por pasta (total de arquivos, quantos
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

| Data | Total de arquivos | Casados automaticamente | Sem correspondência |
|---|---|---|---|
| 2026-07-07 | 312 | 272 | 40 |

Detalhamento por pasta (2026-07-07):

| Pasta | Casados / Total | Aba da planilha |
|---|---|---|
| Artigo, Nota, Comunicação Científica | 94/95 | Artigo,Nota,Comun. Cient. |
| Resumos_Eventos Científicos | 91/110 | Resumo_Evento Científico |
| Livro, Capítulo Livro, Cartilha, Revista, Manual | 24/28 | Liv,Cap.Liv,Cart,Mat.Rev.,Man. |
| Matérias_ICMBio-em-Foco_Outros Meios | 32/33 | Boletim |
| Boletins_RAN-2015 a 2018 | 10/25 | Boletim |
| Monografias_TCC | 8/8 | Monografia_TCC |
| Teses e Dissertações | 10/10 | Dissertação, Tese |
| Outras Publicações Técnicas | 3/3 | Outras publicações |

**Pendências identificadas:**

- Os 40 arquivos sem correspondência automática estão concentrados em
  `Boletins_RAN-2015 a 2018` (arquivos como `Boletim_RAN_Ano 2_n3_2015.pdf`, sem número no
  nome) e em `Resumos_Eventos Científicos/Resumos_CBH_2004-2015` (`.docx` de congressos
  antigos que não constam na planilha) — precisam de matching manual ou de metadados
  digitados à mão.
- `Boletins_RAN-2015 a 2018` e `Matérias_ICMBio-em-Foco_Outros Meios` parecem se sobrepor
  parcialmente (vários arquivos "ICMBio em Foco nº X" aparecem duplicados nas duas pastas) —
  ainda não deduplicado.
- Duas abas da planilha (`2018-2023` e `Relatório Anual do RAN`) não têm pasta de arquivos
  correspondente — a aba `2018-2023` parece ser uma curadoria bibliográfica anterior,
  possivelmente sobreposta com a aba `Artigo,Nota,Comun. Cient.`.

## Observações sobre dados sensíveis

Nenhum arquivo é movido, copiado ou lido por este script além do nome — o conteúdo dos
PDFs/DOCX não é acessado. Os arquivos permanecem em `02_publicacoes_cientificas_ran/`
(fora de `03_documentos_autorizados/`) até que a sensibilidade e o copyright/termos de uso
de cada publicação sejam avaliados (ver Fase 3 do roadmap), conforme
[ADR 0002](../decisoes/0002-classificacao-de-sensibilidade-em-pastas.md).

# Extração de texto das fichas SALVE

- **Status:** ✅ Em produção (extração completa — 2086/2086 fichas)
- **Última atualização:** 2026-07-06
- **Responsável(eis):** Script `scripts/processamento/extrair_texto_salve.py`

## Objetivo

Converter os metadados brutos das fichas de espécies do SALVE (JSON com HTML e campos
estruturados) em texto plano organizado por seção, pronto para a etapa de chunking.
Diferente dos PDFs do Monitora/PANs, as fichas SALVE já chegam como JSON via API —
não há PDF para extrair, mas há HTML para limpar e tabelas para serializar.

## Entradas

- `01_fontes_web/salve/fichas/<slug>/metadados.json` — um por espécie
- Coletados pelo script `scripts/coleta/coleta_salve.py`

## Saídas

- `07_processados/textos_extraidos/salve/<slug>.json` — um por espécie

> **Nota:** esses arquivos **estão versionados no git** (ao contrário dos textos de PDFs),
> porque as fichas-fonte JSON também estão no git.

Estrutura de cada JSON de saída:
```json
{
  "slug": "acanthochelys-macrocephala-...",
  "id_ficha": "...",
  "nome_cientifico": "Acanthochelys macrocephala (...)",
  "nome_cientifico_atual": "...",
  "nome_comum": "Tartaruga-do-pantanal",
  "grupo": "Répteis",
  "categoria_risco": "VU",
  "categoria_risco_completa": "Vulnerável (VU)",
  "bioma": "Cerrado, Pantanal",
  "estados": "Mato Grosso, Mato Grosso do Sul",
  "doi": "10.37002/salve.ficha.20244.3",
  "url_origem": "https://salve.icmbio.gov.br/...",
  "data_coleta": "2026-06-25",
  "secoes": {
    "visao_geral": "Justificativa da avaliação: ...",
    "taxonomia": "Reino: Animalia | Filo: Chordata | ...",
    "distribuicao": "Endêmica do Brasil: Não\nEstados: ...",
    "historia_natural": "...",
    "populacao": "Tempo geracional: 17.50 Ano(s)\n...",
    "ameacas": "...",
    "uso": "...",
    "conservacao": "...",
    "pesquisa": "...",
    "referencias": "..."
  }
}
```

## Ferramentas

- **BeautifulSoup4** + **lxml** — limpeza de HTML nas seções narrativas
- Serialização manual de campos estruturados (árvore taxonômica, tabelas de ameaças,
  histórico de avaliações, UCs, ações de conservação)

```bash
source venv/bin/activate
pip install beautifulsoup4 lxml  # já incluídas no requirements.txt
```

## O que o script faz por seção

| Seção interna | Campo(s) da API | Tratamento |
|---|---|---|
| `visao_geral` | `header.justificative`, `authorship`, `citation` | HTML → texto; join |
| `taxonomia` | `taxonomicClassification.tree`, `oldNames`, `commonNames` | Árvore → "Reino: X \| Filo: Y \| ..." |
| `distribuicao` | `distribution.*` | HTML + campos planos; join com rótulos |
| `historia_natural` | `naturalHistory.description`, `foodHabit`, `reproduction` | HTML + tabelas → texto |
| `populacao` | `population.*` | Campos planos + HTML |
| `ameacas` | `threats.description`, `threats.table` | HTML + lista de categorias IUCN |
| `uso` | `uses.description`, `uses.table` | HTML + lista |
| `conservacao` | `conservation.*` | HTML + histórico de avaliações + UCs + ações |
| `pesquisa` | `research.description`, `research.table` | HTML + lista de temas |
| `referencias` | `bibliographicReferences.table.refsTaxon` | Lista de HTML → texto limpo |

## Passo a passo

```bash
source venv/bin/activate
python scripts/processamento/extrair_texto_salve.py
```

O script descobre automaticamente todas as fichas em
`01_fontes_web/salve/fichas/*/metadados.json` e gera um JSON por espécie.

### Verificar progresso / resultado
```bash
# Quantas fichas foram extraídas
ls 07_processados/textos_extraidos/salve/ | wc -l

# Inspecionar uma ficha
python3 -c "
import json
from pathlib import Path
d = json.loads(Path('07_processados/textos_extraidos/salve/<slug>.json').read_text())
for s, t in d['secoes'].items():
    print(f'[{s}] {len(t)} chars')
"
```

## Frequência de execução

Após cada coleta do SALVE (`coleta_salve.py`). A coleta completa é semestral;
a extração deve ser rodada logo em seguida, sobre as fichas novas/atualizadas.

Para reprocessar apenas fichas novas (sem sobrescrever as existentes), o script
pode ser adaptado com verificação de existência do arquivo de saída — atualmente
regrava todas as fichas encontradas.

## Resultados das execuções

| Data | Fichas disponíveis | Extraídas | Erros |
|---|---|---|---|
| 2026-06-25 | 24 (teste) | 24 | 0 |
| 2026-07-06 | 2086 (coleta completa) | 2086 | 0 |

Todas as 2086 fichas extraídas foram copiadas para `03_documentos_autorizados/salve/`
(ver [ADR 0002](../decisoes/0002-classificacao-de-sensibilidade-em-pastas.md) e a seção
"Observações sobre dados sensíveis" abaixo) e já foram chunkadas por
`gerar_chunks.py` (20.069 chunks — ver [`docs/roadmap.md`](../roadmap.md), Fase 4.1).

## Observações sobre dados sensíveis

As fichas SALVE são documentos públicos do ICMBio, disponíveis abertamente em
`salve.icmbio.gov.br`. Não contêm coordenadas precisas de ocorrência (apenas
estados e biomas) — sem risco de sensibilidade geográfica. Conteúdo considerado
autorizado para indexação.

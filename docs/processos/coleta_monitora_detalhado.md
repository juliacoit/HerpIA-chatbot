# Coleta do Programa Monitora

- **Status:** Em produção
- **Última atualização:** 2026-06-23
- **Responsável(eis):** Script automatizado (`scripts/coleta/coleta_monitora.py`)
- **Última execução:** 2026-06-23 — 8 categorias coletadas, 163 documentos indexados

## Objetivo

Coletar e indexar **metadados estruturados** das 8 categorias de conteúdo do Programa Monitora do ICMBio (Materiais de Apoio, Artigos, Estrutura do Programa, Relatórios, Dados, Livros/Monografias/Dissertações/Teses, Legislação, Encontro dos Saberes). O processo extrai, para cada categoria:

- **Título e seções de conteúdo**, quando a página as tiver.
- **Documentos linkados**: PDFs, planilhas, apresentações, e outros formatos (ver lista de extensões abaixo).
- **Contexto de cada documento**: seção de origem (quando houver), tipo e data de modificação (na categoria Dados).

Essas informações são salvas em JSON estruturado, no mesmo formato usado para os PANs (ver `coleta_pans_detalhado.md`), para que o pipeline de extração de texto e chunking trate as duas fontes de forma uniforme.

## Diferença em relação à coleta dos PANs

Os PANs têm uma única página de listagem com ~74 subpáginas descobertas por crawling, todas seguindo o mesmo padrão de HTML (`<p class="callout">` agrupando conteúdo e documentos). O Monitora não tem uma listagem central: são **8 URLs fixas**, conhecidas de antemão, e a inspeção do HTML bruto de cada uma (2026-06-23) revelou **três padrões estruturais diferentes**:

| Padrão | Categorias | Estrutura |
|---|---|---|
| `secoes` | Materiais de Apoio, Artigos, Livros, Encontro dos Saberes | `<p class="callout">Título</p>` agrupando links — mesmo padrão dos PANs. Aqui os links ficam dentro de tabelas de layout (imagem + texto), com links decorativos duplicados que precisam ser deduplicados por URL na etapa de download. |
| `flat` | Estrutura do Programa, Relatórios, Legislação | Links diretos a arquivos no corpo do texto, sem `callout` agrupando. Tratado como caso particular de `secoes` (sem seções) — a mesma função de extração de documentos cobre os dois casos. |
| `listagem` | Dados | Listagem de pasta do Plone (`<table class="listing">`), com colunas Título/Tipo/Data de modificação. Os links de título terminam em `/view` em vez da extensão do arquivo (ex.: `arquivo.xlsx/view`); o script remove esse sufixo para chegar à URL real do arquivo. |

O script detecta automaticamente qual padrão cada página usa (primeiro verifica se há `<table class="listing">`; senão, tenta agrupar por `callout`; o resultado vazio nesse segundo caso indica o padrão `flat`) — não é necessário indicar manualmente.

## Entradas

- **8 URLs fixas de categoria**, definidas em `CATEGORIAS` dentro do próprio script (não há crawling de uma listagem, como ocorre nos PANs).

## Saídas

```
01_fontes_web/monitora/
├── _indice_monitora.json                # Índice geral + painéis Power BI não coletados
├── materiais-de-apoio/
│   └── metadados.json
├── artigos/
│   └── metadados.json
├── estrutura-do-programa/
│   └── metadados.json
├── relatorios/
│   └── metadados.json
├── dados/
│   └── metadados.json
├── livros/
│   └── metadados.json
├── legislacao/
│   └── metadados.json
└── encontro-dos-saberes/
    └── metadados.json
```

### Estrutura de `_indice_monitora.json`

```json
{
  "categorias": [
    {
      "nome": "Materiais de Apoio",
      "slug": "materiais-de-apoio",
      "url": "https://www.gov.br/icmbio/pt-br/assuntos/monitoramento/conteudo/Materiais-de-Apoio",
      "data_coleta": "2026-06-23",
      "padrao": "secoes",
      "total_documentos": 94
    },
    ...
  ],
  "paineis_powerbi_nao_coletados": [
    {
      "nome": "Painel de dados gerenciais do Programa Monitora",
      "url": "https://app.powerbi.com/view?r=...",
      "motivo": "SPA do Power BI, sem HTML estático; dados exigiriam exportação manual ou descoberta de API."
    },
    {
      "nome": "Painel Interativo Relatório Florestal",
      "url": "https://www.gov.br/icmbio/pt-br/assuntos/monitoramento/painel-interativo-relatorio-florestal-1",
      "motivo": "Página gov.br que embute painel Power BI; mesmo motivo do painel gerencial."
    }
  ]
}
```

### Estrutura de cada `metadados.json` (exemplo: `dados/metadados.json`, padrão `listagem`)

```json
{
  "nome": "Dados",
  "slug": "dados",
  "url": "https://www.gov.br/icmbio/pt-br/assuntos/monitoramento/conteudo/dados",
  "data_coleta": "2026-06-23",
  "titulo": "Dados",
  "padrao": "listagem",
  "secoes": {},
  "documentos": [
    {
      "texto_link": "Base de dados painel UCs Programa Monitora_26",
      "contexto": "Arquivo",
      "url": "https://www.gov.br/icmbio/pt-br/assuntos/monitoramento/conteudo/dados/base-de-dados-painel-ucs-programa-monitora_25.xlsx",
      "nome_arquivo": "base-de-dados-painel-ucs-programa-monitora_25.xlsx",
      "extensao": "xlsx",
      "data_modificacao": "12/05/2026 18h22"
    }
  ]
}
```

## Ferramentas

- **Python 3.10+**
- **requests** — requisições HTTP às 8 páginas de categoria
- **BeautifulSoup4** + **lxml** — parsing HTML

## Resultado da última execução (2026-06-23)

✅ **Sucesso completo**

| Categoria | Padrão detectado | Documentos |
|---|---|---|
| Materiais de Apoio | `secoes` | 94 |
| Artigos | `secoes` | 27 |
| Estrutura do Programa | `flat` | 1 |
| Relatórios | `flat` | 10 |
| Dados | `listagem` | 2 |
| Livros | `secoes` | 13 |
| Legislação | `flat` | 6 |
| Encontro dos Saberes | `secoes` | 10 |

**Total:** 163 documentos indexados (apenas metadados/URLs — nenhum arquivo baixado nesta etapa).

Validação pontual: a URL de um item do padrão `listagem` (`base-de-dados-painel-ucs-programa-monitora_25.xlsx`, sem o sufixo `/view`) foi testada com `curl -I` e devolveu `content-type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` — confirma que o arquivo real é servido nessa URL, sem necessidade de tratamento especial na etapa de download.

## Passo a passo para executar

```bash
cd chatbot-ran-icmbio
source venv/Scripts/activate  # Windows (PowerShell: venv\Scripts\Activate.ps1)
# ou
source venv/bin/activate      # Linux/macOS

python scripts/coleta/coleta_monitora.py
python scripts/coleta/coleta_monitora.py --atraso 2.0   # mais educado com o servidor
```

## Próximos passos

1. **Baixar os documentos**: adaptar (ou generalizar) `download_documentos_pans.py` para também ler `01_fontes_web/monitora/*/metadados.json`.
2. **Classificação de sensibilidade**: os 163 documentos são públicos (mesma natureza dos PANs), mas ainda não passaram pela triagem formal antes de mover para `03_documentos_autorizados/`.
3. **Extração de texto e chunking**: mesmo pipeline planejado para os PANs (PyMuPDF + Tesseract OCR como fallback).
4. **Investigar os 2 painéis Power BI**: avaliar se há exportação manual viável, ou se ficam permanentemente fora da base de conhecimento.

## Relacionados

- Análise técnica original (todas as fontes web): [`coleta_fontes_web.md`](coleta_fontes_web.md)
- Padrão de coleta equivalente para os PANs: [`coleta_pans_detalhado.md`](coleta_pans_detalhado.md)

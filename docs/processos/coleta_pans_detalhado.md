# Coleta de Planos de Ação Nacional (PANs)

- **Status:** Em produção
- **Última atualização:** 2026-06-17
- **Responsável(eis):** Script automatizado (`scripts/coleta/coleta_pans.py`)
- **Última execução:** 2026-06-17 — 74 PANs coletados, 1.141 documentos indexados

## Objetivo

Coletar e indexar **metadados estruturados** de todos os Planos de Ação Nacional para Conservação de Espécies Ameaçadas de Extinção (PANs) do ICMBio. O processo extrai:

- **Metadados de cada PAN**: nome, URL, status (em execução/finalizado), data de vigência/ciclo
- **Seções de conteúdo**: resumo, contexto, estratégia, bioma, instituições responsáveis
- **Documentos anexados**: PDFs (portarias, sumários executivos, livros), planilhas (matrizes de planejamento/monitoramento/avaliação)
- **Contexto de cada documento**: seção de origem, número do ciclo, extensão de arquivo

Essas informações são salvas em formato JSON estruturado, servindo como **fonte de referência para o RAG** — permite recuperação semântica de documentos e resposta a perguntas sobre ações de conservação, espécies ameaçadas e metas de ciclos anteriores e atuais.

## Entradas

- **URL única da listagem**: `https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan`
  - Página HTML tradicional (gov.br), sem renderização JavaScript — webscraping simples é suficiente

## Saídas

```
01_fontes_web/pans/
├── _indice_pans.json                           # Índice geral (lista resumida de todos os PANs)
├── pan-albatrozes-e-petreis/
│   └── metadados.json                          # Detalhe completo do PAN
├── pan-alto-parana/
│   └── metadados.json
├── pan-arara-azul-de-lear/
│   └── metadados.json
├── pan-aves-da-amazonia/
│   └── metadados.json
├── pan-aves-de-rapina/
│   └── metadados.json
├── pan-grandes-felinos/
│   └── metadados.json
└── ... (74 PANs ao total)
```

### Estrutura de `_indice_pans.json`

Arquivo JSON com lista resumida de todos os PANs coletados:

```json
[
  {
    "nome": "Albatrozes e Petréis",
    "slug": "pan-albatrozes-e-petreis",
    "url": "https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-albatrozes-e-petreis",
    "status": "em_execucao",
    "data_coleta": "2026-06-17",
    "total_documentos": 25
  },
  {
    "nome": "Ariranha",
    "slug": "pan-ariranha",
    "url": "https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-ariranha",
    "status": "em_execucao",
    "data_coleta": "2026-06-17",
    "total_documentos": 22
  },
  ...
]
```

### Estrutura de cada `metadados.json` (exemplo: `pan-albatrozes-e-petreis/metadados.json`)

```json
{
  "nome": "Albatrozes e Petréis",
  "slug": "pan-albatrozes-e-petreis",
  "url": "https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-albatrozes-e-petreis",
  "status": "em_execucao",
  "data_coleta": "2026-06-17",
  "titulo": "Plano de Ação Nacional para a Conservação dos Albatrozes e Petréis",
  "secoes": {
    "RESUMO": "Albatrozes e petréis são aves migratórias que frequentam a costa brasileira...",
    "ESPÉCIES-ALVO": "O PLANACAP contempla 12 espécies-alvo, dentre as quais 7 são nacionalmente ameaçadas de extinção...",
    "VIGÊNCIA": "2025-2030 (4º ciclo)\n2018-2023 (3º ciclo)\n2012-2017 (2º ciclo)\n2006-2011 (1º ciclo)",
    "BIOMA": "Marinho",
    "CENTROS RESPONSÁVEIS": "...",
    "DOCUMENTOS": "Sumário Executivo, Portaria do PAN, Matriz de Planejamento, Matriz de Monitoria, Matriz de Avaliação"
  },
  "documentos": [
    {
      "texto_link": "Portaria do PAN",
      "contexto": "Portaria do PAN",
      "url": "https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-albatrozes-e-petreis/4-ciclo/20241219-pan-albatrozes-e-petreis-portaria-aprovacao.pdf",
      "nome_arquivo": "20241219-pan-albatrozes-e-petreis-portaria-aprovacao.pdf",
      "extensao": "pdf",
      "ciclo": "4"
    },
    {
      "texto_link": "Matriz de Planejamento",
      "contexto": "Matriz de Planejamento",
      "url": "https://www.gov.br/icmbio/pt-br/assuntos/biodiversidade/pan/pan-albatrozes-e-petreis/4-ciclo/20260408-planacap-matriz-planejamento-site.xlsx",
      "nome_arquivo": "20260408-planacap-matriz-planejamento-site.xlsx",
      "extensao": "xlsx",
      "ciclo": "4"
    },
    ...
  ]
}
```

## Ferramentas

- **Python 3.10+** — linguagem principal
- **requests** — fazer requisições HTTP à página de listagem e páginas de cada PAN
- **BeautifulSoup4** — parser HTML, extração de elementos (tags, classes, atributos)
- **lxml** — backend de parsing (mais rápido que html.parser)

## Funcionamento técnico detalhado

### Fluxo geral

```
┌─ Visita listagem (https://...biodiversidade/pan)
│  ├─ Extrai lista de ~74 PANs (separando "em_execucao" vs "finalizado")
│  ├─ Para cada PAN:
│  │  ├─ Visita página dedicada (ex: /pan-albatrozes-e-petreis/)
│  │  ├─ Extrai título da página
│  │  ├─ Extrai seções de conteúdo (agrupadas por títulos com classe "callout")
│  │  ├─ Extrai lista de documentos (PDFs, XLSXs, DOCXs, ZIPs)
│  │  ├─ Detecta número do ciclo em URLs (ex: "/3-ciclo/")
│  │  └─ Salva tudo em JSON
│  └─ Espera N segundos antes do próximo (respeita servidor)
└─ Salva índice geral com contagem de documentos
```

### Funções principais do script

#### 1. **`buscar_html(url: str) -> BeautifulSoup`**

Faz requisição HTTP com tratamento de falhas:

- **Tentativas**: até 3 vezes se falhar (timeout, conexão, erro HTTP)
- **Espera exponencial**: 2s, 4s, 6s entre tentativas
- **Encoding**: força UTF-8 para caracteres acentuados
- **User-Agent**: identifica-se como bot educacional/uso interno

```python
# Exemplo interno:
try:
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()  # Erro se 4xx/5xx
    resp.encoding = "utf-8"
    return BeautifulSoup(resp.text, "lxml")
except requests.RequestException as erro:
    # Retry com sleep
```

#### 2. **`slug_da_url(url: str) -> str`**

Extrai identificador da URL para usar como nome de pasta:

```python
# Exemplo:
# Input:  "https://...biodiversidade/pan/pan-albatrozes-e-petreis/"
# Output: "pan-albatrozes-e-petreis"
```

#### 3. **`listar_pans(soup: BeautifulSoup) -> list[dict]`**

Extrai lista de PANs da página de listagem. A página **não tem estrutura HTML clara** (seções aninhadas), então o script rastreia manualmente o estado:

- Encontra parágrafos contendo "PANS EM EXECUÇÃO" / "PANS FINALIZADOS" / "SAIBA MAIS"
- Marca status conforme lê
- Coleta links com classe `govbr-card-content` enquanto status está ativo
- Pula links que apontam para "/saiba-mais/" (links adicionais, não PANs)

**Saída esperada:**
```json
[
  {
    "nome": "Albatrozes e Petréis",
    "slug": "pan-albatrozes-e-petreis",
    "url": "https://...",
    "status": "em_execucao"
  },
  ...
]
```

#### 4. **`extrair_secoes(content: BeautifulSoup) -> dict`**

Agrupa conteúdo de texto por seção dentro de uma página de PAN. Usa como marcadores parágrafos com classe `callout`:

- Identifica `<p class="callout">TÍTULO</p>` como início de seção
- Coleta `<p>`, `<table>`, `<dl>` subsequentes até o próximo título
- Extrai texto limpo (sem tags HTML) e agrupa por seção

**Saída esperada:**
```json
{
  "RESUMO": "Albatrozes e petréis são aves migratórias...",
  "ESPÉCIES-ALVO": "O PLANACAP contempla 12 espécies-alvo...",
  "VIGÊNCIA": "2025-2030 (4º ciclo)...",
  "DOCUMENTOS": "..."
}
```

#### 5. **`extrair_documentos(content: BeautifulSoup, url_pagina: str) -> list[dict]`**

Localiza e indexa todos os documentos anexados:

- Procura por links (`<a href>`) que apontam para `.pdf`, `.xlsx`, `.docx`, `.zip`
- Converte URLs relativas em absolutas (`urljoin`)
- Detecta número do ciclo usando regex: `r"/(\d+)-ciclo/"` (ex: "/4-ciclo/" → ciclo "4")
- Captura contexto de cada link (elemento pai: `<tr>`, `<li>`, `<p>`, `<dd>`)
- Extrai nome e extensão do arquivo

**Saída esperada:**
```json
[
  {
    "texto_link": "Portaria do PAN",
    "contexto": "Portaria do PAN",
    "url": "https://www.gov.br/.../20241219-pan-albatrozes-e-petreis-portaria-aprovacao.pdf",
    "nome_arquivo": "20241219-pan-albatrozes-e-petreis-portaria-aprovacao.pdf",
    "extensao": "pdf",
    "ciclo": "4"
  },
  ...
]
```

#### 6. **`extrair_detalhe(soup: BeautifulSoup, url_pagina: str) -> dict`**

Orquestra extração de uma página de PAN:

- Localiza `<div id="content">` (container principal)
- Extrai título (primeiro `<h1>` ou `<h2>`)
- Chama `extrair_secoes()` e `extrair_documentos()`

**Saída esperada:**
```json
{
  "titulo": "Plano de Ação Nacional para a Conservação dos Albatrozes e Petréis",
  "secoes": { ... },
  "documentos": [ ... ]
}
```

#### 7. **`coletar(limite: int | None, atraso: float) -> list[dict]`**

Função principal de orquestração:

1. Baixa página de listagem e extrai ~74 PANs
2. Se `--limite` foi passado, toma apenas os N primeiros (útil para testes)
3. Cria diretório `01_fontes_web/pans/` se não existir
4. **Para cada PAN:**
   - Visita página dedicada
   - Extrai detalhe (título, seções, documentos)
   - Cria subpasta com slug do PAN
   - Salva `metadados.json` com dados completos
   - Aguarda N segundos antes do próximo (padrão: 1.0s)
5. Salva `_indice_pans.json` com lista resumida e contagem

**Tempo esperado:** ~120-150 segundos para os 74 PANs (1-2s por PAN, incluindo download)

#### 8. **`main()`**

Interpreta argumentos de linha de comando:

```bash
# Coletar todos os PANs
python scripts/coleta/coleta_pans.py

# Testar com apenas 5 PANs
python scripts/coleta/coleta_pans.py --limite 5

# Aumentar espera entre requisições
python scripts/coleta/coleta_pans.py --atraso 2.0

# Combinar
python scripts/coleta/coleta_pans.py --limite 10 --atraso 1.5
```

## Passo a passo para executar

### Pré-requisitos

```bash
# Estar no diretório do projeto
cd chatbot-ran-icmbio

# Ativar venv (se ainda não)
source venv/Scripts/activate  # Windows (PowerShell: venv\Scripts\Activate.ps1)
# ou
source venv/bin/activate      # Linux/macOS

# Instalar dependências
pip install -r requirements.txt
```

### Execução

```bash
# Coleta completa (todos os 74 PANs)
python scripts/coleta/coleta_pans.py

# Teste rápido (apenas 5 PANs)
python scripts/coleta/coleta_pans.py --limite 5

# Coleta com espera maior (educado com servidor)
python scripts/coleta/coleta_pans.py --atraso 2.0
```

### Verificação de resultados

```bash
# Verificar índice geral
cat 01_fontes_web/pans/_indice_pans.json | head -50

# Listar pastas de PANs coletadas
ls -la 01_fontes_web/pans/ | grep "^d"

# Verificar metadados de um PAN específico
cat 01_fontes_web/pans/pan-albatrozes-e-petreis/metadados.json | head -30

# Contar total de documentos coletados
python -c "import json; data = json.load(open('01_fontes_web/pans/_indice_pans.json', encoding='utf-8')); print(sum(p['total_documentos'] for p in data))"
```

## Última execução (2026-06-17)

✅ **Sucesso completo**

- **Total de PANs coletados:** 74
- **Status distribuição:** ~40 em execução, ~34 finalizados
- **Total de documentos indexados:** 1.141
- **Tempo decorrido:** ~2 minutos
- **Tamanho total de metadados:** ~20 KB (apenas JSON estruturado, sem PDFs)

### Estatísticas por tipo de documento

Baseado no índice gerado:

- **PDFs**: portarias, sumários executivos, livros de ciclos anteriores
- **XLSXs**: matrizes de planejamento, monitoria, avaliação
- **ZIPs**: arquivos de histórico de ciclos anteriores

### Arquivos gerados

```
01_fontes_web/pans/
├── _indice_pans.json                       (20 KB)
├── pan-albatrozes-e-petreis/metadados.json (68 KB)
├── pan-alto-parana/metadados.json          (30 KB)
├── pan-arara-azul-de-lear/metadados.json   (22 KB)
├── pan-aves-da-amazonia/metadados.json     (35 KB)
├── ... (e assim por diante para todos os 74 PANs)
```

## Frequência de execução

- **Atual:** Manual (sob demanda)
- **Recomendado:** **Semestral** (conforme ciclos de PANs são atualizados no ICMBio)
- **Triggers potenciais:** Quando houver lançamento de novo ciclo de PAN, ou reavaliação de espécies ameaçadas

## Observações sobre dados sensíveis

O script coleta **apenas metadados públicos** do site governamental:

- ✅ Texto de descrições de PANs e estratégias — **público, citável**
- ✅ Títulos e contexto de documentos — **público, citável**
- ✅ URLs de documentos — **públicas, acessíveis**
- ❌ **Documentos PDF/XLSX em si não são baixados** — apenas URLs e metadados são armazenados

### Checklist de segurança

- [x] Nenhum documento completo é salvo (apenas URLs)
- [x] Nenhuma chave de API ou credencial é necessária (acesso público)
- [x] User-Agent identifica propósito educacional/interno
- [x] Espera entre requisições respeita servidor
- [x] Dados são UTF-8 validados

## Próximos passos

1. **Baixar PDFs**: Criar script que baixe os PDFs/XLSXs referenciados em `metadados.json` para `03_documentos_autorizados/pans/`
2. **Extração de texto**: Implementar pipeline PyMuPDF + Tesseract OCR para extrair texto de PDFs
3. **Chunking**: Dividir textos extraídos em chunks semanticamente significativos
4. **Embeddings**: Gerar embeddings (OpenAI, Cohere, ou local) para busca semântica
5. **Validação**: Testar recuperação semântica em perguntas sobre PANs (ex: "Qual é o status da tartaruga-marinha?")

## Relacionados

- Análise técnica original: [`docs/processos/coleta_fontes_web.md`](coleta_fontes_web.md)
- Decisão sobre stack: [`docs/decisoes/0001-stack-tecnologica-inicial.md`](../decisoes/0001-stack-tecnologica-inicial.md)
- Classificação de sensibilidade: [`docs/decisoes/0002-classificacao-de-sensibilidade-em-pastas.md`](../decisoes/0002-classificacao-de-sensibilidade-em-pastas.md)

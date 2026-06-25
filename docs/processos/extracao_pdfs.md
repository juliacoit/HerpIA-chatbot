# Extração de texto de PDFs (Monitora e PANs)

- **Status:** ✅ Em produção
- **Última atualização:** 2026-06-25
- **Responsável(eis):** Script `scripts/processamento/extrair_texto_pdfs.py`

## Objetivo

Extrair o texto dos PDFs coletados do Programa Monitora e dos PANs, página por página,
gerando um JSON por arquivo com o texto limpo e metadados de extração. Os JSONs resultantes
alimentam a etapa de chunking do pipeline RAG.

## Entradas

- PDFs em `01_fontes_web/monitora/*/documentos/` (incluindo subpastas)
- PDFs em `01_fontes_web/pans/*/documentos/` (incluindo subpastas `ciclo-1/`, `ciclo-2/`)
- `metadados.json` de cada categoria/PAN (para enriquecer a saída com URL e contexto)

## Saídas

- `07_processados/textos_extraidos/monitora/<categoria>/<nome>.json`
- `07_processados/textos_extraidos/pans/<slug>/[ciclo-N/]<nome>.json`

> **Nota:** esses diretórios estão no `.gitignore` — são regeneráveis a partir dos PDFs.
> Os PDFs também estão no `.gitignore` (`01_fontes_web/**/documentos/`).

Estrutura de cada JSON de saída:
```json
{
  "fonte": "pans",
  "subdir": "pan-herpetofauna-do-sudeste",
  "nome_arquivo": "pan-herpetofauna-do-sudeste-sumario.pdf",
  "url_origem": "https://...",
  "contexto": "Sumário Executivo",
  "ciclo": "1",
  "num_paginas": 95,
  "paginas_sem_texto": [],
  "provavelmente_escaneado": false,
  "metodo_extracao": "texto",
  "data_extracao": "2026-06-25",
  "paginas": [{"pagina": 1, "texto": "..."}, ...],
  "texto_completo": "[Página 1]\n...\n\n[Página 2]\n..."
}
```

## Ferramentas

- **PyMuPDF** (`fitz`) — extração direta da camada de texto de PDFs nativos
- **Tesseract OCR** (`tesseract-ocr`, `tesseract-ocr-por`) + **pytesseract** — fallback para PDFs escaneados
- **Pillow** — renderização de páginas como imagem para o OCR

Instalação:
```bash
# Sistema
sudo apt install tesseract-ocr tesseract-ocr-por

# Venv
source venv/bin/activate
pip install pymupdf pytesseract pillow
```

## Passo a passo

### Execução padrão (sem OCR)
```bash
source venv/bin/activate
python scripts/processamento/extrair_texto_pdfs.py
```
Processa ambas as fontes. PDFs escaneados são sinalizados mas não extraídos.

### Apenas uma fonte
```bash
python scripts/processamento/extrair_texto_pdfs.py --fonte monitora
python scripts/processamento/extrair_texto_pdfs.py --fonte pans
```

### Com OCR (requer Tesseract instalado)
```bash
python scripts/processamento/extrair_texto_pdfs.py --ocr
```
Ativa fallback OCR para páginas com menos de 50 caracteres extraídos.

### Reprocessar arquivos já extraídos
```bash
python scripts/processamento/extrair_texto_pdfs.py --ocr --reprocessar
```
Útil após instalar o Tesseract para reprocessar os PDFs escaneados identificados na
primeira rodada.

### Verificar progresso
```bash
find 07_processados/textos_extraidos/pans -name "*.json" | wc -l
find 07_processados/textos_extraidos/monitora -name "*.json" | wc -l
```

## Resultados da execução de 2026-06-25

| Fonte | PDFs | Processados | Escaneados (OCR) | Erros |
|---|---|---|---|---|
| Monitora | 109 | 109 | 0 | 0 |
| PANs | 707 | 707 | 47 | 0 |
| **Total** | **816** | **816** | **47** | **0** |

Os 47 PDFs escaneados foram reprocessados com OCR após instalação do Tesseract no mesmo dia.

## Detecção de PDFs escaneados

Uma página é considerada sem texto quando contém menos de 50 caracteres após extração.
Se mais de 50% das páginas de um PDF estão nessa condição, ele é marcado como
`provavelmente_escaneado: true` e, com `--ocr`, é reprocessado página a página via OCR.

## Frequência de execução

Sob demanda — na atualização semestral da base de conhecimento, após novos PDFs serem
baixados pelos scripts de coleta.

## Observações sobre dados sensíveis

O script processa os arquivos de `01_fontes_web/` (Monitora e PANs), que são fontes
públicas do ICMBio. Documentos de `04_documentos_pendentes_avaliacao/` e
`05_documentos_sensiveis_nao_indexar/` **não são processados** por este script —
exigem avaliação manual antes de qualquer extração.

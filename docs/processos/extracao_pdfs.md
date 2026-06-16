# Extração de PDFs

- **Status:** A definir
- **Última atualização:** 2026-06-16
- **Responsável(eis):**

## Objetivo

Extrair o texto de publicações científicas e demais documentos em PDF (artigos, estudos técnicos, relatórios, capítulos, materiais institucionais) para que possam ser processados pelo pipeline de RAG.

## Entradas

- PDFs autorizados em `03_documentos_autorizados/` (nunca de `04_documentos_pendentes_avaliacao/` ou `05_documentos_sensiveis_nao_indexar/`).

## Saídas

- Texto extraído salvo em `07_processados/textos_extraidos/`.

## Ferramentas

- **PyMuPDF** para extração de texto de PDFs nativos.
- **Tesseract OCR** como fallback para PDFs escaneados (sem camada de texto).

## Passo a passo

A definir.

## Frequência de execução

A definir — provavelmente acoplada à atualização semestral da base de conhecimento.

## Observações sobre dados sensíveis

Este processo só deve operar sobre documentos já presentes em `03_documentos_autorizados/`. Qualquer PDF em `04_*` ou `05_*` está fora do escopo deste processo até ser reclassificado.

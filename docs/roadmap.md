# Roadmap do projeto — Chatbot RAG RAN/ICMBio

Documento de referência para todas as fases, tarefas e processos do projeto,
do estado atual até o protótipo funcional validado com usuários.

**Atualizado em:** 2026-07-03

---

## Status geral

```
[Fase 1] Coleta de dados          ███████░░░  70% — SALVE incompleto; publicações pendentes; SEI catalogado
[Fase 2] Extração de texto        ███████░░░  70% — PDFs Monitora/PANs extraídos (816/816); SALVE testado (24 fichas), aguardando coleta completa
[Fase 3] Classificação            ░░░░░░░░░░   0% — nenhum documento avaliado
[Fase 4] Chunking                 ████████░░  80% — 39.242 chunks (monitora, PANs, SALVE); SEI pendente (autorização Fase 1.5)
[Fase 5] Embeddings + Qdrant      ░░░░░░░░░░   0%
[Fase 6] Backend RAG (FastAPI)    ░░░░░░░░░░   0%
[Fase 7] Interface (Streamlit)    ░░░░░░░░░░   0%
[Fase 8] Validação com usuários   ░░░░░░░░░░   0%
```

---

## Fase 1 — Coleta de dados

### 1.1 Programa Monitora
- [x] Script de coleta de metadados (`scripts/coleta/coleta_monitora.py`)
- [x] Script de download de documentos (`scripts/coleta/download_documentos_monitora.py`)
- [ ] **Executar download completo** de todos os documentos listados nos metadados
  - Saída esperada: `01_fontes_web/monitora/documentos/`
  - Verificar relatório de download (`relatorio_download.json`) após execução

### 1.2 PANs (Planos de Ação Nacional)
- [x] Script de coleta de metadados (`scripts/coleta/coleta_pans.py`)
- [x] Script de download de documentos (`scripts/coleta/download_documentos_pans.py`)
- [ ] **Executar download completo** de todos os documentos listados nos metadados
  - Saída esperada: `01_fontes_web/pans/documentos/`

### 1.3 SALVE
- [x] Script de coleta implementado (`scripts/coleta/coleta_salve.py`)
- [x] Coleta de teste validada (3 fichas — 2026-06-24)
- [ ] **Executar coleta completa** (~2086 fichas de répteis e anfíbios)
  ```bash
  source venv/bin/activate
  python scripts/coleta/coleta_salve.py --atraso 1.0
  ```
  - Estimativa: 4–6 horas (~23 mil requisições com atraso de 1s)
  - Saída: `01_fontes_web/salve/fichas/<slug>/metadados.json` + `_indice_salve.json`
  - Rodar com `--atraso 0.5` se a API tolerar; manter 1.0 se houver erros 429

### 1.4 Publicações científicas do RAN
- [ ] **Definir critérios de inclusão** (quais publicações entram no acervo inicial?)
  - Proposta: publicações dos pesquisadores listados no site do RAN/ICMBio, com foco em herpetofauna brasileira
- [ ] **Organizar PDFs** nas subpastas de `02_publicacoes_cientificas_ran/` (anfibios, repteis, conservacao, monitoramento, outros)
- [ ] Catalogar no inventário (`06_inventario/inventario_fontes.xlsx`)
- [ ] Avaliar sensibilidade de cada publicação antes de mover para `03_documentos_autorizados/`

### 1.5 SEI/ICMBio
- [x] **Login automatizado** via Python (requests + BeautifulSoup) com autenticação SIP (`listar_blocos_sei.py`)
- [x] **43 blocos internos catalogados** com todos os processos (`01_fontes_web/sei/blocos_internos.json`)
- [x] **Classificação de relevância** dos 464 processos nos blocos prioritários: ~194 técnicos, ~75 admin, ~195 a avaliar
- [x] **Script de catalogação de documentos** por processo (`scripts/coleta/listar_documentos_sei.py`) — extrai títulos de documentos dentro de cada processo sem ler seu conteúdo
- [x] **16 blocos prioritários definidos** (PANs, Monitora, avaliação de risco, quelônios, crocodilianos, guias, etc.)
- [ ] **Executar catalogação completa** dos 16 blocos prioritários (~290 processos, ~20–30 min)
  ```bash
  source venv/bin/activate && set -a && source .env && set +a
  python scripts/coleta/listar_documentos_sei.py
  # Retomar se interrompida:
  python scripts/coleta/listar_documentos_sei.py --retomar
  ```
  - Saída: `01_fontes_web/sei/documentos_por_processo.json`
- [x] **Analisar catálogo** — triagem automática gerou lista de 197 processos candidatos (`processos_para_exportacao.json`; ver [`docs/processos/selecao_processos_sei.md`](processos/selecao_processos_sei.md))
- [x] **Documentar os 220 processos descartados**, com o motivo do descarte (`01_fontes_web/sei/processos_descartados.json`/`.csv`) — nenhum processo é removido do catálogo, apenas fica fora da lista de exportação
- [ ] **Decidir com a equipe do RAN** quais processos/documentos têm autorização para exportação
- [ ] Exportar documentos aprovados manualmente e mover para `04_documentos_pendentes_avaliacao/sei/`
- [ ] Avaliar sensibilidade individualmente antes de mover para `03_documentos_autorizados/`

> Ver detalhamento completo em [`docs/processos/coleta_sei_detalhado.md`](processos/coleta_sei_detalhado.md)
> e critérios de seleção em [`docs/decisoes/0004-criterios-selecao-documentos-sei.md`](decisoes/0004-criterios-selecao-documentos-sei.md)

---

## Fase 2 — Extração de texto

> **Dependência:** documentos coletados (Fase 1)

### 2.1 SALVE — fichas de espécies (JSON → texto limpo)
- [x] Script de extração criado (`scripts/processamento/extrair_texto_salve.py`)
- [x] **Executar extração no conjunto de teste (24 fichas) e validar saída**
  ```bash
  source venv/bin/activate
  python scripts/processamento/extrair_texto_salve.py
  ```
  - Verificado: texto limpo, parágrafos preservados, campos estruturados legíveis (0 erros)
  - Saída: `07_processados/textos_extraidos/salve/<slug>.json`
  - Ver detalhamento em [`docs/processos/extracao_texto_salve.md`](processos/extracao_texto_salve.md)
- [ ] Executar extração completa após coleta completa do SALVE (Fase 1.3)

### 2.2 PDFs do Monitora e dos PANs (PDF → texto)
- [x] **Script de extração de PDFs implementado** (`scripts/processamento/extrair_texto_pdfs.py`)
  - Usa PyMuPDF (`fitz`) como extrator principal
  - Detecta PDFs escaneados (ausência de camada de texto): aplica Tesseract OCR como fallback
  - Salva texto extraído em `07_processados/textos_extraidos/<fonte>/<nome_doc>.json`
  - Registra metadados de extração: número de páginas, método usado (texto/OCR), status
  - Ver detalhamento completo em [`docs/processos/extracao_pdfs.md`](processos/extracao_pdfs.md)
- [x] Dependências instaladas (`pymupdf`, `pytesseract`, `pillow`, Tesseract no sistema)
- [x] Executar extração nos PDFs do Monitora e validar amostra — 109/109 processados, 0 erros (2026-06-25)
- [x] Executar extração nos PDFs dos PANs e validar amostra — 707/707 processados (47 via OCR), 0 erros (2026-06-25)

### 2.3 Publicações científicas (PDF → texto)
- [ ] Reutilizar o mesmo script de extração de PDFs (Fase 2.2)
- [ ] Executar sobre `03_documentos_autorizados/` (somente documentos já aprovados)

---

## Fase 3 — Classificação de sensibilidade

> **Dependência:** documentos coletados (Fase 1); pode correr em paralelo com Fase 2

> Esta fase envolve decisão humana — não pode ser automatizada integralmente.

- [ ] **Revisão manual dos documentos do Monitora:** verificar se há localização precisa de espécies ameaçadas ou dados pessoais
- [ ] **Revisão manual dos PDFs dos PANs:** mesmos critérios
- [ ] **Fichas SALVE:** avaliar se as coordenadas de distribuição nas fichas são sensíveis
  - As fichas são públicas no site do ICMBio, portanto a tendência é classificá-las como autorizadas
- [ ] **Publicações científicas:** verificar copyright e termos de uso de cada publicação
- [ ] Mover documentos aprovados: `04_documentos_pendentes_avaliacao/` → `03_documentos_autorizados/`
- [ ] Mover documentos sensíveis: `04_documentos_pendentes_avaliacao/` → `05_documentos_sensiveis_nao_indexar/`
- [ ] Atualizar inventário com a classificação de cada documento

---

## Fase 4 — Chunking

> **Dependência:** textos extraídos (Fase 2) + documentos autorizados (Fase 3)

- [x] **Script único de chunking implementado** (`scripts/processamento/gerar_chunks.py`)
  - Lê exclusivamente de `03_documentos_autorizados/{monitora,pans,salve}/` (nunca de `04_*`/`05_*`, conforme ADR 0002)
  - Tamanho alvo ~2000 caracteres (~500 tokens), sobreposição ~200 caracteres (~50 tokens), por aproximação de caracteres
  - Splits preferencialmente em parágrafo/sentença; parágrafos minúsculos (ex.: número de artigo isolado por quebra de página) são fundidos ao próximo até atingir um tamanho mínimo, para não gerar chunks sem contexto
  - Saída: `07_processados/chunks/<fonte>/chunks.jsonl` — um JSON por linha

### 4.1 SALVE
- [x] Um chunk por seção da ficha (10 seções); seções longas divididas em sub-chunks com overlap
- [x] Cabeçalho em cada chunk com metadados da espécie (nome, categoria de risco, bioma, DOI)
- [x] Executado: 24 fichas → 231 chunks (`07_processados/chunks/salve/chunks.jsonl`)

### 4.2 PDFs do Monitora e dos PANs
- [x] Janela deslizante com overlap sobre o texto por página; cada chunk registra `pagina_inicio`/`pagina_fim`, fonte, nome do documento, URL/caminho local e data de extração
- [x] Executado: 109 documentos do Monitora → 7.220 chunks; 706 documentos dos PANs → 31.791 chunks
  - 1 documento do catálogo de PANs (`pan-quelonios-portaria-gat.json`) tem texto extraído mas **não** está em `03_documentos_autorizados/` — corretamente excluído do chunking

### 4.3 SEI
- [ ] **Pendente** — depende da equipe do RAN autorizar a exportação dos processos candidatos (Fase 1.5) e da avaliação de sensibilidade de cada documento exportado
- [ ] Depois que os documentos aprovados forem movidos para `03_documentos_autorizados/sei/`: implementar/adaptar extração de texto (Fase 2) e então rodar `gerar_chunks.py --fonte sei` (requer adicionar suporte à fonte "sei" no script)
- **A Fase 4 só pode ser considerada concluída depois que o SEI passar por essa etapa.**

### 4.4 Publicações científicas
- [ ] Reutilizar ou adaptar `gerar_chunks.py` para publicações científicas quando entrarem em `03_documentos_autorizados/` (Fase 1.4)
  - Considerar incluir metadados bibliográficos (autores, ano, título, DOI) em cada chunk

---

## Fase 5 — Embeddings e banco vetorial (Qdrant)

> **Dependência:** chunks gerados (Fase 4) + infraestrutura com Qdrant ativo

### 5.1 Escolha do modelo de embeddings
- [ ] **Decisão pendente:** qual modelo usar?
  - Opção A: `text-embedding-3-small` (OpenAI API) — simples, boa qualidade, custo por token
  - Opção B: modelo open-source em português (ex: `neuralmind/bert-base-portuguese-cased`) — sem custo de API, requer GPU ou CPU mais potente
  - Recomendação inicial: OpenAI `text-embedding-3-small` para o protótipo (troca fácil depois)

### 5.2 Configuração do Qdrant
- [ ] Verificar que o PC servidor está ativo e acessível via túnel SSH
- [ ] Criar coleção no Qdrant com os parâmetros adequados (dimensão do vetor, métrica de similaridade)
  ```bash
  ssh -N -L 6333:localhost:6333 usuario@IP_DO_SERVIDOR
  ```
- [ ] Validar conectividade (`scripts/check_services.py`)

### 5.3 Geração e indexação de embeddings
- [ ] **Implementar script de indexação** (`scripts/indexacao/indexar_chunks.py`)
  - Lê `chunks.jsonl` de cada fonte
  - Gera embeddings (modelo escolhido na 5.1)
  - Insere pontos no Qdrant com payload de metadados
  - Registra IDs e status no PostgreSQL (tabela de índice)
- [ ] Indexar SALVE (testar com 3 fichas primeiro)
- [ ] Indexar Monitora, PANs e publicações

---

## Fase 6 — Backend RAG (FastAPI)

> **Dependência:** Qdrant com dados indexados (Fase 5)

- [ ] **Inicializar projeto FastAPI** (`backend/`)
- [ ] **Implementar endpoint de busca semântica**
  - Recebe pergunta do usuário
  - Gera embedding da pergunta
  - Busca top-K chunks no Qdrant
  - Retorna chunks com metadados de fonte
- [ ] **Implementar filtro de acesso**
  - Verificar que apenas chunks de documentos autorizados são retornados
- [ ] **Implementar endpoint de geração de resposta**
  - Monta prompt com os chunks recuperados
  - Chama API do LLM (ex: `claude-sonnet-4-6` ou `gpt-4o`)
  - Retorna resposta com citações de fonte formatadas
- [ ] **Implementar busca híbrida** (semântica + palavras-chave) se a busca pura por embeddings for insuficiente
- [ ] **Configurar logging e feedback**
  - Registrar perguntas, chunks recuperados e respostas no PostgreSQL
  - Permitir feedback do usuário (thumbs up/down) por resposta

---

## Fase 7 — Interface (Streamlit)

> **Dependência:** backend FastAPI funcional (Fase 6)

- [ ] **Criar protótipo de chat em Streamlit** (`interface/app.py`)
  - Campo de pergunta
  - Exibição da resposta com citações de fonte
  - Botão de feedback por resposta
- [ ] **Exibir fontes de forma clara**
  - Nome do documento, seção, página (quando aplicável), link/DOI
- [ ] Testar fluxo completo localmente: pergunta → busca → resposta → citação

---

## Fase 8 — Validação com usuários

> **Dependência:** protótipo funcional (Fase 7)

- [ ] **Definir perguntas de teste** com técnicos e gestores do RAN
- [ ] **Sessão de teste com usuários reais** — observar comportamento, anotar gaps
- [ ] **Avaliar qualidade das respostas:**
  - As citações de fonte estão corretas?
  - O chatbot indica corretamente quando não tem evidência suficiente?
  - Há alucinações?
- [ ] **Iterar** com base no feedback: ajustar chunking, embeddings, prompt, filtros
- [ ] **Documentar limitações conhecidas** para os usuários

---

## Decisões pendentes

| Decisão | Impacto | Quando decidir |
|---|---|---|
| Modelo de embeddings (OpenAI vs. open-source) | Custo, qualidade, dependência de API | Antes da Fase 5 |
| Modelo de LLM para geração (Claude vs. GPT vs. outro) | Custo, qualidade, privacidade dos dados | Antes da Fase 6 |
| Quais publicações científicas incluir no acervo inicial | Escopo da base de conhecimento | Fase 1.4 |
| Quais documentos do SEI têm autorização de uso | Escopo e conformidade | Fase 1.5 |
| Sensibilidade das coordenadas nas fichas SALVE | Quais fichas podem ser indexadas | Fase 3 |
| Migração para servidor dedicado | Capacidade de processamento e armazenamento | Após validação do protótipo (Fase 8) |

---

## Ordem recomendada para as próximas sessões

1. **Agora:** analisar catálogo do SEI (`documentos_por_processo.json`) para identificar processos com documentos técnicos relevantes
2. **Em seguida:** decidir com a equipe do RAN quais processos/documentos do SEI têm autorização para exportação
3. **Em seguida:** executar coleta completa do SALVE (`coleta_salve.py` sem `--limite`)
4. **Depois:** executar e validar `extrair_texto_salve.py`
5. **Depois:** extração dos PDFs do Monitora e dos PANs
6. **Depois:** classificação de sensibilidade dos documentos coletados
7. **Depois:** chunking (SALVE primeiro, depois PDFs)
8. **Depois:** embeddings e indexação no Qdrant
9. **Depois:** FastAPI + Streamlit + validação

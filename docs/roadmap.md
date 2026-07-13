# Roadmap do projeto — Chatbot RAG RAN/ICMBio

Documento de referência para todas as fases, tarefas e processos do projeto,
do estado atual até o protótipo funcional validado com usuários.

**Atualizado em:** 2026-07-08

---

## Status geral

```
[Fase 1] Coleta de dados          ████████░░  80% — SALVE completo (2086 fichas); publicações organizadas (312 arquivos, catálogo inicial); SEI catalogado
[Fase 2] Extração de texto        █████████░  90% — PDFs Monitora/PANs extraídos (816/816); SALVE completo (2086/2086)
[Fase 3] Classificação            ░░░░░░░░░░   0% — sem avaliação individual formal registrada; Monitora/PANs/SALVE já estão em 03_documentos_autorizados/ por serem fontes públicas (ver docs/processos/classificacao_sensibilidade.md, status "A definir")
[Fase 4] Chunking                 ████████░░  80% — 59.080 chunks (monitora, PANs, SALVE completos); SEI pendente (autorização Fase 1.5)
[Fase 5] Embeddings + Qdrant      ███░░░░░░░  30% — BGE-M3 escolhido temporariamente para testes (ADR 0005); script de indexação implementado, aguardando primeira execução real
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
- [x] **Coleta completa executada** — 2086 fichas de répteis e anfíbios em `01_fontes_web/salve/fichas/`

### 1.4 Publicações científicas do RAN
- [x] **Definir critérios de inclusão** — resolvido na prática: a equipe do RAN já mantém uma
  planilha de controle própria (`Publicacoes_RAN_Herpetofauna_..._15_11_2025.xlsx`, em
  `02_publicacoes_cientificas_ran/bkup planilhas antigas/`) com o levantamento de publicações
  de herpetofauna dos pesquisadores do RAN — esse é o critério de facto
- [x] **PDFs entregues e organizados por tipo** em `02_publicacoes_cientificas_ran/`
  (312 arquivos): Artigo/Nota/Comunicação Científica (95), Resumos de Eventos Científicos (110),
  Livro/Capítulo/Cartilha/Manual (28), Matérias ICMBio em Foco (33), Boletins RAN (25),
  Teses e Dissertações (10), Monografias/TCC (8), Outras Publicações Técnicas (3)
  - As subpastas temáticas originais (`anfibios/`, `repteis/`, `conservacao/`, `monitoramento/`,
    `outros/`) continuam vazias — a organização entregue pela equipe é por **tipo de
    publicação**, não por tema; decidir se vale a pena reclassificar por tema ou manter por tipo
- [x] **Catálogo gerado e revisado**, cruzando os arquivos com a planilha de controle da
  equipe (`scripts/coleta/catalogar_publicacoes_ran.py` → `06_inventario/catalogo_publicacoes_ran.json`)
  — 284/312 arquivos resolvidos automaticamente (número único, faixa de números, duplicata
  exata ou placeholder de lacuna conhecida); 18 revisados manualmente (ver
  [`docs/processos/catalogacao_publicacoes.md`](processos/catalogacao_publicacoes.md)):
  9 edições do Boletim do RAN + 1 HerpetoPAN sem linha própria na planilha (institucionais,
  baixo risco), 7 anais completos do Congresso Brasileiro de Herpetologia 2004–2015
  (conteúdo majoritariamente de terceiros, **não** apenas do RAN — ver observação de
  sensibilidade abaixo) e 1 artigo mais novo que a última atualização da planilha
- [ ] Consolidar esse catálogo em `06_inventario/inventario_fontes.xlsx` (planilha geral do projeto)
- [ ] Avaliar sensibilidade/copyright de cada publicação antes de mover para
  `03_documentos_autorizados/` — atenção especial aos anais de congresso (copyright de
  terceiros — Sociedade Brasileira de Herpetologia) e aos artigos publicados em revistas
  externas (copyright da editora); publicações institucionais do próprio RAN (boletins,
  HerpetoPAN, ICMBio em Foco) têm risco mais baixo
- [ ] **Decidir como versionar os PDFs**: vários arquivos excedem o limite de tamanho do
  GitHub (um arquivo de 130 MB e outros entre 50–90 MB já bloquearam um `git push`) — decidir
  entre Git LFS, manter os binários fora do git (como já é feito para `01_fontes_web/**/documentos/`,
  com apenas o catálogo JSON versionado) ou outra estratégia de armazenamento

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
- [x] **Analisar catálogo** — triagem automática gerou lista de 173 processos candidatos (`processos_para_exportacao.json`, v2 após correção de falsos positivos em 2026-07-13; ver [`docs/processos/selecao_processos_sei.md`](processos/selecao_processos_sei.md))
- [x] **Documentar os 244 processos descartados**, com o motivo do descarte (`01_fontes_web/sei/processos_descartados.json`/`.csv`) — nenhum processo é removido do catálogo, apenas fica fora da lista de exportação
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
- [x] Executar extração no conjunto de teste (24 fichas) e validar saída (0 erros)
- [x] **Executar extração completa** — 2086/2086 fichas, 0 erros (2026-07-06)
  ```bash
  source venv/bin/activate
  python scripts/processamento/extrair_texto_salve.py
  ```
  - Saída: `07_processados/textos_extraidos/salve/<slug>.json`
  - Ver detalhamento em [`docs/processos/extracao_texto_salve.md`](processos/extracao_texto_salve.md)

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
- [x] **Fichas SALVE:** avaliadas — não contêm coordenadas precisas de ocorrência (só estados/biomas/EOO-AOO agregados e mapa-imagem público); fichas são públicas no site do ICMBio, classificadas como autorizadas. Todas as 2086 copiadas para `03_documentos_autorizados/salve/` (2026-07-06)
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
- [x] Executado: 2086 fichas → 20.069 chunks (`07_processados/chunks/salve/chunks.jsonl`) (2026-07-06)

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
- [x] **Decisão temporária tomada:** `BAAI/bge-m3` (Opção C, local), usado apenas para
  testar os chunks já gerados e validar a qualidade dos vetores enquanto a decisão
  final não sai (ver [ADR 0005](decisoes/0005-escolha-temporaria-modelo-embeddings.md))
- [ ] **Decisão final pendente com a equipe do RAN** — condicionada a definir se há
  orçamento para custear uma API de embeddings de forma recorrente; documento de apoio:
  [`docs/processos/escolha_modelo_embeddings.md`](processos/escolha_modelo_embeddings.md)
  - Opção A: `text-embedding-3-small` (OpenAI API) — simples, boa qualidade, custo por token
  - Opção B: `text-embedding-3-large` (OpenAI API) — mais qualidade, mais caro; provavelmente acima do necessário
  - Opção C: modelo open-source multilíngue local (`BAAI/bge-m3`, em teste; ou `intfloat/multilingual-e5-large`) — sem custo de API nem envio de dados a terceiros, requer processamento local
  - Se a equipe confirmar que não há orçamento para API, a escolha temporária (BGE-M3) tende a virar definitiva — atualizar o ADR 0005 nesse caso, não criar um novo

### 5.2 Configuração do Qdrant
- [x] Serviço definido em `docker-compose.yml` (imagem `qdrant/qdrant`, porta 6333 restrita a 127.0.0.1)
- [x] Criação da coleção automatizada pelo próprio script de indexação (5.3) — dimensão 1024, distância cosseno
- [x] **Modo alternativo sem servidor implementado** (`QDRANT_LOCAL_PATH` no `.env`) — Qdrant
  embutido, sem Docker nem rede, para poder testar antes do PC servidor estar pronto
- [ ] **PC servidor ainda não configurado** — pendente de revisão de segurança de rede
  (não é bloqueio para a Fase 5: use o modo embutido acima enquanto isso)
- [ ] Quando o servidor estiver pronto: verificar que está ativo e acessível via túnel SSH
  ```bash
  ssh -N -L 6333:localhost:6333 usuario@IP_DO_SERVIDOR
  ```
- [ ] Validar conectividade (`scripts/check_services.py`)

### 5.3 Geração e indexação de embeddings
- [x] **Script de indexação implementado** (`scripts/indexacao/indexar_chunks.py`) — ver
  [`docs/processos/embeddings.md`](processos/embeddings.md) para detalhes
  - Lê `chunks.jsonl` de cada fonte
  - Gera embeddings densos com BGE-M3 (escolha temporária, ADR 0005)
  - Insere pontos no Qdrant com payload de metadados; ID derivado do `chunk_id` (idempotente)
  - Inclui modo `--buscar` para rodar buscas de teste sem reindexar
  - **Ainda não registra IDs/status no PostgreSQL** — só grava no Qdrant por enquanto
- [ ] Executar primeira indexação real (todas as fontes: monitora, pans, salve), usando o
  modo embutido do Qdrant por enquanto, e avaliar qualidade da recuperação com perguntas
  reais do domínio
- [ ] Indexar publicações e SEI quando essas fontes tiverem chunks gerados (Fase 1.4/1.5, 4.3/4.4)

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
| Modelo de embeddings em produção (OpenAI vs. open-source) — BGE-M3 já em uso temporário para testes ([ADR 0005](decisoes/0005-escolha-temporaria-modelo-embeddings.md)); decisão final depende de orçamento para API — ver [`docs/processos/escolha_modelo_embeddings.md`](processos/escolha_modelo_embeddings.md) | Custo, qualidade, dependência de API | Antes de indexar em produção (Fase 6) |
| Modelo de LLM para geração (Claude vs. GPT vs. outro) | Custo, qualidade, privacidade dos dados | Antes da Fase 6 |
| Quais publicações científicas incluir no acervo inicial | Escopo da base de conhecimento | Fase 1.4 |
| Quais documentos do SEI têm autorização de uso | Escopo e conformidade | Fase 1.5 |
| Migração para servidor dedicado | Capacidade de processamento e armazenamento | Após validação do protótipo (Fase 8) |

---

## Ordem recomendada para as próximas sessões

Coleta, extração e chunking de Monitora, PANs e SALVE estão completos (59.080 chunks
em `07_processados/chunks/`). O que resta não depende da reunião do SEI e pode
avançar em paralelo:

1. **Agora:** subir o Qdrant e implementar a indexação com BGE-M3, o modelo escolhido temporariamente para testes (ADR 0005) — chunks de Monitora/PANs/SALVE já estão prontos para indexar
2. **Em paralelo:** organizar e catalogar publicações científicas do RAN (Fase 1.4)
3. **Em paralelo:** atualizar `06_inventario/inventario_fontes.xlsx` com o estado atual de cada fonte
4. **Em paralelo:** decidir com a equipe do RAN quais processos/documentos do SEI têm autorização para exportação (Fase 1.5) — quando sair, roda extração + `gerar_chunks.py --fonte sei`
5. **Depois:** FastAPI + Streamlit + validação com usuários

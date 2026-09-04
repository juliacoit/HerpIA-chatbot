# Roadmap do projeto — HerpIA (Sistema RAG RAN/ICMBio)

Documento de referência para todas as fases, tarefas e processos do projeto,
do estado atual até o protótipo funcional validado com usuários.

**Atualizado em:** 2026-07-21

---

## Status geral

```
[Fase 1] Coleta de dados          ████████░░  80% — SALVE completo (2086 fichas); publicações organizadas (312 arquivos, catálogo inicial); SEI catalogado
[Fase 2] Extração de texto        ██████████  100% — PDFs Monitora/PANs extraídos (816/816); SALVE completo (2086/2086); piloto de processamento de imagens implementado
[Fase 3] Classificação            ░░░░░░░░░░   0% — sem avaliação individual formal registrada; Monitora/PANs/SALVE já estão em 03_documentos_autorizados/ por serem fontes públicas (ver docs/processos/classificacao_sensibilidade.md, status "A definir")
[Fase 4] Chunking                 ████████░░  80% — 59.080 chunks (monitora, PANs, SALVE completos); SEI pendente (autorização Fase 1.5)
[Fase 5] Embeddings + Qdrant      ████████░░  80% — BGE-M3 (ADR 0005); indexação real concluída (59.085/59.085 chunks, monitora+PANs+SALVE, 0 erros, 2026-08-10); comparação com outros modelos e indexação de publicações/SEI pendentes
[Fase 6] Backend RAG (FastAPI)    ████████░░  80% — esqueleto validado de ponta a ponta (busca + geração com Ollama local, 2026-08-11); logging/feedback em PostgreSQL implementado e validado contra o Postgres real (2026-09-02, ver docs/processos/backend_fastapi.md); faltam busca híbrida e autenticação
[Fase 7] Interface (Streamlit)    ███████░░░  70% — protótipo de chat implementado (interface/, 2026-09-04): pergunta, resposta com citações, feedback, filtros de fonte/top_k; falta testar num navegador de verdade (bloqueado nesta sessão, ver docs/processos/interface_streamlit.md)
[Fase 8] Validação com usuários   ░░░░░░░░░░   0%
```

---

## Fase 1 — Coleta de dados

### 1.1 Programa Monitora
- [x] Script de coleta de metadados (`scripts/coleta/coleta_monitora.py`)
- [x] Script de download de documentos (`scripts/coleta/download_documentos_monitora.py`)
- [x] **Download completo executado** (2026-08-11, reexecutado 2026-09-02 sem regressão) — 127/128
  arquivos baixados com sucesso; 1 falha residual (link morto em `researchgate.net`, fora do
  controle do ICMBio). Saída: `01_fontes_web/monitora/<categoria>/documentos/`;
  relatório em `relatorio_download.json`

### 1.2 PANs (Planos de Ação Nacional)
- [x] Script de coleta de metadados (`scripts/coleta/coleta_pans.py`)
- [x] Script de download de documentos (`scripts/coleta/download_documentos_pans.py`)
- [x] **Download completo executado** (2026-08-11, reexecutado 2026-09-02 sem regressão) —
  1021/1038 arquivos baixados com sucesso; 17 falhas residuais, todas em PANs sem relação com
  herpetofauna (corais, ariranha, peixe-boi, quelônios, etc.) — 14 links mortos (404) em sites
  externos ao ICMBio (researchgate, repositorios de universidades, ibama.gov.br) e 3 erros de
  conexão intermitentes; nenhuma falha nos PANs de herpetofauna. Saída:
  `01_fontes_web/pans/<slug>/documentos/`; relatório em `relatorio_download.json`

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

### 2.3 Processamento de imagens em PDFs (CLIP + VLM local, 100% local)

A maioria dos PDFs nas fontes (publicações científicas, relatórios, PANs) contém imagens críticas: gráficos, mapas de distribuição, tabelas visuais, diagramas. Apenas extrair texto perde essas informações essenciais para o RAG.

**Estratégia 100% local (CLIP + Qwen2-VL-2B-Instruct):** decisão de 2026-07-21 —
por falta de verba, a descrição de imagens não pode depender de API paga.
Substituiu a estratégia original (CLIP + Claude Haiku). Ver nota de atualização
e seção "Solução Escolhida (revisada)" em
[`docs/processos/ESTRATEGIA_PROCESSAMENTO_IMAGENS.md`](processos/ESTRATEGIA_PROCESSAMENTO_IMAGENS.md).

1. Extrai imagens com PyMuPDF (já incluso na Fase 2.2)
2. Classifica cada imagem com CLIP (gráfico/mapa/diagrama/tabela vs. fotografia/ilustração)
3. Descreve apenas as relevantes com um VLM local (`Qwen/Qwen2-VL-2B-Instruct`,
   4-bit em GPU quando disponível, fallback CPU — cabe na RTX 2050 de 4 GB da
   máquina de dev)
4. Descrições são indexadas como chunks adicionais

- [ ] **Piloto implementado** (`scripts/processamento_imagens/processar_imagens_piloto.py`)
  - Script pronto para testes com PDFs reais
  - Dependências: `pip install -r scripts/processamento_imagens/requirements_imagens.txt`
  - Teste rápido (só CLIP, sem custos): `python testar_classificacao.py`
  - Pipeline completo (com descrição via VLM local, sem custo de API): `python processar_imagens_piloto.py`
  - Ver instruções: [`scripts/processamento_imagens/COMECE_AQUI.md`](../../scripts/processamento_imagens/COMECE_AQUI.md)
- [ ] **Validação:** testar com 5-10 PDFs variados
  - Verificar qualidade de classificação (CLIP)
  - Verificar qualidade de descrição (Qwen2-VL-2B local)
  - Tempo real por imagem (GPU 4-bit vs. CPU) — não há custo de API a medir
  - Documentar em [`docs/processos/VALIDACAO_PILOTO_IMAGENS.md`](processos/VALIDACAO_PILOTO_IMAGENS.md)
- [ ] **Integração:** adicionar ao pipeline principal de indexação
  - Armazenar descrições em `07_processados/imagens_descritas/`
  - Indexar descrições no Qdrant junto com chunks de texto
  - Metadados: referência cruzada texto ↔ imagem

### 2.4 Publicações científicas (PDF → texto)
- [ ] Reutilizar o mesmo script de extração de PDFs (Fase 2.2)
- [ ] Executar sobre `03_documentos_autorizados/` (somente documentos já aprovados)
- [ ] Integrar processamento de imagens (Fase 2.3) para publicações com gráficos/mapas

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
- [x] **Teste comparativo de modelos implementado** (2026-07-17)
  - Estratégia: indexar com 3 modelos diferentes e comparar qualidade
  - Ver [`docs/processos/teste_comparativo_embeddings.md`](processos/teste_comparativo_embeddings.md)
  - Modelos: multilingual-e5-small (local, leve), BGE-M3 (local, maior), text-embedding-3-small (OpenAI API)
  - Scripts: `indexar_chunks_lite.py` (multilingual-e5), `indexar_chunks.py` (BGE-M3), `teste_openai_embeddings.py` (OpenAI)
- [x] **Indexação real com BGE-M3 concluída** (2026-08-10) — 59.085/59.085 chunks (monitora 7.220, PANs 31.796, SALVE 20.069), 0 erros, Qdrant embutido (`07_processados/qdrant_local`)
  - Busca de teste validada com perguntas do domínio nas 3 fontes (ex.: status de conservação da jararaca-ilhoa — retornou ficha SALVE + PAN herpetofauna insular corretamente)
- [ ] Testar multilingual-e5-small e OpenAI API em amostra e comparar custo/qualidade com BGE-M3 (comparação ainda não feita — decisão de modelo definitivo pendente)
- [ ] Indexar publicações e SEI quando essas fontes tiverem chunks gerados (Fase 1.4/1.5, 4.3/4.4)

---

## Fase 6 — Backend RAG (FastAPI)

> **Dependência:** Qdrant com dados indexados (Fase 5)

- [x] **Inicializar projeto FastAPI** (`backend/`) — esqueleto criado (2026-08-11), ver [`docs/processos/backend_fastapi.md`](processos/backend_fastapi.md)
- [x] **Implementar endpoint de busca semântica** (`POST /buscar`)
  - Recebe pergunta do usuário
  - Gera embedding da pergunta (BGE-M3, mesmo modelo da indexação)
  - Busca top-K chunks no Qdrant
  - Retorna chunks com metadados de fonte
  - Testado manualmente contra a coleção real (59.085 pontos) — retornos corretos
- [x] **Implementar filtro de acesso**
  - Filtro por `nivel_sensibilidade == "autorizado"` aplicado na consulta ao Qdrant (`backend/services/retrieval.py`), além do filtro já existente na indexação
- [x] **Implementar endpoint de geração de resposta** (`POST /perguntar`)
  - Monta prompt com os chunks recuperados
  - Chama o LLM através de uma interface `LLMClient` (ver [ADR 0006](decisoes/0006-escolha-temporaria-llm-geracao.md)) — implementação inicial usa Ollama local (`qwen2.5:3b-instruct` ou equivalente), trocável por API paga depois sem redesenho
  - Retorna resposta com citações de fonte formatadas (deduplicadas)
  - Responde `503` com instrução clara se o Ollama não estiver rodando
  - [x] **Validado de ponta a ponta** (2026-08-11) — Ollama instalado sem root em `~/.local`
    (ver `scripts/infra/subir_ollama.sh`, ADR 0006) e modelo `qwen2.5:3b-instruct` baixado;
    `/perguntar` testado contra a coleção real (59.085 pontos), resposta e citações corretas
  - [x] Testar com uma amostra maior de perguntas reais do domínio — em andamento via `scripts/teste_perguntas_dominio.py` e `diagnosticos/baterias/` (8 execuções entre 2026-08-19 e 2026-08-25, ver `diagnosticos/teste-perguntas-dominio.md`)
- [ ] **Implementar busca híbrida** (semântica + palavras-chave) se a busca pura por embeddings for insuficiente
- [x] **Configurar logging e feedback** (2026-09-02, ver [`docs/processos/backend_fastapi.md`](processos/backend_fastapi.md#logging-e-feedback-postgresql))
  - [x] Registrar perguntas, chunks recuperados e respostas no PostgreSQL — `backend/db.py` + `backend/services/logging_db.py`, tabelas `interacoes`/`feedback` criadas automaticamente no startup
  - [x] Permitir feedback do usuário (thumbs up/down) por resposta — `POST /feedback`
  - [x] **Validado contra um PostgreSQL real** (2026-09-02, containers `ran_postgres`/`ran_qdrant` já existentes neste ambiente, só faltava habilitar a integração Docker Desktop ↔ WSL): tabelas criadas automaticamente no startup; `/perguntar` gravou uma interação real com citações/chunks em JSONB e devolveu o `id`; `/feedback` gravou a avaliação referenciando esse `id`; `interacao_id` inexistente devolveu 404 corretamente
- [ ] **Autenticação/autorização de usuários** — a API hoje não tem nenhuma

---

## Fase 7 — Interface (Streamlit)

> **Dependência:** backend FastAPI funcional (Fase 6)

- [x] **Criar protótipo de chat em Streamlit** (`interface/app.py` + `interface/cliente_api.py`, 2026-09-04, ver [`docs/processos/interface_streamlit.md`](processos/interface_streamlit.md))
  - [x] Campo de pergunta (`st.chat_input`, histórico em `st.session_state`)
  - [x] Exibição da resposta com citações de fonte, diferenciando `evidencia_suficiente`/`resposta_fundamentada`
  - [x] Botão de feedback por resposta (útil/não útil, `POST /feedback`) — desabilitado com explicação quando `id` é `null` (PostgreSQL indisponível)
- [x] **Exibir fontes de forma clara**
  - Nome do documento, seção, página (quando aplicável), link — um `st.expander` por resposta, um `Citacao` por linha
- [ ] **Testar fluxo completo num navegador de verdade** — bloqueado nesta
  sessão (Playwright exige o canal "chrome", que precisa de `apt`/root para
  instalar; sem sudo interativo disponível). Validado por outros meios:
  `streamlit run interface/app.py` sobe sem exceções (HTTP 200) e
  `interface/cliente_api.py` foi testado diretamente contra o backend real
  (`/perguntar` e `/feedback`, incluindo o caminho de erro 503 com
  PostgreSQL indisponível) — mas falta a confirmação visual/interativa num
  navegador. Pendência para a próxima sessão ou para a Júlia confirmar
  manualmente abrindo http://localhost:8501.

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
| Modelo de LLM para geração em produção (API paga vs. local) — LLM local via Ollama já escolhido temporariamente para a Fase 6 ([ADR 0006](decisoes/0006-escolha-temporaria-llm-geracao.md)); decisão final depende de orçamento para API, mesmo padrão do ADR 0005 | Custo, qualidade, privacidade dos dados | Antes de ir a produção (Fase 8) |
| Quais publicações científicas incluir no acervo inicial | Escopo da base de conhecimento | Fase 1.4 |
| Quais documentos do SEI têm autorização de uso | Escopo e conformidade | Fase 1.5 |
| Migração para servidor dedicado | Capacidade de processamento e armazenamento | Após validação do protótipo (Fase 8) |

---

## Ordem recomendada para as próximas sessões

Indexação real concluída (Fase 5) e esqueleto do backend FastAPI implementado
(Fase 6, ver [`docs/processos/backend_fastapi.md`](processos/backend_fastapi.md)).
O que resta não depende da reunião do SEI e pode avançar em paralelo:

1. **Agora (Fase 6):** Testar `/perguntar` com uma amostra maior de perguntas reais
   do domínio (Ollama já instalado e validado com uma pergunta de fumaça, 2026-08-11)

2. **Depois (Fase 6):** Logging de perguntas/respostas no PostgreSQL + feedback do usuário

3. **Em paralelo (Fase 2.3):** Validar piloto de processamento de imagens (100% local — CLIP + Qwen2-VL-2B)
   - Testar com 5-10 PDFs variados
   - Verificar qualidade de classificação (CLIP) e descrição (VLM local)
   - Documentar tempos reais e validação (sem custo de API a medir)
   - Ver: [`scripts/processamento_imagens/COMECE_AQUI.md`](scripts/processamento_imagens/COMECE_AQUI.md)

4. **Depois:** Integrar processamento de imagens ao pipeline de indexação
   - Armazenar descrições em `07_processados/imagens_descritas/`
   - Indexar no Qdrant junto com chunks de texto

5. **Em paralelo:** Organizar e catalogar publicações científicas do RAN (Fase 1.4) + processamento de imagens para as que tiverem

6. **Em paralelo:** Atualizar `06_inventario/inventario_fontes.xlsx` com o estado atual

7. **Em paralelo:** Decidir com a equipe do RAN quais processos/documentos do SEI têm autorização para exportação (Fase 1.5)

8. **Depois:** Streamlit (Fase 7) + validação com usuários (Fase 8)

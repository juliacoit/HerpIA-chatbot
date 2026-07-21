# Estratégia de Processamento de Imagens em PDFs

**Data**: 2026-07-21  
**Autora**: Júlia  
**Status**: Piloto em validação

## Problema

A maioria dos PDFs nas fontes de dados (publicações científicas, relatórios, PANs) contém imagens críticas: gráficos, mapas de distribuição, tabelas visuais, diagramas. Apenas extrair texto dos PDFs perdia essas informações essenciais para o RAG.

No entanto, nem toda imagem é relevante:
- ✅ Gráficos, mapas, diagramas, tabelas visuais — **precisam ser descritos**
- ❌ Fotos de animais, ilustrações decorativas — **podem ser descartadas**

## Soluções Avaliadas

### Opção 1: API Closed-Source
- **Claude (Haiku/Sonnet)**: $0,002-0,012 USD/imagem
- **GPT-4o**: $0,005 USD/imagem
- Custo estimado (59k chunks → ~3k imagens relevantes): **$6-36 USD por execução**
- ✅ Alta qualidade, consistência previsível
- ✅ Sem overhead computacional local
- ❌ Depende de API, precisa chave

### Opção 2: Modelos Locais
- **LLaVA 13B**: 8-12 GB VRAM, 1-3s/imagem
- **MiniCPM-V 8B**: 6-8 GB VRAM, 0.5-1s/imagem
- Custo estimado (3k imagens): **~25-100 min com paralelização**
- ✅ Zero custo de API
- ❌ Requer GPU dedicada, overhead operacional

### Opção 3: Híbrida (CLIP + API)
- **Estágio 1**: CLIP local (2-4 GB VRAM) classifica "é gráfico/mapa?" em milissegundos
- **Estágio 2**: Claude Haiku descreve apenas as relevantes (~60% das imagens)
- Custo estimado: **~$6 USD por execução completa**
- ✅ Melhor custo-benefício
- ✅ Filtro local elimina latência de API para fotos de animais
- ✅ Escalável — pode migrar descrição para local depois

## Solução Escolhida: Híbrida (CLIP + Claude Haiku)

### Arquitetura do Pipeline

```
PDF
  ↓
[PyMuPDF] Extrai imagens
  ↓
[CLIP Local] Classifica: relevante? (gráfico/mapa/diagrama/tabela)
  ├→ NÃO (foto animal, ilustração) → Descarta
  ├→ SIM → Enfileira para descrição
  ↓
[Claude Haiku API] Descreve as relevantes
  ↓
[JSON] Salva: { id, source_pdf, page, classification, description, tokens_used, cost }
  ↓
[Indexação] Descrições são tratadas como chunks de texto + metadados
```

### Camadas de Processamento

#### 1. Extração (PyMuPDF)
- Extrai todas as imagens dos PDFs
- Preserva contexto: número da página, ordem, tamanho

#### 2. Classificação (CLIP)
- Modelo: `openai/clip-vit-base-patch32` (330 MB)
- Tarefa: Zero-shot classification — "é um gráfico, mapa, tabela ou diagrama científico?"
- Input: imagem
- Output: score de confiança para cada classe
- Threshold: >0.5 para "relevante"
- **Custo computacional**: ~0.1-0.2s/imagem em CPU, <100 ms em GPU

#### 3. Descrição (Claude Haiku)
- Modelo: `claude-3-5-haiku-20241022`
- Tarefa: "Descreva este gráfico/mapa/diagrama focando em dados, tendências e achados principais. Inclua eixos, legendas, valores numéricos importantes."
- Tokens médios: ~150-300 tokens/imagem (input: 1000 tokens fixo para imagem, output: 150-300)
- **Custo**: ~$0.002 USD/imagem (Haiku)
- **Throughput**: 5-10 imagens/segundo com batching

#### 4. Indexação
- Descrições armazenadas como chunks adicionais: `tipo_conteudo: "imagem_descrita"`
- Metadados: `source_pdf`, `page`, `classification`, `confidence`
- Link reverso: chunks de texto com `referenced_images: [ids]`

---

## Custos Estimados

### Cenário: Reindexação Completa

Base atual: **59.080 chunks** (Monitora, PANs, SALVE)

**Estimativa de imagens**:
- PDFs com imagens: ~200-300 documentos
- Média: 10-20 imagens/documento → **2.000-6.000 imagens totais**
- Relevantes (após CLIP): ~60% → **1.200-3.600 imagens descritas**

**Custos**:

| Etapa | Recursos | Tempo | Custo |
|-------|----------|-------|-------|
| Extração (PyMuPDF) | CPU local | ~2-5 min | $0 |
| Classificação (CLIP) | GPU/CPU local | ~5-20 min | $0 |
| Descrição (Haiku) | API | ~2-5 min (batching) | $2-8 USD |
| **Total** | — | **~15-30 min** | **~$2-8 USD** |

**Por descrição**: $0.002 USD (Haiku), marginal.

### ROI vs. Alternativas

- **Claude Sonnet** (toda imagem): $0.012/imagem → $14-43 USD (40% mais caro)
- **Modelo local LLaVA** (sem CLIP): 25-100 min CPU/GPU (mais lento, mais complexo)
- **Não processar imagens**: Perde informações críticas para RAG

---

## Implementação

### Fase 1: Piloto (esta sessão)
- [ ] Script piloto em `scripts/processamento_imagens/`
- [ ] Testa com 1-2 PDFs das fontes
- [ ] Valida qualidade de classificação (CLIP) e descrição (Haiku)
- [ ] Registra custos reais

### Fase 2: Validação (próxima sessão)
- [ ] Rodas em 20-30 PDFs
- [ ] Ajusta prompts de descrição conforme necessário
- [ ] Otimiza batching/throughput
- [ ] Documenta edge cases (imagens muito pequenas, baixa qualidade, etc.)

### Fase 3: Integração
- [ ] Integra ao pipeline principal de indexação
- [ ] Armazena descrições em `07_processados/imagens_descritas/`
- [ ] Indexa descrições no Qdrant
- [ ] Testa recuperação: "Qual foi a tendência de população de X?"

---

## Dependências

```
pip install anthropic>=0.36  # Claude API
pip install torch torchvision  # CLIP
pip install transformers>=4.36  # CLIP via HuggingFace
pip install pillow pymupdf  # Imagens e PDFs
pip install numpy pydantic  # Utilitários
```

---

## Monitoramento e Ajustes

### Métricas para Acompanhar

1. **Classificação (CLIP)**:
   - Taxa de falsos positivos (foto animal classificada como "relevante")
   - Taxa de falsos negativos (gráfico descartado)
   - Distribuição de confiança

2. **Descrição (Haiku)**:
   - Tokens consumidos (input/output)
   - Custo real vs. estimado
   - Qualidade: responde que tipo de gráfico é? Quais são os dados principais?

3. **Integração**:
   - Quantas queries do usuário são respondidas com base em descrições de imagens?
   - Usuários confiam nas descrições?

### Prompts Ajustáveis

Se a qualidade das descrições for insuficiente, ajustar:
```python
DESCRIPTION_PROMPT = """
You are analyzing a graph, map, diagram or scientific table from a biodiversity/herpetology document.
Provide a structured description:
1. **Type**: (bar chart, distribution map, line graph, etc.)
2. **Main Finding**: (key data, trend, geographic pattern)
3. **Axes/Categories**: (what is being measured?)
4. **Values**: (key numbers, ranges, percentages)
5. **Implications**: (what this tells us about the species/conservation)

Be concise, objective, and include any legends, titles, or annotations visible.
"""
```

---

## Decisões Futuras

### Quando Migrar para Modelo Local?

- Se custo de API ultrapassar $50/mês → avaliar LLaVA
- Se latência de API se tornar problema → cache descritivo local
- Se volume crescer >10k imagens/mês → priorizar modelo local

### Quando Incluir Fotos de Animais?

- Futura integração com reconhecimento de espécies (fine-tuned CLIP + identificação)
- Exemplo: "Quais são as características de identificação do Rhinatrema bivittatum?"
- Por enquanto: descartadas, foco em dados estruturados

---

## Referências

- [CLIP Paper](https://arxiv.org/abs/2103.14030) — Learning transferable visual models
- [Claude Vision API Docs](https://docs.anthropic.com/en/docs/build-a-bot/vision)
- [LLaVA GitHub](https://github.com/haotian-liu/LLaVA) — alternativa local

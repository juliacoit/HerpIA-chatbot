# Estratégia de Processamento de Imagens em PDFs

**Data**: 2026-07-21 (revisado em 2026-07-21 — restrição de orçamento)
**Autora**: Júlia  
**Status**: Piloto em validação — solução escolhida revisada para 100% local

> **Atualização (2026-07-21):** ficou definido que este processamento deve ser
> **100% local, sem API paga**, por falta de verba. A Opção 3 (híbrida com
> Claude Haiku), descrita abaixo como "Solução Escolhida" original, **não é
> mais a solução adotada** — mantida no documento apenas como referência
> histórica de custo. A solução atual é a Opção 2 (100% local), detalhada na
> seção "Solução Escolhida (revisada)" mais abaixo.

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
- ⚠️ **GPU real da máquina de desenvolvimento: RTX 2050, 4 GB VRAM** (`nvidia-smi`,
  2026-07-21) — LLaVA 13B e MiniCPM-V 8B **não cabem** nessa placa (precisam de
  6-12 GB). Modelo viável precisa ser bem menor ou rodar quantizado — ver
  "Solução Escolhida (revisada)" abaixo.

### Opção 3: Híbrida (CLIP + API)
- **Estágio 1**: CLIP local (2-4 GB VRAM) classifica "é gráfico/mapa?" em milissegundos
- **Estágio 2**: Claude Haiku descreve apenas as relevantes (~60% das imagens)
- Custo estimado: **~$6 USD por execução completa**
- ✅ Melhor custo-benefício
- ✅ Filtro local elimina latência de API para fotos de animais
- ✅ Escalável — pode migrar descrição para local depois

## Solução Escolhida (revisada): 100% Local (CLIP + VLM local)

Substitui o Estágio 2 (Claude Haiku) da híbrida original por um modelo de
visão-linguagem (VLM) local. Mantém o Estágio 1 (CLIP) sem alteração — já era
100% local.

**Modelo escolhido para descrição: `Qwen2-VL-2B-Instruct`** (via
`transformers`), carregado em 4-bit (`bitsandbytes`) quando GPU disponível,
com fallback para CPU (mesmo padrão já usado pelo `ClipClassifier`).

Motivos da escolha, dado o hardware real (RTX 2050, 4 GB VRAM):
- Cabe em 4-bit (~2 GB VRAM) mesmo com a GPU pequena — LLaVA 13B/MiniCPM-V 8B
  não cabem.
- Suporte multilíngue melhor que a maioria dos VLMs pequenos (moondream2,
  por exemplo, é majoritariamente treinado em inglês) — relevante porque toda
  a base de conhecimento e os prompts são em português.
- Ativamente mantido, boa qualidade em descrição de gráficos/tabelas/diagramas
  para o tamanho.

**Custo**: $0 de API. Custo é só tempo de GPU/CPU local — mais lento que Haiku
por imagem, mas sem limite de orçamento.

**Atenção operacional**: a GPU de 4 GB é compartilhada com a indexação de
embeddings (BGE-M3, ver [`embeddings.md`](embeddings.md)) — não rodar os dois
processos pesados simultaneamente na mesma GPU (risco de OOM). Rodar o
processamento de imagens depois que a indexação de embeddings terminar, ou
forçar CPU (`--device cpu`) se precisar rodar em paralelo.

### Arquitetura do Pipeline (histórica — híbrida com Claude Haiku)

> Descrição abaixo é a arquitetura *original*, mantida como referência. A
> arquitetura atual é igual, trocando apenas o Estágio 3 (Claude Haiku →
> Qwen2-VL-2B-Instruct local).

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

#### 3. Descrição (VLM local — Qwen2-VL-2B-Instruct)
- Modelo: `Qwen/Qwen2-VL-2B-Instruct` (via `transformers`), 4-bit quantizado
  (`bitsandbytes`) em GPU, fallback CPU
- Tarefa: "Descreva este gráfico/mapa/diagrama focando em dados, tendências e achados principais. Inclua eixos, legendas, valores numéricos importantes." (mesmo prompt da versão Haiku, adaptado)
- **Custo**: $0 (100% local)
- **Throughput**: mais lento que API — depende de GPU/CPU disponível no momento;
  medir throughput real no piloto (ver Fase 1 de Implementação)
- **Nota**: Claude Haiku (`claude-3-5-haiku-20241022`) foi a escolha original
  desta etapa — descontinuado por falta de verba (ver nota de atualização no
  topo do documento). Mantido aqui só como registro histórico do que foi
  testado antes.

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

**Custos (solução atual — 100% local)**:

| Etapa | Recursos | Tempo | Custo |
|-------|----------|-------|-------|
| Extração (PyMuPDF) | CPU local | ~2-5 min | $0 |
| Classificação (CLIP) | GPU/CPU local | ~5-20 min | $0 |
| Descrição (Qwen2-VL-2B local) | GPU (4-bit)/CPU local | a medir no piloto — provavelmente mais lento que os ~2-5 min do Haiku, já que GPU é pequena (4 GB) e compartilhada com a indexação de embeddings | $0 |
| **Total** | — | a medir | **$0** |

**Custos (referência histórica — descartada por falta de verba)**:

| Etapa | Recursos | Tempo | Custo |
|-------|----------|-------|-------|
| Descrição (Claude Haiku) | API | ~2-5 min (batching) | $2-8 USD |

### ROI vs. Alternativas

- **Claude Haiku/Sonnet** (API paga): descartado — sem verba disponível
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
pip install torch torchvision  # CLIP + Qwen2-VL
pip install transformers>=4.45  # CLIP e Qwen2-VL via HuggingFace
pip install accelerate bitsandbytes  # quantização 4-bit do Qwen2-VL em GPU
pip install pillow pymupdf  # Imagens e PDFs
pip install numpy pydantic  # Utilitários
```

`anthropic` não é mais necessário — removido do piloto junto com a troca de
Claude Haiku pelo Qwen2-VL-2B-Instruct local.

---

## Monitoramento e Ajustes

### Métricas para Acompanhar

1. **Classificação (CLIP)**:
   - Taxa de falsos positivos (foto animal classificada como "relevante")
   - Taxa de falsos negativos (gráfico descartado)
   - Distribuição de confiança

2. **Descrição (Qwen2-VL-2B local)**:
   - Tempo por imagem (GPU 4-bit vs. CPU)
   - Uso de VRAM (cabe nos 4 GB da RTX 2050 junto com o resto do pipeline?)
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

### Migração para modelo local (decidido)

Já decidido em 2026-07-21 — ver nota de atualização no topo do documento.
Não há previsão de voltar a usar API paga enquanto não houver orçamento
aprovado.

### Se a qualidade do Qwen2-VL-2B for insuficiente

- Testar prompt mais estruturado/específico em português
- Avaliar quantização diferente (8-bit em vez de 4-bit, se a VRAM permitir)
- Avaliar outro VLM pequeno (ex.: SmolVLM2, InternVL2-2B) mantendo o mesmo
  contrato de interface (`describe(imagem, classificação) -> descrição`)
- Como último recurso, reavaliar orçamento para API paga com a equipe do RAN

### Quando Incluir Fotos de Animais?

- Futura integração com reconhecimento de espécies (fine-tuned CLIP + identificação)
- Exemplo: "Quais são as características de identificação do Rhinatrema bivittatum?"
- Por enquanto: descartadas, foco em dados estruturados

---

## Referências

- [CLIP Paper](https://arxiv.org/abs/2103.14030) — Learning transferable visual models
- [Claude Vision API Docs](https://docs.anthropic.com/en/docs/build-a-bot/vision)
- [LLaVA GitHub](https://github.com/haotian-liu/LLaVA) — alternativa local

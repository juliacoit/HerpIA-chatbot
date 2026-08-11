# Piloto: Processamento de Imagens — Comece aqui

## 1. Instalar Dependências (5 min)

```bash
cd scripts/processamento_imagens
pip install -r requirements_imagens.txt
```

**Dependências principais:**
- `torch` — framework de ML (GPU: ~2 GB, CPU: ~500 MB)
- `transformers` — modelos HuggingFace (CLIP + Qwen2-VL-2B-Instruct)
- `accelerate`, `bitsandbytes` — quantização 4-bit do VLM em GPU
- `Pillow` — manipulação de imagens

Tudo roda localmente — **sem chave de API, sem custo** (decisão de 2026-07-21,
falta de verba; ver
[`docs/processos/ESTRATEGIA_PROCESSAMENTO_IMAGENS.md`](../../docs/processos/ESTRATEGIA_PROCESSAMENTO_IMAGENS.md)).

## 2. Nota sobre a GPU (1 min)

A máquina de dev tem uma RTX 2050 com só 4 GB de VRAM, compartilhada com a
indexação de embeddings (BGE-M3). Evite rodar os dois processos pesados ao
mesmo tempo — se a GPU estiver ocupada, o VLM local cai automaticamente para
CPU (mais lento, mas funciona).

## 3. Teste Rápido: Apenas Classificação (10 min, $0)

Antes de rodar o pipeline completo (mais lento por usar o VLM local), valide
que a classificação está funcionando:

```bash
# Teste em um PDF pequeno (ex: 1-2 MB)
python testar_classificacao.py "../../02_publicacoes_cientificas_ran/seu_pdf.pdf"
```

**O que esperar:**
- Extrai imagens do PDF
- Para cada imagem: mostra classificação + distribuição de confiança
- Salva relatório JSON com: total de imagens, taxa de relevância, tipos

**Exemplos de saída:**
```
[1] Página 3 (800x600): gráfico (92%) ✓ RELEVANTE
    Distribuição: gráfico: 92%, mapa: 5%, fotografia: 2%, ...

[2] Página 3 (400x300): fotografia (88%) ✗ descartada
    Distribuição: fotografia: 88%, ilustração: 8%, ...

RESUMO: 2/10 relevantes (20%)
  Gráficos: 3
  Fotografias: 5
  Ilustrações: 2
```

**Se confiante na classificação:** prossiga para Passo 4

**Se muitos falsos positivos/negativos:** 
- Ajuste `--threshold` (padrão: 0.5)
- Exemplo com threshold mais alto: `--threshold 0.7`

## 4. Piloto Completo: Classificar + Descrever (tempo variável, $0)

Agora execute o pipeline completo com o VLM local (primeira execução baixa o
Qwen2-VL-2B-Instruct, ~4 GB):

```bash
python processar_imagens_piloto.py "../../02_publicacoes_cientificas_ran/seu_pdf.pdf"
```

**O que acontece:**
1. Extrai imagens
2. Classifica com CLIP
3. Descreve imagens relevantes com o VLM local (Qwen2-VL-2B-Instruct — GPU
   4-bit se disponível, senão CPU)
4. Salva resultado em JSON
5. Mostra custo total (sempre $0)

**Exemplo de saída:**
```
RESUMO DO PROCESSAMENTO
===============================
PDF: seu_pdf.pdf
Imagens extraídas: 10
Imagens relevantes: 3
Taxa de relevância: 30%

Distribuição de tipos:
  - Gráficos: 2
  - Mapas: 1

Custo total: $0.00 (VLM local — sempre $0)
```

## 5. Revisar Resultados (5 min)

Abra o JSON gerado:

```bash
# Linux/Mac
cat resultado_seu_pdf_20260721_143000.json | head -100

# Windows PowerShell
Get-Content resultado_seu_pdf_20260721_143000.json | Select-Object -First 100
```

**Checklist:**
- [ ] Classificações fazem sentido? (gráficos estão marcados como "gráfico"?)
- [ ] Descrições são úteis? (mencionam dados principais, eixos, tendências?)
- [ ] Fotos de animais foram descartadas?
- [ ] Tempo por imagem está aceitável (GPU 4-bit ou CPU, conforme o que rodou)?

## 6. Relatório de Validação (10 min)

Antes de integrar ao pipeline principal, responda:

### Qualidade de Classificação

- [ ] **Taxa de relevância**: Qual % de imagens foi classificado como relevante?
- [ ] **Falsos positivos**: Quantas fotos de animais foram marcadas como "relevante"?
- [ ] **Falsos negativos**: Algum gráfico/mapa foi descartado por erro?

### Qualidade de Descrição

- [ ] **Estrutura**: As descrições mencionam tipo, dados principais, eixos?
- [ ] **Precisão**: Estão corretas as informações extraídas?
- [ ] **Rastreabilidade**: Consegue voltar da descrição para a imagem original?

### Tempo/Recursos (não há custo de API — 100% local)

- [ ] **Tempo real por imagem**: GPU (4-bit) vs. CPU?
- [ ] **Escalabilidade**: Quantas imagens por lote é viável rodar de uma vez, dado que a GPU é compartilhada com a indexação de embeddings?

## 7. Próximos Passos

### Se tudo OK:

1. Repita com 5-10 PDFs diferentes (validar robustez)
2. Ajuste prompts de descrição se necessário
3. Documente insights em `docs/processos/VALIDACAO_PILOTO_IMAGENS.md`
4. Inicie integração ao pipeline principal (Fase 3)

### Se houver problemas:

1. Compartilhe relatório JSON comigo
2. Aumentar threshold para reduzir falsos positivos
3. Experimentar prompts diferentes
4. Considerar VLM local alternativo (ex.: SmolVLM2, InternVL2-2B)

## Arquivos Criados

```
scripts/processamento_imagens/
├── processar_imagens_piloto.py      ← Pipeline completo (CLIP + VLM local)
├── testar_classificacao.py           ← Teste rápido (apenas CLIP)
├── requirements_imagens.txt          ← Dependências
├── README.md                         ← Documentação
└── COMECE_AQUI.md                   ← Este arquivo
```

## Documentação Relacionada

- [`docs/processos/ESTRATEGIA_PROCESSAMENTO_IMAGENS.md`](../../docs/processos/ESTRATEGIA_PROCESSAMENTO_IMAGENS.md) — estratégia completa
- [`docs/roadmap.md`](../../docs/roadmap.md) — roadmap

## Suporte

Se encontrar erros ou tiver dúvidas, consulte:

1. **ImportError**: `pip install -r requirements_imagens.txt`
2. **CUDA out of memory**: o VLM local cai para CPU automaticamente (mais
   lento); evite rodar junto com a indexação de embeddings na mesma GPU de 4 GB

Boa sorte! 🚀

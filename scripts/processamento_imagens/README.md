# Processamento de Imagens em PDFs

Scripts para extrair, classificar e descrever imagens em PDFs usando CLIP e Claude Haiku.

## Instalação de Dependências

```bash
# Instalar dependências adicionais
pip install -r requirements_imagens.txt

# Verificar que ANTHROPIC_API_KEY está definida em .env
# Exemplo em .env:
# ANTHROPIC_API_KEY=sk-ant-...
```

## Script Principal: `processar_imagens_piloto.py`

Pipeline de 3 etapas:

1. **Extração**: PyMuPDF extrai todas as imagens do PDF
2. **Classificação**: CLIP classifica cada imagem (gráfico? mapa? fotografia?)
3. **Descrição**: Claude Haiku descreve as imagens relevantes com estrutura

### Uso Básico

```bash
python processar_imagens_piloto.py <caminho_pdf>
```

### Exemplos

```bash
# Processar um PDF específico
python processar_imagens_piloto.py "../../02_publicacoes_cientificas_ran/exemplo.pdf"

# Especificar diretório de saída
python processar_imagens_piloto.py "exemplo.pdf" --output resultados/

# Apenas classificar (sem descrever = sem custo de API)
python processar_imagens_piloto.py "exemplo.pdf" --skip-description

# Aumentar threshold de confiança (menos falsos positivos)
python processar_imagens_piloto.py "exemplo.pdf" --threshold 0.7
```

### Argumentos

| Argumento | Padrão | Descrição |
|-----------|--------|-----------|
| `pdf_path` | - | Caminho do PDF (obrigatório) |
| `--output` | `.` | Diretório de saída para JSON |
| `--threshold` | `0.5` | Mínimo de confiança para classificar como relevante (0-1) |
| `--skip-description` | - | Só classifica, não descreve (economiza $) |

### Saída

Arquivo JSON com estrutura:

```json
{
  "pdf": "caminho/do/arquivo.pdf",
  "timestamp": "2026-07-21T14:30:00",
  "imagens_totais": 42,
  "imagens_relevantes": 25,
  "classificacoes": [
    {
      "image_id": 0,
      "page": 3,
      "width": 800,
      "height": 600,
      "is_relevant": true,
      "classification": "gráfico",
      "confidence": 0.92,
      "reason": "Classe: um gráfico de barras... (92%)"
    }
  ],
  "descricoes": [
    {
      "image_id": 0,
      "page": 3,
      "classification": "gráfico",
      "description": "Gráfico de barras mostrando...",
      "tokens_input": 1234,
      "tokens_output": 156,
      "cost_usd": 0.0034
    }
  ],
  "custo_total_usd": 0.0850,
  "resumo": {
    "gráficos": 12,
    "mapas": 8,
    "diagramas": 3,
    "tabelas": 2,
    "fotografias": 15,
    "ilustrações": 2
  }
}
```

## Classificação de Imagens

CLIP usa zero-shot classification com estas classes:

- ✅ **Relevante para RAG**:
  - Gráfico de barras ou linhas com dados científicos
  - Mapa geográfico ou de distribuição de espécies
  - Diagrama ou esquema científico
  - Tabela de dados ou números

- ❌ **Descartada**:
  - Fotografia de um animal
  - Ilustração decorativa

### Threshold

- **0.5** (padrão): Balanço entre precisão e recall
- **0.7+**: Mais conservador, menos falsos positivos
- **<0.5**: Mais permissivo, pode pegar fotos de animais

## Custos de API

Baseado em Claude Haiku:

- **Input**: $0.80 por 1M tokens
- **Output**: $0.40 por 1M tokens

Por imagem:
- ~1000 tokens input (imagem codificada)
- ~150-300 tokens output (descrição)
- **Custo**: ~$0.002 USD/imagem

Exemplo com 59.080 chunks (2-6k imagens totais, 60% relevantes = ~1.2-3.6k descritas):
- **Custo total**: $2-8 USD por reindexação completa

## Próximas Etapas

### Fase 1 (Esta)
- [x] Documentar estratégia
- [ ] Testar com 2-3 PDFs reais
- [ ] Validar qualidade de classificação e descrição
- [ ] Registrar custos reais

### Fase 2
- [ ] Otimizar prompts de descrição
- [ ] Ajustar threshold de classificação
- [ ] Testar em 20-30 PDFs
- [ ] Documentar edge cases

### Fase 3
- [ ] Integrar ao pipeline de indexação principal
- [ ] Armazenar descrições em `07_processados/imagens_descritas/`
- [ ] Indexar no Qdrant
- [ ] Testar recuperação

## Troubleshooting

### ImportError: No module named 'transformers'

```bash
pip install -r requirements_imagens.txt
```

### RuntimeError: CUDA out of memory

Use CPU para CLIP (mais lento, mas funciona):
- Modelo CLIP é pequeno (~330 MB)
- Automaticamente usa CPU se GPU não disponível

### Erro: "ANTHROPIC_API_KEY não está definida"

Adicionar em `.env`:
```
ANTHROPIC_API_KEY=sk-ant-...
```

### PDF com muitas imagens (1000+) demora muito

Use `--skip-description` para teste rápido:
```bash
python processar_imagens_piloto.py grande.pdf --skip-description
```

Depois rode apenas nas relevantes.

## Implementação Futura

- **Modelo local**: Migrar descrição para LLaVA/MiniCPM se volume crescer
- **Cache**: Armazenar descrições já feitas (reprocesso apenas de PDFs novos)
- **Validação**: Feedback do usuário sobre qualidade de descrições
- **OCR**: Integração com Tesseract para gráficos em imagens escaneadas

---

Documentação relacionada:
- [`docs/processos/ESTRATEGIA_PROCESSAMENTO_IMAGENS.md`](../../docs/processos/ESTRATEGIA_PROCESSAMENTO_IMAGENS.md) — estratégia completa
- [`docs/roadmap.md`](../../docs/roadmap.md) — roadmap do projeto

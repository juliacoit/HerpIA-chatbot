# Fontes de dados: estruturas, conteúdo e utilidade para o RAG

Documento de referência sobre os dados disponíveis no projeto — o que cada fonte contém,
como está estruturada e como pode ser útil para o chatbot RAG do RAN/ICMBio.

**Atualizado em:** 2026-06-25

---

## Visão geral

| Fonte | Volume | Formato bruto | Status da coleta |
|---|---|---|---|
| SALVE | ~2086 fichas (répteis + anfíbios) | JSON por ficha | 🔶 Coleta completa em andamento |
| PANs | 74 PANs, 1141 documentos | PDF, XLSX, ZIP | ✅ Metadados completos; PDFs copiados |
| Programa Monitora | 163 documentos em 8 categorias | PDF | ✅ Metadados completos; PDFs copiados |

---

## 1. SALVE — Sistema de Avaliação do Risco de Extinção

**O que é:** Avaliações científicas formais de espécies quanto ao risco de extinção,
produzidas por especialistas e publicadas com DOI pelo ICMBio. Cada ficha representa
uma espécie com seu diagnóstico de conservação mais recente.

**Arquivos:** `01_fontes_web/salve/fichas/<slug>/metadados.json`
**Extração:** `07_processados/textos_extraidos/salve/<slug>.json`
**Script de coleta:** `scripts/coleta/coleta_salve.py`
**Script de extração:** `scripts/processamento/extrair_texto_salve.py`

### Estrutura das seções (após extração)

| Seção | Conteúdo | Tamanho típico |
|---|---|---|
| `visao_geral` | Justificativa da categoria de risco (parágrafo denso, fundamentado em dados) + autoria + citação recomendada | 2–4 mil chars |
| `taxonomia` | Árvore taxonômica completa (Reino → Espécie), sinonímias, nomes comuns em vários idiomas | 300–600 chars |
| `distribuicao` | Distribuição global e no Brasil, estados, biomas, bacias hidrográficas, EOO em km² | 600–1500 chars |
| `historia_natural` | Habitat, comportamento, dieta, reprodução, biometria (comprimento, peso, ninhada) | 2–6 mil chars |
| `populacao` | Tendência populacional, tempo geracional, observações quantitativas disponíveis | 500–2000 chars |
| `ameacas` | Narrativa das principais ameaças + categorias hierárquicas IUCN (ex: "7.1.1 – Aumento de incêndios") | 1–4 mil chars |
| `uso` | Uso humano da espécie (comércio, subsistência, tráfico, etc.) | 100–500 chars |
| `conservacao` | Ações em curso, histórico de avaliações de risco (ciclos anteriores, avaliações globais), UCs com registro, ações necessárias | 1–3 mil chars |
| `pesquisa` | Lacunas de conhecimento e pesquisas recomendadas | 300–1000 chars |
| `referencias` | Lista bibliográfica completa citada na ficha | 3–8 mil chars |

### Metadados por ficha

- `nome_cientifico`, `nome_cientifico_atual`, `nome_comum`
- `grupo`: Répteis ou Anfíbios
- `categoria_risco`: EX / EW / CR / EN / VU / NT / LC / DD
- `bioma`: Amazônia, Cerrado, Mata Atlântica, Pantanal, Caatinga, Pampas, Costeiro/Marinho
- `estados`: siglas dos estados com ocorrência confirmada
- `doi`: identificador permanente (ex: `10.37002/salve.ficha.20244.3`)
- `url_origem`: URL da ficha na API do SALVE
- `data_coleta`: data de coleta dos dados

### Utilidade para o RAG

- **Perguntas sobre status de conservação:** *"O jacaré-do-papo-amarelo está ameaçado?"*
- **Listagens por critério:** *"Quais anfíbios CR ocorrem no Cerrado?"*
- **Justificativa da ameaça:** *"Por que a Tartaruga-do-pantanal é Vulnerável?"*
- **Biologia e distribuição:** *"Em que estados ocorre a Acanthochelys macrocephala?"*
- **Histórico de avaliações:** *"O status da espécie X mudou desde 2012?"*
- **Complemento ao PAN:** ligar espécies do SALVE às ações do PAN correspondente

### Observações

- As fichas são públicas no site do ICMBio — conteúdo considerado autorizado para indexação.
- Coordenadas precisas de ocorrência **não estão nas fichas** (apenas estados e biomas) — sem risco de sensibilidade geográfica.
- A seção `referencias` é longa mas menos útil para recuperação direta — pode receber tratamento diferenciado no chunking.

---

## 2. PANs — Planos de Ação Nacional para Conservação de Espécies Ameaçadas

**O que é:** Instrumentos de gestão do ICMBio que estabelecem estratégias prioritárias
de conservação para grupos de espécies ameaçadas. Cada PAN tem vigência de 5 anos e
pode ter múltiplos ciclos.

**Arquivos:** `01_fontes_web/pans/<slug>/metadados.json` + `<slug>/documentos/*.pdf`
**Script de coleta:** `scripts/coleta/coleta_pans.py`

### Volume e status

- **74 PANs** no total: 40 em execução, 34 finalizados
- **1141 documentos:** 823 PDFs + 294 planilhas XLSX + 24 ZIPs
- **707 PDFs baixados** em `01_fontes_web/pans/*/documentos/`

### PANs diretamente relevantes para herpetofauna

| PAN | Espécies-alvo | Vigência | Status |
|---|---|---|---|
| Herpetofauna do Sudeste | 95 (55 ameaçadas) | 2024–2029 (2º ciclo) | Em execução |
| Herpetofauna do Nordeste | — | — | Em execução |
| Herpetofauna do Sul | — | — | Em execução |
| Herpetofauna do Espinhaço | — | — | Finalizado |
| Herpetofauna Insular | — | — | Finalizado |
| Quelônios | — | — | Finalizado |
| Tartarugas Marinhas | — | — | Em execução |

Os demais 67 PANs cobrem outros grupos (aves, mamíferos, peixes, plantas etc.) e são
relevantes para contexto institucional mais amplo ou quando a pergunta envolve conservação
no Brasil de forma geral.

### Tipos de documentos

| Tipo | Qtd (estimado) | Conteúdo | Prioridade para RAG |
|---|---|---|---|
| **Sumário Executivo** (PDF) | 95 | Texto narrativo completo: diagnóstico, espécies-alvo, ameaças, ações prioritárias (80–200 pág.) | ⭐⭐⭐ Alta |
| **Boletim informativo** (PDF) | 46 | Comunicados periódicos sobre andamento do PAN | ⭐⭐ Média |
| **Relatório de atividades** (PDF) | 37 | Resultados e avaliação de ciclo | ⭐⭐ Média |
| **Portaria** (PDF) | 182 | Ato oficial de aprovação — texto jurídico, pouco conteúdo técnico | ⭐ Baixa |
| **Matriz de Planejamento** (XLSX) | 106 | Ações, metas, prazos, responsáveis — dado estruturado valioso, mas exige parser separado | ⭐⭐ Média (futura) |
| **Matriz de Monitoria** (XLSX) | 95 | Indicadores de progresso — dado estruturado | ⭐ Baixa (futura) |

> **Atenção:** as planilhas XLSX e ZIPs **não serão extraídas** na pipeline de PDF atual.
> O conteúdo mais rico está nos PDFs de Sumário Executivo.

### Metadados por PAN

- `nome`: nome do PAN
- `slug`: identificador único
- `url`: página oficial no gov.br
- `status`: `em_execucao` ou `finalizado`
- `data_coleta`: data da coleta dos metadados
- Por documento: `texto_link`, `contexto` (trecho do texto da página onde o link aparecia), `url`, `nome_arquivo`, `extensao`, `ciclo` (1 ou 2)

### Utilidade para o RAG

- **Estratégias de conservação:** *"Quais ações prioritárias existem para anfíbios do Nordeste?"*
- **Espécies-alvo:** *"Quais espécies estão no PAN Herpetofauna do Sudeste?"*
- **Ameaças identificadas formalmente:** *"Quais ameaças o PAN identificou para quelônios?"*
- **Ações em andamento vs. concluídas:** distinção entre PANs em execução e finalizados
- **Contexto institucional:** explica o que o ICMBio está fazendo formalmente em conservação
- **Complemento ao SALVE:** enquanto o SALVE documenta o status das espécies, o PAN documenta o que está sendo feito sobre isso

---

## 3. Programa Monitora

**O que é:** O Programa Nacional de Monitoramento da Biodiversidade do ICMBio.
Coleta dados sistemáticos sobre biodiversidade em Unidades de Conservação federais,
com participação de monitores comunitários. Os documentos cobrem metodologias,
resultados científicos e estrutura operacional do programa.

**Arquivos:** `01_fontes_web/monitora/<categoria>/metadados.json` + `<categoria>/documentos/*.pdf`
**Script de coleta:** `scripts/coleta/coleta_monitora.py`

### Volume

- **163 documentos** em 8 categorias
- **109 PDFs baixados** em `01_fontes_web/monitora/*/documentos/`

### Categorias e conteúdo

| Categoria | Docs | Conteúdo | Prioridade para RAG |
|---|---|---|---|
| **Materiais de Apoio** | 94 | Protocolos de campo, fichas de amostragem, manuais metodológicos, guias de identificação de espécies | ⭐⭐⭐ Alta |
| **Artigos** | 27 | Publicações científicas geradas com dados do Monitora (revistas nacionais e internacionais) | ⭐⭐⭐ Alta |
| **Livros, Monografias, Dissertações** | 13 | Obras científicas extensas com dados do programa | ⭐⭐ Média |
| **Relatórios** | 10 | Relatórios de atividades e resultados do programa | ⭐⭐ Média |
| **Encontro dos Saberes** | 10 | Documentos do evento que integra conhecimento científico e tradicional/comunitário | ⭐ Baixa |
| **Legislação** | 6 | Normas e portarias que regem o programa | ⭐ Baixa |
| **Dados** | 2 | Planilhas de dados brutos coletados em campo | ⭐ Baixa (formato difícil) |
| **Estrutura do Programa** | 1 | Documento-base descrevendo a arquitetura do Monitora | ⭐⭐ Média |

### Utilidade para o RAG

- **Metodologias de monitoramento:** *"Como é feito o monitoramento de anfíbios em UCs?"*
- **Descrição do programa:** *"O que é o Programa Monitora e como funciona?"*
- **Resultados científicos:** artigos com dados empíricos sobre biodiversidade em UCs
- **Participação comunitária:** tema recorrente nos artigos — relevante para perguntas sobre gestão participativa
- **Protocolos padronizados:** os Materiais de Apoio definem os métodos oficiais do ICMBio para monitoramento de campo

---

## Como as três fontes se complementam

O potencial do RAG está na **combinação entre fontes** para responder perguntas complexas:

```
Pergunta: "Por que a Tartaruga-do-pantanal está ameaçada e o que está sendo feito?"

SALVE  →  Categoria VU, justificativa (incêndios, pecuária, hidrovias),
           histórico de avaliações, distribuição, tempo geracional

PANs   →  PAN Quelônios: ações de conservação específicas planejadas,
           espécies-alvo, metas de 5 anos, responsáveis institucionais

Monitora → Protocolo de monitoramento de quelônios em UCs (se existir),
            dados de campo e resultados de monitoramento
```

```
Pergunta: "Quais anfíbios ameaçados ocorrem na Mata Atlântica do Sudeste?"

SALVE   →  Lista de espécies CR/EN/VU com distribuição no Sudeste/Mata Atlântica
PANs    →  PAN Herpetofauna do Sudeste: lista oficial das 55 espécies prioritárias
            com diagnóstico e justificativa de priorização
```

---

## O que os dados ainda não cobrem

| Lacuna | Fonte futura |
|---|---|
| Localização precisa de espécies (coordenadas) | Não será indexada — dado sensível |
| Dados quantitativos brutos de monitoramento | Monitora/Dados (2 planilhas) — processamento futuro |
| Documentos administrativos internos | SEI/ICMBio — acesso restrito, apenas exportações autorizadas |
| Literatura científica dos pesquisadores do RAN | `02_publicacoes_cientificas_ran/` — a organizar |
| Matrizes de planejamento dos PANs (XLSX) | Processamento futuro separado |

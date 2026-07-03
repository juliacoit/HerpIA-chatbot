# Seleção de processos do SEI para exportação

- **Status:** Lista gerada (197 processos); autorização de exportação pendente com a equipe do RAN
- **Última atualização:** 2026-07-03
- **Arquivo resultante:** `01_fontes_web/sei/processos_para_exportacao.json`
- **Processos descartados (com motivo):** `01_fontes_web/sei/processos_descartados.json` (e `.csv`)

## O problema

O catálogo completo do SEI — resultado do script `listar_documentos_sei.py` — tem **417 processos** distribuídos em 16 blocos prioritários, com **28.100 documentos** no total. Não é viável revisar tudo manualmente de uma vez. Antes de levar a lista para a equipe do RAN decidir o que exportar, precisamos de uma triagem automática para descartar o que claramente não tem conteúdo técnico indexável.

O objetivo da triagem não é decidir o que vai para a base de conhecimento — isso é responsabilidade da equipe do RAN. O objetivo é reduzir o volume de análise humana, priorizando os processos com maior probabilidade de conter documentos úteis.

## Os dois critérios de filtro

A triagem usa dois critérios aplicados em sequência. Um processo só entra na lista se passar pelos **dois**:

---

### Critério 1 — Tipo de processo técnico

O campo `Tipo` de cada processo no SEI indica o assunto geral. Processos com tipo puramente administrativo (viagem, diárias, compras, contratações) são descartados nessa etapa, mesmo que estejam nos blocos prioritários.

**Tipos aceitos (30 tipos):**

| Categoria | Tipos |
|---|---|
| Fauna e espécies | FAUNA, ESPÉCIES AMEAÇADAS, ESPÉCIES EXÓTICAS INVASORAS, CAPTURA DE EXEMPLARES, MANEJO DE ANIMAIS |
| Planejamento e conservação | PLANO, PLANO DE MANEJO, IMPLEMENTAÇÃO DE PAN, PROJETO, PROJETO DE PESQUISA |
| Monitoramento e pesquisa | MONITORAMENTO, PESQUISA, ESTUDO |
| Documentos normativos | INSTRUÇÃO NORMATIVA, PORTARIA, PARECER |
| Publicações e guias | PUBLICAÇÃO, PUBLICAÇÃO BIBLIOGRÁFICA, GUIA *(implícito)* |
| Cooperação | COOPERAÇÃO TÉCNICA, DADOS GEOESPACIAIS |
| Atividades institucionais | OFICINA, CURSO DE CAPACITAÇÃO, GRUPO DE TRABALHO, COMITÊ, PROPOSTA |
| Informação/Consultoria | INFORMAÇÃO, CONSULTORIA, RELATÓRIO, RELATÓRIO DE ATIVIDADE, MOÇÃO |

**Tipos descartados (exemplos dos 44 tipos excluídos):**

| Tipo | Processos descartados |
|---|---|
| CONSULTA | 31 |
| VIAGEM A SERVIÇO | 26 |
| SOLICITAÇÃO | 20 |
| PROTOCOLO | 10 |
| PROCESSO ADMINISTRATIVO | 10 |
| EVENTO | 8 |
| GESTÃO DE UNIDADE DE CONSERVAÇÃO | 7 |
| DIÁRIAS E PASSAGENS | 6 |
| ... | ... |

Resultado do Critério 1: **244 processos passam** (173 descartados).

---

### Critério 2 — Pelo menos um documento com título técnico

O tipo do processo indica o assunto geral, mas um processo do tipo MONITORAMENTO pode ter 80 ofícios e convites e apenas 2 relatórios. O Critério 2 olha para os **títulos dos documentos dentro de cada processo** e exige que pelo menos um título contenha um termo técnico — e que esse mesmo documento não seja claramente administrativo.

#### Como a verificação funciona

Para cada documento em um processo, a lógica é:

```
titulo_normalizado = titulo.lower()  # ignora maiúsculas

é_técnico = qualquer palavra de TITULOS_TECNICOS está no título
é_tramite = qualquer palavra de TITULOS_TRAMITE está no título

documento conta como técnico se: é_técnico E NÃO é_tramite
```

O processo passa se tiver **pelo menos 1 documento técnico** por esse critério.

#### Palavras-chave de documentos técnicos (`TITULOS_TECNICOS`)

```
relatório, nota técnica, informação técnica, it , ata , matriz,
plano, estudo, laudo, parecer, portaria, instrução normativa,
publicação, guia, manual, inventário, diagnóstico, ficha,
resultado, monitoramento, expedição, oficina, planilha,
formulário de campo, relatório de campo, relatório final,
relatório técnico, relatório de atividade, relatório mensal,
moção, termo de referência, projeto, protocolo de monitoramento,
relatório fotográfico
```

#### Palavras-chave de documentos de tramitação administrativa (`TITULOS_TRAMITE`)

```
memorando abertura, despacho, ofício, oficio, e-mail, convite,
encaminhamento, solicitação, autorização, recibo, nota de empenho,
certidão, declaração, comunicação interna, ci , memorando ,
protocolo , minuta, planilha de custos, comprovante, passagem,
bilhete, ordem bancária
```

A lista de exclusão é usada para evitar falsos positivos. Um documento com título "Autorização de Pesquisa" contém "autorização" (tramitação) mas não contém termos técnicos. Já "Relatório de Campo - Quelônios RDS Mamirauá 2023" contém "relatório de campo" (técnico) e não contém termos de tramitação — é contado como técnico.

Resultado do Critério 2: **197 processos passam** (47 descartados dos 244 que vieram do Critério 1).

Os 220 processos descartados no total (173 do Critério 1 + 47 do Critério 2), com o motivo de cada descarte, estão listados em `01_fontes_web/sei/processos_descartados.json` (e versão `.csv`). Nenhum processo é removido do catálogo — os descartados continuam em `01_fontes_web/sei/documentos_por_processo.json`, apenas fora da lista de exportação.

---

## Resultado final

**197 processos** selecionados para revisão humana, distribuídos por bloco:

| Bloco | Processos |
|---|---|
| Monitoramento da fauna / Programa Monitora | 52 |
| PAN Cerrado Pantanal - CERPAN | 30 |
| PAN Nordeste | 15 |
| Quelônios amazônicos | 14 |
| Avaliação do risco de extinção da Herpetofauna | 13 |
| PAN Sudeste | 12 |
| PAN Sul | 12 |
| Guias/Publicações | 12 |
| Alvo Complementar Quelônios Amazônicos - Monitora | 11 |
| Espécies Invasoras/Espécies Migratórias | 6 |
| PAN Espinhaço | 6 |
| Crocodilianos | 5 |
| Avaliação do Estado de Conservação da Fauna | 5 |
| Comitê Científico do RAN | 2 |
| PAN Baixo Iguaçu | 1 |
| PAN Paraíba do Sul | 1 |
| **Total** | **197** |

Cada processo no arquivo tem:
- `docs_tecnicos_identificados`: lista dos títulos (com ID interno SEI) que passaram no Critério 2
- `n_docs_tecnicos`: quantidade de documentos técnicos encontrados (mediana = 5, variação = 1 a 61)
- `status_exportacao`: começa como `"pendente"` — a equipe do RAN atualiza para `"autorizado"` ou `"excluir"` conforme decide

---

## Limitações e cuidados

**Falsos positivos (processo passou, mas pode não ter conteúdo útil)**

- O filtro detecta títulos com palavras-chave, mas não avalia a qualidade do conteúdo. Um "Relatório de Atividade 3" pode ser apenas 1 página com informações genéricas.
- 39 processos passaram com **apenas 1 documento técnico identificado** — nesses casos, a revisão humana é especialmente importante.
- Algumas categorias têm alta variabilidade de conteúdo (ex.: COMITÊ — pode conter atas técnicas riquíssimas ou apenas atas de encaminhamento).

**Falsos negativos (processo descartado, mas poderia ter conteúdo útil)**

- O filtro descarta processos cujos documentos técnicos têm **títulos genéricos** (ex.: "Documento 47", "Arquivo 3", "Anexo"). No SEI, a qualidade dos títulos varia muito entre unidades.
- Processos com tipo excluído (ex.: EVENTO) podem ocasionalmente conter relatórios técnicos de peso. A lista de tipos aceitos é ampla, mas não é exaustiva.
- Processos dos blocos prioritários que ficaram **fora dos 16 blocos** não foram analisados pelo script — os blocos não-prioritários não estão em `documentos_por_processo.json`.

**O filtro não substitui a decisão humana**

A lista de 197 processos é um ponto de partida para a equipe do RAN, não uma seleção final. A autorização de exportação — e a avaliação de sensibilidade de cada documento — é sempre responsabilidade de um servidor autorizado.

---

## Como usar o arquivo `processos_para_exportacao.json`

O arquivo pode ser usado como lista de trabalho pela equipe do RAN:

1. Abrir o arquivo (ou importar em uma planilha via `jq` ou Python)
2. Para cada processo, ver `docs_tecnicos_identificados` — os títulos dos documentos que o filtro identificou como técnicos
3. Marcar `status_exportacao` como `"autorizado"` ou `"excluir"` para cada processo
4. Para processos autorizados: exportar os documentos manualmente pelo SEI e salvar em `04_documentos_pendentes_avaliacao/sei/`
5. Após a exportação: avaliar sensibilidade individualmente e mover aprovados para `03_documentos_autorizados/sei/`

### Ver a lista no terminal

```bash
# Resumo dos processos (número, bloco, tipo, n_docs_técnicos)
python3 -c "
import json
data = json.load(open('01_fontes_web/sei/processos_para_exportacao.json'))
for p in data['processos']:
    print(p['numero'], '|', p['bloco'][:40], '|', p['tipo'], '|', p['n_docs_tecnicos'], 'docs técnicos')
"

# Ver docs técnicos de um processo específico
python3 -c "
import json
data = json.load(open('01_fontes_web/sei/processos_para_exportacao.json'))
proc = next(p for p in data['processos'] if p['numero'] == '02071.000061/2022-82')
for d in proc['docs_tecnicos_identificados']:
    print(d)
"
```

---

## Relação com outros documentos

- Critérios de seleção por blocos internos: [`docs/decisoes/0004-criterios-selecao-documentos-sei.md`](../decisoes/0004-criterios-selecao-documentos-sei.md)
- Detalhamento técnico dos scripts de coleta: [`docs/processos/coleta_sei_detalhado.md`](coleta_sei_detalhado.md)
- Regras de sensibilidade e autorização: [`docs/decisoes/0002-classificacao-sensibilidade-documentos.md`](../decisoes/0002-classificacao-sensibilidade-documentos.md)
- Processos descartados na triagem, com motivo do descarte: [`01_fontes_web/sei/processos_descartados.json`](../../01_fontes_web/sei/processos_descartados.json) (e `.csv`)

# 0004. Critérios de seleção de documentos do SEI/ICMBio para indexação

- **Status:** Decisão parcial tomada — triagem por blocos internos implementada; autorização de exportação pendente
- **Data:** 2026-06-26 (atualizado 2026-06-30 e 2026-10-20)
- **Responsável(eis):** Julia Coite

## Contexto

O SEI/ICMBio é o sistema de gestão de processos administrativos do órgão. Diferente das outras fontes (SALVE, PANs, Monitora), o SEI requer login institucional e os documentos precisam ser avaliados e autorizados antes de qualquer indexação (ver ADR 0002).

A abordagem inicial previa usar **marcadores** (tags aplicadas a processos) como critério primário de triagem. Após exploração técnica em 2026-06-30, identificou-se que os **blocos internos** são mais eficazes: representam a organização temática que a própria equipe do RAN já fez de seus processos, com anotações descritivas por processo.

## Decisão

### Estratégia de seleção

Usar os **blocos internos do SEI** como critério primário de triagem. Os blocos internos são pastas de organização criadas pela equipe do RAN, já categorizadas tematicamente — refletem diretamente os assuntos de interesse do chatbot.

A seleção por marcadores (estratégia anterior) permanece válida como estratégia complementar para processos que estejam fora dos blocos, mas não é a abordagem principal.

### Blocos prioritários (16 blocos, ~464 processos)

| Bloco | Processos | Relevância |
|---|---|---|
| Avaliação do risco de extinção da Herpetofauna | 26 | Alta — core do trabalho do RAN |
| Processo de Avaliação do Estado de Conservação da Fauna | 17 | Alta — complementa anterior |
| PAN Cerrado Pantanal - CERPAN | 54 | Alta |
| PAN Nordeste | 36 | Alta |
| PAN Sul | 36 | Alta |
| PAN Sudeste | 27 | Alta |
| PAN Espinhaço | 11 | Alta |
| PAN Baixo Iguaçu | 2 | Alta |
| PAN Paraíba do Sul | 4 | Alta |
| Quelônios amazônicos | 29 | Alta |
| Crocodilianos | 14 | Alta |
| Monitoramento da fauna / Programa Monitora | 163 | Alta |
| Processos do Alvo Complementar Quelônios Amazônicos - Monitora | 12 | Alta |
| Espécies Invasoras/Espécies Migratórias | 12 | Alta |
| Guias/Publicações | 19 | Alta |
| Comitê Científico do RAN | 2 | Alta |

### Classificação por tipo de processo

Dentro dos blocos prioritários, os processos foram classificados por tipo:

- **Técnicos (~194 proc):** FAUNA, PLANO, MONITORAMENTO, PUBLICAÇÃO, RELATÓRIO, PESQUISA, INFORMAÇÃO, MOÇÃO, CONSULTORIA — maior probabilidade de conter documentos indexáveis
- **Outros relevantes (~100 proc):** ESPÉCIES AMEAÇADAS, PLANO DE MANEJO, PROJETO DE PESQUISA, OFICINA, MANEJO DE ANIMAIS, IMPLEMENTAÇÃO DE PAN, ESTUDO, INSTRUÇÃO NORMATIVA — avaliar caso a caso
- **Administrativos (~170 proc):** DIÁRIAS, VIAGEM, CONTRATAÇÃO, FÉRIAS, RECONHECIMENTO DE DÍVIDA — excluir

### Fluxo de seleção

1. `listar_blocos_sei.py` → cataloga blocos e processos (`blocos_internos.json`)
2. `listar_documentos_sei.py` → para cada processo prioritário, lista documentos internos sem ler conteúdo (`documentos_por_processo.json`)
3. Análise do catálogo → identificar processos com documentos técnicos reais (não só ofícios e despachos)
4. Decisão com equipe do RAN → quais processos têm autorização de exportação
5. Exportação manual pelo SEI → `04_documentos_pendentes_avaliacao/sei/`
6. Avaliação de sensibilidade → `03_documentos_autorizados/sei/` (se aprovado)

### O que NÃO será indexado

- Processos puramente administrativos (férias, contratos de TI, diárias, suprimento de fundos)
- Processos com dados pessoais (gestão de pessoas, afastamentos por saúde)
- Qualquer processo sem autorização explícita da equipe do RAN
- Documentos com localização precisa de espécies ameaçadas (risco de biopirataria)

## Ferramentas implementadas

| Script | Função |
|---|---|
| `scripts/coleta/listar_blocos_sei.py` | Lista todos os blocos internos e seus processos |
| `scripts/coleta/listar_documentos_sei.py` | Lista documentos dentro de cada processo prioritário |

Ambos fazem login automatizado via SIP (requests + BeautifulSoup) e navegam o SEI respeitando os mecanismos de `infra_hash`. Nenhum conteúdo de documento é lido ou transmitido — apenas metadados (título, tipo, ID interno).

Ver detalhamento técnico em [`docs/processos/coleta_sei_detalhado.md`](coleta_sei_detalhado.md).

## Próximas etapas

- [x] Implementar `listar_blocos_sei.py` e catalogar os 43 blocos
- [x] Implementar `listar_documentos_sei.py` para os 16 blocos prioritários
- [x] Analisar `documentos_por_processo.json` — triagem automática gerou lista de 173 processos candidatos em `processos_para_exportacao.json` (v2 após correção de falsos positivos em 2026-07-13; ver [`docs/processos/selecao_processos_sei.md`](../processos/selecao_processos_sei.md))
- [ ] Validar com a coordenação do RAN quais processos têm autorização de exportação
- [ ] Definir critério de sensibilidade específico para processos com localização de espécies
- [ ] Realizar primeira exportação piloto e mover para `04_documentos_pendentes_avaliacao/sei/`

## Atualização 2026-10-20

Orientação da coordenação do RAN, em troca de mensagens com a Júlia. Não
muda o status nem a decisão acima: **confirma** os blocos internos como
critério.

### Situação

- O SEI continua **não indexado**.
- A Júlia tem acesso próprio ao SEI.
- Há uma planilha de processos relevantes aguardando preenchimento pelo ponto
  focal do Monitora.

### Revisão dos blocos internos

- Segundo a coordenação, os blocos **passaram por revisão recente**: foram
  reagrupados e subdivididos por tema. Exemplos de títulos novos:
  "Autorização/licenciamento ambiental" e "Consulta sobre implementação de
  ações de PAN".
- São cerca de 30 blocos, e uns 20 são altamente relevantes. Esses números
  diferem do catálogo atual (43 blocos, 16 prioritários), gerado em
  2026-06-30, antes da revisão.
- **O catálogo (`blocos_internos.json`) provavelmente precisa ser
  regenerado.** Isso exige login no SEI e só a Júlia pode autorizar.

### Tipos de documento

Complementa a exclusão de processos administrativos (seção "O que NÃO será
indexado"), agora no nível do documento:

- **Manter:** notas técnicas, pareceres, relatórios e relatórios finais,
  projetos, avaliações de projetos e orientações técnicas, ou seja,
  documentos com trabalho analítico ou técnico especializado.
- **Excluir:** despachos simples e anexos sem relevância.

### Próximos passos propostos

1. Sessão presencial com a coordenação para filtrar os blocos relevantes,
   validando a triagem que já existe (173 processos candidatos, ver
   [`selecao_processos_sei.md`](../processos/selecao_processos_sei.md)).
2. Se os blocos mudaram, atualizar o catálogo e contar os documentos técnicos
   e o nível de acesso por bloco.
3. Definir os critérios com a equipe.
4. Piloto com 1 ou 2 blocos.
5. Ampliação.

### Decisões em aberto

- **Acesso:** indexar só documentos de acesso público, ou também os
  restritos, com controle de acesso por usuário? Sem esse controle, qualquer
  usuário do HerpIA pode receber trechos de um documento restrito.
- **Dados pessoais:** como tratá-los, por exemplo com anonimização, como no
  pipeline atual.
- **Sensibilidade e avaliação:** qual valor de `nivel_sensibilidade` os
  chunks do SEI recebem, e se vão ou não ao juiz externo do RAGAS. Pelo
  [ADR 0007](0007-avaliacao-offline-ragas-juiz-claude.md), só `autorizado` vai
  à API.

### Objetivo futuro (fase separada)

A coordenação quer que o HerpIA ajude a gerar documentos técnicos quase
finalizados, no formato do SEI. Isso é **outro produto**:

- exige modelos de documento, contexto maior e um LLM mais forte que o 3B
  atual ([ADR 0006](0006-escolha-temporaria-llm-geracao.md));
- tudo precisa sair como **rascunho para revisão humana**.

Fica como fase posterior. Precisa de ADR próprio antes de qualquer
implementação.

## Consequências

- A seleção por blocos internos reduz significativamente o volume a avaliar e aproveita a categorização temática já feita pela equipe do RAN.
- Documentos do SEI não entram na base sem avaliação e autorização humana — restrição permanente, conforme ADR 0002.
- A automação do login é tecnicamente viável, mas o conteúdo dos documentos nunca é acessado pelos scripts — apenas metadados de navegação.

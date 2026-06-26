# 0004. Critérios de seleção de documentos do SEI/ICMBio para indexação

- **Status:** Em definição
- **Data:** 2026-06-26
- **Responsável(eis):** Julia Coite, Flávia (RAN/ICMBio)

## Contexto

O SEI/ICMBio é o sistema de gestão de processos administrativos do órgão. Diferente das outras fontes (SALVE, PANs, Monitora), o SEI não permite scraping automatizado — o acesso requer login institucional e os documentos precisam ser exportados manualmente, avaliados e classificados antes de qualquer indexação (ver ADR 0002).

O SEI possui um sistema de **marcadores** (tags aplicadas a processos) que funciona como critério de seleção natural: em vez de analisar processo a processo, é possível filtrar pelo marcador para identificar conjuntos de processos tematicamente relevantes.

Os marcadores disponíveis na unidade do RAN/ICMBio foram mapeados em 2026-06-26. O acesso ao SEI é feito com login e senha institucional (sem segundo fator de autenticação).

## Decisão

### Estratégia de seleção

Usar os **marcadores do SEI** como critério primário de triagem, começando pelos de alta prioridade e avaliando os de média prioridade caso a caso.

### Marcadores por prioridade

**Alta prioridade — indexar após avaliação individual de sensibilidade**

| Marcador | ID | Justificativa |
|---|---|---|
| Espécies ameaçadas - risco de extinção | 7796 | Core temático do chatbot |
| Manejo de fauna | 8997 | Diretamente relevante para o RAN |
| Monitoramento da fauna | 7786 | Diretamente relevante para o RAN |
| PAN | 7790 | Complementa os documentos públicos já coletados |
| Pesquisa | 9061 | Produção científica e técnica interna |
| SINTAX | 16955 | Sistema de Informações Taxonômicas — dados de espécies |

**Média prioridade — avaliar caso a caso**

| Marcador | ID | Observação |
|---|---|---|
| CITES | 8963 | Comércio internacional de espécies — contextualmente relevante |
| Espécies Exóticas Invasoras | 16997 | Relevante para herpetofauna |
| SISBIO | 20096 | Autorizações de pesquisa — pode conter dados de campo |
| Plano de manejo | 7798 | Planos de UCs com fauna relevante |
| Publicações e normas | 8226 | Normas que regem a conservação |
| CONAMA | 20898 | Contexto regulatório |
| COP 15 / COP 16 - CDB / COP 19 | 20377, 16757, 16755 | Convenções internacionais de biodiversidade |
| Licenciamento ambiental | 7792 | Atenção: pode conter localização precisa de espécies |
| Criação e Ampliação de UC | 20665 | Relevante se envolver habitats críticos para herpetofauna |

**Excluir — não indexar**

| Marcador | ID | Motivo |
|---|---|---|
| Gestão de pessoas | 7794 | Dados pessoais — alto risco, sem utilidade técnica |
| Setor administrativo | 7788 | Sem conteúdo técnico relevante |
| Fiscalização | 18741 | Risco de dados pessoais (autuados) |
| Viagem / expedição | 7800 | Majoritariamente burocrático |
| Voluntariado | 18742 | Sem conteúdo técnico |
| Cursos e eventos | 7784 | Baixa utilidade para o chatbot |
| Entregas estratégicas | 8878 | Genérico demais, sem conteúdo técnico consistente |
| Apresentação | 9053 | Baixa utilidade |

### Fluxo de exportação

1. Filtrar processos pelos marcadores de alta prioridade
2. Para cada processo, avaliar sensibilidade individualmente antes de exportar
3. Documentos aprovados vão para `04_documentos_pendentes_avaliacao/sei/` e depois, se liberados, para `03_documentos_autorizados/sei/`
4. A extração de texto reutiliza o pipeline de PDFs já existente (`scripts/processamento/extrair_texto_pdfs.py`)

### Ferramenta de apoio

Script `scripts/coleta/listar_blocos_sei.py` — adaptação planejada para listar processos por marcador (em vez de por bloco interno), facilitando a triagem.

## Próximas etapas

- [ ] Adaptar o script para listar processos por marcador (começar pelos de alta prioridade)
- [ ] Validar com a Flávia quais marcadores de média prioridade incluir
- [ ] Definir critério de sensibilidade específico para o `Licenciamento ambiental` (risco de localização de espécies)
- [ ] Realizar primeira exportação piloto com processos do marcador `Espécies ameaçadas - risco de extinção`

## Consequências

- A seleção por marcador reduz significativamente o volume a avaliar, tornando o processo viável sem automação total.
- Documentos do SEI não entram na base sem avaliação humana — isso é uma restrição permanente, não contornável mesmo com automação futura.
- O marcador `Licenciamento ambiental` requer atenção especial: processos podem conter coordenadas precisas de ocorrência de espécies ameaçadas, que são dados sensíveis conforme ADR 0002.

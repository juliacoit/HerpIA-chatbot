# Classificação de sensibilidade

- **Status:** A definir
- **Última atualização:** 2026-11-11
- **Responsável(eis):** Equipe do RAN/ICMBio (decisão humana — não automatizável)

## Objetivo

Avaliar cada documento em `04_documentos_pendentes_avaliacao/` quanto à presença de
informação sensível (dados pessoais, informação administrativa restrita) e decidir
se ele pode ser indexado no RAG. Localização precisa de espécies deixou de ser
critério em 2026-11-11: coordenadas públicas são autorizadas
([ADR 0009](../decisoes/0009-coordenadas-de-ocorrencia.md)), e dado sigiloso é filtrado antes de chegar ao RAN.
Ver [ADR 0002](../decisoes/0002-classificacao-de-sensibilidade-em-pastas.md) para a
decisão de usar a estrutura de pastas como mecanismo de controle desse fluxo.

## Entradas

- Documentos em `04_documentos_pendentes_avaliacao/` (qualquer fonte: Monitora, PANs,
  SALVE, SEI, publicações científicas).

## Saídas

- Documentos aprovados movidos para `03_documentos_autorizados/`.
- Documentos sensíveis movidos para `05_documentos_sensiveis_nao_indexar/`.
- Inventário (`06_inventario/inventario_fontes.xlsx`) atualizado com a classificação
  de cada documento.

## Ferramentas

Revisão manual — esta etapa envolve decisão humana e não pode ser automatizada
integralmente (ver [`docs/roadmap.md`](../roadmap.md), Fase 3).

## Passo a passo

Critérios já decididos por fonte (roadmap Fase 3):

1. **Monitora e PANs:** revisão manual dos PDFs verificando dados pessoais. Coordenada
   pública não é motivo de bloqueio (ADR 0009).
2. **Fichas SALVE:** públicas no site do ICMBio e classificadas como autorizadas. As
   coordenadas do SALVE são públicas (ADR 0009).
3. **SEI:** avaliação individual por processo/documento, condicionada à autorização de
   exportação da equipe do RAN (ver [ADR 0004](../decisoes/0004-criterios-selecao-documentos-sei.md)
   e [`selecao_processos_sei.md`](selecao_processos_sei.md)).
4. **Publicações científicas:** verificar copyright e termos de uso de cada publicação.
5. Mover o documento para `03_documentos_autorizados/` ou `05_documentos_sensiveis_nao_indexar/`
   conforme o resultado, e atualizar o inventário.

Passo a passo detalhado (ferramenta de apoio, critérios objetivos por tipo de dado)
ainda não definido.

Triagens automáticas já geradas para priorizar a revisão manual de Monitora/PANs
(sensibilidade) e publicações científicas (copyright), com planilhas de trabalho prontas
para a equipe do RAN preencher: ver
[`triagem_pendente_sensibilidade_copyright.md`](triagem_pendente_sensibilidade_copyright.md).

## Frequência de execução

Sob demanda, conforme novos documentos chegam em `04_documentos_pendentes_avaliacao/`;
revisão geral esperada a cada atualização semestral da base de conhecimento.

## Observações sobre dados sensíveis

Este processo é, por definição, o controle de sensibilidade do projeto. Nenhum
documento deve ser movido para `03_documentos_autorizados/` sem essa avaliação —
qualquer script de ingestão que leia diretamente de `04_*` ou `05_*` é considerado um
bug de segurança do projeto (ver ADR 0002).

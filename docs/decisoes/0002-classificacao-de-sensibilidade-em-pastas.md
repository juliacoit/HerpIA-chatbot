# 0002. Classificação de sensibilidade por pastas

- **Status:** Aceita
- **Data:** 2026-06-16
- **Responsável(eis):** Equipe do projeto (RAN/ICMBio, CNPq, CIEE)

## Contexto

O acervo de documentos do RAN (publicações científicas, relatórios, dados de fontes web) pode conter informações sensíveis — por exemplo, localizações precisas de espécies ameaçadas, dados pessoais ou informações administrativas restritas (processos SEI). Esses documentos ainda não foram totalmente avaliados, e o chatbot não deve indexar nem expor conteúdo sensível antes dessa avaliação.

## Decisão

Usar a estrutura de pastas como mecanismo explícito de controle de fluxo de avaliação:

- `04_documentos_pendentes_avaliacao/` — ponto de entrada para qualquer documento ainda não avaliado.
- `03_documentos_autorizados/` — documentos avaliados, autorizados e liberados para indexação.
- `05_documentos_sensiveis_nao_indexar/` — documentos avaliados e classificados como sensíveis; **nunca** devem ser indexados ou enviados a uma API externa.

O pipeline de ingestão deve ler apenas de `03_documentos_autorizados/`. Qualquer script de ingestão que varra `04_*` ou `05_*` diretamente é considerado um bug de segurança do projeto.

## Consequências

- Toda movimentação de um documento de `04_*` para `03_*` ou `05_*` é, por definição, uma decisão humana de classificação — não deve ser automatizada sem revisão.
- O inventário em `06_inventario/inventario_fontes.xlsx` deve registrar em qual dessas três pastas cada documento se encontra, para rastreabilidade.
- Esta decisão não cobre a anonimização de dados pessoais dentro de documentos já autorizados — isso é tratado como um processo separado (ver `docs/processos/classificacao_sensibilidade.md`).

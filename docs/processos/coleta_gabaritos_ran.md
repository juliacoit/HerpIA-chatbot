# Coleta de gabaritos da avaliação RAGAS com a equipe do RAN

- **Status:** Em desenvolvimento (pedido enviado em 2026-10-19; retorno previsto para o início de novembro de 2026)
- **Última atualização:** 2026-10-20
- **Responsável(eis):** Julia Coite (organização); coordenação do RAN e pontos focais de cada base (conteúdo)

## Objetivo

Obter da equipe técnica do RAN os gabaritos (campo `reference` de
`avaliacao/casos.jsonl`) e os vereditos que faltam para a avaliação offline
com RAGAS ([ADR 0007](../decisoes/0007-avaliacao-offline-ragas-juiz-claude.md)).
Sem gabarito, os casos pulam as métricas que dependem de referência
(`ContextPrecisionWithReference` e `ContextRecall`). Pelo ADR 0007, item 7,
os gabaritos vêm só da equipe do RAN, nunca de quem desenvolve.

## Entradas

**Documento compartilhado (enviado em 2026-10-19)**, com 4 pedidos:

1. Gabaritos de 21 perguntas da bateria.
2. Veredito em 9 casos de discordância entre juízes.
3. Custo das rodadas.
4. Mais perguntas reais.

O link do documento compartilhado só permite leitura. Por isso foi feita uma
versão em Word, `HerpIA_pedido_apoio_RAN.docx`, só com os Pedidos 1 e 2. Ela
traz:

- instruções no topo;
- a coluna "Área" em cada pergunta;
- as perguntas prioritárias marcadas com ★.

**Avaliação cega:** a versão em Word **omite** o veredito do juiz interno e a
nota de `Faithfulness` na tabela do Pedido 2. Assim o especialista avalia sem
saber o que os juízes disseram.

## Saídas

- Gabaritos validados no campo `reference` de `avaliacao/casos.jsonl`, no
  lugar de `PENDENTE_VALIDACAO_RAN`.
- Vereditos dos 9 casos de discordância, para comparar com os juízes (ver
  `diagnosticos/comparacao-juizes-rodada2.md`).

## Divisão por área

**Prioridade dentro do Pedido 1:** C1, C2, C3, I1, A1, A2 e A3.

| Área | Pedido 1 (gabaritos) | Pedido 2 (veredito) |
|---|---|---|
| SALVE | A1, C1, C2, C3, F6, H1, I1, L4, L5 | C3, F6, L4 |
| PANs | A2, D1, D2, D3, D4, F5, H2 | B1, D1, D3, L1, L2 |
| Monitora | A3 | — |
| Em conjunto | B1 (PAN+SALVE), B2 (Monitora+PAN), B3 (SALVE+PAN), J1 (SALVE+PAN) | G3 (qualquer área) |

Os 15 casos de recusa (F2–F4, F7, G1–G5, L1–L3, L6–L8) **não precisam de
gabarito**. As métricas com referência medem o conteúdo recuperado, e nesses
casos a resposta certa é recusar. Com os 21 do Pedido 1, eles somam os 36
casos de `casos.jsonl`.

## Passo a passo

1. A coordenação do RAN encaminha o pedido aos pontos focais de cada base:
   avaliação do risco de extinção (SALVE), PANs e Monitora.
2. Os pontos focais devolvem gabaritos e vereditos até o **início de
   novembro de 2026**.
3. Reunião presencial de validação, no formato de pequena oficina:
   coordenação do RAN, Júlia e ponto focal do Monitora, com até mais dois
   colegas. A tabela é projetada, e cada gabarito e veredito é revisado em
   conjunto.
4. Só depois da validação os gabaritos entram em `avaliacao/casos.jsonl`
   (campo `reference`). Nesse momento, revisar o teste
   `test_nenhum_gabarito_escrito_fora_do_ran` (ver
   [`avaliacao/README.md`](../../avaliacao/README.md)).

## Frequência de execução

Sob demanda. Esta é a primeira coleta. Novas coletas só quando a bateria
ganhar perguntas novas (Pedido 4).

## Observações sobre dados sensíveis

- As perguntas e os gabaritos tratam de conteúdo das fontes públicas já
  indexadas (SALVE, PANs, Monitora). Nada do SEI entra nesta coleta.
- Os gabaritos vão para o repositório, que é público. Antes de copiá-los
  para `casos.jsonl`, conferir que não trazem dados pessoais nem
  localizações precisas de espécies ameaçadas.
- Neste documento, as pessoas aparecem pelo papel, não pelo nome.

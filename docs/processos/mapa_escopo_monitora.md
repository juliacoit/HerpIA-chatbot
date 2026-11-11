# Mapa de escopo do Monitora

- **Status:** Em desenvolvimento (planilha aguardando preenchimento)
- **Última atualização:** 2026-11-11
- **Responsável(eis):** servidores do RAN (preenchimento); responsável pelo projeto (aplicação no HerpIA)

## Objetivo

Decidir, documento por documento e alvo por alvo, o que do Programa Monitora
entra na base consultada pelo HerpIA. A equipe do RAN definiu a regra geral em
2026-11-11 ([ADR 0008](../decisoes/0008-escopo-da-base-herpetofauna.md)), mas
duas pendências dependem deste mapa:

1. a análise do **componente Florestal**, que está fora por enquanto;
2. a **lista de exclusões**, que ainda está incompleta.

O mapa também resolve os documentos que a regra automática não consegue
classificar: 32 dos 109 documentos do Monitora na simulação de 2026-11-11.

## Entradas

- **Planilha compartilhada**, fora do repositório: `<link a preencher>`
- A regra geral do ADR 0008:
  - entram os alvos de anfíbios e répteis do subprograma Terrestre (componente
    Campestre e Savânico) e do subprograma Aquático Continental;
  - entram as instruções gerais do programa (portarias, definições);
  - ficam fora pesca, borboletas, aves, mamíferos e o subprograma Marinho e
    Costeiro.
- A lista dos 109 documentos do Monitora na base, com a classificação
  automática de cada um. Sai de
  `diagnosticos/scripts/adr_escopo_simulacao_v2.py` (só leitura).

## Saídas

- A planilha preenchida, com uma situação para cada linha.
- A seção do Monitora no arquivo de configuração do escopo (`config/escopo.yaml`,
  proposto no ADR 0008), atualizada a partir da planilha.
- O ADR 0008 atualizado, com a decisão sobre o componente Florestal e a lista
  de exclusões completa.

## Quem preenche

Os servidores do RAN que trabalham com o Programa Monitora. A responsável pelo
projeto prepara a planilha, tira dúvidas sobre os documentos e aplica o
resultado. Ela não decide a situação de nenhuma linha.

## O que cada situação significa

| Situação | Significado | Efeito no HerpIA |
|---|---|---|
| **Entra** | O documento ou alvo é do escopo do RAN: alvo de anfíbios ou répteis, ou instrução geral do programa | Os trechos ficam disponíveis para a busca e podem ser citados nas respostas |
| **Fora** | Não é do escopo: outro alvo, outro subprograma ou material sem relação com a herpetofauna | Os trechos continuam guardados, mas não aparecem na busca. Perguntas sobre o assunto recebem a mensagem de fora de escopo |
| **Fora por enquanto** | Decisão adiada, com análise pendente. Hoje vale para o componente Florestal | Igual a "Fora" até a análise terminar. A linha volta a ser revisada |
| **A definir** | Ninguém decidiu ainda | Igual a "Fora". O HerpIA só usa o que está marcado "Entra" |

Nenhuma situação apaga dados. Mudar uma linha depois é reclassificar, sem
processar os documentos de novo.

## Ferramentas

- Planilha compartilhada (Google Drive).
- `diagnosticos/scripts/adr_escopo_simulacao_v2.py`, para gerar a lista de
  documentos e conferir as contagens.

## Passo a passo

1. A responsável pelo projeto monta a planilha com uma linha por documento do
   Monitora (nome do arquivo, categoria, subprograma, componente e alvo
   sugeridos pela regra automática) e uma linha por alvo ou tema da lista de
   exclusões.
2. Os servidores do RAN marcam a situação de cada linha e, quando souberem,
   corrigem subprograma, componente e alvo.
3. Para o componente Florestal, os servidores registram a análise: o que
   entra, o que fica fora e por quê.
4. A lista de exclusões é completada com os alvos e temas que faltam.

**Depois do preenchimento:**

5. A responsável pelo projeto confere se toda linha tem situação e leva as
   dúvidas de volta à equipe.
6. O resultado vai para o arquivo de configuração do escopo, e o ADR 0008 é
   atualizado.
7. A classificação roda em modo simulação, e a contagem por situação é
   conferida com a planilha.
8. Só então, com aprovação, o campo `escopo` é gravado para os documentos do
   Monitora e a lista de exclusões passa a alimentar a mensagem de fora de
   escopo (passos 7 e 9 do plano do ADR 0008).

## Frequência de execução

Uma vez agora, para fechar as pendências do ADR 0008. Depois, a cada
atualização semestral da base, só para os documentos novos do Monitora.

## Observações sobre dados sensíveis

- A planilha fica fora do repositório. Aqui entra só o resultado: a situação
  de cada documento.
- Os documentos do Monitora são públicos (portal do ICMBio). A planilha traz
  nomes de arquivo e classificação, sem conteúdo dos documentos.
- No repositório, que é público, as pessoas aparecem pelo papel, não pelo
  nome.

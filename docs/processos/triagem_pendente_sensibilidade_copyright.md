# Triagens pendentes de revisão — sensibilidade (Monitora/PANs) e copyright (publicações)

- **Status:** Planilha 1 (sensibilidade Monitora/PANs): revisão humana pendente, 0 decisões. Planilha 2 (copyright das publicações): **resolvida pela equipe do RAN em 2026-11-06**, 303 publicações autorizadas (as 9 linhas restantes são marcadores de lacuna)
- **Última atualização:** 2026-11-06
- **Responsável(eis):** Equipe do RAN/ICMBio (decisão humana — não automatizável)

## O problema

Antes de gerar chunks e indexar qualquer documento, o projeto exige avaliação de
sensibilidade e/ou copyright (ver [`classificacao_sensibilidade.md`](classificacao_sensibilidade.md)
e regras em `/CLAUDE.md`). Revisar documento por documento sem nenhuma priorização não é
viável, então foram geradas duas planilhas de triagem automática — uma para
Monitora/PANs (sensibilidade) e outra para publicações científicas (copyright) — para
reduzir o volume de análise humana e indicar por onde começar.

**Nenhuma dessas planilhas decide o que entra na base de conhecimento.** Isso continua
sendo responsabilidade da equipe do RAN. O papel da triagem é apenas priorizar.

## Atualização 2026-07-13 — redação automática de padrões estruturados

O pipeline de chunking (`scripts/processamento/gerar_chunks.py`) passou a redigir
automaticamente CPF, e-mail pessoal, telefone e coordenadas (decimal ou graus/min/seg)
encontrados no texto de Monitora/PANs, substituindo-os por um placeholder antes de
gerar os chunks — ver [`chunking.md`](chunking.md#estratégia-de-chunking) e o módulo
compartilhado `scripts/classificacao/regras_pii.py`. Isso **não substitui** a revisão
manual da Planilha 1 abaixo, mas muda o que ela precisa cobrir: os 4 padrões
estruturados (que motivaram boa parte da prioridade ALTA) já não vão para o texto
indexado sem revisão nenhuma. A revisão humana continua necessária para:

- Os padrões semânticos, que não são redigidos automaticamente (`palavra_restrito`,
  `palavra_localizacao`, `dado_pessoal_generico`) — falso positivo/negativo alto
  demais para redação automática segura.
- Confirmar, por amostragem, que a redação automática não está redigindo em excesso
  (falso positivo) nem passando batido algum caso (falso negativo).
- Decidir, documento a documento, se algum PDF deveria ser excluído por completo
  (não é isso que a redação por chunk resolve).

Relatório de auditoria de cada execução: [`06_inventario/relatorio_anonimizacao_chunks.json`](../../06_inventario/relatorio_anonimizacao_chunks.json)
(lista os documentos afetados e a contagem de substituições por tipo).

## Planilha 1 — Sensibilidade: Monitora e PANs

- **Arquivo:** [`06_inventario/triagem_sensibilidade_monitora_pans.xlsx`](../../06_inventario/triagem_sensibilidade_monitora_pans.xlsx)
- **Aba `Triagem`:** 816 documentos (PDFs do Monitora e dos PANs), um por linha
- **Aba `Resumo`:** contagem por prioridade

O que a triagem detectou automaticamente em cada PDF (coluna `flags_encontrados`): CPF,
telefone, e-mail pessoal, coordenada geográfica, menção a localização de espécie e
palavras de restrição — com trechos de exemplo em `trechos_exemplo` (`[p.X | flag] (...)`).

| Prioridade | Documentos | Observação |
|---|---|---|
| ALTA | 234 | CPF/e-mail/coordenada/palavra de restrição encontrados — revisar primeiro |
| MÉDIA | 77 | Menção genérica a localização/dado pessoal, sem padrão numérico confirmado |
| BAIXA | 505 | Nenhum padrão encontrado — recomenda-se amostragem, não pular |

### Colunas de decisão (a preencher pela equipe do RAN)

`decisao` (`autorizado` / `sensivel` / outro critério a definir), `revisado_por`,
`data_revisao`, `observacoes`. Todas as 816 linhas estão vazias nessas colunas hoje.

## Planilha 2 — Copyright: publicações científicas do RAN

> **Decisão da equipe do RAN (2026-11-06):** não há restrição de copyright para
> nenhuma das publicações, porque o HerpIA é uma aplicação interna, de uso exclusivo
> dos servidores do RAN. A equipe informou que todas foram analisadas manualmente e
> liberou o uso de todas, incluindo os 7 anais do CBH. A classificação de risco
> abaixo fica como registro histórico.
>
> Na cópia local da planilha, 245 linhas sem decisão (7 ALTO e 238 MÉDIO)
> passaram para `decisao = autorizado`, `revisado_por = Equipe do RAN`,
> `data_revisao = 2026-11-06`. Com as 58 de risco BAIXO já autorizadas, são **303
> publicações autorizadas**. Ficaram em branco 9 linhas que são marcadores de
> lacuna, não documentos: as 5 `N/A` e 4 arquivos "NN - Falta.docx" que a triagem
> automática tinha classificado como MÉDIO (têm 11–12 caracteres; a observação da
> linha explica). A cópia do Google Drive foi substituída pela local em 2026-11-06
> (conferido: 303 `autorizado`).
>
> Premissa da decisão: o acesso fica restrito aos servidores do RAN, o que torna o
> login um pré-requisito antes de indexar as publicações.

- **Arquivo:** [`06_inventario/triagem_copyright_publicacoes.xlsx`](../../06_inventario/triagem_copyright_publicacoes.xlsx)
- **Aba `Triagem`:** 312 publicações, uma por linha
- **Aba `Resumo`:** contagem por risco

| Risco | Publicações | Observação |
|---|---|---|
| ALTO | 7 | Anais completos do Congresso Brasileiro de Herpetologia (2004–2015) — conteúdo majoritariamente de terceiros, copyright da Sociedade Brasileira de Herpetologia. Recomendação já registrada em `motivo_automatico`: não indexar o volume inteiro; se houver interesse, extrair manualmente só os resumos de autoria de pesquisadores do RAN |
| MÉDIO | 242 | Publicado em revista/editora externa — checar política de copyright do veículo |
| BAIXO | 58 | Institucional do próprio RAN/ICMBio (boletins, HerpetoPAN, ICMBio em Foco) — risco mais baixo, mas ainda recomenda-se amostragem |

### Colunas de decisão (a preencher pela equipe do RAN)

Mesmo padrão da planilha 1: `decisao`, `revisado_por`, `data_revisao`, `observacoes`.
Na cópia local (conferido em 2026-10-20), as 58 publicações de risco BAIXO estão marcadas
`autorizado` (revisão de 2026-07-14). As 7 de risco ALTO e as 242 de risco MÉDIO seguem sem
decisão. Há uma cópia compartilhada no Google Drive.

## O que falta (nas duas planilhas)

1. Revisar as linhas, começando por ALTA/ALTO.
2. Preencher `decisao`, `revisado_por` e `data_revisao` para cada linha revisada.
3. Mover os documentos aprovados para `03_documentos_autorizados/` e os reprovados/sensíveis
   para `05_documentos_sensiveis_nao_indexar/`, conforme a decisão.
4. Atualizar `06_inventario/inventario_fontes.xlsx` com o resultado.

Só depois desse fluxo os documentos correspondentes devem seguir para a Fase 4
(chunking) — ver [`docs/roadmap.md`](../roadmap.md).

## Outras avaliações pendentes fora dessas duas planilhas

- **SEI:** a seleção de 173 processos (v2, 2026-07-13) foi validada pela equipe do RAN em
  2026-11-06, e os 244 descartados ficam fora — ver
  [`selecao_processos_sei.md`](selecao_processos_sei.md). Falta a exportação manual; depois
  dela, cada documento ainda precisa de avaliação de sensibilidade individual.
- **PANs — sensibilidade documento a documento:** pelo menos 1 documento (portaria GAT do
  PAN Quelônios) já foi avaliado individualmente e classificado como sensível, em
  `05_documentos_sensiveis_nao_indexar/pans/pan-quelonios/ciclo-1/`. Essa avaliação é
  pontual e independente da triagem em massa da Planilha 1.
- **Fichas SALVE:** já avaliadas e aprovadas (ver [`classificacao_sensibilidade.md`](classificacao_sensibilidade.md)) — não há pendência aqui.

## Relação com outros documentos

- Processo geral de classificação de sensibilidade: [`classificacao_sensibilidade.md`](classificacao_sensibilidade.md)
- Seleção de processos do SEI: [`selecao_processos_sei.md`](selecao_processos_sei.md)
- Catalogação das publicações científicas (origem da planilha de copyright): [`catalogacao_publicacoes.md`](catalogacao_publicacoes.md)
- Status geral do projeto por fase: [`docs/roadmap.md`](../roadmap.md)

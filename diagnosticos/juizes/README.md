# Conjunto rotulado para a rodada 2 (juízes de groundedness)

`conjunto_rotulado.jsonl` é o gabarito usado para comparar os juízes de groundedness (J1–J6) offline.
Cada linha é uma resposta real já gerada pelo HerpIA, com os trechos que o gerador recebeu e o rótulo
humano. **53 itens, todos confirmados pela Júlia em 2026-09-30 / 2026-10-02.**

## Campos

| Campo | Conteúdo |
|---|---|
| `id` | `<origem>-<gerador>-<caso>[-e<execução>]`, ex.: `r1-qwen2.5-3b-A1-e1` |
| `origem` | `rodada1` (2026-09-25) ou `bateria_antiga` (2026-08-13 e 2026-09-22) |
| `caso`, `gerador`, `execucao` | Caso da bateria, modelo gerador, execução (1–3) |
| `pergunta`, `resposta` | Pergunta da bateria e resposta gerada, sem alteração |
| `trechos` | Os 8 chunks entregues ao gerador (`id_chunk`, `fonte`, `documento`, páginas, `secao`, `texto`) |
| `rotulo` | Ver abaixo |
| `afirmacoes_sem_suporte` | Frases literais da resposta sem apoio nos trechos (ou que os contradizem) |
| `rotulo_status` | `confirmado` em todos os itens |
| `observacao` | Justificativa curta e procedência |

## Rótulos

| Rótulo | Itens | Origem na rodada 1 |
|---|---|---|
| `nao_fundamentada` | 28 | alucina, especula, ou "outro" com afirmação que contradiz os trechos |
| `fundamentada` | 13 | ok |
| `abstencao_honesta` | 10 | abstém, e os trechos de fato não têm a informação |
| `abstencao_indevida` | 2 | abstém, mas os trechos têm a informação (a recusa é uma afirmação falsa sobre os trechos) |

## Decisões tomadas (2026-10-02)

1. **Mapeamento aprovado:** alucina/especula → `nao_fundamentada`; ok → `fundamentada`;
   abstém com trechos sem a informação → `abstencao_honesta`.
2. **5 itens "proposto" confirmados como `nao_fundamentada`** (b0922 A1-e3, B3-e3, I1-e3; a0813 G1 e
   I1), com ajuste de `afirmacoes_sem_suporte` em B3-e3, I1-e3 e a0813 I1.
3. **Quarto rótulo `abstencao_indevida`**, só com casos inequívocos:
   - `r1-qwen3.5-4b-D3-e1`: D3-7 lista as 8 UCs da AE Espinhaço Oeste; a resposta diz que não há.
   - `r1-gpt-oss-20b-B2-e1`: B2-4 traz a relação PAN–Monitora; a resposta diz que não há.
   - **Ficaram fora por ambiguidade:** F6 gpt-oss (a ficha diz onde a espécie ocorre, mas não tem
     "últimos registros") e B1 granite (nenhum trecho do SALVE, e a pergunta pede "segundo o SALVE").
4. **Células "outro":** entrou só `r1-gpt-oss-20b-L5-e1` (cita LC e conclui que o SALVE considera a
   espécie ameaçada). Ficaram fora A1 qwen2.5 e2 (terceira cópia do erro da Marinha, já presente em
   A1-e1 e b0922 A1-e3) e B3 qwen2.5 (erro de lógica sem fato inventado; juízes podem divergir com razão).
5. **Tamanho mantido** (sem corte): os 4 itens F4 são de geradores diferentes.

## Como os trechos foram obtidos

Os relatórios de bateria guardam só as citações, não o texto dos chunks. Os trechos foram
reconstruídos com `buscar_chunks_priorizados` (`top_k=8`) no HEAD; `retrieval.py` e `roteamento.py` não
mudam desde 2026-09-16, e o índice desde 2026-09-04. Para a rodada 1 e a bateria de 2026-09-22, as
citações batem 100% (documento, página e ordem). Nos dois itens de 2026-08-13 (`a0813-*`), só
documentos e páginas são verificáveis, não o texto exato. Itens de mesma pergunta compartilham os
mesmos trechos (retrieval determinístico).

## Para a Parte B (sugestão; conferir com o prompt da rodada 2)

- `abstencao_indevida` tem só 2 itens: reportar à parte, como observação qualitativa (algum juiz
  percebe que a recusa contradiz os trechos?), não como métrica.
- As métricas principais comparam o veredito binário de cada juiz com
  `nao_fundamentada` vs. (`fundamentada` + `abstencao_honesta`).

## Ampliação proposta (2026-10-09, aguardando confirmação)

`candidatos_ampliacao.jsonl` traz 101 respostas da rodada 1 que ainda não estavam no conjunto, no
mesmo formato, com `rotulo_status: "proposto"`. `candidatos_ampliacao_revisao.md` é a mesma lista em
formato de leitura, com espaço para confirmar ou trocar cada rótulo. **Não são gabarito** até a Júlia
confirmar; depois de confirmados, entram em `conjunto_rotulado.jsonl`.

| Rótulo proposto | Candidatos | No conjunto hoje | Total se todos forem confirmados |
|---|---|---|---|
| `fundamentada` | 37 | 13 | 50 |
| `abstencao_honesta` | 60 | 10 | 70 |
| `abstencao_indevida` | 4 | 2 | 6 |
| `nao_fundamentada` | 0 | 28 | 28 |

**A ampliação não acrescenta nenhuma resposta não fundamentada.** Todas as células "alucina" e
"especula" da rodada 1 já estavam no conjunto. Ela melhora só a medida de retenção indevida (respostas
boas e abstenções honestas retidas por engano); para medir melhor a detecção é preciso gerar respostas
novas, com perguntas novas por categoria.

### Como os candidatos foram montados

- Universo: as 180 células caso × modelo da rodada 1 (36 casos, 5 geradores), execução 1, menos as
  48 células que já tinham item no conjunto.
- Rótulo proposto pelo mapeamento aprovado em 2026-10-02, aplicado ao rótulo do Anexo A da rodada 1
  (revisado pela Júlia em 2026-09-30):
  - `ok 3/3` → `fundamentada`;
  - `abstém 3/3` em caso cujo esperado é recusar → `abstencao_honesta`;
  - `abstém 3/3` em B3, D4 e H2 → `abstencao_honesta` (mesmos trechos de itens já confirmados assim);
  - `abstém 3/3` em B2 e D3 → `abstencao_indevida` (mesmos trechos dos dois itens já confirmados assim).
- Ficaram fora 31 células:
  - 14 com rótulo "outro" ou misto (mesmo critério da decisão 4 de 2026-10-02);
  - 6 abstenções em B1 e F6 (ambíguas, decisão 3 de 2026-10-02);
  - 6 abstenções em casos de esperado "responder" sem item confirmado que sirva de referência (F5,
    I1, J1): falta decidir se os trechos têm ou não a informação;
  - 5 respostas do G1, que são a mensagem fixa do backend para perguntas sobre o SEI, sem LLM.
- Trechos: reconstruídos com `buscar_chunks_priorizados` (`top_k=8`). Nos 33 casos da rodada 1 que já
  tinham trechos no conjunto, a reconstrução de 2026-10-09 saiu idêntica; G5 e L7 são casos novos.
- O campo `observacao` traz o rótulo e a justificativa do Anexo A. Em 6 itens há um aviso `CONFERIR`,
  com o que a camada 1 de `groundedness.py` ou uma busca por siglas expandidas apontou; é pista para
  a leitura, não rótulo.

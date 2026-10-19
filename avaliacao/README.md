# Avaliação offline com RAGAS

Ver [ADR 0007](../docs/decisoes/0007-avaliacao-offline-ragas-juiz-claude.md)
e [`diagnosticos/ragas_fase0.md`](../diagnosticos/ragas_fase0.md).

## `casos.jsonl`

Uma linha por caso da bateria de domínio
(`CASOS_TESTE` em `scripts/teste_perguntas_dominio.py`). A pergunta e a
categoria **não** ficam aqui: são lidas da bateria por `casos.py`, que
também valida o arquivo. O teste `tests/test_casos_avaliacao.py` garante que
o JSONL cobre a bateria inteira.

| Campo | Obrigatório | Conteúdo |
|---|---|---|
| `id` | sim | id do caso em `CASOS_TESTE` (ex.: `D3`) |
| `reference` | sim | gabarito validado pela **equipe técnica do RAN**, ou `PENDENTE_VALIDACAO_RAN`. Nunca escrito por quem desenvolve. Sem gabarito, o caso pula `ContextPrecisionWithReference` e `ContextRecall`. |
| `fonte_esperada` | não | `monitora`, `pans` ou `salve`: fonte que a recuperação deve trazer (checagem de **efeito**). `null` = não checar. |
| `rota_esperada` | não | `salve` ou `nenhuma`: decisão esperada do gate do SALVE (`detectar_fonte_prioritaria`), na checagem de **decisão**. Omitido = indiferente. |
| `falha_conhecida` | não | texto descrevendo uma falha já conhecida. Se o caso falha, o status é `falha_conhecida` (não `divergente`); se passa, o relatório avisa que a falha pode ter sido corrigida. |
| `top_k` | não | sobrescreve o padrão do script (5, o mesmo do frontend) |
| `fontes` | não | filtro de fontes enviado ao `/perguntar` (a bateria não usa) |

## Checagens de rota (`rota.py`, sem custo)

- **Decisão:** `detectar_fonte_prioritaria(pergunta)` comparada com
  `rota_esperada`, sem regra por categoria. Testa a mesma função da produção:
  pega regressão no regex, não erro de especificação.
- **Efeito:** a partir da `fonte` dos contextos devolvidos.
  - Com `rota_esperada == "salve"`, é **estrita**: o primeiro contexto
    precisa ser da `fonte_esperada`.
  - Nos demais casos, basta a `fonte_esperada` aparecer no top-k, e a fração
    de contextos dessa fonte fica registrada.
- **Status do caso:** o pior das duas checagens (`divergente` >
  `falha_conhecida` > `ok` > `nao_checada`).

**Valores atuais (revisados pela Júlia, 2026-10-19):**

| Casos | `fonte_esperada` | `rota_esperada` | Motivo |
|---|---|---|---|
| A1 | salve | (indiferente) | espécie via SALVE: disparar o gate não seria erro |
| A2, A3 | pans, monitora | nenhuma | PAN e Monitora: o gate restringiria ao SALVE |
| C1–C3 | salve | salve | categoria "deve rotear para SALVE" |
| D1–D3 | pans | nenhuma | categoria "controle negativo (sem rotear)" |
| D4 | pans | nenhuma | idem; `falha_conhecida`: o gate dispara hoje |
| F5 | pans | nenhuma | decisão de 2026-09-22: responder com o PAN de aves; o gate restringiria ao SALVE, que não tem aves |
| F6 | salve | (indiferente) | decisão de 2026-09-25: o que está na ficha pública do SALVE pode ser informado |
| H1 | salve | (indiferente) | pergunta sobre uma ficha do SALVE: disparar o gate não seria erro |
| H2 | pans | nenhuma | pergunta sobre uma página de um PAN |
| I1 | salve | (indiferente) | fraseio leigo: testa se a busca semântica sozinha traz o SALVE |
| L4, L5 | salve | (indiferente) | corrigir a premissa exige recuperar a ficha do SALVE |
| L2, L8 | — | nenhuma | recusa (PAN inexistente); `falha_conhecida`: mesmo falso positivo do D4, o gate dispara hoje |

Os casos multifonte (B, J) ficam sem checagem, porque `fonte_esperada` aceita
uma fonte só. Os demais casos de recusa (F2–F4, F7, G, L1, L3, L6, L7) também
ficam sem `fonte_esperada` nem `rota_esperada`.

## `rodar_ragas.py`

```bash
pip install -r requirements-avaliacao.txt   # ragas, instructor e anthropic fixados
python avaliacao/rodar_ragas.py --dry-run   # sem custo: coleta, rota, bloqueios e plano
python avaliacao/rodar_ragas.py --casos A1 --metricas faithfulness   # smoke test pago
```

- O backend precisa estar rodando com `PERMITIR_MODO_AVALIACAO=true`. Sem
  isso, `/perguntar` responde 403 e o script para.
- **Primeiro coleta todos os casos**, que é a parte sem custo. Só depois mostra
  o plano (casos a avaliar e chamadas estimadas ao juiz) e pede confirmação
  antes de qualquer chamada paga. `--sim` pula a confirmação.
- **Bloqueio por sensibilidade, falhando fechado:** o caso é pulado
  (`bloqueado_sensibilidade`) se algum contexto tiver `nivel_sensibilidade`
  diferente de `"autorizado"`, inclusive `None` ou campo ausente. Nesse caso,
  nada dele vai à API.
- **Texto avaliado:**
  - `resposta`, nas saídas `gerada` e `abstencao`;
  - `resposta_original`, na `retida_groundedness`, para comparar o juiz
    interno com o RAGAS;
  - as saídas sem texto do LLM (`sem_chunks`, `sei_nao_indexado`,
    `contexto_excedido`) ficam como `sem_texto_llm`.
- **Métricas:**
  - Faithfulness e AnswerRelevancy sempre. A AnswerRelevancy usa o BGE-M3
    local para os embeddings;
  - ContextPrecisionWithReference e ContextRecall só com gabarito do RAN;
  - nunca as multimodais (CVE-2026-6587).
- **Juiz:** `claude-sonnet-5-5` por padrão (`--juiz`), com `--esforco low`
  por padrão. Os contornos da seção 8.2 do diagnóstico estão em
  `criar_metricas`.
- **Credencial:** vem do ambiente (`ANTHROPIC_API_KEY` ou `ant auth login`),
  nunca do repositório.
- **Saída:** `diagnosticos/ragas/<data>_<juiz>[_dry-run].{md,json}`. O JSON
  guarda os metadados dos contextos, mas não o texto deles.

## Para a equipe do RAN preencher os gabaritos

Trocar `PENDENTE_VALIDACAO_RAN` pelo texto da resposta correta, com base nas
fontes indexadas. Depois, revisar o teste
`test_nenhum_gabarito_escrito_fora_do_ran`, que hoje exige que todos estejam
pendentes.

# 0006. Escolha temporária do LLM de geração (local, sem custo de API)

- **Status:** Decisão parcial tomada — LLM local via Ollama escolhido temporariamente para a Fase 6; decisão final de produção segue pendente de orçamento
- **Data:** 2026-08-11
- **Responsável(eis):** Julia Coite

## Contexto

A Fase 6 ([`docs/roadmap.md`](../roadmap.md)) depende de escolher um LLM para a etapa de geração de resposta (monta prompt com os chunks recuperados do Qdrant, gera a resposta com citação de fontes). O [ADR 0001](0001-stack-tecnologica-inicial.md), de 2026-06-16, previa "API externa de LLM (ex.: OpenAI API)" — mas essa decisão é anterior à descoberta da restrição orçamentária real do projeto.

Desde então, a mesma pergunta ("há orçamento para API paga?") já apareceu duas vezes e recebeu a mesma resposta — não:

- **Embeddings (Fase 5):** [ADR 0005](0005-escolha-temporaria-modelo-embeddings.md) escolheu BGE-M3 (local) temporariamente porque a decisão de orçamento não saía e não podia bloquear a validação do pipeline.
- **Descrição de imagens (Fase 2.3):** revisão de 2026-07-21 em [`docs/processos/ESTRATEGIA_PROCESSAMENTO_IMAGENS.md`](../processos/ESTRATEGIA_PROCESSAMENTO_IMAGENS.md) — "por falta de verba", trocou Claude Haiku por um VLM local (Qwen2-VL-2B).

Não há nenhum sinal de que a situação orçamentária mudou para a etapa de geração. Esperar uma terceira rodada de "confirmar orçamento" para só então implementar a Fase 6 repetiria o mesmo atraso evitável que os ADRs anteriores já identificaram.

## Decisão

Usar um **LLM local via [Ollama](https://ollama.com)** para a etapa de geração, **temporariamente** — mesma lógica do ADR 0005: não bloquear a implementação do backend (Fase 6) enquanto a decisão de orçamento não é confirmada pela equipe do RAN.

Modelo inicial recomendado: **um modelo instruct pequeno (~3B parâmetros)**, ex. `qwen2.5:3b-instruct` ou `llama3.2:3b-instruct`, em vez de um modelo maior (7-8B). Motivo: a máquina de dev tem GPU de 4 GB (RTX 2050), já compartilhada em tempo de consulta com o BGE-M3 (que precisa rodar para embeddar a pergunta do usuário) — um modelo de geração de ~3B em 4-bit deixa espaço para os dois convivirem na GPU sem um forçar o outro para CPU a cada pergunta. Se a qualidade das respostas na validação (Fase 8) for insuficiente, subir para um modelo maior é um parâmetro de configuração, não uma mudança de arquitetura.

O backend deve isolar a chamada ao LLM atrás de uma interface pequena (ex.: uma classe `LLMClient` com um método `generate(prompt) -> str`), para que trocar de modelo local ou migrar para uma API paga futuramente seja só uma troca de implementação, sem redesenhar o resto do pipeline (retrieval, filtro de acesso, formatação de citações continuam iguais).

## Consequências

- Nenhum dado sai da máquina na etapa de geração — mais estrito que o plano original do ADR 0001 (API externa só com chunks filtrados), já que agora nem os chunks filtrados saem da máquina.
- Qualidade de resposta fica limitada pela capacidade de um modelo pequeno rodando localmente — pode exigir mais engenharia de prompt (respostas mais curtas, formato de citação bem explícito no prompt) do que seria necessário com um modelo de fronteira via API. Validar isso é o objetivo da Fase 8.
- **Ollama** se torna uma dependência nova de infraestrutura (instalar na máquina de dev e, futuramente, no servidor dedicado) — operacionalmente parecido com o que já foi feito para o VLM local da Fase 2.3.
- Se a equipe confirmar que não há orçamento para API paga (padrão que se repetiu nas duas decisões anteriores), esta escolha tende a virar definitiva — registrar como **atualização deste mesmo ADR**, não um novo.
- Se a equipe confirmar orçamento, a troca para API paga (Claude, GPT, etc.) é viável sem redesenho, graças à interface `LLMClient` — só reavaliar se o modelo local usado nos testes de validação (Fase 8) precisa ser re-executado com o modelo final antes de ir a produção.

## Próximas etapas

- [ ] Instalar Ollama na máquina de dev
- [ ] Baixar o modelo escolhido (`ollama pull qwen2.5:3b-instruct` ou equivalente)
- [ ] Implementar `LLMClient` no backend (Fase 6), chamando a API HTTP local do Ollama
- [ ] Testar qualidade de resposta com perguntas reais do domínio + citação de fontes corretas
- [ ] Medir latência real por pergunta (GPU vs. CPU, concorrência com BGE-M3 em tempo de consulta)
- [ ] Levar o resultado + a necessidade (ou não) de orçamento para API para decisão final com a equipe do RAN
- [ ] Atualizar este ADR quando a decisão definitiva for confirmada

# Agregação incompleta/incorreta em perguntas de "espécies por bioma" (fichas SALVE)

Investigação disparada por um teste manual da Júlia na interface Streamlit
(2026-09-04): a pergunta "Quais espécies de anuros existem no Pantanal?"
retornou uma resposta que listava só 3 das 5 espécies citadas. O campo
`Citacao.texto` (adicionado nesta mesma sessão, ver commit `3d22802`) tornou
possível diagnosticar a causa real comparando cada resposta com o campo
estruturado `Bioma:` que toda ficha SALVE carrega no cabeçalho do chunk.

## Reprodução

```bash
curl -s -X POST http://localhost:8000/perguntar -H "Content-Type: application/json" \
  -d '{"pergunta":"Quais espécies de anuros existem no Pantanal?","top_k":5}'
```

Sem filtro de fonte — a heurística de roteamento (`backend/services/roteamento.py`)
já prioriza SALVE para esse padrão de pergunta (caso C2 de
`diagnosticos/baterias/*.md`), então os 5 chunks recuperados foram todos
fichas SALVE.

## Achado 1 (mais sério) — inclusão de espécie de bioma diferente

Chunk 3 (*Leptodactylus notoaktites* Heyer, 1978) tem `Bioma: Mata Atlântica`
no próprio cabeçalho — não ocorre no Pantanal. A resposta original (antes do
fix, commit anterior a este documento) incluiu a espécie na lista de "anuros
que existem no Pantanal" mesmo notando, na mesma frase, que ela "está
presente na Mata Atlântica" — uma contradição interna que a resposta não
resolveu a favor da pergunta feita. Pior que uma omissão: apresenta uma
espécie errada como resposta a uma pergunta sobre bioma específico.

## Achado 2 — omissão de evidência forte

Chunk 4 (*Pseudopaludicola motorzinho*, seção "População") tem
`Bioma: Amazônia, Cerrado, Pantanal` e descreve ocorrência real e detalhada
no Pantanal ("localmente abundante... segunda espécie mais abundante entre
27 anuros registrados" no PARNA do Pantanal) — a evidência mais forte e
específica do lote recuperado. Ficou de fora da resposta original sem
justificativa; a resposta chegou a se autodenunciar ("documentadas nos
trechos 1, 2 e 3"), ignorando os trechos 4 e 5 sem revisá-los.

(Chunk 5, *Rhinella arenarum*, `Bioma: Mata Atlântica, Pampa`, foi
corretamente excluído — não é um bug generalizado de "sempre inclui/exclui
tudo", é inconsistência por trecho.)

## Causa provável

As fichas SALVE trazem um campo estruturado e confiável (`Bioma: ...`) logo
no início do chunk, mas `PROMPT_SISTEMA` (`backend/services/geracao.py`) não
instruía o modelo a usar esse campo como critério — a decisão de "essa
espécie ocorre no bioma perguntado?" ficava a cargo de inferência livre do
texto corrido (inclusive de referências bibliográficas, que citam biomas em
contextos não relacionados à ocorrência da espécie em si), com qwen2.5:3b.
Some a isso o mesmo padrão de leitura incompleta já visto no achado B2 de
`teste-perguntas-dominio.md`: nem todos os trechos são revisados antes da
resposta final.

## Fix tentado

Adicionado a `PROMPT_SISTEMA` (commit deste documento): instrução para (1)
revisar todos os trechos antes de responder, priorizando seções tipo
"População" sobre listas de referências, e (2) para perguntas de espécies
por bioma com fichas SALVE, usar literalmente o campo `Bioma:` do cabeçalho
como critério de inclusão/exclusão, não inferir do resto do texto.

## Reteste (4 execuções, mesma pergunta, mesmo `top_k=5`)

Sem fixar `temperature`/`seed` (`backend/services/llm.py`), então cada
execução pode amostrar de forma diferente — metodologia já estabelecida no
projeto de rodar pelo menos 3x antes de declarar um fix confirmado.

1. **Melhorou o achado 2, não corrigiu o achado 1**: lista as 4 espécies
   corretas do Pantanal (`Pseudis paradoxa`, `Physalaemus biligonigerus`,
   `Pseudopaludicola motorzinho` — achado 2 resolvido nesta execução) mas
   ainda inclui `Leptodactylus notoaktites` sem qualificação (achado 1
   persiste).
2. **Corrigiu o achado 1, reintroduziu o achado 2, e criou um novo problema
   de subinclusão**: reconhece corretamente que `Leptodactylus notoaktites`
   é só de Mata Atlântica ("não há evidências suficientes sobre sua
   ocorrência no bioma do Pantanal") — mas a conclusão final da resposta
   contradiz o próprio raciocínio, afirmando que só `Pseudis paradoxa` "pode
   ser confirmada" e pondo em dúvida `Physalaemus biligonigerus` (que **tem**
   `Bioma: ... Pantanal` no cabeçalho, inclusão claramente válida).
   `Pseudopaludicola motorzinho` (achado 2) volta a ficar de fora.
3. **Retida pelo hard gate** (`resposta_fundamentada: false`) — sem detalhe
   do texto original (mensagem de retenção substitui a resposta).
4. **Retida pelo hard gate**, termo isolado "Atlântico" — mesma família de
   falso positivo já catalogada na bateria `2026-09-02_17h16` para
   "Nacionais" (`diagnosticos/baterias/2026-09-02_17h16_qwen2.5-3b-instruct.md`,
   achado B2): um fragmento de bioma/categoria administrativa capturado pelo
   padrão de nome+parênteses ou item de lista, não uma fabricação real.
   Aqui é bem plausível — a resposta provavelmente escreveu algo como
   "bioma Atlântico" ao descrever `Leptodactylus notoaktites`.

## Conclusão

O fix **não elimina** os dois achados de forma confiável — mudou o padrão de
falha (de "sempre confiante e às vezes errado" para "às vezes certo, às
vezes errado, às vezes retido/hedgeado demais"), mas isso não é claramente
pior do ponto de vista do projeto: `CLAUDE.md` prioriza reter uma resposta
duvidosa sobre mostrar uma errada, e 2 das 4 execuções resultaram em
retenção segura (ainda que por um motivo lateral — falso positivo do hard
gate em "Atlântico" — não por reconhecimento correto da ambiguidade).

**Mantive o fix** (é uma instrução objetivamente correta — "use o campo
estruturado que já existe no chunk" — mesmo que o modelo de 3B nem sempre a
siga à risca) mas não considero o achado 1/2 resolvido. Isso confirma, com
um caso concreto, a avaliação já feita antes desta investigação: ajustes de
prompt/léxico neste modelo local têm retorno decrescente — o problema de
fundo é capacidade de seguir instrução composta (checar um campo estruturado
E revisar todos os trechos) de um modelo de 3B, não corrigível por mais uma
frase no prompt. Solução estrutural melhor (não implementada agora, fora do
escopo desta investigação pontual): extrair o campo `Bioma:` como metadado
estruturado na indexação (`scripts/processamento/gerar_chunks.py`) e aplicar
como filtro de payload no Qdrant (`backend/services/retrieval.py`), do
mesmo jeito que já existe filtro por `nivel_sensibilidade` — tira a decisão
de biomas do LLM e vira um filtro determinístico antes mesmo da geração,
igual ao padrão já usado no roteamento por fonte
(`backend/services/roteamento.py`).

## Pendência residual — novo falso positivo do hard gate ("Atlântico")

Mesma classe do achado "Nacionais" (fragmento de nome de bioma/categoria
administrativa) — registrar como mais uma variante a cobrir numa futura
rodada de ajuste de `_SUBSTANTIVOS_GATILHO_COMUNS`/`_CONECTIVOS_E_PRONOMES_COMUNS`
(`backend/services/groundedness.py`), sem prioridade isolada — mesmo padrão
de "cada bateria expõe uma variação nova" já documentado.

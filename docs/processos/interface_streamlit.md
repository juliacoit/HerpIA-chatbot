# Interface Streamlit (Fase 7)

Protótipo de chat em `interface/`, consumindo o backend FastAPI (Fase 6, ver
[`backend_fastapi.md`](backend_fastapi.md)). Primeira interface de usuário do
projeto — até aqui só existia o Swagger (`/docs`).

## Estrutura

```
interface/
├── app.py           # UI Streamlit (chat, filtros, exibição de citações e feedback)
├── cliente_api.py    # chamadas HTTP ao backend (POST /perguntar, POST /feedback, GET /saude)
└── tema.py           # identidade visual (CSS + wordmark), ver seção "Identidade visual"
```

Mesma separação de responsabilidades do resto do projeto: `cliente_api.py`
isola a comunicação de rede (erros de conexão viram `ErroAPI` com mensagem já
pronta para exibição), `tema.py` isola a marca, `app.py` só cuida de UI e
estado da sessão (`st.session_state.historico`).

## Identidade visual

**2026-09-16**: a paleta forest/amber/cream do guia de identidade visual
original (artifact "HerpIA — Guia de Identidade Visual") foi **descontinuada**
e substituída por um design system novo — teal institucional + neutros
areia (nunca cinza puro), tipografia Spectral/Source Sans 3/IBM Plex Mono.
Motivo: o guia original não cobria formalmente estados de resposta, forma
(raio/sombra), espaçamento e movimento — o design system novo define esses
tokens explicitamente, o que permitiu recolorir também os estados de
resposta (ver abaixo), não só fonte/cor de base. **`interface/tema.py`
(`CORES`, `CORES_FONTE`) é a fonte de verdade dos hex — não reinventar cor
aqui, só portar.**

`interface/tema.py` porta o design system para dentro das restrições do
Streamlit — não recria o sistema inteiro, só o que dá para fazer com
CSS/HTML seguro:

- **`.streamlit/config.toml`**: tema nativo do Streamlit (fundo, cor
  primária, texto) com os mesmos hex de `tema.CORES` — cobre botões, sliders
  e fundo padrão sem precisar de CSS.
- **`tema.aplicar_estilo()`**: injeta as três fontes (Spectral para
  títulos, Source Sans 3 para corpo, IBM Plex Mono para dado/código) via
  Google Fonts; controles (botões, chat input) em pill (raio 999px), cards
  (`stExpander`) em raio 14px; recolore os estados de resposta e do backend
  (ver abaixo) e aplica a tipografia da resposta (17px/28px, medida máxima
  68ch). Mira seletores/testids estáveis do Streamlit 1.63
  (`.stApp`, `[data-testid="stExpander"]`, `[data-testid="stAlertContainer"]`,
  `[data-testid^="stBaseButton"]`, `[data-testid="stChatMessageContent"]`)
  — testids não são API pública versionada do Streamlit, então uma major
  version futura pode renomeá-los; o pior caso é o estilo não aplicar
  (degrada para o tema nativo), não quebra layout. Revalidar visualmente
  depois de qualquer bump de versão do Streamlit.
- **`tema.cabecalho()`/`tema.marca_sidebar()`**: substituem `st.title` e dão
  um bloco de marca na sidebar (wordmark "Herp**IA**", teal institucional
  sobre fundo escuro) — blocos de HTML **estáticos**, nunca interpolam texto
  do backend/LLM (ver docstring do módulo para o motivo: `unsafe_allow_html`
  só é seguro enquanto os campos dinâmicos — resposta, citação, pergunta —
  continuarem passando por `st.write`/`st.markdown` sem essa flag). **Sem
  selo**: o design system novo é tipográfico, não define símbolo (decisão
  2026-09-16 — o selo do guia anterior, ficha de campo + lagartixa, foi
  removido, não recolorido).

**Deliberadamente não portado**: o "indicador de confiança" de 3 níveis
(alta/moderada/baixa) que o guia anterior mostrava como componente — o
backend só calcula `resposta_fundamentada` booleano (`backend/schemas.py`),
então um componente de 3 níveis na interface estaria afirmando uma
granularidade que o sistema não tem. Os dois estados reais
(`evidencia_suficiente`/`resposta_fundamentada`) continuam em
`st.info`/`st.warning` (a lógica de qual é chamado não mudou, só a cor via
CSS, ver abaixo).

**Chip de fonte na citação**: `app.py._chip_fonte()` usa a cor fixa por
fonte de dados (`tema.CORES_FONTE`) como prefixo colorido do título de cada
`st.expander` de citação. Como o label do `st.expander` só aceita um
subconjunto de Markdown (não `unsafe_allow_html`), o chip usa a sintaxe
nativa de cor custom do Streamlit — `:color[TEXTO]{foreground="#hex"}` —
em vez de HTML, então não quebra a invariante de segurança acima (nada de
`fonte`/`documento` do backend passa por `unsafe_allow_html`; o hex vem só
de `tema.CORES_FONTE`, nunca do backend). Não é um chip com borda/pill
literal (o Markdown de label não dá controle de padding/borda), só texto
em negrito na cor da fonte — aproximação aceita dentro da limitação do
Streamlit.

**Testado sem navegador** (mesma limitação de Chrome/sudo já documentada
abaixo) via `streamlit.testing.v1.AppTest` — roda o script inteiro
headless e captura exceções reais de execução, diferente de só checar
HTTP 200: `at.run()` (carga inicial), `at.chat_input[0].set_value(...).run()`
(pergunta real contra o backend, checando `chat_message`/`expander`
gerados) e clique no botão "Útil" (fluxo de feedback) — as três vezes sem
exceção.

**2026-09-16, testado no navegador** (Chromium do Playwright baixado
avulso, `~/.cache/ms-playwright/`, e acionado via CLI headless — o canal
`chrome` que o MCP do Playwright exige continua indisponível, mesma
limitação de sudo já documentada) — confirmou visualmente o cabeçalho, a
sidebar e o card de status na paleta nova. Duas descobertas no processo,
registradas aqui para não repetir a investigação:

- **`st.markdown(html, unsafe_allow_html=True)` não é mais seguro para
  injetar `<style>`** no Streamlit 1.63 instalado neste venv — o bloco de
  CSS aparecia como texto solto na página em vez de aplicar (reproduzido
  isoladamente, fora deste projeto). `aplicar_estilo()` usa `st.html()`
  agora, que não tem esse problema (ver comentário na função). Os blocos
  de `cabecalho()`/`marca_sidebar()` (só `<div>`, sem `<style>`) continuam
  em `st.markdown(unsafe_allow_html=True)` normalmente.
- **O watcher de arquivo do Streamlit no WSL é poll-based** ("Detected
  WSL. Using poll-based file watching") e, neste teste, não recarregou o
  módulo `tema.py` num processo `streamlit run` de longa duração já
  aberto (edições em `tema.py`, importado via `import tema` em `app.py`,
  não refletiram em novas sessões de navegador até o processo ser
  reiniciado) — só `app.py` (o script principal) parece sempre reexecutar
  fresco. **Depois de editar `tema.py`, reinicie o `streamlit run`** em
  vez de confiar no watcher para ver a mudança.

## Rodando localmente

Requer o backend já rodando (ver `SETUP_PROJETO.md`):

```bash
source venv/bin/activate
streamlit run interface/app.py
```

Abre em `http://localhost:8501`. Por padrão aponta para o backend em
`http://localhost:8000`; para apontar para outro endereço, defina
`BACKEND_API_URL` antes de rodar (ex.: backend n PC servidor via túnel SSH).

## Funcionalidade

- **Campo de pergunta** (`st.chat_input`) — histórico da conversa mantido em
  `st.session_state.historico` (perdido ao recarregar a página; sem
  persistência entre sessões, escopo de protótipo).
- **Filtros na sidebar**: restringir por fonte (`monitora`/`pans`/`salve`) e
  `top_k` — mesmos parâmetros de `POST /perguntar`.
- **Exibição da resposta**, diferenciada por estado (mesmos campos de
  `PerguntarResponse`, ver `backend_fastapi.md`); a cor de cada faixa vem do
  CSS em `tema.aplicar_estilo()` (recolore `st.info`/`st.warning` nativos via
  `[data-testid="stAlertContainer"]`, ver "Identidade visual" acima):
  - `evidencia_suficiente: false` → `st.info`, faixa `clay_100`/`clay_700`
    (mensagem fixa de "sem evidência").
  - `resposta_fundamentada: false` → `st.warning`, faixa
    `amber_100`/`amber_700`, com a mensagem de retenção do groundedness
    (`backend/services/groundedness.py`) e, se houver,
    `justificativa_groundedness` como legenda.
  - Caso normal → resposta exibida direto, sem faixa, tipografia 17px/28px
    com medida máxima 68ch.
- **Citações**, um `st.expander` colapsado por citação (título: chip da
  fonte na cor fixa de `tema.CORES_FONTE`, documento, seção, página), com a
  URL de origem e o **texto do chunk recuperado** (`Citacao.texto`, ver
  `backend_fastapi.md`) dentro — permite conferir a fonte exata sem sair da
  interface. Um expander por citação em vez de uma lista dentro de um único
  expander porque o Streamlit não
  permite expander aninhado.
- **Feedback por resposta** (`POST /feedback`): dois botões, "Útil"/"Não
  útil". Desabilitado (mensagem explicando o motivo) quando `id` da resposta
  é `null` — acontece quando o PostgreSQL está indisponível na sessão do
  backend (comportamento de degradação graciosa já documentado em
  `backend_fastapi.md`), caso em que não há `interacao_id` para referenciar.
- **Indicador de saúde do backend** na sidebar (`GET /saude`): `st.success`
  (faixa `moss_100`/`moss_700`) ou `st.error` (faixa `clay_100`/`clay_700`),
  com mensagem de onde olhar (`SETUP_PROJETO.md`) se estiver fora do ar.

## Testado

**2026-09-04, manualmente pela Júlia** em http://localhost:8501, contra o
backend real (59.085 pontos indexados): três perguntas — jararaca-ilhoa
(CR, citações PANs+SALVE corretas), anuros do Pantanal (roteamento
heurístico para SALVE funcionou, ver `backend/services/roteamento.py`) e
uma pergunta sobre SEI (recusada corretamente, fonte não indexada). Fluxo
completo confirmado: pergunta → resposta com citações → expander por
citação com o texto do chunk. Não pôde ser testado por Claude Code nesta
sessão — Playwright exige o canal "chrome", que precisa de `apt`/root para
instalar, sem sudo interativo disponível neste ambiente.

Observação de qualidade (não era bug da interface): na resposta sobre
anuros do Pantanal, o texto final só mencionava 3 das 5 espécies presentes
nas citações, e uma execução chegou a incluir uma espécie de outro bioma —
investigado a fundo em
[`diagnosticos/agregacao-biomas-fichas-salve.md`](../../diagnosticos/agregacao-biomas-fichas-salve.md)
graças ao campo `Citacao.texto`. Corrigido na mesma sessão com um filtro de
payload determinístico no Qdrant (bioma/categoria de risco), não mais
prompt — a inclusão de espécie de bioma errado não reapareceu em nenhuma
das execuções de reteste nem na bateria completa de 21 perguntas rodada
depois do fix.

## O que falta (próximas sessões)

- [ ] Persistir a conversa entre recarregamentos de página (hoje é só
  `st.session_state`, perdido a cada refresh) — não é claro se vale a pena
  para um protótipo de validação com usuários, avaliar com a equipe do RAN
- [ ] Autenticação de usuário (mesma pendência do backend, Fase 6)
- [ ] Avaliar exibir também `POST /buscar` (retrieval sem geração) como modo
  de depuração para a equipe técnica, se for útil durante a validação

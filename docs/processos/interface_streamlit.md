# Interface Streamlit (Fase 7)

Protótipo de chat em `interface/`, consumindo o backend FastAPI (Fase 6, ver
[`backend_fastapi.md`](backend_fastapi.md)). Primeira interface de usuário do
projeto — até aqui só existia o Swagger (`/docs`).

## Estrutura

```
interface/
├── app.py           # UI Streamlit (chat, filtros, exibição de citações e feedback)
└── cliente_api.py    # chamadas HTTP ao backend (POST /perguntar, POST /feedback, GET /saude)
```

Mesma separação de responsabilidades do resto do projeto: `cliente_api.py`
isola a comunicação de rede (erros de conexão viram `ErroAPI` com mensagem já
pronta para exibição), `app.py` só cuida de UI e estado da sessão
(`st.session_state.historico`).

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
  `PerguntarResponse`, ver `backend_fastapi.md`):
  - `evidencia_suficiente: false` → `st.info` (mensagem fixa de "sem
    evidência").
  - `resposta_fundamentada: false` → `st.warning` com a mensagem de retenção
    do groundedness (`backend/services/groundedness.py`) e, se houver,
    `justificativa_groundedness` como legenda.
  - Caso normal → resposta exibida direto.
- **Citações**, um `st.expander` colapsado por citação (título: fonte,
  documento, seção, página), com a URL de origem e o **texto do chunk
  recuperado** (`Citacao.texto`, ver `backend_fastapi.md`) dentro — permite
  conferir a fonte exata sem sair da interface. Um expander por citação em
  vez de uma lista dentro de um único expander porque o Streamlit não
  permite expander aninhado.
- **Feedback por resposta** (`POST /feedback`): dois botões, "Útil"/"Não
  útil". Desabilitado (mensagem explicando o motivo) quando `id` da resposta
  é `null` — acontece quando o PostgreSQL está indisponível na sessão do
  backend (comportamento de degradação graciosa já documentado em
  `backend_fastapi.md`), caso em que não há `interacao_id` para referenciar.
- **Indicador de saúde do backend** na sidebar (`GET /saude`), com mensagem
  de onde olhar (`SETUP_PROJETO.md`) se estiver fora do ar.

## O que falta (próximas sessões)

- [ ] Testar o fluxo completo num navegador de verdade (bloqueado nesta
  sessão — Playwright sem Chromium instalável neste ambiente, sem sudo
  interativo; validado via chamada direta a `interface/cliente_api.py`
  contra o backend real e via `streamlit run` + checagem HTTP do processo,
  ver histórico de commits)
- [ ] Persistir a conversa entre recarregamentos de página (hoje é só
  `st.session_state`, perdido a cada refresh) — não é claro se vale a pena
  para um protótipo de validação com usuários, avaliar com a equipe do RAN
- [ ] Autenticação de usuário (mesma pendência do backend, Fase 6)
- [ ] Avaliar exibir também `POST /buscar` (retrieval sem geração) como modo
  de depuração para a equipe técnica, se for útil durante a validação

repo: juliacoit/chatbot-ran-icmbio
branch: main
path: (raiz — README.md, CLAUDE.md, backend/, docs/)

## Last sync
date: 2026-09-16T17:35:00Z

### Updated in this project
- Design system autorado a partir do contexto do repositório (o repo não contém front-end, CSS, fontes nem logo).
- Tokens de cor/tipo/forma/movimento derivados do domínio e do contrato da API FastAPI.
- Componentes de domínio espelham campos reais de `PerguntarResponse` e `BuscaResponse`.
- UI kit "HerpIA (assistente)" construído sobre `/perguntar`, `/buscar` e `/feedback` — proposta, não recriação.

## Screen map
| Tela / arquivo | Arquivos do repositório |
| --- | --- |
| `ui_kits/herpia-assistente/index.html` (Consulta) | `backend/routers/perguntar.py`, `backend/services/geracao.py`, `backend/schemas.py`, `backend/routers/feedback.py` |
| `ui_kits/herpia-assistente/busca.card.html` (Busca) | `backend/routers/busca.py`, `backend/services/retrieval.py`, `backend/services/roteamento.py`, `backend/schemas.py` |
| `ui_kits/herpia-assistente/login.card.html` (Acesso) | `CLAUDE.md` (público-alvo), `backend/main.py` (autenticação pendente) |
| `components/rag/*` | `backend/schemas.py`, `backend/services/geracao.py`, `backend/services/groundedness.py` |
| `readme.md` (conteúdo e tom) | `README.md`, `CLAUDE.md`, `backend/services/geracao.py`, mensagens de erro dos routers |

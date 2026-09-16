# UI kit — HerpIA (assistente interno RAN/ICMBio)

**Aviso importante:** o repositório de origem (`juliacoit/chatbot-ran-icmbio`) **não contém interface alguma** — nem front-end, nem CSS, nem protótipo Streamlit implementado (a interface é a Fase 8 do roadmap, ainda não iniciada). Portanto este kit **não é uma recriação** de telas existentes: é uma proposta construída estritamente sobre o contrato da API FastAPI (`backend/`) e sobre as regras de resposta definidas em `CLAUDE.md`. Nada aqui foi inventado além do necessário para representar campos reais.

## Telas

| Tela | Base no código-fonte |
| --- | --- |
| `LoginScreen.jsx` | `CLAUDE.md` — público-alvo interno (técnicos, gestores, pesquisadores do RAN); autenticação citada como "ainda não implementada" em `backend/main.py` |
| `ConsultaScreen.jsx` | `POST /perguntar` → `PerguntarResponse` (`resposta`, `citacoes`, `evidencia_suficiente`, `resposta_fundamentada`, `justificativa_groundedness`); `POST /feedback` (`avaliacao` 1/−1, `comentario`) |
| `BuscaScreen.jsx` | `POST /buscar` → `BuscaResponse.resultados[]` (`score`, `fonte`, `documento`, `secao`, `pagina_inicio/fim`, `url_origem`, `nivel_sensibilidade`) |

## Fidelidade e lacunas

- Filtro de fontes usa exatamente as chaves da API: `monitora`, `pans`, `salve` (+ `sei` desabilitado, pois nunca está indexado — ver `backend/services/geracao.py`).
- `top_k` limitado a 1–20 como em `BuscaRequest`.
- Textos de erro reproduzem as mensagens reais dos endpoints (Ollama 503, PostgreSQL indisponível, SEI não indexado).
- Não há marca gráfica: o cabeçalho usa `Wordmark` (tipografia), pois não existe logo nos materiais fornecidos.

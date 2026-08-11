# Backend FastAPI (Fase 6)

Esqueleto inicial do backend do RAG, implementado em `backend/`. Cobre a parte
já desbloqueada pela Fase 5 (Qdrant indexado com BGE-M3): busca semântica e
geração de resposta com citações. Ainda não cobre logging/feedback em
PostgreSQL, busca híbrida nem autenticação de usuários — ver "O que falta"
no fim deste documento.

## Estrutura

```
backend/
├── main.py              # cria o FastAPI app, carrega os recursos pesados no startup (lifespan)
├── config.py             # Settings (pydantic-settings), lê o mesmo .env dos scripts de indexação
├── schemas.py             # modelos Pydantic (request/response) dos endpoints
├── dependencies.py        # Depends() que expõem os recursos carregados no startup
├── routers/
│   ├── busca.py           # POST /buscar — só retrieval, sem LLM (para depurar)
│   └── perguntar.py        # POST /perguntar — retrieval + geração com citações
└── services/
    ├── retrieval.py        # embeda a pergunta (BGE-M3) e consulta o Qdrant
    ├── llm.py               # LLMClient (interface, ADR 0006) + OllamaLLMClient
    └── geracao.py            # monta o prompt com os chunks e formata a resposta com citações
```

Segue os mesmos princípios do resto do projeto: responsabilidades separadas
(config / schemas / retrieval / geração / rotas), sem framework de
orquestração de RAG (LangChain/LlamaIndex) — o ADR 0001 deixou essa escolha
em aberto, e os scripts de indexação já mostraram que dá para fazer o
pipeline inteiro sem um framework grande. Reavaliar isso vira necessário
só se a lógica de orquestração crescer muito (ex.: busca híbrida com
reranking, agentes com múltiplas etapas).

## Por que os recursos pesados são carregados uma vez só

O modelo de embeddings (BGE-M3) e o cliente do Qdrant são caros para
inicializar. `main.py` usa o `lifespan` do FastAPI para carregá-los **uma
vez**, no startup do processo, e guardá-los em `app.state`. Os endpoints
pegam essas instâncias via `Depends` (`backend/dependencies.py`) em vez de
recriá-las a cada requisição — caso contrário, cada pergunta pagaria o custo
de recarregar o modelo (~alguns segundos) antes mesmo de embedar a pergunta.

## Endpoints

### `GET /saude`
Checagem simples de que o processo está de pé. `{"status": "ok"}`.

### `POST /buscar`
Só retrieval — não chama o LLM. Útil para depurar a qualidade da busca
semântica isoladamente (é basicamente o `--buscar` do
`scripts/indexacao/indexar_chunks.py`, exposto como API).

Request:
```json
{"pergunta": "qual o status de conservação da jararaca-ilhoa?", "top_k": 5, "fontes": ["salve", "pans"]}
```
`top_k` (1-20, padrão 5) e `fontes` (lista opcional; valores: `monitora`,
`pans`, `salve`) são opcionais.

Response: lista de `ChunkRecuperado` (score, fonte, documento, texto, seção/
categoria, página, URL, caminho local, nível de sensibilidade).

### `POST /perguntar`
Retrieval + geração: monta um prompt com os chunks recuperados, chama o LLM
configurado (`LLMClient`, ADR 0006) e devolve a resposta com as citações
correspondentes (deduplicadas por documento/seção/página).

Mesmo request de `/buscar`. Response:
```json
{
  "pergunta": "...",
  "resposta": "...",
  "citacoes": [{"fonte": "...", "documento": "...", "secao": "...", "pagina_inicio": null, "url_origem": "..."}],
  "evidencia_suficiente": true
}
```

Se a busca não retornar nenhum chunk, a resposta é fixa ("Não há evidência
suficiente...", `evidencia_suficiente: false`) e o LLM **não** é chamado —
evita gastar uma chamada de geração numa pergunta sem base para responder.

`evidencia_suficiente` hoje só reflete se algum chunk foi recuperado, não se
a resposta do LLM de fato se apoiou neles — checar isso de forma mais
confiável é trabalho da Fase 8 (validação).

Se o Ollama não estiver rodando, o endpoint responde `503` com uma mensagem
explicando como subir o serviço (em vez de vazar um erro genérico de conexão).

## Filtro de acesso

O roadmap da Fase 6 pede para "verificar que apenas chunks de documentos
autorizados são retornados". A indexação (`gerar_chunks.py`) já só lê de
`03_documentos_autorizados/`, então nenhum chunk sensível chega a ser
indexado — mas `backend/services/retrieval.py` aplica um filtro adicional na
consulta ao Qdrant (`nivel_sensibilidade == "autorizado"`), como segunda
camada de defesa, não a única.

## Configuração

Reaproveita as variáveis já existentes no `.env` (nenhuma variável nova):

| Variável | Uso |
|---|---|
| `QDRANT_URL` / `QDRANT_LOCAL_PATH` | mesmo comportamento do `indexar_chunks.py` — local tem prioridade |
| `QDRANT_COLLECTION` | coleção consultada |
| `LLM_PROVIDER`, `OLLAMA_URL`, `LLM_MODEL` | ADR 0006 — hoje só `ollama` está implementado |
| `OPENAI_API_KEY` | reservado para quando `LLM_PROVIDER=openai` for implementado |

## Rodando localmente

```bash
source venv/bin/activate
pip install -r requirements.txt   # inclui fastapi, uvicorn, pydantic-settings, httpx

uvicorn backend.main:app --reload
# docs interativas (Swagger): http://localhost:8000/docs
```

`/buscar` funciona sem nenhuma dependência extra (usa o Qdrant já indexado).
`/perguntar` precisa do Ollama rodando com o modelo baixado:
```bash
scripts/infra/subir_ollama.sh --pull
```

O Ollama foi instalado (2026-08-11) sem root — tarball oficial extraído em
`~/.local` em vez do instalador padrão, porque a sessão não tinha sudo sem
senha disponível. Sem instalador padrão não existe serviço systemd, então
o Ollama não sobe sozinho no boot: rode `scripts/infra/subir_ollama.sh`
manualmente (ele não faz nada se o Ollama já estiver de pé). O binário fica
em `~/.local/bin/ollama`, já coberto pelo `PATH` de novas sessões via
`~/.profile`.

Testado manualmente de ponta a ponta (2026-08-11) contra a coleção real
(59.085 pontos): `/saude`, `/buscar` e `/perguntar` responderam
corretamente — pergunta "qual o status de conservação da jararaca-ilhoa?"
retornou resposta correta (CR, categoria criticamente ameaçada) com as
citações certas (PAN herpetofauna insular + ficha SALVE da *Bothrops
insularis*). ~8s de latência com o modelo já carregado em memória (~35s na
primeira chamada, por causa do load inicial do modelo).

## O que falta (Fase 6, ver roadmap.md)

- [ ] Testar `/perguntar` com uma amostra maior de perguntas reais do domínio (só uma pergunta de fumaça foi validada até agora)
- [ ] Logging de perguntas/chunks recuperados/respostas no PostgreSQL
- [ ] Feedback do usuário (thumbs up/down) por resposta
- [ ] Busca híbrida (semântica + palavras-chave), se a busca pura for insuficiente
- [ ] Autenticação/autorização de usuários (hoje a API não tem nenhuma)
- [ ] `OpenAILLMClient`, se a equipe do RAN confirmar orçamento (ADR 0006)

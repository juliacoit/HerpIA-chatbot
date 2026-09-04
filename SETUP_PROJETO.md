# Como subir o projeto (HerpIA — RAN/ICMBio)

Guia rápido para colocar o backend RAG no ar numa máquina já configurada
(ambiente Python, dados já processados/indexados). Para configurar uma
máquina do zero, ver também `SETUP_WSL_CONEXAO_SERVIDOR.md` (conexão com o
PC servidor) e `SETUP_DOWNLOAD_REMOTO.md` (download das fontes).

## 0. Pré-requisitos já esperados no repositório

- `venv/` com as dependências de `requirements.txt` instaladas.
- `.env` na raiz (copiado de `.env.example` e ajustado — nunca versionar).
- `07_processados/qdrant_local/` com os chunks já indexados (Qdrant embutido,
  sem precisar de Docker — ver `QDRANT_LOCAL_PATH` no `.env`).
- Ollama instalado em `~/.local/bin/ollama` (ver seção 2).

Se algum desses itens não existir, ver `docs/roadmap.md` para o status das
fases anteriores (extração, chunking, embeddings/indexação).

## 1. Ativar o ambiente Python

```bash
source venv/bin/activate
pip install -r requirements.txt   # só se houver dependência nova
```

## 2. Subir o Ollama (LLM local, ADR 0006)

O Ollama foi instalado sem root (tarball em `~/.local`), então não tem
serviço systemd — precisa subir manualmente a cada reinício da máquina/sessão:

```bash
scripts/infra/subir_ollama.sh --pull
```

`--pull` garante que o modelo configurado em `LLM_MODEL` (`.env`, hoje
`qwen2.5:3b-instruct`) está baixado. O script não faz nada se o Ollama já
estiver rodando. Confirma que subiu:

```bash
curl -s http://localhost:11434/api/version
```

## 3. Subir o backend FastAPI

```bash
uvicorn backend.main:app --reload
```

No startup ele carrega o modelo de embeddings (BGE-M3) e conecta ao Qdrant —
leva alguns segundos. Confirma que subiu:

```bash
curl -s http://localhost:8000/saude
# {"status":"ok"}
```

Docs interativas (Swagger): http://localhost:8000/docs

Endpoints principais:
- `POST /buscar` — só retrieval (não chama o LLM), útil para depurar a busca.
- `POST /perguntar` — retrieval + geração com citações (precisa do Ollama).
- `POST /feedback` — thumbs up/down de uma resposta já registrada.

Detalhes de cada endpoint: `docs/processos/backend_fastapi.md`.

## 4. PostgreSQL (opcional — só para logging/feedback)

`/buscar` e `/perguntar` funcionam **sem** o PostgreSQL — se ele estiver
indisponível, o backend loga um aviso e segue funcionando normalmente, só
sem gravar interações/feedback (`id: null` na resposta, `/feedback`
responde `503`).

Para habilitar o logging, suba o Postgres (e o Qdrant em container, se for
usar o Docker em vez do modo embutido) via Docker Compose:

```bash
docker compose up -d
docker compose ps   # confirma ran_postgres / ran_qdrant saudáveis
```

Se aparecer `docker: command not found` no WSL, é preciso habilitar a
integração WSL do Docker Desktop (Settings → Resources → WSL Integration →
ativar para esta distro) — sem isso o `docker` do Windows não fica visível
dentro do WSL.

As portas do compose ficam restritas a `127.0.0.1` — não altere isso sem
revisar as implicações de segurança (ver `docker-compose.yml`).

## 5. Testar rapidamente

```bash
curl -s -X POST http://localhost:8000/buscar \
  -H "Content-Type: application/json" \
  -d '{"pergunta": "qual o status de conservação da jararaca-ilhoa?", "top_k": 3}'

curl -s -X POST http://localhost:8000/perguntar \
  -H "Content-Type: application/json" \
  -d '{"pergunta": "qual o status de conservação da jararaca-ilhoa?"}'
```

## Resumo (checklist)

```bash
source venv/bin/activate
scripts/infra/subir_ollama.sh --pull
uvicorn backend.main:app --reload
# opcional, só para logging/feedback:
docker compose up -d
```

## Problemas comuns

| Sintoma | Causa provável | Solução |
|---|---|---|
| `/perguntar` responde 503 | Ollama não está rodando | `scripts/infra/subir_ollama.sh --pull` |
| Log mostra `PostgreSQL indisponível` | Docker Desktop sem integração WSL, ou containers parados | Ver seção 4 (opcional — resto da API funciona sem isso) |
| `docker: command not found` no WSL | Integração WSL do Docker Desktop desligada | Docker Desktop → Settings → Resources → WSL Integration |
| Startup lento (~20-30s) | Carregamento do modelo BGE-M3 + primeira resposta do Ollama | Normal na primeira chamada; próximas ficam rápidas (~8s) |
| Não há interface web ainda | Streamlit (Fase 7 do roadmap) ainda não implementado | Usar `/docs` (Swagger) ou `curl` por enquanto |

Não há interface Streamlit implementada ainda (ver `docs/roadmap.md`) — a
forma atual de interagir com o sistema é via API (`/docs` ou `curl`/HTTP
client).

#!/usr/bin/env bash
# Fase 4 do experimento Lumi-4B (docs/processos/experimento_lumi_4b.md).
# Roda UMA configuração da bateria de domínio contra o backend deste worktree.
#
# Uso: rodar_bateria.sh <rotulo> <modelo> <think: ''|true|false> [args extras de teste_perguntas_dominio.py]
#   ex.: rodar_bateria.sh C3 lumi-4b false
#        rodar_bateria.sh C4-calibracao lumi-4b true --repeticoes 1 --categorias A,B,F,J,L
#
# - Parâmetros do LLM só por variáveis de ambiente na linha de comando; o .env
#   principal é lido (uvicorn --env-file, sem sobrescrever as variáveis daqui)
#   e nunca alterado.
# - QDRANT_LOCAL_PATH absoluto: relativo, ele seria resolvido contra a raiz do
#   worktree, onde a base não existe, e o Qdrant embutido criaria uma vazia.
# - Porta 8010 para não colidir com um backend de produção na 8000. O Qdrant
#   embutido trava a pasta: não pode haver outro backend usando a base.
set -euo pipefail

ROTULO=$1; MODELO=$2; THINK=$3; shift 3
WT=/home/juliacoite/dev/chatbot-ran-icmbio-lumi
PRINCIPAL=/home/juliacoite/dev/chatbot-ran-icmbio
PY=$PRINCIPAL/venv/bin/python
OLLAMA=$HOME/.local/bin/ollama
PORTA=8010
URL=http://127.0.0.1:$PORTA
LOGDIR=$HOME/experimentos-llm/fase4-logs
mkdir -p "$LOGDIR"
CARIMBO=$(date +%Y%m%d_%H%M)
LOG_UVICORN=$LOGDIR/${CARIMBO}_${ROTULO}_uvicorn.log
LOG_MONITOR=$LOGDIR/${CARIMBO}_${ROTULO}_monitor.log

echo "[$(date +%T)] $ROTULO: modelo=$MODELO think='${THINK}' extras=$*"

cd "$WT"
env LLM_MODEL="$MODELO" LLM_THINK="$THINK" LLM_NUM_CTX=16384 LLM_TEMPERATURE=0 LLM_SEED=42 \
    LLM_TIMEOUT=900 GROUNDEDNESS_VERIFICAR=false \
    QDRANT_LOCAL_PATH="$PRINCIPAL/07_processados/qdrant_local" \
    "$PY" -m uvicorn backend.main:app --host 127.0.0.1 --port $PORTA --env-file "$PRINCIPAL/.env" \
    > "$LOG_UVICORN" 2>&1 &
PID_UVICORN=$!

monitorar() {
    while true; do
        {
            echo "=== $(date +%T)"
            "$OLLAMA" ps 2>/dev/null | tail -n +2
            nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader
            ps -eo rss=,args= | awk '/llama-server|uvicorn backend.main/ && !/awk/ {printf "RSS %.2f GiB %s\n", $1/1048576, $2}'
        } >> "$LOG_MONITOR" 2>&1
        sleep 60
    done
}

limpar() {
    kill "${PID_MONITOR:-}" 2>/dev/null || true
    kill "$PID_UVICORN" 2>/dev/null || true
    wait "$PID_UVICORN" 2>/dev/null || true
    curl -s "http://127.0.0.1:11434/api/generate" -d "{\"model\":\"$MODELO\",\"keep_alive\":0}" > /dev/null || true
}
trap limpar EXIT

for _ in $(seq 1 180); do
    curl -sf "$URL/saude" > /dev/null && break
    kill -0 "$PID_UVICORN" 2>/dev/null || { echo "uvicorn morreu; ver $LOG_UVICORN"; exit 1; }
    sleep 2
done
curl -sf "$URL/saude" > /dev/null || { echo "backend não subiu; ver $LOG_UVICORN"; exit 1; }
echo "[$(date +%T)] backend de pé: $(curl -s "$URL/saude" | "$PY" -c 'import json,sys; print(json.load(sys.stdin)["llm"])')"

# Aquecimento (fora da bateria e das latências), como na rodada 1.
curl -s -X POST "$URL/perguntar" -H 'Content-Type: application/json' --max-time 960 \
    -d '{"pergunta": "Qual o status de conservação da jararaca-ilhoa?", "top_k": 8}' > /dev/null || true
echo "[$(date +%T)] aquecimento feito"

monitorar & PID_MONITOR=$!
"$PY" scripts/teste_perguntas_dominio.py --url "$URL" --top-k 8 --timeout 960 "$@"
echo "[$(date +%T)] $ROTULO concluída"

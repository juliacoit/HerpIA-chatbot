#!/usr/bin/env bash
# Sobe o Ollama (LLM local, ADR 0006) em background, se ainda não estiver rodando.
#
# Instalado sem root em ~/.local (tarball oficial, não o instalador padrão),
# porque a máquina de dev não tem sudo sem senha disponível para esta sessão.
# Por isso não existe um serviço systemd — precisa rodar este script (ou
# `ollama serve`) manualmente a cada reinício da máquina/sessão.
#
# Uso:
#   scripts/infra/subir_ollama.sh
#   scripts/infra/subir_ollama.sh --pull   # também garante que o modelo do ADR 0006 está baixado

set -uo pipefail

MODELO="qwen2.5:3b-instruct"
LOG_DIR="$HOME/.ollama/logs"
mkdir -p "$LOG_DIR"

export PATH="$HOME/.local/bin:$PATH"

if ! command -v ollama > /dev/null; then
    echo "ollama não encontrado em ~/.local/bin — reinstalar (ver docs/processos/backend_fastapi.md)." >&2
    exit 1
fi

if curl -s -o /dev/null http://localhost:11434/api/version; then
    echo "Ollama já está rodando (http://localhost:11434)."
else
    echo "Subindo o Ollama em background..."
    nohup ollama serve > "$LOG_DIR/serve.log" 2>&1 &
    disown
    for _ in $(seq 1 30); do
        curl -s -o /dev/null http://localhost:11434/api/version && break
        sleep 1
    done
    echo "Ollama no ar. Log: $LOG_DIR/serve.log"
fi

if [ "${1:-}" = "--pull" ]; then
    echo "Garantindo que o modelo $MODELO está baixado..."
    ollama pull "$MODELO"
fi

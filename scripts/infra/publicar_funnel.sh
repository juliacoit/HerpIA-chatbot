#!/usr/bin/env bash
# Publica a interface do HerpIA na internet pelo Tailscale Funnel, em HTTPS,
# sem depender da rede interna do RAN. Só a interface (Streamlit, porta 8501)
# é publicada; backend, PostgreSQL, Qdrant e Ollama continuam em 127.0.0.1.
#
# Com a interface pública, o login é a única barreira. Por isso o script se
# recusa a publicar se o backend não estiver exigindo sessão para tudo.
# Ver docs/processos/acesso_externo_funnel.md.
#
# Uso:
#   scripts/infra/publicar_funnel.sh            # confere e publica
#   scripts/infra/publicar_funnel.sh status     # mostra o que está publicado
#   scripts/infra/publicar_funnel.sh parar      # tira do ar
#
# Variáveis: BACKEND_API_URL (padrão http://localhost:8000),
# PORTA_INTERFACE (padrão 8501).

set -uo pipefail

BACKEND="${BACKEND_API_URL:-http://localhost:8000}"
PORTA="${PORTA_INTERFACE:-8501}"

falhar() { echo "NÃO PUBLICADO: $1" >&2; exit 1; }

# O Tailscale está instalado no Windows (recomendação da documentação para
# WSL 2), então o comando é o .exe chamado de dentro do WSL. O Windows alcança
# a porta do Streamlit no WSL por 127.0.0.1.
TAILSCALE_EXE="/mnt/c/Program Files/Tailscale/tailscale.exe"
if command -v tailscale >/dev/null; then
    tailscale() { command tailscale "$@"; }
elif [ -x "$TAILSCALE_EXE" ]; then
    tailscale() { "$TAILSCALE_EXE" "$@"; }
else
    falhar "o Tailscale não está instalado (ver docs/processos/acesso_externo_funnel.md)."
fi

case "${1:-publicar}" in
    status) tailscale funnel status; exit $? ;;
    parar)
        tailscale funnel --https=443 off || falhar "o Tailscale não conseguiu desligar o Funnel."
        echo "Funnel desligado. A interface voltou a ser acessível só nesta máquina."
        exit 0 ;;
    publicar) ;;
    *) falhar "comando desconhecido: $1 (use publicar, status ou parar)." ;;
esac

# 1. O backend declara que exige login para tudo.
exigir="$(curl -fsS -m 10 "$BACKEND/saude" \
    | python3 -c 'import json,sys; print(json.load(sys.stdin).get("auth",{}).get("exigir",""))' 2>/dev/null || true)"
[ "$exigir" = "tudo" ] || falhar "o backend em $BACKEND respondeu AUTH_EXIGIR='${exigir:-sem resposta}'. Defina AUTH_EXIGIR=tudo no .env e reinicie o backend."

# 2. E de fato recusa uma pergunta sem sessão (não confia só na declaração).
codigo="$(curl -s -m 10 -o /dev/null -w '%{http_code}' -X POST "$BACKEND/perguntar" \
    -H 'content-type: application/json' -d '{"pergunta":"teste de acesso sem sessão"}' || true)"
[ "$codigo" = "401" ] || falhar "o backend respondeu $codigo (esperado 401) a uma pergunta sem login."

# 3. A interface está no ar e escutando só em 127.0.0.1.
curl -fsS -m 10 -o /dev/null "http://127.0.0.1:$PORTA/_stcore/health" \
    || falhar "a interface não responde em 127.0.0.1:$PORTA. Suba com: streamlit run interface/app.py"
if ss -ltnH 2>/dev/null | awk '{print $4}' | grep -E ":$PORTA\$" | grep -qvE '^(127\.0\.0\.1|\[::1\]):'; then
    falhar "a porta $PORTA está aberta fora de 127.0.0.1. Confira [server] address em .streamlit/config.toml."
fi

tailscale funnel --bg --https=443 "127.0.0.1:$PORTA" || falhar "o Tailscale recusou o comando (o Funnel já foi aprovado para esta máquina?)."
echo
tailscale funnel status
echo
echo "Publicado. Para tirar do ar: scripts/infra/publicar_funnel.sh parar"

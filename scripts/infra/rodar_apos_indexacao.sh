#!/usr/bin/env bash
# Aguarda a indexação de embeddings (BGE-M3, scripts/indexacao/indexar_chunks.py)
# terminar e, em seguida, roda automaticamente os próximos passos combinados:
# uma verificação da indexação e o piloto de processamento de imagens (100%
# local, CLIP + VLM local). Pensado para rodar sem supervisão numa máquina que
# vai ficar ligada sem ninguém acompanhando.
#
# Uso:
#   nohup scripts/infra/rodar_apos_indexacao.sh > /dev/null 2>&1 &
#   disown
#
#   # opcional: caminho de um PDF diferente para o piloto de imagens
#   nohup scripts/infra/rodar_apos_indexacao.sh "caminho/para/outro.pdf" > /dev/null 2>&1 &
#
# Acompanhar depois (a qualquer momento, inclusive no dia seguinte):
#   tail -f logs/pipeline_overnight_*.log

set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$RAIZ"

PDF_TESTE="${1:-01_fontes_web/pans/pan-tubaroes/documentos/2018-pan-tubaroes-boletim-1.pdf}"

LOG_DIR="$RAIZ/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/pipeline_overnight_$(date +%Y%m%d_%H%M%S).log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"
}

log "=== Início do acompanhamento automático ==="
log "Aguardando a indexação de embeddings (scripts/indexacao/indexar_chunks.py) terminar..."

while pgrep -f "[s]cripts/indexacao/indexar_chunks.py" > /dev/null; do
    sleep 30
done

log "Indexação finalizada (processo não está mais rodando)."
sleep 10  # dá um tempo para a GPU liberar memória antes do piloto de imagens

source venv/bin/activate

log ""
log "--- Verificação: contagem de pontos na coleção ---"
python -c "
from qdrant_client import QdrantClient
import os
from dotenv import load_dotenv
load_dotenv()
c = QdrantClient(path=os.getenv('QDRANT_LOCAL_PATH'))
colecao = os.getenv('QDRANT_COLLECTION', 'ran_herpetofauna')
print(f'{colecao}: {c.count(colecao).count} pontos indexados')
" >> "$LOG" 2>&1

log ""
log "--- Verificação: busca de teste ---"
python scripts/indexacao/indexar_chunks.py --buscar "qual o status de conservação da jararaca?" >> "$LOG" 2>&1

log ""
log "=== Iniciando piloto de processamento de imagens (CLIP + VLM local, sem custo de API) ==="
OUT_DIR="07_processados/imagens_descritas/piloto"
mkdir -p "$OUT_DIR"

if [ -f "$PDF_TESTE" ]; then
    log "PDF de teste: $PDF_TESTE"
    python scripts/processamento_imagens/processar_imagens_piloto.py "$PDF_TESTE" --output "$OUT_DIR" >> "$LOG" 2>&1
    if [ $? -eq 0 ]; then
        log "Piloto de imagens concluído com sucesso. Resultado em $OUT_DIR/"
    else
        log "ATENÇÃO: piloto de imagens terminou com erro — ver log acima para detalhes."
    fi
else
    log "ATENÇÃO: PDF de teste não encontrado em '$PDF_TESTE' — pulando piloto de imagens."
fi

log ""
log "=== TUDO CONCLUÍDO — ver $LOG para todos os detalhes ==="

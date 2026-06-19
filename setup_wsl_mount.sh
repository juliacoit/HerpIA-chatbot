#!/bin/bash
# setup_wsl_mount.sh
# Script automatizado para montar compartilhamento SMB do servidor no WSL
# Uso: bash setup_wsl_mount.sh

set -e

SERVIDOR_IP="10.62.62.191"
SERVIDOR_HOST="RAN_AvalFauna_FHF9703"
COMPARTILHAMENTO="pans_dados"
CAMINHO_MONTAGEM="/mnt/pans_dados"

echo "=============================================================="
echo "Setup: Montagem SMB no WSL"
echo "=============================================================="
echo ""
echo "Servidor: $SERVIDOR_IP ($SERVIDOR_HOST)"
echo "Compartilhamento: $COMPARTILHAMENTO"
echo "Local de montagem: $CAMINHO_MONTAGEM"
echo ""

# Passo 1: Verificar se cifs-utils está instalado
echo "[PASSO 1] Verificando dependencias..."
if ! command -v mount.cifs &> /dev/null; then
    echo "[AVISO] cifs-utils nao encontrado. Instalando..."
    sudo apt update
    sudo apt install -y cifs-utils
else
    echo "[OK] cifs-utils ja instalado"
fi

# Passo 2: Criar diretorio de montagem
echo ""
echo "[PASSO 2] Criando diretorio de montagem..."
if [ ! -d "$CAMINHO_MONTAGEM" ]; then
    sudo mkdir -p "$CAMINHO_MONTAGEM"
    echo "[OK] Diretorio criado: $CAMINHO_MONTAGEM"
else
    echo "[OK] Diretorio ja existe: $CAMINHO_MONTAGEM"
fi

# Passo 3: Verificar se ja esta montado
echo ""
echo "[PASSO 3] Verificando se ja esta montado..."
if mountpoint -q "$CAMINHO_MONTAGEM"; then
    echo "[INFO] Compartilhamento ja esta montado em $CAMINHO_MONTAGEM"
    echo "[AVISO] Desmontando para remountar..."
    sudo umount "$CAMINHO_MONTAGEM" || true
fi

# Passo 4: Montar compartilhamento
echo ""
echo "[PASSO 4] Montando compartilhamento SMB..."
sudo mount -t cifs //$SERVIDOR_IP/$COMPARTILHAMENTO $CAMINHO_MONTAGEM \
  -o guest,uid=1000,gid=1000,file_mode=0777,dir_mode=0777

if [ $? -eq 0 ]; then
    echo "[OK] Compartilhamento montado com sucesso"
else
    echo "[ERRO] Falha ao montar compartilhamento"
    echo "Verifique:"
    echo "  1. O servidor $SERVIDOR_IP esta online (ping $SERVIDOR_IP)"
    echo "  2. O compartilhamento '$COMPARTILHAMENTO' foi criado"
    echo "  3. Nao ha firewall bloqueando porta 445"
    exit 1
fi

# Passo 5: Verificar conteudo
echo ""
echo "[PASSO 5] Verificando conteudo..."
if [ -d "$CAMINHO_MONTAGEM/01_fontes_web" ]; then
    echo "[OK] Estrutura de diretorios validada"
    echo ""
    echo "Conteudo do compartilhamento:"
    ls -la "$CAMINHO_MONTAGEM"
else
    echo "[ERRO] Estrutura de diretorios incorreta"
    echo "Conteudo encontrado:"
    ls -la "$CAMINHO_MONTAGEM"
    exit 1
fi

# Passo 6: Criar symlink (opcional)
echo ""
echo "[PASSO 6] Criando symlink..."
if [ ! -L "$HOME/pans_dados" ]; then
    ln -s "$CAMINHO_MONTAGEM" "$HOME/pans_dados"
    echo "[OK] Symlink criado: ~/pans_dados -> $CAMINHO_MONTAGEM"
else
    echo "[OK] Symlink ja existe: ~/pans_dados"
fi

# Sucesso!
echo ""
echo "=============================================================="
echo "[SUCESSO] Setup concluido!"
echo "=============================================================="
echo ""
echo "Para fazer download remoto, execute:"
echo ""
echo "  python scripts/coleta/download_documentos_pans.py --servidor $CAMINHO_MONTAGEM"
echo ""
echo "Opcoes:"
echo "  --dry-run              : Testar sem fazer download"
echo "  --apenas-herpetofauna  : Baixar apenas PANs de herpetofauna"
echo "  --pan [SLUG]           : Baixar um PAN especifico"
echo ""
echo "Exemplo completo:"
echo "  python scripts/coleta/download_documentos_pans.py \\\"
echo "    --servidor $CAMINHO_MONTAGEM \\\"
echo "    --apenas-herpetofauna \\\"
echo "    --dry-run"
echo ""

# Setup: Conexão WSL com Servidor via SMB

Este documento descreve como configurar automaticamente o acesso ao compartilhamento SMB do servidor no WSL do PC de desenvolvimento.

## 📋 Informações do Servidor

- **IP Ethernet:** `10.62.62.191`
- **Hostname:** `RAN_AvalFauna_FHF9703`
- **Compartilhamento SMB:** `pans_dados`
- **Caminho local no servidor:** `C:\compartilhado\pans_dados`

---

## 🔧 Passo 1: Montar o Compartilhamento SMB no WSL

Execute **no WSL (terminal Linux)**:

```bash
# Criar diretório de montagem
mkdir -p /mnt/pans_dados

# Montar o compartilhamento SMB
sudo mount -t cifs //10.62.62.191/pans_dados /mnt/pans_dados \
  -o guest,uid=1000,gid=1000,file_mode=0777,dir_mode=0777

# Verificar se foi montado com sucesso
ls -la /mnt/pans_dados
```

**Saída esperada:**
```
total 0
drwxrwxrwx ...  01_fontes_web
drwxrwxrwx ...  03_documentos_autorizados
drwxrwxrwx ...  07_processados
```

---

## 📍 Passo 2: Atualizar o Script Python para usar o Caminho Montado

O script `download_documentos_pans.py` precisa ser modificado para:
1. Quando `--servidor` for passado, verificar se é um caminho montado no WSL
2. Converter o caminho UNC para o caminho local montado

**Script de configuração automática:**

```bash
#!/bin/bash
# setup_wsl_mount.sh

set -e

echo "==================================================================="
echo "Configurando conexao WSL -> Servidor SMB"
echo "==================================================================="

# 1. Montar o compartilhamento
echo "[INFO] Montando compartilhamento SMB..."
mkdir -p /mnt/pans_dados
sudo mount -t cifs //10.62.62.191/pans_dados /mnt/pans_dados \
  -o guest,uid=1000,gid=1000,file_mode=0777,dir_mode=0777 2>/dev/null || true

# 2. Verificar se montou
if [ -d "/mnt/pans_dados/01_fontes_web" ]; then
    echo "[OK] Compartilhamento montado com sucesso em /mnt/pans_dados"
else
    echo "[ERRO] Nao foi possivel montar o compartilhamento"
    echo "Verifique:"
    echo "  1. O servidor 10.62.62.191 esta online"
    echo "  2. O compartilhamento 'pans_dados' foi criado"
    echo "  3. Voce tem cifs-utils instalado: sudo apt install cifs-utils"
    exit 1
fi

# 3. Criar symlink (opcional, para facilitar acesso)
ln -sf /mnt/pans_dados ~/pans_dados 2>/dev/null || true

echo ""
echo "[OK] Setup concluido!"
echo ""
echo "Para fazer download remoto, execute:"
echo "  python scripts/coleta/download_documentos_pans.py --servidor /mnt/pans_dados"
echo ""
echo "Ou, usando o IP (sera convertido para /mnt/pans_dados automaticamente):"
echo "  python scripts/coleta/download_documentos_pans.py --servidor 10.62.62.191"
```

---

## 🚀 Opção A: Usar caminho local montado (RECOMENDADO no WSL)

```bash
# Montar (executar uma vez)
mkdir -p /mnt/pans_dados
sudo mount -t cifs //10.62.62.191/pans_dados /mnt/pans_dados -o guest,uid=1000,gid=1000,file_mode=0777,dir_mode=0777

# Fazer download
python scripts/coleta/download_documentos_pans.py --servidor /mnt/pans_dados

# Ou testar primeiro
python scripts/coleta/download_documentos_pans.py --servidor /mnt/pans_dados --dry-run
```

---

## 🚀 Opção B: Usar IP (automático, se script detectar WSL)

```bash
# Fazer download (o script detecta que é WSL e converte para /mnt/pans_dados)
python scripts/coleta/download_documentos_pans.py --servidor 10.62.62.191

# Ou testar
python scripts/coleta/download_documentos_pans.py --servidor 10.62.62.191 --dry-run
```

---

## 🔄 Para Claude (Automação)

Quando Claude precisar fazer o setup automaticamente no WSL:

```bash
# 1. Montar compartilhamento
mkdir -p /mnt/pans_dados
sudo mount -t cifs //10.62.62.191/pans_dados /mnt/pans_dados \
  -o guest,uid=1000,gid=1000,file_mode=0777,dir_mode=0777 2>/dev/null || true

# 2. Verificar montagem
if [ -d "/mnt/pans_dados/01_fontes_web" ]; then
    echo "OK: Compartilhamento montado"
    
    # 3. Fazer download
    cd ~/chatbot-ran-icmbio
    source venv/bin/activate
    python scripts/coleta/download_documentos_pans.py --servidor /mnt/pans_dados
else
    echo "ERRO: Compartilhamento nao acessivel"
    exit 1
fi
```

---

## ⚙️ Configuração Permanente (opcional)

Para manter a montagem após reiniciar o WSL:

### 1. Instalar `cifs-utils` (se nao tiver)
```bash
sudo apt update
sudo apt install cifs-utils
```

### 2. Criar arquivo de credenciais (opcional, para nao pedir senha)
```bash
cat > ~/.smbcredentials << EOF
username=guest
password=
EOF

chmod 600 ~/.smbcredentials
```

### 3. Adicionar ao `/etc/fstab` (requer sudo)
```bash
sudo bash -c 'echo "//10.62.62.191/pans_dados /mnt/pans_dados cifs guest,uid=1000,gid=1000,file_mode=0777,dir_mode=0777 0 0" >> /etc/fstab'
```

Depois, para montar na proxima vez:
```bash
sudo mount -a
```

---

## 🐛 Troubleshooting

### Erro: "mount.cifs: command not found"
```bash
sudo apt update
sudo apt install cifs-utils
```

### Erro: "Permission denied"
```bash
# Tentar com sudo
sudo mount -t cifs //10.62.62.191/pans_dados /mnt/pans_dados \
  -o guest,uid=1000,gid=1000,file_mode=0777,dir_mode=0777
```

### Erro: "Connection refused"
```bash
# Verificar se servidor está online
ping 10.62.62.191

# Verificar se porta SMB esta aberta
nc -zv 10.62.62.191 445
```

### Erro: "No route to host"
- Verificar se os dois PCs estão na mesma rede
- Pode ser problema de firewall no servidor
- Tentar com hostname ao invés de IP:
```bash
sudo mount -t cifs //RAN_AvalFauna_FHF9703/pans_dados /mnt/pans_dados \
  -o guest,uid=1000,gid=1000,file_mode=0777,dir_mode=0777
```

---

## ✅ Checklist de Execução

- [ ] Montar compartilhamento SMB em `/mnt/pans_dados`
- [ ] Verificar que `/mnt/pans_dados/01_fontes_web` existe
- [ ] Ativar venv: `source venv/bin/activate`
- [ ] Rodar download: `python scripts/coleta/download_documentos_pans.py --servidor /mnt/pans_dados`
- [ ] Verificar que arquivos estão sendo baixados

---

## 📝 Notas Importantes

1. **Montagem temporária:** Será desmontada quando você reiniciar o WSL ou desligar o PC
2. **Permissões:** `guest` não requer senha, mas o servidor deve permitir acesso anônimo
3. **Performance:** SMB sobre rede pode ser mais lento que local; é normal
4. **Armazenamento:** Os arquivos estão sendo salvos no servidor, não no WSL

---

## 🔗 Relacionados

- Documentação completa: [`SETUP_DOWNLOAD_REMOTO.md`](SETUP_DOWNLOAD_REMOTO.md)
- Script Python modificado: [`scripts/coleta/download_documentos_pans.py`](scripts/coleta/download_documentos_pans.py)
- Setup do compartilhamento: [`setup_compartilhamento_pans.ps1`](setup_compartilhamento_pans.ps1)

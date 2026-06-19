# Setup: Download Remoto de Documentos PANs

Este documento guia o setup para fazer downloads de documentos diretamente do PC de desenvolvimento para o servidor via compartilhamento SMB.

## 🎯 O que vai acontecer

1. **Servidor (PC cabeado)**: Criar um compartilhamento SMB
2. **PC Desenvolvimento (WiFi)**: Fazer download dos documentos PANs diretamente para o servidor
3. Resultado: Documentos armazenados no servidor, sem precisar re-download

---

## 📋 Pré-requisitos

- ✅ Python 3.10+ instalado em ambos os PCs
- ✅ Dependências (`pip install -r requirements.txt`)
- ✅ Os dois PCs em rede (podem ser WiFi ↔ Ethernet, funciona)
- ✅ `coleta_pans.py` já foi executado (metadados coletados)

---

## 🔧 Passo 1: Configurar o Compartilhamento SMB no Servidor

Execute **no PC Servidor** com **privilégios de administrador**:

```powershell
# Abra PowerShell como Administrador
# (Clique com direito → "Executar como administrador")

# Navegue até o repositório
cd C:\Users\julia.santos\Documents\dev\chatbot-ran-icmbio

# Execute o script de setup
.\setup_compartilhamento_pans.ps1
```

### O que o script faz:

✅ Cria a pasta `C:\compartilhado\pans_dados`  
✅ Cria subpastas para organizar documentos  
✅ Compartilha via SMB (nome: `pans_dados`)  
✅ Configura permissões NTFS  
✅ Exibe as informações de conexão

### Saída esperada:

```
═══════════════════════════════════════════════════════
   ✅ Compartilhamento criado com sucesso!
═══════════════════════════════════════════════════════

📋 Informações de conexão:
  Nome do compartilhamento: pans_dados
  Pasta local: C:\compartilhado\pans_dados
  Hostname: RAN_AvalFauna_FHF9703
  IP(s) Ethernet: 10.62.62.191

📡 Para acessar do PC de desenvolvimento:
  Option 1 (por IP):
    \\10.62.62.191\pans_dados

  Option 2 (por hostname):
    \\RAN_AvalFauna_FHF9703\pans_dados
```

---

## 🔗 Passo 2: Testar Conectividade (do PC de Desenvolvimento)

Antes de fazer o download, verifique que o PC de desenvolvimento consegue acessar o servidor:

```powershell
# Testar conexão na porta 445 (SMB)
Test-NetConnection -ComputerName 10.62.62.191 -Port 445

# Deve retorgar: TcpTestSucceeded : True
```

Se falhar, verifique:
- Os dois PCs estão na mesma rede?
- O firewall do servidor não está bloqueando SMB (porta 445)?

---

## ⬇️ Passo 3: Download Remoto (do PC de Desenvolvimento)

No **PC de Desenvolvimento**, com o repositório clonado:

```powershell
# Ativar venv
venv\Scripts\Activate.ps1

# Download remoto para o servidor
python scripts/coleta/download_documentos_pans.py --servidor 10.62.62.191

# Ou com hostname
python scripts/coleta/download_documentos_pans.py --servidor RAN_AvalFauna_FHF9703
```

### Opções adicionais:

```powershell
# Apenas testar (sem fazer download)
python scripts/coleta/download_documentos_pans.py --servidor 10.62.62.191 --dry-run

# Apenas PANs de herpetofauna
python scripts/coleta/download_documentos_pans.py --servidor 10.62.62.191 --apenas-herpetofauna

# Um PAN específico
python scripts/coleta/download_documentos_pans.py --servidor 10.62.62.191 --pan pan-herpetofauna-do-nordeste

# Combinar opções
python scripts/coleta/download_documentos_pans.py --servidor 10.62.62.191 --apenas-herpetofauna --dry-run
```

### Saída esperada:

```
Modo de download: REMOTO
Destino: \\10.62.62.191\pans_dados\01_fontes_web\pans

────────────────────────────────────────────────────────
PAN: Herpetofauna do Nordeste  (25 arquivo(s) únicos)
  GET   20260415-pna-herpetofauna-nordeste.pdf
        OK  1250 KB
  GET   20260415-matriz-planejamento.xlsx
        OK  450 KB
  ...
────────────────────────────────────────────────────────
Concluído — 85 baixados | 12 já existiam | 0 falhas
```

---

## 🗂️ Verificar Arquivos Baixados

**No Servidor**, verifique que os documentos chegaram:

```powershell
# Listar pastas de PANs
Get-ChildItem C:\compartilhado\pans_dados\01_fontes_web\pans\

# Verificar documentos de um PAN
Get-ChildItem C:\compartilhado\pans_dados\01_fontes_web\pans\pan-herpetofauna-do-nordeste\documentos\

# Contar total de arquivos baixados
(Get-ChildItem -Path C:\compartilhado\pans_dados\01_fontes_web\pans\ -Recurse -File).Count
```

---

## 🐛 Troubleshooting

### Erro: "Caminho não acessível"

```
Erro: Caminho não acessível: \\10.62.62.191\pans_dados\...
```

**Causas possíveis:**
1. ❌ O servidor ainda não executou `setup_compartilhamento_pans.ps1`
2. ❌ O servidor está offline
3. ❌ Firewall bloqueando SMB (porta 445)
4. ❌ Permissões insuficientes

**Soluções:**
- No servidor, execute o script de setup com privilégios de admin
- Teste a conexão: `Test-NetConnection -ComputerName 10.62.62.191 -Port 445`
- Verifique firewall do servidor

### Erro: "Nenhum metadados.json encontrado"

O repositório não tem os metadados dos PANs. Opções:
1. Execute `python scripts/coleta/coleta_pans.py` no PC de desenvolvimento para coletar metadados primeiro
2. Copie a pasta `01_fontes_web/pans/` do outro PC para cá

### Download muito lento

Normal! O download depende de:
- Banda de internet (para baixar dos servidores do ICMBio)
- Velocidade da rede interna (para escrever no servidor via SMB)
- Quantidade de arquivos (~1100+ PDFs)

**Tempo estimado:** 30-90 minutos para todos os PANs

---

## 📊 Status de Execução

Após cada download, um arquivo `relatorio_download.json` é criado em:
```
\\10.62.62.191\pans_dados\01_fontes_web\pans\relatorio_download.json
```

Contém status detalhado de cada arquivo (ok, falha, skip).

---

## 🔄 Re-executar Downloads

O script é **idempotente** — se executado novamente:
- ✅ Pula arquivos que já existem
- ✅ Re-tenta arquivos que falharam (HTTP 404, timeout, etc)
- ✅ Atualiza o relatório

Useful para retomar download interrompido:

```powershell
python scripts/coleta/download_documentos_pans.py --servidor 10.62.62.191
# (retoma de onde parou)
```

---

## 📝 Próximos Passos

Após ter todos os documentos no servidor:

1. **Extração de texto** → Pipeline PyMuPDF + OCR
2. **Chunking** → Dividir em chunks semanticamente significativos
3. **Embeddings** → Gerar vetores para busca semântica
4. **Qdrant** → Indexar no banco vetorial
5. **RAG** → Implementar o pipeline de recuperação

---

## ❓ Dúvidas?

- Documentação completa: [`docs/processos/coleta_pans_detalhado.md`](docs/processos/coleta_pans_detalhado.md)
- Script Python: [`scripts/coleta/download_documentos_pans.py`](scripts/coleta/download_documentos_pans.py)
- Setup SMB: [`setup_compartilhamento_pans.ps1`](setup_compartilhamento_pans.ps1)

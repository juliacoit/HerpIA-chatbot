# Script para criar compartilhamento SMB no servidor
# Executa com privilégios de administrador

# Verificar se está executando como admin
$isAdmin = [Security.Principal.WindowsIdentity]::GetCurrent().Groups -contains `
    [Security.Principal.SecurityIdentifier]"S-1-5-32-544"

if (-not $isAdmin) {
    Write-Host "⚠️  Este script precisa ser executado como Administrador!" -ForegroundColor Red
    Write-Host "Clique com direito no PowerShell e escolha 'Executar como administrador'" -ForegroundColor Yellow
    exit 1
}

# Configurações
$pastaLocal = "C:\compartilhado\pans_dados"
$nomeCompartilhamento = "pans_dados"
$descricao = "Compartilhamento de dados dos PANs - RAN/ICMBio Chatbot"

Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "   Configurando compartilhamento SMB no servidor" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan

# Passo 1: Criar pasta se não existir
if (-not (Test-Path $pastaLocal)) {
    Write-Host "`n📁 Criando pasta: $pastaLocal" -ForegroundColor Green
    New-Item -ItemType Directory -Path $pastaLocal -Force | Out-Null
} else {
    Write-Host "`n✅ Pasta já existe: $pastaLocal" -ForegroundColor Green
}

# Passo 2: Criar subpastas
$subpastas = @(
    "01_fontes_web\pans",
    "03_documentos_autorizados",
    "07_processados\textos_extraidos",
    "07_processados\chunks",
    "07_processados\metadados"
)

foreach ($subpasta in $subpastas) {
    $caminho = Join-Path $pastaLocal $subpasta
    if (-not (Test-Path $caminho)) {
        Write-Host "  📂 Criando: $subpasta" -ForegroundColor Gray
        New-Item -ItemType Directory -Path $caminho -Force | Out-Null
    }
}

# Passo 3: Verificar se compartilhamento já existe
$compartilhamentoExistente = Get-SmbShare -Name $nomeCompartilhamento -ErrorAction SilentlyContinue

if ($null -ne $compartilhamentoExistente) {
    Write-Host "`n⚠️  Compartilhamento já existe. Removendo..." -ForegroundColor Yellow
    Remove-SmbShare -Name $nomeCompartilhamento -Force | Out-Null
}

# Passo 4: Criar novo compartilhamento
Write-Host "`n🔗 Criando compartilhamento SMB..." -ForegroundColor Green
New-SmbShare -Name $nomeCompartilhamento `
    -Path $pastaLocal `
    -Description $descricao `
    -FullAccess "Everyone" `
    -ChangeAccess "Everyone" | Out-Null

# Passo 5: Configurar permissões NTFS
Write-Host "`n🔐 Configurando permissões NTFS..." -ForegroundColor Green
$acl = Get-Acl $pastaLocal
$regra = New-Object System.Security.AccessControl.FileSystemAccessRule(
    "Everyone",
    "FullControl",
    "ContainerInherit,ObjectInherit",
    "None",
    "Allow"
)
$acl.AddAccessRule($regra)
Set-Acl -Path $pastaLocal -AclObject $acl

# Passo 6: Obter informações de conexão
Write-Host "`n" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "   ✅ Compartilhamento criado com sucesso!" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan

$interfaces = Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -match "Ethernet"}
$ips = @()
foreach ($iface in $interfaces) {
    $ips += $iface.IPAddress
}

$hostname = [System.Net.Dns]::GetHostName()

Write-Host "`n📋 Informações de conexão:" -ForegroundColor Cyan
Write-Host "  Nome do compartilhamento: $nomeCompartilhamento" -ForegroundColor White
Write-Host "  Pasta local: $pastaLocal" -ForegroundColor White
Write-Host "  Hostname: $hostname" -ForegroundColor White

if ($ips.Count -gt 0) {
    Write-Host "  IP(s) Ethernet: $($ips -join ', ')" -ForegroundColor White
}

Write-Host "`n📡 Para acessar do PC de desenvolvimento:" -ForegroundColor Yellow
Write-Host "  Option 1 (por IP):" -ForegroundColor Gray
Write-Host "    \\$($ips[0])\$nomeCompartilhamento" -ForegroundColor Cyan
Write-Host "`n  Option 2 (por hostname):" -ForegroundColor Gray
Write-Host "    \\$hostname\$nomeCompartilhamento" -ForegroundColor Cyan

Write-Host "`n💡 Para mapear como drive no PC de desenvolvimento:" -ForegroundColor Yellow
Write-Host "  PowerShell (como admin):" -ForegroundColor Gray
Write-Host "    net use Z: \\$($ips[0])\$nomeCompartilhamento" -ForegroundColor Cyan

Write-Host "`n✨ Teste de conexão:" -ForegroundColor Yellow
Write-Host "  Do PC de desenvolvimento, execute:" -ForegroundColor Gray
Write-Host "    Test-NetConnection -ComputerName $($ips[0]) -Port 445" -ForegroundColor Cyan

Write-Host "`n"

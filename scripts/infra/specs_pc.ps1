# Coleta especificacoes do PC e informacoes de infraestrutura relevantes para o projeto.
# Salva o relatorio em scripts/infra/output/specs_<data>.txt e tambem exibe no terminal.
# Uso: abra o PowerShell neste diretorio e execute:  .\specs_pc.ps1

$dataHora  = Get-Date -Format "yyyy-MM-dd_HH-mm"
$outDir    = Join-Path $PSScriptRoot "output"
$outFile   = Join-Path $outDir "specs_$dataHora.txt"

if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir | Out-Null }

$linhas = [System.Collections.Generic.List[string]]::new()

function Add ($texto = "") { $linhas.Add($texto) }
function Secao ($titulo) {
    Add ""
    Add "=== $titulo ==="
}

# ---------- SISTEMA OPERACIONAL ----------
Secao "SISTEMA OPERACIONAL"
$os  = Get-CimInstance Win32_OperatingSystem
Add "Nome:          $($os.Caption)"
Add "Versao:        $($os.Version)  (Build $($os.BuildNumber))"
Add "Arquitetura:   $($os.OSArchitecture)"
Add "Instalado em:  $($os.InstallDate.ToString('yyyy-MM-dd'))"
Add "Ultimo boot:   $($os.LastBootUpTime.ToString('yyyy-MM-dd HH:mm'))"

# ---------- CPU ----------
Secao "PROCESSADOR"
$cpu = Get-CimInstance Win32_Processor
Add "Modelo:        $($cpu.Name.Trim())"
Add "Nucleos:       $($cpu.NumberOfCores) fisicos / $($cpu.NumberOfLogicalProcessors) logicos"
Add "Velocidade:    $($cpu.MaxClockSpeed) MHz"
Add "Virtualizacao: $(if ($cpu.VirtualizationFirmwareEnabled) { 'Habilitada (VT-x/AMD-V)' } else { 'Desabilitada' })"

# ---------- RAM ----------
Secao "MEMORIA RAM"
$cs  = Get-CimInstance Win32_ComputerSystem
$ramTotal = [math]::Round($cs.TotalPhysicalMemory / 1GB, 1)
$ramLivre = [math]::Round($os.FreePhysicalMemory / 1MB / 1024, 1)
$ramUso   = [math]::Round($ramTotal - $ramLivre, 1)
Add "Total:         $ramTotal GB"
Add "Em uso:        $ramUso GB"
Add "Disponivel:    $ramLivre GB"
Add "Obs Docker:    $(if ($ramTotal -ge 16) { 'OK para todos os conteineres (>=16 GB)' } elseif ($ramTotal -ge 8) { 'Suficiente para prototipo (>=8 GB), mas limite para modelos maiores' } else { 'Atencao: menos de 8 GB pode ser insuficiente para rodar todos os servicos' })"

# ---------- GPU ----------
Secao "GPU"
$gpus = Get-CimInstance Win32_VideoController |
        Where-Object { $_.Name -notlike '*Virtual*' -and $_.Name -notlike '*Basic*' }
if ($gpus) {
    foreach ($g in $gpus) {
        Add "Modelo:        $($g.Name)"
        $vram = if ($g.AdapterRAM -gt 0) { "$([math]::Round($g.AdapterRAM / 1GB, 1)) GB" } else { "nao informada" }
        Add "VRAM:          $vram"
        Add "Driver:        $($g.DriverVersion)"
    }
} else {
    Add "(nenhuma GPU dedicada detectada)"
}

# ---------- DISCOS ----------
Secao "DISCOS"
$drives = Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Used -ne $null }
Add ("{0,-6} {1,10} {2,10} {3,10}  {4}" -f "Drive","Total_GB","Livre_GB","Uso_%","Root")
Add ("-" * 60)
foreach ($d in $drives) {
    $total  = [math]::Round(($d.Used + $d.Free) / 1GB, 1)
    $livre  = [math]::Round($d.Free / 1GB, 1)
    $pct    = if ($total -gt 0) { [math]::Round(($d.Used / ($d.Used + $d.Free)) * 100, 0) } else { 0 }
    $alerta = if ($livre -lt 10) { "  !! POUCO ESPACO" } else { "" }
    Add ("{0,-6} {1,10} {2,10} {3,10}  {4}{5}" -f $d.Name, $total, $livre, "$pct%", $d.Root, $alerta)
}

# ---------- REDE ----------
Secao "REDE"
$ips = Get-NetIPAddress -AddressFamily IPv4 |
       Where-Object { $_.InterfaceAlias -notlike '*Loopback*' -and $_.IPAddress -notlike '169.*' }
foreach ($i in $ips) {
    Add "Interface: $($i.InterfaceAlias.PadRight(30))  IP: $($i.IPAddress)"
}

# ---------- DOCKER ----------
Secao "DOCKER"
$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
if ($dockerCmd) {
    $dockerVer  = docker version --format "{{.Server.Version}}" 2>$null
    $composeVer = docker compose version --short 2>$null
    Add "Docker Engine:   $dockerVer"
    Add "Docker Compose:  $composeVer"

    $containers = docker ps --format "{{.Names}}\t{{.Status}}\t{{.Ports}}" 2>$null
    if ($containers) {
        Add ""
        Add "Conteineres em execucao:"
        Add ("{0,-35} {1,-25} {2}" -f "Nome", "Status", "Portas")
        Add ("-" * 80)
        foreach ($c in $containers) {
            $cols = $c -split "`t"
            Add ("{0,-35} {1,-25} {2}" -f $cols[0], $cols[1], $cols[2])
        }
    } else {
        Add "Conteineres:     nenhum em execucao"
    }

    $images = docker images --format "{{.Repository}}:{{.Tag}}\t{{.Size}}" 2>$null |
              Where-Object { $_ -notlike '<none>*' }
    if ($images) {
        Add ""
        Add "Imagens locais:"
        foreach ($img in $images) {
            $cols = $img -split "`t"
            Add "  $($cols[0].PadRight(45)) $($cols[1])"
        }
    }
} else {
    Add "Docker:  NAO INSTALADO"
}

# ---------- WSL ----------
Secao "WSL (Windows Subsystem for Linux)"
$wslCmd = Get-Command wsl -ErrorAction SilentlyContinue
if ($wslCmd) {
    $wslVer = wsl --version 2>$null | Select-Object -First 1
    Add "WSL:  $wslVer"
    $distros = wsl --list --quiet 2>$null
    if ($distros) {
        Add "Distribuicoes instaladas:"
        $distros | ForEach-Object { Add "  $_" }
    }
} else {
    Add "WSL:  nao detectado"
}

# ---------- PYTHON ----------
Secao "PYTHON"
$pyCmd = Get-Command python -ErrorAction SilentlyContinue
if ($pyCmd) {
    $pyVer = python --version 2>$null
    Add "Python global:  $pyVer  ($($pyCmd.Source))"
} else {
    Add "Python global:  nao encontrado no PATH"
}

# venv do projeto (dois niveis acima do diretorio do script = raiz do repo)
foreach ($rel in @("..\..\..venv\Scripts\python.exe", "..\.venv\Scripts\python.exe")) {
    $vp = Join-Path $PSScriptRoot $rel
    if (Test-Path $vp) {
        $venvVer = & $vp --version 2>$null
        Add "Python venv:    $venvVer  ($vp)"
        break
    }
}

# ---------- GIT ----------
Secao "GIT"
$gitCmd = Get-Command git -ErrorAction SilentlyContinue
if ($gitCmd) {
    $gitVer = git --version
    Add "Git:  $gitVer  ($($gitCmd.Source))"
} else {
    Add "Git:  nao encontrado no PATH"
}

# ---------- PORTAS RELEVANTES PARA O PROJETO ----------
Secao "PORTAS RELEVANTES PARA O PROJETO"
$portasAlvo = @{
    5432 = "PostgreSQL"
    6333 = "Qdrant (HTTP)"
    6334 = "Qdrant (gRPC)"
    8000 = "FastAPI"
    8501 = "Streamlit"
}
foreach ($porta in $portasAlvo.Keys | Sort-Object) {
    $conn   = Get-NetTCPConnection -LocalPort $porta -ErrorAction SilentlyContinue | Select-Object -First 1
    $status = if ($conn) { "EM USO  (PID $($conn.OwningProcess))" } else { "livre" }
    Add ("Porta {0,-6} {1,-20}  {2}" -f $porta, $portasAlvo[$porta], $status)
}

# ---------- RODAPE ----------
Add ""
Add "Gerado em: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Add "Maquina:   $($env:COMPUTERNAME)  |  Usuario: $($env:USERNAME)"

# ---------- EXIBE E SALVA ----------
$linhas | ForEach-Object { Write-Host $_ }
$linhas | Out-File -FilePath $outFile -Encoding utf8

Write-Host ""
Write-Host "Relatorio salvo em: $outFile" -ForegroundColor Green

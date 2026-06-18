# Coleta especificações do PC: OS, CPU, RAM, disco(s) e IP local.
# Uso: abra o PowerShell neste diretório e execute:  .\specs_pc.ps1

$ram  = (Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB
$os   = (Get-CimInstance Win32_OperatingSystem).Caption
$cpu  = (Get-CimInstance Win32_Processor).Name
$ip   = (Get-NetIPAddress -AddressFamily IPv4 |
         Where-Object { $_.InterfaceAlias -notlike '*Loopback*' -and
                        $_.IPAddress      -notlike '169.*' } |
         Select-Object -First 1).IPAddress

Write-Host "=== ESPECIFICACOES DO PC ===" -ForegroundColor Cyan
Write-Host "OS:  $os"
Write-Host "CPU: $cpu"
Write-Host "RAM: $([math]::Round($ram, 1)) GB"
Write-Host "IP:  $ip"
Write-Host ""
Write-Host "=== DISCOS ===" -ForegroundColor Cyan
Get-PSDrive -PSProvider FileSystem |
    Where-Object { $_.Used -ne $null } |
    Select-Object Name,
        @{N='Total_GB'; E={[math]::Round(($_.Used + $_.Free) / 1GB, 1)}},
        @{N='Livre_GB'; E={[math]::Round($_.Free / 1GB, 1)}} |
    Format-Table -AutoSize

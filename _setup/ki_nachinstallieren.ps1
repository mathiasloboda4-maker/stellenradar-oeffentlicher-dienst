# Stellenradar — die lokale KI nachtraeglich einrichten.
# Fuer den Fall, dass sie bei der Installation uebersprungen wurde.

$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"
$Projekt = Split-Path -Parent $PSScriptRoot

function Gut($t)     { Write-Host "   + $t" -ForegroundColor Green }
function Info($t)    { Write-Host "     $t" -ForegroundColor Gray }
function Warnung($t) { Write-Host "   ! $t" -ForegroundColor Yellow }

Clear-Host
Write-Host ""
Write-Host "  ====================================================================" -ForegroundColor DarkGray
Write-Host "   STELLENRADAR  ·  Lokale KI einrichten" -ForegroundColor Cyan
Write-Host "  ====================================================================" -ForegroundColor DarkGray
Write-Host ""
Write-Host "   Die KI bereitet zu jeder vorgemerkten Stelle eine Kurzinfo auf."
Write-Host "   Sie laeuft auf diesem Rechner, es verlaesst nichts das Geraet."
Write-Host ""

$ramGB = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)
Info "Arbeitsspeicher: $ramGB GB"

# Dieselbe Staffelung wie bei der Erstinstallation.
if ($ramGB -ge 16)     { $modell = "gemma4:12b"; $groesse = "7,6 GB" }
elseif ($ramGB -ge 12) { $modell = "qwen3.5:9b"; $groesse = "6,6 GB" }
elseif ($ramGB -ge 8)  { $modell = "qwen3.5:2b"; $groesse = "2,7 GB" }
else {
    Warnung "Unter 8 GB Arbeitsspeicher lohnt sich keine lokale KI."
    Info "Das Programm laeuft vollstaendig ohne sie — die Favoriten zeigen"
    Info "dann die Eckdaten ohne KI-Aufbereitung."
    Write-Host ""
    Read-Host "   Zum Schliessen Eingabetaste druecken"
    exit 0
}

Info "Passendes Modell: $modell ($groesse)"
if ($ramGB -lt 12) {
    Warnung "Mit $ramGB GB laeuft nur das kleine Modell. Es braucht fuer eine"
    Info "Kurzinfo mehrere Minuten und formuliert einfacher als die grossen."
}
Write-Host ""
Write-Host "   Geladen werden Ollama (rund 1 GB) und das Modell ($groesse)." -ForegroundColor Gray
Write-Host "   Jetzt einrichten?  [J/N] " -ForegroundColor Yellow -NoNewline
$antwort = Read-Host
if ($antwort -notmatch "^[jJyY]") {
    Info "Abgebrochen."
    Read-Host "   Zum Schliessen Eingabetaste druecken"
    exit 0
}

$ollamaExe = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
if (Test-Path $ollamaExe) {
    Gut "Ollama ist schon installiert."
} else {
    Info "Lade Ollama ..."
    $ziel = Join-Path $env:TEMP "OllamaSetup.exe"
    try {
        Invoke-WebRequest -Uri "https://ollama.com/download/OllamaSetup.exe" `
                          -OutFile $ziel -UseBasicParsing -TimeoutSec 1800
    } catch {
        Warnung "Download fehlgeschlagen: $($_.Exception.Message)"
        Info "Alternative: ollama.com im Browser oeffnen und von Hand installieren."
        Read-Host "   Zum Schliessen Eingabetaste druecken"
        exit 1
    }
    Info "Installiere Ollama ..."
    Start-Process -FilePath $ziel -ArgumentList "/VERYSILENT","/NORESTART" -Wait | Out-Null
    Remove-Item $ziel -ErrorAction SilentlyContinue
    if (Test-Path $ollamaExe) { Gut "Ollama installiert." }
    else {
        Warnung "Ollama wurde nicht am erwarteten Ort gefunden."
        Read-Host "   Zum Schliessen Eingabetaste druecken"
        exit 1
    }
}

Info "Starte den Dienst ..."
Start-Process -FilePath $ollamaExe -ArgumentList "serve" -WindowStyle Hidden
Start-Sleep -Seconds 6

Info "Lade das Modell $modell — das dauert 5 bis 30 Minuten ..."
& $ollamaExe pull $modell
if ($LASTEXITCODE -eq 0) {
    Gut "Modell $modell ist da."
    Write-Host ""
    Write-Host "   Fertig. Im Programm unter 'Favoriten' auf 'Mit KI aufbereiten'." -ForegroundColor Green
} else {
    Warnung "Das Modell konnte nicht geladen werden."
    Info "Spaeter nachholbar in einem Eingabeaufforderungsfenster mit:"
    Info "  ollama pull $modell"
}

Write-Host ""
Read-Host "   Zum Schliessen Eingabetaste druecken"

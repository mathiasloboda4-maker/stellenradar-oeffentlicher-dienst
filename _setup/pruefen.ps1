# Stellenradar — Zustand pruefen.
# Sagt in Klartext, was da ist und was fehlt. Aendert nichts.

$ErrorActionPreference = "Continue"
$Projekt = Split-Path -Parent $PSScriptRoot
$VenvPy  = Join-Path $Projekt ".venv\Scripts\python.exe"

function Gut($t)     { Write-Host "   [ok]    $t" -ForegroundColor Green }
function Fehlt($t)   { Write-Host "   [fehlt] $t" -ForegroundColor Red }
function Hinweis($t) { Write-Host "   [hm]    $t" -ForegroundColor Yellow }
function Zeile($t)   { Write-Host "           $t" -ForegroundColor Gray }

Clear-Host
Write-Host ""
Write-Host "  ====================================================================" -ForegroundColor DarkGray
Write-Host "   STELLENRADAR  ·  Zustand" -ForegroundColor Cyan
Write-Host "  ====================================================================" -ForegroundColor DarkGray
Write-Host ""

$ramGB = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)
Zeile "Arbeitsspeicher: $ramGB GB"
Write-Host ""

# --- Umgebung ---
if (Test-Path $VenvPy) {
    Gut "Programmumgebung vorhanden"
    $pakete = & $VenvPy -c "import scrapling, pypdf, tkinter, sqlite3; print(scrapling.__version__)" 2>$null
    if ($pakete) { Gut "Pakete vollstaendig (Scrapling $pakete)" }
    else         { Fehlt "Ein Paket fehlt — INSTALLIEREN.bat noch einmal ausfuehren" }
} else {
    Fehlt "Programmumgebung — bitte INSTALLIEREN.bat ausfuehren"
}

# --- Browser fuers Auslesen ---
$browser = @(Get-ChildItem (Join-Path $env:LOCALAPPDATA "ms-playwright") -Directory -Filter "chromium*" -ErrorAction SilentlyContinue)
if ($browser.Count -ge 2)      { Gut "Browser zum Auslesen: $($browser.Count) Fassungen" }
elseif ($browser.Count -eq 1)  { Hinweis "Nur eine Browser-Fassung — BROWSER_NACHINSTALLIEREN.bat hilft" }
else                           { Fehlt "Browser zum Auslesen — BROWSER_NACHINSTALLIEREN.bat ausfuehren" }

# --- Browser fuer PDF ---
$pdf = @(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
    "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($pdf) { Gut "PDF-Erzeugung ueber $(Split-Path -Leaf $pdf)" }
else      { Fehlt "Chrome oder Edge — ohne einen davon keine Steckbriefe und kein Archiv" }

# --- Lokale KI ---
$ollamaExe = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
if (Test-Path $ollamaExe) {
    Gut "Ollama installiert"
    $laeuft = $false
    try {
        Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 4 | Out-Null
        $laeuft = $true
    } catch { }
    if ($laeuft) { Gut "Ollama-Dienst laeuft" }
    else         { Hinweis "Ollama-Dienst laeuft nicht — das Programm startet ihn selbst" }

    $modelle = & $ollamaExe list 2>$null | Select-Object -Skip 1
    if ($modelle) {
        foreach ($m in $modelle) {
            $name = ($m -split "\s+")[0]
            if ($name) { Gut "Modell: $name" }
        }
    } else {
        Hinweis "Kein Modell geladen — KI_NACHINSTALLIEREN.bat holt eins"
    }
} else {
    Hinweis "Ollama nicht installiert — die Favoriten zeigen dann Eckdaten ohne KI"
}

# --- Daten ---
Write-Host ""
$db = Join-Path $Projekt "stellenradar.db"
if (Test-Path $db) {
    $zahlen = & $VenvPy -c @"
import sys, os
sys.path.insert(0, r'$Projekt')
os.chdir(r'$Projekt')
import datenbank as db
db.einrichten()
k = db.kennzahlen()
print('%d|%d|%d|%d' % (k['gesamt'], k['status'].get('neu',0),
                       k['status'].get('vorgemerkt',0), k['favoriten']))
"@ 2>$null
    if ($zahlen -and $zahlen.Contains("|")) {
        $t = $zahlen.Split("|")
        Gut "Datenbank: $($t[0]) Stellen, davon $($t[1]) neu, $($t[2]) vorgemerkt, $($t[3]) Favoriten"
    } else {
        Gut "Datenbank vorhanden"
    }
} else {
    Zeile "Noch keine Datenbank — sie entsteht beim ersten Suchlauf."
}

foreach ($paar in @(@("archiv","gesicherte Seiten"), @("steckbriefe","Steckbriefe"),
                    @("sicherungen","Sicherungen"))) {
    $ordner = Join-Path $Projekt $paar[0]
    if (Test-Path $ordner) {
        $n = @(Get-ChildItem $ordner -File -ErrorAction SilentlyContinue).Count
        Zeile "$($paar[1]): $n Dateien"
    }
}

# --- Fehlerprotokoll ---
Write-Host ""
$log = Join-Path $Projekt "fehler.log"
if (Test-Path $log) {
    Hinweis "Es gibt ein Fehlerprotokoll (fehler.log). Letzter Eintrag:"
    Get-Content $log -Tail 6 -Encoding UTF8 | ForEach-Object { Zeile $_ }
} else {
    Gut "Kein Fehlerprotokoll — das Programm ist bisher sauber gestartet"
}

Write-Host ""
Read-Host "   Zum Schliessen Eingabetaste druecken"

# -*- coding: utf-8 -*-
# Stellenradar — Einrichtung auf einem neuen Rechner.
# Wird von INSTALLIEREN.bat aufgerufen, nicht direkt gestartet.
#
# Sieben Schritte. Jeder sagt, was er tut und ob es geklappt hat.
# Was nicht zwingend ist (Ollama), darf fehlschlagen — das Programm läuft
# trotzdem, nur ohne die KI-Aufbereitung der Favoriten.

$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"   # beschleunigt Invoke-WebRequest erheblich

$Projekt = Split-Path -Parent $PSScriptRoot
$Setup   = $PSScriptRoot
$Venv    = Join-Path $Projekt ".venv"
$VenvPy  = Join-Path $Venv "Scripts\python.exe"

$script:Warnungen = @()
$script:Fehler    = @()

# ----------------------------------------------------------------------------
# Darstellung
# ----------------------------------------------------------------------------

function Titel($text) {
    Write-Host ""
    Write-Host ("  " + ("=" * 68)) -ForegroundColor DarkGray
    Write-Host "   $text" -ForegroundColor Cyan
    Write-Host ("  " + ("=" * 68)) -ForegroundColor DarkGray
    Write-Host ""
}

function Schritt($nummer, $text) {
    Write-Host ""
    Write-Host "  [$nummer von 7]  $text" -ForegroundColor White -BackgroundColor DarkBlue
    Write-Host ""
}

function Gut($text)     { Write-Host "    + $text" -ForegroundColor Green }
function Info($text)    { Write-Host "      $text" -ForegroundColor Gray }
function Warnung($text) {
    Write-Host "    ! $text" -ForegroundColor Yellow
    $script:Warnungen += $text
}
function Schlecht($text) {
    Write-Host "    X $text" -ForegroundColor Red
    $script:Fehler += $text
}

function Frage($text) {
    Write-Host ""
    Write-Host "    $text  [J/N] " -ForegroundColor Yellow -NoNewline
    $antwort = Read-Host
    return ($antwort -match "^[jJyY]")
}

# ----------------------------------------------------------------------------

Clear-Host
Titel "STELLENRADAR  ·  Einrichtung"
Write-Host "   Dieses Fenster richtet alles ein, was der Stellenradar braucht."
Write-Host "   Es laedt dabei Dateien aus dem Internet — rechne mit 15 bis 40"
Write-Host "   Minuten, je nach Leitung. Du kannst nebenher weiterarbeiten."
Write-Host ""
Write-Host "   Administratorrechte sind NICHT noetig." -ForegroundColor Green
Write-Host ""

# ============================================================================
Schritt 1 "Rechner pruefen"
# ============================================================================

$betriebssystem = (Get-CimInstance Win32_OperatingSystem).Caption
Gut "Windows: $betriebssystem"

if ([Environment]::Is64BitOperatingSystem) {
    Gut "64-Bit-System"
} else {
    Schlecht "Das Programm braucht ein 64-Bit-Windows."
}

$ramGB = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)
Gut "Arbeitsspeicher: $ramGB GB"

$laufwerk = (Get-Item $Projekt).PSDrive.Name
$freiGB = [math]::Round((Get-PSDrive $laufwerk).Free / 1GB)
if ($freiGB -lt 8) {
    Warnung "Nur $freiGB GB frei auf Laufwerk $laufwerk. Fuer alles inklusive KI-Modell werden rund 8 GB gebraucht."
} else {
    Gut "Freier Speicherplatz: $freiGB GB"
}

# Welches KI-Modell passt zu diesem Rechner?
# Die Zahlen stammen aus den Versuchen im Vorgaengerprojekt: Ein Modell braucht
# im Betrieb grob das Doppelte seiner Dateigroesse an Arbeitsspeicher.
if ($ramGB -ge 16) {
    $modell = "gemma4:12b";  $modellGB = 8;   $modellText = "gemma4:12b (beste Textqualitaet, 7,6 GB)"
} elseif ($ramGB -ge 12) {
    $modell = "qwen3.5:9b";  $modellGB = 7;   $modellText = "qwen3.5:9b (gute Qualitaet, 6,6 GB)"
} elseif ($ramGB -ge 8) {
    $modell = "qwen3.5:2b";  $modellGB = 3;   $modellText = "qwen3.5:2b (klein und sparsam, 2,7 GB)"
} else {
    $modell = ""; $modellGB = 0; $modellText = ""
}

if ($modell -eq "") {
    Warnung "Unter 8 GB Arbeitsspeicher lohnt sich keine lokale KI. Das Programm laeuft vollstaendig ohne sie."
} else {
    Info "Passendes KI-Modell fuer diesen Rechner: $modellText"
}

if ($script:Fehler.Count -gt 0) {
    Write-Host ""
    Schlecht "Einrichtung abgebrochen."
    Read-Host "  Zum Schliessen Eingabetaste druecken"
    exit 1
}

# ============================================================================
Schritt 2 "Python"
# ============================================================================

function Finde-Python {
    # py-Launcher, dann python im PATH, dann die Standardinstallation.
    # Der Platzhalter aus dem Microsoft Store faellt durch, weil er einen
    # Fehlercode liefert statt einer Versionsnummer.
    $kandidaten = @()
    $pyPfad = (Get-Command py -ErrorAction SilentlyContinue)
    if ($pyPfad) {
        $gefunden = & py -3 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $gefunden) { $kandidaten += $gefunden }
    }
    $pythonPfad = (Get-Command python -ErrorAction SilentlyContinue)
    if ($pythonPfad) {
        $gefunden = & python -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $gefunden) { $kandidaten += $gefunden }
    }
    foreach ($ordner in (Get-ChildItem "$env:LOCALAPPDATA\Programs\Python" -Directory -ErrorAction SilentlyContinue)) {
        $exe = Join-Path $ordner.FullName "python.exe"
        if (Test-Path $exe) { $kandidaten += $exe }
    }
    foreach ($k in $kandidaten) {
        $version = & $k -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
        if ($LASTEXITCODE -eq 0 -and $version) {
            $teile = $version.Split(".")
            if ([int]$teile[0] -ge 3 -and [int]$teile[1] -ge 10) { return $k }
        }
    }
    return $null
}

$python = Finde-Python
if ($python) {
    $v = & $python --version
    Gut "Python ist vorhanden: $v"
    Info $python
} else {
    Info "Python wird nicht gefunden — installiere die mitgelieferte Fassung."
    $installer = Get-ChildItem $Setup -Filter "python-*-amd64.exe" | Select-Object -First 1
    if (-not $installer) {
        Schlecht "Python ist nicht installiert, und im Ordner _setup liegt kein Installer."
        Info "Zwei Wege:"
        Info "  a) Python von https://www.python.org/downloads/ holen,"
        Info "     beim Installieren 'Add python.exe to PATH' ankreuzen,"
        Info "     danach INSTALLIEREN.bat erneut ausfuehren."
        Info "  b) Oder die Datei python-3.x.x-amd64.exe von python.org"
        Info "     in den Ordner _setup legen und INSTALLIEREN.bat erneut starten."
        Read-Host "  Zum Schliessen Eingabetaste druecken"
        exit 1
    }
    Info "Das dauert ein bis drei Minuten. Bitte warten."
    # Nur fuer den angemeldeten Benutzer -> keine Administratorrechte noetig
    $argumente = @("/quiet", "InstallAllUsers=0", "PrependPath=1",
                   "Include_launcher=1", "Include_test=0", "Include_doc=0")
    $vorgang = Start-Process -FilePath $installer.FullName -ArgumentList $argumente -Wait -PassThru
    if ($vorgang.ExitCode -ne 0) {
        Warnung "Der Python-Installer meldete Code $($vorgang.ExitCode)."
    }
    $python = Finde-Python
    if (-not $python) {
        Schlecht "Python wurde installiert, ist aber noch nicht auffindbar."
        Info "Bitte diesen Rechner einmal neu starten und INSTALLIEREN.bat erneut ausfuehren."
        Read-Host "  Zum Schliessen Eingabetaste druecken"
        exit 1
    }
    Gut "Python installiert: $(& $python --version)"
}

# ============================================================================
Schritt 3 "Programmumgebung und Zusatzpakete"
# ============================================================================

if (Test-Path $VenvPy) {
    Gut "Die Umgebung ist schon da."
} else {
    Info "Lege die Umgebung an ..."
    & $python -m venv $Venv
    if (-not (Test-Path $VenvPy)) {
        Schlecht "Die Umgebung konnte nicht angelegt werden."
        Read-Host "  Zum Schliessen Eingabetaste druecken"
        exit 1
    }
    Gut "Umgebung angelegt."
}

Info "Lade die Zusatzpakete (Scrapling, pypdf, pymupdf) — das dauert einige Minuten ..."
& $VenvPy -m pip install --quiet --disable-pip-version-check --upgrade pip
& $VenvPy -m pip install --disable-pip-version-check -r (Join-Path $Projekt "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    Schlecht "Die Pakete konnten nicht geladen werden. Internetverbindung pruefen."
    Read-Host "  Zum Schliessen Eingabetaste druecken"
    exit 1
}
$pruefung = & $VenvPy -c "import scrapling, pypdf, fitz, tkinter, sqlite3; print('ok')" 2>$null
if ($pruefung -eq "ok") {
    Gut "Alle Pakete sind da."
} else {
    Schlecht "Ein Paket fehlt noch. Meldung: $pruefung"
}

# ============================================================================
Schritt 4 "Browser fuer das Auslesen der Portale"
# ============================================================================

# Scrapling braucht ZWEI Chromium-Fassungen: Playwright fuer den normalen
# Abruf und Patchright fuer die Seiten, die ihren Inhalt erst nachladen.
# `scrapling install` holt nur die erste — die zweite muss separat kommen.
Info "Lade die Browser (rund 400 MB). Das ist der laengste Schritt ..."

$scraplingExe = Join-Path $Venv "Scripts\scrapling.exe"
if (Test-Path $scraplingExe) {
    & $scraplingExe install
} else {
    & $VenvPy -m scrapling install
}

Info "Lade zusaetzlich den Browser fuer die JavaScript-Portale ..."
& $VenvPy -m patchright install chromium

$browserOrdner = Join-Path $env:LOCALAPPDATA "ms-playwright"
$gefundene = @(Get-ChildItem $browserOrdner -Directory -Filter "chromium*" -ErrorAction SilentlyContinue)
if ($gefundene.Count -ge 2) {
    Gut "Browser sind da ($($gefundene.Count) Fassungen)."
} elseif ($gefundene.Count -eq 1) {
    Warnung "Nur eine Browser-Fassung gefunden. Einzelne Portale lassen sich moeglicherweise nicht auslesen."
} else {
    Warnung "Es wurde kein Browser installiert. Portale mit JavaScript bleiben leer."
    Info "Das laesst sich spaeter mit BROWSER_NACHINSTALLIEREN.bat nachholen."
}

# ============================================================================
Schritt 5 "Browser fuer die PDF-Erzeugung"
# ============================================================================

# Fuer Steckbriefe und das Archiv wird Chrome oder Edge gebraucht.
# Edge liegt auf jedem Windows 10 und 11 — deshalb ist das fast immer erfuellt.
$pdfBrowser = @(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
    "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($pdfBrowser) {
    Gut "Gefunden: $(Split-Path -Leaf $pdfBrowser)"
    Info $pdfBrowser
} else {
    Warnung "Weder Chrome noch Edge gefunden. Steckbriefe und Seitenkopien koennen nicht erzeugt werden."
    Info "Abhilfe: Microsoft Edge oder Google Chrome installieren."
}

# ============================================================================
Schritt 6 "Lokale KI (freiwillig)"
# ============================================================================

if ($modell -eq "") {
    Info "Dieser Rechner hat zu wenig Arbeitsspeicher fuer eine lokale KI."
    Info "Das Programm laeuft vollstaendig — die Favoriten zeigen dann die"
    Info "Eckdaten ohne KI-Aufbereitung."
} else {
    Write-Host "    Die lokale KI bereitet zu jeder vorgemerkten Stelle eine Kurzinfo auf:"
    Write-Host "    was die Stelle verlangt, wo die eigenen Kompetenzen passen, was man"
    Write-Host "    im Gespraech fragen kann. Sie laeuft auf diesem Rechner, es verlaesst"
    Write-Host "    nichts das Geraet."
    Write-Host ""
    Write-Host "    Dafuer werden geladen:  Ollama (rund 1 GB) + Modell $modell ($modellGB GB)" -ForegroundColor Gray
    if ($ramGB -lt 12) {
        Write-Host ""
        Write-Host "    Hinweis: Mit $ramGB GB Arbeitsspeicher laeuft nur das kleine Modell." -ForegroundColor Yellow
        Write-Host "    Es braucht fuer eine Kurzinfo mehrere Minuten und formuliert" -ForegroundColor Yellow
        Write-Host "    einfacher als die grossen. Das Programm funktioniert auch ohne." -ForegroundColor Yellow
    }

    if (Frage "Lokale KI jetzt einrichten?") {
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
                Warnung "Ollama konnte nicht geladen werden: $($_.Exception.Message)"
            }
            if (Test-Path $ziel) {
                Info "Installiere Ollama (ohne Administratorrechte, nur fuer dich) ..."
                $vorgang = Start-Process -FilePath $ziel -ArgumentList "/VERYSILENT","/NORESTART" -Wait -PassThru
                Remove-Item $ziel -ErrorAction SilentlyContinue
                if (Test-Path $ollamaExe) {
                    Gut "Ollama installiert."
                } else {
                    Warnung "Ollama wurde nicht am erwarteten Ort gefunden."
                }
            }
        }

        if (Test-Path $ollamaExe) {
            Info "Starte den Ollama-Dienst ..."
            Start-Process -FilePath $ollamaExe -ArgumentList "serve" -WindowStyle Hidden
            Start-Sleep -Seconds 6

            Info "Lade das Modell $modell. Das dauert je nach Leitung 5 bis 30 Minuten ..."
            & $ollamaExe pull $modell
            if ($LASTEXITCODE -eq 0) {
                Gut "Modell $modell ist da."
            } else {
                Warnung "Das Modell konnte nicht geladen werden. Spaeter nachholbar mit: ollama pull $modell"
            }
        }
    } else {
        Info "Uebersprungen. Laesst sich jederzeit mit KI_NACHINSTALLIEREN.bat nachholen."
    }
}

# ============================================================================
Schritt 7 "Pruefen und Verknuepfung anlegen"
# ============================================================================

Info "Fuehre den Selbsttest aus ..."
& $VenvPy (Join-Path $Projekt "stellenradar.py") --selftest | Out-Null
if ($LASTEXITCODE -eq 0) {
    Gut "Selbsttest bestanden."
} else {
    Warnung "Der Selbsttest meldet Fehler. Das Programm startet trotzdem."
}

Info "Fuehre den Oberflaechentest aus ..."
& $VenvPy (Join-Path $Projekt "stellenradar.py") --guitest | Out-Null
if ($LASTEXITCODE -eq 0) {
    Gut "Oberflaeche baut sich sauber auf."
} else {
    Warnung "Der Oberflaechentest meldet Fehler."
}

$verknuepfung = Join-Path $Projekt "verknuepfung.ps1"
if (Test-Path $verknuepfung) {
    & $verknuepfung | Out-Null
    $lnk = Join-Path ([Environment]::GetFolderPath("Desktop")) "Stellenradar.lnk"
    if (Test-Path $lnk) {
        Gut "Startsymbol liegt auf dem Desktop."
    } else {
        Warnung "Das Startsymbol konnte nicht angelegt werden."
    }
}

# ============================================================================
# Abschluss
# ============================================================================

Titel "FERTIG"

if ($script:Warnungen.Count -eq 0) {
    Write-Host "   Alles eingerichtet." -ForegroundColor Green
} else {
    Write-Host "   Eingerichtet, mit $($script:Warnungen.Count) Hinweis(en):" -ForegroundColor Yellow
    foreach ($w in $script:Warnungen) { Write-Host "     ! $w" -ForegroundColor Yellow }
}

Write-Host ""
Write-Host "   So geht es weiter:" -ForegroundColor Cyan
Write-Host "     1. Doppelklick auf das Symbol  Stellenradar  auf dem Desktop"
Write-Host "     2. Oben rechts auf  'Suchlauf starten'"
Write-Host "     3. Beim ERSTEN Lauf im Zahnrad die Interamt-Runden auf 85 stellen"
Write-Host "        — dann wird der gesamte Bestand gelesen statt nur der neueste Teil."
Write-Host ""
Write-Host "   Der erste Suchlauf dauert eine knappe Stunde, weil zu jeder"
Write-Host "   gefundenen Stelle die Seite als PDF gesichert wird."
Write-Host ""
Write-Host "   Eine Anleitung steht in LIESMICH.txt und ausfuehrlich in README.md."
Write-Host ""
Read-Host "   Zum Schliessen Eingabetaste druecken"

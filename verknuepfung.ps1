# Legt die Desktop-Verknuepfung fuer den Stellenradar an.
$ordner = Split-Path -Parent $MyInvocation.MyCommand.Path
$ziel   = Join-Path $ordner "Stellenradar_starten.bat"
$symbol = Join-Path $ordner "stellenradar.ico"
$desktop = [Environment]::GetFolderPath("Desktop")
$link   = Join-Path $desktop "Stellenradar.lnk"

$shell = New-Object -ComObject WScript.Shell
$vk = $shell.CreateShortcut($link)
$vk.TargetPath       = $ziel
$vk.WorkingDirectory = $ordner
$vk.Description      = "Stellenradar - Stellensuche Berlin und Potsdam"
$vk.WindowStyle      = 7          # minimiert: das Konsolenfenster bleibt unsichtbar
if (Test-Path $symbol) { $vk.IconLocation = $symbol }
$vk.Save()

Write-Host ""
Write-Host "  Verknuepfung angelegt: $link"
Write-Host ""

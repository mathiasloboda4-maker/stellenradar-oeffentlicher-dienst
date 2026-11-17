@echo off
chcp 65001 >nul
title Stellenradar einrichten
cd /d "%~dp0"

rem Einziger Knopf fuer die Einrichtung. Die eigentliche Arbeit macht
rem _setup\installieren.ps1 — PowerShell kann herunterladen und pruefen,
rem was eine Batchdatei nicht kann.

if not exist "_setup\installieren.ps1" (
  echo.
  echo   Der Ordner _setup fehlt. Bitte den ganzen Ordner kopieren,
  echo   nicht nur einzelne Dateien.
  echo.
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0_setup\installieren.ps1"
exit /b 0

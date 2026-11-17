@echo off
chcp 65001 >nul
title Stellenradar
cd /d "%~dp0"

set "PYW=%~dp0.venv\Scripts\pythonw.exe"
set "PY=%~dp0.venv\Scripts\python.exe"

if not exist "%PY%" (
  echo.
  echo   Die Umgebung fehlt. Bitte einmal "Einrichten.bat" ausfuehren.
  echo.
  pause
  exit /b 1
)

rem Ohne Konsolenfenster starten, damit nur das Programmfenster sichtbar bleibt.
if exist "%PYW%" (
  start "" "%PYW%" stellenradar.py
) else (
  start "" "%PY%" stellenradar.py
)
exit /b 0

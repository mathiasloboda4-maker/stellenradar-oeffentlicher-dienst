@echo off
chcp 65001 >nul
title Stellenradar pruefen
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0_setup\pruefen.ps1"
exit /b 0

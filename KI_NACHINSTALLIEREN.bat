@echo off
chcp 65001 >nul
title Lokale KI nachinstallieren
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0_setup\ki_nachinstallieren.ps1"
exit /b 0

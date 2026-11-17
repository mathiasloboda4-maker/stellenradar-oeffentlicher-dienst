@echo off
chcp 65001 >nul
title Verknuepfung anlegen
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0verknuepfung.ps1"
pause

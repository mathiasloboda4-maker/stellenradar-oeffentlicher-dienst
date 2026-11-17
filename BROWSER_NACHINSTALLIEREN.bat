@echo off
chcp 65001 >nul
title Browser nachinstallieren
cd /d "%~dp0"
echo.
echo   Laedt die Browser nach, mit denen der Stellenradar Portale
echo   ausliest, die ihren Inhalt erst per JavaScript aufbauen.
echo   Rund 400 MB.
echo.
if not exist ".venv\Scripts\python.exe" (
  echo   Die Umgebung fehlt. Bitte zuerst INSTALLIEREN.bat ausfuehren.
  echo.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m scrapling install
".venv\Scripts\python.exe" -m patchright install chromium
echo.
echo   Fertig.
echo.
pause
exit /b 0

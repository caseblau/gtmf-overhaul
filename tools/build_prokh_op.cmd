@echo off
setlocal
set HERE=%~dp0
echo Rebuilding only the test operation (07_12_Prokhorovka GER/RUS) from the installed polygon and docs\m11_prokhorovka\layout_12jul.json
powershell -NoProfile -ExecutionPolicy Bypass -File "%HERE%build_prokh.ps1" -OpOnly
pause

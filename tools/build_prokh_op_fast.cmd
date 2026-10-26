@echo off
setlocal
set HERE=%~dp0
echo Rebuilding only the operation packs, reusing the 12 July OOB already in build\prokhorovka\op_GER / op_RUS (fast: ~1 min per side)
powershell -NoProfile -ExecutionPolicy Bypass -File "%HERE%build_prokh.ps1" -OpOnly -ReuseOob
pause

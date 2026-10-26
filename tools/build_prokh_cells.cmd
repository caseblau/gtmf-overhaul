@echo off
setlocal
set HERE=%~dp0
echo Reinstalling only the Prokh terrain cells from build\prokhorovka\cellsrc (the operation packs stay)
powershell -NoProfile -ExecutionPolicy Bypass -File "%HERE%build_prokh.ps1" -CellsOnly
pause

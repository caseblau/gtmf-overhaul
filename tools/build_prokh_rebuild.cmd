@echo off
setlocal
set HERE=%~dp0
echo --- removing the installed Prokh polygon and test operation
powershell -NoProfile -ExecutionPolicy Bypass -File "%HERE%build_prokh.ps1" -Clean
echo --- rebuilding from the generated cells (build\prokhorovka\cellsrc)
powershell -NoProfile -ExecutionPolicy Bypass -File "%HERE%build_prokh.ps1"
pause

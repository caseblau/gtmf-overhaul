@echo off
setlocal
set HERE=%~dp0
echo --- flipping the generated heightmaps north-south
powershell -NoProfile -ExecutionPolicy Bypass -File "%HERE%pha6_flip.ps1" -Dir "%HERE%..\build\prokhorovka\cells"
echo --- removing the installed Prokh polygon and test operation
powershell -NoProfile -ExecutionPolicy Bypass -File "%HERE%build_prokh.ps1" -Clean
echo --- rebuilding
powershell -NoProfile -ExecutionPolicy Bypass -File "%HERE%build_prokh.ps1"
pause

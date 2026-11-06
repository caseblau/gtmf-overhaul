@echo off
setlocal
set "HERE=%~dp0"
echo Copies the M4 / M3A1 textures the M3 Lee previews need into Downloads\m3c\gameref (outside the repo).
powershell -NoProfile -ExecutionPolicy Bypass -File "%HERE%extract_refs.ps1" %*
pause

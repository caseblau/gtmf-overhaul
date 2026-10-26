@echo off
setlocal
set HERE=%~dp0
powershell -NoProfile -ExecutionPolicy Bypass -Command "& '%HERE%build_prokh.ps1' -Clean"
pause

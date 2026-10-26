@echo off
setlocal
set HERE=%~dp0
powershell -NoProfile -ExecutionPolicy Bypass -File "%HERE%build_prokh.ps1"
pause

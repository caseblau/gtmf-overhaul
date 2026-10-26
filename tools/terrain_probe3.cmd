@echo off
setlocal
set HERE=%~dp0
powershell -NoProfile -ExecutionPolicy Bypass -File "%HERE%terrain_probe3.ps1"
pause

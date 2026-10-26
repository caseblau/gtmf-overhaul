@echo off
setlocal
set HERE=%~dp0
powershell -NoProfile -ExecutionPolicy Bypass -File "%HERE%terrain_probe2.ps1"
pause

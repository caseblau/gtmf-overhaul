@echo off
setlocal
set HERE=%~dp0
powershell -NoProfile -ExecutionPolicy Bypass -File "%HERE%terrain_probe.ps1"
pause

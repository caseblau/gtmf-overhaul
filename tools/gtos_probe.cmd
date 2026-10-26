@echo off
setlocal
set HERE=%~dp0
if "%~1"=="" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%HERE%gtos_probe.ps1"
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%HERE%gtos_probe.ps1" -GtosRoot "%~1"
)
pause

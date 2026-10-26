@echo off
setlocal
set HERE=%~dp0
if "%~1"=="" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%HERE%sf_probe2.ps1"
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%HERE%sf_probe2.ps1" -SfRoot "%~1"
)
pause

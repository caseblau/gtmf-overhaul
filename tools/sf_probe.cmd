@echo off
rem M10 probe: Steel Fury assets vs Mius-Front vehicle reference. Pass the Steel Fury folder as the first argument if auto-detect fails.
setlocal
set HERE=%~dp0
if "%~1"=="" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%HERE%sf_probe.ps1"
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%HERE%sf_probe.ps1" -SfRoot "%~1"
)
pause

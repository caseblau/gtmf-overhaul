@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0remove_prokh_addon.ps1"
pause

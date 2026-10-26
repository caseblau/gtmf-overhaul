@echo off
setlocal
set HERE=%~dp0
powershell -NoProfile -ExecutionPolicy Bypass -Command "& '%HERE%terrain_hill_test.ps1' -Restore"
pause

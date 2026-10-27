@echo off
setlocal
set HERE=%~dp0
echo Packaging Prokhorovka into build\release and copying it into the game new_updates folder
powershell -NoProfile -ExecutionPolicy Bypass -File "%HERE%release_prokh.ps1" -Install %*
pause

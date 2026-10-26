@echo off
setlocal
set HERE=%~dp0
echo Packaging the Prokhorovka polygon + operations from the installed add-on folder into build\release\mfo_prokhorovka_VERSION.gt3ext
powershell -NoProfile -ExecutionPolicy Bypass -File "%HERE%release_prokh.ps1" %*
pause

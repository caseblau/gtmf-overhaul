@echo off
setlocal
set HERE=%~dp0
echo 9 x 9 block loading test: all 81 cells from the template layers + heightmaps (no generated terrain), the 10 July operation on top.
echo build\prokhorovka\cellsrc is parked as cellsrc_parked; rename it back before a real cell build.
powershell -NoProfile -ExecutionPolicy Bypass -File "%HERE%build_prokh.ps1" -Placeholders -ReuseOob
pause

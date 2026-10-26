@echo off
setlocal
set HERE=%~dp0
set REPO=%HERE%..
set LOG=%REPO%\build\prokhorovka\gen_prokh_log.txt
if not exist "%REPO%\build\prokhorovka" mkdir "%REPO%\build\prokhorovka"
set PY=
py -3 -c "print(1)" >nul 2>nul && set PY=py -3
if not defined PY python -c "print(1)" >nul 2>nul && set PY=python
if not defined PY goto :nopython
echo using: %PY%
%PY% --version
%PY% -c "import numpy, PIL, scipy" >nul 2>nul
if errorlevel 1 %PY% -m pip install numpy pillow scipy
if not exist "%REPO%\docs\m12_terrain\osm\prokh.osm.json" goto :noosm
if not exist "%REPO%\build\prokhorovka\template\!flatlist" goto :notemplate
rem --- reference cells for the ground textures (texture by example, tools\texref.py): three village cells and two
rem     river / wood cells of the Petropolye terrain (Stalingrad-Donets DLC), unpacked once into build\prokhorovka\ref
if not defined GTMF_ROOT set "GTMF_ROOT=C:\Program Files (x86)\Steam\steamapps\common\Graviteam Tactics Mius-Front"
set "PETRO=%GTMF_ROOT%\data\addons\stal_donets\shared\polygons\9p_petropolye"
if not exist "%PETRO%\pgd5_petropolye.polypack2" goto :nopetro
for %%C in (pgd5 pge4 pgf6 pgf2 pgg1) do (
  if not exist "%REPO%\build\prokhorovka\ref\%%C\mat_map.cell.loc_def.bin" (
    echo --- unpacking reference cell %%C
    powershell -NoProfile -ExecutionPolicy Bypass -File "%HERE%gt3.ps1" unpack "%PETRO%\%%C_petropolye.polypack2" "%REPO%\build\prokhorovka\ref\%%C"
  )
)
echo --- generating all cell layers (about 1-2 min per cell, 35 cells) -- log: %LOG%
%PY% "%HERE%prokh_gen.py" --osm "%REPO%\docs\m12_terrain\osm\prokh.osm.json" --cells "%REPO%\build\prokhorovka\cells" --template "%REPO%\build\prokhorovka\template" --out "%REPO%\build\prokhorovka\cellsrc" --ref "%REPO%\build\prokhorovka\ref" %*
echo EXIT CODE %errorlevel%
pause
exit /b 0
:nopython
echo Python 3 was not found (a "python" that only opens the Microsoft Store does not count). Install it from https://www.python.org/downloads/ - tick "Add python.exe to PATH" - then run this again.
pause
exit /b 1
:noosm
echo docs\m12_terrain\osm\prokh.osm.json is missing - run tools\fetch_osm.cmd first.
pause
exit /b 1
:notemplate
echo build\prokhorovka\template is missing - run tools\build_prokh.cmd once first (it unpacks the Mius template cell).
pause
exit /b 1
:nopetro
echo The Petropolye terrain of the Stalingrad-Donets DLC was not found at %PETRO% - the ground textures are copied from its cells. Set GTMF_ROOT if the game is installed elsewhere.
pause
exit /b 1

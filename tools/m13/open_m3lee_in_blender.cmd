@echo off
setlocal
set "BL=C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe"
if not exist "%BL%" goto :nobl
set "S=%~dp0..\..\Claude outputs\m3lee_blender"
if not exist "%S%\m3lee.obj" goto :noobj
echo Building the M3 Lee scene (m3lee.blend) and four preview renders in "%S%"...
"%BL%" --background --python "%~dp0blender_open.py" -- "%S%\m3lee.obj" "%S%\m3lee.blend" "%S%\renders"
start "" "%BL%" "%S%\m3lee.blend"
exit /b 0
:nobl
echo Blender was not found at "%BL%" - edit the BL line of this file (or just open Blender and File ^> Import ^> Wavefront .obj the m3lee.obj in "Claude outputs\m3lee_blender").
pause
exit /b 1
:noobj
echo m3lee.obj is missing from "%S%" (it is a local export, not in git) - ask Claude to export it again.
pause
exit /b 1

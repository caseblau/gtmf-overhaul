@echo off
setlocal
set "BL=C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe"
if not exist "%BL%" goto :nobl
set "S=%~dp0..\..\Claude outputs\su76m_blender"
if not exist "%S%\su76m.obj" goto :noobj
echo Building the SU-76M scene (su76m.blend) and four preview renders in "%S%"...
"%BL%" --background --python "%~dp0blender_open.py" -- "%S%\su76m.obj" "%S%\su76m.blend" "%S%\renders"
start "" "%BL%" "%S%\su76m.blend"
exit /b 0
:nobl
echo Blender was not found at "%BL%" - edit the BL line of this file (or just open Blender and File ^> Import ^> Wavefront .obj the su76m.obj in "Claude outputs\su76m_blender").
pause
exit /b 1
:noobj
echo su76m.obj is missing from "%S%" - ask Claude to export it again (tools\m13\su76_obj.py).
pause
exit /b 1

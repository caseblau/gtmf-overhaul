@echo off
setlocal
set "BL=C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe"
if not exist "%BL%" goto :nobl
set "B=%~dp0..\..\build\m13"
echo Building the SU-122 scene and preview renders...
"%BL%" --background --python "%~dp0blender_open.py" -- "%B%\su122_v34.obj" "%B%\su122_v34.blend" "%B%\renders"
start "" "%BL%" "%B%\su122_v34.blend"
exit /b 0
:nobl
echo Blender was not found at "%BL%" - edit the BL line of this file.
pause

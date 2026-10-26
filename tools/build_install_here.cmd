@echo off
rem Double-click launcher: build the overhaul and install it into the game's new_updates\.
rem First run on a machine: unpacks the pristine vanilla tables into <game>\users\modwork\_orig\3598\ (needed by the merge stage).
rem Output is shown live and also written to build_log.txt next to this file.
setlocal
set HERE=%~dp0
if "%GTMF_ROOT%"=="" set "GTMF_ROOT=C:\Program Files (x86)\Steam\steamapps\common\Graviteam Tactics Mius-Front"
set "LOG=%HERE%build_log.txt"
if not exist "%GTMF_ROOT%\starter_x64.exe" goto :noroot
echo GTMF_ROOT=%GTMF_ROOT%
echo GTMF_ROOT=%GTMF_ROOT%> "%LOG%"
set "ORIG=%GTMF_ROOT%\users\modwork\_orig\3598"
call :unpack "%GTMF_ROOT%\data\common\shared\packed_data\tabs.flatdata"       "%ORIG%\tabs"
call :unpack "%GTMF_ROOT%\data\common\shared\packed_data\tabs_oprum.flatdata" "%ORIG%\tabs_oprum"
call :unpack "%GTMF_ROOT%\data\common\loc_eng\packed_data\text_loc.flatdata"  "%ORIG%\text_loc"
echo --- build install
powershell -NoProfile -ExecutionPolicy Bypass -Command "& '%HERE%build.ps1' -Install 2>&1 | Tee-Object -FilePath '%LOG%' -Append"
echo EXIT CODE %errorlevel%
echo.
echo Done. Log: %LOG%
pause
exit /b 0

:noroot
echo GTMF_ROOT not found: "%GTMF_ROOT%"
echo GTMF_ROOT not found: "%GTMF_ROOT%"> "%LOG%"
pause
exit /b 1

:unpack
if exist "%~2\!flatlist" goto :skip
echo --- unpack "%~1" to "%~2"
powershell -NoProfile -ExecutionPolicy Bypass -Command "& '%HERE%gt3.ps1' unpack '%~1' '%~2' 2>&1 | Tee-Object -FilePath '%LOG%' -Append"
goto :eof
:skip
echo vanilla already unpacked: "%~2"
goto :eof

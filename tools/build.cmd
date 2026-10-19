@echo off
rem MF Overhaul build wrapper. Everything happens in build.ps1 / gt3.ps1 (pure PowerShell, no starter.exe).
rem   build.cmd            build only
rem   build.cmd install    build and copy the .gt3ext into %GTMF_ROOT%\new_updates
rem   build.cmd unpack <archive.flatdata> <out dir>     unpack any vanilla archive (for users\modwork)
rem   build.cmd list   <archive.flatdata>
setlocal
set HERE=%~dp0
if /i "%1"=="install" ( powershell -NoProfile -ExecutionPolicy Bypass -File "%HERE%build.ps1" -Install & exit /b %errorlevel% )
if /i "%1"=="unpack"  ( powershell -NoProfile -ExecutionPolicy Bypass -File "%HERE%gt3.ps1" unpack "%~2" "%~3" & exit /b %errorlevel% )
if /i "%1"=="list"    ( powershell -NoProfile -ExecutionPolicy Bypass -File "%HERE%gt3.ps1" list "%~2" & exit /b %errorlevel% )
powershell -NoProfile -ExecutionPolicy Bypass -File "%HERE%build.ps1"
exit /b %errorlevel%

@echo off
setlocal
rem Re-unpacks the game's pristine tables into users\modwork\_orig\3598 - the base every delta in src\ is merged onto by
rem tools\build.ps1.  Run it after every game update (the first time after the 2 Nov 2026 patch, build 3598 assembly 2),
rem otherwise the mod ships the pre-patch vanilla rows (the patch's shell / effect changes would silently vanish).
set HERE=%~dp0
if not defined GTMF_ROOT set "GTMF_ROOT=C:\Program Files (x86)\Steam\steamapps\common\Graviteam Tactics Mius-Front"
set "ORIG=%GTMF_ROOT%\users\modwork\_orig\3598"
for %%A in (tabs tabs_oprum) do (
  echo --- %%A
  powershell -NoProfile -ExecutionPolicy Bypass -File "%HERE%gt3.ps1" unpack "%GTMF_ROOT%\data\common\shared\packed_data\%%A.flatdata" "%ORIG%\%%A"
)
echo --- text_loc
powershell -NoProfile -ExecutionPolicy Bypass -File "%HERE%gt3.ps1" unpack "%GTMF_ROOT%\data\common\loc_eng\packed_data\text_loc.flatdata" "%ORIG%\text_loc"
type "%GTMF_ROOT%\root\engine.txt"
echo done - now rebuild the add-on (tools\build_install_here.cmd).
pause

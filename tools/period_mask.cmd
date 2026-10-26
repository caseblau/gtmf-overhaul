@echo off
setlocal
set HERE=%~dp0
set PY=
py -3 -c "print(1)" >nul 2>nul && set PY=py -3
if not defined PY set PY=python
%PY% "%HERE%period_cover.py" --tiles "%HERE%..\docs\m12_terrain\period\tiles_rkka100k" "%HERE%..\docs\m12_terrain\period\builtup_1941.png"
echo EXIT CODE %errorlevel%
pause

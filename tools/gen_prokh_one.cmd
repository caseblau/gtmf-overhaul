@echo off
rem Regenerates ONE or a few cells only (quick checks): edit the ONLY line, run, then tools\build_prokh_cells.cmd
rem (it repacks only the cells whose generated layers are newer than the installed pack).
setlocal
set HERE=%~dp0
set ONLY=MgF4,MgG2
for %%C in (%ONLY%) do if exist "%HERE%..\build\prokhorovka\cellsrc\%%C" rmdir /s /q "%HERE%..\build\prokhorovka\cellsrc\%%C"
call "%HERE%gen_prokh.cmd" --only %ONLY% %*

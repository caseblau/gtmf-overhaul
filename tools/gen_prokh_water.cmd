@echo off
setlocal
set HERE=%~dp0
set SRC=%HERE%..\build\prokhorovka\cellsrc
echo Regenerating only the cells that carry water surfaces (deletes those cell folders, then gen_prokh fills them in)
for /d %%D in ("%SRC%\M*") do if exist "%%D\water_pal.cell.loc_def.bin" ( echo   %%~nxD & rmdir /s /q "%%D" )
call "%HERE%gen_prokh.cmd" %*

@echo off
setlocal
set HERE=%~dp0
if exist "%HERE%..\build\prokhorovka\cellsrc" rmdir /s /q "%HERE%..\build\prokhorovka\cellsrc"
call "%HERE%gen_prokh.cmd" %*

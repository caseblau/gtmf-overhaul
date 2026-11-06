@echo off
setlocal
set HERE=%~dp0
py -3 "%HERE%stack_test.py" F || (pause & exit /b 1)
call "%HERE%build_prokh_cells.cmd"

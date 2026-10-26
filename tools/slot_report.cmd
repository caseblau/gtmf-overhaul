@echo off
setlocal
set HERE=%~dp0
echo Slot report: platoons referenced by more than one battle group (vanilla 30 July desc and the built 12 July desc, RUS side)
powershell -NoProfile -ExecutionPolicy Bypass -File "%HERE%slot_report.ps1" "%HERE%..\build\prokhorovka\op_RUS\desc.config.loc_def.bin.orig30" "%HERE%..\build\prokhorovka\op_RUS\slot_report_orig30.txt"
powershell -NoProfile -ExecutionPolicy Bypass -File "%HERE%slot_report.ps1" "%HERE%..\build\prokhorovka\op_RUS\desc.config.loc_def.bin" "%HERE%..\build\prokhorovka\op_RUS\slot_report.txt"
pause

@echo off
setlocal
set HERE=%~dp0
if /i "%~1"=="restore" (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "& '%HERE%terrain_hill_test.ps1' -Restore 2>&1 | Tee-Object -FilePath '%HERE%..\build\m12_test\log.txt'"
) else (
  if not exist "%HERE%..\build\m12_test" mkdir "%HERE%..\build\m12_test"
  powershell -NoProfile -ExecutionPolicy Bypass -Command "& '%HERE%terrain_hill_test.ps1' 2>&1 | Tee-Object -FilePath '%HERE%..\build\m12_test\log.txt'"
)
pause

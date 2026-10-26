@echo off
setlocal enabledelayedexpansion
set HERE=%~dp0
set OUT=%HERE%..\docs\m12_terrain\period\tiles_rkka100k
if not exist "%OUT%" mkdir "%OUT%"
del /q "%OUT%\15_*.jpg" 2>nul
del /q "%OUT%\14_*.jpg" 2>nul
for %%F in ("%OUT%\13_*.jpg") do if %%~zF LSS 3000 del /q "%%F"
echo Downloading the 1940 RKKA 1:100 000 sheet tiles (retromap.ru map 14194055, zoom 13, the finest level that exists, 12 m/px) for the Prokhorovka block: 10 x 12 tiles, ~3 MB, under a minute.
set N=0
for /L %%y in (2736,1,2747) do (
  for /L %%x in (4924,1,4933) do (
    if not exist "%OUT%\13_%%y_%%x.jpg" (
      curl.exe -s -e "https://retromap.ru/14194055_51.0366,36.7354" -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36" -H "Accept: image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8" -H "Accept-Language: ru,en;q=0.9" -H "Sec-Fetch-Dest: image" -H "Sec-Fetch-Mode: no-cors" -H "Sec-Fetch-Site: cross-site" -o "%OUT%\13_%%y_%%x.jpg" "https://hutun.ru/tiles/4/14194126/Z13/%%y/%%x.jpg"
      set /a N+=1
    )
  )
  echo   row %%y done
)
echo downloaded !N! tiles into %OUT%
echo --- tiles the server refused (grey 1715-byte placeholders): fetching their zoom-12 parents as a fallback
set M=0
for %%F in ("%OUT%\13_*.jpg") do if %%~zF LSS 3000 (
  for /f "tokens=2,3 delims=_." %%a in ("%%~nxF") do (
    set /a PY=%%a/2
    set /a PX=%%b/2
    if not exist "%OUT%\12_!PY!_!PX!.jpg" (
      curl.exe -s -e "https://retromap.ru/14194055_51.0366,36.7354" -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36" -H "Accept: image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8" -H "Accept-Language: ru,en;q=0.9" -H "Sec-Fetch-Dest: image" -H "Sec-Fetch-Mode: no-cors" -H "Sec-Fetch-Site: cross-site" -o "%OUT%\12_!PY!_!PX!.jpg" "https://hutun.ru/tiles/4/14194126/Z12/!PY!/!PX!.jpg"
      set /a M+=1
    )
    echo   %%~nxF is a placeholder - parent tile 12_!PY!_!PX!.jpg
  )
)
for %%F in ("%OUT%\12_*.jpg") do if %%~zF LSS 3000 echo   !! parent %%~nxF was refused too (grey placeholder, will be ignored)
echo fetched !M! parent tiles; run tools\period_mask.cmd next (it fills the holes from the parents at half resolution)
for %%F in ("%OUT%\13_2741_4931.jpg") do echo sample tile size: %%~zF bytes (should be 10-60 KB; 1715 bytes is the grey placeholder the server sends when it refuses)
pause

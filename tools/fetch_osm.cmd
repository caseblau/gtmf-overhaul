@echo off
setlocal
set HERE=%~dp0
set OUT=%HERE%..\docs\m12_terrain\osm
if not exist "%OUT%" mkdir "%OUT%"
set Q=%OUT%\query.txt
set F=%OUT%\prokh.osm.json
echo Downloading OpenStreetMap data for the Prokhorovka block (lat 50.9046..51.1254, lon 36.4903..36.8120). 1-3 minutes, several MB.
> "%Q%" echo [out:json][timeout:300]^;^(way[highway]^(50.9046,36.4903,51.1254,36.8120^)^;way[railway]^(50.9046,36.4903,51.1254,36.8120^)^;way[waterway]^(50.9046,36.4903,51.1254,36.8120^)^;way[natural]^(50.9046,36.4903,51.1254,36.8120^)^;relation[natural]^(50.9046,36.4903,51.1254,36.8120^)^;way[landuse]^(50.9046,36.4903,51.1254,36.8120^)^;relation[landuse]^(50.9046,36.4903,51.1254,36.8120^)^;way[building]^(50.9046,36.4903,51.1254,36.8120^)^;node[place]^(50.9046,36.4903,51.1254,36.8120^)^;way[place]^(50.9046,36.4903,51.1254,36.8120^)^;way[power=line]^(50.9046,36.4903,51.1254,36.8120^)^;way[man_made]^(50.9046,36.4903,51.1254,36.8120^)^;^)^;out body^;^>^;out skel qt^;
for %%S in (https://overpass.kumi.systems/api/interpreter https://lz4.overpass-api.de/api/interpreter https://overpass-api.de/api/interpreter https://overpass.private.coffee/api/interpreter) do (
  echo --- trying %%S
  curl.exe -sS -L -A "gtmf-overhaul-terrain/1.0 (contact: github caseblau)" -H "Accept: application/json" -o "%F%" --data-urlencode "data@%Q%" %%S
  findstr /B /C:"{" "%F%" >nul 2>nul && goto :ok
  echo    failed, response:
  type "%F%"
  echo.
)
echo All servers failed. Open https://overpass-turbo.eu/ , paste the query from docs\m12_terrain\osm\query.txt, run it, Export - raw data - download as prokh.osm.json into docs\m12_terrain\osm\
pause
exit /b 1
:ok
for %%F in ("%F%") do echo OK: %%~zF bytes in %%F
pause
exit /b 0

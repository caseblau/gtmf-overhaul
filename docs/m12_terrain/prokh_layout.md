# Prokhorovka terrain layout (generated 2026-10-22)

Polygon name: Prokh. 11 x 12 cells of 2048 m (22.5 x 24.6 km), columns D..N, rows 1..12; Mx = border cells, Mg = interior.
Geographic block (WGS84): lat 50.9046 (2 rows added south 2026-10-23; was 50.9414)..51.1254 N, lon 36.4903..36.8120 E; local metric grid centred at lat 51.0334,
x east (111320*cos(lat) m/deg), y south (111320 m/deg) from the NW corner. Cell (col i, row j) covers
x in [i*2048, (i+1)*2048), y in [j*2048, (j+1)*2048) metres. Heights in PHA6 units (65535 = 320 m), 4096 x 4096 samples
per cell at 0.5 m, row 0 = north edge, sample 0 = west edge (orientation to be verified in game).
Source: Copernicus DEM GLO-30 tiles N51_E036 and N50_E036, bilinear resampling. Heights 152..265 m.
Files: build\prokhorovka\cells\<cell>_hei_map.cell.loc_def.bin (110 files, 8 389 680 B each).
Generator: tools\make_cells.py (needs numpy; uses tools\pha6.py and tools\cogdem.py; DEM tiles in docs\m12_terrain\dem\).

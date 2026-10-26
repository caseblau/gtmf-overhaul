# M12 — Mius-Front terrain ("polygon") format: findings (2026-10-22)

## 1. Layout

- An operation names its terrain in `desc` → `campgen.polygon = polygons\6M_Mius\6M_Mius.cfgpack` and uses a cell rectangle
  `camp_area = x0;y0;x1;y1` of it (17 July Stepanovka: `3;1;9;5` = the whole populated block). `turns`/`hours_per_turn`
  (18 × 4 h) are there too.
- Terrains live in `data\<pack>\shared\polygons\<name>\` (30 folders on this install, 35 terrains incl. winter/autumn
  variants, ~36 GB). Each has:
  - `<name>.cfgpack` — AZCF, struct `i_polygen:polygen`, 153 fields: **Graviteam's generator config**, still naming the
    source inputs: `src_hei_map = MAPS\<name>_hei.raw`, `src_rou_map` (roads), `src_grass_map`, `src_flora_map`,
    `src_ext_flora_map`, `src_det_map` (all TGA), `season = tabs\season_ua_summer.cfgpack`, `lat_lon_tz = 47.55;38.48;2`,
    `dist_width 2816 × dist_height 1792` at `cell_size 256` (= 11 × 7 cells), `size 2048`, `max_h 320`, `water_h 23`,
    `hfcc PHA6`, `hei_range_bias 16`, plus the entry names used inside each cell pack.
  - `<name>_cells.cfgpack` — 11 × 7 table of cell pack file names (populated 7 × 5: columns D–J, rows 1–5; `Mg` =
    interior cells, `Mx` = border cells).
  - `local\<name>_text.loc_*.textpack` — AZTX place names.
  - one `<cell>_<name>.polypack2` per cell (AZP3 pack, `GRAVITECH3 pack system v3.0`, read/written by `gt3.ps1`) and one
    `<cell>_<name>_ao.aomap` (`AZLM`, 2048 × 2048 ambient occlusion / lightmap, not in the pack).
- Cell = 2048 m square; the 7 × 5 Mius block is 14.3 × 10.2 km.

## 2. Entries of a cell pack (kind `cell`)

`cell_desc` (AZCF: arc, dist_desc, cell_x/cell_y, seed, cells_max), `hei_map` (8 389 680 B, below), `vars_map`
(1 048 576 B = 1024², 1 B/sample), `mat_map` (4 194 304 B = 2048², materials), `det_map` (ATF1/DXT5 2048² detail),
`land_ambient_col` (ATF1/DXT5 small), `nor_map` (ATF1/DXT1 2048² normals), `water_map` (ATF1/DXT5, border cells with
water), `water_pal` (516 B), `water_levels` (262 144 B = 256² floats?), `flora_quads` (vegetation placement, binary
records), `obj_quads` (objects: `tabs\buildings…`, fences), `trench_pos` (entrenchments, `INF` records), `op_pos`
(`AMB`…), `grass_map` (2048² bytes), `opmap` (AZG2 mesh: the operational-map vector picture), `back` (ATF1/DXT1
background), `opmap_tri` (triangulated op map, texture names `well`, `bushes`), `spr_map_side` (4 B), `pen_tanks` /
`pen_hums` / `pen_cars` / `pen_apcs` (passability per mover class, ~1 MB each), `landchar` (196 608 B), `aiplaces`
(622 804 B, AI positions), `ambients` (4 B), `class_map` (4 096 B = 64²).

## 3. Heightmap: `hei_map`, format `PHA6` (decoded, read + write: `tools\pha6.py`)

Header 0x40 B: `AZHP`, u32 0x00100000, `PHA6`, u32 0, u32 width 4096, u32 height 4096, u32 bits 16, u32 0, u32 header
size 0x40, u32 ×3 zero, then 4 floats `0.125 0.375 0.625 0.875` (fixed palette) and 4 floats `0 0.33 0.66 1.0`
(= palette 0). Then 252 floats = 63 four-level palettes (0x40..0x430). Then 1 048 576 blocks of 8 bytes, one per 4 × 4
samples, row-major (1024 blocks per row):
```
u16 base          height of level 0 (16-bit units, 65535 = max_h 320 m → 4.88 mm)
u16 pr            bits 15..10 palette index (0..62 table, 63 = fixed 0.125..0.875); bits 9..0 range (0..1023 units)
u32 idx           16 × 2-bit indices; byte y = sample row y (0..3), bits 2x..2x+1 = sample x
height(x,y) = base + range * palette[pr>>10][idx]
```
Samples are 0.5 m apart (4096 over 2048 m). Verified: decoded MgG3 = 175–255 m, MxD1 = 93–192 m, hillshade shows the
Mius balka network, no block seams; re-encoding a decoded cell reproduces the heights within the quantiser step (max
0.12 m on a 40 m test hill, mean 3 mm). Graviteam's encoder chooses palette/range slightly differently, so byte-identical
re-encoding is not expected; equal heights are.

**In-game test (user, 2026-10-22): a 40 m, 600 m wide hill written into MgG3's `hei_map` is visible in the game** —
`tools\terrain_hill_test.cmd` (backup → repack → install; `restore` undoes). Normals, AO and passability were left vanilla.

**Full-terrain test (user, 2026-10-22): the 110-cell `Prokh` polygon loads** — `tools\build_prokh.cmd` installs it with the
cloned 30 July operation; the op map shows the 22 × 20 km grid and a battle starts on it. In the battle every cell seam
is a straight gap/cliff of ~20 m with the engine's edge skirt: the cells are individually mirrored. The MgG3 `opmap` tile
(north-up on the op map) is the vertical mirror of the hillshade decoded with "row 0 = north", so **the engine reads
`hei_map` sample row 0 as the SOUTH edge of the cell** (rows run south → north; the cells table rows still run north →
south, row 1 at the top). `tools\pha6_flip.ps1` mirrors encoded cells byte-exactly (tested against numpy); `make_cells.py`
now samples rows south-first. If seams persist after the row flip, the alternative is the column mirror (`-Cols`).

## 4. The other cell entries (decoded 2026-10-22 from MgG3; readers/writers in `tools\cellfmt.py`, `tools\atf1.py`)

All layers share one orientation: array row 0 / y = 0 is the SOUTH edge, x grows east (checked: `nor_map` and `opmap`
match the `hei_map` hillshade; the engine shows them north-up).

- **ATF1 textures** (`nor_map` DXT1 2048², `det_map` DXT5 2048², `back` DXT1 512² no mips, `land_ambient_col` DXT5 256²):
  0x2000-byte header: `ATF1`, fourcc, u32 file size, u32 1; @0x80 u32 mip count, u32 0; @0x88 mip table smallest first
  (u16 w, u16 h, u32 offset from 0x2000). DXT1 chains end at 2×2, DXT5 at 1×1. `nor_map` = tangent-space normal:
  R = −dh/dx, G = −dh/dy (fitted, corr −0.88/−0.94), B = z. `det_map` RGB = blend weights of the ground detail
  textures (per soil: grass → R≈58, bare/road → G,B high), A = noise. `back` = the paper op-map background (woods green,
  fields, village). `land_ambient_col` = coarse ground tint (RGB) + alpha.
- **Raw grids**: `mat_map` 2048² u8: low nibble = soil index into `season.soils` (GRAS0 MARS1 BLAC2 CLAY3 STON4 SAND5
  FIEL6 FIGR7 CONC8 ASPH9 PAVE10 RBAC11 FORG12 LEAV13 TREN14 BUMP15), high nibble = micro tile (values 6–15, noise).
  `grass_map` 2048² u8: low nibble grass type, high nibble (even values 0..14) density. `vars_map` 1024² u8 noise
  (0..~20). `class_map` 64² u8 (32 m): 0 open, 3 wood, 4 bushes, 5 field, 6 ?, 7 settlement/road. `landchar` 64² × 48 B
  records (unknown, copied). Per-soil statistics of all these are in `tools\prokh_style.json`.
- **`flora_quads`**: u32 n; n × (f32 x, f32 rnd 0..1, f32 y, u32 flora row); u32 23 groups (= flora table rows); per
  group u32 nq, nq × (u32 x0,y0,x1,y1, u32 count, count × u32 record index), 16 quads of 512 m in Morton order (some
  split to 256 m by an unknown rule; unsplit quads with >2000 records exist). MgG3: 38 733 plants, mostly bush 7,
  corn 13, sunfl 17 (crops are plants!), bush_big 8.
- **`obj_quads`**: u32 total; stream of `[u32 len][name]`: `tabs\<table>.cfgpack` switches table, otherwise a node of
  that table + f32 x, f32 y, f32 rotation, u32 0, u32 0; empty name repeats the previous node; a u32 0 separates
  consecutive records of one table. MgG3: builds (build0-3, saray0-3), fences (fence2a/4a, gates, kalitka), objects
  (haystacks seno_*, benches, drova), posts (fpost2/3), mil_fences (wire0), flora_sum (valezn, br_tree, pen), structs (well0).
- **`trench_pos`**: u32 n; n × (`INF\0`, f32 x0, y0, width, x1, y1). **`op_pos`**: u32 n; n × (`AMB\0` x, y, r, u32 k,
  k × 8 B slot (3 B?, fourcc MG/INF/GUN)) — AI positions; MxD1 has n = 0, so both may be empty.
- **`opmap_tri`**: u32 n; n × ([len][name] [len][label] u32 ARGB, u32 ARGB2, f32 x, z, y, rot, scale, u32 kind, u32 flag):
  op-map sprites `build` (0xff694320, scale 0.4/0.5), `well`, `bushes` (z 1.0, kind 3), `map_point` with label = spot
  height text (kind 7, colour 0x80101010).
- **`opmap`** (AZG2 line mesh): node `d_map`, geometry `GXT7` @0x430 (u32 2, 0, index offset 0x1000, vertex offset,
  index count, vertex count); indices u16 pairs = line segments; vertex = i16 x, i16 y (0..32767 over the cell) + u32
  ARGB. Colours: contours 0x80767d6d (5 m), 250 m grid 0x30101010 (cell edge 0x80101010), roads 0xff795310 /
  0xff63320d, tracks/railway 0xff1d0a04 (dashed). File padded to 16 KiB; header copied from the template.
- **`pen_*`** (passability per mover class, `tools\pen.py`): array of 40-byte quadtree nodes: u8 flags (0x80 = has
  stored children), u8 flags1 (0x88 mostly), u8 level (1 = 1024 m quadrant … 9 = 4 m), u8 flags3, u16 cx, u16 cy (node
  centre in metres), u16 mask (0 in most leaves, unknown), u8 cost (asphalt ~40–60, grass ~60 rising with slope, marsh
  ~100, forest ~105, trench ~130; cars pay ~120 off-road), u8, u24 parent (ffffff for the 4 roots), u24 neighbours N S W E
  (same level, wrapping round the cell), u24 children NE NW SE SW (leaves: ffffff / junk), 0xff. Levels 1–5 always
  full; deeper nodes split where the ground is not uniform. Generated from the soil map + slope with per-class/soil
  statistics fitted to MgG3/MxD1 (`tools\prokh_pen_model.json`).
- **Water** (MxD1): `water_levels` = 512² u8 index (4 m) into `water_pal` (16 B header `64,4,5,512` + 64 f32 surface
  heights, [0] = descriptor water_h) and `water_map` = ATF1 DXT5 512², RGB (228,238,231) alpha ~21 on water. Generated
  from OSM water polygons / river buffers with the level = local terrain minimum + 0.4 m.
- **Place names**: `map_point` sprites in `opmap_tri` whose label is a text key (`pe_mm_bal_med`, kind 0, colour
  0xC0000000, z 1.0) resolved through `local\<poly>_text.loc_*.textpack` (AZTX, writer `tools\textpack.py`, hash
  verified byte-exact; keys `pe_poly_name`, `pe_poly_country`, `pe_mm_*`). OSM place names → keys + transliteration.
- `aiplaces` (AI positions, 622 804 B, u32 header + records), `.aomap` (`AZLM`, 2048², 5.5 MB) — not decoded, copied.

## 5. Generator (`tools\prokh_gen.py`, run by `tools\gen_prokh.cmd`, packed by `build_prokh.ps1` from `build\prokhorovka\cellsrc`)

Input: the 110 heightmaps + `docs\m12_terrain\osm\prokh.osm.json` (OpenStreetMap, fetched by `tools\fetch_osm.cmd`;
modern land cover as the baseline, to be corrected from the 1943 photos). Per cell it rasterises the cover at 1 m
(fields/woods/orchards/scrub/villages/water/marsh, roads, tracks, railway, buildings), then writes mat/grass/vars/class
maps sampled from the template's per-soil statistics, det/ambient textures, normals from the heights, the op-map paper
background and line mesh (grid, 5 m contours from the smoothed DEM, roads, railway with ticks, tracks dashed, streams),
spot-height and building sprites, vegetation (woods, scrub, orchards, crops in fields, reeds), buildings (OSM footprints
→ build/saray nodes, rotation from the longest wall) and haystacks. Empty trench/op_pos; pen_*/aiplaces/landchar copied.

## 6. Tables the layers index (`samples\tabs\`, exported by `tools\terrain_probe3.ps1`)

`season_ua_summer` (tabs_oprum): `materials` 24 rows (grass, marsh, black, clay, stone, sand, field, field_green, concrete,
asphalt, paved, road_back, forest_grass, leaves, trench, bumps, dry_grass, mud, metal, wood, flesh, tree, water, fake),
`soils` 18 rows (fourcc GRAS/MARS/BLAC/CLAY/STON/SAND/FIEL/FIGR/CONC/ASPH/PAVE/RBAC/FORG/LEAV/TREN/BUMP/DRGR/MUD with
physics and colour), `micros` 15 rows = grass/crop detail tiles with 4×4 atlas UVs (grass_field_01..04, corn_01/02,
potato, grass_bad, reed_01, swamp_01..03, grass_forest_01/02, burdok), `grass` 15 rows, `flora` 23 rows (pine_sm/mid/big,
tree_sm/mid/big, rogoz, bush, bush_big, fir, garden, birch, water_tree, corn, poplar, cultbush, verba_bush, sunfl,
corn_dry, dry_sm/mid/big, cut) each with TREE/BUSH class and a ground soil, `vegetation` 23 rows = model mixes from
`tabs\flora_sum.cfgpack`, `common` (land shader/material names, `def_soil = grass`, `wet_dirt`, trench/hole dig maps).
Also exported: `builds` (170 nodes), `builds_wood` (76), `fences` (14), `mil_fences` (24), `flora_sum` (164 models),
`objects` (46), `structs` (99), `posts` (23), `ai_plans` (6), `materials` (shader library LAND_SUMMER_UA…).

`mat_map` first reading: byte = two 4-bit fields; along a road the low nibble is 11 (road_back) and 15 (bumps) while
grass areas carry 0 → low nibble = soil index into `soils`; high nibble (values 6–15) = detail/micro tile or blend
weight — to be confirmed against `det_map` and `grass_map`.

## 8. Operation body (`desc` of a `.campack2`; decoded 2026-10-23 from 07_30_Stepanovka_GER, generator `tools\prokh_op.py`)

Coordinates: operational squares are 1024 m, x counted from the west edge of `camp_area`, **y from its north edge**; the
cells table rows run north -> south as well. Side fourccs as u32: `USSR` = 1381192533, `GDR` = 5391687.

| node | type / cols | row format |
|---|---|---|
| `mg_nodes` | 2 / 13 `aaavvaaaaaaaa` | `a:x;y;nlinks;edge` square, number of listed links, **edge = 1 on the nodes of the border squares** (rear "back line" nodes, not movement nodes; border squares have 4 nodes, interior ones 2); `a:side;0;0;flags` owner + flags: low bits describe the square (1 hamlet/farm, 2 height, 16 woods/gully, 32 settlement), **bits 11+ = key point value << 11** (Saur-Mogila 8, h. 277.9 9, Marinovka 4, Stepanovka south 4, h. 223 3, h. 214.0 2; the label shown is the nearest `tac_marker`); `a:uid;-1;-1;-1` occupant = the platoon standing on the node (one per node, rebuilt from `plat_pos`; two units on one node crash); `v:dx;0;dy` offset from the square centre, always +-256 (dy>0 = north); `v:0`; 8 x `a:` of 4 link indices into `mg_links`, -1 padded (max 32). Vanilla: ~2.6 nodes/square (364 for 14 x 10). |
| `mg_links` | 2 / 2 `av` | `a:nodeA;nodeB;2[;k]` + `v:cost` = length in km (0.5 / 0.707 / 1.0); every link once |
| `plat_pos` | 2 / 2 `aa` | `a:uid;x;y;node` + `a:flags` ; units off map `-1;-1;-1` (only battle groups and HQs are on the map: 220 of 3764) |
| `tac_markers` | 2 / 4 `vvas` | `v:x;0;y` metres inside the **cell** (x from west, y from north); `v:w;0;h` label box; `a:cell_col;cell_row;level;1` (cells table coordinates, level 0..5); `s:op_tm_*` key of the op text pack (`text.text.loc_eng.bin`, AZTX, `tools\textpack.py` round-trips it byte-exactly). `bnd_*` rows are the sector boundary symbols that `tac_limits` names. |
| `tac_limits` | 2 / 2 `sa` | `bnd_<formation>` + unit code |
| `frames` | 2 / 7 | one row per turn: brief id, weather start/end, flags |
| `ai_orders` | 2 / 2 | order fourcc + `a:uid;1;side` |

`tools\prokh_op.py` (run by `build_prokh.ps1` step 4b after `gt3 csv` exports of `mg_nodes`, `plat_pos`, `tac_markers`)
replaces the three tables through a gt3 delta (`shape~` + `row+`): 2 nodes per interior square (NE/SW quarters) and 4 on
the border squares with edge = 1 (1232 nodes / 5007 links for 22 x 24, cost = km), key points on the node nearest every
OSM settlement (town 8, village 4, hamlet 2) and on the 24 most prominent hilltops of the 64 m block DEM (4 / 2), markers
`op_tm_<place>` / `op_tm_h<m>_<dm>` added to both op text packs, the old deployment scaled into the new area, every placed
unit on its own free interior node on its side of a front polyline (`--front x,y,...`) with the node's occupant set.

## 7. Open

- `gt3.ps1 pack` of an untouched cell is the same size as the original but not byte-identical (`tools\polypack_diff.cmd`
  shows where); the engine loaded the repacked cell anyway.
- Row flip confirmed in game 2026-10-22 (seams gone).
- 2026-10-23: operation body regenerated for the whole area (`tools\prokh_op.py`) - check in game that battles can be started everywhere and that units path across the lattice.
- In-game check of the generated passability (do units path sensibly, roads preferred), water and place names.
- 1943 trimming: `tools\period_cover.py` turns scanned RKKA sheets (M-37-38, M-37-50) into `docs\m12_terrain\period\builtup_1941.png`; the generator then drops modern buildings/village areas outside it.
- pen_* mask field and flags semantics; `landchar`/`aiplaces` still copied from Mius; `.aomap` copied (flat AO).
- Which derived layers the engine recomputes from heights (normals? AO? passability?) — from the hill test's look and
  unit movement.
- Formats still to decode for a new terrain: `mat_map`/`vars_map`/`grass_map`/`class_map` (raw grids, likely indices
  into the season tables), `nor_map`/`det_map` (ATF1 textures, derivable), `pen_*` (passability grids), `flora_quads`,
  `obj_quads`, `trench_pos`, `aiplaces`, `opmap`/`opmap_tri`/`back` (operational map picture), `water_*`, the `.aomap`,
  and the registration of a new polygon (descriptor + cells table + an operation pointing at it).

## 11. Per-cell ambient-occlusion map `<cell>_<poly>_ao.aomap` (format AZLM v3; decoded 2026-10-25, `tools\aomap.py`)

Header 400 B: `AZLM`, u32 3, u16 2048, u16 2048, u16 6148, u16 1, then 24 x float4 **light directions** (x east, y up,
z north; azimuths every 15 deg from north, elevations 64/64/42/23/15/4/4/8/11/15/19/23/28/28/28/23/15/11/8/4/4/23/42/52
deg - a low "sun path" ring plus a few high directions).  Body: RLE stream of one u32 per pixel, row-major, row 0 = south
(mat_map orientation): **bit k set = the ray from the pixel towards direction k is blocked** (terrain, trees, buildings),
0 = open sky.  Records = zero or more run bytes b < 0x80 (each adds b + 1 **zero** pixels, 0x7f = 128 and continue) then one
literal byte 0x80 | (n - 1) and n (1..128) literal words.  mgg3_mius: 69 % of the pixels have no bit set; open ground
averages 0.8 bits (low-elevation bits set by distant rises), the trench pixels 5.3 (10-15 of the low directions at the
floor), woods 10; the vanilla maps were computed on a 2 m grid (pairs of equal columns and rows).  The build copied the
MgG3 map to every cell until 25 Oct, so our trenches were lit from inside and random MgG3 shadows lay on the fields;
`tools\aomap.py` now ray-marches our heights + plant / building heights (1 m steps to 12 m, 2 m to 40 m, 4 m to 64 m) and
`build_prokh.ps1` installs `cellsrc\<cell>\ao.aomap` when present.  Decoder, encoder (round-trip exact) and the 400-byte
header (`docs\m12_terrain\aomap_header.bin`) are in the tools.

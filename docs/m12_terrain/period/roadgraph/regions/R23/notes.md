# R23 (node N7): E centre, x 12288..18432, y 8192..14336 lattice m

Prokhorovka station (S part of the town), Lutovo, Yamki, sovkhoz Stalinskoye otd., Storozhevoye N, Pravorot N, the railway.

## Files
| file | content |
|---|---|
| `frag.json` | 38 lines, 46.1 km, schema of `roads_1941.json` (`highway`, `name`, `source`, `length_m`, `pts` in lattice m) plus **`ends: [start_tag, end_tag]`** per line: `"border"` = the line was cut exactly on the region border there (x = 12288 / 18432 or y = 8192 / 14336), a stub for N11; `null` = a junction, a street end in a village, or a reviewed dead end. All names start with `R23_`. |
| `deadends.json` | 2 reviewed genuine dead ends, each with a crop in `review/` |
| `eval/` | `eval_roads.py` output (`metrics.json`, `report.md`), `make_review.py` output (`tiles/`, `uncovered.json`, `index.md`), **`c2_verdicts.json`** (139 verdicts). `uncovered.json` also carries each verdict. |
| `review/` | dead-end crops, doubt crops, `overlay/` (16 tiles of 1.5 km, traced lines on the sheet; red = secondary, blue = track, green = path, magenta = street, orange = built-up edge, red box = region border), `c2_*` contact sheets of the judged pieces |
| `tools/` | the scripts: `roads_def.py` (waypoints read off the sheet), `build.py` (routing, clipping, border tags), `router.py` (least-cost route on the frozen centre lines plus spike removal), `band.py` / `recentre.py` (the road along the railway, re-centred into the gap of its double line), `selfink.py` (my own on-sheet check, not the gate) |

Rebuild: `python3 tools/build.py frag.json` (run in `tools/`; it reads only the sheet and the frozen N1 files).

## Results (the frozen evaluator, `--region 12288 8192 18432 14336 --allow-border`)
| check | result | target | verdict |
|---|---|---|---|
| C1 on-ink | **71.2 %** of 46.1 km (secondary 71.4, track 52.9, path 57.3, street 87.5) | ≥ 98 % | **FAIL** |
| C2 | 139 road-like uncovered pieces, all judged `not-road` with a reason (`eval/c2_verdicts.json`); 0 `road` | no `road` | pass, pending the reviewer |
| C3 | 0 dangling (46 junction, 18 street end, 5 border, 2 whitelisted) | 0 | pass |
| C4 | 0 illegal; 2 at drawn crossings (X1, X3) | 0 | pass |
| C5 | 0 of 12 villages ≥ 0.3 ha without a street | 0 | pass |

## Why C1 fails (3 passes done, then stopped)
- 13.3 km of the trace counts as off-ink.
- **9.7 km of that lies within 8 m of black line work on the raw sheet** (`tools/selfink.py`: 91.1 % of the trace overall).
- So most of the miss is line work the frozen reference `c1_centre.png` does not hold, not lines across paper. I did not bend lines onto the reference where the sheet draws them elsewhere.

**Main gaps in the reference:**
- **R23_band_rd, the double-line road along the NW side of the railway (4.8 km, 27 % on).** On this sheet the road's two lines run 23–41 px from the railway centre, next to the hatched railway symbol. The reference has no centre line for that road, only scattered pieces of the railway symbol and its edges. I traced the road at the centre of its double line: the light gap at +30 px from the railway (+36 px in the NE part), measured by profiles across the whole stretch.
- **R23_mts_pravorot, the single solid black line from the MTS S to Pravorot (5.6 km, 53 % on).** The line is clearly drawn (RGB about 19/17/5), but `ink_clean.png` keeps only 12 px of it over the 1.1 km S of the MTS, and none through the lettering "Правороть 228". It looks as if the grid filter or the lettering filter removed it. Crop: `review/doubt_mts_track_missing_in_reference.jpg`.
- **Dashed paths (R23_r62, R23_p_sw, R23_p_yamki_w, R23_p_yamki_n, R23_p_se_village).** The dash gaps here are 60–80 m, longer than the reference's bridging (about 40 m), and some dashes are missing from the reference altogether.
- **The park S of the town (R23_park_s) and Pravorot street ends just outside the built-up mask.**

## Crossings (C4)
- **X1:** used by R23_s1, the double-line road S from the booth (Б.) to 245.8 and the sovkhoz.
- **X3:** used by R23_p_yamki_n, the dashed track to Yamki.
- **X2:** not used. The Oktyabrsky double-line road (R23_okt) ends at the road along the railway, on the NW side, at 252.2.
- **X4: not used (doubt).** The Lutovo double-line road (R23_lutovo_yamki) reaches the SE edge of the railway symbol at (15592, 13816), 350 m E of X4. From there it continues E as the town's S street (R23_town_s) on the SE side. I could not read a crossing to the NW side at X4. Crop: `review/doubt_lutovo_road_at_railway.jpg`.
- **X6, X7:** N of the region (R13).

## Unreadable spots (left out)
- **Sovkhoz Stalinskoye otd. (around 12630, 11190).** The double-line road from X1 ends at the sovkhoz. Its continuation W and S is under the red staff pencil band, and no black line can be separated from the pencil. Crop: `review/unreadable_sovkhoz_pencil.jpg`.
- **Prokhorovka town, S part (y 13600–14336).** The scan is about 12 m/px, and the blocks are solid ink and blue wash. I traced only the streets I could follow as light lanes:
  - R23_town_s, the street along the SE side of the railway;
  - R23_town_n1 and R23_town_n2, from the railway S;
  - the MTS lane;
  - R23_park_w, the double line W of the park;
  - R23_town_e1–e4.

  Other lanes in the town are not readable.
- **Park / wood S of the town centre (17200–18100, 13100–13700).** Only the double line through it (R23_park_s) and its W edge road are traced. The strokes inside are wood symbols.
- **Pravorot.** The streets (R23_pv_st1–st6) are straight lanes between the house rows, read off the light gaps. The exact lane edges are not legible at this resolution.

## Doubts in the C2 verdicts (all judged `not-road`)
- **U0025 / U0027.** Black bank lines of the blue-washed strip (stream and ponds) S of the town. U0027 starts at the Lutovo road and runs E for 320 m. It could be read as a track along the valley, but it borders blue wash on both sides, so I judged it a bank line.
- **U0089.** An irregular line S of Yamki, judged an orchard boundary.
- **U0097 (12792, 9024).** A dark-brown curved line N of Storozhevoye, judged a ravine line: it starts with a hooked head in the open field and no road meets it. Its tone is close to the warm-black road ink. Crop: `review/doubt_U0097_ravine.jpg`.
- **U0038.** The thin outline round the blue-washed pond at the SE end of the town.

## Dead ends (deadends.json)
- **R23_park_s2 end (17288, 12732).** The track from 230.5 ends at a small point symbol.
- **R23_p_se_village start (17244, 12464).** The dashed track starts in the field. The 260 m gap to the track end is blank.

## Border stubs for N11 (lattice m)
| line | class | end | point |
|---|---|---|---|
| R23_band_rd | secondary | start | W border (12288, 11917.1) |
| R23_band_rd | secondary | end | N border (16216.5, 14336) |
| R23_okt | secondary | start | W border (12288, 13111.8) |
| R23_w1 | secondary | start | W border (12288, 12303.7) |
| R23_town_n2 | residential | start | N border (16691.4, 14336) |
| R23_park_w | secondary | start | N border (17123.5, 14336) |
| R23_se_road | secondary | start | N border (17944.3, 14336) |
| R23_se_road | secondary | end | block edge (18432, 13877.2) |
| R23_r46 | secondary | end | S border (17476, 8192) |
| R23_p_sw | path | start | S border (12920.6, 8192) |

## Other notes
- Prokhorovka town N of y = 14336 belongs to R13. R23_band_rd leaves the region N at x 16216, before the station.
- I shared the scratchpad with the other region nodes. My working files are in `.../scratchpad/r23/`. Early on, one call overwrote `scratchpad/base_eval/` (another node's baseline eval output). That folder is regenerated by re-running the eval.

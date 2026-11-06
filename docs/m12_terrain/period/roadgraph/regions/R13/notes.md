# R13 (NE) notes: node N4

Region x 12288..18432, y 14336..20480 lattice m (sheet px x 3072..4608, y 1024..2560). The N edge and the E edge are the block edge.

## How the lines were made
- Waypoints read off the sheet. Between the waypoints the line is a least-cost path on the frozen `c1_centre` / `dbl_centre` layer, inside a 10 px (40 m) corridor. Waypoints are first snapped to the centre line within 16 px.
- Segments marked straight (`'s'`) bridge lettering, the river wash and the railway crossings. The crossings at X6 and X7 are exact vertices.
- Vertices are at most 24 m apart.
- Tools are in `tools/`: `trace.py roads_def.py frag.json`. `roads_def.py` holds every waypoint and a note for each line.
- **Schema:** the same as roads_1941.json, plus `"ends": [start, end]`. Each end is one of:
  - `junction`
  - `border` (cut exactly on x = 12288 or y = 14336)
  - `block_edge`
  - `residential_end`
  - `deadend` (listed in deadends.json)
- Names are local to R13, for example `h12`, `t_ns`, `vo_a`.

## Results (final pass)
| check | result |
|---|---|
| C1 | **82.2 %** of 37.5 km (target 98 %: FAIL). Per class: secondary 71.9 %, track 85.4 %, path 60.3 %, residential 86.0 %. |
| C2 | 108 road-like uncovered pieces, all judged `not-road` (`eval/c2_verdicts.json`); 0 left to trace |
| C3 | 0 dangling: 22 junction, 10 residential end, 7 border, 4 reviewed dead ends |
| C4 | 0 illegal; 2 legal crossings (h12 at X6, pk_ew at X7) |
| C5 | 0 of 10 villages without a street |

## Why C1 stays low (checked by eye on the chk crops)
Most of the off-ink length lies more than 20 m from any `c1_centre` pixel. These are gaps in the reference, not traces running beside the ink:
1. **Red and green staff pencil over the roads.** It is not in void, and its hue mask removed the black road ink underneath:
   - h12 at 252.2 and 3740–3800 px;
   - t_kus S of Kusty (the whole hatched stretch);
   - t_olsh at the E edge of Vyshnyaya Olshanka;
   - the dnw / h12 junction;
   - the W end of t_sw, beside the black smudge.
2. **Blue river wash** at the W entrance of Prokhorovka: h12 from 15930 to 16440 m x, bridged straight.
3. **Dash gaps longer than about 40 m** on the dashed track p_n. The closing does not bridge them.
4. **Lettering:** "12.0" on h12 and "Прох..." where t_sw leaves the region; crossed straight along the drawn direction.
5. **h12, the 12.0 road:** the symbol is three lines (one thin line, then a close pair). `c1_centre` sits on the centre of the close pair, and I followed it where it exists. The middle of the full symbol is 12–18 m to the N.

## Doubts and unreadable spots (left out or uncertain)
- **Beregovoye (blob 147).** What I first read as a double-line road is the hatched single house row. The street `ber` is traced along the light lane on its NW side, between the row and the river line. The open S side is the alternative reading. No secondary road is traced through Beregovoye.
- **Vyshnyaya Olshanka (blobs 136/137).** The double-line streets vo_a–vo_e and the start of t_olsh are my best reading of a very dense, blurred block. The NW–SE lane at about px (3440..3550, 1050..1200) was not readable and is not traced.
- **Station L. (px 4470–4530, 1650–1870).** Both t_ns from the N and t_stw from the W end at the station building (dead ends). The light lane S between the station bands (dbl_centre at 4515, 1665–1690) could be a road continuing S on the W side of the railway to Barchevka. Pieces U0052–U0055 and U0065–U0067 lie on it, but they are within 20 m of the railway centre line and read as rail lines. **Not traced: check with the lead.**
- **t_stw W of about 17240 m x** is a faint grey double line; it may be pencil.
- **Prokhorovka (blobs 184/192):**
  - Traced: the main street W of the railway (pk_m), its N continuation to Barchevka (barch), and the E–W street over X7 (pk_ew, along the light lane at y ≈ 14730 m).
  - Not readable: the other lanes between the house blocks, a possible W street parallel to pk_m (dropped), and the street grid S of pk_ew. The C2 town pieces are verdicted as block outlines on this basis.
  - The frozen railway bends W along y ≈ 14780 m between X7 and X6. pk_m stays NW of it.
- **Brick works (kirp., blob 196).** The street kp0 is the lane between its two buildings. kp1, the E–W lane for blobs 197 and 204, is a weak reading.
- **t_east (E of the railway)** enters from the E block edge at y ≈ 16620 m. Its N part, along x ≈ 18350 m, could not be separated from the block edge.
- No road crosses the railway except at X6 (h12) and X7 (pk_ew).

## Files
- `frag.json`: 25 lines.
- `deadends.json`: 4 entries, crops in `review/deadend_*.png`.
- `review/overview_*.png`: traced lines over the sheet, green where on the C1 reference and red where off.
- `eval/`: metrics.json and report.md from eval_roads.py; tiles/, uncovered.json and c2_verdicts.json from make_review.py.

# R33 (node N10): notes

Region: x 12288..18432, y 2048..8192 lattice m (sheet px x 3072..4608, y 4096..5632). Region px below = sheet px − (3072, 4096).

## Status after 3 passes: NOT PASSED (C1)
| check | result | target |
|---|---|---|
| C1 | **75.8 %** of 36.8 km (path 47.8 %, track 78.9 %, secondary 76.7 %, residential 98.7 %) | ≥ 98 % FAIL |
| C2 | 176 road-like uncovered pieces, all given a verdict in `eval/c2_verdicts.json` (0 road, 176 not-road) | verdict list |
| C3 | 0 dangling (13 junction, 3 border, 4 block edge, 24 street ends, 5 reviewed dead ends) | pass |
| C4 | 0 illegal crossings (the railway does not enter R33) | pass |
| C5 | 0 of 8 villages without a street | pass |

Baseline (c72 lines in R33): C1 44.6 %, 10 dangling, 2 villages without a street.

## Schema
`frag.json` uses the roads_1941.json schema plus one field per line: `ends: [start, end]`. The values are `"border"` (cut exactly on x = 12288 or y = 8192), `"block_edge"` (x = 18432 or y = 2048), `"junction:<name>"` (shares the exact vertex with that line), or null (a village street end, or a dead end listed in deadends.json).

## Why C1 stays below 98 % (main off-ink stretches)
- **r59 (dashed path, 230 area), 964 m at region px x 260–500, y 177–203.** The dashes are visible on the sheet. The C1 reference has no line here (450 m to the nearest reference), probably because the lettering and pink-wash filter dropped them. Kept, because the sheet draws it.
- **r85 (dashed, px y≈1200) and d01 (dashed, NW corner).** The dashes are drawn, but the reference only has the longer dashes. The gaps are bridged as the spec requires, and the bridged parts score off-ink.
- **r46 (double-line main road), 1.7 km off.** At the W loop (px 1060–1100, y 560–640) the reference follows the inner edge of the symbol, not its centre. Elsewhere, short stretches where one of the two lines is broken have no reference centre. The trace follows the drawn centre between the two lines.
- **r87 / r78 / r88.** These are partly under the stream wash at px x 560–720 and partly next to the sheet grid line at y≈1372–1394.
- None of this can be fixed without moving lines off the drawn symbol, which the spec forbids. The reference gaps need N1 or lead review.

## Doubts
- **r87 (track, px y≈1360–1380, x 528–1180)** runs next to, and in places on, the straight sheet grid line (grid line at y≈1394 at x 0, falling to y≈1372 at x 1536). It comes from the baseline reading, and it does connect r88, the village at Plota (blob 9) and the triangle junction at 247.7. **Check whether it is a road or the grid line.**
- **Region border.** The secondary r46 leaves the region N at px x≈1302 and S at x≈1160. Track r78 leaves W at y≈1196, s1 leaves S at x≈400 and r80 leaves S at x≈1466. Paths r59 and d01 leave W and N at the NW corner.
- **Streets.** The streets of Pravorot S and Zhimolostnoye (r81, r83, pv2–pv4, b20, b21) were taken from the starting lines and clipped to the 1941 built-up mask. Parts outside the village were dropped. v9a (Plota) and v10a (S of 247.7) are new, drawn along the light lane between the house rows. The house-block pattern in Pravorot S and Belenikhino E is only partly readable.
- **New line s1** (track SW from r78 at px (473, 1401) to the S border): drawn on the sheet, missing from the baseline.

## C2 verdicts: how they were made
I looked at the enhanced review panels by eye and then filed each piece into a category:
- 57 pieces: house-block outlines inside villages
- 8 pieces: the grid line, where the grid filter missed it
- 4 pieces: labels (249.2, 247.7)
- 3 pieces: stream banks under the wash
- 104 pieces: thin curved isolated lines (contours, ravine edges, gully symbols)

**Least certain (re-check):** U0006, U0007 (N edge), U0135, U0136, U0140 (SW, near the 36 label), U0149–U0154, U0158 (S of Zhimolostnoye, by the stream).

## Unreadable / left out
- **Stream and ravine wash at px x 680–1000, y 480–1300** (brown/orange/blue). Lines inside it cannot be told from bank line work. Nothing was traced there except the through roads r61 and r83.
- **The continuation of r78 E of px (640, 1427)** into the wash: not readable. Listed as a dead end.

## Files
- `frag.json`
- `deadends.json` (5 entries, crops in `review/`)
- `eval/` (metrics.json, report.md, review/ tiles + uncovered.json, c2_verdicts.json)
- `tools/` (build.py router + spec_d.py waypoints, region px)

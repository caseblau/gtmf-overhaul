# R32 (node N9): notes, unreadable spots and doubts

Region: x 6144..12288, y 2048..8192 (lattice m). Output: `frag.json` (41 lines, 51.0 km scored), `deadends.json` (12), `review/`, `eval/`.
Check: `python3 /mnt/user-data/outputs/roadgraph/n1/eval_roads.py frag.json eval --region 6144 2048 12288 8192 --allow-border`

## Result (pass 2)

| check | result | target | verdict |
|---|---|---|---|
| C1 | 87.2 % of 51.0 km (secondary 78.8 %, track 90.4 %, residential 90.5 %) | >= 98 % | FAIL |
| C2 | 171 road-like pieces, each judged in `eval/c2_verdicts.json` (also written into `eval/uncovered.json`); 0 `road` | all judged | pass |
| C3 | 0 dangling (junction 47, residential end 11, whitelisted 12, border 7, block edge 4) | 0 | pass |
| C4 | 0 illegal; 2 crossings at X5 | 0 | pass |
| C5 | 0 of 14 villages without a street | 0 | pass |

## Schema
Same as `roads_1941.json`: `{highway, name, source, length_m, pts}`. Added per road: `ends: [start, end]`. The value is `'border'` where the line was clipped exactly on the region border. Otherwise it is `null` (a junction, village end, block edge or reviewed dead end). Lines meeting at a junction share the exact vertex. Lines that cross also get a shared vertex at the crossing.

## Why C1 stays below 98 %
6.6 km is off the `c1_centre` reference. About 3 km of that is in places where the reference has no centre line but the sheet does draw the road:
- **Lettering on the road:** 9.0 on n_r53 (380 m), Беленихино / РС on bel_s and bel_sw (540 m), …ино on se_dbl (350 m), the а of Поляна on bel (250 m). The lines follow the drawn direction straight through.
- **Railway road (bel) at the MTS, y 4630..5140 (480 m):** railway.json runs on the road's double band here. The W line of the band is mostly missing from `c1_centre`. The trace keeps 30–40 m W of railway.json so it does not cross it (C4), so it lies on paper.
- **River crossings:** r76 across the Ivanovka stream (190 m) and the village lanes between built-up blobs (iv_main, iv_w, iv_e, about 300 m).
- The rest is about 110 runs under 100 m (3.5 km). These are gaps in the reference at junctions and line breaks, and places where the router steps between the two edge lines of a double line whose centre is not in `dbl_centre` (w_r70 E part, w_r72, r75).
- I don't see a way to reach 98 % without tracing off the drawn symbol. The lead may want to look at the reference in these spots.

## Doubts (classes and geometry)
- **bel (railway road, secondary):** W of the railway the sheet draws 3–4 thin lines plus the thick hatched band. railway.json sits on the inner thin lines in places (y 4600–5200, 6900–7100). I traced the westernmost line, which is the line `c1_centre` keeps. If the true road centre is the middle of the W pair, it is 15 m further E. Kept as `secondary` as in c72. Its S continuation, bel_s, runs W of the railway to the block edge.
- **Double-line roads:** I set w_r72 and r75 (the S part, y 4575–5080) to `secondary` because they are drawn as double lines. The w_r70 E part (x 7200–8440) and w_r73 also look doubled, but I could not separate them from the ravine lines, so they stay `track`.
- **r75 through the villages:** the double line ends at the Ivanovka N junction (10650, 4575). S of it, the line runs in the lane between two house columns: `iv_main`, residential, down to the r76 / r78 junction. N of y 5080, the line through Ivanovsky Vyselok S is `r75n`, residential, joined to n_b19 at (11600, 6100).
- **X5 road:** x5_e crosses at X5 and ends at the station houses at раз. r76 starts 260 m further E. The link through the houses is not readable, so both ends are listed as dead ends.
- **bel_sw:** the track SW from Belenikhino (U0129/U0130). Its NE end is joined to bel_s through the РС lettering, which is a guess along the drawn direction (180 m).
- **NE corner (Ivanovsky Vyselok, pencil overprint):** n_r56 E of x 10240 and parts of n_e1, n_e2 and ivv_n lie in or next to void. Their ends at the pencil are listed as dead ends. n_r58 merges with the 2 km grid line at (11880, 7290); its continuation S along the grid line is not separable and is left out.

## Left out (not readable or not on the reference)
- **n_e1 W part (x 9030–10800, y about 7790):** a thick line through the wood E of the railway, apex of the ravine symbol. It is not in `c1_centre` and may be the ravine bottom.
- **Street y03 in the SW part of Yasnaya Polyana:** no lane is visible, only orchard and scattered houses. The village has y01 and y02.
- **Second lane in the Ivanovsky Vyselok house blocks (x about 11815, y 6290–6620):** between the hatched rectangles. It is not in the built-up mask and not on the reference.
- **Parallel thin straight lines S of r70 (x 6200–7000, y 4000–4700):** brown-grey and not joined to anything. Judged as slope or contour lines (U0094, U0096).
- **A crossing at the booth Б. N of Teterevino (8650–8900, 7120–7215):** the sheet seems to draw a track over the railway here, but it is not in crossings.json. n_r56 stops on the E side and the W stub is not traced.

## Earlier lines changed or dropped
r57 was dropped: there is no ink along it. s_bel1 was dropped: it ran on the 2 km grid line through Ivanovka. bl03 and bl04 were replaced: bl04 was the double-line road, now `se_dbl`, secondary. b18 and d01, and r59 in the NE corner, were not kept. b18 lies mostly N of the region. For d01 and r59 the review flags no road-like uncovered piece E of x 11900, so I could not confirm them on the sheet; this should be checked again at the merge with the region to the E. The village streets were redrawn in the lanes.

## Tools (in `tools/`)
- `spec.py`: waypoints per road.
- `build.py`: routing, junction snapping and clipping.
- `route.py`: least-cost routing on `c1_centre`, with waypoint snapping and spur removal.
- `deadends_make.py` and `tile.py`: crops.
- To rebuild: `cd tools; python3 build.py spec ../frag.json`. It must be run with `route.py` next to it.

# R31 (node N8): notes, unreadable spots and doubts

Region: x 0..6144, y 2048..8192 lattice m (sheet px x 0..1536, py 4096..5632). West (x = 0) and south (y = 2048) are block edges; north (y = 8192) and east (x = 6144) are region borders.

## Files
- `frag.json`: 39 lines, the same schema as roads_1941.json, plus `ends: [start, end]` on every line. Values:
  - `border`: the end lies exactly on the region border (y = 8192 or x = 6144), for N11 to join. The evaluator skips these points as out-of-region (`x < x1`, `y < y1`), so they are never counted as dangling.
  - `block_edge`, `blank`, `deadend` (see deadends.json), `street_end` (a residential end inside the built-up mask).
  - `junction:<id>`: the end shares the exact vertex with that line, inserted into the other line.
- `deadends.json`: 3 reviewed dead ends, each with a crop in `review/`.
- `eval/`: report.md and metrics.json from eval_roads.py. `eval/c2/` holds the make_review.py output: tiles and uncovered.json with the verdicts filled in. `eval/c2_verdicts.json` lists the verdicts.
- `tools/`: spec.py (the waypoints), trace.py (routes along c1_centre or the village lane between waypoints, resampled every 12 m) and finalize.py (junction vertices, border/edge clipping).

## Final numbers (eval run on the saved frag.json)

| check | result | target | verdict |
|---|---|---|---|
| C1 | 77.6 % of 43.5 km. Per class: path 57 %, residential 84 %, secondary 72 %, track 84 %. | ≥ 98 % | **FAIL** |
| C3 | 0 dangling ends: 42 junction, 16 residential_end, 7 block_edge, 2 blank_edge, 3 whitelisted (plus the border ends, which the evaluator skips as out-of-region) | no dangling ends | pass |
| C4 | 0 illegal crossings; no railway in R31 | 0 | pass |
| C5 | 0 of 11 villages without a street | 0 | pass |
| C2 | 70 road-like uncovered pieces, all with a verdict: 0 `road`, 70 `not-road`. U0011 (the east side of the village loop) and U0034 (the ШК spur) were judged `road` in pass 2 and traced. | every piece judged | pass |

## Why C1 stays at 77.6 % (about 9.7 km of the 43.5 km is off)
The C1 tolerance is 8 m (2 px) from `c1_centre`. Most of the off length is in places where `c1_centre` has no centre line under a symbol that is drawn on the sheet:
1. **Main street of Mal. Mayachki (R31_s_m1), 1.9 km off.** The double-line band runs in the lane between the built-up blobs, and the reference has no centre for it there: house blocks were removed and the dbl_centre is missing. It is traced by eye along the band centre (straight segments). South of the village it runs between the sheet frame line (x ≈ 128 px) and a hatched house row.
2. **Dashed paths (R31_p66, R31_p55), 1.7 km off.** The dash gaps here are longer than the ~40 m the reference bridges, so every gap counts as off.
3. **Lettering crossings:** "9.0" (~320 m), "8.0" (~180 m), "224" / "Мал. Маячки" on p66, and "247.0" on t67. Each line continues along its drawn direction.
4. **Broken double-line centres** on the 9.0 and 8.0 roads, about 1.2 km in 20–80 m pieces. dbl_centre is fragmentary near (830–1050, 4850–4990) px and (330–460, 4330–4450) px.
5. **Lines that ink_clean removed.** These point to real doubts:
   - **R31_t_e2 (932 of 1005 m off).** A curved line from the end of the E road at (950,4399) px NE to t51 at (1152,4264) px. Its tint is dark brown, and the frozen filter dropped it as brown line work. It may be a ravine rim, not a road. I kept it because the E road and the dashed path p55 both meet it there. **Doubt.**
   - **R31_t_w1 (266 m off).** The gap at the frame line (95–127 px) is bridged straight.

I did not move any line onto an edge line of the double-line symbol, or onto other non-centre ink, to raise C1.

## Doubts (decisions taken, listed for the lead)
- **The village network of Mal. Mayachki** is read at the limit of the scan (the sheet is effectively ~12 m/px, upsampled 3x).
  - The through roads are M1, the arc road (R31_s_arc) with its east-side loop (R31_s_loop), and the 8.0 road (R31_s80), which continues from the loop at (400,4378) px.
  - The baseline started the 8.0 road at the central crossroads (288,4354) px. I could not see a band there: it is house blocks (blob 7).
  - The streets (st2–st8, st_w) are placed in the most legible lanes, one or more per built-up blob. Their exact lanes are approximate.
- **The E road from the village (R31_t_e1).** West of x ≈ 690 px there are three near-parallel dark lines. I traced the lower pair as the road. The upper line, which has dots along it and ends in a hook at (700,4290) px, I read as a ravine rim (C2 U0015 = not-road).
  - East of (765,4375) px the road runs between a double line and a row of dots to (950,4399) px.
  - At (765,4378) px a solid line with a row of dots runs S along the W rim of яр Воловский to (830,4600) px. I read it as the ravine rim, so it is not traced. It was not flagged road-like by C2 except as U0039 and U0030 (not-road).
- **The black line E of (950,4400) px** along y ≈ 4405 → (1290,4470) px ends in the ravine-head hachures. I read it as a ravine line (C2 U0032 = not-road).
- **The broken dark line N of the E road**, (480,4140) → (770,4212) px (C2 U0014, with U0007 at the N border). It fades into a grey contour at both ends: not-road. If it is a track, it would run from the N border (493,4096) px to (770,4212) px.
- **The two long straight verticals at x ≈ 12–52 px and x ≈ 123–137 px** are the sheet grid / frame lines (removed by ink_clean). No road is drawn along them. The thick piece at x ≈ 52 px, y 4864–5110 px, is a grid line where it is denser.
- **The S end of M1 (deadend).** No line continues past the ravine structure at (95–125, 4740–4790) px.
- **t65 W end.** The line stops at (28,5272) px with a small hook. A short collinear stroke at (0–14, 5248–5258) px reaches the block edge, so I bridged across. The thin grey line (0,5305)–(60,5300) px is read as a contour.
- **The horizontal line (0–145, 5498) px** stops in open field with no connection. Read as a field boundary or contour, not traced.
- **Ozerovsky.** Only the W edge of the village is outside blank patch B. The two blobs get one street each (st12 along the lane W of the house row, st13). The horizontal line through it at y ≈ 5552 px is the grid line (the baseline oz01 traced it as a track; dropped).
- **Baseline errors not carried over:**
  - c01 ran along the grid line y ≈ 4546 px.
  - r48 and b17 ran through the village rows.
  - The baseline r11 ran along the grid line S of the village.

## Unreadable / left out
- The interior lanes of the Mal. Mayachki house hatching, with blocks at (195–245, 4205–4275) px and (300–440, 4250–4340) px. These outlines are skeleton pieces, but no lane between them is legible as a street.
- The orchard / garden ravines W and N of Ozerovsky, at (640–780, 5200–5632) px and (1100–1450, 5100–5420) px. Only garden boundaries, rims and the grid are drawn there; no road symbol is readable.

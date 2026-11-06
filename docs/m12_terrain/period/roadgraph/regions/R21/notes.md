# R21 (node N5): notes, unreadable spots and doubts

Region x 0..6144, y 8192..14336 lattice m (sheet px x 0..1536, y 2560..4096). 30 lines, 31.9 km.
Check: `python3 /mnt/user-data/outputs/roadgraph/n1/eval_roads.py frag.json eval --region 0 8192 6144 14336 --allow-border`

| check | result | target |
|---|---|---|
| C1 | **79.9 %** (path 22 %, track 86 %, secondary 82 %, residential 94 %) | >= 98 % FAIL |
| C2 | 69 road-like pieces, all judged in `eval/c2_verdicts.json`: 0 road, 69 not-road | pass |
| C3 | 0 dangling (junction 15, border 5, block edge 2, blank 2, village street end 26, reviewed dead end 7) | pass |
| C4 | 0 illegal (there is no railway in R21) | pass |
| C5 | 0 of 15 villages without a street | pass |

## Schema
Same as roads_1941.json (`highway`, `name`, `source`, `length_m`, `pts`), plus `note` and `ends: [start, end]`:
`border` = cut exactly on the R21 border, `deadend` = listed in deadends.json, null = classified by the evaluator.
The W block edge (x = 0) is also the block edge.

## Why C1 stays at 80 % (where the off-reference length is: 6.4 km)
1. **Dashed paths, 2.9 km (9 % of the region).** Most of the dashes of r52, r54 and of the two new paths at the W edge
   (n5_w_path, n5_klkh_path) are not in `c1_centre.png` at all, so points on the drawn dashes are up to 200–500 m from
   the reference. The dashes are clearly drawn (crop `review/doubt_dash_gaps_r52_r54.png`). This is a gap in the frozen
   reference, not a tracing error. Leaving these paths out would raise C1 to about 89 %.
2. **Main road n5_main_s, 1.7 km off.**
   - 0.4 km run through the "Prokhorovka" lettering on the drawn direction (rule 1). The reference has no line there.
   - About 0.7 km through the Gryaznoye valley. Here the road is drawn as a faint pale band between two thin lines,
     which ink_clean does not hold. The trace keeps the earlier (c72) position in that band (crop `review/doubt_gryaznoye_valley.png`).
   - Elsewhere the main road is drawn as one heavy line with a faint thin line W of it. c1 runs on the heavy line and so
     does the trace. The two lines of the symbol are 5–9 px apart, so the true centre is 10–20 m W of the trace. The
     evaluator's double-line detector (dbl_band) misses this stretch. If the centre is wanted, the reference must change first.
3. Through lettering and over the sheet frame: r50 under "...ный" (0.3 km), w_track over the frame line, and short
   gaps in the house-block streets of Kozlovka (kz1) and Gryaznoye (g_lane, gw_street).

## Readings and doubts
- **Bridge X (px 882,2784).** The Krasny Oktyabr street (double line in the lane between the house rows) meets the
  Prokhorovka street at the X-shaped crossing over the stream. The diagonal running SW from X is read as the **stream bank**
  (black line with the blue channel beside it). It is not read as the road. The old c72 r11 ran on it. The main road S
  instead leaves the Prokhorovka street just S of X, curves SW and runs under the "Prokhorovka" lettering to the heavy
  line at px (790,3008). The curved stretch is brownish on the scan and could be a contour; **doubt**
  (`review/doubt_main_road_lettering.png`, `review/doubt_x_bridge.png`).
- **Gryaznoye** (lower sheet). The town is only partly readable: house rows, orchards, a stream valley, and at least
  two thin double lines.
  - Traced: the main road in the c72 position, a street along the E side of the W house row (n5_gw_street, on c1 the
    whole way), a lane across the valley (n5_g_lane), and an axis street in every built-up blob.
  - Whether the main road runs along the W row (n5_gw_street line) rather than in the valley is **not resolved**.
- **Sheet joint at y ~ 10720–10740 m (px 3456–3465).** The upper and lower sheets are offset. Lines crossing the joint
  join straight across. n5_gw_street starts at the joint (whitelisted).
- **Frame line at x ~ 470 m (px 116–118).** This is the sheet frame, not a road and not a grid line. The W track crosses it.
  n5_w_path ends on it.
- **Bogoroditskoe / Kozlovka.** The main street is traced in the lane between the N house row and the S house blocks.
  Kozlovka's street follows the thin line along the S side of the village (n5_kz1). The c72 street bg1 (N of the
  village) was **dropped**: nothing is drawn there. ko1 (in the wood E of Krasny Oktyabr) was dropped and replaced by
  n5_ko_west (the drawn line along the W house row).
- **Left out (cannot read, not traced):**
  - The dark wavy line beside the grid line N of the Psel (px 1488–1516, 2560–2720). It may be a track down to the river.
    Crop: `review/doubt_ne_line_to_psel.png`.
  - The smooth black curve from blank patch A S to the 224.5 track (px 1400,3870 to 1470,4030). ink_clean drops it as
    contour. It looks like a road, but its class and ends cannot be read. Crop: `review/doubt_blank_se_curve.png`.
  - The pair of brown-black lines running ESE from Gryaznoye N (px 560–750, 3468–3548). They are read as a ravine.
- **Dotted lines** (round dots) are read as vegetation and garden boundaries, not roads.

## Files
- `frag.json`, `deadends.json` (7 reviewed dead ends, each with a crop in `review/`)
- `eval/` (evaluator report and metrics), `eval/c2/` (make_review sheets; verdicts also written into uncovered.json),
  `eval/c2_verdicts.json`
- `tools/` (the guided router and spec used: `python3 build.py frag.json` from that folder rebuilds the lines. Run it
  with the scratch copies of the frozen masks; it reads n1/ read-only)

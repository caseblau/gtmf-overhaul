# R11 (N2): notes, unreadable spots and doubts

Region: x 0..6144, y 14336..20480 lattice m (sheet px x 0..1536, y 1024..2560). The W and N sides are the block edge. The E (x = 6144) and S (y = 14336) sides are the region border.

## Files
- `frag.json`: 27 lines, 32.0 km. The schema is the same as roads_1941.json, plus one field, `ends = [start, end]`. Its values are `junction` (shares the exact vertex with another line), `border` (exactly on x = 6144 or y = 14336), `block_edge`, `street_end` (residential end inside the built-up mask) and `dead_end` (listed in deadends.json). Border stubs: klu_e (E border), ko_rd and ko_st (S border).
- `deadends.json`: 1 entry, the ily_path start, with crop `review/deadend_ily_path_start.png`.
- `eval/`: eval_roads.py and make_review.py output. `eval/c2_verdicts.json` holds the verdicts for all 150 road-like pieces; they are also written into `eval/uncovered.json`.
- `review/`: overview plus crops of the doubtful spots.

## Method
- Waypoints were read off the sheet by eye. Between waypoints, each line follows a least-cost path over the frozen `c1_centre` layer inside a corridor of 5 to 10 px.
- Village streets run along the light lanes. Junctions were snapped to shared vertices, then the lines were clipped to the region.
- `ko_rd` is placed at the lane centre from perpendicular ink profiles.

## Check results (eval_roads.py, --allow-border)
| check | result | target |
|---|---|---|
| C1 | **78.0 %** of 32.0 km (path 52.5 %, track 82.2 %, residential 83.9 %, secondary 82.7 %) | ≥ 98 %: **FAIL** |
| C2 | 150 road-like pieces, all judged `not-road` (see below) | no `road`: pass |
| C3 | 0 dangling (36 junction, 11 street end, 2 border, 1 block edge, 1 whitelisted) | pass |
| C4 | no railway in the region; 0 crossings | pass |
| C5 | 0 of 15 villages without a street | pass |

## Why C1 fails (7.0 km off the reference)
1. **Dashed paths (2.5 km off).** ily_path, kur_path and ves_path follow the dashes. Most dash gaps on this sheet are 50 to 80 m, but c1_centre only bridges gaps up to about 40 m, so the bridged gaps count as off. Without the paths, C1 would be 83 %.
2. **Solid roads the reference misses.**
   - ves_n: the thick black arc E of Veselyi has no centre line on most of its length in c1_centre (550 m off). See `review/doubt_ves_n_arc.png`.
   - olk_rd: about 850 m off, between Olkhovsky and the river crossing. The road band W of x ≈ 450 px has only edge skeletons. The line at y ≈ 585 px (x 470 to 600) is ink, but only fragments of it are in c1. See `review/doubt_olk_rd.png`.
3. **Streets outside the built-up mask.** These are vn_s, ves_st, olk_g, ko_st and kur_n, together about 1.7 km off. They lie in lanes next to houses that `builtup_1941.png` does not cover.

I did not move any line onto ink that is not the road just to raise C1.

## Left out: could not be read reliably (rule 6)
- **a00, a01, a02 of the old trace (NW corner, W of the sheet join).** The join is the frame line at x ≈ 140 px. On the W sheet the contours and ravines are printed dark brown, the same tone as these lines. a00 is dashed, a01 is a straight piece and a02 is a curve. Their shapes fit contours and ravines, and none of them connects to anything. The frozen ink test also classes them as warm (brown). They are left out. Crop: `review/doubt_NW_west_of_frame.png`.
- **a05 of the old trace.** This is a very faint, straight grey line at y ≈ 600 to 605 px, E of the Kurlov farm, running to the E border. It is barely visible and is not in the reference. It is left out, but it may be a faded field track. The neighbouring E region should check whether it continues. Crop: `review/doubt_a05_faint_line.png`.
- **Ravine N of the block top (x 1150 to 1450 px, y 60 to 130 px).** The old r12 ran E along its brown, dotted S edge. That edge is a ravine outline, not a road, so it is left out.
- **Short lines from the windmill symbol at (1335, 1080) px to klu_e.** These are thin and grey and turn into the brown ravine line. They are left out.

## Doubts in what was traced
- **Olkhovsky to Veselyi (olk_rd).** E of x ≈ 580 px the road is traced on the line through the star symbol (y ≈ 600 to 610 px) up to the Olshanka crossing at (752, 598) px. The parallel line at y ≈ 555 to 560 px is the 2 km grid; the old r04 followed it.
- **Veselyi streets (ves_st, vn_st, vn_s, vn_top, vn_e).** The scan is about 12 m/px here, so streets are placed in the light lanes as well as they can be read. vn_s runs along the E bank of the Olshanka and may partly sit on bank line work.
- **ko_rd (old r09, secondary).** It is traced in the light lane between the thick black band (houses) and the thin SW line, not on either edge. `dbl_centre` is empty there. Crop: `review/doubt_ko_rd.png`.
- **Kurlov farm.** The hatched rectangle's double outline is treated as an enclosure, not a road. kur_n covers only the W part, where there are houses. kur_e is the lane on the farm's E side; it is needed for village blob 155.
- **olk_st.** It ends at the edge of the built-up area at x ≈ 169 px. The lane continues for another 23 px to the sheet join. The road W of the join does not line up with it (it is about 50 px further N), so it is not continued.
- **ily_path.** It starts at its first dash below the lettering "Ильинский"; no continuation can be read N of the lettering. It is whitelisted as a dead end.
- **ko_st.** The street continues S across the border into the next region.

## C2 verdict classes (150 pieces, all `not-road`)
- House outlines and house-row edges inside villages.
- Banks of the Psel and the Olshanka (dark print under the blue wash).
- Hatching and the outline of the Kurlov farm enclosure.
- Wood, orchard and marsh symbols.
- Lettering.
- Grid lines (x ≈ 930 px and x ≈ 975 px).
- Ravine and contour curves.
- Edge lines of roads that are traced at their centre or lane (olk_rd, ves_st, ko_rd, olk_g).

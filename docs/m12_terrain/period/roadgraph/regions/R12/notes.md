# R12 (node N3): notes, doubts and unreadable spots

Region x 6144..12288, y 14336..20480 (lattice m). 22 lines, 33.0 km. No railway in the region (railway.json does not enter it), so C4 is trivially 0.

## Files
- `frag.json`: roads_1941.json schema plus `ends: [start, end]`. `'border'` means the line is cut exactly on the region border and the merge node should join it. `null` means a junction (shared vertex), a street end inside the village mask, or a reviewed dead end. The N border is also the block edge.
- `deadends.json`: 2 reviewed dead ends, each with a crop in `review/`.
- `eval/`: eval_roads.py output. `eval/c2/` holds the make_review.py sheets. `eval/c2_verdicts.json` has a verdict for all 124 road-like pieces.
- `tools/`: the guided tracer (`trace.py`, `build.py`) and the waypoint spec (`spec8.py`). Each line is routed over the frozen c1_centre inside a corridor of about 56 m around waypoints read off the sheet. Line ends are snapped onto the other line by inserting a shared vertex, then the line is clipped to the region.
- `review/overview.png`: the sheet next to the traced lines. Magenta dots mark off-ink points.

## Results (eval_roads.py --region ... --allow-border)
C1 is 92.3 % of 33.0 km and fails the 98 % target. C3 has 0 dangling ends, C4 has 0 illegal crossings, C5 has 0 of 10 villages without a street, and C2 has 124 road-like pieces, all `not-road` (16 of them marked UNREADABLE).

### Why C1 stays below 98 % (about 2.5 km off-ink)
- **R12_r15, dashed path (68.7 %).** The dash gaps on this sheet are about 40-60 m, longer than the 11 px closing bridges, so each gap counts as off. The line does follow the dashes.
- **R12_r16, main road (88 %).** It runs about 370 m through the "12.0" lettering and 150 m through the hatched marks NW of it. Both stretches are traced straight along the drawn direction (rule 1), and c1_centre has no line there.
- **R12_r17 (87.8 %).** The solid track ends at the top of the lettering "Polezhayev" (8200, 16770). A segment of the same line comes out under the lettering at (7990, 16525) and runs on to r14. I joined the two straight through the lettering (about 320 m). This is a doubt: the two pieces are not exactly collinear.
- **sw2, r22, sov1.** Short stretches in the scan blur at the Psel N bank and at the sovkhoz pond.
- **Crossing at Petrovka N (11727, 17851).** Several double lines merge into a blob of ink here, and the topology is my best reading: the NW-SE road (r16) crosses the SW-NE road (r19 / r20).

## Doubts
1. **The Prelestnoye main street.** The wide solid band SW-NE through Prelestnoye is traced as the continuation of the double-line road r19 from Petrovka. The thin single line about 150 m SE of it is traced as track `pre2` and ends at the "klkh." lettering (dead end, see the crop). The baseline (c72) had it the other way round. Which of the two is the double-line road cannot be read from this scan.
2. **Polezhayev main street (`pol1`).** It is drawn as two thin parallel lines but classed `residential` because it is the village street (C5). It might be a `secondary` road.
3. **`pb1`** runs from the S end of `pol1`, S past 272.9 and then W to the village at (8380, 15220). Its middle part (the bend at 8850, 15270) is uncertain.
4. **`pl2`** is a solid line along the S edge of the orchard N of 272.9 and is classed `track`. It may be an orchard or field boundary rather than a road.
5. **Baseline `a05` (y ≈ 18170, W of x 7082) is not traced.** It lies exactly on the scan-strip seam, is perfectly straight and has no ink in ink_clean / c1_centre. I judge it to be the seam or frame edge.
6. **Baseline `b04` (vertical at x ≈ 7930) is not traced.** It is the 2 km grid line. Its street `b22` is replaced by streets inside the two village blobs (`v195`, `v194`).
7. **Baseline `pl1` (NW of the Prelestnoye band) is not traced.** There is no ink line along it.
8. **sw2** comes from the S border NE to the r15 end. Its last 100 m into the junction at (7744, 14858) cannot be read well.

## Unreadable spots, left out (these are the UNREADABLE verdicts in c2_verdicts.json)
- **U0039, U0040:** black curved strokes N of 181.9 (10744-11000, 17836-17960). They may be a track from Petrovka-N towards the sovkhoz.
- **U0067, U0068, U0095, U0096:** short dark strokes at the W and E edges of Petrovka.
- **U0098, U0099:** two parallel NE lines S of the village at (8000-8340, 14750-15170). They may be Psel bank lines or a track to r15 / sw2.
- **U0100, U0101, U0103, U0108, U0111, U0113, U0119, U0121:** line work at the Psel N bank near the S border (x 7500-9600). The river wash, the bank lines and the edge of the village S of the region overlap there. The region S of R12 should check what continues here.

## Other verdicts, all judged on the eval/c2 tile sheets
- Orchard, wood and garden outlines around sovkhoz Voroshilova, and brown contours.
- Lettering: "32", "Svkh. im", "Voroshilova", "Prelestnoye".
- House-block outlines inside the village masks. This was decided partly by the village share of each piece, so it is a group judgment, not a check of every piece one by one.
- Second edge lines of the double-line bands at the Petrovka-N crossing.
- Stream and river bank lines, including the blue-tinted Psel N bank.
- Rows of short dashes between 272.9 and Prelestnoye, read as a garden or field-strip symbol.

## Border stubs for the merge node
- N border: r16 (7220, 20480), r18 (9102, 20480).
- E border: r16 (12288, 17518), r20 (12288, 18160), r21 (12288, 17967), r22 (12288, 18986), r30 (12288, 15439).
- S border: r19 (8803, 14336), sw2 (7338, 14336).
- W border: r14 (6144, 15968).

# R22 (node N6): notes

Region x 6144–12288, y 8192–14336 lattice m (sheet px 1536–3072, 2560–4096). It covers Bogoroditskoye (E part), Andreyevka, Mikhailovka, sovkhoz Oktyabrsky (W part), 241.6, sovkhoz Komsomolets, Ivanovsky Vyselok and the railway road. Blank patch A takes up the SW (px 1536–2032, 3107–3876).

## Check (frozen evaluator, `--allow-border`)
| check | result | target |
|---|---|---|
| C1 | **81.6 %** of 25.8 km (track 100 %, residential 99.9 %, secondary 77.5 %, path 28.2 %) | ≥ 98 %: **FAIL** (reasons below) |
| C2 | 127 road-like pieces, all judged in `eval/c2_verdicts.json`, 0 `road` | pass |
| C3 | 0 dangling (junction 18, residential_end 21, border 6, whitelisted 1) | pass |
| C4 | 0 illegal, 0 crossings (crossings.json has no point in R22) | pass |
| C5 | 0 of 8 villages without a street | pass |

## Why C1 fails: the traced length off the frozen reference (≈ 4.75 km)
Each of these lines follows the drawn symbol. The reference `c1_centre` has no centre line there. Crops are in `review/c1gap_*.png` (left: sheet; right: c1_centre in red, dbl_centre in blue).
- **sw_path, 1.33 km.** A long-dash field path runs from the W border across the trig point at px (1749, 3923), then SE to the S border. The dash gaps are wider than the 11 px closing, so `c1_centre` has none of it.
- **railroad, 1.82 km.** The double-line road on the NW side of the railway.
  - The scan shows 3–4 parallel lines here. The reference keeps only scattered pieces of them, and none along the Komsomolets lettering (px 2290–2340, 3830–3890), which the trace crosses straight.
  - **Frozen railway.json is misplaced** from about px (2760, 3455) to (2990, 3250). It lies on the NW line of the road; the hatched railway is ~15–25 px further SE (`c1gap_railroad_json_on_road_line.png`).
  - To keep C4 legal I held the road on its NW line there (o ≈ +1.5 px from json), about 6 px NW of the true centre. A true-centre trace would cross railway.json twice. **Lead / N1 decision needed.**
- **road10, 0.99 km.** The "10.0" double-line road: through the "10.0" lettering (px 2600–2690, straight) and the stream wash at px 2330–2370. The reference has gaps at both.
- **okt_path, 0.38 km.** Dashed path from road10 to Oktyabrsky. Most of its dashes are missing from the reference.
- **r19, 0.23 km.** The main village road. It comes from the start lines and is off only at village edges.

C1 on everything except these four lines would be about 99 %.

## Schema
Same as roads_1941.json (`highway`, `name`, `source`, `length_m`, `pts`), plus `ends: [start_tag, end_tag]`:
- `border`: cut exactly on the region border, for the N11 merge.
- `junction`: shares an exact vertex with another line.
- `village_edge`: a street end inside the built-up mask.
- `blank`
- `deadend`, or null when the end is whitelisted in deadends.json.

Border ends (lattice m):
- r19: (8806.5, 14336) and (6144, 12937.6)
- road10: (12288, 12303.8)
- okt_road: (12288, 13112.4)
- railroad: (8645.9, 8192) and (12288, 11909.9)
- r58: (11722.1, 8192)
- hamlet_trk: (11484.7, 8192)
- sw_path: (6144, 8988) and (7528.9, 8192)

## Doubts / left out (rule 6)
- **Railway band structure.** NW of railway.json there are 3–4 thin parallel lines (spacing ~10–13 px). I read them as the road's double line (NW) beside the railway symbol, following graph.md. Which pair is the road cannot be resolved firmly at this scan. The trace follows the reference skeleton inside the NW band.
- **Woods NW edge.** A solid line parallel to the railway on its SE side, ~0.7 km (px 2650–2900, 3450–3600). I judged it a wood outline, not a road (U-pieces in c2_verdicts). If it is a track, it needs tracing on the SE side only.
- **woods_trk.** A solid track from Ivanovsky Vyselok NW to the SE corner of the wood. It ends there and is whitelisted in deadends.json with a crop.
- **Komsomolets.** A thick short bar SE of the sovkhoz (px 2153–2201, 3915–3939) stops 160 m short of the railway road. I read it as a building, not traced. A narrow closed double outline S of the sovkhoz (px 2092–2105, 3900–3985) is not traced.
- **Village streets kz2, kz3, b12.** In the start lines they ran S out of Andreyevka/Bogoroditskoye over empty paper to the blank patch. They are now cut at the village edge. No ink continues S there, except a 130 m stroke at px (1545, 3070–3098) and an arc at px (1604–1643, 3100) at the blank edge, which I could not read and have not traced.
- **Hill 241.6.** The dark loop round it is taken as an index contour: the contour layer carries most of it.
- **Short streets.** st216 is a short street through the 0.35 ha sliver blob 216 (needed for C5). st229 runs along the open E side of the solid block blob 229. Both are placed by the C5 rule rather than read from a drawn lane.
- **Start streets kept.** mk1/mk2/an1/an2/b03/st1/b18 are reused from the start lines (lanes checked by eye), trimmed to the built-up mask. r19 (the main road through the villages) is kept as the start traced it.
- **Pencil.** Pencil areas (void) cover the NE corner. road10 and railroad cross them toward the E border, where X1 lies just outside the region.

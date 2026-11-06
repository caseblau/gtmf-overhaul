# Node spec: region digitiser (N2–N10), reusable

**Job:** digitise, for ONE region of the Prokhorovka block, every road, cart track, field track and village street drawn on the 1941 RKKA 1:100 000 sheet, exactly as drawn. Work in the cloud only. Do not commit, do not touch the PC, do not use a browser, and write only inside your own output folder.

**Inputs (read-only)**
- Sheet: /mnt/user-data/uploads/gtmf-overhaul/docs/m12_terrain/period/rkka100k_block.png. Grid: 4 m/px, row 0 = north; lattice metres x = 4·px, y = 24576 − 4·py.
- Frozen evaluator (do NOT edit) in /mnt/user-data/outputs/roadgraph/n1/:
  - eval_roads.py, make_review.py
  - ink_clean.png, c1_centre.png, dbl_centre.png
  - railway.json, crossings.json, blank.png
  - README.md (how the rules are applied)
- Settlements: /mnt/user-data/uploads/gtmf-overhaul/docs/m12_terrain/period/builtup_1941.png
- Starting lines (may be wrong): /mnt/user-data/uploads/gtmf-overhaul/docs/m12_terrain/period/roads_1941.json. Same schema for your output. The guided-waypoint tooling is in /mnt/user-data/uploads/gtmf-overhaul/tools/roads_1941.py and can be reused.
- Graph context: /mnt/user-data/outputs/roadgraph/graph.md (rules learned).

**Rules**
1. Lines follow the centre of the drawn symbol: the centre between the two lines of a double line; the dashed line itself, with dash gaps bridged. Vertices at least every 25 m and at every bend. No straightening, no shortcuts. A line through lettering or a spot height continues along the drawn direction.
2. Class comes from the symbol: double line = secondary, single solid = track, dashed = path, village street = residential. Streets run along the light lanes between house-block rows. For a single row, the street is on the open side.
3. A line ends only where the sheet line ends: at a junction (it shares the exact vertex with the line it meets), a village edge (street), a blank patch, the block edge, or your REGION BORDER. At the border, end the line exactly on the border and tag the end `border` (`ends: ['border', ...]` or the field the schema uses; document it).
4. Roads stay on the side of the railway the sheet draws them on; they cross only at points in crossings.json.
5. Every built-up blob of 0.3 ha or more in the region gets at least one street.
6. Do not invent. Where you cannot read the sheet, leave it out and list it.

**Output:** a folder with
- `frag.json` (same schema as roads_1941.json, only your region's lines, clipped to the region with border ends)
- `deadends.json`: reviewed genuine dead ends, each with a crop path
- `review/` crops
- `notes.md`: unreadable spots and doubts

**Check (run it yourself before reporting; the lead re-runs it):**
`python3 /mnt/user-data/outputs/roadgraph/n1/eval_roads.py <out>/frag.json <out>/eval --region x0 y0 x1 y1 --allow-border`

Targets for the region:
- C1 ≥ 98 % (on the centre-line reference)
- C3: no unclassified dangling ends
- C4: 0 illegal crossings
- C5: 0 villages without a street
- C2: run `make_review.py`. Every remaining road-like uncovered piece must get a verdict (`road`, which you then trace, or `not-road` with its reason) in `eval/c2_verdicts.json`.

Iterate until the targets pass or you have done 3 full passes. Report in under 200 words: the numbers, the remaining failures with reasons, and the output path.

# N1 v3: the frozen evaluator for the 1941 roads, built from the sheet only

**Changes since v2.** v2 failed the gate because C1 was measured against raw ink. The lines on this scan are about 36 m wide, so a correct centre trace of a double line failed, while a trace 25 m off still passed. v3 measures C1 against **centre lines**: single lines by their medial axis, double lines by the centre between the two lines, dashed lines bridged across their gaps.

**Earlier versions.** The v2 files are kept as `*_v2` and the v1 files as `*_v1`. `baseline_v2/` and `baseline_v1/` are left untouched.

**Inputs.** The sheet raster, `builtup_1941.png`, and the OSM main line, used only as a 180 m search corridor for the railway symbol. Nothing is read from any roads JSON.

## Conventions
- **Rasters:** full sheet grid, 5632 x 6144 at 4 m/px, row 0 at the north edge.
- **Lattice metres:** x = 4·px, y = 24576 − 4·py, where the pixel index is the pixel centre.
- **Tiles:** 1024 m squares of the block, named `Trrcc`, with row 0 at the north edge.

## Frozen layers
| file | content |
|---|---|
| `ink_clean.png` | black line work, including the warm-tinted black and dark print under the blue river wash (grey < 75, b−r < 24); dash chains bridged. Removal classes are in the table below. |
| `dbl_centre.png` | centre of the double-line (main road) symbol: the medial axis of the band closed between its two lines, found with an 11 px and a 17 px closing, where the centre is paper and the band is 10–34 px wide |
| `dbl_band.png` | the double-line bands: both lines plus the gap |
| `c1_centre.png` | **the C1 reference**: the skeleton of ink_clean closed with an 11 px disk (bridges dash gaps up to about 40 m), with the two edge lines of every double-line band replaced by `dbl_centre`. Spurs under 36 m are pruned. |
| `ink_skel.png` | the C2 layer: `c1_centre` with only pieces of 60 m or more |
| `house_blocks.png` | the house blocks that were removed |
| `contours.png`, `warm.png`, `lettering.png` | the brown contour line work, the brownish line work and the lettering boxes, used only by the C2 review filter |
| `builtup_ref.png`, `void.png`, `blank.png`, `railway.json`, `crossings.json` | as in v2 |

**What ink_clean removes:**
- **Lettering:** rows of letter-sized pieces, plus a component shape filter that drops compact or holed pieces under 200 m across. Dashes are kept: elongation ≥ 2.8, or ≥ 1.8 if no wider than 32 m.
- **Grid and frame:** the 2 km grid lines and the frame lines.
- **Contours:** brown, judged by the local ink tint.
- **Railway symbol.**
- **Pencil:** by hue, plus the black-pencil masks.
- **Water:** blue line work, by hue.
- **Wood and orchard:** dots and rings.
- **House blocks:** solid blobs in the villages. Anything that survives an opening by a 124 m straight line in any of 12 directions stays, which keeps the solid main-road bands through villages.

## Evaluator rules (fixed before the freeze)
**C1 (gate ≥ 98 %)**
- A traced point is on ink if it lies within 8 m of `c1_centre`.
- Inside the villages (builtup or house blocks, + 8 m), a point of any class counts as on. The sheet draws village streets and through roads as the light lane between the house rows.
- Void is not scored.
- Reported per road, per class and per tile.

**C2a (a number, not a gate)**
- For each tile: the share of `ink_skel` within 12 m of a traced line.

**C2 gate: `make_review.py`**
- The uncovered skeleton is split at its junctions, and every piece of 60 m or more is judged.
- **ROAD-LIKE** pieces are drawn in yellow and numbered `U....`; each one needs a `road` / `not-road` verdict in `uncovered.json`. A piece is road-like if all of these hold:
  - length ≥ 120 m;
  - low mean curvature: length-weighted chord / arc ≥ 0.9, ≥ 0.8 for pieces of 300 m or more, ≥ 0.95 if the line is dashed;
  - less than half of it within 10 m of contour line work;
  - less than half on brownish line work;
  - less than half inside lettering boxes.
- Everything else is drawn in cyan as an info layer (`I....`), listed with its reason.
- C2 passes when no piece is marked `road`.

**C3–C5**
- C3, C4 and C5 are unchanged from v2.
- **Railway through Prokhorovka:** the track is the band with the hatched black/white symbol, E of the solid main-street band.
- **Crossings:** X1 is certain; X2–X7 are probable. X6 and X7 are in Prokhorovka town.

## Sanity tests (current c72 roads_1941.json)
**Synthetic sideways shift.**

| shift | C1 all | path | track | secondary |
|---|---|---|---|---|
| none | 49.1 % | 34.2 % | 53.2 % | 44.1 % |
| 5 m | 47.5 % | | | |
| 15 m | 32.4 % | 9.6 % | 19.2 % | 37.7 % |
| 30 m | 29.6 % | | | |

- The floor of about 30 % is the village allowance.
- Secondary drops only a little under a 15 m shift because c72 mostly traces one edge of the double line. A sideways shift moves about half of it onto the centre.

**Worst roads.**
- `review/c1_worst/`: the 15 lowest roads, each with a crop.
- `review/c1_worst_secondary/`: the 8 lowest main roads.
- I checked all 15 crops and the 4 worst main-road crops by eye. Every off-ink stretch I looked at is a real tracing error:
  - lines across empty paper (a08, r49, r85);
  - lines parallel to brown ravine edges (a00–a02);
  - lanes through lettering or woods (bg1, y03);
  - main roads traced along one edge of the double line (belgorod_road, r16, r79).
- Earlier artefacts found this way and fixed:
  - dashes dropped by the shape filter;
  - road ink lost under the river wash;
  - gaps between wide double lines left unclosed;
  - through roads lying in village lanes.

## Baseline v3 (`baseline_v3/`)
| check | result |
|---|---|
| C1 | 49.1 % of 303.4 km. Per class: path 34.2 %, track 53.2 %, secondary 44.1 %, residential 53.9 %. |
| C2a | 11.9 % covered (number only) |
| C2 review | 4176 uncovered pieces of 60 m or more. **1433 road-like pieces to review (274 km)**; 2743 in the info layer (292 km). |
| C3 | 127 dangling ends |
| C4 | 4 roads cross at drawn crossings, 6 illegal |
| C5 | 40 of 103 villages have no street |

## Limits
- **Unremoved line work:** river-bank outlines drawn in dark ink, and dark contours that pass the tint test, are still in the skeleton. They show up as road-like pieces for the reviewer to reject.
- **Partial double-line centres:** `dbl_centre` is incomplete where one of the two lines is broken. The closed-band skeleton still gives the centre there.
- **Dash chaining:** linking dashes into chains rarely triggers. Dash gaps are bridged by the 11 px closing instead, which covers gaps up to about 40 m.
- **Towns:** in the Prokhorovka and Belenikhino town centres the street pattern is only partly readable.

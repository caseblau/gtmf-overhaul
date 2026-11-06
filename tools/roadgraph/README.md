# roadgraph: digitising the 1941 roads, Nov 2026

These scripts digitised every road on the RKKA 1941 1:100 000 sheet (`docs/m12_terrain/period/rkka100k_block.png`), checked each line against the sheet, and merged the results.

They ran in Claude's cloud workspace, so they still contain absolute paths such as `/mnt/user-data/outputs/roadgraph/...`. Before running a script anywhere else, change its path constants. Its data lives in `docs/m12_terrain/period/roadgraph/`.

| file | job |
|---|---|
| `build/` | Builds the frozen evaluator reference (N1 v3). `inkclean3.py` writes the centre-line masks in `docs/.../roadgraph/ref/` from the sheet. |
| `eval_roads.py` | Scores a roads json against the reference. The checks are C1 (on the drawn centre line), C3 (dangling ends), C4 (railway crossings) and C5 (villages without a street). Example: `python eval_roads.py roads.json outdir [--region x0 y0 x1 y1 --allow-border] [--ref-dir dir]` |
| `make_review.py`, `c1_worst.py` | Make review crops: the uncovered road-like pieces, and the worst off-line stretches. |
| `match.py` | Moves each traced line onto the drawn centre line, by a least-cost route inside a 40 m corridor. The railway acts as a wall except at the drawn crossings. |
| `red_stretches.py` | Lists every off-line stretch of 60 m or more, with a crop for each. |
| `merge.py` | Joins the corrected group files and their border ends into one file. |
| `connect.py` | Connects dangling ends to the nearest other line within 60 m. |
| `smooth.py` | Light smoothing that keeps junction vertices exactly in place. |
| `natural.py` | EXPERIMENTAL and not used: stronger smoothing. It made bends sharper, so it was rejected. |
| `seam/` | Prepared, not applied. Realigns the two scans that are stitched together in the sheet, using the 2 km grid. The seam is at sheet row ~1631 and ~3455; below it the scan is shifted 33–47 px west. |

**Result:** `docs/m12_terrain/period/roadgraph/roads_1941_graph.json`. The generator does not use it yet; it still reads `roads_1941.json` (the c72 version). To try the new roads, either:
- pass `--roads1941 docs\m12_terrain\period\roadgraph\roads_1941_graph.json` to `tools\prokh_gen.py`, or
- copy the file over `roads_1941.json`.

The status, the numbers and the open problems are in `docs/m12_terrain/period/roadgraph/progress.md` and `checks.md`.

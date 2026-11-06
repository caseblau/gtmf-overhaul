# Graph: 1941 road network for the Prokhorovka map (exact digitisation)

Status: **DRAFT, waiting for approval** (Layer 1 pause). Nothing has been run.

## Inputs (filled from the conversation)
| Field | Value |
|---|---|
| TASK | Digitise every road, cart track, field track and village street drawn on the 1941 RKKA 1:100 000 sheet inside the 9 x 9 cell block (x 0..18432 m, y 2048..20480 m, lattice metres), exactly as drawn: no modern (OSM) roads, no invented geometry. Junctions must connect, and roads must not jump sides of the railway. |
| OUTPUT | `docs/m12_terrain/period/roads_1941.json` (format read by `tools/prokh_gen.py`), plus `graph.md`, `checks.md`, `progress.md` in `/mnt/user-data/outputs/roadgraph/` |
| CHECKS | C1–C7 below |
| SOURCES | `docs/m12_terrain/period/rkka100k_block.png` (sheet, 4 m/px, row 0 = north, x = 4·px, y = 24576 − 4·py); `builtup_1941.png` (cleaned c72); the c72 `roads_1941.json` as the baseline and starting point; `tools/roads_1941.py` |
| SCOPE | Cloud workspace only. A node writes only its own fragment file. Only the merge node writes `roads_1941.json`. Writing to the PC repo is one gated commit at the end (N9), with your approval. No browser and no PC control, except running the generator cmd files if you allow it. |
| LIMIT | Up to 3 correction attempts per node and 14 subagent runs in total, then stop and return a partial status. |

## Fixed evaluators (frozen before work starts; never loosened to get a pass)
- **C1 on-ink:** at least 98 % of traced length lies within 8 m of drawn road ink in the frozen reference `roads_ref.png` (made by N1). Measured per road and per region.
- **C2 coverage:** in every 1 km tile, at least 95 % of the reference road-skeleton length lies within 12 m of a traced line. Tiles that miss are listed, never averaged away.
- **C3 topology:** every line end is a shared junction vertex (≤ 2 m), on the block edge, on a blank-patch edge, a street end inside the built-up mask, or on the reviewed dead-end list. Each dead-end entry has a tile crop as evidence.
- **C4 railway:** no traced road crosses the railway except at crossings drawn on the sheet. The crossings come from a list made in N1.
- **C5 villages:** every built-up blob of 0.3 ha or more has at least one street.
- **C6 generator:** `prokh_gen.py` imports, and three fixed test cells generate without error: MgF4 (Psel villages), MgI9 (Belenikhino), MgK3 (Prokhorovka). Houses must stand along the streets.
- **C7 human gate:** you accept the overview and the 1 km tile contact sheets.

## Nodes
| id | kind | scope (one job) | input | output | check |
|---|---|---|---|---|---|
| N0 | code | Baseline: run C1–C5 on the c72 json | c72 json, current ink mask | `baseline.json` (metrics per tile) | runs; numbers recorded in checks.md |
| N1 | judgment + code | Freeze the evaluator: road-only reference skeleton (lettering, grid, contours, pencil, railway removed), the railway centre line, the list of drawn crossings, the blank-patch masks | sheet, ink mask | `roads_ref.png`, `railway.json`, `crossings.json`, `blank.png` | 1 km contact sheet of the reference reviewed; reviewer note for every removal class |
| N2–N10 | judgment | Digitise one region of 2 × 2 block cells (4 × 4 km; the last row/column 1 cell wide), 9 regions. Every drawn road, track and street in the region, starting from the baseline lines there. Lines that cross the region border end in a `border` stub at the border. | sheet crop, `roads_ref.png` crop, baseline lines in the region, `railway.json`, `crossings.json` | `frag_R{r}{c}.json` | C1, C2, C3 (border stubs allowed), C4, C5 restricted to the region |
| N11 | code | Merge: join border stubs within 15 m into shared vertices, dedupe, assign classes and ids, write the JSON | 9 fragments | `roads_1941.json` | C3 globally (no border stubs left), C4 globally, schema valid |
| N12 | code | Full evaluation: C1–C5 on the merged file, and diffs against the baseline | merged json, frozen refs | `checks.md` rows, `report/` | all of C1–C5 pass |
| N13 | code | Generator check: C6 on the three test cells | merged json, generator, cell inputs | cell logs, top-down previews | C6 |
| N14 | code | Review sheets: overview and 1 km tile contact sheets with traced lines over the sheet | merged json, sheet | `review/*.jpg` | files exist; C7 by you |
| N15 | gated action | Commit `roads_1941.json` (and `roads_1941.py` if it changed) to the PC repo, stage the files back and byte-compare | accepted json | committed files | byte-identical after staging back; only with your approval |

**Code nodes (never routed through a subagent):** N0, N11, N12, N13, N14, N15, plus the deterministic half of N1 (masking, skeletonising).

## Edges
- N0 → N12 (baseline for comparison)
- N1 → N2..N10 (frozen reference and railway data)
- N1 → N12 (the evaluator)
- N2..N10 → N11 → N12 → N13 → N14 → (gate C7) → N15
- **Parallel:** N2..N10 run side by side once N1 is accepted. N0 can run in parallel with N1.

## Gates
- **N1 → N2..N10:** the evaluator must be reviewed. Any edit to `roads_ref.png` after this gate invalidates every region result.
- **Each region → N11:** deterministic C1–C5 for the region first, then the node's report.
- **N12 → N13:** all of C1–C5 pass.
- **N14 → N15:** your acceptance (C7).

## Return paths
- **Correction:** a failed region gate goes back to that region node only, with the failing tiles, the measured numbers and the crops, scoped "fix this node only". Up to 3 attempts; after the third the region is reported unresolved.
- **Learning:** rules confirmed by accepted results are appended below.

## Rules learned (from runs before this graph)
- Automatic skeleton tracing of this sheet picks up lettering, ravine edges and village interiors. Use guided waypoints snapped to the ink inside a narrow corridor (c68–c72).
- The road along the Prokhorovka – Belenikhino railway runs on the NW/W side the whole way; the sheet draws no crossing (c71).
- Villages need streets, otherwise the generator places no houses (c72).
- Some sheet tiles print roads black with a warm tint; the ink test must accept it (c71).

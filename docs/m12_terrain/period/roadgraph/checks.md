# checks.md: completion checklist (written before execution)

| node | requirement | verdict | evidence |
|---|---|---|---|
| N0 | Baseline C1–C5 measured on the c72 json | pass | n1/baseline_v3: C1 49.1 %, C3 127 dangling, C4 6, C5 40/103 |
| N1 | Reference skeleton, railway, crossings and blank masks frozen and reviewed | pass (v3), with known gaps | v4 attempts (dash gap 80 m, grid-only removal, lettering bridges, raw-ink union) rejected: they raised random-line and shifted-trace scores more than real traces. railway.json lies on the road's NW line in R22 (not fixed). |
| N2–N10 | Each region passes C1–C5 locally | **fail (C1)** | Lead re-ran eval_roads.py on every frag.json (evaluator files unchanged since freeze, md5 recorded in progress.md). C1: R11 78.0, R12 92.3, R13 82.2, R21 79.9, R22 81.6, R23 71.2, R31 77.6, R32 87.2, R33 75.8 % (target 98). C3 0 dangling, C4 0 illegal, C5 0 villages without street, C2 verdicts present: all 9 pass. Worst crops: status/worst/; overview: status/regions_c1_overview.jpg |
| N11 | Merged file: no border stubs left, schema valid, C3 and C4 global | partial | map-match (n11/match.py) + 5 correction nodes (n11/fix/A–E) + merge (17 border joins) + 16 gap connections ≤ 60 m + smoothing. C4 0. C3 26 dangling left (border ends whose neighbour did not continue). |
| N12 | C1 ≥ 98 % on-ink; C2 ≥ 95 % per 1 km tile; C3 every end classified; C4 0 illegal crossings; C5 every village ≥ 0.3 ha has a street | **fail (C1, C3)** | n12/eval: C1 85.3 % (path 54, track 89, secondary 85, residential 95), C3 26 dangling, C4 0, C5 0/103. 219 C1 stretches carry a `gap` verdict; lead spot-check of 16: 12 sound, 4 wrong (3 in group A around the railway road / Prokhorovka). |
| N13 | C6: test cells generate without error, houses along the streets | pass | MgF4, MgK3, MxL4 (Prokhorovka), MxH9 (Belenikhino; MgI9 is not a block cell name) generated; previews n13/prev_*_s.jpg |
| N14 | C7: overview and contact sheets accepted by you | unresolved | not run |
| N15 | Committed files byte-identical after staging back | unresolved | not run |
| all | Every node output exists and opens; every gate ran on the saved version; failures fixed or reported | unresolved | not run |
| all | Rules from this run written to graph.md (and to the repo's CLAUDE.md, which does not exist yet; creating it needs your OK) | unresolved | not run |

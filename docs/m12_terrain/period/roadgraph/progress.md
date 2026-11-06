# progress.md

- **Graph:** 16 nodes drafted (N0–N15). Done: none. Running: none. Blocked: all, waiting for approval of graph.md.
- **Outputs:** graph.md, checks.md and progress.md in /mnt/user-data/outputs/roadgraph/. Baseline data: the c72 roads_1941.json, committed in the PC repo.
- **Decisions:** regions of 2 × 2 block cells, so each node holds one area at full detail. Only the merge node writes roads_1941.json. The evaluator (reference skeleton) is frozen in N1 before any digitising.
- **Open issues:** the repo has no CLAUDE.md. N13 needs the cell inputs, which are on the PC or already in the cloud from earlier test cells. Committing to the PC repo needs your OK.
- **Next action:** after approval, run N0 and N1 in parallel.

## Update - N1 done (5 Nov)
- N1 attempt 1 FAIL: reference seeded from the current roads (circular). Attempt 2 FAIL: double-line centres lay outside the 8 m tolerance, so main roads failed unfairly. Attempt 3 ACCEPTED and frozen: /mnt/user-data/outputs/roadgraph/n1/ (eval_roads.py, make_review.py, c1_centre.png, ink_clean.png, railway.json, crossings.json with 7 crossings, blank.png). The shift test drops C1 from 49.1 % to 32.4 %. The 15 worst crops show genuine tracing errors.
- N0 baseline (n1/baseline_v3): C1 49.1 %, C2a 11.9 %, 1433 road-like uncovered pieces, C3 127 dangling ends, C4 6 illegal crossings, C5 40 of 103 villages without a street.
- Decision: regions are 3 × 3 block cells (9 regions of 6 × 6 km); 2 × 2 cells would have made 25. C2 is a per-piece verdict list on the road-like uncovered pieces, gated by a reviewer.
- Next: N2–N10 in parallel (spec node_region_spec.md).

## Update - N2–N10 done, gate failed (5 Nov)
- 9 region nodes ran (9 of 14 subagent runs used). Lead gate re-run reproduces every node's numbers. Evaluator md5: eval_roads.py db4a3a2d, c1_centre.png 8117dfc2, railway.json 32e95460 (unchanged since N1 freeze).
- C2–C5 pass in all 9 regions. C1 fails in all 9 (71–92 %, 274 lines, ~340 km).
- Cause is mixed, checked on the 8 worst crops: some are reference gaps (dashed paths with 50–80 m gaps, lines through lettering, double lines with one edge broken; R22 says railway.json lies on the road's NW line), some are real tracing errors (R31_s_m1 cuts across blank paper; R23_band_rd sits on the outer edge line of the railway band, not a road centre).
- Not merged; N11+ blocked by the gate. Gate not loosened.
- Decision needed from the user (see chat).

## Update - N11–N13 (5 Nov, evening)
- Reference fix (user choice) tried as v4 and rejected by its own sanity test; v3 stays the evaluator.
- Code: map-matching onto the v3 centre lines (C1 80.5 -> 85.0, C4 kept 0 with a railway wall). 5 correction nodes on the 240 red stretches (14 of 14 subagent runs now used). Merge, gap connections, smoothing.
- Result n11/roads_1941.json: 277 lines, C1 85.3 %, C3 26 dangling, C4 0, C5 0/103 (c72 was 49.1 / 127 / 6 / 40).
- Gate N12 fails on C1 and C3; not loosened. N13 pass. Not committed (N15 needs the user's OK after C7).
- Open: the road beside the railway (railway.json misplaced; trace on the NW edge line), Prokhorovka knots (group A gap verdicts unreliable), 26 border ends, the sheet seam (user dropped realignment).

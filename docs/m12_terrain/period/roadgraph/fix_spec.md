# Correction node spec (C1 red stretches), one attempt

**Context.** The region traces were map-matched in code onto the frozen v3 centre-line reference (`n11/match.py`). Every stretch of 60 m or more that is still more than 8 m from the reference (outside villages) is listed in your group's `red.json`. Each entry has the road name, class, length, midpoint, start and end points (lattice m), and a crop. The crop shows the sheet on the left and the reference on the right, with the stretch in red.

**Inputs (read-only):**
- `/mnt/user-data/outputs/roadgraph/n11/fix/<G>/in.json`: your lines.
- `/mnt/user-data/outputs/roadgraph/n11/fix/<G>/red.json`: your stretches.
- The sheet: `/mnt/user-data/uploads/gtmf-overhaul/docs/m12_terrain/period/rkka100k_block.png`. It is 4 m/px, x = 4·px, y = 24576 − 4·py. The scan is upsampled 3×, so lines are blocky.
- The frozen evaluator in `/mnt/user-data/outputs/roadgraph/n1/`. Do not edit it.
- The rules in `/mnt/user-data/outputs/roadgraph/node_region_spec.md`; they still apply.

**Job.** Look at every stretch on the sheet itself, using your own crops at 4–6× zoom. Give each one exactly one verdict:
- `fixed`: the trace was off the drawn symbol. Retrace that stretch on the centre of the drawn symbol, with vertices at least every 25 m. The centre of a double line is between its two lines.
- `deleted`: no road is drawn there. Remove the stretch. If a line breaks in two, keep both parts only if each part ends at a junction, a village or a legitimate end.
- `gap`: the trace IS on the centre of a drawn road symbol, and the reference simply lacks that line. Give the reason in a few words, for example "under lettering 12.0", "under red pencil", "faint dashed path, dashes visible", or "straight road the grid filter removed". Save a 5× crop with the trace drawn on it as `review/<id>.png`. A gap verdict will be spot-checked by the lead against the sheet. A wrong gap verdict fails the whole group.

**Constraints:**
- Do not move line ends or vertices that other lines share, unless the fix requires it. If you move a shared vertex, move it identically in every line that uses it.
- Do not cross the railway except at the points in `n1/crossings.json`.
- Do not add new roads. Do not touch lines that are not in red.json, except to keep shared vertices identical.

**Output:** in `/mnt/user-data/outputs/roadgraph/n11/fix/<G>/`:
- `out.json`: same schema as in.json.
- `verdicts.json`: a list of `{id, verdict, reason}`.
- `review/`
- `notes.md`

**Check before reporting:**
1. `python3 /mnt/user-data/outputs/roadgraph/n1/eval_roads.py out.json eval`. C4 must report 0 illegal crossings in your area. Report the C1 value.
2. `python3 /mnt/user-data/outputs/roadgraph/n11/red_stretches.py out.json red_after`. Every stretch left in red_after must have a `gap` verdict.

Report in under 150 words: the counts of fixed, deleted and gap verdicts, C1 before and after, and any doubts.

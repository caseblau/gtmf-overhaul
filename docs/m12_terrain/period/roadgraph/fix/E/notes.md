# Correction node E (R32): notes

The input was `in.json` (41 lines) and the output is `out.json` (43 lines, same schema). I made one pass and gave a verdict for every id in `verdicts.json`.

## Checks
- `eval_roads.py out.json eval`: C1 rose from **89.6 %** (in.json) to **90.5 %**. C4 shows **0 illegal crossings**. C3 dangling went from 21 to 24, because of the splits listed below.
- `red_stretches.py out.json red_after`: 20 stretches (3061 m) are still red. Each one maps to an original id with a `gap` verdict:
  S0001=S0188, S0002=S0189, S0003=S0190, S0004=S0191, S0005=S0193, S0006=S0194, S0007=S0195, S0008=S0197, S0009=S0199, S0010=S0200, S0011=S0201, S0012=S0202, S0013=S0203, S0014=S0204, S0015=S0205, S0016=S0206, S0017=S0207, S0018=S0208, S0019=S0211, S0020=S0212.

## Verdict counts
fixed 1, deleted 5, gap 20, out_of_scope 2.

Twelve of the gap entries carry `retraced: true`. In those, the old trace was off the drawn symbol and I moved it onto the symbol, as a `fixed` verdict would. The reference has no centre line there, so the stretch stays red, and the spec's check 2 requires a `gap` verdict for it. Most of these are faint lines below the ink threshold, lanes between house blocks, or links under lettering.

## Topology changes (new or changed line ends)
- `bel` N end: now on the border at (8645.9, 8192). This is the start of the R22 line ("railroad"). The old border point at x 8540 matched nothing.
- `bel_sw` NE end: now the shared vertex (8988, 3600), which is the last point of `bl01`. It is no longer joined to `bel_s` at (9087, 3360), and that vertex is now a plain bel_s vertex. N9's notes called the old link a guess. The new link follows the drawn NNE direction under the lettering.
- `bel_sw` is split at S0213. The N part ends at (8168, 2268), on the untraced thick ENE line. The new line `bel_sw_s` runs from (8206.6, 2164) to the border.
- `n_e2` is split at S0209. The W part ends at (11276, 7436.6), where its line goes under the red pencil band. The new line `n_e2_e` starts at the bottom of the drawn stub (11382.6, 7496.4) and ends at the n_e1 junction (11581.4, 7429.7).
- `n_r56` now starts at (8848, 7168) at the ravine edge and ends at (11800, 6680) in the Ivanovsky Vyselok blot.

No vertex shared with a line outside red.json was moved. The junction vertices kept are mts_x/w_r74 (8919.9, 4127.7), iv_e/r76 (10468.6, 3778.6), n_r53/bel (8556, 8040) and n_e1/n_e2 (11581.4, 7429.7).

## Doubts
- **S0205 (se_dbl, 64 m)** is my lowest-confidence gap. East of Belenikhino the road runs through oblique black hatch strokes. The two reference pieces on either side lie in different gaps between the strokes, and the link between them crosses one solid stroke. Please check this one first.
- **S0197 (under the ink blot)** is not readable on the sheet. I kept the line because it is the straight continuation into the ivv_n junction.
- **S0195 and S0211** sit on faint grey lines with a darkness of about 100–150 on a 0–255 scale. They are visible on the sheet but are not in `ink_clean`.
- **S0216 and S0217** belong to R33's `r78`, which has the same name as R32's `r78`. They were assigned to E, but the line is in group D's `in.json`, and D's `red.json` does not list them either. Nobody has reviewed them. The lead needs to reassign them.
- **Process issue:** at the start I wrote `tools/crop.py`, `tools/allcrops.py`, `cr/*.png` and `eval_in/` into the shared scratchpad root, before I noticed that other nodes use it. Another node's `tools/crop.py` may have been overwritten. Everything after that is in `scratchpad/nodeE_do2l/`.

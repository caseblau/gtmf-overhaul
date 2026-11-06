# Correction node C (R11, R12, R22): notes

**Verdicts (53 entries):** 4 fixed, 2 deleted, 47 gap. That is the 52 stretches in red.json plus one extra item, explained below.

## Checks
- `eval_roads.py out.json eval`: C1 went from 88.0 % (in.json) to 88.6 %. C4 has 0 illegal crossings. C3 dangling ends went from 23 to 27: the two deletions created 3 ends, tagged `village_edge`.
- `red_stretches.py out.json red_after`: 47 stretches remain. Every one of them has a `gap` verdict.
- One of them is not in red.json: an ily_path dash gap at 1694,16170. Before the edits it measured about 56 m. It reaches 64 m only because `densify` resamples the whole line once the line's length changes. I listed it as `ily_path@1694,16170`, with the crop `review/ily_path_1694_16170.png`.

## Method
- I read each stretch from the sheet, using 2.5× context crops, 5× crops and ASCII grey dumps (4 m cells).
- The retraces are of these kinds:
  - least-cost route along dark ink (dash and line centres), with gaps bridged straight;
  - straight lines under lettering, pencil and water;
  - a sideways shift to the centre of a double line (S0030 and S0033, checked with grey profiles);
  - route onto the reference (S0019, S0025, S0028);
  - hand-placed points (S0005).
- Shared vertices were not moved. The one exception is the ves_path start at 3472,19432, which was removed by the S0008 deletion; vn_st keeps that vertex.
- `review/<id>.png`: the sheet at 5×. Blue is the line before the edit, red the line after.

## Doubts (the weakest gap verdicts)
- **Village lanes outside the builtup/house-block masks:** S0001–S0003 (Olkhovatka), S0006, S0013, S0024, S0026, S0027, S0041. The sheet here is dense and blocky, and I could not read the micro-geometry of these lanes with confidence.
- **Road beside the railway:** S0092–S0094. The road is drawn as the NW lines of the composite railway band. In S0093 the trace sits on the outer NW line, not exactly on the double-line centre. Moving it about 8 m SE would put it on top of railway.json, so I left it.
- **Remaining red to the junction:** S0018 follows the drawn line, but its last part to the klu_rd junction is still red. S0019 now sits on the reference, but it takes a small detour W of that junction.
- **Long dash gaps:** S0009 (about 95 m) and S0040 (about 80 m) are bridged straight. Both are longer than the usual dash gaps on this sheet.
- **S0011 and S0012 (ves_path):** these are straightened under lettering. The untouched piece of ves_path between them follows the outline of the letter "о", but it was on the reference and not in red.json, so I left it.
- **Deletions:** S0007 (ves_n, 200 m of open paper) and S0008 (ves_path connector to the vn_st junction). The faint line running NE from the S0008 path end was not traced, because the rules forbid adding new roads.

# Correction node D (R13, R33): notes

## Counts (50 stretches in red.json)
- fixed 15: S0054-S0059, S0215, S0219, S0220, S0222, S0229, S0231, S0236, S0238, S0239
- deleted 2: S0063 (vo_a tail), S0065 (vo_d tail)
- gap 33: the rest (review/<id>.png)

## Checks
- `eval_roads.py out.json eval`: C1 85.0 % (in.json) -> 86.0 % (out.json), whole-block run, D lines only. C4: 0 illegal.
- `red_stretches.py out.json red_after`: 48 stretches (7592 m).
  - 33 are the original gap stretches.
  - 12 are fixed stretches that were moved onto the drawn line, which the reference does not contain. Each has an `after:` gap entry in verdicts.json and a `review/after_<id>.png` crop.
  - after:S0025 (r46, 64 m) is a junction knot. Its geometry did not change. It went over 60 m only because the S0215 edit upstream changed where the line is resampled. It has a gap entry.
  - after:S0026 and after:S0027 (r78) were not in red.json, and in.json shows them too. I did not touch them, as the spec says. **They have no gap verdict, so check 2 is not fully met.** S0027 looks about 15 m N of its black line and needs a fix.

## Method
- I looked at every stretch on 3–5× crops of the sheet, with the reference and the ink layers beside them.
- Single lines were retraced by a least-cost path on the sheet's darkness (255 − max RGB), inside a 48 m corridor. Thick or double bands used a blurred version. Every route was checked by eye, and several were placed by hand instead (S0054, S0057, S0058/59, S0215, S0220, S0222, S0231, S0236, S0238). S0229 and S0239 were snapped onto the reference.
- Line ends and the vertices shared with other lines were kept. The exceptions:
  - The t_sw start moved to the R12_r30 border end (12288, 15438.5), so the two lines now meet.
  - The t_sw end moved along the border to 14518.6, which continues the drawn line straight. No other line uses that point.
  - The r85 start (a free end) moved onto its dash.
- Dash-gap bridges were left straight. S0226 was straightened.

## Doubts
- S0238 (r87): the diagonal crosses grey wash. The retrace follows a faint dark strip that shows on a contrast stretch. Low confidence.
- The town streets in Prokhorovka and Vyselki, judged as light lanes (S0047, S0049, S0064, S0066, S0067), are gaps. The builtup mask has holes there.
- The deletions S0063 and S0065 are judgement calls: an open light patch, and the edge of the water wash. vo_a now ends at (14524, 20316), which C3 reports as a new dangling end. It is outside the builtup mask, inside the town.
- S0237: I first moved it about 19 m S, then reverted. The darkness profile puts the old trace on the line, so it is a gap.
- S0052: a faint grey double line. The trace is about 6 m from the estimated centre.

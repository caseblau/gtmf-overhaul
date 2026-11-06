# Correction node B (R31, R21): notes

**Result:** 55 stretches. 19 fixed, 2 deleted, 34 gap.
- C1 (whole file, eval_roads.py out.json eval): 83.0 % before, 83.7 % after.
- C4: 0 illegal crossings.
- C3: 24 dangling ends, the same as in.json. The s_m1 dead end moved from (540,5596) to (600,5956).
- red_after: 51 stretches. Each one is covered by a `gap` verdict. 34 are the original gap stretches. The other 17 lie on lines I retraced that are still off the reference. These have their own entries, `red_after/Sxxxx` with `origin`, and crops `review/after_Sxxxx.png`.

**Why C1 barely moved.** Most fixed lines now sit on drawn symbols the reference does not contain: faint dashes, lettering, the W sheet frame, the brown-filled band and village lanes. Only S0160, S0186 and S0187 landed on the reference.

## Larger changes
- **main_s N end (S0068, S0069):** the old trace ran down the brown gully contour, then straight through the lettering 90 m E. The line now starts at the ko_street vertex (3500,13460). It follows the black line on the NW bank of the stream, then runs straight through the "Prokhorovka" lettering to (3168,12552). It no longer meets prokh_street at (3596,13317.5). That vertex stays in prokh_street.
- **t_e2 (S0168):** now runs on the brown-filled double band and ends on t51 at the existing vertex (4575.2,7569.2), not at (4609.3,7520.2).
- **klkh_path (S0076):** now starts at w_track (716,10076). It no longer doubles back along w_track.
- **p66 (S0174):** now starts at s80 (1872,6772).
- **t_lsw2 (S0172):** no longer duplicates t_lsw.
- **kz1 (S0073):** no longer duplicates kozl_s.
- Interior shared vertices were kept: main_s/g_lane (1978.4,9670.9) and r52/r54 (3850.3,9401.9).

## Doubts (the lead should check these first)
- **Village-lane gaps:** S0070, S0072, S0077, S0078 (Gryaznoye), S0154, S0155, S0156, S0163, after-S0161 and after-S0073. These count as gaps only because rule 2 treats the light lane as the street symbol. In S0072 the lane is about 200 m wide. A thin straight double line at x ≈ 1612 nearby may be the real road (possibly removed by the grid filter). I did not trace it.
- **S0165, S0167, S0180, S0164, S0170:** lines in contour-tinted or brown areas. They could be contours, not tracks.
- **S0075:** brownish dashes. They could be a half-interval contour, not a path.
- **S0069:** the line through the lettering is my best reading of where the road bends north under the letters.
- **The black line taken as main_s:** it could instead be the stream bank.

# Group A (R23): correction notes

## Results
- 55 stretches: 4 fixed, 2 deleted, 49 gap.
- 6 more gap entries (A-N1 to A-N6) cover red_after stretches that are new or were just under 60 m before. Each verdict in `verdicts.json` lists its `red_after` ids. All 53 red_after stretches have a gap verdict.
- C1 was 77.2 % on in.json and is 77.0 % on out.json.
- C4: 0 illegal crossings (2 at drawn crossings).
- C3: 10 dangling ends, the same as before. All are region-border ends, plus the existing ends of p_se_village and park_s2.

## What changed
- **band_rd (S0097 to S0106).** The road is a double line along the NW side of the railway. Measured outward from the railway, the profile is: railway band, light gap, black line, white strip, black line, paper. The reference has no double-line centre here, only the two edge lines. Most of the band_rd trace outside red.json runs on the SE edge line, 25 to 30 m from the centre. I moved the red stretches onto the centre of the white strip, so they stay red and get gap verdicts. Between the moved stretches and the untouched trace there are short taper jogs.
  **Lead decision needed:** either retrace the whole band_rd on the centre (it would then mostly fail C1, because the reference only has the edge lines), or accept the edge line.
- **252.2 junction (S0100).** The old trace cut across paper NW of the band. The new trace follows the band centre. The R23_okt end vertex (13033.5, 12753.5) moved to (13067.4, 12677.4), on the band centre. This creates a new 106 m red stretch on okt (A-N2).
- **r46 spikes (S0134, S0135).** r46 ran out about 65 m to the pv-street junctions and back. I removed the spikes and moved the junctions onto the r46 vertices (17643.8, 8737.5) and (17596.0, 8456.5), identically in pv_st1, pv_st5, pv_st2 and pv_st6. The street ends now cross the road band edge, giving new red stretches A-N4 to A-N6.
- **Deleted:** the first 260 m of pv_st4 (S0146). It ran across open paper, and the only line there is a brown contour. pv_st4 now starts at the junction of the drawn roads (17920, 9072). The road N of it is not traced; that is a C2 matter.
- **Deleted:** the pv_st5 hook west of r46 (S0147).
- **Retraced onto drawn dashes:** S0118 (lower dash to the Yamki road, in the lettering mask), S0128 (first dash) and S0136.
- **Dash gaps re-bridged straight between dash ends:** S0112, S0113, S0115 to S0117, S0129, S0130, S0137 to S0141 and S0148 to S0151.
- **Recentred on the bold straight track that the grid filter removed:** mts_pravorot S0121 and S0124.
- **Snapped onto the reference double-line centre:** r46 S0132 and S0133.

## Doubts (low-confidence gap verdicts, for the lead's spot check)
- **S0120:** the track runs under the МТС lettering and blue pencil for about 330 m. A short dark stroke about 50 m E of the trace might be the real continuation.
- **S0122:** the track jogs about 120 m at a horizontal seam where the vertical grid line also jogs, so it looks like a map-sheet join. I joined the two parts along the seam. S0132 (r46, fixed) crosses the same seam.
- **S0131:** r46 through the village east of the park. The trace runs along a house block's E edge, and the lane centre may be 30 to 60 m W.
- **S0149:** the dashed path turns NE across a 150 m gap with only faint dashes.
- **S0119, S0107 and S0108:** under pencil or in light lanes between blobs.
- **S0145, S0143 and S0144:** village lanes outside the mask.
- **S0110 and S0111:** railway crossings X1 and X3. The railway symbol is masked out of the reference.

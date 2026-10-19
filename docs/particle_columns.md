# Particle table columns, decoded (2026-10-15)

Source: a three-decoder / two-skeptic workflow over the pristine 3598 tables, the `adv_render` / `adv_game` code libraries
(disassembled) and the compiled particle shaders, cross-checked against the in-game A/Bs of 0.3.x-0.4.x. Confidence in
brackets; "code" = read from the disassembly, "data" = inferred from the tables. The decoder was stopped after nine skeptic
verdicts (all nine claims survived, several sharpened); the rest is unrefereed but code-backed where marked.

## The motion law (code, 0.9)

```
pos(t) = p0 + v0 * tau_v * (1 - exp(-t / tau_v)) + 0.5 * c6 * t^2   [+ wind * t for ADVW / ADWP / SCR rows]
tau_v  = c13.slot3 * lifetime          (launch velocity decays with this time constant)
size   = lerp(c9, c10, t'),  t' = 1 - (1 - t)^c22   (c22 <= 0.15 means linear)
alpha  = fade-in over c13.slot1 SECONDS, hard-coded fade-out over the last 30 % of life
colour = 4 keyframes at t = 0, 1/3, 2/3, 1 = (c11[1] or c11[0], c11[0], c12[1] or avg, c12[0])
life   = c13.slot0 * (1 +/- c14/2) * burst power * (wind factor 0.3..1 for smoke/dust types)
```

Consequence that explains the whole "beaded columns" episode: **launch travel = v0 * tau_v, and tau_v scales with
lifetime**. Lengthening burst smoke from 12 s to 24-48 s silently lengthened the launch decay from 1.8 s to 3.6-7.2 s, so a
35 m/s puff travelled 100-250 m instead of 60. Vanilla keeps smoke short for that reason. (The 0.4.7 test, where slot 3 = 1.2
gave tiny puffs, is not fully explained by the code reading; the life-size decoder read slot 3 as the size-growth end instead,
0.75 from that test. Treat slot 3 as "small = compact and fast-growing, large = far-flying", and keep it at the vanilla
0.15-0.2 on burst smoke.)

## parts_desc (27 columns, row format `$5uv5a2vf3u4bf2ubf`)

| col | meaning | notes |
|---|---|---|
| c0-c4 | name, shader, sprite set, diffuse, normal map | shaders: sh_smoke soft lit quad, sh_dust same constants, sh_dirt, sh_flash unlit, sh_*_3d meshes |
| c5 | constant 5 on every row | unknown, copy 5 |
| c6 | constant acceleration (x; y up; z) m/s² | code 0.95. Undamped 0.5·a·t². Clods -9.8, cores -5..-8, smoke ±0.01..0.15. ±0.3 on smoke is invisible before it fades |
| c7 | sprite UV cell (u; v; w; h) | never touch; winter moves u to 0.5 for snow sprites |
| c8 | UV inset (0.002; 0.002; -0.004; -0.004) | bleed guard, never edit (code 0.98, two skeptics) |
| c9 / c10 | start / end size m (2-vector; DEC rows x;0;z) | times (0.75..1.25) times expl c9.x |
| c11 | birth colours ARGB, 1-2 values | two values = keyframes t=0 and t=1/3, not a random pick (code 0.8) |
| c12 | end colours ARGB, 1-2 values | slot1 = keyframe at t=2/3, slot0 = death |
| c13 | (life s; fade-in s; spin tau fraction; velocity tau fraction) | code 0.9. Slot1 is SECONDS. The overhaul's "fade point" edits to slot1 only changed a 0.3-0.6 s swell-in |
| c14 | random-variation amplitude, clamped 0..0.75 | code 0.9, skeptics 0.93. Spreads lifetime ±A/2 and tint/alpha ±A. NOT a speed factor: the overhaul's 0.9-2.0 on thrown earth acted as 0.75 |
| c15 / c16 | flipbook fps / random start-frame span | only on the nine c21=1 rows (flames, impact puffs); inert on smoke and dust |
| c17 / c18 | sheet cells per row / rows | 4;1 on ordinary rows (four variants) |
| c19 / c20 | log2 strides of the sheet | leave |
| c21 | flipbook flag | 1 on SIM* rows only |
| c22 | ease-out exponent of the size/colour ramp | code 0.9. 5 = half the growth in 13 % of life; 0 = linear. NOT an animation rate |
| c23 | initial spin rate deg/s, decays with tau = c13.slot2·life | code 0.8; 360 → 40 removed the rotating-puff look (A/B) |
| c24 | draw/motion mode | ADV no wind; ADVW relaxes to wind; ADWP wind + ground clamp; ADVP ground bounce; SCR invisible line-of-sight volume; DEC decal; SIM* flipbook |
| c25 | 3D-mesh particle flag | 1 on sh_*_3d rows |
| c26 | ground-wetness gate, -1 none | code 0.8 + A/B: emission skipped when terrain wetness >= c26. Acts on wet ground, not rain only |

## pgens_desc (`$bufbf$b`)

| col | meaning |
|---|---|
| c1 | "Additional SFX" option gate (ext_* clods, fragments, crater dust, muzzle ground effects); not a ground flag |
| c2 | generator recipe, see below |
| c3 | emission duration s, -1 = one burst; with c3 > 0, c5 is particles per second and power decays as 1-(t/c3)^4 |
| c4 | 0 = continuous emitter owned by an object (exhaust, fires, wheels), 1 = one-shot at an event |
| c5 | particles per burst (c3 = -1) or per second |
| c6 | particle row |
| c7 | set only on the four looping flames |

Generator recipes (code 0.75-0.9): **BROB** velocity = (±U²·c10.x, U²·c10.y, ±U²·c10.z) of the burst, born one start-size
along it; **DIRE** fountain, vertical 0.5..1.12 × c10.y, random horizontal cone; **RND** ((2U-1)·x, U²·y, (2U-1)·z), born
0.5-3 m out; **EDIR/EDI0/EDI1/CAN/EOBJ/AIR** fragments: speed from expl c9.z times a cone, c10 ignored; **ECOR** core rises at
6 × size scale m/s; **SMK** fire smoke fixed 1.25-3.25 m/s up; **SMK0** uniform ball; **SMKG** smoke-pot drift scaled by size
and wind; **DUST/DIRT/BREA** scale the emitter's base velocity; **VEL1** inherits the shell's motion; **SCR/SCR2** screen
quad plus a light; **PLAN/PLAW** decals. The burst-dust generator (expl_desc c12) is created by the game with a **hard-coded
spread (5; 1.5; 5) and power = soil dustiness** (season soils c13: grass 0.85, marsh 1, black earth 0.5, clay 0.6, stone 0.1,
sand 0.2), which is why crater dust always stays a low skirt and why its amount differs per soil.

## expl_desc (`$9v3$2a`)

| col | meaning |
|---|---|
| c1-c8 | flash, smoke, spark, core, earth, extra, clods, screen generators |
| c9 | (size scale; power = lifetime/size factor; throw speed m/s for fragment generators) |
| c10 | launch velocity spread (x; up; z) m/s for BROB/DIRE/RND/SMK0/SPLE/SMKE rows |
| c11 | burst light: (radius m; duration s; height m; colour parameter) |
| c12 | dust-skirt generator (always RND in vanilla; hard-coded spread) |
| c13 / c14 | secondary water splashes: row, (radius m; probe count) |

expl_dect maps shell class × surface column to an expl_desc row; the surface classes come from the season `materials`
table. Seasons override particle rows by name through `parts_desc_<season_parts>` (`sum`, `wint`, `aut`); a `parts_desc_sum`
node would be a legal summer-only override. Weather reaches particles only through the engine wind (lifetime factor, ADVW
drift) and the c26 wetness gate; there is no per-weather table. The SCR rows (`scr_*`, `smk_screen*`) are the visibility
volumes and must be kept in step with the visible smoke when lifetimes or sizes change.

## What this changes for the overhaul

- The thrown-earth "speed factor" edits (c14 up to 2.0) were clamped to 0.75; the look comes from c6, c9/c10 and the expl
  c10 fountain. The c14 values should be set back to 0.75 or below (cosmetic, no visual change).
- `tools\vfx_changes.ps1` and README labels for c14 ("speed factor"), c22 ("animation rate") and c13 slot1 ("fade point")
  were wrong; corrected in the script, the changelog entries stand as history.
- Burst smoke lifetime must stay near vanilla (12-16 s) unless slot 3 is lowered in proportion (e.g. 0.15 × 12 s = 1.8 s of
  launch decay; at 24 s life use 0.075).
- Open single-variable tests the decoder suggested: `ext_dirt_sm` ADVP → ADV (clods sink into ground if P = contact);
  smoke_expl slot1 = 5 (should take 5 s to appear); canister c23 → 360 (spin vs cone).

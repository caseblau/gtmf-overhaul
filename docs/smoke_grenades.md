# White smoke grenades and pots: real behaviour, game data, possible changes (2026-10-15)

Research by two workflow agents (web sources listed at the end of `build\tp\smoke_real_world.txt`; game inventory in
`build\tp\smoke_game_rows.txt`); synthesis by hand after the workflow was stopped.

## Real-world reference (1943, Eastern Front)

| item | start-up | emission | cloud | colour / behaviour |
|---|---|---|---|---|
| Soviet RDG (RDG-1) hand grenade, ~0.5 kg, friction igniter | 5-15 s thin smoke before full output | 60-90 s | 25-30 m long, 5-8 m wide, 2-4 m high; lingers 30-120 s after | white to greyish-white, cool HC-type aerosol hugs the ground, drifts at wind speed |
| German Nebelhandgranate 39, 0.85 kg HC | 7 s delay, then near-full output | 100-120 s | 30-50 m per grenade | grey-white; "two must never be used together" because heat lifts the screen |
| German Nebelkerze 39 pot, 1.8 kg | 15-30 s | 4-7 min | 200-300 m screen 10-15 m high | grey-white |
| Soviet pots (BDSh-5 class, DM-11 placeholder) | 15-30 s | 5-10 min | 50-250 m | |
| WP grenades (US M15, British No. 77) | instant | ~60 s burn | pillar | brilliant white, hot, rises and shreds in tens of seconds |
| Mortar/gun smoke (oleum or WP bursting) | instant | one puff 10-20 m across | stands 1-2 min, must be refreshed | brilliant white |

Weather: steady 3-6 m/s wind ideal; above ~5 m/s the screen shreds; calm evening/night under an inversion pools it flat and
wide; sunny midday heating lifts and tears it; cold dry air gives a thin, fast-vanishing cloud; humidity thickens it. Five
or six grenades 5-10 m apart in a crosswind merge into one low wall 50-80 m long for ~2 min. From 500 m one grenade is a pale
smudge barely wider than a vehicle; from 1000 m only a merged bank shows.

## What the game does now (vanilla and merged are identical here)

Hand grenades ND_39, RDG, No. 79 and the pot SMK_MT all use VFX class **SMKL** → expl_desc `smkl` → one continuous
generator `smoke_longg` (type SMKG, 2 puffs/s for 110 s) → particle `smoke_longg`: born 0.3 m, grows to 10 m in ~7 s, lives
70 s, no vertical acceleration, drawn ADWP (wind + ground clamp), colour keyframes 0x60C0C0C0 → 0xFFF0F0F0 → 0xFFF0F0F0 → 0,
1 s fade-in, spin 120°/s, no wetness gate. Line-of-sight: `smk_screeng`, 0.2 volumes/s for 115 s, each 0.5 → 10 m over 40 s.
No flash, no fragments, no light. Visible cloud therefore ~180 s, pure white, 10 m balls, same for a Soviet grenade, a
German grenade and a smoke pot. In water: splash only, no smoke. Mortar and gun smoke (classes SMK / SMKB) are a burst of
20-25 puffs 7 → 15 m (10 → 22 m) living 140-160 s with an orange flash and 350 burning fragments (WP-like), one SCR volume
14/24 m for 120/150 s. The British 2-inch mortar smoke bomb is class SMKG and therefore emits GREEN smoke (vanilla mistake).

## Possible changes, ranked by visual effect

1. **Separate the grenade from the pot** (new VFX class the way RHE was added for rockets). Grenades: emission 110 s →
   RDG 80 s / Nb.Hgr.39 110 s, puffs 2/s → 3/s, cloud ~30-40 m. Pot SMK_MT: emission 300 s, 1 puff/s, bigger puffs, screen
   volumes to match. Rows: shells c22 (RDG, ND_39, NO79GR, SMK_MT), new expl_dect / expl_desc / pgens / parts / SCR rows.
2. **Ground-hugging shape**: puff end size 10 → 6 m (height 2-4 m), 3 puffs/s so the wall is continuous, c6 0 → -0.02
   (slight settle), keep ADWP. Match `smk_screeng` end size 10 → 7 m and emission to the new durations so the AI's
   line-of-sight blocking equals the picture.
3. **Build-up instead of instant wall**: fade-in (c13 slot1, seconds) 1 → 5 s and start size 0.3 → 0.8 m, so the first
   15 s are thin smoke as with a real igniter. (A true 7 s delay would need the shell fuze columns, untested.)
4. **Colour**: pure 0xF0F0F0 → grey-white with a faint warm cast (0xECEAE2), keyframes translucent → opaque → thinning →
   gone (0xA0E6E2DA, 0xF0ECEAE4, 0xC0E6E2DA, 0x00E0DED8) so edges are translucent and the cloud thins over its last third
   instead of popping.
5. **Persistence after emission**: puff life 70 → 55 s; the engine already shrinks smoke lifetime in strong wind
   (factor 0.3-1), which matches "shreds above 5 m/s".
6. **Winter/autumn**: a `parts_desc_wint` override of `smoke_longg` with life 55 → 40 s (cold dry air) via the same
   generator script as the autumn rows.
7. **Fix the 2-inch mortar smoke** (SBML_SMK) from SMKG (green) to SMKL or SMK.
8. **WP grenades / mortar smoke** are already instant bursts; leave the 350 burning fragments (that is WP), but the German
   oleum shells (Nbgr) share the same WP-style flash; a separate class without fragments would be more accurate (low impact).

Cannot be done from data: rain scavenging (no per-weather particle table; c26 gates on ground wetness, which also bites in dry
weather), convective lift at midday, merging of neighbouring clouds (puffs already overlap visually). One in-game test to run
first if this is built: the fade-in change alone (slot1 = 5), which also settles the slot1 = seconds reading for every smoke row.

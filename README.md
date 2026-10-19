# MF Overhaul for Graviteam Tactics: Mius-Front

Data-only overhaul for game 6.00 build 3598: 1943 squads and weapons, corrected orders of battle, coherent quick-battle pools,
and a balanced *Duel* ruleset built for online play through [MiusPlayer](https://github.com/VampyrCat/MiusPlayer).
Hot-seat co-op and play-by-save campaigns are the offline fallbacks.

See [DESIGN.md](DESIGN.md) for the design and [docs/miusplayer_compat.md](docs/miusplayer_compat.md) for the multiplayer rules.

## Install (players)
1. Download `mfo_<version>.gt3ext`.
2. Drop it into `new_updates\` in the game root, or double-click it.
3. Start the game, click the *Version:* label top-right of the main menu, confirm the add-on is listed.

## Required third-party content
These are not inside the overhaul package (no redistribution permission yet). Install them from the authors' own links first:
1. **Realistic Battlefield VFX Part 1 and Part 2** by Toni (Steam discussion 596286707636141131). Part 1 is textures, Part 2 is the configs; you need both.
   `T-D-Battlefield-SFX-Mod_V250919.gt3ext` is the same file as Part 1 under its old name. Do not install both.
2. **Achtung Panzer Ostfront Mius DataBase** by night_postman (Steam discussion 1642041106353358037), 1.2 GB of soldier models and textures.
   Do **not** install `Achtung_Panzer_Ostfront_Mius_Configs.gt3ext` with the overhaul: it is a 2021 table snapshot that removes current-game content. The overhaul's M9 module replaces it.

Why and what collides: [docs/third_party.md](docs/third_party.md).

## Multiplayer (MiusPlayer)
Both players need the same game build, the same MiusPlayer version and the same MF Overhaul version.
The game will not warn you if they differ; the battles will just come out different on each PC.
Install MiusPlayer per its README (copy `mpmod1`, run `Enable_Multiplayer.bat`). Order relative to the overhaul does not matter.

**Install the overhaul last, after every other add-on.** When two add-ons carry the same entry, the one registered first in
`paths.cfgpack` wins, and the game's updater puts the newest install first (verified 2026-10-15). Reinstalling the overhaul moves it
back to the top; reinstalling any dependency after it would put that dependency on top instead.
In the lobby, pick a Duel pair and check both players see the same `[MFO x.y]` tag.

## Build (modders)
Requirements: Mius-Front 6.00 build 3598 installed, Windows PowerShell 5.1 (ships with Windows), `GTMF_ROOT` set to the game root
(the folder with `starter_x64.exe`). No game tools are needed: this build has no `unflat`/`mkflat`, so `tools\gt3.ps1` reads and
writes the archives itself (see `docs/toolchain.md`).

```bat
set GTMF_ROOT=C:\Program Files (x86)\Steam\steamapps\common\Graviteam Tactics Mius-Front
tools\build.cmd list   "%GTMF_ROOT%\data\common\shared\packed_data\tabs_oprum.flatdata"
tools\build.cmd unpack "%GTMF_ROOT%\data\common\shared\packed_data\tabs_oprum.flatdata" "%GTMF_ROOT%\users\modwork\tabs_oprum"
tools\build.cmd install
```

`install` merges every entry from its modules' whole files and row deltas (vanilla → m8 → m9 → m1 → m2 → m3, so it needs
`GTMF_ROOT` for the pristine tables in `users\modwork\_orig\3598`), packs the archives into `build\mfo_overhaul_<version>.gt3ext`
and copies it into `new_updates\`; start the game once and the updater installs it. `tools\check_conflicts.ps1` runs first and fails
if two modules ship the same entry whole, or any MiusPlayer-owned file. Details: `docs\toolchain.md` 7.

## Modules
| Folder | Content | Ships by default |
|---|---|---|
| `src\m1_core` | squads, weapons, ammunition | yes |
| `src\m2_oob` | campaign orders of battle, FO teams, signals | yes |
| `src\m3_quickbattle` | quick-battle pools, Duel pools | yes |
| `src\m6_sound` | sound replacements | optional |
| `src\m7_textures_loc` | textures, English strings | yes |
| `src\m8_vfx` | Realistic Battlefield VFX (Toni) as the base for effect tables | dependency until permission |
| `src\m9_ap_port` | Achtung Panzer soldier-model bindings ported onto 6.00 tables | yes, needs night_postman's OK to publish |

## Changelog
- 0.5.13 (2026-10-16): user: "remove artillery batteries from BG if their own FO is already in said battlegroup".
  Stepanovka: when a rifle battle group's scout slot gets a battery's FO team, that battery leaves the group's SUP
  slot and stays in reserve (it fires through the FO; the freed slot is filled from the regiment as before). The 1st,
  2nd and 3rd batteries of 1012 AR, the 84/90/234 Gds AR and 294/128 AR batteries the old file had attached to rifle
  groups are affected. Saur-Mogila was already like that (FO teams in the groups, batteries in reserve).
  Also in 0.5.13: Stepanovka, user: "move 2 tank coy, 2 tank platoon to 2/22 det gds TR in place of 4 tank coy, 1 tank
  platoon and move it to reserve" (done; 1/22's freed slot stays empty, the 1st company has no spare platoon).
  Saur-Mogila, user: "move 3/105 BG to the white X mark on the map", "move 3/103 to the white X mark": 3/105 starts on
  the node between 1/105 and 2/105 (cell 3;5 south), 3/103 on the node between 1/103 and 2/103 (cell 2;5 south-east);
  until now both stood in the regiment HQ cell behind the line.
- 0.5.12 (2026-10-16): **confirmed in game by the user ("Checked, works").** User: "corresponding FO and their batteries are in different BGs, move either one as
  reinforcements". Stepanovka: a rifle battle group that holds an artillery-regiment battery (the 17 July file attaches
  the 1st-3rd batteries to the 362/1328/724 RR groups) now gets that battery's own FO team in its scout slot, and a
  group without a battery gets an FO whose battery sits in reserve, so no FO is separated from its guns by another
  group. Saur-Mogila already had that (its battery FOs sit with the groups, the batteries in reserve).
- 0.5.11 (2026-10-16): user, on the 0.5.10 1012 AR panel (regiment HQ now WAITING, every battery with FO and guns):
  "they lack commander". Every artillery-regiment battery that has an FO team and a gun platoon but no battery
  command gets one (COMC, battery command squad + phone + observer, the 30 July 4th-battery pattern, code = battery
  group), so each battery reads Command / FO / Arty plt like the 4th and 6th did. Both operations.
- 0.5.10 (2026-10-16): user: "some artillery batteries lack their FO; FO lacks guns" (panel: number of guns 0 (4)),
  and "make 293 RR in Saur-Mogila have two battle groups, 1st and 2nd battalion with companies 1-3 and 4-6 and their
  organic regimental and battalion support units". From the saves: an FO team's gun count is the number of guns of its
  type in the gun platoons of its own company group (code & 0xFF0) in its formation; FO-only batteries (30 July
  pattern: 1012 AR 1st-3rd, 5th, 9th; 84 AR 1st-6th; German 6.-9.) and the regimental 120 mm mortar FOs therefore had
  none. Both operations now complete every battery: an FO without guns gets a two-gun platoon of its calibre in its
  group (or moves into the group that already holds its guns, e.g. the regimental 76 mm FO to the gun battery), and
  every indirect-fire gun platoon without an FO gets one (anti-tank units excluded). 293 Gds RR in Saur-Mogila is now
  the full 30 July regiment (HQ, three battalions, two battle groups for 1st and 2nd bn, regimental and battalion
  support) placed where the old regiment stood; its reserve-pool platoons of 0.5.8 are superseded.
- 0.5.9 (2026-10-16): user: "in Stepanowka 17 July the artillery regiments are not accessible to the divisions they
  are supposed to be attached to". A battle group can only draw units from the formations named in its `pool`,
  `pool2`, `pool3`, `pool4` fields; 30 July groups list regiment / division / artillery regiment / attachment, the
  17 July groups listed only one attachment (8 or 15 iptabr), so the new regiments' FO teams and batteries were out of
  reach of the "+" buttons. Every 17 July battle group now links its division and its artillery regiment first and
  keeps the old attachment after them (104 groups changed per side). Saur-Mogila already had the links.
- 0.5.8 (2026-10-16): **confirmed in game by the user ("Checked, works").** Saur-Mogila follow-ups from the user's deployment-phase check of 0.5.7. (1) 306 ID Marder
  company and 210 StuG battery split into command + two platoons (the Marder group now has COM = company command and
  two SUPM slots; the StuG command and 2nd platoon stand next to the battery). (2) The reserve guns, MGs and mortars of
  every German formation (Pak 38 + Pak 97/38, 2 x Pak 184/1(r), 2 x MG 42, 2 x leIG 18, 2 x GrW 34) are platoons now,
  the IG and mortar platoons with an FO team each (35 platoons), so battle groups can take them. (3) 103 and 105 Gds RR
  get a third battle group (3rd bn, 7th coy) in the regiment HQ cell. (4) 293 Gds RR: its reserve pool (two artillery
  spotters, 2 x 45 mm, 76 mm regimental gun, 2 x 82 mm, 2 x Maxim, 2 SMG squads) became FO 120 mm, FO 76 mm, ATG,
  gun, mortar (+ FO), MG and SMG platoons shaped like the 30 July 103 Gds RR ones. (5) 140 STBde: both tank companies,
  SMG coy, ATR coy, mortar battery (+ FO) and AA MG coy split into command + platoons; the T-3 pair, the SdKfz 250 and
  six motor-rifle squads became platoons (T-20 tractor stays in reserve); the brigade group has COM = 1st tank coy
  command, APC recon, two tank slots, two SMG slots, AA MG and mortars. 460 platoons per side.
- 0.5.7 (2026-10-16): **confirmed in game by the user ("Checked, works": Saur-Mogila starts).** User: "Saur-Mogila still crashes with 0.5.6". Disassembled the crashing function
  (`adv_opgame.codelib` 0x180036d60): for every map node within one cell of a position it reads the node's occupant id
  (`mg_nodes` column 2, element 0), searches the platoon array for that uid and indexes with the result without
  checking for -1. In every vanilla file that column mirrors `plat_pos` exactly (uid of the unit on the node, -1 when
  empty); the generated files never touched it, so Saur-Mogila nodes still named the removed 105 Gds RR units and the
  new HQ/battle-group placements were missing there. Both generators now rebuild the column from `plat_pos` (also for
  the 17 July regiment HQs, which the engine had probably not placed at all in 0.5.3-0.5.6). Node-sharing and HQ-less
  battle groups (0.5.5/0.5.6) stay fixed as they are.
- 0.5.6 (2026-10-16): user: "Saur-Mogila still crashes with 0.5.5". Minidump read with a small parser
  (`scratchpad\minidump.ps1`): access violation in `adv_opgame.codelib+0x36e34`, registers rcx = 399 (the platoon count)
  and rax = -1, i.e. a failed lookup used as an index while scanning the platoons. The only structural novelty left in
  the file was battle groups in formations that have no HQ node (60 Gds TPP, 210 StuG bn, 335 ID); every vanilla battle
  group's formation has one. Those three groups are dropped and the units keep their single placements (10 battle
  groups per side remain). Everything else as 0.5.5.
- 0.5.5 (2026-10-16): user: "the game crashes when clicking on saur-mogila operation" (0.5.4; crash report 13:38,
  the engine had already written the new operation's save with all battle groups placed). Cause found by comparing
  with vanilla: no vanilla operation ever puts two units on one map node, while 0.5.4 put the 34 Gds RD HQ, the 84 AR
  HQ and the 105 RR HQ on node 95, and 0.5.3 put every new artillery-regiment HQ on its anchor HQ's node (nine shared
  nodes per side in Stepanovka). Both generators now give every placed unit its own node (a free node linked to the
  wanted one in the same map cell, else any free node of the cell, else a linked node next door) and a unit put into a
  battle-group slot loses its own placement (9 iptabr 1st battery was both IN BG and on the map). Nothing else changed.
- 0.5.4 (2026-10-16): **M2, second operation.** User: "Saur-Mogila tumulus operational campaign upgrade from old OOB
  without BG to operational campaign with battlegroup system, copy OOB from July 30 campaign for 34th guards rifle
  division." `08_28_Saur_RUS/GER` (28 August 1943, 2015 format: 118 platoons placed one by one, no battle groups) now
  uses the battle-group system: the 34th Guards Rifle Division is the 30 July one (division HQ and troops, 103/105/107
  Gds RR with two battle groups each, 84 Gds AR; 305 platoons copied verbatim, old 37 removed), placed where the old
  file had the regiments; every other formation's placed companies became battle groups (13 per side: 293 Gds RR,
  60 Gds TPP, 7 Gds OTPP, 140 STBde; 306 ID, 581/570 IR, 210 StuG, 294 ID, 514 IR, 335 ID); current-format flags set.
  Generator `tools\oob_saur.ps1`, reasoning and deviations in `docs\oob_saur_mogila.md`. (The parent session asked for
  this as 0.5.3; 0.5.3 had already been taken by the Stepanovka HQ-placement fix below, so this is 0.5.4.)
- 0.5.3 (2026-10-16): user, after checking 0.5.2 in game (1012 AR panel: regiment HQ without a map state, the three
  old division batteries listed under "Command"): "create the regimental HQ on the operational map and check the OOB
  again; look up the divisions' artillery support". Found how the engine places units: the `plat_pos` table of the
  operation (one row per platoon: uid, map cell, map node, arrival turn); a formation whose HQ has no map node never
  becomes available (its platoons sit in state 11, blank in the panel). The nine new artillery-regiment HQs now get a
  placement row: with the division HQ where the division has one on the map (German side), else with the first
  regiment HQ of the division, same arrival turn (234 Gds AR arrives with 291 Gds RR on turn 6, 128 AR with 23 PzD on
  turn 9/10). Every new platoon gets a reserve row. The 17 July division batteries moved into the regiments are now the
  gun platoons of batteries 1-3 (codes and 30 July names "1 battery, 1 Arty plt (76 mm)", "2./294 AR, 1 arty plt
  (105 mm)") and each new regiment lists HQ first, then battery by battery. Historical check of the artillery
  attachments in `docs\oob_stepanowka_17jul.md` section 9.
- 0.5.2 (2026-10-16): **confirmed in game by the user ("new upgrade works")**. User: "remove MFO rifle squad name; add scout or FO slot to battle groups; create AR regimental HQ
  and its own artillery and FO; remove FO addition from OP for BG; split tank companies into platoons and add one slot to
  tank battle groups; mimic the 30 July campaign for the AR and its FOs". The "MFO Riflemen (e.1943)" test name is gone
  (m7 entry reverted to vanilla bytes). Battle-group slots now follow the 30 July pattern: the first battle group of a
  rifle regiment carries the FO team of a division artillery battery, the next one the regiment's own FO (76 mm guns,
  120 mm or battalion mortars) or recon; armour battle groups carry a recon platoon or nothing (no FO teams pushed into
  tank battle groups any more); a battle group holding a split tank company gets a third STR slot so all three platoons
  of the company deploy together. Artillery regiments and tank company splits as in 0.5.1.
- 0.5.1 (2026-10-16): user on 0.5.0: "no scout or FO in companies; tank companies should be split into platoons like
  the 30 July campaign; no artillery regiments and their FO; divisions have their own organic artillery, list it like
  30 July". Three more generator passes: (1) the division artillery regiments are now formations of their own under the
  division, with HQ, FO teams per battery and gun batteries (1012 AR, 84/90/234 Gds AR; 294, 146, 128 AR; 306 and 302 AR
  cloned from 294 AR), and the batteries the 17 July file had attached to rifle regiments are moved into them;
  (2) every tank/SPG company that was one platoon of 7-14 vehicles is split into a company command tank and platoons of
  3 (German 4-5) vehicles, 35 companies per side, vehicle counts unchanged; (3) every battle group gets a SCT slot
  holding an artillery FO team (rifle battle groups) or a recon platoon (armour), and empty STR/UNI/SUP slots are filled
  from the same battalion (81 slots per side). Per side: 990 platoons added, 9 formations added, 1 940 platoons.
- 0.5.0 (2026-10-16): **M2 milestone: the OOB of "Stepanovka-Marinovka, 17 July 1943" brought to the standard of
  "Stepanovka, 30 July 1943".** The game plays the `07_17_Stepanovka_NA_*` operation files (the current-format rebuild; the
  user's saves name them), so those are overridden: per side 935 platoons added to the formations' reserves and 174 compositions
  changed, generated by `tools\oob_17jul.ps1` from the 30 July structures (regimental sapper/recon/SMG/ATR/AT/gun companies,
  battalion FO teams, company mortar and MG platoons, MG and mortar companies, third battalions, German 13th/14th/MG and heavy
  companies, division recon/sapper/AT battalion companies and artillery FO teams spread over the regiments on the map). HQ and
  battle-group nodes, scripted arrival turns, tank/SPG counts and the 17 July strengths are kept; nothing from formations that
  were not in the sector on 17 July. Unit-by-unit list and historical reasoning: `docs\oob_stepanowka_17jul.md`; platoon list:
  `docs\oob_stepanowka_17jul_changes.md`. New pipeline: `src\<module>\camps\<chapter>\<op>\` ships an operation pack
  (`core\shared\camps\<chapter>\<op>.campack2`, the DLC layout); `gt3.ps1` gained `lib` (dot-source), a fix of the AZCF
  writer's kid index (an identity-hash collision on 3 600-node tables wrote one wrong kid pointer) and cp1251 node names;
  the fingerprint now covers the operation packs. **To check in game:** the 17 July operation listed once per side (if twice,
  say so), the new reserves in the deployment screen (section 6 of the doc), arrival turns as before.
- (open, 2026-10-15) user: "during rain, dust and smoke should be tuned down". Findings: the particle table has season variants
  (`parts_desc_wint`, `parts_desc_aut` override rows by name) but no weather variant. Weather lives in each season table's `weather`
  node (rows clear/cloudy/fog/rain/snow…, c14 precipitation type, c15 intensity, c16 wind) and the season `common` node has
  `wet_dirt` (0.17 summer, 0.12 winter); the renderer gets `v_wet`, `v_rain_time`, `v_dust`, `v_dust_color` as shader constants
  (`basic_game.codelib`), so wetness is a global engine value, not a table. The only per-particle candidate is `parts_desc` c26:
  -1 on smoke and flashes, 0.5 on burst dust, wheel dirt/water and burning fragments, 0.2–0.7 on clods. Its meaning is unverified
  (a wetness gate fits dust and burning fragments but not wheel mud at 0.5), so an A/B in a rain battle is needed first.
- (docs, 2026-10-16) `docs\mp_operations.md`: inventory of all 58 operations on this install (base `oprum`, 17 `ma_*` packs,
  12 `addons\*` packs); every one has both sides' campack2 files, which is MiusPlayer's requirement for the joiner's own map view.
  Three have been played over MiusPlayer by its author (Odintsov, Saur-Mogila, Peleshi); the rest are file-checked only.
  `docs\ai_smoke_investigation.md` (side session): the AI smoke-throw decision uses code constants only; no data setting exists.
- 0.4.16 (2026-10-16): user on 0.4.15: "the wall build-up is good; squads throw 1-2 grenades but then have none left; they need
  the standard quantity and should not throw them all at once". The allotment delta is retired (`retired\smoke_allotment_0.4.15\`,
  `ammo_hum` removed from the m1_core `!flatlist`), so counts are vanilla again. No data lever exists for the throw rate: the
  hand smoke grenades fire through the same `GREN_TR` weapon row as HE grenades (no smoke-only timing), the data holds no AI
  smoke-use parameter, and the decision to throw lives in `adv_game`. In game the platoon/squad "smoke" order (in_pl_smk /
  in_sq_smk) is the player's control over it. The 0.4.15 wall build-up stays.
- 0.4.15 (2026-10-15): user on 0.4.14: "still too fast from throw to full wall; a squad of 10 men each throws multiple smoke
  grenades, 2-4 are enough". (a) `75_smoke4.delta`: 2 puffs/s (pot 1), fade-in 12 s (pot 15), size ease-out 0.8, life 85 s (pot
  110): thin at 5-10 s, full wall at 20-30 s; winter rows matched. (b) New table `ammo_hum` in m1_core (`!flatlist` + delta, 65 rows):
  smoke grenades per soldier class, vanilla 1943 = 1 per rifleman and 2 per SMG man / leader → riflemen, AT, MG and mortar crews 0,
  SMG men, leaders (pistol classes) and sappers 1, for all four supply levels; Soviet RDG, German ND_39, British No. 79, US M15/M16.
  Vehicle smoke-grenade stocks (ammo.config: T-34 12 RDG, Pz III 5-6 pots …) untouched. The AI's decision to throw is engine-side.
- 0.4.14 (2026-10-15): user on 0.4.13: "still small; from throw to full cloud is too fast". `sfx…09_smoke2.delta`: smoke class
  launch spread 1;1;1 → 3;0.3;3 (pot 4;0.3;4) so puffs pool outward in calm air instead of all being born at the can.
  `74_smoke3.delta`: fade-in 8 s (pot 10), size ease-out 3 → 1.5 (puffs swell over more of their life), end 12 m (pot 15),
  start 1 m; screens 12 / 15 m; winter rows matched.
- 0.4.13 (2026-10-15): user on 0.4.12: "without wind the smoke cloud is small". `73_smoke2.delta`: grenade puffs 6 → 9 m (pot
  12 m), start 1.5 m, life 70 s (pot 90), drift time constant 0.1 → 0.3 so puffs carry further from the can in calm air, 4 puffs/s
  (pot 1.5); screen volumes 9 / 12 m; winter rows matched (50/50/70 s).
- 0.4.12 (2026-10-15): smoke-grenade pass (`docs\smoke_grenades.md`), after the user confirmed the 5 s fade-in at 0.4.11.
  Three classes instead of one: SMKL (German Nb.Hgr.39, British No. 79, now also the British 2-inch mortar smoke) 3 puffs/s for
  110 s; new SMKS (Soviet RDG) 3/s for 80 s; new SMPT (smoke pot SMK_MT) 1.2/s for 300 s with bigger puffs (1 → 9 m, 70 s).
  Grenade puff `smoke_longg`: 0.8 → 6 m (a 2-4 m wall, not 10 m balls), settle -0.02, 55 s, 5 s fade-in, keyframes translucent →
  opaque grey-white (0xECEAE4) → thinning → gone. Screen (SCR) volumes follow each class (7 m / 7 m / 9 m, emission matched).
  Winter override rows: life 40/40/55 s. Deltas: parts `72_smoke`, sfx `08_smoke` (expl_dect SMKS/SMPT, expl_desc smkls/smkpt),
  m1_core `03_smoke` (shells c22: RDG → SMKS, SMK_MT → SMPT, SBML_SMK SMKG → SMKL). Test delta 71 removed.
- 0.4.11 (2026-10-15): SINGLE-VARIABLE TEST for the smoke-grenade pass. `71_smoke_test.delta`: `smoke_longg` (every hand smoke
  grenade and smoke pot) c13 slot 1 → 5 (decoder: fade-in in seconds; vanilla 1). Smoke taking ~5 s to come up confirms it.
- (docs, 2026-10-15) Two workflows run and stopped on request. Column decoder (three decoders, nine skeptic verdicts, all
  survived) → `docs\particle_columns.md`: the motion law from the `adv_render` disassembly; launch travel = v0 × c13.slot3 ×
  lifetime (why long-lived burst smoke strung out into columns); c14 is a variation amplitude clamped at 0.75, not a speed
  (the earth's 0.9-2.0 settings acted as 0.75); c22 is an ease-out exponent, not an animation rate; c13 slot1 is fade-in in
  seconds; crater dust has a hard-coded spread (5;1.5;5) and soil-dependent power; pgens c1 is the "Additional SFX" option gate.
  Smoke-grenade research (real-world figures with sources + full game inventory) → `docs\smoke_grenades.md` with eight ranked
  possible changes; nothing built. `tools\vfx_changes.ps1` labels corrected. No build in this entry; 0.4.10 remains installed.
- 0.4.10 (2026-10-15): user screenshots of 28 cm and 150 mm on 0.4.9: both dense masses; the 28 cm pillars stood ~4× the 150 mm
  columns, while ~8× the HE gives ~2× the column height (cube-root scaling). `70_realism66.delta`: heavy row life 16 → 13 s, end
  20 → 18 m, alpha 0xB0; medium row life 14 → 16 s, end 18 → 22 m, 52 puffs.
  User screenshots on 0.4.10 (150 mm and 28 cm side by side): dense single masses, ~30 m and ~60 m. Burst baseline from here.
  Confirmed by the user: "Keep 0.4.10 as the explosion baseline." Summer-map screenshots match the autumn ones (same proportions,
  tan dust skirt, muzzle smoke from firing guns visible as small white patches).
- 0.4.9 (2026-10-15): user screenshot of 150 mm bursts on 0.4.8: thin, faint 40 m wisps next to the dense 28 cm pillars.
  `69_realism65.delta`: medium row (152 mm) 30 → 48 puffs, end 15 → 18 m, alpha 0xC0 → 0xF0; small row (105-122 mm, mortars, 76 mm)
  24 → 32 puffs, end 10 → 12 m, alpha 0xE0. Heavy row unchanged (reference).
- 0.4.8 (2026-10-15): test result, user: "they are tiny" → c13 slot 3 is the size-growth fraction (confirmed), and the columns
  still rose 100 m+ with tiny puffs, so the burst smoke rises on its own whatever the launch spread, speed factor or pull-down:
  the BROB generator sends its puffs up, and vanilla hides that with a 12-15 s life. `68_realism64.delta`: burst smoke lives like
  vanilla (12/14/16 s, fade from 0.4), 24/30/40 puffs 1/1.5/2 → 10/15/20 m, growth 0.15/0.2 restored, two tints, animation 5; the long
  persistence stays with the low dust skirt (26/34/40 s). Launch deltas 06/07 and the damping test moved to
  `retired\launch_tests_0.4.5-0.4.7\` (vanilla launch again).
  Bug found: the user's maps are autumn, and the `parts_desc_aut` rows generated in 0.4.0 froze that build's dust and column values
  (big 0.3.56-style dust puffs), so no later dust change applied on autumn maps. `tools\gen_autumn.ps1` now regenerates the rows from
  the current merged summer rows (colours only differ); run it after every summer dust/earth/column change, then build.
  User screenshot on 0.4.8: dense dark 60-80 m pillars with no separate balls, identified by the user as 28 cm rocket (RHE) bursts;
  plausible for 50 kg HE. Reference look for the heavy tier; 152 mm (medium row) and 105-122 mm (small row) scale down from it.
- 0.4.7 (2026-10-15): SINGLE-VARIABLE TEST. User screenshot on 0.4.6: columns got taller and denser (80-100 m) with the launch cut
  to 15 %, so the rise is not the launch velocity. The other cell 0.4.6 changed on the smoke rows was c13 slot 3 (0.15 → 0.06); if it is
  velocity damping rather than size growth, lowering it let the puffs keep climbing. `68_test_damping.delta`: slot 3 → 1.2 on the three
  burst-smoke rows, nothing else. Compact low cloud → damping; tiny puffs that never grow → growth fraction.
- 0.4.6 (2026-10-15, interim): user screenshot on 0.4.5: "still spheres thrown into the air" (a lower cloud, but discrete balls
  flying apart). Puffs separate faster than they grow. `sfx…07_launch2.delta`: launch spread of every soil row 15 % up and 60 %
  sideways of vanilla (UHE 6;35;6 → 3.6;5.3;3.6). `67_realism63.delta`: puffs reach full size early (c13 slot3 → 0.06, hypothesis:
  fraction of life at which end size is reached) and 36/44/56 of them. A column-decoding workflow (three decoders, two skeptics per
  claim, synthesis) is running to replace these guesses with verified semantics; its result goes to `docs\tables.md`.
- 0.4.5 (2026-10-15): diagnostic result, user: "they are gone" → the columns are the burst smoke, and 0.4.3 showed neither the
  particle speed factor nor the pull-down tames them, so the launch comes from sfx `expl_desc` c10 (x;up;z velocity spread).
  `sfx…06_launch.delta`: up component of every `dirt_*` soil row cut to 40 % (UHE 35 → 14, BOMB 40 → 16, LHE 20 → 8, …), x/z kept.
  `66_realism62.delta`: burst smoke back to a drifting cloud (c6 -0.1, c14 0.25, life 22/28/34 s); thrown earth and clods get
  speed factor 2/1.9/1.8 (clods 1.8) in case the earth shares the launch spread. Diagnostic delta removed.
- 0.4.4 (2026-10-15): DIAGNOSTIC. The beaded columns survived 0.4.3 (new screenshot over a pine forest, columns 100 m+ of fully
  opaque spheres). `66_diag_smoke_off.delta` makes the three burst-smoke rows fully transparent so one battle tells which row
  makes the columns. To be removed once known.
- 0.4.3 (2026-10-15): user screenshot: tall beaded columns of grey spheres far above the trees. Those are the burning-vehicle and
  fire smoke rows, which 0.4.0 made buoyant; over a 60-130 s life that lifts each puff hundreds of metres and strings the steady
  emission into separate balls. `64_realism60.delta`: vertical accel back to vanilla for `smoke`, `smoke_sm`, `choke`,
  `smoke_burn`, `smoke_filler`, `smoke_mid`, `smoke_fuel`, `fuel_smoke`, `smoke_fbomb`, `smoke_flam`; emission doubled
  (`smoke_burn` 1 → 2, `smoke` 3 → 5, `smoke_big` 5 → 8, `smoke_mid` 3 → 5) so the plume is continuous; spin 30. Sooty palette kept.
  User then: the columns come from artillery bursts. Found: sfx `expl_desc` c10 (x;up;z, e.g. 6;35;6 for UHE) is the burst's launch
  velocity and `parts_desc` c14 scales it; with 24-48 s lifetimes and only -0.1 pull-down every smoke puff kept climbing (~9 m/s for
  30 s). `65_realism61.delta`: burst smoke launch factor 0.25 → 0.1, pull-down -0.1 → -0.25 (rise stops at ~14 s, ~25 m), life
  18/22/26 s. Dust unchanged (its skirt stayed low in the screenshot).
- 0.4.2 (2026-10-15): user on 0.4.1: "still spherical". A puff that grows to 18-38 m is a ball whatever its animation, so
  `63_realism59.delta` returns to the vanilla structure: many small puffs that overlap into a cloud, kept low by the vanilla
  pull-down (-0.1): burst smoke 24/30/40 puffs 1/1.5/2 → 9/14/18 m with two birth tints, sideways 0.25, animation 5; burst dust
  20/28/24 puffs 1.5/2/2 → 10/16/16 m, two tints, animation 4. Longer lifetimes and palette kept. The screenshot's spheres sat above
  the treeline where tree-burst and airburst smoke lives, so `smoke_hit*` / `smoke_air*` / `smoke_gray*` get the same treatment
  (more, smaller puffs, rise back to the vanilla +0.01, spin 30).
- 0.4.1 (2026-10-15): user screenshot: burst smoke "is spherical instead of fluid" (separate grey balls above the treeline).
  Cause: each puff was one big (3-6 m at birth), slowly animated sprite (c22 1.2-1.5 against vanilla 5) with little overlap. The
  smoke and dust textures are animated flipbooks, so the animation rate is what makes them boil. `62_realism58.delta`: animation
  4.5 (bomb 3.5, dust 3), puffs born small and growing (smoke 1.5/2.5/3 → 18/28/38 m, dust 2/3/3 → 20/30/30 m), more of them at
  alpha 0xB0 so they merge (smoke 14/16/22, dust 12/16/14), sideways 0.2/0.22. Lifetimes, fades, colours, vertical motion as 0.4.0.
- 0.4.0 (2026-10-15): user: "make everything realistic in colour palette and physics, no shortcuts". `60_realism57.delta` (50 rows)
  applies one rule set to every particle family the overhaul had not touched: solids under real gravity (wheel mud, muzzle dirt,
  debris, branches, fuel drops at -9.8; leaves -2, hay -1.5) in the soil palette; dust (vehicle, muzzle, building collapse) drifts
  with the wind, settles at -0.02/-0.03, spins 40° and takes the lightened field/mud tone 0xA89C7E; hot smoke is buoyant and sooty
  (burning vehicles +0.12 near-black brown, burning fuel +0.15/+0.3 oily black, incendiaries +0.2, HE on steel +0.04 dark grey, the
  long burn plume +0.05/+0.08), spin 360° → 60° everywhere; water spray under gravity, water columns -5. Flashes, exhaust and the
  burst rows of 0.3.57-0.3.59 unchanged. `61_autumn.delta` adds 12 `parts_desc_aut` override rows generated from the summer rows:
  wet-ground palette (dust 0x887C64 thinner and 12-26 s, earth/clods/column 0x3A3226 / 0x40382A / 0x403A30). Winter keeps the
  vanilla white `parts_desc_wint` rows. The soils c6 palette is identical across seasons, so seasonal looks come only from these
  override tables. Version bumped to 0.4.0 for the breadth of the pass.
- 0.3.59 (2026-10-15): user: "as close as possible to real-life explosions, and take the ground colour palette into account for
  the dust". Palette read from `season_ua_summer.soils` c6 (0x00RRGGBB): black earth 0x4C4D41, clay 0x4E4332, mud/trench 0x8D7D63,
  field/dry grass 0x9F946F, grass 0x869352, sand 0x828453. `58_realism55.delta`: burst dust 0xD0A89C7E (lightened field/mud tone);
  column 0xFF4C4638 (black earth) with a tighter, faster rise (end 26;52 / 56;96, speed 0.65 / 0.5); thrown earth 0xFF463E30 and
  0xFF4E4634 (clay / black earth), clods 0xFF4A4234; burst smoke 0xE0584E44. User: "realism at its highest" → `59_realism56.delta`:
  thrown earth and clods under real gravity (-9.8), launched harder (0.9/0.85/0.8, clods 0.8) and gone in 3-4 s like real debris.
  Column, smoke, dust and flash timings as 0.3.58. The autumn/winter
  palettes are different and untouched (their `parts_desc_aut` / `parts_desc_wint` rows still override by name).
- 0.3.58 (2026-10-15): user sent howitzer-impact footage (youtube --JmEF446fE) as the reference. Real impacts on dry ground: one
  dark earth-grey column that shoots up and mushrooms, clods arcing for 2-3 s, the column turning into a soft tan-grey cloud that
  drifts and thins over 20-40 s, a low dust skirt. `57_realism54.delta` makes the engine's column (`core_expl`, ECOR) the main
  element: earth grey 0xFF4A4236 instead of near-black, 5.5 s (bomb 6.5), faster rise (speed 0.55 / 0.45); burst smoke becomes
  the aftermath (translucent dark grey 0xE0564E46, 24/30/36 s, fade from 0.35); burst dust tan-grey 0xD0A09480 with a 0.2 sideways
  skirt. Earth pieces, flash and the 0.3.57 spin fix unchanged.
- 0.3.57 (2026-10-15): user on 0.3.56: "rotating separate puffs of smoke; dust that does not fade fast enough". `parts_desc` c23 is
  the sprite spin in degrees over the life (flashes and cores 0, screen smoke 60, burst smoke and dust 360). `56_realism53.delta`:
  burst smoke and dust spin 360 → 40; dust life 48/64/72 → 26/34/40 s with the fade starting at 0.25. Smoke lifetimes as 0.3.55.
- 0.3.56 (2026-10-15): user on 0.3.55: "dust creates several smaller moving puffs instead of one organic, realistic big one".
  `54_realism51.delta`: burst dust puffs 20/28/24 → 8/10/10, start 4/6/6 m, end 18/28/28 m, sideways speed 0.3/0.35 → 0.12/0.15,
  animation slowed to 0.6/0.5/0.5 so the puffs overlap into one slow mass. Lifetimes, fade and colour as 0.3.55.
  User: "smoke vertical puffs are too many and stick out unnaturally" → `55_realism52.delta`, same treatment for burst smoke:
  puffs 22/26/44 → 8/10/14, start 3/5/6 m, end 16/26/36 m, sideways 0.1/0.1/0.12, animation 1.5/1.5/1.2, vertical accel → -0.05.
- 0.3.55 (2026-10-15): user on 0.3.54: "fading too fast, more smoke and dust". `53_realism50.delta`: burst smoke puffs 16/18/32 →
  22/26/44, life 22/28/32 → 32/40/48 s, fade starts at 0.5/0.5/0.6 of life; burst dust puffs 14/20/16 → 20/28/24, life 34/48/54 →
  48/64/72 s, fade starts at 0.4. Sizes, colours and motion unchanged from 0.3.37.
- 0.3.54 (2026-10-15): user: "more smoke and dust during explosions, it dissipates slower". `52_realism49.delta` on the 0.3.53
  baseline: burst smoke puffs 12/12/25 → 16/18/32 and life 16/19/22 → 22/28/32 s; burst dust puffs 10/14/10 → 14/20/16 and life
  26/38/42 → 34/48/54 s. Fade points, sizes, colours and motion unchanged from 0.3.37.
- 0.3.53 (2026-10-15): user: "revert all explosion changes to 0.3.37". Parts deltas 34–49 and 51 (0.3.39–0.3.52: blast skirt,
  c6 sign fix, earth and flash passes, ladders, bomb-tier trims) and sfx `05_lhe_dust` moved to `retired\explosions_0.3.38-0.3.52\`
  (kept on disk, not applied). User: "remove rain gate too, it works in non-raining conditions too" → `33_wetness` retired as well
  (c26 is a ground-wetness gate, not rain-only; vanilla values restored). Still in: everything up to `32_realism30` (0.3.37), the
  hatch vent smoke `50_realism47` (0.3.51, not an explosion), the RHE class and rocket assignments (0.3.33/0.3.34).
  Confirmed by the user at 0.3.53: "explosions look like 0.3.37 again". This is the explosion baseline from here on. Note: the 0.3.41 finding that c6 y is an acceleration with negative = down still stands; the 0.3.37 smoke values
  carry c6 -0.28/-0.24/-0.22 (slow sink) and burst dust -0.03.
- 0.3.52 (2026-10-15): user: "thrown earth and clods should be more proportional to the explosion; big round chunks of earth do not
  look realistic". `51_realism48.delta`: many small pieces instead of few big blobs, stepped by tier: small 1 → 3.5 m and 110 pieces,
  medium 2 → 5.5 m and 120, bomb 2.5 → 7 m and 100 (was 6/10/9 m end with 80/80/65); clods 0.35 → 0.25 m. Launch, fall, colours as 0.3.50.
- 0.3.51 (2026-10-15): user: "all the effects except the ground explosion and its falling particles can stay longer and be thicker,
  for more realism". `48_realism45.delta`, earth untouched: burst smoke and dust life 18/28/40 → 24/36/50 s, smoke alpha 0xE0 → 0xF0,
  dust 0xC8 → 0xE0; fireball core 3.5/4 → 4.5/5.5 s; muzzle smoke 8/11 → 10/14 s and a step denser. User: "wider too" →
  `49_realism46.delta`: burst smoke and dust end size 10/18/28 → 14/24/36 m, muzzle smoke 2.5/6 → 3.5/8 m. User: "smoke exhaust
  from vehicle hatches after they fire should be smoother and less visible" → `50_realism47.delta`: `smoke_vent` alpha 0x80 → 0x50,
  fades to nothing, 3.5 → 5 s with a soft 0.3 fade-in, 1.5 m, slower animation.
- 0.3.50 (2026-10-15): user: "near the crater it should have the opposite effect: violent explosion, and the dust over the explosion
  dissipates smoothly". `46_realism43.delta`: the first second is violent, the rest as 0.3.49: dust and smoke fade-in 0.1/0.05 → 0.02
  (present at the flash), dust launch speed 0.55/0.6/0.6 → 0.7/0.8/0.85, dark fireball core speed 0.35 → 0.65 (bomb 0.25 → 0.55),
  sparks 0.1 → 0.3 (bomb 0.25). Hold-then-thin fade (0.5) and lifetimes 18/28/40 s unchanged.
  Also, user: "particles of ground are too visible; tune them proportional to dust and smoke" → `47_realism44.delta` backs the
  0.3.46 push off by a third: clods 0.6 → 0.35 m and darker, 60/70 per burst; earth lumps end 6/10/9 m, a shade darker, 80/80/65 pieces.
- 0.3.49 (2026-10-15): user on 0.3.48: "too much upward drift of smoke and dust from the initial explosion; make them thicker and
  dissipate smoother, they seem to just disappear fast". `45_realism42.delta`: smoke rise 0.08/0.06/0.04 → 0.02/0.015/0.01, dust
  -0.015 → -0.02; smoke alpha 0xB8 → 0xE0, dust 0xA0 → 0xC8; life 14/22/32 → 18/28/40 s with the fade point at 0.5 (dense for half
  the life, then a 9/14/20 s thin-out). Sizes and counts as 0.3.48.
- 0.3.48 (2026-10-15): user: "explosions look less powerful due to how fast smoke and dust dissipate; both have to match the power of
  the explosion, organic, proportional". After 0.3.46/0.3.47 the bomb tier had shrunk to the medium tier. `44_realism41.delta` sets
  one ladder, each step about 1.5× the one below: small (76 mm, 105-122 mm, mortars) smoke 8 puffs 1 → 10 m 14 s, dust 8 puffs 10 m
  14 s; medium (152 mm) smoke 10 puffs 18 m 22 s, dust 14 puffs 18 m 22 s; big (21/28 cm rockets, bombs) smoke 14 puffs 28 m 32 s,
  dust 20 puffs 28 m 32 s. Rise 0.08/0.06/0.04, opacity and hue unchanged.
- 0.3.47 (2026-10-15): user: "the 21 cm and 28/32 cm rocket explosions do not need to give up so much smoke and dust upwards, just
  as the fire blast, make it proportional". The bomb tier (`smoke_bomb`, `dust_expl_big`; classes BOMB and RHE, also aerial bombs)
  trimmed to the fireball's scale in `43_realism40.delta`: smoke 18 → 10 puffs, 34 → 22 m, 22 → 15 s, rise 0.05 → 0.02; dust 28 → 16
  puffs, 32 → 22 m, 28 → 20 s. Medium (152 mm) and small tiers unchanged.
- 0.3.46 (2026-10-15): user on 0.3.45: "more pronounced ground burst, it has to be more visible". `41_realism38.delta`: earth lumps
  bigger (start 2/5/4.5 m, end 7/12/10 m), longer (4/5.5/5.5 s), lighter (0xFF5A4A38, big/bomb 0xFF64523E instead of near-black
  0xFF3A2E22 / 0xFF4C3C2C) and more of them (100/100/80); clods lighter (0xFF564636) and, user: "with particles that are visible",
  0.22 → 0.6 m so each clod reads on its own. Launch speed and fall as 0.3.43.
  Also, user: "the dust kicked off from the crater has to dissipate smoothly instead of floating around" → `42_realism39.delta`:
  burst dust life 24/38/46 → 15/22/28 s, fade point 0.06 → 0.2 (short hold, then steady thin-out to nothing).
- 0.3.45 (2026-10-15): user: "looking from afar, explosions seem like just puffs of dust and smoke; make them more visible, yet the
  dust and smoke dissipate". `40_realism37.delta`: flash sizes small/medium/big 1.2/2/4 → 2/3.5/6 m (end 3/5/9) and life
  0.12/0.12/0.14 → 0.22/0.25/0.3 s, still a snap but visible at range; sparks 5 → 10 per burst (bomb 10 → 16), larger and 0.5 s;
  dark fireball core starts 11;13 m (bomb 15;19) instead of 8;9 / 12;15. Dust and smoke untouched.
- 0.3.44 (2026-10-15): user: "the kicked-off dust has to match the explosion: larger explosions produce more dust, smaller equally".
  Dust tiers (sfx `expl_desc` c12): HE 105-122 mm and mortars → small, UHE 152 mm → medium, bombs and heavy rockets → big; the big
  tier had been smaller than the medium one. `38_realism35.delta`: small 8 puffs 1.5 → 10 m 24 s, medium 16 puffs 3 → 20 m 38 s, big
  28 puffs 4 → 32 m 46 s. `sfx…05_lhe_dust.delta`: light HE (75/76 mm) had no dust generator; it now gets the small tier.
  Also, user: "it does not necessarily have to go upward, just more realistic" → `39_realism36.delta`: burst smoke rise
  +0.25/+0.2/+0.18 → +0.08/+0.06/+0.05, gentle buoyancy with the wind doing the rest.
- 0.3.43 (2026-10-15): user on 0.3.42: "it has to be more violent, more realistic" (ground burst). `37_realism34.delta`: earth launch
  speed 1/0.9/0.85 → 1.4/1.3/1.2, pull-down -8 → -10, start size 1/3.5/3 → 1.5/4/3.5 m, pieces 60/65/50 → 80/80/65; clods speed
  0.8 → 1.1, medium/big clod counts 60/80 → 80/100. Dust and smoke as 0.3.42.
- 0.3.42 (2026-10-15): user: "tune down the dust and smoke so the ground burst is clearly visible; blend both in, less dominant,
  still dissipating realistically". `36_realism33.delta`: burst dust birth alpha 0xE0 → 0xA0 and puffs 18/24/20 → 12/16/14; burst
  smoke birth alpha 0xFF → 0xB8 and puffs 12/12/25 → 9/9/18. Lifetimes, sizes, colours' hue and motion unchanged.
- 0.3.41 (2026-10-15): user: "the ground particles appear in chunks like dust; they should look like they got sent violently up and
  dissipate down". Column c6 re-read: clods carry 0;-9.8 (gravity) and exhaust 0;+0.15, so c6 y is a vertical acceleration with
  negative = down. The smoke "lift" values set in 0.3.31 (-0.28/-0.24/-0.22) were a slow sink; `35_realism32.delta` sets burst smoke
  to +0.25/+0.2/+0.18 so it rises. Thrown earth: launch speed 0.6/0.5/0.45 → 1/0.9/0.85, pull-down -5 → -8 so it arcs and falls,
  sprite end size 10/18/13 → 5/8/7 m and life 3.5/6/5 → 3/4.5/4.5 s so it stays lumps instead of dust blobs; clods speed 0.5 → 0.8.
  `docs\vfx_changes.md` column note for c6 should read "vertical acceleration (negative = down)".
- 0.3.40 (2026-10-15): A/B result at 0.3.38, user: "burst smoke looks the same in clear weather but weaker in rain" → `parts_desc`
  c26 is a wetness gate (-1 = never affected; vanilla puts 0.5 on burst dust, wheel dirt/water, burning fragments). `33_c26_test.delta`
  replaced by `33_wetness.delta`: c26 = 0.5 also on burst smoke (3 rows), muzzle smoke (`smoke_white`, `smoke_shotb`), muzzle dust
  (`dust_shot`) and vehicle dust (`dust_wh`), so all of them weaken in rain and on wet ground. Mud and water spray unchanged.
- 0.3.39 (2026-10-15): user: "more dust kicked off from the initial explosion; it does not have to travel vertically like smoke; the
  blast should be more realistic". `34_realism31.delta`: burst dust is a blast skirt now: puffs 10/14/10 → 18/24/20, sideways speed
  0.3/0.35/0.35 → 0.55/0.6/0.6, lift -0.03 → -0.015, fade-in 0.15 → 0.06 (present at the flash), birth alpha 0xD0 → 0xE0.
  Lifetimes, sizes and hue as 0.3.37. The c26 experiment from 0.3.38 is still in.
  Confirmed by the user at 0.3.39: "the blast dust spreads out low and fast now, looks right".
- 0.3.38 (2026-10-15): EXPERIMENT `33_c26_test.delta`: `smoke_expl`, `smoke_expl_big`, `smoke_bomb` get c26 = 0.5 (vanilla -1).
  Compare one battle in clear weather and in rain. Smoke unchanged in clear but weaker in rain → c26 is a wetness gate; changed in
  clear too → c26 is something else; no difference → c26 ignores smoke. In the last two cases the delta is removed.
- 0.3.37 (2026-10-15): user: "dust and smoke from explosions should be wider and smoothly dissipate; small dust around crater and
  explosions should be smoother too". `32_realism30.delta`: smoke end size 9/16/30 → 12/22/34 m, fade point earlier (0.35 → 0.3,
  bomb 0.7 → 0.5) and sideways speed 0.18 → 0.22; burst dust small/medium/big start 1.5/2.5/2 → 2/3/3 m, end 9/16/14 → 13/22/20 m,
  fade-in 0.05 → 0.15 so it swells in instead of popping, sideways 0.3/0.35, animation slowed to 1/0.8/0.7. Lifetimes and colours as 0.3.35.
- 0.3.36 (2026-10-15): user: "smoke from gun muzzles should be longer but withers away with the next shot; dissipate more smoothly
  instead of white trails". The trail was `smoke_white`'s end colour 0x40F0F0F0: it never reached alpha 0, so each puff left a pale
  ghost. `31_realism29.delta`: the three muzzle rows (`smoke_white`, `smoke_shotb` big guns, `smoke_shot_sm`) now fade to alpha 0,
  start dimmer and warmer grey, live 8 / 11 / 4.5 s (was 5 / 7 / 3), fade from 30 % of life instead of at birth, grow to 2.5 / 6 m
  and animate slower. The engine does not cull old smoke on the next shot; the longer, smooth fade is what reads as "withers away".
- 0.3.35 (2026-10-15): user: "dust and smoke from explosion impacts should last a bit longer, more realistic". `30_realism28.delta`:
  lifetimes up about 45 % with the same fade points: `smoke_expl` 11 → 16 s, `smoke_expl_big` 13 → 19 s, `smoke_bomb` 15 → 22 s,
  burst dust small/medium/big 18/26/28 → 26/38/42 s; sprite animation rate slowed in step (smoke 5 → 3.5, bomb 3.5 → 2.5, dust
  2/1.6/1.4 → 1.4/1.1/1) so the longer-lived puffs drift instead of churning. Sizes, colours and lift unchanged.
- 0.3.34 (2026-10-15): user on 0.3.33: "too large burst of ground". Flash and smoke kept; the earth is pulled in: `dirt_bomb`
  start 3 → 2.5 m, end 20 → 13 m, life 5.5 → 5 s, pieces 65 → 50, big-burst clods 100 → 80 (`29_realism27.delta`); RHE scale
  1.6 → 1.45 and dirt count 50 → 42 (`sfx…04_rhe_tone.delta`). Speed factor 0.45 stays so it still looks violent.
- 0.3.33 (2026-10-15): user: "explosions from heavy rocket artillery like 21 cm and 28/32 cm should be larger and more violent".
  Vanilla had the 21 cm `NBW42` on the aerial-bomb burst (BOMB) and, oddly, the 28/32 cm `WK_SPR` on the smaller UHE. Now: `NBW42`
  back to BOMB (its dirt and smoke have since been reworked, so it no longer blankets), `WK_SPR` → new class `RHE` = BOMB scaled
  1.4 → 1.6 with more pieces (`sfx…03_rhe.delta`: new `expl_dect` row RHE and `expl_desc` row `dirt_rhe`; class names are table-driven,
  `adv_game.codelib` only names the tables). `28_realism26.delta`: `dirt_bomb` speed factor 0.25 → 0.45 so the earth is thrown hard.
  `M_13` (132 mm) and `NBW41` (15 cm) stay on UHE / HE. Replaces 0.3.32 in new_updates, which was never run.
- 0.3.32 (2026-10-15): user: "larger explosions kick up a lot of dirt, make it more visible". `27_realism25.delta`: `dirt_expl_big`
  45 → 65 pieces, start 2.5 → 3.5 m, end 15 → 18 m, life 5 → 6 s; `dirt_bomb` 50 → 65 pieces, start 2 → 3 m; both tinted 0xFF3A2E22 →
  0xFF4C3C2C (a shade lighter so the thrown earth separates from the dark crater); `ext_dirt_big` clods 70 → 100 and clod sprite
  0.15 → 0.22 m (shared `ext_dirt` row, so medium bursts get the bigger clods too). Replaces 0.3.31 in new_updates, which was never run.
- 0.3.31 (2026-10-15): user: "smoke from explosions should dissipate upwards and be visible, make it realistic". `26_realism24.delta`,
  rows `smoke_expl` / `smoke_expl_big` / `smoke_bomb`: lift (c6 y) -0.1/-0.06/-0.1 → -0.28/-0.24/-0.22 so the smoke climbs as a column;
  birth colour fully opaque and a shade darker (0xF0807870 → 0xFF6A625A, 0xF0787068 → 0xFF645C54, bomb 0xFF787068 → 0xFF605850) so it
  reads against the khaki dust; end size 10/20 → 9/16 m and sideways speed 0.25 → 0.18 so it stays a plume instead of a blanket;
  lifetime 10/12 → 11/13 s with the fade point at 0.35 so it thins while climbing. Particle counts (12/12/25) unchanged.
- 0.3.30 (2026-10-15): user: "smoke from vehicle exhausts should be toned down". Exhaust is `smoke_eng` (bound in `adv_physic.codelib`;
  `smokew_eng` is its white twin, kept in step). `25_realism23.delta`: start alpha 0x70/0x80 → 0x38/0x40, end alpha 0x00/0x30 → 0x00,
  end size 3 → 2.2 m, puffs per burst 8 → 5; lifetime 2 s and drift unchanged. `smoke_vent` (ventilation smoke) untouched.
- 0.3.29 (2026-10-15): user: "spray mud in mud and water in water". `adv_physic.codelib` binds the wheel effects by name:
  `dust_wh` (dust), `dirt_wh` + `ext_dirt_wh` (soft ground: thrown clods), `water_wh` (splash), `wrounds_wh` (ripples); the choice per
  soil is engine-side. `24_realism22.delta`: mud spray stronger and wet-brown (dirt_wh 8 → 14 clods, ext_dirt_wh 5 → 9, tint 0xFF4A3C30,
  speed 0.25 → 0.4); water spray stronger (water_wh 8 → 14, end size 3;7 → 4;9, speed 0.4). Whether mud soil triggers `dirt_wh` or
  `dust_wh` is the engine's call; the user's look in a muddy patch decides.
- 0.3.28 (2026-10-15): user: "vehicles kick up dust which has white-greyish colour; change it so it depends on the terrain colour".
  Not reachable from data: `season_ua_summer.soils` c6 is a per-soil colour (grass 0x869352, dry_grass 0x9F946F, mud 0x8D8343…) but the
  engine does not apply it to wheel dust (vanilla's 0xF0F0F0 `dust_wh` would look olive on grass if it did). `23_realism21.delta`:
  `dust_wh` tint 0xC0F0F0F0;0x40B0B0B0 → 0xC0B8B090;0x40A8A080, end 0x00B8B090 (dominant grass / dry-grass khaki). Mud/water: the engine
  switches to `water_wh` (wheel splash) on water; per-soil dust suppression is probably `soils` c7 (mud/asphalt/concrete 0) but unverified.
- 0.3.27 (2026-10-15): user: "ground burst from rocket artillery is too much; dust in the crater hovers in one place and is very
  light compared to the other dust and smoke". Rockets: `M_13`, `NBW41`, `NBW42` carry VFX class `BOMB` (c22, the aerial-bomb burst:
  `dirt_bomb` row); now `UHE` / `HE` / `UHE` like 152 mm / 105 mm / 152 mm shells (`src\m1_core\mfo_tabs\common_res_mod.config.loc_def.
  02_rockets.delta`; c25 physics class untouched). Crater dust (`22_realism20.delta`): tint 0xD0A89C84 → 0x00A89C84 (darker khaki-brown,
  nearer the smoke), lift -0.02 → -0.03, speed factor 0.15/0.18 → 0.3 so it drifts and thins instead of hovering.
  Confirmed by the user at 0.3.29: "rockets look good".
- 0.3.26 (2026-10-15): user on 0.3.25: "too brown, motion shouldn't be so upward, density high at beginning and dissipating".
  `21_realism19.delta`: smoke_expl_big 0xF0787068 → 0x00585048, smoke_expl 0xF0807870 → 0x00605850, smoke_bomb 0xFF787068 → 0x00585048
  (brown-grey); dust lift c6 -0.05 → -0.02, smoke_expl_big -0.1 → -0.06; dust starts at full opacity (big 0xD8, medium 0xD0) with the
  fade-in (c13.y) 0.2 → 0.05 and life 35/30/20 → 28/26/18 s, ending transparent.
- 0.3.25 (2026-10-15): user: "large explosions have large clumps of dust visibly moving from the explosion". `20_realism18.delta`:
  dust_expl_big 18 → 10 puffs; dust_expl_rnd_big start/end 3.5/20 → 2/14 m, alpha 0xB0 → 0x90, speed factor 0.25 → 0.15;
  dust_expl_rnd speed factor 0.25 → 0.18, alpha 0xB0 → 0xA0.
- 0.3.24 (2026-10-15): user: "large explosion still has strong light grey dust and smoke". Remaining grey in big bursts = the
  screen-type puffs `scr_expl`/`scr_expl_sm` (colour cell 0xFFFF0000 is a special encoding for SCR parts; not tinted) and
  `smoke_bomb`'s grey end colour. `19_realism17.delta`: smoke_bomb end → 0x004A4038; scr_expl end size 12 → 8 m, life 8 → 5 s;
  scr_expl_sm 10 → 7 m, 5 → 3.5 s. Next step if grey persists: try the tint on the SCR rows anyway, one build, revert if it breaks.
- 0.3.23 **confirmed in game (user test 2026-10-15): colours and ground-burst contrast right.** VFX realism pass closed at 18 deltas;
  `docs\vfx_changes.md` is the vanilla-vs-current record.
- 0.3.23 (2026-10-15): user: "the ground burst also should have more contrast". `18_realism16.delta`: dirt column
  (`dirt_expl`, `dirt_expl_big`, `dirt_bomb`) 0xFF3A2E22 → 0x003A2E22 (near-black chernozem), clods 0xFF46382A opaque; dust stays pale.
- 0.3.22 (2026-10-15): user: "large explosions still have greyish colour of dust". The grey in big bursts is `smoke_expl_big` (and
  the untintable screen cloud). `17_realism15.delta`: smoke_expl_big 0xF06A5848 → 0x004A4038 (earth brown), 16 → 12 particles;
  smoke_expl 0xF0786858 → 0x00504840; smoke_bomb start 0xFF6A5848. Screen-type parts (`scr_expl*`) untouched: their colour cell is a
  special encoding.
- 0.3.21 (2026-10-15): user on 0.3.20: "colour should blend more with what the ground looks like". Source: `season_ua_summer.soils`
  c6 = soil base colour (grass 0x869352 olive, dry_grass 0x9F956F khaki, default soil = grass). `16_realism14.delta`: burst dust tint
  0xB0B8B898 → 0x00B8B898 (grass soil lightened ~55% toward white), muzzle dust 0xFFB8B898 → 0x00B8B898. Dirt column stays dark brown.
- 0.3.20 (2026-10-15): user on 0.3.19: "dust from explosions sits on ground and is very grey when expanding, looks like clumps of white
  diluted smoke". `15_realism13.delta`: dust tint darker and more saturated at higher opacity (0xB0A08060 → 0x00A08060); upward drift
  `c6` 0;-0.01 → 0;-0.05 (smoke_expl uses -0.1) so the haze lifts; fewer, larger puffs: counts 14/20/26 → 10/14/18, start sizes
  1/1.5/2 → 1.5/2.5/3.5 m. End sizes and lifetimes unchanged.
- 0.3.19 (2026-10-15): user: "colour of dust and explosions looks grey, should be in tune with the actual ground". `14_realism12.delta`,
  colours only (ARGB tints over the sprites), chernozem premise: burst dust haze 0x80D8C4A0 → 0x00D8C4A0 (greyish tan, half alpha);
  dirt column `dirt_expl`/`dirt_expl_big`/`dirt_bomb` 0xFF5C4A36 → 0x005C4A36 (dark brown); flying clods `ext_dirt`/`ext_dirt_sm`
  0xFF6A553F opaque; muzzle dust 0xFFD8C4A0 → 0x00D8C4A0 (tan); burst smoke 0xF0807468 → 0x00585048 (grey with a brown cast).
  Summer tables only; autumn/winter variants untouched.
- 0.3.18 **confirmed in game (user test 2026-10-15): medium and large ground bursts right.** State of the VFX pass: see
  `docs\vfx_changes.md` (regenerate with `tools\vfx_changes.ps1` after every build).
- 0.3.18 (2026-10-15): user: "ground burst in larger explosions should be toned down; visibility of ground burst is poor, it should be
  more pronounced". `13_realism11.delta`: dirt_expl_big 90 → 45 pieces, ext_dirt_big 110 → 70, its speed factor 0.7 → 0.5; dirt pieces
  bigger so the column reads through the dust haze: dirt_expl start/end 0.5/8 → 1/10 m, dirt_expl_big 1.5/14 → 2.5/15 m.
- 0.3.17 (2026-10-15): **delta ordering bug fixed.** Delta tags sort as strings, so `10_`, `11_`, `12_` were applied before `2_`…`9_`
  and the later passes' dust and dirt counts were overwritten by earlier ones: 0.3.14's dust was 14/20/26 (not 8/12/15, and that is
  what the user approved), and the extra earth of 0.3.15/0.3.16 (dirt counts 60/90) never reached the game, while the flash and the
  speed factor did. Tags are now zero-padded (`01_`…`12_`), pass 8's count lines dropped to keep the approved dust, and the build now
  applies all twelve in order. `tools\vfx_changes.ps1` writes `docs\vfx_changes.md`, vanilla vs current for every touched value.
  Rule for new deltas: always two-digit tags.
- 0.3.16 (2026-10-15): user on 0.3.15: "it should look more violent, the dirt is thrown". `12_realism10.delta`: `parts_desc` c14
  (speed-like factor: 0.1 static screens, 0.25 default, 0.35 fireball core, 0.75 airborne burning debris) raised for `dirt_expl` 0.25→0.6,
  `dirt_expl_big` 0.25→0.7, `ext_dirt`/`ext_dirt_sm` clods 0.25→0.5; dirt counts 52/75 → 60/90. Hypothesis on c14; user's look decides.
- 0.3.15 (2026-10-15): user: "ground burst could throw more earth and flash of explosion has to be instant". `11_realism9.delta`:
  dirt generators +50% (dirt_expl_sm/dirt_expl/dirt_expl_big 10/35/50 → 15/52/75, ext_dirt_med/big 40/75 → 60/110); flashes start at
  near full size (flash_sm/med/big start 0.4/0.5/0.7 → 1.2/2/4 against ends 1.5/2.5/5) and live 0.12–0.14 s instead of 0.3–0.35 s.
- 0.3.14 **confirmed in game (user test 2026-10-15): burst dust right, rocket trails gone.** VFX realism pass closed for HE bursts,
  muzzle dust and burst smoke; smoke screens not yet touched.
- 0.3.14 (2026-10-15): user on 0.3.13: "still too dense, drifts off in clumps, remove trail from rocket artillery too".
  `10_realism8.delta`: burst dust 8/12/15 particles (was 14/20/26) with a half-transparent start colour (0x80F0F0F0) so it reads as haze;
  rocket in-flight smoke (`smoke_path`, `smoke_path_sm`, generators bound by name in `basic_physic.codelib`) made transparent.
  New entry `common_res` (`src\m8_vfx\mfo_tabs\common_res.config.loc_def.1_mfo.delta`): the luminous tracer tails of `rocket`, `rs_82`,
  `m_13`, `nbw41_15cm`, `nbw42_21cm` made transparent. Side effect: RPG/ATGM rounds share `smoke_path*` and lose their smoke too.
- 0.3.13 (2026-10-15): billowing dust was "too dense" on 0.3.12 → `9_realism7.delta`: counts 25/35/45 → 14/20/26 (below vanilla's
  20/30/35 ring counts; the billowing type stacks particles at one point, so fewer are needed). Life, size, animation unchanged.
- 0.3.12 (2026-10-15): on 0.3.11 the dust "appears around the burst on the ground in a circle": the burst-dust generators are type
  `RND`, random points on the ground around the burst, vanilla's brief shock ring. `8_realism6.delta` switches `dust_expl_sm/dust_expl/
  dust_expl_big` to type `BROB` (what `smoke_expl` uses: billows from the burst point and rises), flag c1 0 like the smoke rows,
  counts 25/35/45. Dust particles (sprite, 20–35 s life, sizes 9/16/20) unchanged.
- 0.3.11 (2026-10-15): 0.3.10 drew dust and smoke "in squares": `parts_desc` c7 is the sprite's UV cell in the sheet (u;v;w;h), not a
  velocity, and halving it sampled a wrong half-size region with hard edges. `7_realism5.delta` restores vanilla c7 and instead reins in
  the end sizes (9/16/20, vanilla 8/14/18) so the long-lived cloud does not balloon outward. Lifetimes 20/30/35 s and animation rate stay.
- 0.3.10 (2026-10-15): 0.3.9 stopped the looping but the long-lived dust "spreads in all directions". `6_realism4.delta`: the
  per-particle scatter velocity (`parts_desc` c7, vanilla `0;0.5;0.25;0.25`) halved to `0;0.25;0.12;0.12` for the three burst-dust parts,
  lifetimes trimmed to 20/30/35 s, animation rate re-scaled (2 / 1.6 / 1.4). Goal: one dust mass that rises slowly and drifts with the wind.
- 0.3.9 (2026-10-15): burst dust looked like it was looping on 0.3.8: the sprite animation rate (`parts_desc` c22, vanilla 4) was tuned
  for a 10–12 s life and now cycles several times over 25–45 s. `5_realism3.delta` scales it by old life / new life (1.6 / 1.2 / 1.1)
  so the animation runs once at vanilla speed per particle life. If c22 turns out to be a loop count rather than a rate, the next step is 1.
- 0.3.8 (2026-10-15): **VFX realism pass 2** (`parts.config.loc_def.4_realism2.delta`), from the user's look at 0.3.7: burst dust was
  still too little and too short → counts 35/55/70, lifetimes 25/40/45 s, end sizes 13/24/32; muzzle dust was too much → 18 particles,
  20 s, size 9 (near vanilla); burst smoke was too much → 12/16 particles, 10/12 s (below vanilla).
- 0.3.7 (2026-10-15): **VFX realism pass 1** (`src\m8_vfx\mfo_vfx\parts.config.loc_def.3_realism.delta`, on top of Toni's tables).
  Premise: dry steppe, summer 1943. Ground bursts throw more earth (dirt particles 30→35, large 40→50) and leave a dust haze that
  hangs 18–28 s instead of 10–12 s and spreads wider (end size +30%); dust particle counts up (20/30/35 → 28/40/50). Tank and gun
  muzzle dust: 25 particles instead of 15, 30 s instead of 20, larger. Burst smoke lingers 16–18 s instead of 12–14 s. Flashes, dirt
  columns, smoke screens unchanged (screens are the special SCR type, pass 2). Visual only; no physics; local in MiusPlayer.
- 0.3.6 (2026-10-15): data-mismatch protection for multiplayer, as far as a data mod can provide it. MiusPlayer never checks that both
  PCs run the same data, so: (1) the build stamps a 6-digit fingerprint of every shipped entry into the add-on name shown in the Version
  menu (`MF Overhaul 0.3.6 [xxxxxx]`); (2) `tools\mp_fingerprint.ps1` prints one CODE for a PC's whole installed state (game build,
  MiusPlayer files, every registered add-on) to compare before a match, `-Detail` names the differing add-on; (3) a feature request for
  a live lobby check is drafted in `docs/upstream_requests.md` for the MiusPlayer author.
- 0.3.5 **confirmed in game (user test 2026-10-15): helmets and kit back.**
- 0.3.5 (2026-10-15): **helmets and kit back on the Achtung Panzer soldiers.** His outfits reference 63 addins (Stahlhelm 42 variants,
  SSh-40, caps, bread bags, holsters, binoculars…) that exist only in *his* `common_res_mod.addins`; dropping his table in 0.3.x dropped
  them, so ported soldiers rendered bare-headed. `src\m9_ap_port\mfo_tabs\common_res_mod.config.loc_def.delta` now carries exactly those
  63 `row+` ops (he changes no vanilla addin row); the build merges vanilla → RBVFX2 delta → these 63 rows → our 31 sound-class cells.
  First build from the merge session's delta pipeline (`build.ps1` merges per entry in `table_merge_order`).
- 0.3.4 **confirmed in game (user test 2026-10-15): smoke grenade sound right, flare trail gone.** **Sound rule, settled** (0b session, from `basic_sound.codelib` + `base_shell.codelib`): at audio init the sound manager
  enumerates every `sound` entry of every mounted pack into one sorted fragment table; on a duplicate name the vanilla copy is kept, so
  an add-on can never replace a vanilla sound by name, unlike configs and text. Add-on sounds with **new** names are always in the table.
  M6 therefore ships samples under new names (`mfo_*`) and points `sfx.expl_snds` rows at them; `ch_sounds` must carry no vanilla names.
- 0.3.4 (2026-10-15): the 0.3.2 battle log had no more `acts` errors, yet the user still found the smoke hiss loud, and sample overrides from
  add-ons are evidently never used by the sound bank. So the fix moves to the config level: `sfx.expl_snds` rows SMK and SMKP now play
  `expl_ks*` (the 1 s Molotov ignition whoosh, −19 dBFS RMS) in group `acts` instead of the 47 s `expl_smk*` hiss (−13 dBFS sustained).
  Flares: `adv_game.codelib` binds `smk_flare` and `smk_flare_black` by name for signal flares; both particle definitions are now fully
  transparent (the grey ground-flare plume goes with it). If a long loud sound remains at a smoke pot, it is the engine's burning loop
  (`fire*` / `lfire*` through mixer group `default3d_loud`, also named in that code), which is the next lever.
- 0.3.3 (2026-10-15): sounds back inside the main add-on. The separate GUID sound add-on of 0.3.1 made the main menu's update check
  report it as "lost" (`[i_opgame] -lost!`) and prompt "1 update found" on every start, although it was installed. Players who installed
  `mfo_sounds_0.3.1` should remove "MF Overhaul Sounds" via the Version label. `tools\build_sounds.ps1` kept for reference, unused.
- 0.3.2 (2026-10-15): **root cause of the loud smoke grenade found and fixed.** Realistic Battlefield VFX Part 2's `sfx` table has every
  `expl_snds` row mangled: vanilla cells like `"expl_smk*, acts"` (sound pattern, mixer group) are split across two columns, so the smoke
  pop is bound with no group (default, loud, long-range) and the engine logs `Bind() Unable to find audio fragment 'acts'` at every pop.
  All 19 rows are affected (HE, mortar, grenade sounds lose their groups too). The overhaul now ships `sfx` with vanilla's `expl_snds`
  and Toni's `expl_desc` / `expl_dect` changes (M8 base rule, delta-applied). Also: airborne burning smoke (`smoke_burn_air`) made transparent,
  the likely flare trail; `smk_flare_black` stays zeroed. The −18 dB `expl_smk_0` sample stays in the separate sound add-on (its effect is now secondary).
- 0.3.1 (2026-10-15): sounds moved to a **separate add-on** `mfo_sounds_<ver>.gt3ext` (folder `7C1E2B4A-5F3D-4B6E-9A2C-1D0E8F7A6B5C`,
  only `ch_sounds.flatdata`), the exact shape the in-game builder produces and that RukiSoundMod uses. Reason: the 0b session found the
  engine scans hash-less archives linearly, so 0.3.0's hash table was not the fix either; the `ch_sounds` literal in `adv_opgame.codelib`
  belongs to the builder, not the loader. Shape is the last difference to a known-working sound mod. `tools\build_sounds.ps1`; main build skips `separate_modules`.
- 0.3.0 (2026-10-15): first build whose sound archive has a name hash table (turned out not to be the gate). Root cause of 0.2.1–0.2.9's silent failures: the AZP3 name
  hash table (`base_shell.codelib` looks entries up through it; our packer wrote none). `gt3.ps1 pack` now writes it (0b session's work;
  vanilla archives round-trip byte-identically). `ch_sounds` carries `expl_smk_0` at −18 dB plus three unchanged vanilla copies
  (`shot_smk`, `shot_nebel`, `expl_ks_0`) so the archive has ≥4 entries and gets a table. The `base_params` acts-gain experiment is withdrawn.
- 0.2.11 (2026-10-15): signal-flare smoke trail removed entirely (generator emission 0, particle fully transparent), per user test of 0.2.10.
- 0.2.10 (2026-10-15): signal-flare trail is a thin, light-grey, fading wisp instead of a black plume (`parts` table, M8, on RBVFX Part 2's base).
  Sound diagnostics withdrawn: on 0.2.9 the silenced rifles were still audible, so no sound entry from our archives loads at all; the cause is the
  missing AZP3 name hash table (our packer writes none) and is being fixed in the packer. `ch_sounds` now carries only the quiet `expl_smk_0`.
- 0.2.9 (2026-10-15): diagnostic. On 0.2.8 the smoke hiss still had vanilla's loud-then-fading shape, so `mfo_sounds.flatdata` is
  not consulted for sounds although `mfo_tabs.flatdata` is for configs. `adv_opgame.codelib` names `ch_sounds.flatdata` / `ch_textures.flatdata`
  (the in-game builder's archive names); the sound archive is renamed to `ch_sounds` and `build.ps1` allows those two names. Same diagnostic content.
- 0.2.6 (2026-10-15): diagnostic. 0.2.4's 2 s hiss and the acts gain change had no audible effect, so the hiss is not `expl_smk_0`
  via `acts`, or sound overrides are not loading. This build silences `fire_0-4`, `lfire_0-2` (burning loops, not referenced by any config,
  so engine-bound) and `shot_mosin` / `shot_kar98` (control: proves whether our sound entries load). `expl_smk_0` restored to full length at −30 dB.
  Also first build carrying the M9 port tables from the milestone 0b session. RukiSoundMod and Kuli Kraut Fix were uninstalled via the Version menu before this build.
- 0.2.4 (2026-10-15): diagnostic. Sample level had no effect, so the `acts` sound-group gain in `base_params` goes 0.7 → 0.2; the shipped hiss is cut to 2 s so the test also shows whether our sample is the one playing.
- 0.2.3 (2026-10-15): smoke hiss 30 dB under vanilla.
- 0.2.2 (2026-10-15): smoke hiss 18 dB under vanilla (was 12 dB in 0.2.1; still loud by ear).
- 0.2.1 (2026-10-15): smoke sounds. Smoke grenades and light smoke rounds: the 47 s emission hiss is 12 dB quieter.
  Artillery and mortar smoke rounds no longer burst with the full HE sound of their calibre (one sound class down:
  LHE/MORT → GREN, HE → LHE; 31 shell rows, sound-only column). M1 shells table is now based on RBVFX Part 2's.
  Tools: `tools\sound_gain.py`, `tools\azcf_setcell.ps1`.
- 0.2.1 (2026-10-15): third-party content analysed (`docs/third_party.md`, `docs/addon_matrix.txt`, `tools\addon_matrix.ps1`).
  T-D SFX identified as RBVFX Part 1; Achtung Panzer Configs found to be a 2021 snapshot; modules M8 and M9 added to the design.
- 0.2.0 (2026-10-15): design rewritten around MiusPlayer as the multiplayer transport. Milestone 0: toolchain replaced by
  `tools\gt3.ps1` (no game tools on 3598), build pipeline produces an installable `.gt3ext`, both MiusPlayer install orders
  verified hash-clean. Contains only a visibility test (one squad renamed). Nothing playable yet.
- 0.1.0 (2026-10-15): design and scaffold only.

# "Saur-Mogila tumulus, 28 August 1943" brought to the battle-group system (M2, build 0.5.4)

User: "Saur-Mogila tumulus operational campaign upgrade from old OOB without BG to operational campaign with
battlegroup system, copy OOB from July 30 campaign for 34th guards rifle division." Generator: `tools\oob_saur.ps1`;
platoon-level list: `docs\oob_saur_mogila_changes.md`. How the engine places units and why battle groups need placement
rows: `docs\oob_stepanowka_17jul.md` section 8.

## 1. The files

`data\oprum\shared\camps\1943_08_Mius\08_28_Saur_RUS.campack2` and `_GER` (1.1 MB each; the two differ only in the
campgen side fields and the `ai` ids). 2015 format: `features` 0x2000008, 29 formations, 118 platoons, each placed
platoon has its own map node and arrival turn in `plat_pos`, no battle-group nodes, no `tac_limits`. 7 turns of 4 hours
from 28 August 06:00, map window `camp_area` 4;2;6;5 of the 6M_Mius polygon (the Saur-Mogila height and Saurovka).

Old order of battle (both sides): Soviet 34 Gds RD with 103 Gds RR (1st bn), 105 Gds RR (2nd bn: 4th-6th coys),
107 Gds RR (1st/2nd coys), 60 Gds TPP (two KV-1S platoons), 7 Gds OTPP (two KV-1 platoons), 9 iptabr (two 45 mm and
three 76 mm batteries), 140 STBde (Matilda/Sherman companies, mortars, AA MG, SMG coy), 293 Gds RR of 96 Gds RD (1st coy),
air; German 306 ID (training coy, 1st coy, Marder coy, AT platoon, depot), 581 IR (1st coy), 570 IR (9th/10th coys),
210 StuG bn (one battery), 294 ID (pioneer coy, 754 sapper platoon), 514 IR (5th coy), 335 ID (Marder coy, supply).

## 2. What was done

1. **34 Gds RD = the 30 July division.** The old `p_ra_103gds_rr`, `p_ra_105gds_rr`, `p_ra_107gds_rr` formations and
   their 37 platoons are removed. The 30 July formation structs `p_ra_103rr`, `p_ra_105rr`, `p_ra_107rr`, `p_ra_84ar`
   are inserted under the existing `p_ra_34rd` (its struct is kept: its name key is in this pack; `ai` ids of the
   side file are used throughout) and every 30 July platoon of `p_ra_34rd`, `p_ra_103rr`, `p_ra_105rr`, `p_ra_107rr`,
   `p_ra_84ar` is copied verbatim, 305 nodes: division HQ, NKVD platoon, recon company, training battalion, sapper
   battalion, AT battalion, the attached 665 destroyer bn companies and 16 mortar FO teams, three regiments of three
   battalions with companies, MG/mortar/AT/SMG sub-units, FO teams, two battle groups per regiment (`ra_103_1` =
   1st bn with 1st coy, `ra_103_2` = 2nd bn with 4th coy, and so on), and 84 Gds AR (HQ, nine FO teams, 7th-9th
   batteries). Names, codes, uids (no collision with the Saur uids), compositions and the 30 July strengths
   (`params` 0.3-0.5) are unchanged. The 60 Gds TPP and 7 Gds OTPP stay under `p_ra_34rd` as before.
   - Battle-group reserve links: `pool4` `p_ra_1destr` (not in this operation) -> `p_ra_9_iptabr`.
   - Slots: `ra_107_2` had an empty UNI slot -> `ra_107_3c_1p`; `ra_105_1` SCT (empty on 30 July) -> `ra_84ar_4b_ac`;
     the two empty SUP slots -> `ra_9iptabr_1bat`, `ra_9iptabr_2bat` (the old file attached 9 iptabr to the division).
     The other slot references (84 AR FO teams, 665 destr bn AT guns, 16 mortar FO teams) resolve inside the copied block.
   - Placement: regiment HQ at the old regiment HQ node (103: node 92, 105: 94, 107: 84); 1st battle group at the old
     first company command's node (114, 117, 68); 2nd battle group at the old battalion command's node (76, 79, 107);
     division HQ (node 93) and 84 AR HQ (node 95) in the old 105 Gds RR HQ cell (3;7, the rear), as 30 July keeps the
     AR HQ with the division HQ. **One unit per map node** (0.5.5): no vanilla operation ever stacks two placed units
     on one node, and 0.5.4, which put three HQs on node 95, crashed after creating the operation; now every placement
     takes the wanted node if free, else a free node linked to it in the same cell. A unit put into a battle-group slot
     (9 iptabr 1st battery) loses its own placement. Everything else is in reserve (`-1;-1;-1`), all on turn 1.
2. **Battle groups for every other formation that has an HQ node** (10 per side). Each company that had placed
   platoons in the old file became one battle group placed at its company command's node on the company's turn:
   COM = company command, UNI = its rifle platoons, SUP = its MG/AT platoon (German 1st/306, training coy/306, 1st/581,
   9th/570, pioneers/294, 5th/514; Soviet 1st/293 Gds RR). Tank and SPG companies without a company command node form
   a battle group with an empty COM slot, as `ra_22stp_bg2` in the 17 July file: 7 Gds OTPP, 140 STBde (Matilda
   company + SMG coy + AA MG coy, turn 3), the Marder company of 306 ID with its AT platoon. Battle-group names
   `<formation>_bgN`, codes 0xF0N, name key = the company's key, sprite = the company's. The grouped platoons lose
   their own placement (they deploy with the group). HQs, depot, supply columns, repair units and the 10th/570 IR
   company (not placed in the old file) keep their rows. **Formations without an HQ node keep the old single-unit
   placements** (60 Gds TPP, 210 StuG battery, 335 ID Marder company): 0.5.5 gave them battle groups and the engine
   crashed on a failed lookup (minidump: `adv_opgame.codelib+0x36e34`, index -1 while scanning the 399 platoons);
   every vanilla battle group's formation has an HQ node.
2b. **Map-node occupants (0.5.7).** `mg_nodes` column 2, element 0, is the uid of the unit standing on the node
   (-1 when empty) and mirrors `plat_pos` in every vanilla file. The engine's node scan (`adv_opgame.codelib`
   0x180036d60: for every node within one cell of a position, take its occupant id, find that platoon, index by the
   result) has no -1 check, so a stale or missing occupant id crashes the game right after the operation is created,
   which is what 0.5.4-0.5.6 did (nodes still named the removed old 105 Gds RR units; the new HQ and battle-group
   nodes had no occupant). The column is now rebuilt from `plat_pos` after all placement changes.
3. **Flags.** `features` 0x2000008 -> 0x200000B, the value of the 17 July NA and 30 July files (bits 0-1 are what
   the old file lacks; the engine's battle-group handling is assumed to key on them, untested until the user plays).
4. **Text.** 22 keys copied from the 30 July pack (formation and battle-group names: "34 gds RD, 1/103 gds RR" ...).

Totals per side: 399 platoons (118 - 37 + 305 + 13), 30 formations, `plat_pos` row for every platoon, delta
640 node+ / 40 node- / 10 106 row+; `vanilla + delta` reproduces the generated table byte for byte.

## 2g. Build 0.5.8: the user's deployment-phase requests

After 0.5.7 ran in game the user asked, from the German and Soviet panels: "separate this battalion [306 ID Marders]
into command unit and 2 platoons, do the same with 210 AT bn; add platoons to the reserve [the German reserve guns] so
they are available to battle groups as units; add FO to artillery units which you create; add a 3rd company BG for 103
and 105 RR; 293 RR needs its organic artillery FO and support units, base it off its reserves; 140 TBde: split the
tank companies into command and platoons, give it 2 tank slots, same with the MR battalion and SMG coy, add the
reserve units except the T-20". Generator passes 2c-2f:

- **SPG companies** (`_ccom` + two `_com` sections): 306 ID Marder coy -> `wer_306id_mar_coy_com` (COMC, plu_tankcmd,
  "1 ATG coy, Command") + two SUPM platoons; its group now reads COM = command, SUPM, SUPM, SUP = AT platoon. 210 StuG
  battery -> command + two platoons, all three placed on neighbouring nodes (the battalion has no HQ, so no group).
- **German reserve guns as platoons**, every German formation with the standard pool (306 ID, 581 IR, 570 IR, 294 ID,
  514 IR): ATG platoon 1 (Pak 38 + Pak 97/38), ATG platoon 2 (2 x Pak 184/1(r)), MG platoon (2 x MG 42), IG platoon
  (2 x leIG 18) + FO 75 mm, mortar platoon (2 x GrW 34, phone) + FO 81 mm; codes 0x141-0x147; name keys of the 30 July
  13./14./12./8. company platoons; the FO teams are the 30 July `we_513_13c_ac75` / `we_513_1b_ac81` (off-map support
  ids leIG / GrW 34 section). The consumed pool rows are removed; light mortars, AT teams and trucks stay in reserve.
- **Third battle groups** `ra_103_3`, `ra_105_3` (3rd bn: 7th coy command + its platoons, SCT = 84 AR FO, SUP from the
  regiment), placed on a free node in the regiment HQ cell. (The user wrote "104 RR", then corrected to 105.)
- **293 Gds RR** from its own reserve pool: FO 120 mm (`ra_293rr_ac120mt`, support 120 mm mortar platoon), FO 76 mm
  (`ra_293rr_ac76gun`, ZiS-3 support), ATG platoon (2 x 45 mm), regimental gun platoon (1 x 76 mm mod. 1927), mortar
  platoon (2 x 82 mm) + its FO team, MG platoon (2 x Maxim), SMG platoon (2 squads); each shaped like the 30 July
  103 Gds RR counterpart (node, code, name key); the pool is empty afterwards.
- **140 STBde**: 1st tank coy -> command (Matilda) + platoon; 2nd -> command (Stuart pair) + platoon (Shermans); SMG
  coy, ATR coy, mortar battery (+ FO team 82 mm) and AA MG coy -> command + two platoons each; from the pool: T-3
  platoon (2 tanks, "2 tank coy, 2 tank platoon"), SdKfz 250 recon platoon, two motor-rifle platoons (3 squads each);
  the T-20 tractor, trucks and air spotters stay in reserve. Brigade group: COM = 1st coy command, SCT = recon,
  STR = 1st coy platoon, STR = 2nd coy platoon, UNI = SMG 1 and 2, SUP = AA MG, SUP = mortars.
- About the "[II / 0]" tag the user saw on 45 mm guns: the pool cells that could carry such data are -1 in every file
  (vanilla and generated); the tag is the engine's own display for those gun squads and is unchanged by the mod.

Per side after 0.5.8: 460 platoons, 48 placed, all consistency checks clean (no shared nodes, no placed slot members,
mg_nodes = plat_pos, no stale occupants, every battle group in a formation with an HQ).

## 2i. Build 0.5.10: complete batteries, full 293 Gds RR

User: "some artillery batteries lack their FO; in screenshot FO lacks guns" (FO panel: number of guns 0 (4)) and
"make 293 RR have 2 BG, 1st and 2nd battalion, each with its companies (1-3, 4-6) available, with their organic
regimental and battalion support units".

- **How an FO gets its guns** (from the saves, pool row cell 25 of the FO's `corr_art` squad): the number of guns of
  the FO's type in the gun platoons of the same company group (code & 0xFF0) in the same formation: `ra_1012ar_4b_ac`
  next to `4b_1p` (2 x ZiS-3) = 2, `1b_ac` next to the moved four-gun battery = 4, `ra_84ar_1b_ac` with no gun platoon
  in its group = 0, `ra_103_ac76gun` (0x40) with its gun battery in group 0x70 = 0. The 30 July pattern leaves many
  batteries FO-only and the regimental 120 mm mortar FOs always without mortars; "0 (4)" is what those show.
- **Pass 2h (both operations):** for every FO whose group has no gun platoon of its type: if another group of the
  formation holds guns of that type and no such FO, the FO moves there (regimental 76 mm FO into the gun battery
  group; each battalion 82 mm FO into its battalion's mortar company); otherwise a two-gun platoon of the calibre is
  added to the FO's group (ZiS-3, M-30, 76 mm regimental gun, 82 mm mortar, 120 mm PM-38 mortar; German leFH 18,
  sFH 414(f), leIG 18, GrW 34), named like the 30 July battery platoons ("N battery, 1 Arty plt (76 mm)", "N./294 AR,
  1 arty plt (105 mm)"). For every indirect-fire gun platoon whose group has no FO of its type an FO team is added
  (anti-tank units excluded). Saur-Mogila: 31 fixes per side; Stepanovka: see its change list.
- **293 Gds RR** is now the full 30 July regiment copied like the 34 Gds RD ones (HQ, three battalions with companies
  1-9, regimental gun battery, 120 mm mortars, ATR, MG and mortar companies, battalion mortar/ATG/ATR units), placed
  where the old regiment stood (HQ node 89, 1st bn group at the old 1st coy node 111, 2nd bn group next to the HQ);
  the 30 July 3rd-battalion group is dropped (two groups asked for); its reserve links point to 96 Gds RD and 9 iptabr
  (234 Gds AR is not in this operation). The reserve-pool platoons of 0.5.8 are superseded.

- **0.5.11, "they lack commander":** every artillery-regiment battery that has an FO team and a gun platoon but no
  battery command gets one (COMC, 30 July 4th-battery pattern: battery command squad, phone, observer; code = battery
  group), so each battery reads Command / FO / Arty plt. Saur-Mogila: 84 Gds AR batteries 1-6; Stepanovka: see its
  change list.

- **0.5.13, "move 3/105 BG to the white X mark on the map", "move 3/103 to the white X mark":** the user marked, on
  two map screenshots, where the 3rd-battalion groups should start (0.5.8 had put them on a free node of the regiment
  HQ cell 2;7, behind the line). Reading the marks against the map grid: 3/105's X lies between 1/105 (cell 3;5, north-
  east node) and 2/105 (cell 3;6), at the bottom of cell 3;5 -> map node 65 (cell 3;5, south-centre); 3/103's X lies
  between 1/103 (cell 2;5, north node) and 2/103 (cell 2;6), right of 1/103's column -> node 115 (cell 2;5, south-east).
  Both were free Soviet-side nodes; the generator's placement block sets them after the copied block is placed
  (`$manualPos`), through the same one-unit-per-node `SetPos`, and mg_nodes is rebuilt from plat_pos afterwards.

## 3. 28 August vs 30 July: deviations kept and not kept

- **Kept from 30 July without change:** composition and strengths of the 34 Gds RD (after ten days of the Donbass
  offensive the division was at the same 30-50 % fill as after the July fighting; no 28 August strength return was
  readable, see section 4), the 84 Gds AR FO teams, the 665 destroyer bn and 16 mortar attachments (both 5 Уд. А assets
  on 1 August as well).
- **Changed for 28 August:** the old file's units are the division's actual sub-units engaged at Saur-Mogila on
  28 August: 103 Gds RR 1st bn, 105 Gds RR 2nd bn, 107 Gds RR 1st bn. The 30 July battle groups of those battalions are
  placed on those spots; the other battalions sit in reserve behind them (the 30 July file does the same for its second
  echelon). The 9 iptabr, 60 Gds TPP, 7 Gds OTPP and 140 STBde attachments are those of the old file (not in the
  30 July order of battle) and are kept as formations with their own battle groups.
- **Not done:** 96 Gds RD (whose 295 Gds RR took the height on 30-31 August) is in the old file only as the 1st coy of
  293 Gds RR; it was not expanded (the user asked for the 34th Guards). 127 RD and 271 RD (left flank) are not in the
  file. German side kept at the old file's strength and units (306 ID, 294 ID, 335 ID remnants, 210 StuG), only grouped.

## 4. Sources

- `docs\oob_stepanowka_17jul.md` section 9: Боевой состав Советской Армии 1 Aug 1943, Южный фронт (5 Уд. А: 31 гв. ск
  with 4, 34, 40 гв. сд; 96 гв. сд; 1 гв. ибр; 8, 15 иптабр; 32 гв. тбр, 22 гв. отп).
- ru.wikipedia "Саур-Могила": 28 August the 3rd bn/865 RR of 271 RD attacked the height and was pinned; 127 RD moved to
  the left; 34 Gds RD covered the right flank; 29 August the Soviets nearly took the summit, German counterattack with
  flamethrower tanks and assault guns from Saurovka; night 29/30 August Shevchenko's recon group of 96 Gds RD on the
  summit; 31 August the height taken and lost again; Germans withdrew in the night of 31 August/1 September.
- ru/en Wikipedia 34-я гвардейская стрелковая дивизия (103, 105, 107 гв. сп, 84 гв. ап, 38 гв. оиптд; 31 гв. ск,
  5 Уд. А; Енакиевская for 8 September).
- pamyat-naroda.ru could not be read by this session (captcha for automated requests).

## 5. What to look for in the deployment phase

- Operation list: "Saur-Mogila tumulus" still listed once, loads, briefing shows.
- (0.5.13) 3/105 stands between 1/105 and 2/105, 3/103 between 1/103 and 2/103, where the two white X marks were.
- OOB panel: 34 gds RD with Division HQ, 103/105/107 gds RR (Regiment HQ + "1/103", "2/103" battle groups IN BG,
  companies IN BG / IN RESERVE), 84 gds AR (Regiment HQ, FO teams), 60 Gds TPP and 7 Gds OTPP under the division.
- Map: regiment HQs and the six 34 Gds RD battle groups on the old regiment positions west and south-west of the height;
  division HQ and 84 AR HQ with the 105 RR HQ; 293 Gds RR, 9 iptabr, 140 STBde (turn 3) as before.
- German side: battle groups for 1st/306, training coy/306, 1st/581, 9th/570, pioneers/294, 5th/514, Marder and StuG
  groups; HQs where they were.
- If the engine ignores the battle groups (units shown but the deployment phase behaves like the old file) the flag
  change did not suffice; report what the panel shows.

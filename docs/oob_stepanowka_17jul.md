# OOB upgrade: "Stepanovka-Marinovka, 17 July 1943" to the 30 July 1943 standard (M2, build 0.5.2)

Build 0.5.1 (user feedback on 0.5.0, see section 7) adds the division artillery regiments as formations of their own,
splits the tank companies into command + platoons and fills the battle-group SCT slots; sections 3-6 describe the 0.5.0
pass, section 7 the three additional passes.

Done 2026-10-16 on the pristine 3598 operation files. Generator: `tools\oob_17jul.ps1`; platoon-by-platoon result:
`docs\oob_stepanowka_17jul_changes.md` (generated, 1 100 lines). Deltas: `src\m2_oob\camps\1943_07_Mius\07_17_Stepanovka_NA_RUS\`
and `..._GER\` (one `desc` delta each, two whole text packs each, a `!flatlist`).

## 1. Which files are the operation

An operation is one `.campack2` per playable side under `data\oprum\shared\camps\1943_07_Mius\`: an AZP3 pack with six entries,
`desc` (AZCF: `i_campgen:campgen` parameters, `reserves` = the formations with their reserve squad pools, `act_platoons` = every
platoon of both sides), `div_pool` (the same formations and platoons in the quick-battle `qbattle` shape), `scripts` (AZSC byte
code: deployment areas, arrival turns, objectives; not decoded), `text` (loc_eng, loc_rus) and `op_image`. The 17 July
operation exists twice: `07_17_Stepanovka_RUS/GER` (the original 2015 build) and `07_17_Stepanovka_NA_RUS/GER` (the same scenario
re-built by Graviteam in the current format: hierarchical formations with `parent`, battle-group nodes, 4-component `params`,
`features` 0x200000B instead of 0x1000000). **The game plays the NA files** (the user's save is
`1943_07_Mius_07_17_stepanovka_na_rus.opsave`), so the upgrade targets them; the original pair is left untouched.

How the engine uses `act_platoons` (read from the save): only battle-group nodes (`bg` != 0, with a `slots` table of up to 8
member platoons) and HQ nodes (`code` 0) get a map node and an arrival turn from the scripts; every other platoon sits in its
formation's reserve (`state` 4) and is what the deployment screen offers for the battle groups. Platoons added to a formation
therefore appear as new reserves; nothing in the scripts references platoons by name or uid (checked: no uid of any
platoon occurs in the AZSC byte stream), so the scripted deployment and the reinforcement schedule are unchanged.

## 2. What the 30 July OOB has that the 17 July (NA) one lacked

Per formation the 30 July file models the full regimental/brigade structure of the summer-1943 tables; the 17 July NA file models
rifle companies with three platoons and little else. Missing on 17 July (now added):

| Element | 30 July | 17 July NA before |
|---|---|---|
| Battalion HQ with FO team | `Nb_hq` + `Nb_ac82mt` (CTRL, `plu_fo`, support `rkka_artsup_mt82_plat`) per rifle battalion; `Nb_ac81` per German battalion | bare `cbnN` command groups, no FO teams anywhere |
| Company mortar / MG platoons | `Nc_mt` (50 mm / 8 cm mortars), German `Nc_mg`, Soviet MG companies (`1mgc`, `2mgc`, `3mgc`) and mortar companies (`1mtc`, `2mtc`) per battalion | none |
| Regimental troops | sapper platoon, foot/horse recon platoon, SMG company (cmd + 2 platoons), AT-rifle company (cmd + 2), AT-gun battery (cmd + 2 x 2 guns), regimental gun battery (cmd + FO + 2 x 2 76 mm), 120 mm mortar FO | one AT-rifle platoon, one gun platoon, one SMG platoon per battalion at most |
| Third battalion | `3b_hq`, `3b_ac82mt`, `3b_atg`, `3b_atr`, 7th/8th companies, 3rd MG company | two battalions only (6 companies) |
| German infantry regiment | bicycle platoon, 13th (IG) and 14th (AT) companies with command groups, 4th/8th/12th MG companies with mortar sections, battalion FO teams, ATR squads in company commands | companies with 2-3 rifle platoons, one gun/support company |
| Panzergrenadier regiment | per company a mortar section and an MG platoon, 4th/8th heavy companies (sapper, AT, two IG platoons, SdKfz 250/11 ATR platoon), battalion FO teams (8 cm and 7.5 cm IG) | companies with 3 platoons carrying one 5 cm mortar each |
| Division troops | recon company (cmd + 2 scout platoons), sapper battalion (HQ + 2 companies x 2-3 platoons), AT battalion (HQ with FO + 3 batteries x 45 mm M-42 + ATR company), artillery regiment FO teams per battery; German AT battalion (recon coy + 3 AT companies), artillery regiment FO team per battery | division formations are AI placeholders with no platoons; artillery present only as gun batteries attached to regiments |
| Tank / mech brigade | recon, sappers, AT battery (ZIS-3), AA battery (DShK), tank battalion command, MR battalion with company commands, 82 mm FO, mortar company; mech brigade: recon coy (scouts, M3A1, BA-64), SMG coy, engineer coy, ATR coy, two mortar coys with FO, AA battery, two gun batteries with FO, battalion FO/ATR/SMG, MG platoon per company, MG and mortar coy per battalion | tank companies and three rifle companies per battalion, one mortar battery |
| Strength parameters | `params` with four components, varied per battalion (0.3-0.6; 0.5-0.7; 0.7-1.0; 0.1-0.3) | `0.5;0.5;1` everywhere |

Also in the 30 July file but **not** copied: battle groups (the 17 July ones stay as scripted), the 1./ heavy mortar regiment FO
teams attached to 16 PzGr Div on 30 July, 128 training battalion and 128 AT bn (Marder) of 23 PzD (the 17 July file already has
its Marder company), the 209 StuG bn pattern (the 17 July 210 StuG bn already has its 9 StuG), the 4 Gds Mech Corps brigades
(13/14/15 Gds MBde, 36 Gds TBde: not in the sector on 17 July; their structure is used as the template for 4/5/6 Gds MBde only),
the SS divisions and 2 Gds Army/28 Army formations (arrived after 17 July).

## 3. Rules the generator applied

For every 17 July formation with a 30 July counterpart (or structural twin, see 4): the 30 July platoons are matched by
hierarchical `code` (bn/coy/platoon). A match with the same role (`real_type` and sprite class) keeps the 17 July node name,
uid, text key, strength `params` and mobility and takes the 30 July composition and support fields (`max_squads`, `range`,
`eng_caps`, `scout_caps`); rifle platoons (`UNI`) keep the 17 July composition unless the formation is mechanised/motorised
(there the 30 July squads replace the old ones). An unmatched 30 July platoon is added as a reserve of the formation (new node
after the formation's last platoon; uid = formation uid prefix | code; the formation's `ai`; `pool` = formation; strength per
formation type, see 5). A code clash between different roles gives the added platoon a free code in the same company. Vehicle
platoons (`STR`, `SUPM`) are added only where the 17 July company has no vehicles, so **tank and SPG counts are unchanged**. HQ
nodes (code 0), battle groups and the formations' reserve squad pools are not touched. Division troops of the 30 July divisions
are split over the regiments on the 17 July map (codes shifted by 0x800/0x900 so they never collide with regiment codes),
because the 17 July division formations are AI placeholders without platoons.

Text: 50 name keys exist only in the 30 July text pack (`op_ra_37sap`, `op_ra_431atbn`, `op_we_294ar_1b1`...); they are copied
into both 17 July text packs (English and Russian) with unit numbers substituted for cloned units; all other added platoons use
the global `oppl_*` keys of `01_loc_kit_plats`. 806 distinct keys are used and all resolve.

Totals per side: 935 platoons added, 174 compositions changed, 40 30 July platoons skipped (vehicles already present), 861 ->
1 796 platoons. The RUS and GER files differ only in the `ai` field and the campgen block, so both get the same OOB.

## 4. Changes unit by unit (platoon detail in `oob_stepanowka_17jul_changes.md`)

Soviet (5th Shock Army, 2 Gds Mech Corps)

| Formation | Template | Before -> after | Added |
|---|---|---|---|
| 362 RR (315 RD) | 30 July 362 RR + 315 RD troops + 1012 AR | 36 -> 73 | sappers, recon, SMG coy, 120 mm FO, ATR coy, AT battery, 76 mm gun battery with FO, battalion FO teams, 50 mm mortar platoons, MG coys, mortar coys; division recon coy; 431 AT bn HQ + 1 battery; 1012 AR FO 1-2 |
| 724 RR (315 RD) | 30 July 724 RR | 34 -> 86 | as above plus a third battalion (HQ, FO, AT, ATR, 7th/8th coy with 2 platoons and 50 mm mortars, 3rd MG coy); 700 sap bn HQ + 1 coy; 431 AT bn 2 battery; 1012 AR FO 3-4 |
| 1328 RR (315 RD) | 30 July 1328 RR | 19 -> 75 | as 362 RR plus 2nd and 3rd battalion structure (the 17 July file had one battalion); 700 sap bn 2 coy; 431 AT bn 3 battery + ATR coy; 1012 AR FO 5-6 |
| 103/105/107 Gds RR (34 Gds RD) | 30 July 103/105/107 | 36/34/34 -> 110/104/103 | full three-battalion regiment with all supports; 34 Gds RD recon coy (103), 37 sap bn HQ + 1 coy (105), 2 coy (107), 38 AT bn HQ + batteries 1/2/3 and ATR coy, 84 Gds AR FO teams 1-6 and 7th/8th/9th gun batteries |
| 116 Gds RR (40 Gds RD) | 30 July 111 Gds RR (116 has no platoons on 30 July) | 20 -> 68 | regiment structure; 40 Gds RD recon coy, 42 sap bn HQ + 1 coy, 41 AT bn HQ + 1 battery + ATR coy, 90 Gds AR FO 1-3 |
| 291 Gds RR (96 Gds RD) | 30 July 291 Gds RR | 23 -> 110 | regiment structure (three battalions); 96 Gds RD recon coy, 111 sap bn HQ + 1 coy, 102 AT bn HQ + 1 battery + ATR coy, 234 Gds AR FO 1-3 |
| 32 Gds TBde | 30 July 32 Gds TBde | 14 -> 27 | recon, sappers, AT battery cmd + 2 ZIS-3 platoons, DShK AA platoon, 82 mm FO, MR company commands, mortar company; tank companies unchanged (3 coys, 21 tanks + bn cmd) |
| 37 Gds TBde (2 Gds MC) | 30 July 37 Gds TBde | 27 -> 37 | recon, sappers, AT battery cmd + 2 platoons, 82 mm FO, mortar coy, SMG coy structure; 6 tank coys unchanged; AA (already present) not duplicated |
| 22 Gds det TR | 30 July 22 Gds TR | 8 -> 11 | recon, sapper and SMG platoons; 4 tank coys unchanged |
| 1543 SAP | 30 July 1543 SAP | 8 -> 10 | regiment command group (KV-1S + BA-64), SU-152 FO team; 12 SU-152 unchanged |
| 4/5/6 Gds MBde (2 Gds MC) | 30 July 13 Gds MBde (4 Gds MC) | 45/44/44 -> 92/91/91 | recon coy (scouts, M3A1, BA-64), SMG coy, engineer coy, 120 mm FO, ATR coy, two mortar coys with FO, AA battery, two ZIS-3 batteries with FO, battalion FO/ATR/SMG platoons, MG platoon per company, MG and mortar coy per battalion; tank regiment unchanged |
| 8 and 15 AT Bde | 30 July 1 Gds AT Bde | 6 -> 15 each | SMG company (cmd + 3 platoons) and sapper company (bn HQ, cmd + 3 platoons); the 5 gun batteries (20 guns) unchanged |

German (XVII AK, 16 PzGr Div, 23 PzD)

| Formation | Template | Before -> after | Added |
|---|---|---|---|
| 513 IR (294 ID) | 30 July 513 IR | 41 -> 67 | bicycle platoon, 13th coy FO (guns already in the 17 July support coy), 14th AT coy (cmd + Pak 40 / Pak 38 / Pak 97/38 platoons), battalion FO teams, 4th/8th/12th MG coys with 8 cm mortar sections, ATR squads in company commands |
| 294 ID | 30 July 294 AT bn, 294 AR | 25 -> 47 | AT bn: bicycle recon coy + 3 AT companies (Pak 38/Pak 35); 294 AR FO teams 1-9 |
| 581 IR (306 ID) | 513 IR pattern | 19 -> 57 | full regiment structure, I-III bn, 13th coy with guns (none before), MG coys; 14th coy not added (the 17 July 14at platoon has it) |
| 572 IR (302 ID) | 513 IR pattern, III bn only | 17 -> 25 | bicycle platoon, III bn FO, 9th/10th coy completed, 12th MG coy, 13th coy; I and II bn stay off-map as in the 17 July file |
| 306 ID, 302 ID | 294 AT bn / 294 AR pattern | 31 -> 53, 13 -> 31 | AT battalion companies and artillery regiment FO teams (302: recon coy not duplicated) |
| 60 MIR, 156 MIR (16 PzGr) | 30 July 156 MIR | 47 -> 70 each | battalion FO teams (8 cm, 7.5 cm), mortar section and MG platoon per company, 4th and 8th heavy coys; rifle platoons take the 30 July squads (support weapons move to the coy platoons); the 17 July III battalions kept |
| 16 PzGr Div | 30 July 146 AR | 39 -> 48 | 146 AR FO teams 1-9 (recon and sapper bns already present) |
| 126 MIR, 128 MIR (23 PzD) | 30 July 126/128 MIR | 38 -> 52, 38 -> 55 | battalion FO teams, mortar/MG platoons, heavy coys completed (SdKfz 250/11 ATR platoon, Pak 40) |
| 23 PzD | 30 July 51 eng bn, 23 recon bn, 128 AR | 21 -> 56 | 51 eng bn HQ + 1 coy, 23 recon bn HQ with FO, armoured-car coy, 2 scout coys with MG/mortar, heavy coy (sappers, Pak 38, IG); 128 AR FO teams 1-9; the APC coy and 2nd/3rd eng coys already present, 201 TR and Marder coy unchanged |

Unchanged: 2 Gds MC HQ, 5 Shock A sapper coy, RGK, air formations, 17 AK training coy, OKH, heavy AT bn "A", 116 tank bn, 201 TR,
210 StuG bn, all off-map formations (293/295 Gds RR, 111/119 Gds RR, 4 Gds RD, 514/515 IR, 29 AK/336 ID, 24 PzK, 2 Gds A).

## 5. Historical reasoning (what was deliberately different from 30 July)

- **Strength.** 17 July was the first day of the Mius offensive; the Soviet rifle divisions were at or near establishment, while
  on 30 July the 30 July file gives battalions a fill of 0.7-0.9 and 0.3-0.5 for the worst. Added Soviet platoons get
  `0.5;0.5;1;0.1` (full), mechanised `0.5;0.6;1;0.1`; the existing 17 July platoons keep their `0.5;0.5;1`. The 17 July
  regiments keep three platoons per rifle company where the 30 July file has two: the three-platoon companies are the 17 July
  author's picture of full-strength units and were not reduced.
- **Germans.** 294, 306 and 302 ID had held the Mius line for months and absorbed the first assault; added platoons get
  `0.5;0.5;0.8;0.2`, and their rifle platoons keep the 17 July composition (two-squad 'inf_41l' platoons) instead of the
  30 July four-squad ones. 16 PzGr Div was refitted at the Sea of Azov from mid-April to mid-July 1943 (lexikon-der-wehrmacht,
  16. ID (mot.)) and 23 PzD was alerted from First Panzer Army reserve on 16 July at 22:35 (feldgrau.net, "Mius July 1943"):
  both arrive fresh, so their added platoons get `0.5;0.6;1;0.1`. Their scripted arrival turns (16 PzGr turn 3-4, 23 PzD turn
  9-10 in the save) are untouched.
- **Tanks.** Vehicle counts are the 17 July author's (32 Gds TBde 21 tanks + command, 37 Gds TBde 44, 22 Gds TR 23, 1543 SAP
  12 SU-152, 201 TR 58, 116 tank bn 24 + Marders, 210 StuG 9). The 30 July file would have given 32 Gds TBde two KV-1 and the
  tank regiments a different company split; none of that was copied because the 30 July tank states are after two weeks of losses.
- **Units not yet there.** 4 Gds MC, the SS divisions, 2 Gds A and 28 A formations, 1./ heavy mortar regiment: not on the
  Stepanovka-Marinovka map on 17 July, so nothing from them except as structural templates. 293/295 Gds RR (96 Gds RD) and
  111/119 Gds RR (40 Gds RD) attacked outside the map; they stay empty AI formations as in the 17 July file.
- **572 IR.** The 17 July file has only III/572 (302 ID's sector was mostly west of the map); I and II bn were not added.
- **Ninth companies.** The 30 July regiments have 7th/8th but no 9th company; the 17 July regiments therefore get the same
  (a full regiment would have one more company per battalion in I and II bn as well; left for a later pass).
- **Sources used.** lexikon-der-wehrmacht.de (16. Infanterie-Division (mot.), 23. Panzer-Division, 294. Infanterie-Division:
  organisation lists, no July 1943 strengths), feldgrau.net topic 20862 (16 PzGr: one tank battalion with 29 Pz III and 7 long
  Pz IV on 10 July 1943; 23 PzD alert 16 July), 294id.de "Juli-Abwehrschlacht am Mius", de.wikipedia "Mius-Operation".
  pamyat-naroda.ru turned up no divisional strength returns for 17 July in the searches made; the Soviet strengths above are
  the "first day, full establishment" assumption, not document figures.

## 6. What to check in game (0.5.0)

Start the game once so the updater installs `mfo_overhaul_0.5.0.gt3ext`; the Version label must list MF Overhaul 0.5.0.
1. Operation list, chapter Mius-Front July 1943: "Stepanovka-Marinovka, July 17" must appear **once** per side. If it appears
   twice, the engine lists both the vanilla and the add-on copy of `07_17_Stepanovka_NA_*.campack2`; report which one carries the
   new units (the add-on copy is the one with the reserves below) and the operation will be renamed in the next build.
2. Start the Soviet 17 July operation. In the deployment phase of any 315 RD / 34 Gds RD / 96 Gds RD / 40 Gds RD regiment, the
   reserve list must now show: sapper platoon, recon platoon, SMG company, AT-rifle company, AT-gun battery (45 mm), regimental
   gun battery (76 mm) with an FO team, battalion FO teams ("1 bn, FO 82 mm"), MG companies, mortar companies, 50 mm mortar
   platoons, the division's recon company, sapper companies, "431/38/41/102 det AT bn" batteries and "1012/84/90/234 AR" FO teams.
3. 4/5/6 Gds MBde: recon company (scouts, M3A1 halftracks, BA-64), SMG and engineer companies, two mortar companies with FO,
   DShK battery, two ZIS-3 batteries with FO. 32/37 Gds TBde: recon, sappers, AT battery, mortar company. Tank companies as before.
4. German side: 513/581 IR show bicycle platoon, 13th/14th companies, MG companies, battalion FO teams; 294/306/302 ID show
   AT battalion companies and "N./294 AR, FO 105 mm" teams; 60/156 MIR and 126/128 MIR show heavy companies and FO teams;
   23 PzD shows 23 recon bn and 51 eng bn platoons and 128 AR FO teams.
5. Play two or three turns: arrival turns (16 PzGr turn 3-4, 23 PzD turn 9-10, 2 Gds MC brigades turn 3-4, 1543 SAP turn 7,
   291 Gds RR turn 6) and the battle groups on the map must be as before. Any platoon showing its key (e.g. `oppl_ussr_1b_1p`)
   instead of a name, or an operation that fails to start, is a bug in this build.
6. Both players of a MiusPlayer game need 0.5.0 (the fingerprint now covers the operation packs).

## 7. Build 0.5.1: artillery regiments, tank platoons, battle-group slots

User on 0.5.0: "no scout or FO in companies; tank companies should be split into platoons like the 30 July campaign; no
artillery regiments and their FO; divisions have their own organic artillery, it should be listed like 30 July" (with the
30 July OOB tree and the 1012 AR panel as the example: the regiment HQ sits in the tree as WAITING, the batteries' FO teams
are IN BG or IN RESERVE).

- **Artillery regiments as formations.** The 17 July file has no artillery regiment formations; its division batteries are
  platoons of the rifle regiments (`ra_315_1arty` in 362 RR...). 0.5.1 creates, per side, `p_ra_1012ar` (315 RD), `p_ra_84ar`
  (34 Gds RD), `p_ra_90ar` (40 Gds RD), `p_ra_234ar` (96 Gds RD), `p_we_294ar` (294 ID), `p_we_146ar` (16 PzGr), `p_we_128ar`
  (23 PzD) from the 30 July formations of the same name, and `p_we_306ar` / `p_we_302ar` from the 294 AR pattern. Each is a
  struct cloned from its division (code/ext_code/name/parent of the 30 July one, `ai` of the division's first regiment that
  has platoons, `divh_reg` sprite) inserted after the division's last regiment, with the 30 July HQ (`CAMP`, "Regiment HQ"),
  the FO team of every battery (`CTRL`, "N battery AR, FO 76/122 mm" or "N./294 AR, FO 105 mm"), the battery commands and
  gun platoons the 30 July file has (4th/6th/7th-9th batteries), plus the 17 July division batteries moved in (`ra_315_1/2/3arty`,
  `ra_34_*`, `ra_40_*`, `ra_234_*`, `wer_294ar_1c_2b/3b`, `wer_128ar_1/2/3abat`; node names kept, so the battle groups that
  hold them still do; codes 0x7/0x8 renumbered where two batteries clashed). The 72 AR and 46 AR battalions attached to
  306 ID stay there (on 30 July they belong to the SS divisions, on 17 July they are corps artillery in the sector).
  Name keys `op_ra_1012ar`, `op_ra_1012ar_hq` ... copied from the 30 July text, `op_we_306ar` etc. substituted.
- **Tank and SPG companies.** A 17 July company is one platoon node whose pool is the company command tank (`*_ccom`) and
  2-3 sections (`*_com` + 2-4 vehicles). 0.5.1 splits every such node (35 per side: 32/37 Gds TBde, 22 Gds TR, the tank
  regiments of 4/5/6 Gds MBde, 201 TR incl. the sIG 33B company, 116 tank bn, 210 StuG bn, 306 ID Marder coy) into a
  company command node (`COMC`, `plu_tankcmd`, the `_ccom` section, name "N tank coy, Command") and one `STR`/`SUPM` node per
  section ("N tank coy, N platoon"; the original node keeps its name and becomes platoon 1, so battle groups stay valid;
  platoon codes are the free codes of the company group, which keeps the 116 tank bn's Marder platoons at their codes).
  Vehicle counts are unchanged.
- **Battle-group slots (0.5.2 rules, user: "mimic the 30 July campaign for the AR and its FOs", "remove FO addition for
  BG", "add one slot to tank battle groups").** Every battle group has a SCT slot (inserted after COM where the 17 July
  file had none). It is filled the way the 30 July file does it: the first battle group of a rifle regiment carries the
  FO team of a division artillery battery (`ra_724_1` SCT = `ra_1012ar_3b_ac`, `we_513_1b` SCT = `we_294ar_6b_ac` on
  30 July), the next one the regiment's own FO (`ra_724_2` SCT = `ra_724_ac76gun`, `ra_362_2` = `ra_362_ac120mt1`; the
  German battalions' `_ac81` mortar FOs) or its recon platoon (`ra_1328_2` = `ra_1328_reconh`); armour battle groups
  carry a recon platoon (`ra_32tbde_1` = `ra_32tbde_recon`) or nothing (`ra_37tbde_1/2`), never an FO team. So on the
  Soviet side half of each artillery regiment's FO teams are IN BG and half IN RESERVE, as in the user's 1012 AR screenshot.
  A battle group that holds a platoon of a split tank company gets a third STR slot (30 July: `ra_32tbde_1` STR = 1c_1p,
  1c_2p, 3c_1p) and the company's remaining platoons fill the STR slots before any other tank platoon, so a company deploys
  as command (in reserve) + three platoons together. Other empty STR/UNI/SUP/SUPM slots are filled with unused platoons of
  the same battalion (mortars first for SUP). A platoon in a slot is deployed with the battle group at the start (IN BG);
  everything else stays IN RESERVE.

What to check in 0.5.3 (new operation, not a save): 1012 AR panel shows "Command: Regiment HQ" first with a map state
(WAITING or placed), then "1 battery AR: FO 76 mm, 1 Arty plt (76 mm)" and so on; the reserve rows say IN RESERVE
instead of blank; on the operational map the AR HQ counter stands with the 362 RR HQ (Soviet) or the division HQ
(German); 234 Gds AR appears on turn 6 with 291 Gds RR, 128 AR on turn 9 with 23 PzD.
What to check in 0.5.2: the quick-battle squad list says "Riflemen (early 1943)" again (no "MFO" prefix); a tank brigade
battle group deploys three tank platoons; the second battle group of a rifle regiment has the regiment's own FO or recon
in the scout slot, the first one an artillery-regiment FO; tank battle groups have a recon platoon or an empty scout slot.
What to check in 0.5.1: the OOB tree shows the artillery regiments under their divisions (1012 AR under 315 RD, 84 Gds AR
under 34 Gds RD, 90 Gds AR under 40 Gds RD, 234 Gds AR under 96 Gds RD; 294/306/302 AR, 146 AR, 128 AR on the German side)
with the regiment HQ WAITING and FO teams IN BG / IN RESERVE; a tank brigade lists "1 tank coy, Command" + "1 tank coy,
1/2/3 tank platoon"; every battle group has a scout or FO entry.

## 8. Build 0.5.3: regiment HQs on the operational map, batteries coded like 30 July, artillery attachments checked

User, after checking 0.5.2 in game (two screenshots of the 1012 AR panel, 17 July next to 30 July): the 17 July regiment
HQ had no state (30 July: WAITING), the batteries moved from the rifle regiments appeared under "Command" / "Arty reg"
above the HQ, the FO teams were all IN BG; "create the regimental HQ on the operational map and check the OOB again;
look into pamyat-naroda for the divisions' artillery support and compare it to the 17 July OOB".

**How the engine places units (found in 0.5.3).** The operation scripts hold only briefing and objective ids
(`opb_*`, `draw_brief_*`); they place nothing. The `desc` table has, next to `reserves` and `act_platoons`, a `plat_pos`
table with one row per platoon: `uid; map cell x; cell z; map node | arrival turn`. Rows with `-1;-1;-1` are reserves.
HQs and battle groups have a node and a turn (16 PzGr turn 3-4, 23 PzD 9-10, 2 Gds MC brigades 3-4, 1543 SAP 7, 291 Gds
RR 6). In the user's post-0.5.1 save every platoon of a formation whose HQ has no map node sits in state 11 (blank in the
panel), while reserves of placed formations are state 4 (IN RESERVE) and slot members state 3 (IN BG). So an artillery
regiment needs a `plat_pos` row for its HQ. 0.5.3 adds one per created regiment: German regiments go with their
division HQ (294/306/302 ID, 16 PzGr, 23 PzD all have an HQ on the map; 30 July puts 1012 AR in the cell of the 315 RD
HQ), Soviet regiments, whose divisions have no HQ in the 17 July file, go with the first regiment HQ of the division
(1012 AR with 362 RR, 84 Gds AR with 103 Gds RR, 90 Gds AR with 116 Gds RR, 234 Gds AR with 291 Gds RR on turn 6).
Every other new platoon gets a `-1;-1;-1` reserve row, as every vanilla platoon has one. **0.5.5:** the new HQ takes
its own map node next to the anchor HQ (a free node linked to the anchor's node in the same cell), because no vanilla
operation puts two units on one node and the 0.5.3/0.5.4 files that did crashed the game after creating the operation.
**0.5.7:** the map-node table (`mg_nodes` column 2, element 0 = uid of the unit on the node) is rebuilt from `plat_pos`
too; the engine reads placements from both and looks units up by that uid (see `docs\oob_saur_mogila.md` 2b), so the
0.5.3-0.5.6 regiment HQs, which had a `plat_pos` row but no node occupant entry, were probably never placed.

**Batteries.** The 17 July division batteries moved into the regiments are now their gun platoons: battery n of
battalion ceil(n/3), code `(bn << 8) | (n << 4) | 2` as on 30 July (`ra_1012ar_4b_1p` = 0x242), so `ra_315_1arty`
(ZiS-3) is 1 battery 0x112 "1 battery, 1 Arty plt (76 mm)", `2arty` 0x122, `3arty` (M-30) 0x132 "3 battery, 1 Arty plt
(122 mm)", matching the calibres of the 30 July FO teams of batteries 1-3 (76/76/122). German: `wer_294ar_1c_2b/3b` →
2./294 and 3./294 AR gun platoons "2./294 AR, 1 arty plt (105 mm)" (name cloned from the 30 July 4./294 key),
`wer_128ar_1/2/3abat` → 1./, 2./, 3./128 AR (3./128 already has two platoons on 30 July, so the old battery becomes its
3rd). Each created regiment is listed HQ first, then battery by battery (nodes sorted by code).

**Reserve links (0.5.9).** User: "the artillery regiments are not accessible to the divisions they are supposed to
be attached to". A battle group's `pool`, `pool2`, `pool3`, `pool4` fields name the formations whose reserves the
player may put into its slots; 30 July groups carry regiment / division / artillery regiment / attachment
(`ra_724_1`: p_ra_724rr, p_ra_315rd, p_ra_1012ar; `we_513_1b`: p_we_513ir, p_we_294id, p_we_294ar, p_wer_294at),
the 17 July groups carried one attachment only (8 or 15 iptabr, or nothing). Every group now links its division and
its artillery regiment first and the old attachments after them, three at most (dropped ones are in the change list).

**Complete batteries (0.5.10).** User: "some artillery batteries lack their FO; FO lacks guns". An FO team's gun
count is the number of guns of its type in the gun platoons of its own company group (code & 0xFF0) in its
formation (see `docs\oob_saur_mogila.md` 2i for the evidence), so the 30 July pattern's FO-only batteries and the
regimental 120 mm mortar FOs showed "0 (4)". Generator pass 2b now moves an FO into the group that holds its guns
(battalion 82 mm FOs into their battalion's mortar company, the regimental 76 mm FO into the gun battery) or adds a
two-gun platoon of its calibre to its group, and adds an FO team to every indirect-fire gun platoon without one
(anti-tank units excluded). The platoon-level list is in `oob_stepanowka_17jul_changes.md` under "Batteries completed".

**Battery commands (0.5.11)** and **FO with its battery (0.5.12).** User: "they lack commander"; "corresponding FO and
their batteries are in different BGs". Every artillery-regiment battery with FO and guns now has a battery command
(Command / FO / Arty plt). A rifle battle group that holds a battery in a SUP slot (the 17 July file attaches the 1st,
2nd and 3rd batteries to the 362, 1328 and 724 RR groups) gets that battery's FO team in its scout slot; a group
without a battery gets an FO whose battery is in reserve, so an FO is never separated from its guns by another group.

**Battery out when its FO is in (0.5.13).** User: "remove artillery batteries from BG if their own FO is already in
said battlegroup". When the scout slot takes a battery's FO team, that battery's gun platoon leaves the group's SUP
slot and stays in the regiment's reserve (it fires through the FO; the freed SUP slot is filled from the rifle
regiment as any other empty slot). Nine groups per side are affected (362/1328/724 RR, 116 Gds RR, 291 Gds RR, 294 ID
2nd/4th, 128 MIR 1st). **22 Gds TR (0.5.13).** User: "move 2 tank coy, 2 tank platoon to 2/22 det gds TR in place of
4 tank coy, 1 tank platoon and move it to reserve": pass 3b swaps the slot references after the fill pass; the slot
the 2nd platoon leaves in 1/22 is refilled from the companies already in that group, or stays empty when none has a
spare platoon.

## 9. Artillery support of the rifle divisions: sources vs the 17 July file

pamyat-naroda.ru answered every automated request with a captcha page ("Подтвердите, что вы не робот"), which this
session does not solve, so the division journals could not be read here; the user can open the 5 Уд. А and 315 сд
unit pages there directly. The official snapshot closest to 17 July that was readable is *Боевой состав Советской Армии*
for 1 August 1943 (Генштаб, 1972; copy at tashv.nm.ru via the Wayback Machine), plus the division articles (ru/en
Wikipedia, Sharp "Red Guards", Glantz "After Stalingrad"):

| Division | Organic artillery (sources) | In the 17 July file (0.5.3) |
|---|---|---|
| 315 сд (5 Уд. А) | 1012 ап; 431 оиптд | `p_ra_1012ar` (HQ, FO 1-6/9, batteries 1-3 from the file, 4th/6th from 30 July); 431 AT bn companies as division troops under the regiments (0x8xx) |
| 34 гв. сд (31 гв. ск, 5 Уд. А) | 84 гв. ап; 38 гв. оиптд | `p_ra_84ar` (HQ, FO 1-9, batteries 1-3 + 7-9) |
| 40 гв. сд (31 гв. ск) | 90 гв. ап; 41 гв. оиптд | `p_ra_90ar` (HQ, FO 1-3, batteries 2-3; only 116 Gds RR is in the sector) |
| 96 гв. сд (5 Уд. А on 1 Aug) | 234 гв. ап; 102 гв. оиптд | `p_ra_234ar` (arrives with 291 Gds RR, turn 6) |

Army artillery of 5 Уд. А on 1 August 1943 (Боевой состав): 506 and 1162 пап, 331 гап, 8 and 15 иптабр, 491 and 507 иптап,
489 минп, 15 зенад; armour 32 гв. тбр, 22 гв. отп. Of 2 гв. А: 2 гв. адп (4 гв. лабр, 114 пабр, 5 гв. габр, 20 гв. габр БМ,
33 минбр), 1095 пап, 113 гв./14/747/1255 иптап, 19 минбр, 483 минп; 2 гв. мк (4, 5, 6 гв. мбр, 37 гв. тбр), 4 гв. мк, 7 гв.
отп, 1543 сап. The 17 July file has 8 and 15 иптабр (their batteries sit in the rifle battle groups as attached AT
support), 32 гв. тбр, 22 гв. отп, 2 гв. мк with 37 гв. тбр and 1543 сап, i.e. the anti-tank and armour attachments are
right. Not in the file: the army gun and howitzer regiments (506, 1162 пап, 331 гап), the mortar regiment 489 минп, 491
and 507 иптап and 1 гв. истребительная бригада, and on the 2 гв. А side the 2 гв. адп. These fired from outside the
6M_Mius box; the engine models them as the off-map `rkka_artsup_*` rows in the formation pools (zis3, m30, mt120, pp27
support batteries in `p_ra_724rr`), which the 17 July file already has. Adding 506/1162 пап and 331 гап as off-map
152 mm / 122 mm support rows would be the next historical step (0.5.4 candidate, not done here).

## 10. Open

- Whether the engine lists an operation pack from an add-on folder next to the vanilla one or in place of it is untested
  (quick battles from add-on `camps\qb\` folders are listed additively). If it lists both, the add-on copy gets its own `op_id`.
- The new artillery regiment HQs have no scripted map node (they show as WAITING like the 30 July 1012 AR HQ does in the
  user's screenshot); if the engine objects to a formation without a placed HQ, the fallback is to drop the HQ node.
- `params` component meanings are inferred from the 30 July values (fill / experience / morale-like / spread); unverified.
- The deployment screen may cap reserves per battle group; the extra reserves are then simply more choice.
- `div_pool` was left vanilla (it holds a subset of platoons in the 30 July file, so the engine does not require all platoons in it).

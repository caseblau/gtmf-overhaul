# Table semantics: `div_units_*` and `qbattle` (Mius-Front 6.00 build 3598)

Worked out 2026-10-15 from the pristine tables in `<game>\users\modwork\_orig\3598\` (`tabs_oprum.flatdata` →
`div_units_ussr`, `div_units_ger`, `div_units_misc`, `qbattle`; `tabs.flatdata` → `sides`, `common_res_mod`,
`ger_hum_base`; `tabs_oprum` → `rus_hum_base`), the English text packs (`01_loc_kit_units`, `01_loc_kit_plats`,
`02_loc_qbattle`, `00_loc_kit_weaps`), Graviteam's own Operation Star manuals (Addon Creation Guide 2009, Operation
Editor Manual 2012; both describe the *text* form of these same tables) and MiusPlayer's decompile notes. No game file
was changed.

How to reproduce any number here:

```powershell
$orig = "$env:GTMF_ROOT\users\modwork\_orig\3598"
tools\gt3.ps1 nodes "$orig\tabs_oprum\div_units_ussr.config.loc_def.bin"            # node list with type strings
tools\gt3.ps1 csv   "$orig\tabs_oprum\div_units_ussr.config.loc_def.bin" squads squads_ussr.csv
tools\gt3.ps1 csv   "$orig\tabs_oprum\qbattle.config.loc_def.bin" '*' qbattle_csv\     # one CSV per node, index-prefixed
tools\gt3.ps1 text  "$orig\text_loc\01_loc_kit_units.text.loc_eng.bin" units_eng.csv  # key,short name,long name
```

**Confidence legend:** `high` = stated by Graviteam's manual or verified by cross-reference / full-column census;
`medium` = consistent pattern across all rows, meaning inferred; `low` = values catalogued, meaning guessed or unknown.

## 0. Cell format and type characters

Every AZCF table node carries a *type string*, one character per column (`nodes` prints it). The characters are
the same ones Graviteam's text format uses (Addon Creation Guide, table 3):

| char | binary cell kind | content | CSV rendering by `gt3.ps1 csv` |
|---|---|---|---|
| `s` | 2 | string (cp1251, NUL-terminated; length + offset in the cell) | text |
| `u` | 4 | unsigned 32-bit: a number, a **FCC code** (2–4 capital letters packed little-endian: `INF` = 0x00464E49, `USSR`, `MT`) or a **date** `0xYYYYMMDD` | `INF` / `0x19430801` / `150` |
| `a` | 6 | vector of up to 4 signed ints (a scalar int is a 1-vector) | `100;32;16;1` (trailing zeros dropped) |
| `v` | 1 | vector of up to 4 floats | `0;0.5` |
| `f` | 0 | one float | `0.5` |
| `b` | 5 | bool | `0` / `1` |

A cell is 0x20 bytes: four 32-bit value slots, the kind at +0x10, three zero words. Tables are `rows × cols × 0x20`
contiguous; struct nodes (`type=1`) are `rows × 0x40` (cell + 0x20-byte field name). Strings live in a shared pool
(the empty string is one shared offset), so a row can be edited in place for numbers and for *same-length or shorter*
strings; anything else must append a new string and re-point the cell (what `Set-AzcfStringField` already does).

Dates are plain hex-coded calendar dates (`0x19421201` = 1 Dec 1942); the manual calls the format `0xYYYYMMDD`.
Sides are FCC codes from `sides.sides` column 0: `USSR GER UK USA FIN RUM ITA …`. Organisations are FCC codes from
`sides.orgs` (`NKVD BG CAV MR` for the USSR, `SS PZGR JAG GEB` for Germany).

## 1. `div_units_*` → node `units` (17 cols, type `sssssuuvssssbssss`)

One row per *unit*: a soldier type or a single vehicle/gun. ussr 156 rows, ger 197, misc 57 (Finnish, Romanian…).
The engine merges every `div_units*` entry it finds into one list (manual: "each installed patch or addon … adds a
description of units or subdivisions to the common list; in case of duplication the first one found wins"), which
is why `div_units_ger` can reference `usau_*`/`uku_*` units that live in DLC tables.

| col | type | meaning | example (`rkkau_inf_serg` / `rkkau_t34_42_uztm`) | conf |
|---|---|---|---|---|
| 0 | s | **unit id**. Prefix = side (`rkkau_`, `weru_`, `finu_`…). Referenced by `squads` member slots. | `rkkau_inf_serg` / `rkkau_t34_42_uztm` | high |
| 1 | s | encyclopedia/UI key `ui_*` for vehicles and guns (text in `00_loc_kit_weaps`, data in `ui_params`); empty for soldiers | `` / `ui_t34_m42utz` → "T-34 mod 1942" | high |
| 2 | s | engine class: `i_human` (252 rows) or `i_techn` (158) | `i_human` / `i_techn` | high |
| 3 | s | config file holding the unit definition: `tabs\rus_hum_base.cfgpack`, `tabs\ger_hum_base.cfgpack`, `tabs\techn_base.cfgpack`, `tabs\techn_base_oprum.cfgpack` | `tabs\rus_hum_base.cfgpack` / `tabs\techn_base.cfgpack` | high |
| 4 | s | **node name inside that file**: soldier type (`rus_inf_serg` → struct in `rus_hum_base`, a `redirect` chain to a base soldier with `type`, `mesh`, `ammo_pat`, `outfit_pat`, skins) or vehicle (`t34_utz_m42` in `techn_base`) | `rus_inf_serg` / `t34_utz_m42` | high |
| 5 | u | **crew size** of a vehicle/gun (crew slots the unit has). 0 for soldiers. T-34 4, KV-1 5, ZIS-3 7, F-22 8, IL-2M3 2, Po-2 2, A-20 3, I-152 1 | `0` / `4` | high |
| 6 | u | **passenger capacity** (tank riders / APC seats). T-60 8, T-34 12, KV-1 16, Churchill 23, SdKfz 251 9, guns 0 | `0` / `12` | medium |
| 7 | v | two floats for soldiers, 0 for vehicles. Grows with rank: rifleman `0`, MG gunner `0.1;0.1`, sergeant `0.2;0.2`, lieutenant `0.5;0.5`, captain `0.7;0.7`, major `0.9;1`, tank officer `0.3;0.05`. Probably command/leadership ratings. | `0.2;0.2` / `0` | low |
| 8 | s | **crew position / role tag** `wp_*`: `wp_icommander` (infantry leader, 54 rows), `wp_commander` (vehicle commander, 41), `wp_driver`, `wp_gunner`, `wp_mgunner`; empty otherwise | `wp_icommander` / `` | medium |
| 9 | s | model/skin variant override (8 rows: `53k37`, `53k43`, `kv1s_mid`, `kv1_42_chkz_sw`…) | `` | medium |
| 10 | s | armour-map override `arm_*` (2 rows: `arm_kv1_42_cast_dift`, `arm_kv1_42_rfcast_dift`) | `` | medium |
| 11 | s | model variant override (2 rows: `il2m3v`, `sdkfz231_8`) | `` | low |
| 12 | b | flag, set on exactly one row (`rkkau_t34_41_stz`) | `0` | low |
| 13 | s | set on one row only: `coc_t34_41stz` (same T-34 STZ row) | `` | low |
| 14 | s | always empty in vanilla | `` | low |
| 15 | s | set on one row only: `kv1s_655cr_hp` (`rkkau_kv1s_m42`) | `` | low |
| 16 | s | **main weapon id** for towed guns/mortars/some tanks (`76L42`, `75L24`, `GRW34`, `MT82`, `MT120`, `152L29`…), keys of `common_res_mod.weapons`; 34 rows | `` | medium |

References out of `units`: col 3+4 → `*_hum_base` / `techn_base*` node; col 1 → `ui_params`, `00_loc_kit_weaps`;
col 16 → `common_res_mod.weapons`.
`units` ids are **not** text keys: none of the 410 appears in `01_loc_kit_units` (the UI names soldiers through the
squad or the `ui_*` key).

## 2. `div_units_*` → node `squads` (30 cols, type `ssssususauuuvuuuvususususususu`)

One row per *squad*: an infantry squad, a command group, a gun with its crew, a vehicle with its crew, or a bare
crew/team that other squads nest. ussr 347 rows, ger 362, misc 50. The manual's text form of a row is
`rkka_squad_inf_43a, sq_inf, txt_ce_rkka_squad_inf_43a, …, rkkau_inf_sergant, 1, rkkau_inf_rifle, 6, …` — the
member list "begins at the first unit name; after each inclusion a number of units; delete an entry by writing `, 0,`".

| col | type | meaning | example (`rkka_squad_inf_43a`) | conf |
|---|---|---|---|---|
| 0 | s | **squad id**. Prefix = side (`rkka_`, `wer_`, `fin_`, `rum_`). Referenced by `qbattle` pools, `randoms`, `trophy` and by other squads' member slots. | `rkka_squad_inf_43a` | high |
| 1 | s | **trophy class** `tr_*` (row of node `trophy`) this squad belongs to when captured; empty = cannot be a trophy. 129 rows set, all vehicles/guns/scouts. | `` (T-34: `tr_rkka_med_tank`) | high |
| 2 | s | **squad class** `sq_*` (26 values): `sq_tank sq_crew sq_com sq_inf sq_apc sq_spg sq_gun sq_atgun sq_mg sq_eng sq_mortar sq_atr sq_atspg sq_sup sq_scout sq_spam sq_air sq_pzgr sq_art_corr sq_acar sq_flamer sq_cons sq_air_corr sq_atapc sq_spgapc sq_sniper`. Engine-internal tags (found only in `div_units*`); `sq_crew` marks nested crews/teams. | `sq_inf` | high |
| 3 | s | secondary class, 138 rows: `sq_mg` (rifle squads with an MG, AT guns), `sq_sup`, `sq_inf`, `sq_com`, `sq_atr`. Meaning not established (possibly the class of the detachable sub-team or the fallback class). | `sq_mg` | low |
| 4 | u | **flag bits**, 33 distinct values, 0 for 621 rows (all crews, vehicles, most guns). Bit census: bit0 (11 rows: `*_phone`, `wer_at_team`, cavalry MG/ATR), bit2 (26: battalion/regiment HQs, repair `*_spam`), bit3 (59: HQs, `*_spam`, `sup_mot`), bit4/5/6 (66–69: rifle, MG, ATR, engineer squads), bit7 (52) and bit8 (41) (1943 rifle/engineer squads), bit9–11 (1941–42 rifle, scout, NKVD), bit12 (7: Pz.Gren. 1941–43), `wer_com_mnt_coy` = 0xFE00. Different flag set from the pool flags in §4. **Copy the value from a similar vanilla squad when cloning.** | `384` (0x180) | low |
| 5 | s | **text key** in `01_loc_kit_units` (short name, long name). Usually = col 0; vehicles share generic keys (`rkka_mtank`, `rkka_ltank_com`); nested crews use `squad_unk` (empty text). 591/759 rows resolve; `fin_com_hvy_coy` is the only real miss. | `rkka_squad_inf_43a` → "Squad" / "Riflemen (early 1943)" | high |
| 6 | u | **squad type** FCC: `CREW` (180, nested), `COM` (120, platoon leaders), `INF` (117), `COMC` (92, company HQ), `TANK` (83), `COMB` (30, battalion HQ), `ATG` (28), `APC` (17), `MT` (15, mortar), `SPG` (15), `MGUN` (13), `CAR` (10), `GUN` (8), `CORR` (8, spotter), `AIR` (7), `COMR` (6, regiment HQ), `HOWI` (6), `ACAR` (4). The non-command codes are rows of `sides.unit_types` (icon, hidden-class, `ot_*` object type). | `INF` | high |
| 7 | s | **communication-link profile**, key of `common_res_mod.links` (`rus_lnk_std`, `rus_lnk_sup`, `rus_lnk_wire`, `rus_lnk_air`, `ger_lnk_std/lim/sup/half/com/port/wire/wire_ext/air`, `ll_lnk_std/ext`, `usa_tlnk_std`); empty = no radio/phone. Set on HQs, command vehicles, phone squads, spotters, halftracks. | `` (phone squad: `rus_lnk_wire`) | high |
| 8 | a | 4 ints `[value, code1, code2, flags]`. `[0]` scales like a point value: crews 0, rifle squad 100, HQ/phone/MG 150–200, SdKfz 251 300, ZIS-3 350, T-34 550, Pak 40 550, T-34 cmd 600. `[1]` (16–97, 546) and `[2]` (16–98) look like category codes: `[2]` upper nibble 1 = infantry, 2 = tank, 3 = ?, 4 = APC, 5 = gun, 6 = MG/mortar. `[3]` is a bit set (1 for 389 rows; 16/17 guns and tanks; 512 mortars; 2 heavy MG; 3 ATR). Crews are `0;0;0;1`. | `100;32;16;1` | low |
| 9 | u | **category** FCC: `TECH` (353, vehicles), `INF` (165), `ART` (52, guns/mortars), `LARM` (22, heavy MGs = light arms?), `0` (167 crews) | `INF` | medium |
| 10 | u | **role** FCC: `COM` (168, all command rows), `STR` (132, line tanks = "strike"), `UNI` (45, rifle squads = universal), `SUP` (40, guns), `SUPM` (39, APCs = mobile support), `SCT` (38), `IHW` (37, infantry heavy weapons), `SPEC` (31, engineers/ATR/flame), `MISC` (24, supply/repair), `MINF` (14, Pz.Gren.), `TRAN` (10, trucks), `COMM` (6, phone), `SPOT` (5), `SPOA` (3, air spotter), `0` crews. Same vocabulary as the platoon `type` field in `qbattle` (§4), so this is what the AI/pool logic reads. | `UNI` | medium |
| 11 | u | **map icon / unit kind** FCC: `TANK` (224), `INF` (106), `TEAM` (70, HQs and spotters), `SPG` (63), `APC` (63), `GUNL` (22, light gun), `GUN` (15), `MG` (11), `MORT` (10), `AIR` (7), `PBX` (1), `0` crews | `INF` | medium |
| 12 | v | 2 floats, `0` for crews. `[0]` steps with vehicle class: 0 infantry/guns, 1 light vehicles/T-60/UC, 1.5 T-50, 2 Matilda/BT, 3 T-34, 3.5 KV-1S/SU-152, 4 KV-1/Tiger. `[1]`: HQ 0.25, rifle squad 0.5, ATR/MG squad 1.5, field gun 1.75, Pak 40 2, howitzer 3, sFH 5, T-34 2, Tiger 4, truck 0.1. Reads as AI threat/strength ratings (armour class, firepower). | `0;0.5` | low |
| 13 | u | **begin date** `0xYYYYMMDD` (availability window start); 0 for crews | `0x19421201` | high |
| 14 | u | **end date**; `0x19431201` for 321 rows | `0x19430801` | high |
| 15 | u | **side** FCC (`USSR`, `GER`, `FIN`, `RUM`); 0 for crews | `USSR` | high |
| 16 | v | 1–2 floats, 0 for 460 rows. Scalar 0.1–1.5 on dated line units (T-34 1.5, rifle 42a 0.5, pen_43a 0.2, tank-crew squads 0.1); `0;N` (N = 1,2,3,5) only on T-50 variants and SdKfz 232 command cars. Looks like a rarity/weight for random generation, with the `0;N` form a cap. | `0` | low |
| 17 | u | **organisation** FCC from `sides.orgs` (`PZGR`, `SS`, `MR` motor-rifle, `GEB`, `JAG`, `CAV`, `NKVD`); 0 = regular army (668 rows) | `0` | high |
| 18 | s | **member slot 1: unit or squad id** (leader; `rkkau_inf_serg`, `weru_art_com`, a vehicle…) | `rkkau_inf_serg` | high |
| 19 | u | slot 1 count (1 in 752 rows) | `1` | high |
| 20 | s | member slot 2 id | `rkkau_inf_rifle` | high |
| 21 | u | slot 2 count | `5` | high |
| 22 | s | member slot 3 id | `rkkau_inf_arifle` | high |
| 23 | u | slot 3 count | `1` | high |
| 24 | s | member slot 4 id | `rkka_inf_mg` (a `sq_crew` squad: MG gunner + assistant) | high |
| 25 | u | slot 4 count | `1` | high |
| 26 | s | member slot 5 id (60 rows) | `` | high |
| 27 | u | slot 5 count | `0` | high |
| 28 | s | member slot 6 id (15 rows) | `` | high |
| 29 | u | slot 6 count | `0` | high |

Member resolution across the three files: 1485 slot ids are `units` rows, 490 are `squads` rows (450 `CREW`,
34 `APC`, 6 `INF`), 13 are units from DLC tables (`usau_*`, `uku_*`, `funu_hmg`, `ger_pinf_soldier1`). A vehicle
squad is `[vehicle unit ×1, crew squad ×1]` (`rkka_t34_42_uztm` = `rkkau_t34_42_uztm` + `rkka_crew_t34`); the crew
squad lists the crewmen (`rkkau_tank_com`, `rkkau_tank_agun ×2`…) and the vehicle's col 5 says how many seats exist.
An empty slot is `"" , 0`.

**To change a composition in milestone 1:** edit cols 18–29 (ids must exist in `units` or `squads` of any
`div_units*` file), keep col 4 and col 8 from the vanilla row you cloned, set cols 13–14 to the period, and give a
new row its own col 5 text key in `01_loc_kit_units` (two items: short, long). A new squad is only reachable once
a `qbattle` pool or platoon lists it (§4) or an operation file does.

## 3. `div_units_*` → nodes `randoms`, `trophy`, `supports`

### `randoms` (7 cols, `sssssss`)
`rn_*` id + up to 6 squad ids; the game picks one at random, repeats weight the choice (`rn_rkka_t50_early` lists
`rkka_t50_41` five times). Pools and platoons may reference an `rn_*` instead of a squad (154 pool rows do). Confidence high.

| col | meaning | example |
|---|---|---|
| 0 | random-group id | `rn_rkka_div_gun` |
| 1–6 | candidate squad ids, empty when unused | `rkka_zis3`, `rkka_f22_m36`, `` … |

### `trophy` (3 cols, `sus`)
| col | meaning | example | conf |
|---|---|---|---|
| 0 | trophy class id, referenced by `squads` col 1 | `tr_rkka_mg` | high |
| 1 | side FCC the captured equipment comes **from** (`GER` in the USSR table, `USSR` in the German one) | `GER` | high |
| 2 | squad or `rn_*` group that is spawned as the trophy | `rkka_mg34` / `rn_rkka_bat_mort` | high |

### `supports` (15 cols, `ssuaaassavsuuuu`) — off-map artillery and air support
Referenced by `qbattle` pool rows (col 3) through a spotter squad (`rkka_corr_art` + `rkka_artsup_zis3_plat`).

| col | type | meaning | example (`rkka_artsup_zis3_plat`) | conf |
|---|---|---|---|---|
| 0 | s | support id | `rkka_artsup_zis3_plat` | high |
| 1 | s | text key in `01_loc_kit_units` (several ids share one key) | `rkka_artsup_zis3_plat` → "76.2 mm ZIS-3" | high |
| 2 | u | kind FCC: `ART` (52) or `AIR` (7) | `ART` | high |
| 3 | a | up to 4 ints, 0 for air. ZIS-3 `100;10;50;20`, MT-120 `50;20;30`, PS-3 `180;18` — probably rounds/stock per shell type | `100;10;50;20` | low |
| 4 | a | int 0/4/5/10/12 (0 for air) | `10` | low |
| 5 | a | `[guns, N, 0, k]`: `[0]` = number of tubes (plat 4, section 2, coy 6, B-4 ×2/×3), `[1]` ≈ 100–500 per tube, `[3]` 8–20 | `4;400;0;16` | medium |
| 6 | s | weapon id in `common_res_mod.weapons` (`ZIS3`, `MT120`, `ML20S`, `B4`, `NBW41`) | `ZIS3` | high |
| 7 | s | shell id in `common_res_mod.shells` | `76L42_OF_350` | high |
| 8 | a | 1–4 ints (`5;0;0;2`, `3`, `15;14` for air) | `5;0;0;2` | low |
| 9 | v | `0.5;T;n` — `[0]` always 0.5, `[1]` 2.2–20 (bigger for heavier guns), `[2]` 1–5 | `0.5;13;2` | low |
| 10 | s | aircraft squad id for `AIR` rows (`rkka_il2_m3`, `wer_ju87_d3`) | `` | high |
| 11 | u | planes per sortie for `AIR` (3, once 2); 0 for artillery | `0` | medium |
| 12 | u | begin date | `0x19420501` | high |
| 13 | u | end date | `0x19431201` | high |
| 14 | u | side FCC | `USSR` | high |

## 4. `qbattle` (646 nodes) — quick-battle formations, pools and platoons

Layout (node order matters, names repeat):

```
version   struct  version=2
default   struct  user_side=USSR enemy_side=GER year=4 period=2 district=polygons\6m_mius\6m_mius.cfgpack
ccombat   table   343 × (map id, placement id cc_plc_*, a:4 ints)      — map/placement slots, not unit data
reserves  struct  (empty)
p_<side>_<formation>  struct   ← a formation ("pool of reserves"), 54 of them (28 USSR, 26 GER)
pool                  table 4 cols `suus`  ← its reserve list, immediately after the struct
… (54 pairs)
act_platoons  struct  camo=""
<side>_<platoon>      struct   ← a platoon template, 266 of them
pool                  table 3 cols `sus`   ← the squads that compose it, immediately after the struct
… (266 pairs)
```

`gt3.ps1 csv <qbattle> '*' <dir>` names files `<index>_<name>.csv`, so each `pool` sits right after its owner.

### 4.1 Formation struct `p_*` (11 fields, order varies slightly)
Field names are the engine's own (the manual documents them for operation files; identical here).

| field | type | meaning | example (`p_ra_rr1242`) | conf |
|---|---|---|---|---|
| `code` | u | formation code (battalion/regiment/division id; low values, reused across sides) | `16` | medium |
| `name` | s | text key in `02_loc_qbattle` | `qb_ra_rr1242` → "Gds rifle regiment org. No.04/501 of 12.42" | high |
| `sold_fams` / `sold_names` | s | surname / first-name tables (`sn_ussr_fams`, `sn_ger_fams`) | `sn_ussr_fams` | high |
| `marks_name` | s | vehicle marking set from `markers_01` (`rkka_marks_01`, `wer_marks_23pz`, `wer_marks_lah_pzgr_ss`) | `rkka_marks_01` | high |
| `div_sprite` | s | formation icon (`div_inf`, `div_tanks`, `div_art`, `div_cav`…) | `div_inf` | high |
| `div_sprite_op` | s | echelon icon: `divh_coy`, `divh_batn`, `divh_reg`, `divh_bde`, `divh_div` | `divh_reg` | high |
| `side` | u | side FCC | `USSR` | high |
| `wei` | u | weight: 500–10000 (5000 for 19 formations, 1000–1200 for most others). Not in the manual; likely selection weight / size budget of the formation in the quick-battle generator. | `1000` | low |
| `beg_date` / `end_date` | u | availability window | `0x19421201` / `0x19431201` | high |

### 4.2 Formation `pool` table (4 cols, `suus`) — reserves of the formation
The manual: "each line describes the squad in reserve: name, quantity, flags (table 1.1) … name of support".

| col | type | meaning | example | conf |
|---|---|---|---|---|
| 0 | s | squad id (`squads`, 198 rows) or random group `rn_*` (`randoms`, 30 rows); all 228 resolve | `rkka_corr_art`, `rn_rkka_div_gun` | high |
| 1 | u | quantity available (1–8) | `1` | high |
| 2 | u | **squad flags**, table 1.1 of the Operation Editor manual: `0x01` historical, `0x02` non-historical (player can disable in game settings), `0x08` repair brigade, `0x10` supply brigade, `0x20` draft reinforcements, high byte = historical-reference text index. Vanilla uses only 0 (193 rows) and 2 (35 rows: DShK, M-42, flame-throwers, late tanks in early formations…). | `0` | high |
| 3 | s | **support id** (`supports` node) attached to this entry; set only on spotter squads `rkka_corr_art/air`, `wer_corr_art/air` (29 rows). This is where off-map artillery and air strikes come from. | `rkka_artsup_zis3_plat` | high |

### 4.3 Platoon struct (7–10 fields)
| field | type | meaning | example (`ra_rr1242_smg_plat`) | conf |
|---|---|---|---|---|
| `code` | u | hierarchical code, manual: hex digits = platoon / company / battalion (`0x311` = bn 3, coy 1, plat 1); unique inside its pool | `785` (0x311) | high |
| `name` | s | text key in `02_loc_qbattle` | `qbp_ra_rr1242_smg_plat` | high |
| `str_sprite` | s | platoon sprite (`plu_smg`, `pl_t34_42`, `pl_zis3`…; manual table 3.1) | `plu_smg` | high |
| `max_squads` | u | maximum squads in the platoon (2–14; absent on 79 platoons) | `5` | high |
| `mobility` | u | FCC `STAT FOOT HORS WHEL PIL` (+ `ASUP AIR` per manual); `PIL` is used by every tracked/motorised platoon | `FOOT` | high |
| `pool` | s | owning formation (`p_*` struct name); all 266 resolve | `p_ra_rr1242` | high |
| `type` | u | AI role FCC: manual lists `STR` offensive, `SUP` support, `SCT` scout, `UNI` universal; Mius-Front adds `COM` (24), `COMC` (72, company HQ), `SUPM` (15, mobile support), `REP` (2, repair) | `UNI` | high |
| `beg_date` / `end_date` | u | optional availability window (51 platoons) | — | high |
| `uid` | u | unique platoon id, 0xSSPPCC-like (`0x420311`); 261 distinct of 266 | `4326161` | high |

### 4.4 Platoon `pool` table (3 cols, `sus`) — composition
| col | type | meaning | example | conf |
|---|---|---|---|---|
| 0 | s | squad id or `rn_*` group (652 + 124 rows, all resolve) | `rkka_com_smg_plat`, `rkka_squad_smg_43a` | high |
| 1 | u | quantity (1–6) | `1`, `3` | high |
| 2 | s | optional commander name id (manual); always empty in vanilla | `` | high |

The first row of a platoon pool is its leader group (`rkka_com_*`), the rest the line squads. A Duel pool for M3
is therefore: one `p_*` struct (name key, side, dates, `wei`), its 4-col reserve table (what the host can add,
including spotter + `supports` rows), and a set of platoon structs each followed by a 3-col composition table.

## 5. Cross-reference map

| from | column | to |
|---|---|---|
| `squads` c18/c20/…/c28 | member id | `units` c0 (any `div_units*`), or `squads` c0 (`sq_crew`, APC, INF rows) |
| `squads` c1 | trophy class | `trophy` c0 |
| `squads` c5, `supports` c1 | text key | `01_loc_kit_units` (short, long) |
| `squads` c2/c3 | class | engine-internal; class *names* for the UI live in `01_loc_kit_plats` (`sq_rif_squad`…), not keyed by these values |
| `squads` c6 | type FCC | `sides.unit_types` c0 |
| `squads` c7 | link profile | `common_res_mod.links` c0 |
| `squads` c15, `supports` c14, `trophy` c1, `p_*.side` | side FCC | `sides.sides` c0 |
| `squads` c17 | organisation | `sides.orgs` c0 |
| `units` c3 + c4 | definition | `rus_hum_base` / `ger_hum_base` / `techn_base` / `techn_base_oprum` node |
| `units` c1 | ui key | `00_loc_kit_weaps`, `ui_params` |
| `units` c16, `supports` c6 | weapon id | `common_res_mod.weapons` c0 |
| `supports` c7 | shell id | `common_res_mod.shells` c0 |
| `supports` c10 | aircraft squad | `squads` c0 |
| `trophy` c2, pool c0, platoon pool c0 | squad or random | `squads` c0 / `randoms` c0 |
| formation pool c3 | support | `supports` c0 |
| platoon `pool` field | formation | `p_*` struct name |
| `p_*.name`, platoon `name` | text key | `02_loc_qbattle` |
| `p_*.marks_name` | markings | `markers_01` |
| `p_*.sold_fams/sold_names` | name tables | `16_sold_fams_names` |

## 6. What the decompiled loader does and does not tell us

`_mp_dl\dec\adv_game.divisions_loader.txt` is `adv_game.codelib`'s loader for `config\tacplc_image.cfgpack` — the
*battle image* (`pools`, `plats`, `supports`, `squads`, `units`, `sup_tasks` nodes written when a battle starts),
not for `div_units`. Its row-format strings (`"$a$2a2$a$v$a"`, `"$**uv*4b"`, `"$u$3vuvu2a$a$au$va2$3uav"`) confirm
the type system (`$` string, `u`, `v`, `a`, `b`, digit = vector width, `*` = skip) and that the battle code receives
squads already expanded by the operation layer (`adv_opgame`, not decompiled). The `div_units` column meanings above
therefore rest on the data census and Graviteam's manuals, not on code. The surest way to raise a `low` entry is a
controlled in-game test (clone a squad, change one value, compare).

## 7. Open questions (for milestone 1 to settle by experiment)
- `squads` c4 bit meanings and c8 codes: cloning keeps them consistent, but a new squad *type* (e.g. an SMG squad
  with an LMG team) should copy from the nearest vanilla row and be checked in the quick-battle editor.
- `squads` c12/c16 ratings: whether they affect AI or only generation.
- `p_*.wei` and formation `pool` col 2 non-historical flag: verify that `0x02` entries disappear with the
  "historical squads only" game option.

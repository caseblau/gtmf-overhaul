# Prokhorovka, 11-14 July 1943 — order of battle of both sides and how it is built

The operation now starts at 06:00 on 11 July (turn 1; 4 h turns, 21 turns to 14 July 14:00) with the units that were
on the ground that morning, and brings the 5 gds Army and 5 gds Tank Army formations in on the turns they historically
arrived. `tools\oob_12jul.ps1` builds the formations from the 30 July 1943 Stepanovka files (whole formations cloned under
new names, the Mius formations removed), sets their strength parameters and vehicle numbers, and
`docs\m11_prokhorovka\layout_12jul.json` gives every formation its position or its arrival turn and map edge.

Numbers below are the evening-11-July states from Zamulin's tables ("Прохоровка — неизвестное сражение", appendix
tables of 5 gds TA on 11/12 July) and the II SS-Panzerkorps returns as given by Zetterling & Frankson and Lawrence
(The Battle of Prokhorovka), reproduced from memory because neither source could be fetched from here; they are the
usual published figures but should be checked against the books before the numbers are treated as final. Figures
marked ~ are estimates.

## Soviet

**5 gds Tank Army** (Rotmistrov) — 793 tanks and 37-57 SP guns on 11 July; arrives from the east through Prokhorovka.

| Formation | Template (30 July) | Tanks / SP (11 July) | Men | Arrival |
|---|---|---|---|---|
| 18 TC (Bakharov): 110 TBr, 170 TBr, 181 TBr, 32 MRBr, 36 gds hvy TR | 4 gds MC troops; 37 gds TBde; 13 gds MBde; 7 gds BTR | 110: 21 T-34, 17 T-70; 170: 22 T-34, 17 T-70; 181: 24 T-34, 20 T-70; 36 gds TR: 19 Churchill (21 on strength) — 149 | ~9 000 | 181, 170 TBr and corps troops 11 July 18:00 (turn 4), 110 TBr, 32 MRBr, 36 gds TR 22:00 (turn 5), E edge at the Prokhorovka road |
| 29 TC (Kirichenko): 25 TBr, 31 TBr, 32 TBr, 53 MRBr, 1446 SAP | 2 gds MC troops; 37 gds TBde; 13 gds MBde; 1543 SAP | 25: 32 T-34, 37 T-70; 31: 32 T-34, 35 T-70; 32: 63 T-34; 1446 SAP: 9 SU-122, 12 SU-76 — 191 tanks + 21 SP | ~10 000 | 32, 31 TBr, 1446 SAP, corps troops 18:00 (turn 4); 25 TBr, 53 MRBr 22:00 (turn 5), E edge |
| 2 gds TC (Burdeyny): 4, 25, 26 gds TBr, 4 gds MRBr, 47 gds hvy TR | 36 gds TBde; 14 gds MBde; 7 gds BTR | ~120 tanks (4 gds ~42, 25 gds ~44, 26 gds ~44 incl. T-70) + 47 gds TR ~15 Churchill | ~8 000 | on the map from turn 1 at Belenikhino - Vinogradovka (attached to 5 gds TA on 11 July) |
| 2 TC (Popov): 26, 99, 169 TBr, 58 MRBr | 37 gds TBde; 13 gds MBde | ~90 tanks after 10 July (26 TBr ~29, 99 TBr ~27, 169 TBr ~32) | ~6 000 | turn 1: 99 TBr Vasilyevka, 26 and 169 TBr at Storozhevoye |
| 5 gds MC (Skvortsov): 10, 11, 12 gds MBr (each with 51/54/55 gds TR), 24 gds TBr, 1447 SAP | 13 gds MBde + 36 gds TBde as the tank regiment; 36 gds TBde | tank regiments 23 T-34 + 16 T-70 each; 24 gds TBr 39 T-34, 23 T-70; ~212 in all | ~15 000 | 10 gds MBr, 24 gds TBr, corps troops 12 July 02:00 (turn 6) on the Pravorot road; 11 and 12 gds MBr 06:00 (turn 7), then sent south to Rzhavets (Trufanov's group) |
| 1529 hvy SAP | 1543 SAP | 11 SU-152 (+ KV-1S) | | 12 July 10:00 (turn 8), E edge |
| 29 AT Bde (5 gds TA army troops) | 1 gds det AT Bde | 76 mm / 45 mm AT brigade | | 11 July 22:00 (turn 5), E edge |
| 53 gds TR (5 gds TA army troops) | 36 gds TBde (tank battalions only) | 21 T-34, 16 T-70 | | turn 5, E edge |
| 1549 SAP (5 gds TA), 1447 SAP (5 gds MC) | 1543 SAP | historically 11 SU-76 + 12 SU-122 / SU-76s; **stand-in: 8 SU-152 each** (the Mius-Front desc has no SU-76 / SU-122 squads) | | 12 July 02:00 (turn 6) and 06:00 (turn 7), E edge |

Strength parameters of the 5 gds TA formations: `0.5;0.5;1;0.1` (full, fresh). 2 TC and 183 RD: `0.5;0.5;0.6;0.2`
(worn down since 6 July).

**5 gds Army** (Zhadov) — arrives from the north on the Kartashevka - Prokhorovka road and the Psel.

| Formation | Template | State | Arrival |
|---|---|---|---|
| 33 gds RC HQ | 13 gds RC | | 11 July 10:00 (turn 2), N edge |
| 95 gds RD (Lyakhov): 284, 287, 290 gds RR, 233 gds AR | 96 gds RD (291, 293, 295 gds RR, 234 gds AR) | ~8 800 men, full | 284 and 290 gds RR turn 2, 287 gds RR, division troops and 233 gds AR turn 3 (14:00); first trench Vesyoly - Polezhayev, 287 gds RR on the south bank |
| 42 gds RD (Bobrov): 127, 132, 136 gds RR, 91 gds AR | 34 gds RD (103, 105, 107 gds RR, 84 gds AR) | ~8 800 men, full | 127 gds RR turn 3, the rest turn 4 (18:00), Kartashevka road |
| 9 gds AB Div (Sazonov): 23, 26, 28 gds AB Rgt, 7 gds AB AR | 24 gds RD (70, 71, 72 gds RR, 50 gds LAR) | ~8 800 men, full | turn 1: 26 gds AB Rgt at svkh. Oktyabrsky, 28 at Yamki, 23 at 252.4 - Barchevka (arrived in the night 10/11 July) |
| 52 gds RD (Nekrasov): 151, 153, 155 gds RR, 124 gds AR | 3 gds RD (5, 9, 13 gds RR, 22 gds AR) | ~3 500 men after 5-10 July, `0.6` fill | turn 1: Vesyoly, 226.6, Polezhayev |
| 183 RD (Kostitsyn, 48 RC of 69 A): 227, 285, 295 RR, 623 AR | 315 RD (362, 724, 1328 RR, 1012 AR) | ~5 500 men, `0.6` fill | turn 1: 285 RR Vasilyevka - Andreyevka with a battalion at svkh. Oktyabrsky / 252.2 and at Storozhevoye, 227 RR Belenikhino - Ivanovka, 295 RR Leski |
| 10 AT Bde (iptabr) | 1 gds det AT Bde | | turn 1: AT strongpoints 252.4, 230.5, SW slopes of Prokhorovka |
| 5 gds A HQ | 5 atk A | | turn 3, N edge (Tikhaya Padina) |
| 48 RC HQ | 31 gds RC | | turn 1, Pravorot |

| 97 gds RD (Antsiferov): 289, 292, 294 gds RR, 232 gds AR | 96 gds RD pattern | ~8 500 men, full | 289 and 294 gds RR turn 3 (14:00), 292 gds RR and division troops turn 4; N edge west of the Kartashevka road, i.e. the Psel bend bank |
| 13 gds RD (Baklanov): 34, 39, 42 gds RR, 32 gds AR | 34 gds RD pattern | ~8 500 men, full | turn 5 (22:00), Kartashevka road - 33 gds RC second echelon |
| 301 IPTAP, 1510 IPTAP (5 gds A) | 76 mm gun companies of the 1 gds det AT Bde + HQ | 20 x 76 mm each | turn 3 and turn 4, N edge |
| 148 gds TR, 93 gds TR (5 gds A) | 7 gds det BTR | historically 21 Churchills each; **stand-in: 15 KV-1S** | turn 4 and turn 6, N edge |

Still not modelled: the army and front artillery groups (only the division ARs carry artillery HQs), 6 gds A units west of the Psel (outside the block).

## German

**II SS-Panzerkorps** (Hausser), operational tanks on the evening of 11 July.

| Formation | Template | Tanks / StuG (11 July) | Men | On the map |
|---|---|---|---|---|
| LSSAH (Wisch): 1 and 2 SS-PzGr Rgt, 1 SS-Pz Rgt, 1 SS StuG bn, 1 SS AT bn, 1 SS AR, recon, pioneers, flak | Das Reich (3, 4 MIR SS, 2 TR SS, 2 StuG bn, 2 AT bn, 2 AR SS) | 4 Tiger, 47 Pz IV, 4 Pz III, 10 StuG (77 incl. 7 command tanks); 12 Marder | ~20 000 | turn 1: 2 SS-PzGr Rgt at Komsomolets - 241.6 (taken 10 July), 1 SS-PzGr Rgt Teterevino - Ivanovsky Vyselok, panzer regiment at Komsomolets, recon bn on the Psel bank at Kozlovka; attacks the sovkhoz and 252.2 on 11 July |
| Das Reich (Krüger): 3 SS-PzGr "Deutschland", 4 SS-PzGr "Der Führer", 2 SS-Pz Rgt, 2 StuG bn, 2 AT bn, 2 AR SS | itself | 1 Tiger, 18 Pz IV, 34 Pz III, 8 T-34, 27 StuG (95) | ~19 000 | turn 1: Yasnaya Polyana - Ivanovsky Vyselok (Deutschland), Kalinin - Yasnaya Polyana (Der Führer), panzer regiment Teterevino |
| Totenkopf (Priess): 5 SS-PzGr "Thule", 6 SS-PzGr "Eicke", 3 SS-Pz Rgt, 3 StuG bn, 3 AT bn, 3 AR SS | itself | 10 Tiger, 30 Pz IV, 54 Pz III, 21 StuG (122) | ~19 000 | turn 1: crossings at Krasny Oktyabr and Bogoroditskoye, foothold at Klyuchi, panzer regiment and artillery on the south bank; attacks 226.6 and the Kartashevka road from 12 July |
| II SS-PzK troops: 52 and 72 Werfer regiments, 735 heavy artillery bn, corps HQ | kept from 30 July | | | rear SW (Teterevino - Kalinin) |

Strength parameters: LSSAH and Das Reich `0.5;0.6;0.8;0.2` (panzergrenadier battalions worn down since 5 July, panzers at
60-70 % of establishment), Totenkopf `0.5;0.6;0.85;0.15`. The 30 July division troops (Nebelwerfer, Hummel / Wespe
batteries, 150 mm FO teams) stay as they are in the template; LSSAH's Tiger company is the 13./1 SS (4 Tigers).

Removed from the 30 July files: 23 PzD, 16 PzGr Div, 294 / 306 / 302 ID, 3 PzD, XVII, XXIV and XXIX corps, 6 Army; on
the Soviet side 5 Shock Army, 2 gds Army and 28 Army with all their divisions and corps.

## How the numbers get into the files

- `tools\oob_12jul.ps1 -OpDir <op dir>`: clones the template formation (struct, reserve pool, platoons, battle groups,
  slot tables) under the new name with new uids (unit number as the uid prefix) and text keys (`op_<node>`; unit
  designations substituted in English and Russian), deletes the Mius families, then `Set-Strength` writes the strength
  parameters into every platoon that carries one and `Set-Vehicles` sets the vehicle numbers per class (T-34, T-70,
  Churchill = KV-1 pattern, SU-152, Pz IV, Pz III, Tiger, StuG, T-34(r)): command vehicles stay, line sections get 1-3
  vehicles each, sections are dropped or duplicated when the target is outside that range, and T-70 / T-34(r) sections
  are converted to T-34 / Pz IV where a unit had none. Output: the desc and text packs in place (the 30 July originals
  kept as `*.orig30`), `oob_12jul.delta` against the 30 July desc, `uids.csv` (platoon -> uid, side, bg, code) for the
  deployment step, `oob_12jul_log.txt`.
- `tools\prokh_op.py --layout docs\m11_prokhorovka\layout_12jul.json`: puts every HQ and battle group of a formation
  with a role on its node; units with `turn` > 1 are put on the nearest border node of the given map edge with that
  arrival turn in `plat_pos` (the engine's back-line nodes are where reinforcements appear), the rest are placed as
  before (HQs 3.5 / 6 km behind the nearest enemy, front = nearest combat unit of turn 1).
- `tools\build_prokh.ps1` step 4: `date_beg` 11 July, `time_beg` 06:00, OOB generator, `gt3 csv` exports, op body,
  pack. Both sides get the same OOB; they differ in the `ai` field and the campgen block only.

## Timeline the briefings follow (turn = 4 h from 06:00 11 July)

1 (06:00 11 Jul) LSSAH attack on the sovkhoz begins; 2 (10:00) 95 gds RD arrives, 2 TC counter-attack; 3 (14:00)
fighting for the sovkhoz and the ditch, 287 gds RR, 127 gds RR, 5 gds A HQ arrive; 4 (18:00) 252.2 taken, 18 and 29 TC
arrive through Prokhorovka; 5 (22:00) the rest of the tank corps, 5 gds TA HQ; 6 (02:00 12 Jul) 5 gds MC first echelon;
7 (06:00) 11 / 12 gds MBr, Totenkopf's panzers cross at Klyuchi; 8 (10:00) the counter-attack, 1529 SAP; 9 (14:00)
sovkhoz changes hands, Totenkopf on 226.6; 10 (18:00) evening lines; 11 (22:00) 11 / 12 gds MBr go south; 12-16 (13
July) Totenkopf's second attack, Das Reich takes Belenikhino and the Storozhevoye wood, front stabilises; 17-21 (14
July) Das Reich attacks towards Pravorot, Totenkopf leaves the north bank, the corps goes over to the defensive.


## Cross-check against Frieser (via Wheatley 2019, Luftwaffe photo study) - applied 2026-10-23
18 TC 12 July: 96 T-34, 63 T-70, 31 Churchill (36 gds hvy TR, KV stand-in) -> 110/170/181 TBr 32 T-34 + 21 T-70 each. 29 TC: 122 T-34, 70 T-70, 20 SU (1446 SAP).
LSSAH: 5 Pz III, 47 Pz IV, 4 Tiger, 24 StuG, 20 Marder; one panzer battalion only (I./1 in Germany for Panthers); 12 Wespe + 6 Hummel, 12 x 105 towed, 12 x 150 towed, 4 x 105 guns; 12 Nebelwerfer; 53 towed AT / Flak guns.
Das Reich: 42 Pz III, 18 Pz IV, 1 Tiger (+ 8 captured T-34), 27 StuG, 12 Marder. The anti-tank ditch at the foot of 252.2 was 4.5 m deep.
Terrain (16 July 1943 photographs GX-3734-SK-61 etc.): the whole battlefield is a patchwork of large kolkhoz strip fields (ripe grain, a few harvested/bright and fallow/dark strips), almost no trees outside the woods and the railway belt; the Oktyabrsky state farm is rows of long barns beside the railway.

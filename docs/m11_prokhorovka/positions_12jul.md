# Prokhorovka, 12 July 1943 — positions, works and how they are encoded

Research 2026-10-23 for the M11 operation. Everything below is placed in `layout_12jul.json` (block metres, x east
from lon 36.4903, y north from lat 50.904605) and read by `tools\prokh_op.py` (deployment, key points, markers) and
`tools\prokh_gen.py` via `tools\works.py` (trenches, anti-tank ditch, strongpoints carved into the cells). Places
were located with the OSM nodes of the block and the 1940 RKKA 1:100 000 sheet (`docs\m12_terrain\period`); the
1943 spot heights (252.2, 241.6, 226.6, 252.4 …) are taken from that sheet, not from the modern DEM, which reads
7-8 m higher.

## German side (II SS-Panzerkorps), evening 11 July / morning 12 July

**LSSAH** (77 tanks and assault guns on the evening of 11 July). On 11 July it cleared svkh. Oktyabrsky, crossed the
Soviet anti-tank ditch at the SW foot of height 252.2 and took the hill, ending 3 km SW of Prokhorovka with open
flanks. 2 SS-PzGr Rgt (Krass; II./2 Sandig, I./2 Becker) held the sovkhoz and 252.2 with the anti-tank guns in the
sovkhoz and along the road to the crest; its outposts were 300-500 m from the ravine SW of the station. 1 SS-PzGr Rgt
(Wisch) held the NW edge of the Storozhevoye wood, svkh. Stalinskoye otd. and the railway back to svkh. Komsomolets,
with StuGs in ambush at Stalinskoye and the east edge of the wood; it took Storozhevoye on the morning of 12 July.
The panzer regiment (about 60 tanks on the evening of 11 July) stood on 252.2 (6./1 Lehmann 150 m east of the
sovkhoz, 7./1 von Ribbentrop in it) and behind the ditch; the artillery between the railway and the Psel floodplain,
the SP artillery behind the ditch SW of 252.2; the 13th (Tiger) company and the reconnaissance battalion held the
5 km gap to Totenkopf on the south bank of the Psel between Mikhaylovka and Kozlovka; the division CP on 241.6 /
Komsomolets (taken 10 July).

**Das Reich** (95 tanks and StuG) lagged 4 km behind on the southern flank, facing 2 Gds TC and 183 RD on a line
Storozhevoye - Belenikhino - Pravorot approaches: Deutschland at Ivanovsky Vyselok and the south edge of the
Storozhevoye wood, Der Führer at Yasnaya Polyana towards the west edge of Belenikhino, the panzer regiment around
Teterevino - Kalinin, artillery west of Teterevino. On 12 July it was forced onto the defensive by 2 Gds TC and 2 TC.

**Totenkopf** (122 tanks, 10 Tigers) held the Psel bridgehead taken on 10 July: Klyuchi, the south slopes of 226.6
(the hill itself fell only on 12 July), the bridgehead base at Bogoroditskoye / Kozlovka / Krasny Oktyabr with the
crossings there, Regiment Eicke guarding the bridges and the panzer regiment (Bochmann) crossing at Klyuchi on the
night of 11/12 July to attack along the north bank towards the Kartashevka - Prokhorovka road. 1.5 km from Vesyoly.

## Soviet side

**29 TC** (212 tanks and SP guns): 32 TBr (Linev, 63 tanks) first echelon in the ravine at the brick works west of
Prokhorovka with three batteries of 1446 SAP, attacking along the railway on a 900 m front towards the sovkhoz and
252.2; 31 TBr (Moiseyev, 67) second echelon 2 km east of the brick works at Barchevka; 25 TBr (Volodin, 69) at
Lutovo, attacking from Yamki through the ravine past Storozhevoye to Ivanovsky Vyselok (the LSSAH / DR boundary);
53 MRBr (Lipichev) between the railway embankment and Yamki in two echelons; 1529 SAP still on the road from 7 Gds A.

**18 TC** (190): 181 TBr (Puzyrev, 44) at Petrovka, to go along the Psel through Prelestnoye and Mikhaylovka towards
Vasilyevka and Gryaznoye; 170 TBr (Tarasov, 39) 2 km east of Petrovka on the Beregovoye road and the west slopes of
252.4, through the balka to the brick works and the north edge of the sovkhoz; 36 Gds Tank Rgt (21 Churchills) from
the Kusty area via Petrovka; 32 MRBr second echelon north of the station behind the ravine; 110 TBr (38) third echelon.

**9 Gds Airborne Div**: 26 Gds AB Rgt first trench on the SW outskirts of Prokhorovka, later the S and SE slopes of
252.4 (two trench rows, minefields in front, lanes only partly cleared for the tanks); 23 Gds AB Rgt east of
Petrovka to the railway, second echelon 252.4 - Barchevka; 28 Gds AB Rgt railway - north edge of Lutovo - ravine 1 km
NW of Grushki.

**95 Gds RD**: 284 and 290 Gds RR digging the first trench Vesyoly - Polezhayev on the north bank; 287 Gds RR (with
the 109th penal company) 3 km south along Andreyevka - Mikhaylovka - Prelestnoye - Petrovka and the spurs of the balka
north of the sovkhoz, attacking the sovkhoz at dawn. **42 Gds RD**: 127 Gds RR at Prelestnoye with 18 TC, the other
two regiments on the north bank along the Petrovka - Kartashevka road; a minefield in the ravine at its boundary
with 18 TC. **52 Gds RD** (remnants, with I/156 Gds RR) at Vesyoly - north of 226.6 facing the bridgehead.
**183 RD**: 285 RR at Vasilyevka - Andreyevka (1st bn) and Storozhevoye (3rd bn); 227 RR along the balka, railway
and the wood SW of svkh. Stalinskoye on 11 July, then Belenikhino - Ivanovka; 295 RR Leski - Shakhovo. **2 TC**:
99 TBr at Vasilyevka - Mikhaylovka, 26 and 169 TBr south of Storozhevoye / the wood east of Ivanovsky Vyselok, 58
MRBr Andreyevka - Mikhaylovka. **2 Gds TC** (120 tanks): Vinogradovka - Belenikhino - Shakhovo, attacking at 11:45
towards Yasnaya Polyana and Kalinin (26 Gds TBr detached south to Trufanov's group). **5 Gds Mech Corps**: 10 Gds MBr
and 24 Gds TBr (92 tanks) army reserve east of Prokhorovka (Pravorot - Krasnoye), 11 and 12 Gds MBr sent south to
Shakhovo / Rzhavets. **Artillery**: long-range group at Prelestnoye, Prokhorovka (NE and S outskirts), 252.4,
Tikhaya Padina, Krasnoye and north of Plota; 104 Gds IPTAP and 1447 SAP on heights 243.8 and 242.7 west of
Podolkhi; 271 Mortar Rgt with 53 MRBr; anti-tank guns dug in on the SW slopes of Prokhorovka. 33 Gds RC CP at
Beregovoye, 5 Gds TA CP NE of Prokhorovka.

## Works

The army rear belt here was built in June by the 14 Separate AT Brigade and army sappers ("95 % done"): a
continuous anti-tank ditch (about 4.5 m deep by the German account) from the Psel valley south of Petrovka past
the SW foot of 252.2 to the railway at svkh. Stalinskoye, anti-tank strongpoints at heights 252.4, 230.6 (230.5
on the sheet), 202.2 and in Prokhorovka, and a battalion position of 3/285 RR at 252.2 - Oktyabrsky (now German).
Other trenches: the two rows of 26 and 23 Gds AB Rgt SW of the station, 28 Gds AB Rgt to Lutovo, the 95 Gds RD
first trench Vesyoly - Polezhayev, 287 Gds RR along the south bank, 183 RD at Vasilyevka and the west edge of the
Storozhevoye wood, the 2 Gds TC / 183 RD line Belenikhino - Vinogradovka, the 32 MRBr (18 TC) trench system east of
241.6 taken by LSSAH on 10 July, the former 52 Gds RD trenches at Klyuchi - 226.6 now held by Totenkopf, Das Reich
positions at Yasnaya Polyana and Ivanovsky Vyselok. Minefields: in front of 26 / 23 Gds AB Rgt (lanes cut for 29
TC), the ravine east of Petrovka, German fields on the approaches from Prokhorovka east of 252.2 and south of
Storozhevoye, both sides in the Psel bend at Vesyoly - Klyuchi, and west of Belenikhino.

## Encoding

- Trenches and the ditch are carved into the heightmap (trench 1 m deep / 3 m wide with a 0.3 m parapet band,
  ditch 3 m deep / 6 m wide with a 0.8 m berm), the floor gets soil TREN (14) like the Mius cells, and `trench_pos`
  lists INF foxhole pairs every 10 m plus MG / GUN / MORT positions on the strongpoint rings - the vanilla format
  (`tools\works.py`). Cells touched get their `hei_map` re-encoded; `gen_prokh_fresh.cmd` is needed once.
- Minefields cannot be pre-placed: no cell layer or operation table carries them (the engine lays mines through
  sapper platoons during the operation), so they appear as `mines` markers on the op map only; the AI orders table
  could give the sapper platoons a mining order at turn 1 later.
- The deployment uses the formations of the cloned 30 July operation as stand-ins (`units` in the layout: 23 PzD /
  16 PzGr for LSSAH, DR, TK, 294 ID as the corps rear; Soviet 2 GMC / 4 MC brigades and regiments for the tank
  corps, 24 / 96 / 315 / 221 RD regiments for 9 Gds AB, 95, 42, 52 Gds and 183 RD). Node ownership = side of the
  nearest placed unit, which gives the Psel bridgehead and the LSSAH wedge their real shape. The real 12 July OOB
  (brigades, regiments, 1529 / 1446 SAP, Churchills of 36 Gds TR) is the next step on top of this layout.

## Sources

- [Zamulin, "Бой, ставший легендой" (Засекреченная Курская битва)](https://history.wikireading.ru/hnsqe6YEk3) and
  the same chapter in [Прохоровское побоище](https://military.wikireading.ru/4365): start positions of 18 and 29 TC,
  9 Gds AB Div, LSSAH dispositions, the ditch and minefields.
- [Zamulin, "Район Прохоровки за сутки до знаменитого боя"](https://military.wikireading.ru/4360): 11 July positions
  of 183 RD, 2 TC, 95 Gds RD, 9 Gds AB Div, the ATO strongpoints of 14 oiptabr, trenches east of 241.6.
- [Zamulin, "Ход и результаты контрудара на вспомогательных участках"](https://document.wikireading.ru/hEuZYFawtU):
  German sector list (DR at Kalinin - Yasnaya Polyana - Storozhevoye, TK bridgehead at Bogoroditskoye - Polezhayev).
- [Battle of Prokhorovka (Wikipedia)](https://en.wikipedia.org/wiki/Battle_of_Prokhorovka): strengths, LSSAH layout
  on the railway, the ditch at 252.2, Totenkopf and 226.6.
- [Prochorovka: 12 July 1943 (warhistory.org)](https://warhistory.org/article/prochorovka-12-july-1943): Das Reich
  line Storozhevoye - Belenikhino - Pravorot, Totenkopf bridges and Regiment Eicke, 31 TC on the north bank.
- [Сражение под Прохоровкой (ru.wikipedia)](https://ru.wikipedia.org/wiki/%D0%A1%D1%80%D0%B0%D0%B6%D0%B5%D0%BD%D0%B8%D0%B5_%D0%BF%D0%BE%D0%B4_%D0%9F%D1%80%D0%BE%D1%85%D0%BE%D1%80%D0%BE%D0%B2%D0%BA%D0%BE%D0%B9),
  [Олейников, Прохоровское сражение (militera)](http://militera.lib.ru/h/oleinikov/04.html) — not fetchable from here
  (redirect loop / blocked); worth reading on the PC for the 2 Gds TC and Psel-bend detail, which is the least
  certain part of the layout.

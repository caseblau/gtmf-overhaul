# M11 — "Prokhorovka, 11–13 July 1943": operation design (draft 2026-10-22)

User decisions: battle = Prokhorovka; scope = 11–13 July 1943 as four operations in one chapter: one full-corps
campaign 11–13 July (18 turns) plus three day-operations (Oktyabrsky 11 July, Prokhorovka 12 July, Psel bend 13 July),
each with both side files; terrain = stand-in (no Kursk map exists in
Graviteam Tactics); the Stepanovka terrain (`1943_07_Mius`, July steppe with ravines) is the proposed stand-in, with the
30 July 1943 operation as the technical base (current format, II SS Panzer Corps already in its OOB).

## 1. Historical frame

- 11 July: LSSAH takes the Oktyabrsky state farm and Hill 252.2, reaches the Prokhorovka approaches; Totenkopf holds
  the Psel bridgehead and pushes along the north bank; Das Reich south of the railway at Yasnaya Polyana–Belenikhino.
- 12 July (the battle): 5th Guards Tank Army attacks at 08:30 with 18th and 29th Tank Corps head-on into LSSAH between
  the Psel and the railway; 2nd Guards Tank Corps against Das Reich south of the railway; 2nd Tank Corps in support;
  5th Guards Mechanised Corps in second echelon; 9th Guards Airborne and 42nd Guards Rifle Divisions in the Soviet
  line; 95th and 52nd Guards Rifle Divisions against Totenkopf in the Psel bend. The attack is stopped with very heavy
  Soviet tank losses; Totenkopf gains ground north of the Psel.
- 13 July: local attacks both sides; Totenkopf pulled back from its gains; the front stabilises; Citadel is called off.

## 2. Sides and formations (to be verified against Zamulin *Demolishing the Myth*, Töppel *Kursk 1943*, Lawrence
*Kursk: The Battle of Prokhorovka*; strengths = morning 11 July returns)

German, II. SS-Panzerkorps (Hausser):
- LSSAH (Wisch): SS-PzGrenRgt 1, SS-PzGrenRgt 2 (III. gep. Btl in SPWs), II./SS-PzRgt 1 (Pz IV lang, Pz III), 13. (schwere)
  Kp with the serviceable Tigers (about 4 on 12 July), SS-StuG-Abt 1, SS-PzAufklAbt 1, SS-PzJgAbt 1 (Marder), SS-ArtRgt 1,
  Werfer-Abt, Flak-Abt. (I./SS-PzRgt 1 was in Germany converting to Panther — not present.)
- SS-Totenkopf (Priess): SS-PzGrenRgt 5 "Thule", SS-PzGrenRgt 6 "Theodor Eicke", SS-PzRgt 3 (about 100 tanks incl. ~10
  Tigers), StuG, artillery; in the Psel bridgehead.
- SS-Das Reich (Krüger): SS-PzGrenRgt "Deutschland", "Der Führer", SS-PzRgt 2 (incl. captured T-34s and the Tiger
  company), StuG, artillery; south of the railway.
- Corps troops: Werfer, Flak, sArtAbt; Luftwaffe support (not modelled beyond what the engine offers).

Soviet, 5th Guards Tank Army (Rotmistrov) and 5th Guards Army (Zhadov) elements:
- 18th Tank Corps (Bakharov): 110, 170, 181 Tank Bdes, 32 Motor Rifle Bde, 36th Guards Heavy Tank Regt (Churchill),
  1000 AT Regt, 292 Mortar Regt.
- 29th Tank Corps (Kirichenko): 25, 31, 32 Tank Bdes, 53 Motor Rifle Bde, 1446 SP Art Regt (SU-76, SU-122), 108 AT Regt.
- 2nd Guards Tank Corps (Burdeyny): 4, 25, 26 Guards Tank Bdes, 4 Guards Motor Rifle Bde, 47 Guards Heavy Tank Regt.
- 2nd Tank Corps (Popov): 26, 99, 169 Tank Bdes, 58 Motor Rifle Bde (worn, supporting role).
- 5th Guards Mechanised Corps (Skvortsov): 10, 11, 12 Guards Mech Bdes, 24 Guards Tank Bde (second echelon / flank).
- Rifle: 9th Guards Airborne Div (Prokhorovka), 42nd Guards RD, 95th Guards RD and 52nd Guards RD (Psel bend, vs TK),
  183rd RD (south).
- Army artillery: 678 Howitzer Regt, 1529 Heavy SP Regt (SU-152, if present on 12 July — check), Guards Mortar (Katyusha)
  units, AT brigades.

## 3. Engine fit

- Scale: Mius-Front operations are division/corps-sized; the Stepanovka map (size to be read from the 30 July `desc`
  node grid) will hold the LSSAH sector at full depth and the two flanking sectors compressed. If the map is too small,
  model the LSSAH sector with TK and DR as flank formations with reduced slots.
- Turns: 11–13 July = three days; turn length and count come from the 30 July `campgen` parameters (read before
  deciding how many turns; arrival turns for 5th GTA corps on the 12th, 5 Gds MC later).
- Units already in Mius-Front data (July 1943 Mius): SS panzer-grenadier and panzer units of DR and TK from the 30 July
  OOB (LSSAH = clone of DR with LSSAH numbering and strengths), Pz IV, Pz III, StuG III, Marder, Tiger (check which
  formation carries it), SdKfz 251; Soviet T-34, T-70, SU-76M, SU-122, 45/57/76 mm AT, 122/152 howitzers, Katyusha.
  To check in `div_units_*`: Churchill (36 Gds HTR), SU-152, captured T-34 in German service, Nebelwerfer.
- Scripts: deployment areas, objectives (Oktyabrsky, Hill 252.2, Prokhorovka station, Psel crossings, Belenikhino),
  arrival turns — need the `scripts` (AZSC) entry decoded (M11 step 3); until then the 30 July layout is inherited.

## 3b. Operation split (user, 2026-10-22)

Chapter `1943_07_Kursk`, same terrain rectangle and formation set for all four (one generator source).
0. **07_11_13_Prokhorovka** — the full-corps campaign, 18 turns of 4 h: starts from the 11 July state; 18 TC, 29 TC,
   2 Gds TC and 5 Gds MC arrive by scripted turns; objectives change by day. Needs the `scripts` entry decoded; built last.
Day-operations, 6 turns of 4 h each (06:00–06:00 next day):
1. **07_11_Oktyabrsky** — German attack. LSSAH (eve-10/11 July strength, 4 Tigers) + TK bridgehead flank vs 9 Gds Airborne
   Div, 2 TC remnants, 95 Gds RD; 18/29 TC lead brigades arrive during the day as positional reserves. Objectives:
   Oktyabrsky sovkhoz, Hill 252.2, Komsomolets approaches.
2. **07_12_Prokhorovka** — Soviet attack, the core operation (build first). 18 TC + 29 TC (11 July returns), 2 Gds TC
   south of the railway, 5 Gds MC (10 Gds MBde, 24 Gds TBde) arriving mid-day; vs LSSAH defending Oktyabrsky/252.2,
   DR south, TK attacking north of the Psel. Objectives: Oktyabrsky, Komsomolets, Yasnaya Polyana (RUS); hold +
   Hill 226.6 / Polezhaev (GER).
3. **07_13_Psel** — TK vs 10 Gds MBde + 24 Gds TBde + 95/52 Gds RD; DR vs Storozhevoe/Vinogradovka; LSSAH
   holding; no German Tigers serviceable.

## 4. Work plan

1. Build support for a new operation cloned from a vanilla one (`!base` in `src\m2_oob\camps\<chapter>\<op>\`);
   register `1943_07_Kursk\07_12_Prokhorovka_RUS/GER` on the Stepanovka terrain; confirm it is listed and starts.
2. OOB generator `tools\oob_prokhorovka.ps1` from the 30 July structures; historical write-up `docs\m11_prokhorovka\oob.md`.
3. Decode the `scripts` entry (deployment areas, objectives, arrival turns); place objectives for the stand-in map.
4. Texts (names, briefing), operational map image, both-side files identical for MiusPlayer.
5. In-game checks per step, as in M2.

Sources for terrain: `sources_terrain.md`.

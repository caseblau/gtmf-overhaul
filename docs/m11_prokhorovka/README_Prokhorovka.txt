PROKHOROVKA, 10 - 13 JULY 1943  -  an operation for Graviteam Tactics: Mius-Front
=================================================================================
Part of the MF Overhaul project (https://github.com/caseblau/gtmf-overhaul). This package is the Prokhorovka
terrain and the two campaign operations only; it contains none of the overhaul's other modules and works on the
unmodified game.

WHAT IS IN IT
  * A new 14 x 10 km polygon "Prokh": the Psel bend with Vasilyevka - Andreyevka - Mikhailovka - Prelestnoye, Hill 226.6,
    svkh. Oktyabrsky and Hill 252.2, Prokhorovka station, svkh. Komsomolets and Hill 241.6, Storozhevoye and its wood,
    Ivanovsky Vyselok, Hill 258.2 and Teterevino. Relief from a 30 m elevation model, roads and woods from OpenStreetMap
    corrected to the 1941 Red Army 1:100 000 sheet (settlements, the double-track Belgorod - Kursk railway, no post-war
    reservoirs), field works where the Soviet trenches and the two anti-tank ditches (252.2 and 258.2) were dug.
  * Two operations in a new chapter "Kursk, July 1943": 07_10_Prokhorovka_GER (play II SS-Panzerkorps) and
    07_10_Prokhorovka_RUS (play 2 TC / 183 RD / 5 gds TA). 24 turns of 4 hours from 06:00 on 10 July to 13 July.
    Orders of battle for LSSAH, Das Reich and Totenkopf and for 183 RD, 2 TC, 52 gds RD, 9 gds AB Div, 95 and 42 gds RD,
    2 gds TC and 5 gds TA (18 TC, 29 TC, 5 gds MC) with the vehicle numbers of the returns of 10-11 July. The AI side
    follows the historical timetable (Komsomolets and 241.6 on the 10th, Oktyabrsky and 252.2 on the 11th, the Soviet
    counter-attack on the morning of the 12th). Hand-drawn briefing sketches (F2) for the main turns.

REQUIREMENTS
  * Graviteam Tactics: Mius-Front 6.00, build 3598 (the Steam version of October 2024 or later).
  * Stalingrad - Donets DLC: the Churchill regiments (15, 36, 47, 93 and 148 gds hvy TR) use its Churchill III.
  * About 1 GB of free disk space under the game folder.

INSTALL
  1. Copy mfo_prokhorovka_<version>.gt3ext into <game folder>\new_updates\  (create the folder if it is missing).
  2. Start the game once. The updater installs the add-on into data\common\mfo_prokhorovka\ and registers it.
  3. Operations -> chapter "Kursk, July 1943" -> Prokhorovka (GER or RUS).
  To remove it, delete data\common\mfo_prokhorovka\ and its line from data\common\shared\config\paths.cfgpack, or use the
  game's add-on manager.
  Multiplayer (MiusPlayer): both players need the same package version - the version shows in the game's Version menu.

KNOWN LIMITS (this is a test release)
  * M3 Lee of 245 TR and the SU-76 / SU-122 of the SAP regiments are not in the game: T-34 and SU-152 stand in.
  * The terrain is generated; report odd spots (floating objects, holes, unpassable places) with a screenshot and the
    nearest village or height.

SOURCES AND CREDITS
  Terrain: OpenStreetMap data (c) OpenStreetMap contributors, ODbL (www.openstreetmap.org/copyright); Red Army 1:100 000
  sheet of the Prokhorovka area (1941 printing); Luftwaffe reconnaissance photographs of 14-16 July 1943 as reproduced in Ben Wheatley,
  "A Visual Examination of the Battle of Prokhorovka" (2019); Copernicus GLO-30 elevation data.
  Orders of battle, timetable, positions: Valeriy Zamulin, "Demolishing the Myth" (2011) and "The Battle of Kursk 1943:
  The View through the Camera Lens"; Christopher Lawrence, "Kursk: The Battle of Prokhorovka" (2015); Ben Wheatley (2019);
  TsAMO documents quoted there.
  Tools: the whole pipeline (terrain generator, OOB and operation builders, briefing-sketch compiler) is in the repository.
  Graviteam Tactics: Mius-Front is (c) Graviteam. The operation packs are built on the game's own operation data format
  (the Stepanovka operation of the Mius front served as the template); the terrain cells are generated.

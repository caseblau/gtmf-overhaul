# M11 Prokhorovka — terrain source data (2026-10-22)

Battlefield of 12 July 1943 (LSSAH sector): between the Psel bend (Polezhaev, Vasilyevka, Prelestnoe, Petrovka) and the
Belgorod–Prokhorovka railway (Oktyabrsky state farm, Hill 252.2, Storozhevoe, Yamki, Andreevka), station Prokhorovka at
about 51.04 N, 36.73 E. Soviet sheet grid: 1:100 000 sheets **M-37-026** (51°00'–51°20' N, 36°30'–37°00' E: Prokhorovka,
the Psel bend, Oktyabrsky) and **M-37-038** (50°40'–51°00' N: Storozhevoe, Yamki, Belenikhino); 1:50 000 quarters
M-37-026-В (SW, "M-37-26-C" in Latin transliteration, the sheet C. Lawrence cites for Oktyabrsky) and -Г, M-37-038-А and -Б.

## 1. Elevation (hypsometric) data

| Source | Resolution | Notes |
|---|---|---|
| Copernicus DEM GLO-30 (ESA, free) | 30 m | Best free global DEM for the area; download by 1°×1° tile (N51 E036) from the Copernicus/AWS open bucket or OpenTopography. |
| SRTM 1 arc-second (USGS EarthExplorer) | 30 m | Older (2000), noisier in the ravines; useful as a cross-check. |
| ALOS AW3D30 (JAXA) | 30 m | Comparable to Copernicus; requires free registration. |
| FABDEM (Univ. Bristol) | 30 m | Copernicus with buildings/trees removed ("bare earth"); free for non-commercial use, which is what a mod is. |
| Soviet General Staff (Генштаб) 1:50 000 sheets M-37-026-В/Г, M-37-038-А/Б | 10 m contours | 1970s–80s editions; the relief has not changed, so digitising these contours gives better ravine detail than any 30 m grid. Hosted on the usual Genshtab map sites (loadmap.net, "Топографические карты ГГЦ" collections). |
| Soviet General Staff 1:100 000 M-37-026, M-37-038 | 20 m contours | Same sources; enough for the operational map, not for the tactical terrain. |

Recommendation: FABDEM or Copernicus GLO-30 as the base grid, refined with digitised 1:50 000 contours along the balkas
(ravines), which are the tactically decisive features and are smeared at 30 m.

## 2. Aerial photographs, 1943

- **Luftwaffe reconnaissance imagery, NARA College Park, RG 373 (German Flown Aerial Photography, "GX" series).**
  The Prokhorovka battlefield was flown on 14 and 16 July 1943 (and in June, before the offensive). Ben Wheatley
  (UEA) used these for *A visual examination of the battle of Prokhorovka*, Journal of Intelligence History 2019
  (https://www.tandfonline.com/doi/full/10.1080/16161262.2019.1606545); his frames show the "tank fields" south-west of
  Oktyabrsky and the anti-tank ditch along the Psel–railway line. Christopher Lawrence reproduces 32 June–July 1943
  frames in *Kursk: The Battle of Prokhorovka* (pp. 569–600, e.g. "Tank Fields of Prokhorovka, 16 July 1943") and
  discusses the collection at https://dupuyinstitute.org/2019/07/22/kursk-aerial-photos/ (roll/frame identifiers are
  not public; the Dupuy posts say "dozens of pictures of the area" are at NARA). NARA's cartographic branch answers
  reference requests by area and date; the GX finding aids are indexed by sortie, not by place name.
- **NCAP (National Collection of Aerial Photography, Edinburgh)** holds the British copy of captured Luftwaffe
  imagery (TUGX/ACIU series) and sells scans; coverage of the Belgorod–Prokhorovka sector exists for 1943 but has to
  be requested by coordinates.
- Game-map builders have used exactly these frames: the Advancing Fire ASL boards (Oktyabrsky, Storozhevoe,
  Andreevka) were drawn from the German photos plus sheet M-37-26-C
  (https://dupuyinstitute.org/2021/03/25/oktyabrskii-map-for-the-game-prokhorovka/).

## 3. Period topographic maps (1930s–1943)

- **RKKA (Red Army General Staff) 1:100 000 and 1:50 000, 1937–1941 editions**, the base for both armies' battle maps.
  etomesto.ru hosts georeferenced RKKA 1:500 000 quarters (M-37 (В) "Донбасс" is the SW quarter; Prokhorovka lies in
  the NW quarter M-37 (А)) and some 1:100 000 regions (https://etomesto.com/russia/rkka/maps.php, paginated; Belgorod
  index https://etomesto.com/belgorod/maps.php has a 1943 Kursk oblast map but no large-scale sheet on its first page).
- **German Heereskarte "Osteuropa 1:100 000" and "Russland 1:50 000"** (captured RKKA sheets, overprinted 1941–43):
  Library of Congress and the Polish WIG archive (mapywig.org, German section) hold scans; the Prokhorovka sheet is
  the one named for Prochorowka/Belgorod north.
- **Soviet operational maps of July 1943** (hand-drawn situations on 1:100 000 bases for 5th Guards Tank Army, 18th
  and 29th Tank Corps, 2nd Guards TC, 9th Guards Airborne Division): digitised on *Память народа* (pamyat-naroda.ru,
  "Документы" → карты/схемы by unit and date), the best source for positions, boundaries and the anti-tank ditch.
- **German situation maps** (II. SS-Panzerkorps, LSSAH Ia maps, 11–13 July 1943): NARA T354/T313 microfilm, reproduced
  in Zamulin (*Demolishing the Myth*), Töppel (*Kursk 1943*), Lawrence (*Kursk*).

## 4. What each layer feeds

Heights → heightmap (needs the engine terrain format, M11 step 3+); 1943 photos → land cover of the day (fields, tree
belts, the state farm buildings, trenches, the anti-tank ditch) and the look of the operational map image; period
sheets → place names, roads, the railway, village outlines; operational maps → deployment areas, objectives and
arrival turns for the `scripts` entry and the OOB placements.

## Luftwaffe aerial photographs of the block (found 2026-10-23)

luftfoto.ru (Polish/Russian scanning service working from NARA/Bundesarchiv holdings; catalogue search "Прохоровка")
lists three frames that cover our map, sold as scans at 300/600/1200 dpi for about $4/$8/$15 each
(deukarten@gmail.com, +48 510 632 801):

| article | date | covers | scale / quality |
|---|---|---|---|
| I4DMHU3BR | 14 Jul 1943 | Prelestnoye, Mikhailovka, Andreyevka, Vasilyevka, Yudinka, Belenikhino, Yasnaya Polyana, Storozhevoye-2, Prokhorovka (centre 50.9887 N 36.6161 E) | 1:25 000, medium, some cloud |
| XBEV2MTCL | 16 Jul 1943 | Prokhorovka, Prelestnoye, Storozhevoye-2, Yamki, Grushki (centre 51.0177 N 36.6905 E) | 1:49 000, medium, no cloud |
| AF0GD71PY | 06 Oct 1943 | Prokhorovka, Prelestnoye, Mikhailovka, Andreyevka, Vasilyevka, Storozhevoye-2, Yamki, Yasnaya Polyana, Belenikhino, Kalinin, Leski (centre 50.9737 N 36.6526 E) | medium, no cloud |

The two July frames are two and four days after the tank battle (Oktyabrsky/Hill 252.2 and the Storozhevoye–Belenikhino
corridor are inside them). warfly.ru once hosted three free low-resolution Prokhorovka frames (16 Jul 1943 large frame,
undated station fragment, 21 Jun 1943 "Munitionslager") from wwii-photos-maps.com; its tile store (17200.selcdn.ru) is
dead, so those are no longer retrievable. etomesto.com's aerial section has Belgorod 1941 but nothing for Prokhorovka.
The 1940 RKKA 1:100 000 sheet with the 1943 staff overprint is on retromap.ru (map 14194055, tiles via tools\fetch_period_tiles.cmd).

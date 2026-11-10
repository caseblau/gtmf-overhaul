# Reading the 1941 RKKA 1:100 000 sheet

Key from US Army TM 30-548, *Soviet Topographic Map Symbols* (June 1958; symbol numbers below). It postdates the 1941 sheet, so
each reading is checked against the sheet itself. The dissertation by Bartles (Russian military map symbology) covers the
military overlay, which helps with the staff pencil marks on this sheet but not with terrain.

| On the sheet | Meaning | Symbol | Generator |
|---|---|---|---|
| `ıı` ticks, black | Meadow, not marsh | 348 | Grass |
| `ıı` ticks with blue dashes | Swampy meadow (marsh land) | 384 | MARSH |
| Blue dashes filling an area | Swamp, passable or hard to pass | 342-344 | MARSH |
| Double solid line | Main dirt (country) road, or improved dirt road | 146, 145 | `secondary` |
| Single solid line | Dirt (country) road | 147 | `track` |
| Dashed line | Field or forest road, or a hard section of dirt road | 148 | `path` |
| Small mark across a stream | Small bridge, under 10 m | 187 | Low embanked crossing, no model |
| Marked crossing on a road | Bridge over 10 m; fraction = length / load | 188 | `bridge0` spans |
| Circles in rows | Fruit orchard | 332 | ORCHARD |
| Diagonal hatching in plots | Vegetable gardens | 336 | Village plots |
| Circle with tick | Brush | 387 | SCRUB |
| Toothed contour pair | Ravine with steep slopes, or washout | 292-293 | From the elevation model |

Blue areas drawn with a heavy, uneven stroke are the staff pencil overprint, not water.

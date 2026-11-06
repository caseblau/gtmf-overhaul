r"""The road network of 1941 traced from the RKKA 1:100 000 sheet -> docs/m12_terrain/period/roads_1941.json.

4 Nov 2026 (user: "Just match all the roads from the 1941 map don't take into account the modern"): the Prokhorovka map
takes its roads, cart tracks and field paths from the 1941 sheet itself, not from OpenStreetMap.  This script vectorises
the black line work of the sheet inside the 9 x 9 block into polylines in DEM-lattice metres; tools/prokh_gen.py reads
the committed JSON (no re-tracing at generation time) and drops every OSM highway.

  py -3 tools\roads_1941.py docs\m12_terrain\period\rkka100k_block.png docs\m12_terrain\period\roads_1941.json
        [--builtup docs\m12_terrain\period\builtup_1941.png] [--osm docs\m12_terrain\osm\prokh.osm.json]
        [--preview out_dir]

Needs numpy, scipy, Pillow, scikit-image (skeletonize).  --osm is used ONLY for the railway (an approximate corridor in
which the sheet's railway symbol is looked for and masked out - the railway is not a road); no OSM road is read.

The sheet raster (tools/period_cover.py) is 4 m/px over the lattice, row 0 = north; the scan itself is ~12 m/px (the
z13 tiles were upsampled x 3).  Method:
  1. black print = dark against the local paper (the SW sheet is printed fainter), unsaturated, not blue (pencil); the
     brown contours / ravine edges go by their local mean colour (r - b of the ink within ~25 m);
  2. the 2 km grid (thin straight lines, a slightly rotated lattice per strip) is found by sheared projection profiles
     and its thin runs removed; the railway (double line with hatching - not a road) is masked as the dense ink band
     along the line (OSM is read for the railway corridor only); EXCLUDE masks the staff's black pencil arrows / writing;
  3. GUIDED (the network in use): every road, cart track and field path of the sheet, read off the sheet tile by tile
     as waypoints with its class from the symbol - 'secondary' double line (improved / main road), 'track' single
     solid line (dirt road), 'path' dashed line (field / forest track), 'residential' village street - and snapped to
     the line work between the waypoints by a least-cost path over a cost raster (cheap on the ink, centre of a double
     line cheapest; dear on paper and on the railway symbol; uniform under the pencil masks, inside the villages, where
     the house blocks are ink too, and in the missing-tile patches, so a road crosses those straight between matching
     ends on either side);
  4. an automatic tracer (solids / dashes / skeleton graph / spur pruning / gap bridging, steps in auto_trace) runs as
     a check: a traced piece the guided roads miss is added only if it is >= AUTO_MIN_M and closes a gap in the network
     (on the 4 Nov sheet nothing qualified - what it finds beyond the guided roads is lettering, ravine edges and the
     insides of villages);
  5. village streets: the spine (pruned skeleton) of every 1941 built-up blob (builtup_1941.png) where no road runs
     within 36 m, and for any blob still without a street a lane along its long axis joined to the nearest road
     within 250 m - so tools/settle.py has a street through every 1941 village;
  6. Chaikin-smoothed and written as lattice-metre polylines with their class.
c70 (5 Nov, user: "These roads look weird"): steps 3-6 are now done by trace(): each road is routed inside a corridor
round its waypoints over a cost raster whose cheapest line is the CENTRE of the sheet's line work, re-centred across the
ink band point by point, smoothed along the arc, Douglas-Peucker 6 m and Chaikin x3; inside the villages only thin line
work is cheap (house blocks are not); village streets are the smoothed long-axis centre line of each village (no
hooks, nothing under 80 m, joined to the nearest road within 150 m); road ends are snapped to the roads they meet and
overshoots cut (snap_ends). The automatic tracer (auto_trace) and blob_streets are kept but no longer used.
"""
import sys, os, json, math, argparse, time
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

Image.MAX_IMAGE_PIXELS = None
OLD_ROWS, CELL = 12, 2048.0
BLOCK_PX = (0, 1024, 4608, 5632)      # the 9 x 9 block in the 4 m sheet raster (x0, y0, x1, y1)
F = 3                                 # 4 m px per 12 m tracing px
R = 12.0                              # m per tracing px
NB = (BLOCK_PX[2] - BLOCK_PX[0]) // F # 1536

def to_m(ix, iy):
    """12 m block px (x east, y south, float, pixel centre at +0.5) -> DEM-lattice metres"""
    return BLOCK_PX[0] * 4.0 + (ix + 0.5) * R, OLD_ROWS * CELL - BLOCK_PX[1] * 4.0 - (iy + 0.5) * R

def to_px(x, y):
    return (x - BLOCK_PX[0] * 4.0) / R - 0.5, (OLD_ROWS * CELL - BLOCK_PX[1] * 4.0 - y) / R - 0.5

# ---- hand-reviewed overprint masks (DEM-lattice metres): the staff's black pencil (arrows, writing) that colour does
# not separate from print.  Roads under them are restored by the gap bridging (step 8).
# polygons in 4 m px of the 9 x 9 block crop of the sheet (x east, y south from its NW corner = sheet px x, y - 1024)
EXCLUDE = [
    dict(name='pencil arrow S of Petrovka', px=[(2690, 1340), (2950, 1330), (3060, 1265), (3210, 1265), (3220, 1340), (3130, 1420), (3040, 1450),
                                               (2960, 1520), (2880, 1640), (2820, 1740), (2760, 1720), (2800, 1600), (2700, 1420)]),
    dict(name='pencil arrow W of 252.2', px=[(2800, 1950), (2880, 1990), (3060, 2120), (3150, 2170), (3140, 2230), (2990, 2215), (2860, 2195),
                                            (2760, 2180), (2760, 2140), (2870, 2120), (2800, 2060)]),
    dict(name='pencil arrow at Vinogradovka', px=[(2540, 3140), (2640, 3110), (2720, 3200), (2830, 3330), (2910, 3400), (2900, 3480), (2830, 3510),
                                                 (2760, 3480), (2690, 3440), (2590, 3330), (2560, 3250)]),
    dict(name="pencil 'Сп 227' W of Kusty", px=[(3470, 640), (3870, 630), (3960, 620), (4050, 650), (4060, 740), (3990, 760), (3900, 760), (3700, 800), (3470, 800)]),
    dict(name='pencil strokes E of Kusty', px=[(4080, 640), (4170, 640), (4170, 790), (4080, 790)]),
]

# ---- guided roads: every road, cart track and field path of the sheet inside the block, read off the sheet tile by tile
# (4 m block px: x east, y south from the block's NW corner = sheet px (x, y - 1024)); each is snapped to the sheet's
# line work between its waypoints (least-cost path, snap_road). Classes from the symbol: secondary = double line,
# track = single solid line, path = dashed line, residential = village street (drawn straight between its waypoints).
GUIDED = [
    # t_00 / t_10 (W edge: Olkhovsky, Ilyinsky, Krasny Oktyabr)
    # c70: dropped (no line on the sheet / brown ravine edge) - was ('path', [(0, 52), (28, 136)]),
    # c70: dropped (no line on the sheet / brown ravine edge) - was ('track', [(25, 25), (78, 103), (128, 169)]),
    # c70: dropped (no line on the sheet / brown ravine edge) - was ('track', [(187, 0), (219, 62), (240, 100)]),
    # c70: dropped (no line on the sheet / brown ravine edge) - was ('track', [(0, 290), (37, 319), (62, 362), (87, 387), (125, 400), (150, 410)]),
    ('track', [(150, 500), (281, 505), (356, 531), (437, 552), (530, 552), (625, 546), (700, 548)]),
    ('track', [(437, 552), (487, 500), (519, 450), (525, 400)]),
    ('track', [(640, 778), (700, 760), (820, 745), (1024, 742)]),
    ('path', [(300, 860), (345, 910), (400, 1000), (440, 1100), (455, 1200), (465, 1290)]),
    ('path', [(835, 790), (815, 900), (795, 1000), (790, 1100), (770, 1200), (745, 1300)]),
    ('secondary', [(465, 1290), (560, 1390), (660, 1500), (760, 1610), (860, 1740), (900, 1765)]),   # c70: waypoints re-read
    ('track', [(600, 1470), (660, 1400), (700, 1340), (745, 1305), (800, 1250), (870, 1220), (968, 1235)]),
    ('secondary', [(880, 1820), (800, 1900), (760, 1960), (700, 2100), (640, 2220), (580, 2330), (550, 2400), (530, 2500), (510, 2600), (490, 2700), (470, 2800), (440, 2900), (410, 3000), (380, 3100), (340, 3180), (290, 3260), (240, 3340), (195, 3430), (150, 3530), (100, 3640), (60, 3712)]),
    # t_01 / t_11 (Veselyi - Kurlov - Kluchi - 226.6)
    ('track', [(960, 470), (1060, 400), (1120, 370), (1160, 300), (1175, 210), (1205, 140), (1290, 112)]),
    ('track', [(1170, 760), (1300, 850), (1400, 960), (1460, 1050), (1520, 1132)]),
    ('track', [(968, 1235), (1200, 1195), (1500, 1135), (1700, 1090), (1920, 1050), (2010, 1045)]),
    ('path', [(1625, 1105), (1700, 1205), (1780, 1300), (1850, 1390), (1910, 1460)]),
    # t_02 / t_03 / t_04 (12.0 road, Voroshilova, Beregovoye, V. Olshanka, Kusty)
    ('secondary', [(1800, 0), (1950, 60), (2100, 140), (2180, 205), (2280, 280), (2330, 320), (2450, 370), (2600, 440), (2740, 500), (2800, 545), (2870, 600), (2960, 650), (3100, 740), (3300, 850), (3450, 910), (3600, 985), (3700, 1035), (3800, 1150), (3900, 1300), (3990, 1430), (4060, 1540), (4120, 1600)]),
    ('track', [(2390, 370), (2300, 600), (2200, 800), (2160, 830), (2070, 930)]),
    ('track', [(2280, 0), (2276, 270)]),
    ('secondary', [(2960, 650), (2900, 760), (2850, 850), (2800, 930), (2760, 980), (2690, 1060), (2590, 1160), (2490, 1260), (2390, 1360), (2290, 1460), (2200, 1540), (2100, 1650), (2000, 1780), (1900, 1830), (1700, 1855), (1550, 1870), (1400, 1880), (1250, 1890), (1080, 1850), (900, 1765)]),
    ('secondary', [(3050, 600), (3200, 520), (3300, 470), (3420, 420), (3560, 330), (3650, 260), (3700, 230)]),
    ('track', [(3060, 615), (3130, 700), (3195, 775)]),
    ('track', [(2940, 385), (3005, 370), (3015, 290), (3070, 250), (3160, 245)]),
    ('track', [(3160, 245), (3120, 140), (3085, 0)]),
    ('path', [(3100, 25), (3230, 60), (3330, 60), (3420, 35)]),
    ('track', [(3640, 150), (3850, 200), (4000, 230), (4120, 270), (4210, 340), (4300, 460)]),
    ('track', [(4300, 460), (4440, 482), (4530, 492)]),
    ('track', [(4555, 0), (4565, 150), (4545, 350), (4530, 480), (4545, 580)]),
    ('track', [(3930, 800), (3890, 900), (3860, 1010), (3830, 1140)]),
    # t_12 / t_13 / t_23 (Prelestnoye, 10.0 road, Oktyabrsky, 252.2)
    ('secondary', [(2190, 1552), (2700, 1813)], 'straight'),   # c70: waypoints re-read
    ('track', [(2800, 1090), (3150, 1310), (3560, 1490), (3700, 1560), (3850, 1690)]),
    ('secondary', [(2950, 1790), (3280, 1935)]),
    ('path', [(3000, 1800), (2965, 1900), (2930, 1990)]),
    ('secondary', [(3150, 2100), (3150, 2330)]),
    ('path', [(3150, 2330), (3350, 2180), (3460, 2210)]),
    ('path', [(3295, 1955), (3380, 2010), (3460, 2100), (3490, 2130)]),
    # t_14 (Prokhorovka town)
    ('residential', [(3850, 1690), (4000, 1650), (4120, 1610), (4300, 1585), (4450, 1555), (4608, 1525)]),
    ('residential', [(4300, 1585), (4310, 1700), (4330, 1820), (4345, 1960)]),
    ('residential', [(4120, 1610), (4200, 1470), (4300, 1330), (4400, 1200)]),
    ('track', [(3900, 1700), (3820, 1800), (3760, 1880), (3720, 1950), (3690, 2050), (3660, 2150), (3600, 2200)]),
    # t_20 (Prokhorovka W - Gryaznoye)
    ('residential', [(420, 2620), (400, 2720), (390, 2816)]),
    # t_21 / t_22 (Kozlovka - 217.9, 241.6)
    # c70: dropped (no line on the sheet / brown ravine edge) - was ('track', [(1130, 2040), (1112, 2150), (1115, 2300), (1120, 2450), (1122, 2640)]),
    # c70: dropped (no line on the sheet / brown ravine edge) - was ('track', [(1122, 2640), (1200, 2645), (1262, 2690)]),
    ('track', [(2100, 2800), (2200, 2700), (2310, 2595)]),
    ('track', [(2310, 2595), (2380, 2655), (2440, 2710)]),
    # t_24 (Lutovo, Yamki, Prokhorovka - Pravorot)
    ('track', [(4110, 1615), (4110, 1800), (4120, 2000), (4135, 2200), (4150, 2240), (4125, 2290), (4115, 2440), (4130, 2550), (4150, 2660), (4140, 2780)]),
    ('secondary', [(4560, 1530), (4540, 1700), (4530, 1900), (4530, 2100), (4520, 2300), (4500, 2440), (4460, 2650), (4420, 2816), (4400, 2950), (4370, 3100), (4330, 3230), (4300, 3350), (4270, 3450), (4220, 3550), (4170, 3640), (4140, 3712)]),
    ('path', [(4290, 1990), (4350, 2050), (4420, 2100)]),
    # t_30 (Gryaznoye - Mal. Mayachki)
    ('track', [(300, 3300), (350, 3230), (410, 3195), (470, 3210), (560, 3250), (690, 3300)]),
    ('secondary', [(290, 3320), (340, 3370), (450, 3460), (560, 3560), (650, 3640), (730, 3712), (800, 3770), (900, 3850), (950, 3885)]),
    ('track', [(620, 2880), (700, 2950), (800, 2980), (900, 3000), (1000, 3010), (1100, 3020), (1200, 3015), (1300, 3005), (1420, 3080), (1520, 3160), (1610, 3225), (1595, 3280), (1650, 3350), (1730, 3395)]),
    ('track', [(880, 3000), (935, 3080), (1000, 3170), (1050, 3200), (1150, 3260), (1260, 3310), (1350, 3340), (1420, 3410), (1480, 3480), (1520, 3530)]),
    ('path', [(955, 2700), (965, 2800), (975, 2900)]),
    # t_31 / t_32 / t_33 (224.5, 9.0 road, Teterevino, Komsomolets, Ivanovsky Vyselok, Storozhevoye, Vinogradovka)
    ('secondary', [(1230, 3712), (1350, 3640), (1500, 3530), (1650, 3420), (1820, 3310), (1900, 3260), (2000, 3200), (2130, 3110), (2200, 3060), (2300, 2960), (2380, 2900)]),
    ('path', [(900, 2770), (1050, 2800), (1150, 2815), (1262, 2830), (1500, 2862), (1600, 2880), (1700, 2900), (1830, 2925)]),
    ('path', [(1000, 3420), (1100, 3455), (1200, 3485), (1300, 3515)]),
    ('track', [(2320, 3335), (2500, 3380), (2700, 3425), (2900, 3470)]),
    ('track', [(2195, 2870), (2205, 3000), (2210, 3200), (2212, 3400), (2215, 3600), (2218, 3712)]),
    ('track', [(2830, 2880), (2900, 3000), (2960, 3150), (2990, 3290)]),
    ('path', [(3000, 3190), (3100, 3220), (3250, 3250), (3400, 3280), (3550, 3295), (3712, 3300), (3850, 3320), (4000, 3333)]),
    # the Belgorod - Prokhorovka road beside the railway (NW side), Komsomolets - 252.2 - Prokhorovka
    ('secondary', [(2380, 2900), (2480, 2790), (2640, 2600), (2800, 2420), (2950, 2260), (3080, 2130), (3140, 2085), (3280, 1935), (3400, 1800), (3550, 1720), (3700, 1690), (3850, 1690)]),
    # t_34 (Pravorot, Zhimolostnoye road)
    ('track', [(3080, 4280), (3450, 3900), (3700, 3600), (3820, 3460), (3900, 3380), (4000, 3330), (4200, 3290), (4330, 3240)]),
    ('path', [(3600, 2860), (3700, 2870), (3800, 2890), (3950, 2915)]),
    # t_40 (9.0 road W part, Luchki)
    ('secondary', [(145, 4340), (200, 4320), (370, 4315), (500, 4225), (600, 4150), (700, 4065), (800, 3975), (950, 3885), (1100, 3790), (1230, 3712)]),
    ('track', [(0, 4430), (145, 4340)]),
    ('track', [(0, 4255), (145, 4340)]),
    ('path', [(400, 3710), (370, 3800), (345, 3900), (320, 4010)]),
    ('track', [(370, 4312), (300, 4380), (270, 4440), (240, 4500), (200, 4560), (180, 4608)]),
    # t_41 (240, 243.0, Ozerovsky)
    ('track', [(1230, 3720), (1300, 3830), (1380, 3950), (1440, 4070), (1490, 4200), (1530, 4310)]),
    ('track', [(1450, 3600), (1425, 3700), (1415, 3800), (1440, 3900), (1490, 4000), (1530, 4100), (1560, 4200), (1590, 4320)]),
    ('track', [(1470, 3600), (1570, 3660), (1660, 3740), (1730, 3830), (1790, 3920), (1870, 4010), (1920, 4060)]),
    ('track', [(1590, 4330), (1700, 4310), (1800, 4300), (1920, 4300)]),
    # t_42 (Yasnaya Polyana, Belenikhino, Ivanovka)
    ('track', [(1920, 4300), (2000, 4240), (2110, 4150)]),
    ('track', [(1940, 3910), (2040, 4030), (2110, 4150)]),
    ('track', [(2110, 4150), (2200, 4110), (2290, 4060)]),
    ('track', [(2800, 3600), (2760, 3750), (2720, 3870), (2680, 3960), (2690, 4050), (2700, 4200)]),
    ('track', [(2450, 4100), (2600, 4120), (2760, 4190)]),
    # t_43 (Ivanovka - 234.9 - Zhimolostnoye)
    ('track', [(3078, 4305), (3040, 4420), (3000, 4520), (2970, 4608)]),
    ('track', [(2700, 4185), (2800, 4190), (2900, 4235), (3000, 4275), (3078, 4305), (3200, 4350), (3400, 4425), (3560, 4480), (3712, 4490)]),
    # t_44 (Zhimolostnoye E, Dalny, Plota, 247.7)
    ('secondary', [(4140, 3712), (4180, 3740), (4260, 3810), (4290, 3900), (4290, 4000), (4280, 4100), (4265, 4200), (4255, 4400), (4245, 4608)]),
    ('track', [(4280, 4120), (4350, 4250), (4420, 4380), (4500, 4500), (4540, 4560)]),
    ('residential', [(4150, 3610), (4300, 3660), (4450, 3730), (4608, 3810)]),

    # c70 additions (5 Nov review, 2 x 2 km squares)
    ('secondary', [(2700, 1813), (2900, 1950), (3140, 2090)]),
    ('residential', [(3870, 3930), (3960, 3895), (4060, 3850), (4160, 3815), (4250, 3800)]),
    ('track', [(4060, 3975), (4130, 4040), (4200, 4100), (4275, 4135)]),
    ('path', [(3905, 4275), (4000, 4285), (4100, 4300), (4255, 4310)]),
    ('track', [(4045, 4340), (4150, 4340), (4255, 4338)]),
    ('track', [(3600, 4448), (3700, 4445), (3800, 4440), (3900, 4440), (4000, 4440), (4080, 4432), (4255, 4445)]),
    ('track', [(4080, 4435), (4075, 4520), (4075, 4608)]),
    ('residential', [(2195, 890), (2230, 990), (2260, 1100), (2290, 1220)]),
]

# ---- bridging parameters (12 m px)
SPUR = 6            # spurs shorter than this go (72 m)
MIN_PIECE = 25      # lone pieces shorter than this go (300 m)
MIN_PIECE_PATH = 30 # ... dashed ones (360 m)
GAP = 9             # an end joins anything it points at within 108 m
GAP_ALIGNED = 22    # ... and an end pointing straight at another end within 264 m (labels, villages)
GAP_BLANK = 300     # ... across a missing-tile patch (end to end only)

# ------------------------------------------------------------------ masks
def ink_mask(a):
    """black print: dark, unsaturated, not blue (pencil); then the dark-brown contours and ravine edges go by their
    LOCAL mean colour (black print r - b ~ 17-22, brown ~ 29-38; single pixels overlap, so the mean of the ink within
    ~25 m decides)"""
    a = a.astype(np.int16)
    g = a.mean(-1); r, b = a[..., 0], a[..., 2]; sat = a.max(-1) - a.min(-1)
    # the paper brightness of the neighbourhood (~300 m): the SW sheet is printed fainter (lines g ~ 120 on paper ~ 210)
    paper = (g > 160).astype(np.float32); g8 = g[::8, ::8].astype(np.float32); p8 = paper[::8, ::8]
    bg = ndi.uniform_filter(g8 * p8, 9) / np.maximum(ndi.uniform_filter(p8, 9), 1e-3)
    bg = np.where(ndi.uniform_filter(p8, 9) > 0.05, bg, 205.0)
    bg = np.repeat(np.repeat(bg, 8, 0), 8, 1)[:g.shape[0], :g.shape[1]]
    ink = (g < np.minimum(0.62 * bg, 135)) & (sat < 60) & ((b - r) < 10)
    f = ink.astype(np.float32)
    m = ndi.gaussian_filter((r - b).astype(np.float32) * f, 6) / np.maximum(ndi.gaussian_filter(f, 6), 1e-3)
    return ink & (m < 27)

def grid_lines(A, S=576, spacing=500.0):
    """thin straight lines of the km grid in a 4 m ink raster: per strip of S rows the shear angle that maximises the
    column-sum energy, then narrow peaks covering >= 55 % of the strip on the 2 km lattice. Returns (y0, h, deg, x)."""
    out = []; H, W = A.shape
    for y0 in range(0, H, S // 2):
        sub = A[y0:y0 + S]; h = sub.shape[0]
        if h < S // 2: continue
        ys, xs = np.nonzero(sub); yc = ys - h / 2
        best = None
        for a in np.arange(-3, 3.001, 0.05):
            t = math.tan(math.radians(a)); xp = np.round(xs - yc * t).astype(int) + 200
            hist = np.bincount(xp, minlength=W + 400).astype(float)
            sc = (hist ** 2).sum()
            if best is None or sc > best[0]: best = (sc, a, hist)
        _, a, hist = best
        c3 = np.convolve(hist, np.ones(3), 'same')
        side = np.maximum.reduce([np.roll(hist, k) for k in (4, 5, 6, 7, -4, -5, -6, -7)])
        score = c3 - 3 * side
        pk = [x for x in range(2, len(hist) - 2) if c3[x] >= 0.55 * h and score[x] >= 0.35 * h and c3[x] == c3[x - 2:x + 3].max()]
        pk2 = []
        for x in pk:
            if pk2 and x - pk2[-1] < 4: continue
            pk2.append(x)
        strong = [x for x in pk2 if c3[x] >= 1.4 * h]
        if strong:   # a strip may hold two sheets with their own lattices: a peak must be on the 2 km lattice of a strong one
            pk2 = [x for x in pk2 if any(min((x - y) % spacing, spacing - (x - y) % spacing) < 14 for y in strong)]
        for x in pk2: out.append((y0, h, a, x - 200))
    return out

def remove_runs(A, lines, maxw=6):
    rm = np.zeros_like(A); H, W = A.shape
    for (y0, h, a, x) in lines:
        t = math.tan(math.radians(a))
        for yy in range(y0, min(H, y0 + h)):
            xc = x + (yy - y0 - h / 2) * t
            lo, hi = max(0, int(round(xc)) - 5), min(W, int(round(xc)) + 6)
            if hi <= lo: continue
            idx = np.nonzero(A[yy, lo:hi])[0]
            if not len(idx): continue
            k = idx[np.argmin(np.abs(idx + lo - xc))] + lo
            a_ = b_ = k
            while a_ - 1 >= 0 and A[yy, a_ - 1]: a_ -= 1
            while b_ + 1 < W and A[yy, b_ + 1]: b_ += 1
            if b_ - a_ + 1 <= maxw and abs((a_ + b_) / 2 - xc) <= 4: rm[yy, a_:b_ + 1] = True
    return rm

def pool(m, thr):
    return m.reshape(NB, F, NB, F).mean((1, 3)) >= thr

def disk(r):
    y, x = np.mgrid[-r:r + 1, -r:r + 1]; return x * x + y * y <= r * r + 0.5

LATS, LONW, LAT_C = 50.904605, 36.4903, 51.0334   # the DEM lattice of prokh_gen.py (its project())
def osm_main_railway(osm_path):
    """the main-line railway ways of the OSM extract in lattice metres (the only thing read from OSM)"""
    data = json.load(open(osm_path, encoding='utf-8'))
    M_LAT = 111320.0; M_LON = 111320.0 * math.cos(math.radians(LAT_C))
    nodes = {e['id']: ((e['lon'] - LONW) * M_LON, (e['lat'] - LATS) * M_LAT) for e in data['elements'] if e['type'] == 'node'}
    out = []
    for e in data['elements']:
        t = e.get('tags', {})
        if e['type'] == 'way' and t.get('railway') == 'rail' and t.get('usage') == 'main':
            p = [nodes[n] for n in e['nodes'] if n in nodes]
            if len(p) >= 2: out.append(p)
    return out

def railway_band(ink, osm_path):
    """dense ink near the OSM main line (12 m grid), dilated: the railway symbol and the huts / platforms on it"""
    if not osm_path or not os.path.exists(osm_path): return np.zeros_like(ink), []
    rails = osm_main_railway(osm_path)
    cor = Image.new('L', (NB, NB), 0); d = ImageDraw.Draw(cor)
    for p in rails: d.line([to_px(x, y) for x, y in p], fill=255, width=23)
    cor = np.asarray(cor) > 0
    den = ndi.uniform_filter(ink.astype(np.float32), 3)
    rb = (den > 0.7) & cor
    lab, n = ndi.label(ndi.binary_dilation(rb, iterations=1), structure=np.ones((3, 3))); sl = ndi.find_objects(lab)
    keep = np.zeros(n + 1, bool)
    for k, q in enumerate(sl): keep[k + 1] = max(q[0].stop - q[0].start, q[1].stop - q[1].start) >= 20
    rb = keep[lab] & cor
    return ndi.binary_dilation(rb, structure=disk(1)), rails

def exclude_mask():
    im = Image.new('L', (NB, NB), 0); d = ImageDraw.Draw(im)
    for e in EXCLUDE: d.polygon([(x / F, y / F) for x, y in e['px']], fill=255)
    return np.asarray(im) > 0

# ------------------------------------------------------------------ skeleton graph
OFFS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

def skel_graph(sk):
    """skeleton -> (nodes {id: (x, y)}, edges [[a, b, pts (x, y) array]])"""
    H, W = sk.shape
    nb = ndi.convolve(sk.astype(np.uint8), np.ones((3, 3), np.uint8), mode='constant') - 1
    nodepx = sk & (nb != 2)
    lab, n = ndi.label(nodepx, structure=np.ones((3, 3)))
    cen = ndi.center_of_mass(nodepx, lab, range(1, n + 1)) if n else []
    nodes = {k + 1: (c[1], c[0]) for k, c in enumerate(cen)}
    visited = np.zeros_like(sk); edges = []
    def nbrs(y, x):
        for dy, dx in OFFS:
            yy, xx = y + dy, x + dx
            if 0 <= yy < H and 0 <= xx < W and sk[yy, xx]: yield yy, xx
    for y, x in zip(*np.nonzero(nodepx)):
        a = lab[y, x]
        for yy, xx in nbrs(y, x):
            if lab[yy, xx] or visited[yy, xx]: continue
            path = [(y, x), (yy, xx)]; visited[yy, xx] = True
            py, px = y, x; cy, cx = yy, xx; end = None
            while True:
                nxt = None
                for qy, qx in nbrs(cy, cx):
                    if (qy, qx) == (py, px): continue
                    if lab[qy, qx]:
                        if (qy, qx) != path[0] or len(path) > 2: end = (qy, qx); break
                        continue
                    if not visited[qy, qx]: nxt = (qy, qx); break
                if end is not None: path.append(end); break
                if nxt is None: break
                visited[nxt] = True; path.append(nxt); py, px = cy, cx; cy, cx = nxt
            if end is None:
                n += 1; nodes[n] = (path[-1][1], path[-1][0]); b = n
            else: b = lab[end]
            edges.append([a, b, np.array([(q[1], q[0]) for q in path], float)])
    rest = sk & ~visited & ~nodepx
    lab2, n2 = ndi.label(rest, structure=np.ones((3, 3)))
    for k in range(1, n2 + 1):
        yy, xx = np.nonzero(lab2 == k)
        if len(yy) < 3: continue
        start = (yy[0], xx[0]); path = [start]; seen = {start}; cur = start
        while True:
            nxt = None
            for q in nbrs(*cur):
                if q not in seen and lab2[q] == k: nxt = q; break
            if nxt is None: break
            seen.add(nxt); path.append(nxt); cur = nxt
        n += 1; nodes[n] = (start[1], start[0])
        edges.append([n, n, np.array([(q[1], q[0]) for q in path + [start]], float)])
    return nodes, edges

def plen(p): return float(np.hypot(*np.diff(p, axis=0).T).sum()) if len(p) > 1 else 0.0

def degrees(edges):
    deg = {}
    for a, b, p, *_ in edges:
        deg[a] = deg.get(a, 0) + 1; deg[b] = deg.get(b, 0) + 1
    return deg

def merge_deg2(nodes, edges, same=lambda e1, e2: True):
    """join edges through nodes of degree 2"""
    changed = True
    while changed:
        changed = False
        inc = {}
        for i, e in enumerate(edges):
            inc.setdefault(e[0], []).append(i); inc.setdefault(e[1], []).append(i)
        for nd, lst in inc.items():
            if len(lst) != 2 or lst[0] == lst[1]: continue
            i, j = lst; e1, e2 = edges[i], edges[j]
            if e1 is None or e2 is None or not same(e1, e2): continue
            p1 = e1[2] if e1[1] == nd else e1[2][::-1]; a = e1[0] if e1[1] == nd else e1[1]
            p2 = e2[2] if e2[0] == nd else e2[2][::-1]; b = e2[1] if e2[0] == nd else e2[0]
            new = [a, b, np.vstack([p1, p2[1:]])] + list(e1[3:])
            edges[i] = new; edges[j] = None; changed = True
            break
        edges[:] = [e for e in edges if e is not None]
    return edges

def end_dir(p, at_end, k=6):
    """unit direction pointing OUT of the polyline at its end (at_end) or start"""
    q = p[::-1] if not at_end else p
    L = 0.0; i = len(q) - 1
    while i > 0 and L < k: L += math.hypot(*(q[i] - q[i - 1])); i -= 1
    v = q[-1] - q[i]; n = math.hypot(*v)
    return v / n if n > 1e-6 else np.array([0.0, 0.0])

def rdp(p, eps):
    if len(p) < 3: return p
    a, b = p[0], p[-1]; ab = b - a; L = math.hypot(*ab)
    if L < 1e-9: d = np.hypot(*(p - a).T)
    else: d = np.abs(ab[0] * (p[:, 1] - a[1]) - ab[1] * (p[:, 0] - a[0])) / L
    i = int(np.argmax(d))
    if d[i] > eps:
        return np.vstack([rdp(p[:i + 1], eps)[:-1], rdp(p[i:], eps)])
    return np.array([a, b])

def chaikin(p, n=2):
    for _ in range(n):
        if len(p) < 3: return p
        q = [p[0]]
        for a, b in zip(p[:-1], p[1:]): q += [0.75 * a + 0.25 * b, 0.25 * a + 0.75 * b]
        q.append(p[-1]); p = np.array(q)
    return p

# ------------------------------------------------------------------ tracing
def solids(ink, vz):
    """(blocks, removed): solid ink (opening 5 px) inside the 1941 villages (house blocks) and solid pieces of small
    isolated ink (single houses, bold digits, symbols). Solids that belong to long line work stay: the improved roads
    are drawn filled, and on the faint SW sheet their band breaks into a chain of solid pieces."""
    c = ndi.binary_closing(ink, structure=np.ones((3, 3)))
    o = ndi.binary_opening(c, structure=disk(2))
    lab, n = ndi.label(c, structure=np.ones((3, 3))); sl = ndi.find_objects(lab)
    small = np.zeros(n + 1, bool)
    for k, q in enumerate(sl): small[k + 1] = max(q[0].stop - q[0].start, q[1].stop - q[1].start) < 25
    blocks = (o & vz) | (o & small[lab])
    return blocks, ndi.binary_dilation(blocks, structure=np.ones((3, 3))) & c

def components(ink2):
    """line work (>= 120 m across), dashes (small elongated pieces), the rest dropped"""
    lab, n = ndi.label(ink2, structure=np.ones((3, 3))); sl = ndi.find_objects(lab)
    cls = np.zeros(n + 1, np.uint8); info = {}
    for k, q in enumerate(sl):
        ext = max(q[0].stop - q[0].start, q[1].stop - q[1].start)
        if ext >= 10: cls[k + 1] = 1; continue
        if ext < 2: continue
        yy, xx = np.nonzero(lab[q] == k + 1)
        if len(yy) < 2: continue
        if len(yy) == 2: ev = np.array([0.0, 0.25]); evec = np.eye(2); dx_, dy_ = xx[1] - xx[0], yy[1] - yy[0]; evec[:, 1] = (dx_, dy_) / np.hypot(dx_, dy_)
        else: ev, evec = np.linalg.eigh(np.cov(np.stack([xx, yy]).astype(float)))
        L = 3.46 * math.sqrt(max(ev[1], 0)) + 1; Wd = 3.46 * math.sqrt(max(ev[0], 0)) + 1
        if L >= 3.5 and L >= 2.0 * Wd and Wd <= 3.3 and len(yy) <= 3.2 * L:
            cls[k + 1] = 2
            info[k + 1] = (xx.mean() + q[1].start, yy.mean() + q[0].start, evec[0, 1], evec[1, 1], L)
    return lab, cls, info

def link_dashes(info, shape, gap=7.5, cmin=0.8):
    ends = []; own = []
    for k, (mx, my, ux, uy, L) in info.items():
        for sgn in (-1, 1):
            ends.append((mx + sgn * ux * L / 2, my + sgn * uy * L / 2, sgn * ux, sgn * uy)); own.append(k)
    link = Image.new('L', shape[::-1], 0); dl = ImageDraw.Draw(link)
    if not ends: return np.asarray(link) > 0, {}
    ends = np.array(ends); own = np.array(own); T = cKDTree(ends[:, :2])
    deg = {}
    cand = []
    for i, (x, y, ux, uy) in enumerate(ends):
        for j in T.query_ball_point((x, y), gap):
            if j <= i or own[j] == own[i]: continue
            x2, y2, ux2, uy2 = ends[j]; dx, dy = x2 - x, y2 - y; dd = math.hypot(dx, dy)
            if dd < 0.5: c1 = c2 = 1.0
            else: c1 = (dx * ux + dy * uy) / dd; c2 = -(dx * ux2 + dy * uy2) / dd
            # the two dashes must also be roughly collinear with each other
            ca = -(ux * ux2 + uy * uy2)
            if c1 < cmin or c2 < cmin or ca < 0.8: continue
            cand.append((dd * (3.2 - c1 - c2 - ca), i, j))
    used = set()
    for sc, i, j in sorted(cand):
        if i in used or j in used: continue
        used.add(i); used.add(j)
        dl.line([tuple(ends[i][:2]), tuple(ends[j][:2])], fill=255, width=1)
        deg[own[i]] = deg.get(own[i], 0) + 1; deg[own[j]] = deg.get(own[j], 0) + 1
    return np.asarray(link) > 0, deg

def grid_band(V, Hh, width=5):
    """the detected km-grid lines drawn on the 12 m grid (for dropping traced pieces that run along them)"""
    im = Image.new('L', (NB, NB), 0); d = ImageDraw.Draw(im)
    for (y0, h, a, x) in V:
        t = math.tan(math.radians(a)); ya, yb = y0, y0 + h
        d.line([((x + (ya - y0 - h / 2) * t) / F, ya / F), ((x + (yb - y0 - h / 2) * t) / F, yb / F)], fill=255, width=width)
    for (x0, w, a, y) in Hh:   # transposed: 'x' is the row, the strip runs along x
        t = math.tan(math.radians(a)); xa, xb = x0, x0 + w
        d.line([(xa / F, (y + (xa - x0 - w / 2) * t) / F), (xb / F, (y + (xb - x0 - w / 2) * t) / F)], fill=255, width=width)
    return np.asarray(im) > 0

# ------------------------------------------------------------------ graph stages
class Ctx:
    """the 12 m rasters the edge attributes are read from"""
    def __init__(self, **kw): self.__dict__.update(kw)

def sample(mask, p):
    ix = np.clip(np.round(p[:, 0]).astype(int), 0, mask.shape[1] - 1); iy = np.clip(np.round(p[:, 1]).astype(int), 0, mask.shape[0] - 1)
    return mask[iy, ix]

def seg_pts(P, Q, step=0.5):
    n = max(2, int(math.hypot(*(Q - P)) / step) + 1)
    t = np.linspace(0, 1, n)[:, None]; return P[None] * (1 - t) + Q[None] * t

def annotate(e, cx):
    p = e[2]; a = e[3] if len(e) > 3 else {}
    if a.get('street') or a.get('bridge'):
        a['L'] = plen(p)
    else:
        a.update(L=plen(p), w=float(np.median(sample(cx.dt, p)) * 2), dash=float((sample(cx.dashd, p) & ~sample(cx.lined, p)).mean()),
                 grid=float(sample(cx.gridband, p).mean()))
    if len(e) > 3: e[3] = a
    else: e.append(a)
    return e

def build_graph(road, cx):
    from skimage.morphology import skeletonize
    closed = ndi.binary_closing(road, structure=np.ones((3, 3))) | road
    holes = ndi.binary_fill_holes(closed) & ~closed            # the hollow double lines, junction rings
    lab, n = ndi.label(holes)
    if n:
        sz = ndi.sum(holes, lab, range(1, n + 1)); small = np.zeros(n + 1, bool); small[1:] = sz <= 40
        closed |= small[lab]
    cx.dt = ndi.distance_transform_edt(closed)
    nodes, edges = skel_graph(skeletonize(closed))
    return nodes, [annotate(e, cx) for e in edges]

def merge(nodes, edges, cx, same=None):
    if same is None: same = lambda e1, e2: not (e1[3].get('street') or e2[3].get('street') or e1[3].get('bridge') or e2[3].get('bridge'))
    edges = merge_deg2(nodes, edges, same)
    for e in edges:
        if not e[3].get('street') and not e[3].get('bridge'): annotate(e, cx)
        else: e[3]['L'] = plen(e[2])
    return edges

def prune_spurs(nodes, edges, cx, maxlen, rounds=4):
    for _ in range(rounds):
        deg = degrees(edges); keep = []; rm = False
        for e in edges:
            a, b, p = e[:3]
            if a != b and ((deg[a] == 1 and deg[b] >= 3) or (deg[b] == 1 and deg[a] >= 3)) and e[3]['L'] < maxlen and not e[3].get('street'):
                rm = True; continue
            keep.append(e)
        edges = merge(nodes, keep, cx)
        if not rm: break
    return edges

def comps(edges):
    par = {}
    def f(x):
        while par.setdefault(x, x) != x: par[x] = par[par[x]]; x = par[x]
        return x
    for a, b, *_ in edges: par[f(a)] = f(b)
    out = {}
    for i, e in enumerate(edges): out.setdefault(f(e[0]), []).append(i)
    return list(out.values())

def drop_small(edges, minlen, keep_if=lambda es: False):
    out = []
    for c in comps(edges):
        es = [edges[i] for i in c]
        if sum(e[3]['L'] for e in es) >= minlen or keep_if(es): out += es
    return out

def junk_filter(edges, cx):
    """lettering, contour bits, tree symbols: small pieces that are wiggly (length >> extent) or knotty"""
    out = []; n_drop = 0
    for c in comps(edges):
        es = [edges[i] for i in c]
        L = sum(e[3]['L'] for e in es)
        P = np.vstack([e[2] for e in es]); ext = math.hypot(*(P.max(0) - P.min(0)))
        deg = degrees(es); knots = sum(1 for v in deg.values() if v != 2)
        if ext < 15 or (ext < 30 and (L > 1.5 * ext or knots > 2)) or (L < 60 and (L > 1.9 * ext or knots > 0.12 * L + 2)) or (L < 30 and np.mean([e[3].get('w', 0) for e in es]) > 4.5):
            n_drop += 1; continue
        out += es
    return out, n_drop

def bridge(nodes, edges, cx, gap=GAP, gap_al=GAP_ALIGNED, gap_blank=GAP_BLANK):
    """join road ends: to another end (end to end) or to a road they point at (T); see the module doc, step 8"""
    deg = degrees(edges)
    ends = []
    for i, e in enumerate(edges):
        a, b, p = e[:3]
        if len(p) < 2: continue
        if deg.get(a) == 1: ends.append((a, p[0], end_dir(p, False), i))
        if deg.get(b) == 1 and b != a: ends.append((b, p[-1], end_dir(p, True), i))
    if not ends: return edges, 0
    P = np.vstack([e[2] for e in edges]); own = np.concatenate([np.full(len(e[2]), i) for i, e in enumerate(edges)])
    pidx = np.concatenate([np.arange(len(e[2])) for e in edges])
    T = cKDTree(P); E = np.array([q[1] for q in ends]); TE = cKDTree(E)
    special = cx.rail | cx.excl | cx.vz          # masks under which the line work is gone (railway, pencil, house blocks)
    cand = []
    for k, (nd, Pk, dk, ik) in enumerate(ends):
        if not dk.any(): continue
        for j in TE.query_ball_point(Pk, gap_blank):
            if j <= k: continue
            nd2, Q, dq, iq = ends[j]
            if iq == ik and edges[ik][3]['L'] < 3 * gap: continue
            v = Q - Pk; D = math.hypot(*v)
            if D < 1e-6: cand.append((0.0, k, j, None)); continue
            u = v / D; c1 = float(dk @ u); c2 = float(-(dq @ u))
            if c1 < 0.5 or c2 < 0.5: continue
            sp = seg_pts(Pk, Q); fb = sample(cx.blank, sp).mean(); fs = sample(special, sp).mean()
            sc = None
            if D <= gap: sc = D * (3.0 - c1 - c2)
            elif D <= gap_al and c1 >= 0.9 and c2 >= 0.9: sc = D * (3.0 - c1 - c2) + 4
            elif D <= 2.5 * gap_al and fs >= 0.5 and c1 >= 0.9 and c2 >= 0.9: sc = D * (3.0 - c1 - c2) + 8
            elif gap_blank > 0 and fb >= 0.4 and c1 >= 0.94 and c2 >= 0.94 and abs(dk[0] * v[1] - dk[1] * v[0]) <= 0.15 * D: sc = 20 + 0.05 * D
            if sc is not None: cand.append((sc, k, j, None))
        for idx in T.query_ball_point(Pk, 2 * gap):
            if own[idx] == ik: continue
            Q = P[idx]; v = Q - Pk; D = math.hypot(*v)
            if D < 1e-6: continue
            c1 = float(dk @ v) / D
            fs = sample(special, seg_pts(Pk, Q)).mean()
            if (D <= gap and c1 >= 0.7) or (fs >= 0.5 and c1 >= 0.85):
                cand.append((D * (2.2 - c1) + 2, k, None, idx))
    used = set(); joins_t = {}; new = []; nb = 0
    for sc, k, j, idx in sorted(cand, key=lambda c: c[0]):
        if k in used or (j is not None and j in used): continue
        nd, Pk, dk, ik = ends[k]
        if j is not None:
            nd2, Q, dq, iq = ends[j]; used.add(k); used.add(j)
            new.append([nd, nd2, np.vstack([Pk, Q]), {'bridge': True}])
        else:
            used.add(k); ti = own[idx]
            joins_t.setdefault(ti, []).append((pidx[idx], nd, Pk))
        nb += 1
    # split the edges that T-joins land on
    nid = max(nodes) + 1; out = []
    for i, e in enumerate(edges):
        if i not in joins_t: out.append(e); continue
        a, b, p, at = e
        cuts = sorted(joins_t[i], key=lambda q: q[0])
        prev_n, prev_i = a, 0
        for (pi, nd, Pk) in cuts:
            pi = int(min(max(pi, 1), len(p) - 2)) if len(p) > 2 else 0
            if pi <= prev_i:   # several joins at the same place: join to the previous cut node
                new.append([nd, prev_n, np.vstack([Pk, p[prev_i]]), {'bridge': True}]); continue
            nodes[nid] = tuple(p[pi]); out.append([prev_n, nid, p[prev_i:pi + 1], dict(at)])
            new.append([nd, nid, np.vstack([Pk, p[pi]]), {'bridge': True}])
            prev_n, prev_i = nid, pi; nid += 1
        out.append([prev_n, b, p[prev_i:], dict(at)])
    for e in out:
        if not e[3].get('bridge') and not e[3].get('street'): annotate(e, cx)
    for e in new: e[3]['L'] = plen(e[2])
    return out + new, nb

def village_streets(blocks, bu, roadpx, nodes, cx, lane=4.0):
    """the streets of the 1941 villages (step 9): medial axis of the lanes between the house blocks; for a village whose
    blocks leave no lane and no traced road runs through it, the centre line of the built-up blob"""
    from skimage.morphology import skeletonize
    region = ndi.binary_dilation(bu, structure=disk(14))
    blk = ndi.binary_closing(blocks, structure=np.ones((3, 3)))
    sk = skeletonize(region & ~blk)
    dtb = ndi.distance_transform_edt(~blk)
    zone = ndi.binary_dilation(bu, structure=disk(2))
    near_road = ndi.binary_dilation(roadpx, structure=disk(3))
    st = sk & zone & (dtb <= lane) & ~near_road
    nn, ee = skel_graph(st)
    base = max(nodes) + 1 if nodes else 1
    out = []
    for a, b, p in ee:
        out.append([a + base, b + base, p, {'street': True}])
    for k, v in nn.items(): nodes[k + base] = v
    for e in out: e[3]['L'] = plen(e[2])
    out = prune_spurs(nodes, out, cx, 4)
    out = drop_small(out, 6)
    # villages with no lane and no road: centre line of the blob
    lab, n = ndi.label(bu, structure=np.ones((3, 3)))
    have = ndi.binary_dilation(roadpx, structure=disk(2))
    for e in out:
        for x, y in e[2]: have[int(round(y)), int(round(x))] = True
    have = ndi.binary_dilation(have, structure=disk(2))
    nid = max(nodes) + 1; n_blob = 0
    for k, q in enumerate(ndi.find_objects(lab)):
        m = lab[q] == k + 1
        if m.sum() < 12: continue
        yy, xx = np.nonzero(m)
        ev, evec = np.linalg.eigh(np.cov(np.stack([xx, yy]).astype(float))) if len(xx) > 2 else (np.array([0, 0]), np.eye(2))
        span = 3.46 * math.sqrt(max(ev[-1], 0))
        covered = (have[q] & m).sum() / m.sum()
        if covered >= 0.35 or span < 5: continue
        c = ndi.binary_closing(np.pad(m, 3), structure=disk(2))[3:-3, 3:-3] | m
        s2 = skeletonize(c)
        n2, e2 = skel_graph(s2)
        if not e2: continue
        # the longest path through the blob skeleton
        best = max(e2, key=lambda e: plen(e[2]))
        p = best[2] + np.array([q[1].start, q[0].start], float)
        if plen(p) < 4: continue
        nodes[nid] = tuple(p[0]); nodes[nid + 1] = tuple(p[-1])
        out.append([nid, nid + 1, p, {'street': True, 'blob': True, 'L': plen(p)}]); nid += 2; n_blob += 1
    return out, n_blob

# ------------------------------------------------------------------ classes, chains, output
CLASS_ORDER = {'secondary': 3, 'track': 2, 'path': 1, 'residential': 0}

def classify(nodes, edges, w_double=3.6, dash_frac=0.3):
    for e in edges:
        a = e[3]
        if a.get('street'): a['cls'] = 'residential'
        elif a.get('bridge'): a['cls'] = None
        elif a.get('dash', 0) >= dash_frac: a['cls'] = 'path'
        elif a.get('w', 0) >= w_double: a['cls'] = 'secondary'
        else: a['cls'] = 'track'
    # short pieces take the class of their neighbours (a double line thins at a junction, a dashed track has a solid
    # stretch at a crossing); bridges take the class of the roads they join (the higher one)
    for _ in range(3):
        inc = {}
        for i, e in enumerate(edges): inc.setdefault(e[0], []).append(i); inc.setdefault(e[1], []).append(i)
        for i, e in enumerate(edges):
            a = e[3]
            if a['cls'] == 'residential' and not a.get('bridge'): continue
            nb = [edges[j][3]['cls'] for nd in (e[0], e[1]) for j in inc[nd] if j != i and edges[j][3]['cls'] is not None]
            if a['cls'] is None:
                if nb: a['cls'] = max(nb, key=lambda c: CLASS_ORDER[c])
                continue
            if a['L'] < 12 and len(nb) >= 2 and len(set(nb)) == 1 and nb[0] != 'residential': a['cls'] = nb[0]
    for e in edges:
        if e[3]['cls'] is None: e[3]['cls'] = 'track'
    return edges

def chains(nodes, edges):
    """polylines: edges joined through degree-2 nodes and, at junctions, the straightest continuation of the same class"""
    inc = {}
    for i, e in enumerate(edges): inc.setdefault(e[0], []).append(i); inc.setdefault(e[1], []).append(i)
    def out_dir(i, nd):
        p = edges[i][2]; return end_dir(p, False) if edges[i][0] == nd else end_dir(p, True)
    pair = {}   # (node, edge) -> partner edge at that node
    for nd, lst in inc.items():
        if len(lst) < 2: continue
        cand = []
        for x in range(len(lst)):
            for y in range(x + 1, len(lst)):
                i, j = lst[x], lst[y]
                if i == j or edges[i][3]['cls'] != edges[j][3]['cls']: continue
                c = float(out_dir(i, nd) @ out_dir(j, nd))
                if len(lst) == 2 or c < -0.7: cand.append((c, i, j))
        used = set()
        for c, i, j in sorted(cand):
            if i in used or j in used: continue
            used.add(i); used.add(j); pair[(nd, i)] = j; pair[(nd, j)] = i
    done = set(); out = []
    for i0, e0 in enumerate(edges):
        if i0 in done: continue
        # walk back to the chain start
        i, nd = i0, e0[0]; seen = {i0}
        while (nd, i) in pair and pair[(nd, i)] not in seen:
            j = pair[(nd, i)]; seen.add(j)
            nd = edges[j][1] if edges[j][0] == nd else edges[j][0]; i = j
        # i is the first edge, nd its free end
        pts = []; cur, at = i, nd
        while True:
            done.add(cur); e = edges[cur]
            p = e[2] if e[0] == at else e[2][::-1]
            pts.append(p if not pts else p[1:])
            at = e[1] if e[0] == at else e[0]
            nxt = pair.get((at, cur))
            if nxt is None or nxt in done: break
            cur = nxt
        out.append((e0[3]['cls'], np.vstack(pts)))
    return out

def export(ch, eps=0.7):
    roads = []
    for k, (cls, p) in enumerate(ch):
        q = chaikin(rdp(p, eps), 2)
        pts = [[round(x, 1), round(y, 1)] for x, y in (to_m(px, py) for px, py in q)]
        L = plen(np.array(pts))
        if L < 1: continue
        roads.append(dict(highway=cls, length_m=round(L), pts=pts))
    return roads

COLORS = {'secondary': (215, 0, 0), 'track': (0, 70, 255), 'path': (0, 160, 0), 'residential': (230, 0, 230)}

def render(sheet_rgb, roads, out_png, scale=1.0, box=None, width=4, fade=0.55):
    """sheet (4 m block crop, PIL) with the traced roads on top; box = (x0, y0, x1, y1) in 4 m block px"""
    bg = sheet_rgb if box is None else sheet_rgb.crop(box)
    bg = Image.blend(bg, Image.new('RGB', bg.size, (255, 255, 255)), fade)
    ox, oy = (0, 0) if box is None else box[:2]
    if scale != 1.0: bg = bg.resize((int(bg.size[0] * scale), int(bg.size[1] * scale)), Image.LANCZOS)
    d = ImageDraw.Draw(bg)
    for r in sorted(roads, key=lambda r: CLASS_ORDER[r['highway']]):
        pp = [(((x / 4.0) - BLOCK_PX[0] - ox) * scale, ((OLD_ROWS * CELL - y) / 4.0 - BLOCK_PX[1] - oy) * scale) for x, y in r['pts']]
        d.line(pp, fill=COLORS[r['highway']], width=width, joint='curve')
    bg.save(out_png)

# ------------------------------------------------------------------ guided tracing (the method in use, see the doc)
def cost_raster(ink4, blank4, rail4=None, soft4=None):
    """4 m cost: low on the line work (the centre of a double line lowest), high on paper, uniform in a missing tile;
    the railway symbol costs as much as paper (a road crosses it but does not run along it); soft4 (the overprint
    masks) a medium uniform cost, so a road is carried straight under the pencil"""
    c = ndi.binary_closing(ink4, structure=disk(4)) | ink4
    din = ndi.distance_transform_edt(c); dout = ndi.distance_transform_edt(~c)
    cost = np.where(c, 1.0 + 1.0 / (1.0 + din), 2.0 + 10.0 * np.clip(dout / 4.0, 0, 1)).astype(np.float32)
    if rail4 is not None: cost[rail4] = 12.0
    if soft4 is not None: cost[soft4] = 3.0
    cost[blank4] = 3.0
    return cost

def snap_segment(cost, P, Q, hw_min=45.0):
    """least-cost path from P to Q (4 m px, x, y) inside a corridor round the straight segment"""
    from skimage.graph import route_through_array
    P = np.asarray(P, float); Q = np.asarray(Q, float); L = math.hypot(*(Q - P))
    hw = max(hw_min, 0.15 * L)
    H, W = cost.shape
    x0 = int(max(0, min(P[0], Q[0]) - hw)); x1 = int(min(W, max(P[0], Q[0]) + hw + 1))
    y0 = int(max(0, min(P[1], Q[1]) - hw)); y1 = int(min(H, max(P[1], Q[1]) + hw + 1))
    sub = cost[y0:y1, x0:x1].copy()
    yy, xx = np.mgrid[y0:y1, x0:x1]
    if L > 0:
        u = (Q - P) / L; rx, ry = xx - P[0], yy - P[1]
        t = np.clip(rx * u[0] + ry * u[1], 0, L); dx = rx - t * u[0]; dy = ry - t * u[1]
        dseg = np.hypot(dx, dy)
    else: dseg = np.hypot(xx - P[0], yy - P[1])
    sub = sub + 0.04 * dseg
    sub[dseg > hw] = 1e6
    s = (int(np.clip(round(P[1]), y0, y1 - 1)) - y0, int(np.clip(round(P[0]), x0, x1 - 1)) - x0)
    e = (int(np.clip(round(Q[1]), y0, y1 - 1)) - y0, int(np.clip(round(Q[0]), x0, x1 - 1)) - x0)
    path, _ = route_through_array(sub, s, e, fully_connected=True, geometric=True)
    return np.array([(c + x0, r + y0) for r, c in path], float)

def snap_road(cost, wps, straight=False):
    if straight or len(wps) < 2: return np.asarray(wps, float)
    out = []
    for P, Q in zip(wps[:-1], wps[1:]):
        p = snap_segment(cost, P, Q)
        out.append(p if not out else p[1:])
    return np.vstack(out)

def smooth_px(p, eps=2.0, n=2):
    return chaikin(rdp(np.asarray(p, float), eps), n)

def px4_to_m(x, y):
    """4 m block px (x east, y south) -> DEM-lattice metres"""
    return BLOCK_PX[0] * 4.0 + (x + 0.5) * 4.0, OLD_ROWS * CELL - (BLOCK_PX[1] + y + 0.5) * 4.0

def cut_out(edges, mask, keep_short=2):
    """split edges at the boundary of mask and drop the pieces inside it"""
    out = []
    for e in edges:
        p = e[2]; m = sample(mask, p)
        if not m.any(): out.append(e); continue
        if m.all(): continue
        k = 0; n = len(p)
        while k < n:
            j = k
            while j + 1 < n and m[j + 1] == m[k]: j += 1
            if not m[k] or (j - k) < keep_short:
                a = e[0] if k == 0 else ('c', id(e), k); b = e[1] if j == n - 1 else ('c', id(e), j)
                q = p[max(0, k - 1) if m[k] else k:j + 1] if True else p[k:j + 1]
                if len(q) >= 2 and not m[k]: out.append([a, b, p[k:j + 1], dict(e[3])])
            k = j + 1
    return out

def renumber(nodes, edges):
    """give the string / tuple node ids from cut_out fresh integer ids with positions"""
    nid = max(k for k in nodes if isinstance(k, int)) + 1
    for e in edges:
        for s, pt in ((0, e[2][0]), (1, e[2][-1])):
            if not isinstance(e[s], (int, np.integer)):
                nodes[nid] = tuple(pt); e[s] = nid; nid += 1
    return edges

def wiggly(e, win=8):
    p = e[2]
    if len(p) < win + 1: return False
    seg = np.hypot(*np.diff(p, axis=0).T); s = np.concatenate([[0], np.cumsum(seg)])
    idx = np.searchsorted(s, s + win)
    ok = idx < len(p)
    if not ok.any(): return False
    ch = np.hypot(*(p[idx[ok]] - p[ok]).T) / win
    return float(np.median(ch)) < 0.8

def blob_streets(bu, nodes, min_area=10):
    """street spines of the 1941 villages: the skeleton of each built-up blob, spurs shorter than a quarter of the blob
    (or 70 m) pruned - a street village's blob is the band of houses either side of its street"""
    from skimage.morphology import skeletonize
    m = ndi.binary_closing(np.pad(bu, 4), structure=disk(2))[4:-4, 4:-4] | bu
    lab, n = ndi.label(m, structure=np.ones((3, 3)))
    out = []; nid = max(nodes) + 1 if nodes else 1
    for k, q in enumerate(ndi.find_objects(lab)):
        b = lab[q] == k + 1
        if b.sum() < min_area: continue
        ext = math.hypot(q[0].stop - q[0].start, q[1].stop - q[1].start)
        sm = ndi.binary_opening(b, structure=np.ones((2, 2))) | b if b.sum() > 40 else b
        nn, ee = skel_graph(skeletonize(np.pad(sm, 1))[1:-1, 1:-1])
        off = np.array([q[1].start, q[0].start], float)
        es = []
        for a, c, p in ee: es.append([('b', k, a), ('b', k, c), p + off, {'street': True, 'L': plen(p)}])
        # prune spurs iteratively
        lim = max(6.0, 0.22 * ext)
        for _ in range(6):
            deg = {}
            for e in es: deg[e[0]] = deg.get(e[0], 0) + 1; deg[e[1]] = deg.get(e[1], 0) + 1
            keep = [e for e in es if not (e[0] != e[1] and ((deg[e[0]] == 1 and deg[e[1]] >= 3) or (deg[e[1]] == 1 and deg[e[0]] >= 3)) and e[3]['L'] < lim)]
            if len(keep) == len(es): break
            es = merge_deg2({}, keep, lambda e1, e2: True)
            for e in es: e[3]['L'] = plen(e[2])
        es = [e for e in es if e[3]['L'] >= 3 or len(es) == 1]
        if not es and ee: es = [[('b', k, 0), ('b', k, 1), max(ee, key=lambda e: plen(e[2]))[2] + off, {'street': True}]]
        ids = {}
        for e in es:
            for s in (0, 1):
                if e[s] not in ids: ids[e[s]] = nid; nodes[nid] = tuple(e[2][0] if s == 0 else e[2][-1]); nid += 1
                e[s] = ids[e[s]]
            e[3]['L'] = plen(e[2]); out.append(e)
    return out

# ------------------------------------------------------------------ the whole run
def load_inputs(sheet_png, builtup_png, osm_path):
    rgb = np.asarray(Image.open(sheet_png).convert('RGB'))[BLOCK_PX[1]:BLOCK_PX[3], BLOCK_PX[0]:BLOCK_PX[2]]
    ink4 = ink_mask(rgb)
    V = grid_lines(ink4); Hh = grid_lines(ink4.T)
    g4 = remove_runs(ink4, V) | remove_runs(ink4.T, Hh).T
    blank4 = np.all(rgb == 230, -1)
    blank4 = ndi.binary_dilation(ndi.binary_opening(blank4, iterations=2), iterations=3)
    bu4 = (np.asarray(Image.open(builtup_png).convert('L'))[BLOCK_PX[1]:BLOCK_PX[3], BLOCK_PX[0]:BLOCK_PX[2]] > 0) if builtup_png and os.path.exists(builtup_png) else np.zeros(ink4.shape, bool)
    ink = pool(ink4 & ~g4, 0.5)
    rail, _ = railway_band(ink, osm_path)
    excl = exclude_mask()
    up = lambda m: np.repeat(np.repeat(m, F, 0), F, 1)
    cost = cost_raster(ink4 & ~g4, blank4, up(ndi.binary_erosion(rail)), up(excl))
    # inside the 1941 villages the house blocks are ink as well: there the road goes straight between its waypoints
    cost[ndi.binary_dilation(up(pool(bu4, 0.3)), structure=disk(6))] = 2.5
    return dict(ink=ink & ~excl, blank=pool(blank4, 0.5), bu=pool(bu4, 0.3), gridband=grid_band(V, Hh), rail=rail, excl=excl, cost=cost, bu4=bu4)

def auto_trace(I):
    """steps 5-8 on the 12 m grid: the line work as a graph of pieces outside the villages"""
    ink, bu = I['ink'], I['bu']
    vz = ndi.binary_dilation(bu, structure=disk(2))
    blocks, rmsol = solids(ink, vz)
    lab, cls, info = components(ink & ~rmsol & ~I['rail'])
    lines = cls[lab] == 1; dash = cls[lab] == 2
    link, ldeg = link_dashes(info, ink.shape)
    keepd = np.zeros(len(cls), bool)
    for k in ldeg: keepd[k] = True
    dash &= keepd[lab]
    cx = Ctx(dashd=ndi.binary_dilation(dash | link), lined=ndi.binary_dilation(lines), gridband=I['gridband'], blank=I['blank'], rail=I['rail'], excl=I['excl'], vz=vz)
    nodes, edges = build_graph(lines | dash | link, cx)
    edges = [e for e in edges if not (e[3]['grid'] >= 0.6 and e[3]['L'] >= 2)]
    edges = merge(nodes, edges, cx)
    edges = renumber(nodes, cut_out(edges, ndi.binary_dilation(bu, structure=disk(4))))
    edges = merge(nodes, edges, cx)
    edges = prune_spurs(nodes, edges, cx, 4)
    edges = [e for e in edges if not ((e[3]['L'] < 60 and wiggly(e)) or (e[3]['w'] >= 4.5 and e[3]['L'] < 25))]
    edges = merge(nodes, edges, cx)
    edges, _ = junk_filter(edges, cx)
    edges, _ = bridge(nodes, edges, cx, gap_blank=0)     # no crossing of the missing tiles here: the guided roads do that
    edges = merge(nodes, edges, cx)
    return nodes, edges, cx

def polyline_mask(polys, shape, width, scale=1.0):
    im = Image.new('L', shape[::-1], 0); d = ImageDraw.Draw(im)
    for p in polys:
        if len(p) >= 2: d.line([(x * scale, y * scale) for x, y in p], fill=255, width=width, joint='curve')
    return np.asarray(im) > 0

def runs_of(m):
    out = []; k = 0
    while k < len(m):
        j = k
        while j + 1 < len(m) and m[j + 1] == m[k]: j += 1
        out.append((k, j, bool(m[k]))); k = j + 1
    return out

def attach(p, net_pts, tree, reach):
    """extend the ends of polyline p (4 m px) to the nearest network point within reach"""
    p = list(map(tuple, p))
    if tree is None: return np.array(p)
    for at in (0, -1):
        d, i = tree.query(p[at])
        if 1.0 < d <= reach:
            if at == 0: p.insert(0, tuple(net_pts[i]))
            else: p.append(tuple(net_pts[i]))
    return np.array(p)

AUTO_MIN_M = 300.0   # a traced piece the guided roads miss is added when it is at least this long

def assemble(I, guided, auto_nodes, auto_edges, log=print):
    """G guided roads + T traced pieces they miss + V village streets -> [(cls, source, pts 4 m px)]"""
    out = []
    for cls, wps in guided:
        out.append((cls, 'sheet', snap_road(I['cost'], wps, straight=(cls == 'residential'))))
    log('guided roads: %d' % len(out))
    def dense(p, step=4.0):
        q = [p[0]]
        for a, b in zip(p[:-1], p[1:]):
            n = max(1, int(math.hypot(*(b - a)) / step)); q += [a + (b - a) * k / n for k in range(1, n + 1)]
        return np.array(q)
    def net():
        P = np.vstack([dense(np.asarray(p, float)) for _, _, p in out]) if out else np.zeros((0, 2))
        return P, (cKDTree(P) if len(P) else None)
    # T: traced pieces away from the guided roads
    P, T = net(); n_t = 0
    near = ndi.distance_transform_edt(~polyline_mask([p for _, _, p in out], (NB * F, NB * F), 3)) if out else None
    chains_ = chains(auto_nodes, classify(auto_nodes, [e for e in auto_edges]))
    for cls, p in chains_:
        q = dense(p * F + 1.0)
        far = near[np.clip(q[:, 1].astype(int), 0, NB * F - 1), np.clip(q[:, 0].astype(int), 0, NB * F - 1)] > 12   # > 48 m from a guided road
        for a, b, v in runs_of(far):
            L = (b - a) * 4.0
            if not v or L < AUTO_MIN_M: continue
            seg = q[max(0, a - 3):b + 4]
            if wiggly([0, 0, seg / F], win=25): continue
            # most of what the guided roads leave is lettering, ravine edges and village interiors: a piece is added only
            # when it closes a gap in the network (both ends on it) or is long and leaves it at one end
            d0 = T.query(seg[0])[0] if T is not None else 1e9; d1 = T.query(seg[-1])[0] if T is not None else 1e9
            if not ((d0 <= 25 and d1 <= 25) or (min(d0, d1) <= 25 and L >= 2 * AUTO_MIN_M)): continue
            seg = attach(seg, P, T, 40)
            out.append(('path' if cls == 'path' else 'track', 'sheet-auto', seg)); n_t += 1
    log('traced pieces added: %d' % n_t)
    # V: village streets
    P, T = net(); n_v = 0
    have = ndi.distance_transform_edt(~polyline_mask([p for _, _, p in out], (NB * F, NB * F), 3))
    vn = {}
    st = blob_streets(I['bu'], vn)
    for a, b, p, at in st:
        q = dense(p * F + 1.0)
        free = have[np.clip(q[:, 1].astype(int), 0, NB * F - 1), np.clip(q[:, 0].astype(int), 0, NB * F - 1)] > 9   # > 36 m from any road
        for a_, b_, v in runs_of(free):
            if not v or (b_ - a_) * 4.0 < 60.0: continue
            seg = attach(q[a_:b_ + 1], P, T, 30)
            out.append(('residential', 'village', seg)); n_v += 1
    log('village streets added: %d' % n_v)
    # hamlets still without a street: a lane along the long axis of the blob, joined to the nearest road within 250 m
    P, T = net(); lab, miss = village_check(I, out, log=lambda *a: None); n_h = 0
    for k in miss:
        yy, xx = np.nonzero(lab == k)
        c = np.array([xx.mean(), yy.mean()])
        ev, evec = np.linalg.eigh(np.cov(np.stack([xx, yy]).astype(float)))
        u = evec[:, 1]; half = max(8.0, 1.7 * math.sqrt(max(ev[1], 0)))
        seg = np.array([c - u * half, c + u * half])
        if T is not None:
            d0, i0 = T.query(seg[0]); d1, i1 = T.query(seg[1])
            if min(d0, d1) <= 62.5:
                seg = np.vstack([P[i0], seg]) if d0 <= d1 else np.vstack([seg, P[i1]])
        out.append(('residential', 'village', seg)); n_h += 1
    log('hamlet lanes added: %d' % n_h)
    return out

def village_check(I, roads, log=print):
    """every 1941 village (built-up blob >= 0.3 ha) must have a road or street through it"""
    lab, n = ndi.label(I['bu4'], structure=np.ones((3, 3)))
    m = polyline_mask([p for _, _, p in roads], I['bu4'].shape, 3)
    hit = np.unique(lab[m & (lab > 0)])
    sizes = ndi.sum(I['bu4'], lab, range(1, n + 1)) * 16.0
    miss = [k for k in range(1, n + 1) if sizes[k - 1] >= 3000 and k not in set(hit.tolist())]
    log('1941 villages: %d blobs >= 0.3 ha, %d without a street' % (int((sizes >= 3000).sum()), len(miss)))
    return lab, miss

def to_json(roads, eps=1.0):
    feats = []
    for cls, src, p in roads:
        q = smooth_px(np.asarray(p, float), eps, 2)
        pts = [[round(x, 1), round(y, 1)] for x, y in (px4_to_m(a, b) for a, b in q)]
        L = plen(np.array(pts))
        if L < 20: continue
        feats.append(dict(highway=cls, source=src, length_m=int(round(L)), pts=pts))
    return feats

# ------------------------------------------------------------------ c70 (5 Nov, user: "These roads look weird")
# The c68 output had pixel-stepped roads hugging one edge of the double line, skeleton squiggles as village streets,
# straight lines where the sheet draws nothing and near-miss junctions.  Now: waypoints are moved to the centre of the
# line work, the least-cost route favours the centre strongly, every route point is re-centred across the ink band,
# then simplified (Douglas-Peucker 6 m) and smoothed (Chaikin 3 passes); every road is checked for support on the
# sheet; village streets are the smoothed long-axis centre line of each 1941 village; road ends are snapped to the
# roads they meet (and trimmed where they overshoot).

def centre_cost(ink4, blank4, rail4=None, soft4=None, vil4=None):
    """4 m cost: on the line work 1 + 4 / (1 + depth) (the centre of a band cheapest), paper 3..13, railway 12,
    pencil masks 3, villages 2.5, missing tiles 3"""
    c = ndi.binary_closing(ink4, structure=disk(5)) | ink4
    din = ndi.distance_transform_edt(c); dout = ndi.distance_transform_edt(~c)
    cost = np.where(c, 1.0 + 4.0 / (1.0 + din), 3.0 + 10.0 * np.clip(dout / 4.0, 0, 1)).astype(np.float32)
    if rail4 is not None: cost[rail4] = 12.0
    if soft4 is not None: cost[soft4] = 3.0
    if vil4 is not None:
        # inside the villages the house blocks are solid ink: there only the thin line work (the road's two lines,
        # closed into a band) is cheap, blocks and paper cost 4
        blk = ndi.binary_dilation(ndi.binary_opening(ink4, structure=disk(3)), structure=disk(2))
        cv = np.where(c & ~blk, cost, 4.0).astype(np.float32)
        cost[vil4] = cv[vil4]
    cost[blank4] = 3.0
    return cost, c, din

def centre_point(P, band, din, r=10):
    """the deepest point of the ink band within r px of P (P unchanged when there is no band there)"""
    x, y = int(round(P[0])), int(round(P[1])); H, W = band.shape
    x0, x1, y0, y1 = max(0, x - r), min(W, x + r + 1), max(0, y - r), min(H, y + r + 1)
    sub = din[y0:y1, x0:x1]
    if sub.max() <= 0: return np.asarray(P, float)
    yy, xx = np.mgrid[y0:y1, x0:x1]
    sc = sub - 0.15 * np.hypot(xx - P[0], yy - P[1])
    k = np.unravel_index(np.argmax(sc), sc.shape)
    return np.array([xx[k], yy[k]], float) if sub[k] > 0 else np.asarray(P, float)

def resample(p, step):
    p = np.asarray(p, float)
    if len(p) < 2: return p
    seg = np.hypot(*np.diff(p, axis=0).T); s = np.concatenate([[0], np.cumsum(seg)])
    if s[-1] < 1e-6: return p[:1]
    t = np.linspace(0, s[-1], max(2, int(s[-1] / step) + 1))
    return np.stack([np.interp(t, s, p[:, 0]), np.interp(t, s, p[:, 1])], 1)

def recentre(p, band, maxw=18, reach=6, skip=None):
    """shift every point of a route across the road to the middle of the ink band it lies on (scan +-reach px
    along the normal); the offsets are median-filtered so the road does not jitter"""
    q = resample(p, 4.0)
    if len(q) < 3: return q
    T = np.gradient(q, axis=0); T /= np.maximum(np.hypot(T[:, 0], T[:, 1]), 1e-6)[:, None]
    N = np.stack([-T[:, 1], T[:, 0]], 1); H, W = band.shape
    off = np.zeros(len(q)); ok = np.zeros(len(q), bool)
    ts = np.arange(-reach - maxw // 2, reach + maxw // 2 + 1)
    for i, (P, n) in enumerate(zip(q, N)):
        xs = np.clip(np.round(P[0] + ts * n[0]).astype(int), 0, W - 1); ys = np.clip(np.round(P[1] + ts * n[1]).astype(int), 0, H - 1)
        m = band[ys, xs]
        best = None
        for a, b, v in runs_of(m):
            if not v or (b - a + 1) > maxw: continue
            c = (ts[a] + ts[b]) / 2.0
            if abs(c) <= reach and (best is None or abs(c) < abs(best)): best = c
        if skip is not None and skip[min(H - 1, max(0, int(round(P[1])))), min(W - 1, max(0, int(round(P[0]))))]:
            off[i] = 0.0; ok[i] = True; continue   # inside villages / under the pencil / in missing tiles: as routed
        if best is not None: off[i] = best; ok[i] = True
    # gaps (no band): interpolate the offset, then median filter
    if ok.any():
        idx = np.arange(len(q)); off = np.interp(idx, idx[ok], off[ok])
    k = 5; pad = np.pad(off, k, mode='edge'); off = np.array([np.median(pad[i:i + 2 * k + 1]) for i in range(len(off))])
    off[0] = off[-1] = 0.0 if False else off[0]
    return q + N * off[:, None]

def gsmooth(p, sigma=6.0):
    """Gaussian smoothing along the arc (sigma px), ends kept"""
    q = resample(p, 2.0)
    if len(q) < 5: return q
    s = sigma / 2.0
    pad = int(3 * s) + 1
    a = np.pad(q, ((pad, pad), (0, 0)), mode='reflect', reflect_type='odd')
    sm = np.stack([ndi.gaussian_filter1d(a[:, 0], s), ndi.gaussian_filter1d(a[:, 1], s)], 1)[pad:-pad]
    sm[0] = q[0]; sm[-1] = q[-1]
    return sm

def finish(p, dp=1.5, passes=3, sigma=6.0):
    """Gaussian smoothing along the arc (sigma px, 24 m), Douglas-Peucker (dp px = 6 m at 4 m/px), Chaikin"""
    q = gsmooth(p, sigma) if sigma else np.asarray(p, float)
    return chaikin(rdp(q, dp), passes)

def snap_guided(cost, band, din, wps, cls, skip=None):
    wps = [np.asarray(w, float) for w in wps]
    if cls == 'residential':
        return finish(resample(np.array(wps), 4.0), 1.5, 3)
    wc = [w if (skip is not None and skip[min(skip.shape[0] - 1, int(w[1])), min(skip.shape[1] - 1, int(w[0]))]) else centre_point(w, band, din) for w in wps]
    route = snap_road(cost, wc)
    return finish(recentre(route, band, skip=skip), 1.5, 3)

def support(p, ink12, zone12):
    """(fraction of the road on the sheet's line work, longest unsupported run m) - points in zone12 (villages,
    missing tiles, pencil masks, railway) do not count either way"""
    q = resample(p, 2.0); n_ = ink12.shape[0]
    if n_ == NB: q = q / F
    ix = np.clip(np.round(q[:, 0]).astype(int), 0, n_ - 1); iy = np.clip(np.round(q[:, 1]).astype(int), 0, n_ - 1)
    z = zone12[iy, ix]; on = ink12[iy, ix]
    m = ~z
    if not m.any(): return 1.0, 0.0
    frac = float(on[m].mean())
    worst = 0.0
    for a, b, v in runs_of(~on & m):
        if v: worst = max(worst, (b - a + 1) * 8.0)   # samples every 2 px = 8 m
    return frac, worst

# ---- village streets
def _longest_path(nodes, edges):
    import networkx as nx
    G = nx.Graph()
    for a, b, p in edges:
        L = plen(p)
        if a == b: continue
        if G.has_edge(a, b) and G[a][b]['w'] <= L: continue
        G.add_edge(a, b, w=L, p=p, a=a)
    if not G.number_of_edges(): return None, G
    best = None
    for comp in nx.connected_components(G):
        sg = G.subgraph(comp); s0 = next(iter(comp))
        d = nx.single_source_dijkstra_path_length(sg, s0, weight='w'); u = max(d, key=d.get)
        d2, path = nx.single_source_dijkstra(sg, u, weight='w'); v = max(d2, key=d2.get)
        if best is None or d2[v] > best[0]: best = (d2[v], path[v])
    pts = []
    for x, y in zip(best[1][:-1], best[1][1:]):
        e = G[x][y]; p = e['p'] if e['a'] == x else e['p'][::-1]
        pts.append(p if not pts else p[1:])
    return np.vstack(pts), G

def _extend(p, mask, far=200):
    """extend both ends along their end direction while inside mask (4 m px)"""
    p = list(map(np.asarray, p)); H, W = mask.shape
    for at_end in (False, True):
        q = np.array(p); d = end_dir(q, at_end, k=40)
        if not d.any(): continue
        P = q[-1] if at_end else q[0]; ext = []
        for t in range(2, far, 2):
            X = P + d * t; x, y = int(round(X[0])), int(round(X[1]))
            if not (0 <= x < W and 0 <= y < H) or not mask[y, x]: break
            ext.append(X)
        if ext:
            if at_end: p = p + ext
            else: p = ext[::-1] + p
    return np.array(p)

STREET_CLEAR = 15.0   # px (60 m): a village street closer than this to a sheet road is that road (the house rows flank it)

def village_streets_axis(bu4, roads, min_len_m=80.0, log=print):
    """the street(s) of every 1941 village: the house blocks of one village (merged within 60 m) are smoothed into
    its outline, the longest path through the outline's skeleton is the main street along the village (it follows the
    curve of the valley), extended to the ends of the village and smoothed; a second street only where the outline
    clearly branches (a branch >= 250 m and >= 40 % of the main street). Where a sheet road already runs along the
    village it is its street; only the parts > 30 m from the roads and >= 80 m long are added. Short villages get a
    lane of 80 m along their long axis. Ends within 150 m of a road are joined to it."""
    from skimage.morphology import skeletonize
    H, W = bu4.shape
    merged = ndi.binary_closing(np.pad(bu4, 20), structure=disk(15))[20:-20, 20:-20] | bu4
    lab, n = ndi.label(merged, structure=np.ones((3, 3)))
    rd = polyline_mask(roads, (H, W), 3)
    dist_rd = ndi.distance_transform_edt(~rd)
    rp = np.vstack([resample(p, 4.0) for p in roads]) if roads else np.zeros((0, 2)); TR = cKDTree(rp) if len(rp) else None
    out = []; n_v = 0
    for k, q in enumerate(ndi.find_objects(lab)):
        m = lab[q] == k + 1
        if m.sum() * 16.0 < 3000: continue
        y0, x0 = q[0].start, q[1].start
        sm = ndi.binary_fill_holes(ndi.binary_opening(np.pad(m, 6), structure=disk(3)))[6:-6, 6:-6]
        if sm.sum() < 0.3 * m.sum(): sm = m
        nn, ee = skel_graph(skeletonize(np.pad(sm, 1))[1:-1, 1:-1])
        cand = []
        main, G = _longest_path(nn, ee)
        yy, xx = np.nonzero(m)
        ev, evec = np.linalg.eigh(np.cov(np.stack([xx, yy]).astype(float)))
        span = 3.46 * math.sqrt(max(ev[1], 0)) * 4.0
        if main is None or plen(main) * 4.0 < 0.5 * span:
            u = evec[:, 1]; c = np.array([xx.mean(), yy.mean()]); half = max(min_len_m / 8.0, span / 8.0)
            main = np.array([c - u * half, c + u * half])
        else:
            main = _extend(rdp(main, 2.0), sm)
        cand.append(main)
        # cross lanes / second street: branches of the skeleton far from the main street
        if G is not None and G.number_of_edges() > 1 and plen(main) * 4.0 > 300:
            Tm = cKDTree(resample(main, 2.0))
            for a, b, p in ee:
                L = plen(p) * 4.0
                if L < max(250.0, 0.4 * plen(main) * 4.0): continue
                d = Tm.query(resample(p, 4.0))[0]
                if (d > 6).mean() > 0.7: cand.append(_extend(rdp(p, 2.0), sm))
        for c in cand:
            c = finish(resample(c + np.array([x0, y0], float), 4.0), 2.5, 3, sigma=24.0)
            # parts of the street away from the roads
            qq = resample(c, 4.0)
            far = dist_rd[np.clip(qq[:, 1].astype(int), 0, H - 1), np.clip(qq[:, 0].astype(int), 0, W - 1)] > STREET_CLEAR
            for a, b, v in runs_of(far):
                seg = qq[max(0, a - 2):b + 3] if v else None
                if seg is None or len(seg) < 2: continue
                if plen(seg) * 4.0 < min_len_m:
                    if not (a == 0 and b == len(qq) - 1): continue   # a short piece between roads: the roads serve it
                    seg = _lengthen(seg, min_len_m / 4.0)
                # join the ends to the nearest road within 150 m
                for at in (0, -1):
                    if TR is None: break
                    d_, i_ = TR.query(seg[at])
                    if 1.0 < d_ <= 37.5:
                        seg = np.vstack([rp[i_], seg]) if at == 0 else np.vstack([seg, rp[i_]])
                seg = finish(seg, 1.5, 2)
                # no hooks: a street whose ends are less than 70 % of its length apart (it curls round the blob) is
                # replaced by the straight lane between its ends
                Ls = plen(seg); ch = math.hypot(*(seg[-1] - seg[0]))
                if Ls > 0 and ch < 0.7 * Ls: seg = np.array([seg[0], seg[-1]]) if ch * 4.0 >= min_len_m else None
                if seg is None: continue
                out.append(seg); n_v += 1
    log('village streets: %d' % n_v)
    return out

def _lengthen(seg, L):
    c = seg.mean(0); d = seg[-1] - seg[0]; n = math.hypot(*d)
    if n < 1e-6: d = np.array([1.0, 0.0]); n = 1.0
    d = d / n; half = max(L, plen(seg)) / 2.0
    return np.array([c - d * half, c + d * half])

# ---- junctions
def _seg_intersect(P, Q, A, B):
    r = Q - P; s = B - A; den = r[0] * s[1] - r[1] * s[0]
    if abs(den) < 1e-9: return None
    t = ((A[0] - P[0]) * s[1] - (A[1] - P[1]) * s[0]) / den; u = ((A[0] - P[0]) * r[1] - (A[1] - P[1]) * r[0]) / den
    return (t, u) if 0 <= t <= 1 and 0 <= u <= 1 else None

def snap_ends(roads, reach=40.0, log=print):
    """roads: [(cls, src, pts metres)]. A road end that overshoots another road by < reach is cut at the crossing;
    an end that stops short of a road within reach is extended to its nearest point (shared point)."""
    arr = [np.asarray(p, float) for _, _, p in roads]
    segs = []; own = []
    for i, p in enumerate(arr):
        for j in range(len(p) - 1): segs.append((p[j], p[j + 1])); own.append(i)
    mids = np.array([(a + b) / 2 for a, b in segs]); T = cKDTree(mids); own = np.array(own)
    n_cut = n_ext = 0
    for i, p in enumerate(arr):
        for at_end in (False, True):
            q = p[::-1] if at_end else p         # q[0] is the end being handled
            if len(q) < 2: continue
            # overshoot: walk in from the end up to reach, look for a crossing with another road
            walked = 0.0; cut = None
            for j in range(len(q) - 1):
                A, B = q[j], q[j + 1]; L = math.hypot(*(B - A))
                if walked > reach: break
                for k in T.query_ball_point((A + B) / 2, L / 2 + 60):
                    if own[k] == i: continue
                    r = _seg_intersect(A, B, *segs[k])
                    if r is not None and walked + r[0] * L <= reach and (walked + r[0] * L) > 0.5:
                        X = A + (B - A) * r[0]
                        if cut is None or walked + r[0] * L < cut[0]: cut = (walked + r[0] * L, j, X)
                walked += L
            if cut is not None and cut[0] < 0.5 * plen(q):
                _, j, X = cut; q = np.vstack([X, q[j + 1:]]); n_cut += 1
            else:
                # near miss: nearest point on another road
                E = q[0]; best = None
                for k in T.query_ball_point(E, reach + 60):
                    if own[k] == i: continue
                    A, B = segs[k]; AB = B - A; t = np.clip(((E - A) @ AB) / max(AB @ AB, 1e-9), 0, 1); X = A + AB * t
                    d = math.hypot(*(X - E))
                    if d <= reach and (best is None or d < best[0]): best = (d, X)
                if best is not None and best[0] > 0.5:
                    # do not extend backwards over the road itself
                    if np.dot(best[1] - E, q[0] - q[min(3, len(q) - 1)]) > -0.3 * best[0] * math.hypot(*(q[0] - q[min(3, len(q) - 1)])):
                        q = np.vstack([best[1], q]); n_ext += 1
            p = q[::-1] if at_end else q
        arr[i] = p
    log('junctions: %d overshoots cut, %d ends joined' % (n_cut, n_ext))
    return [(c, s, a) for (c, s, _), a in zip(roads, arr)]

SIGMA = {'secondary': 18.0, 'track': 10.0, 'path': 8.0}   # px: along-arc smoothing of the routed roads

def snap_corridor(cost, wps, hw=32.0):
    """least-cost route from the first to the last waypoint inside a corridor of hw px round the waypoint polyline
    (the interior waypoints shape the corridor only, so a waypoint a few px off the line leaves no spike)"""
    from skimage.graph import route_through_array
    W_ = np.asarray(wps, float); H, W = cost.shape
    x0 = int(max(0, W_[:, 0].min() - hw - 2)); x1 = int(min(W, W_[:, 0].max() + hw + 3))
    y0 = int(max(0, W_[:, 1].min() - hw - 2)); y1 = int(min(H, W_[:, 1].max() + hw + 3))
    im = Image.new('F', (x1 - x0, y1 - y0), 0.0)
    m = Image.new('L', (x1 - x0, y1 - y0), 0); ImageDraw.Draw(m).line([(x - x0, y - y0) for x, y in W_], fill=255, width=1)
    dseg = ndi.distance_transform_edt(np.asarray(m) == 0)
    sub = cost[y0:y1, x0:x1] + 0.04 * dseg
    sub[dseg > hw] = 1e6
    cl = lambda P: (int(np.clip(round(P[1]), y0, y1 - 1)) - y0, int(np.clip(round(P[0]), x0, x1 - 1)) - x0)
    path, _ = route_through_array(sub, cl(W_[0]), cl(W_[-1]), fully_connected=True, geometric=True)
    return np.array([(c + x0, r + y0) for r, c in path], float)

def snap_guided(cost, band, din, wps, cls, skip=None, straight=False):
    wps = [np.asarray(w, float) for w in wps]
    if cls == 'residential' or straight:
        return finish(resample(np.array(wps), 4.0), 1.5, 3)
    ins = lambda w: skip is not None and skip[min(skip.shape[0] - 1, max(0, int(w[1]))), min(skip.shape[1] - 1, max(0, int(w[0])))]
    wc = list(wps)
    for k in (0, -1):
        if not ins(wc[k]): wc[k] = centre_point(wc[k], band, din, r=6)
    route = snap_corridor(cost, wc)
    return finish(recentre(route, band, skip=skip), 1.5, 3, sigma=SIGMA.get(cls, 8.0))

def village_zone(bu4):
    """the 1941 villages, house blocks +40 m, merged (72 m) and filled: roads are routed straight here"""
    m = ndi.binary_dilation(bu4, structure=disk(10))
    m = ndi.binary_closing(np.pad(m, 30), structure=disk(18))[30:-30, 30:-30] | m
    return ndi.binary_fill_holes(m)

# ------------------------------------------------------------------ c71 (5 Nov, user: "they have to be exact like they are
# drawn on map, and not some guesses ... connections are just ending ... the road near the railway suddenly changes sides")
# Digitise, don't infer.  Every road is a list of waypoints read off the sheet tile by tile (1 km tiles viewed at 1.5-4x,
# a waypoint at least every ~600 m and at every bend / junction).  Between two waypoints the road follows the DRAWN LINE:
# the centre line (skeleton) of the sheet's line work, the double line closed into one band first, found by a least-cost
# path restricted to a 40 m corridor round the waypoint polyline.  The railway symbol is impassable except where a road
# is marked as crossing it ('x' flag on the waypoint pair), so a road beside the railway cannot change sides.  Gaps in
# the drawn line (lettering, spot heights, ravine symbols, pencil) are crossed in the line's direction (paper is dear but
# passable inside the corridor).  The only smoothing is a 12 m Gaussian along the line against the 12 m scan staircase
# (deviation from the drawn centre line reported, <= 2 m), Douglas-Peucker 1 m, a vertex at least every 20 m.  Road ends
# lying within 30 m of another road are moved onto it and the junction point is inserted into that road (shared vertex).

def exact_cost(ink4, blank4, rail4, excl4, bu4):
    """4 m cost: 1 on the skeleton of the line work (double lines closed into one band, 8 m closing), 2.5 elsewhere
    on the ink, paper 8; railway symbol 500 (impassable in practice); inside the 1941 villages the solid house blocks 12
    (the streets are the lines / light lanes between them); pencil masks and missing tiles 6"""
    from skimage.morphology import skeletonize
    c = ndi.binary_closing(ink4, structure=disk(2)) | ink4
    blk = ndi.binary_opening(ink4, structure=disk(3))
    # long thin solids are filled road bands (improved roads drawn filled through the villages), not house blocks
    lab, n = ndi.label(blk, structure=np.ones((3, 3)))
    if n:
        sk0 = skeletonize(blk)
        L = ndi.sum(sk0, lab, range(1, n + 1)); A = ndi.sum(blk, lab, range(1, n + 1))
        road_like = np.zeros(n + 1, bool); road_like[1:] = (L >= 25) & (A / np.maximum(L, 1) <= 9)
        blk &= ~road_like[lab]
    vz = village_zone(bu4)
    lines = c & ~(blk & vz)
    sk = skeletonize(lines)
    cost = np.full(ink4.shape, 8.0, np.float32)
    cost[lines] = 2.5; cost[ndi.binary_dilation(sk)] = 1.6; cost[sk] = 1.0
    cost[blk & vz] = 12.0
    # inside the villages the streets are the light lanes between the house rows: paper (raw ink, unclosed) there is
    # cheap, and cheapest on the lane's centre line
    lane = vz & ~ink4
    dl = ndi.distance_transform_edt(lane)
    lane_c = vz & (dl >= 1) & (dl <= 6)
    cost[lane] = 2.4
    cost[lane_c] = np.minimum(cost[lane_c], (2.2 - 0.15 * np.clip(dl[lane_c], 0, 6)).astype(np.float32))
    cost[excl4] = 6.0; cost[blank4] = 6.0
    cost[rail4] = 500.0
    return cost, sk

def route_corridor(cost, wps, hw=10.0):
    from skimage.graph import route_through_array
    W_ = np.asarray(wps, float); H, W = cost.shape
    x0 = int(max(0, W_[:, 0].min() - hw - 2)); x1 = int(min(W, W_[:, 0].max() + hw + 3))
    y0 = int(max(0, W_[:, 1].min() - hw - 2)); y1 = int(min(H, W_[:, 1].max() + hw + 3))
    m = Image.new('L', (x1 - x0, y1 - y0), 0); ImageDraw.Draw(m).line([(x - x0, y - y0) for x, y in W_], fill=255, width=1)
    dseg = ndi.distance_transform_edt(np.asarray(m) == 0)
    sub = cost[y0:y1, x0:x1] + 0.02 * dseg
    sub = np.where(dseg > hw, 1e6, sub)
    cl = lambda P: (int(np.clip(round(P[1]), y0, y1 - 1)) - y0, int(np.clip(round(P[0]), x0, x1 - 1)) - x0)
    path, _ = route_through_array(sub, cl(W_[0]), cl(W_[-1]), fully_connected=True, geometric=True)
    return np.array([(c + x0, r + y0) for r, c in path], float)

def snap_wp(P, sk, r=8):
    """a waypoint onto the nearest skeleton pixel within r px (else unchanged)"""
    x, y = int(round(P[0])), int(round(P[1])); H, W = sk.shape
    x0, x1, y0, y1 = max(0, x - r), min(W, x + r + 1), max(0, y - r), min(H, y + r + 1)
    yy, xx = np.nonzero(sk[y0:y1, x0:x1])
    if not len(yy): return np.asarray(P, float)
    d = np.hypot(xx + x0 - P[0], yy + y0 - P[1]); k = int(np.argmin(d))
    return np.array([xx[k] + x0, yy[k] + y0], float) if d[k] <= r else np.asarray(P, float)

STREET_COST = [None]   # set by run72: street_cost()

def digitise(cost, sk, road, rail4=None, ink4=None):
    """one road: {'c': class, 'wp': [(x, y) | (x, y, 'x')...]} -> polyline (4 m px), max deviation px"""
    wps = road['wp']; pts = [np.array(w[:2], float) for w in wps]
    if not (road['c'] == 'residential' and not road.get('on_line')): pts = [snap_wp(p, sk) for p in pts]
    out = []
    for k in range(len(pts) - 1):
        P, Q = pts[k], pts[k + 1]
        cross = len(wps[k + 1]) > 2 and wps[k + 1][2] == 'x'
        if road.get('straight') or (len(wps[k + 1]) > 2 and wps[k + 1][2] == 's'):
            seg = np.array([P, Q])
        else:
            cst = cost
            if road['c'] == 'residential' and STREET_COST[0] is not None and not road.get('on_line'): cst = STREET_COST[0]
            if cross and rail4 is not None:
                cst = cost.copy(); cst[rail4] = 3.0
            seg = route_corridor(cst, [P, Q], hw=road.get('hw', 10.0))
        out.append(seg if not out else seg[1:])
    raw = np.vstack(out)
    if road['c'] == 'secondary' and ink4 is not None: raw = centre_double(raw, ink4, rail4)
    elif road['c'] == 'residential' and not road.get('on_line'): pass   # lane centre already
    else: raw = lock_to_skeleton(raw, sk)
    sm = gsmooth(raw, 2.0)
    q = resample(raw, 1.0); dev = float(cKDTree(q).query(resample(sm, 2.0))[0].max()) if len(q) > 2 else 0.0
    p = rdp(sm, 0.25)
    return densify(p, 5.0), dev

def densify(p, step):
    out = [p[0]]
    for a, b in zip(p[:-1], p[1:]):
        n = int(math.ceil(math.hypot(*(b - a)) / step))
        for k in range(1, n + 1): out.append(a + (b - a) * k / n)
    return np.array(out)

def share_junctions(roads, reach=26.0, log=print):
    """roads: list of dicts with 'px' (4 m px arrays). An end within reach px of another road (not itself) is moved to
    the nearest point on it and that point is inserted into the other road as a vertex (shared junction vertex)."""
    n_j = 0
    for i, r in enumerate(roads):
        for at in (0, -1):
            E = r['px'][at]; best = None
            for j, o in enumerate(roads):
                if j == i: continue
                p = o['px']
                A, B = p[:-1], p[1:]; AB = B - A; L2 = np.maximum((AB ** 2).sum(1), 1e-9)
                t = np.clip(((E - A) * AB).sum(1) / L2, 0, 1); X = A + AB * t[:, None]
                d = np.hypot(*(X - E).T); k = int(np.argmin(d))
                if d[k] <= reach and (best is None or d[k] < best[0]): best = (d[k], j, k, X[k], t[k])
            if best is None: continue
            d, j, k, X, t = best
            o = roads[j]['px']
            if t <= 1e-6: X = o[k]
            elif t >= 1 - 1e-6: X = o[k + 1]
            else: roads[j]['px'] = np.vstack([o[:k + 1], X[None], o[k + 1:]])
            rp = r['px'].copy(); rp[at] = X
            # if moved backward over the road itself, that is fine: the end vertex IS the junction
            r['px'] = rp; n_j += 1
    log('shared junction vertices: %d' % n_j)
    return roads

def dangling(roads, bu4, blank4, edge=6, reach=1.0):
    """ends not on another road, not in / at a 1941 village (40 m), not at the block edge, not at a blank patch"""
    near_v = ndi.binary_dilation(bu4, structure=disk(10)); near_b = ndi.binary_dilation(blank4, structure=disk(6))
    H, W = bu4.shape; out = []
    for i, r in enumerate(roads):
        for at in (0, -1):
            E = r['px'][at]; x, y = int(round(E[0])), int(round(E[1]))
            if x < edge or y < edge or x >= W - edge or y >= H - edge: continue
            if near_v[min(H - 1, max(0, y)), min(W - 1, max(0, x))] or near_b[min(H - 1, max(0, y)), min(W - 1, max(0, x))]: continue
            on = False
            for j, o in enumerate(roads):
                if j == i: continue
                if np.hypot(*(o['px'] - E).T).min() <= reach: on = True; break
            if not on: out.append((r.get('name', str(i)), 'start' if at == 0 else 'end', (x, y)))
    return out

def ink_dark(a):
    """routing ink (c71): every dark print, whatever its tint - on some sheet tiles the road black is warm
    (r - b ~ 40, rgb 48 34 8), which the colour test of ink_mask dropped; the brown contours are much lighter
    (g ~ 140-170 on paper ~ 210) and stay out by darkness; the pencil (blue) stays out by hue"""
    a = a.astype(np.int16)
    g = a.mean(-1); r, b = a[..., 0], a[..., 2]
    paper = (g > 160).astype(np.float32); g8 = g[::8, ::8].astype(np.float32); p8 = paper[::8, ::8]
    bg = ndi.uniform_filter(g8 * p8, 9) / np.maximum(ndi.uniform_filter(p8, 9), 1e-3)
    bg = np.where(ndi.uniform_filter(p8, 9) > 0.05, bg, 205.0)
    bg = np.repeat(np.repeat(bg, 8, 0), 8, 1)[:g.shape[0], :g.shape[1]]
    red = (r - (a[..., 1] + b) / 2) > 45
    return (g < np.minimum(0.55 * bg, 118)) & ((b - r) < 10) & ~red

def centre_double(p, ink4, rail4, lo=3, hi=16, reach=14, k=7):
    """a double-line road (main road: two lines 15-60 m apart) routed along one of its lines is moved to the middle:
    at each point the ink runs along the normal (+- reach px) are found and the pair of runs nearest to the point whose
    spacing is lo..hi px with paper between is taken; the offsets are median-filtered (k samples either side)"""
    q = resample(p, 4.0)
    if len(q) < 3: return np.asarray(p, float)
    T = np.gradient(q, axis=0); T /= np.maximum(np.hypot(T[:, 0], T[:, 1]), 1e-6)[:, None]
    N = np.stack([-T[:, 1], T[:, 0]], 1); H, W = ink4.shape
    ts = np.arange(-reach, reach + 1)
    off = np.full(len(q), np.nan)
    m_ = ink4 & ~rail4
    for i, (P, n) in enumerate(zip(q, N)):
        xs = np.clip(np.round(P[0] + ts * n[0]).astype(int), 0, W - 1); ys = np.clip(np.round(P[1] + ts * n[1]).astype(int), 0, H - 1)
        runs = [((ts[a] + ts[b]) / 2.0, b - a + 1) for a, b, v in runs_of(m_[ys, xs]) if v and b - a + 1 <= 5]
        best = None
        for x in range(len(runs)):
            for y in range(x + 1, len(runs)):
                c1, c2 = runs[x][0], runs[y][0]; sp = c2 - c1
                if lo <= sp <= hi and c1 <= 1.5 and c2 >= -1.5:      # the point lies on / between the pair
                    mid = (c1 + c2) / 2.0
                    if best is None or abs(mid) < abs(best): best = mid
        if best is not None: off[i] = best
    ok = ~np.isnan(off)
    if ok.sum() < 3: return np.asarray(p, float)
    idx = np.arange(len(q)); off = np.interp(idx, idx[ok], off[ok])
    pad = np.pad(off, k, mode='edge'); off = np.array([np.median(pad[i:i + 2 * k + 1]) for i in range(len(off))])
    return q + N * off[:, None]

def lock_to_skeleton(p, sk, r=4, k=4):
    """every routed point onto the centre line of the drawn line it lies on: the nearest skeleton pixel within r px
    (offsets median-filtered over +-k samples, so a crossing line does not pull single points)"""
    q = resample(p, 2.0)
    ys, xs = np.nonzero(sk)
    if not len(xs): return q
    T = cKDTree(np.stack([xs, ys], 1).astype(float))
    d, i = T.query(q, distance_upper_bound=r)
    off = np.zeros_like(q); ok = np.isfinite(d)
    off[ok] = np.stack([xs[i[ok]], ys[i[ok]]], 1) - q[ok]
    pad = np.pad(off, ((k, k), (0, 0)), mode='edge')
    med = np.stack([np.median(pad[j:j + 2 * k + 1], 0) for j in range(len(q))])
    out = q + med; out[0] = q[0] + off[0]; out[-1] = q[-1] + off[-1]
    return out

def village_lanes(ink4, bu4, roads_px, min_len=25, max_half=5, log=print):
    """the streets the sheet draws inside the 1941 villages: the light lanes between the house-block rows.  The paper
    inside the village zone is thinned to its medial axis; a lane is kept where the paper corridor is at most
    2 * max_half px wide (40 m) with house blocks on BOTH sides, it is >= min_len px (100 m) long, nearly straight
    (chord >= 0.92 of the length per 100 m piece) and more than 6 px from a sheet road (the road is the street there)."""
    from skimage.morphology import skeletonize
    vz = village_zone(bu4)
    blk = ndi.binary_opening(ink4, structure=disk(2)) & vz
    paper = vz & ~ndi.binary_dilation(ink4, structure=disk(1))
    dt = ndi.distance_transform_edt(paper)
    sk = skeletonize(paper) & (dt <= max_half) & (dt >= 1.5)
    # blocks on both sides: within max_half + 3 px of the axis there must be house-block ink across it
    near_blk = ndi.binary_dilation(blk, structure=disk(max_half + 3))
    sk &= near_blk
    rm = ndi.distance_transform_edt(~polyline_mask(roads_px, ink4.shape, 1)) <= 6
    sk &= ~rm
    nodes, edges = skel_graph(sk)
    out = []
    for a, b, p in edges:
        if plen(p) < min_len: continue
        q = rdp(p, 1.5)
        # split at sharp bends, keep straight pieces
        pieces = [[q[0]]]
        for k in range(1, len(q) - 1):
            v1 = q[k] - q[k - 1]; v2 = q[k + 1] - q[k]
            c = float(v1 @ v2) / max(1e-6, math.hypot(*v1) * math.hypot(*v2))
            pieces[-1].append(q[k])
            if c < 0.8: pieces.append([q[k]])
        pieces[-1].append(q[-1])
        for pc in pieces:
            pc = np.array(pc)
            if plen(pc) >= min_len and math.hypot(*(pc[-1] - pc[0])) >= 0.92 * plen(pc): out.append(pc)
    log('village lanes (drawn gaps between house rows): %d' % len(out))
    return out

# ------------------------------------------------------------------ c71 digitised network
# Every road / track / path / street of the sheet inside the block, read tile by tile (1 km tiles at 1.5-4x; the
# railway road from an unrolled strip along the line), as waypoints in 4 m block px (x east, y south from the block's
# NW corner).  A third element 's' on a waypoint = straight step into it (lettering / blank-patch crossing).
# 'hw' = corridor half-width px for the route between waypoints (default 10 = 40 m).
# c72 (5 Nov): village streets ('residential') for every 1941 village of the cleaned builtup_1941.png, read village by
# village (the light lane between two house rows, or the open side of a single row), routed along the lane centre
# (street_cost), ends joined to the roads they meet; ends fixed for r24 r28 r32 r43 r56 r70; tracks c01, d01 added.
DIGITISED = [
    dict(name='r04', c='track', wp=[(150, 500), (281, 505), (356, 531), (437, 552), (530, 552), (625, 546), (700, 548), (780, 525), (870, 495), (960, 470)]),
    dict(name='r05', c='track', wp=[(437, 552), (487, 500), (519, 450), (525, 400)]),
    dict(name='r06', c='track', wp=[(640, 778), (700, 760), (820, 745), (1024, 742)]),
    dict(name='r07', c='path', wp=[(295, 858), (328, 912), (360, 960), (383, 1000), (410, 1040), (437, 1090), (448, 1150), (453, 1200), (458, 1262)]),
    dict(name='r08', c='path', wp=[(832, 791), (822, 850), (815, 900), (800, 960), (795, 1000), (792, 1050), (790, 1100), (775, 1150), (765, 1190), (762, 1215)]),
    dict(name='r09', c='secondary', wp=[(458, 1262), (520, 1320), (580, 1362), (640, 1405), (700, 1475), (760, 1550), (820, 1620), (870, 1690), (900, 1765)]),
    dict(name='r10', c='track', wp=[(762, 1215), (790, 1210), (830, 1204), (880, 1203), (930, 1212), (968, 1232)]),
    dict(name='r11', c='secondary', wp=[(877, 1762), (860, 1800), (820, 1850), (800, 1900), (760, 1960), (700, 2100), (640, 2220), (580, 2330), (550, 2400), (530, 2500), (510, 2600), (490, 2700), (470, 2800), (440, 2900), (410, 3000), (380, 3100), (340, 3180), (290, 3260), (240, 3340), (195, 3430), (150, 3530), (100, 3640), (60, 3712)]),
    dict(name='r12', c='track', wp=[(960, 470), (1060, 400), (1120, 370), (1160, 300), (1175, 210), (1205, 140), (1290, 112)]),
    dict(name='r13', c='track', wp=[(1170, 762), (1215, 805), (1260, 850), (1310, 900), (1357, 950), (1400, 990), (1460, 1050), (1520, 1132)]),
    dict(name='r14', c='track', wp=[(968, 1235), (1200, 1195), (1500, 1135), (1700, 1090), (1920, 1050), (2010, 1045)]),
    dict(name='r15', c='path', wp=[(1625, 1105), (1700, 1205), (1780, 1300), (1850, 1390), (1910, 1460)]),
    dict(name='r16', c='secondary', wp=[(1800, 0), (1950, 60), (2100, 140), (2180, 205), (2280, 280), (2330, 320), (2450, 370), (2600, 440), (2740, 500), (2800, 545), (2870, 600), (2960, 650), (3100, 740), (3300, 850), (3450, 910), (3600, 985), (3700, 1035), (3782, 1132), (3852, 1200), (3925, 1270), (3990, 1330), (4050, 1385), (4107, 1435), (4150, 1475), (4185, 1500)]),
    dict(name='r17', c='track', wp=[(2392, 370), (2345, 485), (2300, 595), (2265, 655), (2230, 710), (2200, 790), (2160, 830), (2070, 930), (2040, 975, 's'), (2013, 1045, 's')]),
    dict(name='r18', c='track', wp=[(2280, 0), (2276, 270)]),
    dict(name='r19', c='secondary', wp=[(2960, 650), (2900, 760), (2850, 850), (2800, 930), (2760, 980), (2690, 1060), (2590, 1160), (2490, 1260), (2390, 1360), (2290, 1460), (2200, 1540), (2100, 1650), (2000, 1780), (1900, 1830), (1700, 1855), (1550, 1870), (1400, 1880), (1250, 1890), (1080, 1850), (900, 1765)]),
    dict(name='r20', c='secondary', wp=[(3050, 600), (3200, 520), (3300, 470), (3420, 420), (3560, 330), (3650, 260), (3700, 230)]),
    dict(name='r21', c='track', wp=[(3060, 615), (3130, 700), (3170, 755), (3185, 790)]),
    dict(name='r22', c='track', wp=[(2940, 388), (3000, 382), (3060, 372), (3093, 352), (3105, 300), (3120, 265), (3153, 242)]),
    dict(name='r23', c='track', wp=[(3160, 245), (3120, 140), (3085, 0)]),
    dict(name='r24', c='path', wp=[(3100, 25), (3230, 60), (3330, 60), (3420, 35), (3445, 45)]),
    dict(name='r25', c='track', wp=[(3640, 150), (3750, 175), (3850, 200), (3950, 222), (4040, 245), (4115, 268), (4175, 335), (4230, 390), (4300, 460)]),
    dict(name='r26', c='track', wp=[(4300, 460), (4440, 482), (4530, 492)]),
    dict(name='r27', c='track', wp=[(4555, 0), (4560, 40), (4575, 120), (4575, 180), (4567, 250), (4548, 320), (4535, 390), (4527, 450), (4530, 490), (4537, 580)]),
    dict(name='r28', c='track', wp=[(3955, 815), (3935, 870), (3897, 960), (3863, 1040), (3838, 1100), (3828, 1128), (3818, 1166)]),
    dict(name='r29', c='secondary', wp=[(2190, 1552), (2700, 1813)]),
    dict(name='r30', c='track', wp=[(2745, 1062), (2800, 1090), (2900, 1150), (3000, 1215), (3150, 1310), (3300, 1395), (3420, 1440), (3560, 1490), (3700, 1560), (3850, 1690)]),
    dict(name='r31', c='secondary', wp=[(2950, 1790), (3280, 1935)]),
    dict(name='r32', c='path', wp=[(3000, 1800), (2965, 1900), (2942, 1973)]),
    dict(name='r33', c='secondary', wp=[(3150, 2100), (3150, 2330)]),
    dict(name='r34', c='path', wp=[(3150, 2330), (3350, 2180), (3460, 2210)]),
    dict(name='r35', c='path', wp=[(3295, 1955), (3380, 2010), (3460, 2100), (3490, 2130)]),
    dict(name='r36', c='residential', wp=[(3850, 1690), (4000, 1650), (4120, 1610), (4300, 1585), (4450, 1555), (4608, 1525)]),
    dict(name='r37', c='residential', wp=[(4300, 1585), (4310, 1700), (4330, 1820), (4345, 1960)]),
    dict(name='r38', c='residential', wp=[(4120, 1610), (4200, 1470), (4300, 1330), (4400, 1200)]),
    dict(name='r39', c='track', wp=[(3900, 1700), (3820, 1800), (3760, 1880), (3720, 1950), (3690, 2050), (3660, 2150), (3600, 2200)]),
    dict(name='r40', c='residential', wp=[(420, 2620), (400, 2720), (390, 2816)]),
    dict(name='r43', c='track', wp=[(2080, 2830, 's'), (2100, 2800), (2200, 2700), (2310, 2595)]),
    dict(name='r44', c='track', wp=[(2310, 2595), (2380, 2655), (2440, 2710)]),
    dict(name='r46', c='secondary', wp=[(4560, 1530), (4540, 1700), (4530, 1900), (4530, 2100), (4520, 2300), (4500, 2440), (4460, 2650), (4420, 2816), (4400, 2950), (4370, 3100), (4330, 3230), (4300, 3350), (4270, 3450), (4220, 3550), (4170, 3640), (4140, 3712)]),
    dict(name='r47', c='path', wp=[(4290, 1990), (4350, 2050), (4420, 2100)]),
    dict(name='r48', c='track', wp=[(300, 3300), (350, 3230), (410, 3195), (470, 3210), (560, 3250), (690, 3300)]),
    dict(name='r49', c='secondary', wp=[(290, 3320), (340, 3370), (450, 3460), (560, 3560), (650, 3640), (730, 3712), (800, 3770), (900, 3850), (950, 3885)]),
    dict(name='r50', c='track', wp=[(620, 2880), (700, 2950), (800, 2980), (900, 3000), (1000, 3010), (1100, 3020), (1200, 3015), (1300, 3005), (1420, 3080), (1520, 3160), (1610, 3225), (1595, 3280), (1650, 3350), (1730, 3395)]),
    dict(name='r51', c='track', wp=[(914, 2995), (960, 3045), (1010, 3095), (1056, 3127), (1120, 3200), (1160, 3250), (1208, 3300), (1260, 3312), (1350, 3340), (1420, 3410), (1480, 3480), (1520, 3530)]),
    dict(name='r52', c='path', wp=[(955, 2700), (965, 2800), (975, 2900), (985, 2995, 's')]),
    dict(name='r53', c='secondary', wp=[(1230, 3712), (1350, 3640), (1500, 3530), (1650, 3420), (1820, 3310), (1900, 3260), (2000, 3200), (2132, 3106)]),
    dict(name='r54', c='path', wp=[(955, 2772), (1050, 2800), (1150, 2815), (1262, 2830)]),
    dict(name='r55', c='path', wp=[(1000, 3420), (1100, 3455), (1200, 3485), (1300, 3515)]),
    dict(name='r56', c='track', wp=[(2172, 3330), (2250, 3318, 's'), (2320, 3335), (2500, 3380), (2700, 3425), (2900, 3470), (2990, 3465)]),
    dict(name='r57', c='track', wp=[(2195, 2870), (2205, 3000), (2210, 3200), (2212, 3400), (2215, 3600), (2218, 3712)]),
    dict(name='r58', c='track', wp=[(2830, 2880), (2900, 3000), (2960, 3150), (2990, 3290), (2990, 3465)]),
    dict(name='r59', c='path', wp=[(3000, 3190), (3100, 3220), (3250, 3250), (3400, 3280), (3550, 3295), (3712, 3300), (3850, 3320), (4000, 3333)]),
    dict(name='r61', c='track', wp=[(3080, 4305), (3195, 4140), (3315, 4000), (3362, 3956), (3460, 3845), (3530, 3745), (3570, 3702), (3620, 3645), (3670, 3585), (3720, 3530), (3760, 3495), (3830, 3440), (3900, 3390), (3960, 3360), (4000, 3335), (4100, 3310), (4200, 3290), (4330, 3240)], hw=5.0),
    dict(name='r62', c='path', wp=[(3600, 2860), (3700, 2870), (3800, 2890), (3950, 2915)]),
    dict(name='r63', c='secondary', wp=[(145, 4340), (200, 4320), (370, 4315), (500, 4225), (600, 4150), (700, 4065), (800, 3975), (950, 3885), (1100, 3790), (1230, 3712)]),
    dict(name='r64', c='track', wp=[(0, 4430), (145, 4340)]),
    dict(name='r65', c='track', wp=[(0, 4255), (145, 4340)]),
    dict(name='r66', c='path', wp=[(400, 3710), (370, 3800), (345, 3900), (320, 4010)]),
    dict(name='r67', c='track', wp=[(370, 4312), (300, 4380), (270, 4440), (240, 4500), (200, 4560), (180, 4608)]),
    dict(name='r68', c='track', wp=[(1230, 3720), (1300, 3830), (1336, 3908), (1365, 3960), (1390, 4000), (1412, 4065), (1440, 4150), (1468, 4243), (1490, 4310), (1510, 4385, 's')], hw=5.0),
    dict(name='r69', c='track', wp=[(1450, 3600), (1440, 3650), (1440, 3700), (1428, 3760), (1425, 3800), (1428, 3850), (1445, 3900), (1480, 3960), (1500, 4000), (1530, 4100), (1560, 4200), (1590, 4320)], hw=5.0),
    dict(name='r70', c='track', wp=[(1445, 3642), (1478, 3668), (1520, 3690), (1560, 3740), (1600, 3790), (1625, 3850), (1645, 3920), (1700, 4005), (1760, 4045), (1830, 4075), (1920, 4095), (1980, 4112), (2040, 4140)], hw=5.0),
    dict(name='r71', c='track', wp=[(1590, 4330), (1700, 4310), (1800, 4300), (1920, 4300)]),
    dict(name='r72', c='track', wp=[(1920, 4300), (2000, 4240), (2110, 4150)]),
    dict(name='r73', c='track', wp=[(1940, 3910), (2040, 4030), (2110, 4150)]),
    dict(name='r74', c='track', wp=[(2110, 4150), (2200, 4110), (2290, 4060)]),
    dict(name='r75', c='track', wp=[(2800, 3600), (2760, 3750), (2720, 3870), (2680, 3960), (2690, 4050), (2700, 4200)]),
    dict(name='r76', c='track', wp=[(2450, 4100), (2600, 4120), (2760, 4190)]),
    dict(name='r77', c='track', wp=[(3078, 4305), (3040, 4420), (3000, 4520), (2970, 4608)]),
    dict(name='r78', c='track', wp=[(2700, 4185), (2800, 4190), (2900, 4235), (3000, 4275), (3078, 4305), (3200, 4350), (3400, 4425), (3560, 4480), (3712, 4490)]),
    dict(name='r79', c='secondary', wp=[(4140, 3712), (4180, 3740), (4260, 3810), (4290, 3900), (4290, 4000), (4280, 4100), (4265, 4200), (4255, 4400), (4245, 4608)]),
    dict(name='r80', c='track', wp=[(4280, 4120), (4350, 4250), (4420, 4380), (4500, 4500), (4540, 4560)]),
    dict(name='r81', c='residential', wp=[(4150, 3610), (4300, 3660), (4450, 3730), (4608, 3810)]),
    dict(name='r82', c='secondary', wp=[(2700, 1813), (2900, 1950), (3140, 2090)]),
    dict(name='r83', c='residential', wp=[(3870, 3930), (3960, 3895), (4060, 3850), (4160, 3815), (4250, 3800)]),
    dict(name='r84', c='track', wp=[(4060, 3975), (4130, 4040), (4200, 4100), (4275, 4135)]),
    dict(name='r85', c='path', wp=[(3905, 4275), (4000, 4285), (4100, 4300), (4255, 4310)]),
    dict(name='r86', c='track', wp=[(4045, 4340), (4150, 4340), (4255, 4338)]),
    dict(name='r87', c='track', wp=[(3600, 4448), (3700, 4445), (3800, 4440), (3900, 4440), (4000, 4440), (4080, 4432), (4255, 4445)]),
    dict(name='r88', c='track', wp=[(4080, 4435), (4075, 4520), (4075, 4608)]),
    dict(name='r89', c='residential', wp=[(2195, 890), (2230, 990), (2260, 1100), (2290, 1220)]),
    dict(name='a00', c='path', wp=[(3, 92), (25, 155), (48, 220)]),
    dict(name='belgorod_road', c='secondary', wp=[(2295, 4059), (2312, 3960), (2328, 3862), (2342, 3763), (2334, 3671), (2313, 3592), (2268, 3506), (2217, 3419), (2170, 3330), (2130, 3222), (2132, 3106), (2175, 3001), (2232, 2909), (2304, 2831), (2376, 2760), (2446, 2691), (2517, 2620), (2589, 2550), (2662, 2481), (2744, 2423), (2816, 2353), (2901, 2297), (2973, 2227), (3044, 2157), (3115, 2087), (3187, 2017), (3258, 1947), (3330, 1877), (3400, 1806), (3478, 1734), (3571, 1692), (3665, 1659), (3759, 1623)], hw=8.0),
    dict(name='a01', c='track', wp=[(27, 0), (40, 35), (53, 60), (90, 115), (127, 170)]),
    dict(name='a02', c='track', wp=[(0, 287), (40, 320), (65, 345), (87, 373), (123, 400)]),
    dict(name='a03', c='residential', wp=[(650, 560), (645, 500), (625, 430), (615, 375)]),
    dict(name='a04', c='residential', wp=[(880, 612), (930, 600), (1060, 600), (1190, 598)]),
    dict(name='a05', c='track', wp=[(1190, 598), (1300, 600), (1427, 598), (1550, 596), (1650, 593), (1770, 590)]),
    dict(name='a06', c='track', wp=[(3153, 242), (3200, 270), (3260, 282), (3310, 283)]),
    dict(name='a07', c='residential', wp=[(3153, 245), (3140, 320), (3147, 395)]),
    dict(name='a08', c='residential', wp=[(3250, 252), (3330, 190), (3420, 112), (3470, 68)]),
    dict(name='a09', c='residential', wp=[(3570, 12), (3620, 90), (3670, 170), (3712, 240)]),
    dict(name='a11', c='path', wp=[(3645, 985), (3700, 983), (3760, 988)]),
    dict(name='a12', c='track', wp=[(4560, 1530), (4562, 1400), (4565, 1250), (4565, 1157), (4585, 917), (4605, 683), (4607, 640)]),
    dict(name='s02', c='residential', wp=[(900, 132), (930, 125), (990, 110)], hw=4.0),
    dict(name='s03', c='residential', wp=[(870, 205), (930, 190), (1000, 165)], hw=4.0),
    dict(name='s04', c='residential', wp=[(1147, 110), (1147, 180), (1150, 235)], hw=4.0),
    dict(name='s08', c='residential', wp=[(5, 795), (60, 775), (100, 768), (150, 730), (200, 690)], hw=6.0),
    dict(name='s20', c='residential', wp=[(1990, 1180), (2060, 1200), (2140, 1225)], hw=4.0),
    dict(name='s_bel1', c='residential', wp=[(2548, 4050), (2548, 4150), (2546, 4250), (2545, 4350), (2543, 4450), (2540, 4560)], hw=4.0),
    dict(name='pk1', c='residential', wp=[(3880, 1640), (4000, 1605), (4120, 1572), (4250, 1540), (4400, 1505), (4520, 1478), (4600, 1462)]),
    dict(name='pk2', c='residential', wp=[(4250, 1535), (4320, 1400), (4390, 1280), (4430, 1210)]),
    dict(name='pk3', c='residential', wp=[(4010, 1400), (4020, 1500), (4030, 1600), (4045, 1700)]),
    dict(name='pk4', c='residential', wp=[(3900, 1460), (3980, 1440), (4060, 1425), (4140, 1415)]),
    dict(name='b01', c='residential', wp=[(4400, 1035), (4378, 1095), (4352, 1150)], hw=6.0),
    dict(name='b02', c='residential', wp=[(925, 1320), (925, 1380), (928, 1440)], hw=6.0),
    dict(name='b03', c='residential', wp=[(1790, 1705), (1840, 1750), (1890, 1795), (1905, 1822)], hw=6.0),
    dict(name='b04', c='track', wp=[(2003, 1225), (2000, 1300), (1995, 1380), (1990, 1450)], hw=6.0),
    dict(name='b05', c='path', wp=[(3740, 1330), (3800, 1385), (3870, 1410), (3920, 1440)], hw=6.0),
    dict(name='b06', c='residential', wp=[(3955, 1712), (4030, 1705), (4100, 1695)], hw=6.0),
    dict(name='b07', c='residential', wp=[(4228, 1590), (4225, 1655), (4220, 1720)], hw=6.0),
    dict(name='b08', c='residential', wp=[(4150, 1662), (4225, 1655), (4300, 1650)], hw=6.0),
    dict(name='b09', c='residential', wp=[(4400, 1832), (4460, 1792), (4530, 1758)], hw=6.0),
    dict(name='b10', c='residential', wp=[(505, 2195), (500, 2280), (495, 2360)], hw=6.0),
    dict(name='b11', c='residential', wp=[(345, 2820), (345, 2900), (350, 2990)], hw=6.0),
    dict(name='b12', c='residential', wp=[(1880, 1960), (1862, 2000), (1860, 2060)], hw=6.0),
    dict(name='b13', c='residential', wp=[(530, 2712), (600, 2712), (680, 2718)], hw=5.0),
    dict(name='b14', c='track', wp=[(2040, 2850), (2120, 2890), (2200, 2930)], hw=6.0),
    dict(name='b15', c='track', wp=[(2030, 2965), (2120, 2958), (2200, 2950)], hw=6.0),
    dict(name='b16', c='residential', wp=[(250, 3020), (320, 3025), (395, 3030)], hw=6.0),
    dict(name='b17', c='residential', wp=[(430, 3215), (470, 3250), (510, 3290)], hw=6.0),
    dict(name='b18', c='residential', wp=[(2790, 2995), (2850, 3030), (2915, 3070), (2935, 3075)], hw=6.0),
    dict(name='b19', c='residential', wp=[(2990, 3465), (2925, 3480), (2922, 3560), (2915, 3650)], hw=6.0),
    dict(name='b20', c='residential', wp=[(4555, 3195), (4555, 3260), (4552, 3330)], hw=6.0),
    dict(name='y01', c='residential', wp=[(1945, 3740), (1900, 3810), (1860, 3880), (1830, 3950)], hw=6.0),
    dict(name='y02', c='residential', wp=[(1730, 3780), (1800, 3835), (1870, 3885), (1920, 3920)], hw=6.0),
    dict(name='y03', c='residential', wp=[(1720, 3840), (1790, 3890), (1850, 3935)], hw=6.0),
    dict(name='bl01', c='residential', wp=[(2248, 4060), (2245, 4140), (2242, 4220)], hw=6.0),
    dict(name='bl02', c='residential', wp=[(2360, 4090), (2365, 4150), (2372, 4210)], hw=6.0),
    dict(name='b21', c='residential', wp=[(4120, 3985), (4200, 3985), (4285, 3990)], hw=6.0),
    dict(name='oz01', c='track', wp=[(1130, 4505), (1200, 4505), (1255, 4510)], hw=6.0),
    dict(name='oz02', c='residential', wp=[(1248, 4455), (1245, 4530), (1240, 4600)], hw=6.0),
    dict(name='bl03', c='residential', wp=[(2580, 4160), (2640, 4230), (2700, 4300)], hw=6.0),
    dict(name='bl04', c='residential', wp=[(2560, 4235), (2620, 4300), (2680, 4370)], hw=6.0),
    dict(name='bl05', c='residential', wp=[(2655, 3990), (2655, 4060), (2652, 4135)], hw=6.0),
    dict(name='b13b', c='residential', wp=[(530, 2750), (600, 2766), (655, 2786)], hw=5.0),
    dict(name='b22', c='residential', wp=[(1975, 1280), (1972, 1330), (1968, 1380)], hw=5.0),
    dict(name='b23', c='residential', wp=[(1165, 600), (1165, 640), (1166, 680)], hw=5.0),
    dict(name='pv1', c='residential', wp=[(4060, 2930), (4180, 2960), (4335, 2995), (4385, 3005, 's')], hw=6.0),
    dict(name='pv2', c='residential', wp=[(4100, 3035), (4220, 3075), (4330, 3110), (4345, 3115, 's')], hw=6.0),
    dict(name='pv3', c='residential', wp=[(4100, 3150), (4200, 3190), (4320, 3238)], hw=6.0),
    dict(name='pv4', c='residential', wp=[(4448, 2990), (4450, 3060), (4452, 3130)], hw=5.0),
    dict(name='pv5', c='residential', wp=[(4100, 2862), (4250, 2870), (4345, 2885), (4393, 2885, 's')], hw=6.0),
    dict(name='pv6', c='residential', wp=[(4420, 2850), (4500, 2900), (4575, 2940)], hw=6.0),
    dict(name='ko1', c='residential', wp=[(690, 1395), (780, 1480), (850, 1560), (890, 1640)], hw=6.0),
    dict(name='kz1', c='residential', wp=[(1100, 1945), (1250, 1955), (1400, 1960), (1480, 1965)], hw=6.0),
    dict(name='kz2', c='residential', wp=[(1598, 1895), (1595, 1980), (1595, 2070)], hw=6.0),
    dict(name='kz3', c='residential', wp=[(1662, 1900), (1665, 2000), (1668, 2060)], hw=6.0),
    dict(name='bg1', c='residential', wp=[(1150, 1815), (1300, 1825), (1450, 1830)], hw=6.0),
    dict(name='an1', c='residential', wp=[(1680, 1870), (1760, 1915), (1840, 1965)], hw=6.0),
    dict(name='an2', c='residential', wp=[(1810, 1850), (1850, 1900), (1880, 1950)], hw=6.0),
    dict(name='mk1', c='residential', wp=[(1985, 1785), (2025, 1715), (2070, 1650), (2115, 1585)], hw=6.0),
    dict(name='mk2', c='residential', wp=[(1925, 1745), (1965, 1690), (2010, 1630), (2055, 1570)], hw=6.0),
    dict(name='pl1', c='residential', wp=[(2280, 1345), (2340, 1275), (2400, 1205), (2470, 1130), (2520, 1080)], hw=6.0),
    dict(name='pl2', c='residential', wp=[(2255, 1152), (2330, 1150), (2420, 1148)], hw=5.0),
    dict(name='pl3', c='residential', wp=[(2620, 1020), (2680, 1060), (2745, 1062)], hw=6.0),
    dict(name='ve1', c='residential', wp=[(740, 620), (800, 560), (860, 490), (920, 440), (980, 395)], hw=6.0),
    dict(name='il1', c='residential', wp=[(650, 775), (640, 850), (630, 930)], hw=6.0),
    dict(name='be1', c='residential', wp=[(3300, 420), (3380, 360), (3460, 300), (3540, 240)], hw=6.0),
    dict(name='vo1', c='residential', wp=[(3480, 160), (3560, 90), (3640, 30), (3680, 5)], hw=6.0),
    dict(name='vo2', c='residential', wp=[(3530, 245), (3610, 180), (3690, 120)], hw=6.0),
    dict(name='c01', c='track', wp=[(1150, 3522), (1230, 3521), (1300, 3520), (1340, 3542), (1385, 3585)], hw=6.0),
    dict(name='st1', c='residential', wp=[(2800, 2895), (2870, 2855), (2945, 2812)], hw=6.0),
    dict(name='d01', c='path', wp=[(2995, 3168), (3100, 3128), (3200, 3105)], hw=6.0),
]

def run71(sheet_png, builtup_png, osm_path, log=print):
    rgb = np.asarray(Image.open(sheet_png).convert('RGB'))[BLOCK_PX[1]:BLOCK_PX[3], BLOCK_PX[0]:BLOCK_PX[2]]
    ink4 = ink_dark(rgb); V = grid_lines(ink4); Hh = grid_lines(ink4.T)
    ink4 &= ~(remove_runs(ink4, V) | remove_runs(ink4.T, Hh).T)
    blank4 = np.all(rgb == 230, -1); blank4 = ndi.binary_dilation(ndi.binary_opening(blank4, iterations=2), iterations=3)
    bu4 = np.asarray(Image.open(builtup_png).convert('L'))[BLOCK_PX[1]:BLOCK_PX[3], BLOCK_PX[0]:BLOCK_PX[2]] > 0
    rail, _ = railway_band(pool(ink4, 0.5), osm_path)
    up = lambda m: np.repeat(np.repeat(m, F, 0), F, 1)
    rail4 = up(ndi.binary_erosion(rail)); excl4 = up(exclude_mask())
    cost, sk = exact_cost(ink4, blank4, rail4, excl4, bu4)
    STREET_COST[0] = street_cost(ink4, blank4)    # c72: village streets follow the light lanes between the house rows
    roads = []; devmax = 0.0
    for r in DIGITISED:
        p, dev = digitise(cost, sk, r, rail4, ink4); devmax = max(devmax, dev)
        roads.append(dict(name=r['name'], c=r['c'], px=p))
    log('digitised roads: %d, smoothing deviation from the routed centre line <= %.1f m' % (len(roads), devmax * 4))
    roads = share_junctions(roads, log=log)
    dang = dangling(roads, bu4, blank4)
    log('road ends not at a junction / village / block edge / blank patch: %d' % len(dang))
    return roads, dang

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sheet'); ap.add_argument('out_json')
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument('--builtup', default=os.path.join(here, '..', 'docs', 'm12_terrain', 'period', 'builtup_1941.png'))
    ap.add_argument('--osm', default=os.path.join(here, '..', 'docs', 'm12_terrain', 'osm', 'prokh.osm.json'), help='railway corridor only')
    ap.add_argument('--preview', default=None)
    a = ap.parse_args(); t0 = time.time()
    roads, dang = run71(a.sheet, a.builtup, a.osm)
    feats = [dict(highway=r['c'], name=r['name'], source='sheet', length_m=int(round(plen(r['px']) * 4)),
                  pts=[[round(x, 1), round(y, 1)] for x, y in (px4_to_m(u, v) for u, v in r['px'])]) for r in roads]
    stats = {}
    for f in feats: s = stats.setdefault(f['highway'], [0, 0]); s[0] += 1; s[1] += f['length_m']
    meta = dict(source='RKKA 1:100 000 sheet of 1941 (docs/m12_terrain/period/rkka100k_block.png), digitised by tools/roads_1941.py (c71)',
                crs='DEM-lattice metres (x east, y north from the lattice SW corner), as prokh_gen.py', block=[0, 2048, 18432, 20480],
                classes={'secondary': 'double line: improved / main road', 'track': 'single solid line: dirt road',
                         'path': 'dashed line: field / forest track', 'residential': 'village street'},
                stats={k: dict(n=v[0], km=round(v[1] / 1000.0, 1)) for k, v in sorted(stats.items())},
                dangling=[dict(road=n, end=e, px=list(p)) for n, e, p in dang])
    json.dump(dict(meta=meta, roads=feats), open(a.out_json, 'w', encoding='utf-8'), indent=0, ensure_ascii=False)
    print('roads_1941:', meta['stats'], '->', a.out_json, '%.0fs' % (time.time() - t0))
    if a.preview:
        os.makedirs(a.preview, exist_ok=True)
        sh = Image.open(a.sheet).convert('RGB').crop(BLOCK_PX)
        render(sh, feats, os.path.join(a.preview, 'roads1941_block.png'), scale=0.5, width=2, fade=0.35)



def street_cost(ink4, blank4):
    """c72: cost for village streets - the light lanes between the house rows (paper), cheapest on the lane's centre
    line; any ink (house blocks, their outlines, hatching) is dear"""
    paper = ~ndi.binary_dilation(ink4, structure=np.ones((2, 2)))
    dl = ndi.distance_transform_edt(paper)
    cost = np.where(paper, 2.6 - 0.25 * np.clip(dl, 0, 6), 14.0).astype(np.float32)
    cost[blank4] = 6.0
    return cost

# c72 review of builtup_1941.png (labels of the 9 x 9 crop, 8-connected): blobs that are not villages, removed
NOT_VILLAGE = {1: 'wood at the frame', 2: 'wood at the frame', 9: 'wood', 7: 'wood', 17: 'wood / orchard by the river', 16: 'wood', 18: 'wood', 20: 'railway buildings (Kursk line)', 21: 'railway', 39: 'wood', 35: 'red / green pencil over the 12.0 road', 29: 'railway (Barchevka)', 36: 'railway (Barchevka)', 53: 'wood', 54: 'road junction / lettering', 81: 'railway (Komsomolets)', 85: 'lettering (svkh. Komsomolets)', 83: 'lettering (svkh. Komsomolets)', 74: 'railway (Kursk line S of Prokhorovka)', 65: 'park / orchard square in Prokhorovka', 102: "lettering ('Виноградовка')", 98: 'spot height 249.2 / windmill symbols', 112: 'wood', 120: 'wood', 117: 'wood', 123: 'road junction', 115: 'lettering (Belenikhino)', 119: "lettering ('раз.')", 125: "lettering / symbol ('раз.')", 121: 'symbol (Belenikhino station)', 135: 'railway (Belenikhino station)', 137: 'railway (Belenikhino station)', 144: 'railway', 145: 'railway', 140: 'blue pencil / stream', 136: 'pencil smudge', 134: 'pencil + ravine (Zhimolostnoye S)', 142: 'pencil + ravine', 138: 'road-junction symbol at 234.9', 30: 'windmill symbols (Petrovka)', 131: 'lettering (Belenikhino)', 128: 'railway (Belenikhino)'}

if __name__ == '__main__':
    main()

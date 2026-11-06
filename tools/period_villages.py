r"""1941 settlements from the RKKA 1:100 000 sheet -> layout `villages_1943` polygons and a cleaned period trim mask.

The sheet (docs/m12_terrain/period/rkka100k_block.png: tools/period_cover.py --tiles output, 4 m/px on the 11 x 12 lattice,
row 0 = north) draws villages as black hatched house blocks along the streets.  This script finds them as blobs of
black-ink density, drops what is not a settlement (the staff's blue / red pencil overprint, black pencil smudges,
labels, the railway) by a reviewed list of blob ids, and writes
  * the polygons (eroded 40 m: the 1:100 000 symbols are exaggerated) into the layout's `villages_1943`, keeping any
    hand-traced entries already there (Teterevino), and
  * docs/m12_terrain/period/builtup_1941.png, the trim mask prokh_gen.py applies to the modern OSM villages, so that the
    same cleaned blobs decide what is kept (the raw ink-density mask kept modern houses under the pencil bands).

  py -3 tools\period_villages.py docs\m12_terrain\period\rkka100k_block.png docs\m11_prokhorovka\layout_10jul.json
        docs\m12_terrain\period\builtup_1941.png [--review out_dir]   (review: the sheet with numbered blobs, 1024 px tiles)

Blob ids depend only on the image and the parameters below; after a new tile download re-run with --review, check the
tiles and edit KEEP / CUTS.  Reviewed 2026-10-25 for the 7 x 5 block (X 0-14, Y 0-10 squares).

2026-11-04 (user: 'non-existing settlements and roads' on the enlarged 9 x 9 block): outside the old 7 x 5 rectangle the
mask was still the raw ink of the sheet (roads, grid lines, text, the staff's pencil), so modern OSM villages and house
footprints along every road survived the trim.  --outer re-does the OUTER RING of the 9 x 9 block (sheet px x 0..4608,
y 1024..5632) the same way: the blobs are labelled on the whole 9 x 9 crop (ids in KEEP_OUTER refer to that labelling),
every blob with pixels outside the old rectangle was looked at on the sheet (tiles from --review-outer) and kept only
if it is drawn with the black house-block symbol; text, the 'Сп 227' / arc pencil marks, orchard tree circles, railway
huts and road junctions were dropped.  The old rectangle (the centre) is copied from the existing mask unchanged, its
layout polygons are kept as they are; the outer polygons are added with 'outer blob N' in their names.
  py -3 tools\period_villages.py <sheet> <layout> <mask> --outer [--review-outer dir] [--roads docs\m12_terrain\period\roads_1941.png]
--roads writes the road-ink raster prokh_gen.py uses to drop OSM roads that the 1941 sheet does not draw (255 = black
line ink of the sheet, 128 = no sheet there (missing tiles), 0 = paper / colour; same 4 m grid, row 0 = north).
"""
import sys, json, argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

BLOCK = (1024, 2048, 4608, 4608)   # the 7 x 5 block in the sheet raster: px x0, y0, x1, y1 (DEM x 4096..18432, y 6144..16384 at 4 m)
# settlements (reviewed): Petrovka, Polezhayev, Prelestnoye, the hamlets on the north bank, Andreyevka - Mikhailovka,
# svkh. Oktyabrsky, the hamlet N of Prokhorovka, Prokhorovka (5, 35: mask only), brick works, Prokhorovka W, MTS,
# the hamlets SE of Prokhorovka, Lutovo, Vasilyevka, Kozlovka - Bogoroditskoye, Yamki, svkh. Stalinskoye otd., Grushki,
# Pravorot (W / main), Teterevino (131: hand-traced polygon instead), railway barracks, svkh. Komsomolets, Storozhevoye,
# Vinogradovka N, Dalny, hamlet E of Pravorot
KEEP = [7, 6, 1, 12, 18, 19, 27, 42, 3, 5, 21, 24, 30, 35, 37, 40, 46, 52, 53, 51, 47, 50, 65, 73, 55, 56, 62, 71, 87, 131, 92, 96, 93, 110, 134, 137, 94, 124, 120]
MASK_ONLY = [5, 35, 131]           # in the trim mask but no polygon: Prokhorovka town (OSM has the houses), Teterevino (hand-traced)
CUTS = [(94, lambda X, Y: (X < 11.9) & (Y < 7.75)),    # Pravorot: the red pencil band NW of the village
        (87, lambda X, Y: Y < 6.8)]                     # Pravorot W: the 'П' of the label
NAMES = {7: 'Petrovka (N)', 6: 'Polezhayev / Petrovka (W)', 1: 'Prelestnoye', 12: 'Polezhayev', 18: 'hamlet on the N bank W of Prelestnoye',
         19: 'hamlet on the N bank W of Prelestnoye (W)', 27: 'Andreyevka - Mikhailovka - Prelestnoye SW', 42: 'svkh. Oktyabrsky yard and houses',
         3: 'hamlet N of Prokhorovka', 21: 'Prokhorovka brick works', 24: 'Prokhorovka W (N of the railway)', 30: 'Prokhorovka W (small)',
         37: 'Prokhorovka MTS (E)', 40: 'Prokhorovka MTS', 46: 'hamlet SE of Prokhorovka (E)', 52: 'hamlet SE of Prokhorovka',
         53: 'hamlet SE of Prokhorovka (W)', 51: 'Lutovo', 47: 'Vasilyevka', 50: 'Kozlovka - Bogoroditskoye', 65: 'Yamki',
         73: 'svkh. Stalinskoye otd.', 55: 'Grushki-Vtorye', 56: 'Lutovo (S)', 62: 'Grushki-Pervye', 71: 'Grushki (S street)',
         87: 'Pravorot (W)', 92: 'railway barracks NE of the Komsomolets wood', 96: 'svkh. Komsomolets yard and houses',
         93: 'Storozhevoye', 110: 'Storozhevoye (SW)', 134: 'Vinogradovka (N)', 137: 'Vinogradovka (NW)', 94: 'Pravorot', 124: 'Dalny',
         120: 'hamlet E of Pravorot'}

# ---- the outer ring of the 9 x 9 block (reviewed 2026-11-04 on the sheet crops; ids = labels of blobs(sheet, FULL))
FULL = (0, 1024, 4608, 5632)       # the 9 x 9 block in the sheet raster (DEM x 0..18432, y 2048..20480 at 4 m)
# kept: black house-block symbols.  Dropped (not listed): text of the place names and spot heights (Вышняя Ольшанка,
# Веселый, Петровка, Береговое, Полежаев, Озеровский, 'Свх. им Ворошилова', 165.4, 227.8, 188.3 ...), the staff's pencil
# ('Сп 227', the arcs NE of Barchevka, the strokes on the red line), orchard / wood tree circles (Ilyinsky, the orchards S
# of Vinogradovka), railway huts and the railway double line at Belenikhino, road junction blobs, single specks < ~20 m.
KEEP_OUTER = [1, 2, 3, 5, 6, 17, 18, 19, 29, 32, 40, 47, 48, 56, 61, 62, 67, 68, 70, 71, 72, 73, 74, 75, 77, 84, 86, 89, 90, 91,
              99, 114, 127, 130, 143, 154, 183, 185, 190, 204, 213, 215, 218, 219, 224, 233, 236, 243, 248, 251, 256, 260, 261,
              262, 267, 272, 278, 284, 294, 295, 296, 303, 305, 306, 307, 310, 313, 314, 316, 317, 318, 319, 320, 321, 322, 324,
              327, 332, 338, 340, 341, 342, 343, 344, 345, 349, 350, 354, 357, 359, 362]
# cuts in FULL-crop pixels (x east, y south from the crop's NW corner)
CUTS_OUTER = [(75, lambda x, y: (x >= 3963) & (y <= 790)),    # Kusty: the pencil arc of 'Сп 227' over the houses
              (75, lambda x, y: (x >= 3940) & (y >= 835)),    # Kusty: the dark pencil stroke along the red line
              (75, lambda x, y: (x < 3910) & (y < 693)),      # Kusty: the pencil 'п'
              (75, lambda x, y: x < 3880),                    # Kusty: the pencil '227' W of the houses
              (47, lambda x, y: (x >= 3440) & (y >= 452) & (y <= 520))]   # Beregovoye: the 'Бе' of the label
NAMES_OUTER = {1: 'houses at the N edge (W)', 2: 'houses at the N edge (W)', 3: 'Olkhovsky (N)', 19: 'Olkhovsky (NE)', 48: 'Olkhovsky - Veselyi',
               70: 'Olkhovsky - Veselyi', 72: 'Veselyi', 56: 'Olkhovsky (S)', 61: 'Olkhovsky (W street)', 67: 'Olkhovsky (river street)',
               77: 'Ilyinsky', 86: 'Ilyinsky (W)', 17: 'Veselyi (E)', 32: 'Veselyi (E)', 84: 'Kurlov', 73: 'Kurlov', 18: 'svkh. im. Voroshilova (N)',
               29: 'svkh. im. Voroshilova', 62: 'hamlet S of svkh. im. Voroshilova', 68: 'hamlet S of svkh. im. Voroshilova', 40: 'Petrovka (N) - Beregovoye',
               5: 'Vyshnyaya Olshanka', 6: 'Vyshnyaya Olshanka (E)', 47: 'Beregovoye', 74: 'Beregovoye (W)', 75: 'Kusty', 71: 'Barchevka (N)',
               89: 'Petrovka (NE)', 90: 'Petrovka (N, single house)', 91: 'Petrovka', 99: 'Polezhayev (E)', 114: 'Krasny Oktyabr (N)', 130: 'Krasny Oktyabr',
               127: 'Klyuchi', 143: 'Klyuchi (S)', 154: 'Krasny Oktyabr - Prokhorovka (W bank)', 183: 'Gryaznoye (N)', 185: 'Gryaznoye (N)',
               190: 'Gryaznoye', 204: 'Gryaznoye', 213: 'Gryaznoye (E)', 215: 'Gryaznoye (S)', 218: 'Gryaznoye (S)', 219: 'Gryaznoye (SE)',
               224: 'Gryaznoye (S)', 233: 'Gryaznoye - Mal. Mayachki', 236: 'Gryaznoye - Mal. Mayachki', 243: 'Gryaznoye - Mal. Mayachki',
               248: 'Mal. Mayachki (N)', 251: 'Mal. Mayachki (N)', 256: 'Mal. Mayachki (NE)', 260: 'Mal. Mayachki', 262: 'Mal. Mayachki',
               267: 'Mal. Mayachki', 345: 'Luchki', 350: 'Ozerovsky', 362: 'Ozerovsky (S)', 313: 'houses in the balka N of Ozerovsky',
               272: 'Teterevino (S)', 294: 'Yasnaya Polyana', 317: 'Yasnaya Polyana (E)', 305: 'Yasnaya Polyana (balka)', 320: 'Yasnaya Polyana (S)',
               307: 'Belenikhino MTS', 319: 'Belenikhino', 316: 'Belenikhino', 318: 'Belenikhino', 322: 'Belenikhino', 342: 'Belenikhino (S)',
               359: 'Belenikhino (S)', 306: 'Ivanovka (N)', 314: 'Ivanovka (N)', 321: 'Ivanovka (N)', 324: 'Ivanovka', 327: 'Ivanovka',
               332: 'Ivanovka - Belenikhino station', 338: 'Ivanovka (S)', 349: 'Ivanovka (E)', 278: 'Vinogradovka (S)', 296: 'Vinogradovka (S)',
               341: 'Zhimolostnoye (W)', 354: 'Zhimolostnoye (W)', 295: 'Zhimolostnoye', 303: 'Zhimolostnoye', 310: 'Zhimolostnoye',
               261: 'Pravorot (S)', 284: 'Dalny', 340: 'Plota (W)', 343: 'Plota (W)', 344: 'houses at 247.7', 357: 'Plota'}


def road_ink(sheet):
    """the black line work of the sheet (roads, tracks, field paths - and grid lines, house symbols, lettering) as a
    0 / 255 raster (thin line work only, see below), with 128 where the sheet has no image (missing tiles: plain (230, 230, 230) fill).  Brown contour lines,
    the blue rivers and the red / blue staff pencil are not black: black print is dark and unsaturated; the brown of the
    contours is as dark as anti-aliased black lines but warmer (r - b > 22)."""
    a = np.asarray(sheet.convert('RGB')).astype(np.int16)
    g = a.mean(-1); r, b = a[..., 0], a[..., 2]; sat = a.max(-1) - a.min(-1)
    ink = ((g < 85) | ((g < 115) & ((r - b) < 22))) & (sat < 60) & ((b - r) < 10)
    # 4 Nov: keep only the LINE work. Lettering (Беленихино, РС 23, 220.3 lie right over the modern grid streets of
    # Belenikhino), spot heights, orchard dots and tree circles are pieces a few tens of px across, as wide as the road
    # lines, so they are told apart by shape: a piece of connected ink under 40 px (160 m) across goes unless it is a dash
    # (at least 10 px long and 3 times as long as wide - the cart tracks are dashed, and on the upsampled western sheet the
    # dashes are short). Roads, the railway and the house rows joined to their streets stay.
    lab, n = ndi.label(ink, structure=np.ones((3, 3)))
    if n:
        sl = ndi.find_objects(lab); big = np.zeros(n + 1, bool)
        for k, q in enumerate(sl):
            h_, w_ = q[0].stop - q[0].start, q[1].stop - q[1].start
            big[k + 1] = max(h_, w_) >= 40 or (max(h_, w_) >= 10 and max(h_, w_) >= 3 * min(h_, w_))   # long, or a dash
        ink = big[lab]
    blank = np.all(a == 230, -1)
    blank = ndi.binary_dilation(ndi.binary_opening(blank, iterations=2), iterations=3)
    return np.where(blank, 128, np.where(ink, 255, 0)).astype(np.uint8)


def outer(sheet, a, old):
    """the outer ring of the 9 x 9 block: mask pixels and polygons (see the module docstring)"""
    from skimage import measure
    lab = blobs(sheet, FULL)
    H, W = lab.shape
    inner = np.zeros((H, W), bool)
    inner[BLOCK[1] - FULL[1]:BLOCK[3] - FULL[1], BLOCK[0] - FULL[0]:BLOCK[2] - FULL[0]] = True
    if a.review_outer:
        import os; os.makedirs(a.review_outer, exist_ok=True)
        ov = sheet.convert('RGB').crop(FULL); d = ImageDraw.Draw(ov, 'RGBA')
        try: font = ImageFont.load_default(size=26)
        except Exception: font = ImageFont.load_default()
        ids = set(int(i) for i in np.unique(lab[~inner]) if i)
        for i, sl in enumerate(ndi.find_objects(lab), 1):
            if sl is None or i not in ids: continue
            m = lab[sl] == i; ys, xs = np.nonzero(m)
            col = (0, 160, 0, 255) if i in KEEP_OUTER else (255, 0, 255, 255)
            for cnt in measure.find_contours(np.pad(m, 1).astype(float), 0.5):
                pts = [(x + sl[1].start - 1, y + sl[0].start - 1) for y, x in cnt[::3]]
                if len(pts) > 2: d.polygon(pts, outline=col, fill=col[:3] + (35,))
            d.text((xs.mean() + sl[1].start - 12, ys.mean() + sl[0].start - 12), str(i), fill=col, font=font)
        tiles = [(x, 0, min(4608, x + 960), 1100) for x in range(0, 4608, 960)] + [(x, 3500, min(4608, x + 960), 4608) for x in range(0, 4608, 960)] + \
                [(0, y, 1100, min(3600, y + 960)) for y in (1000, 1900, 2700)]
        for k, b in enumerate(tiles): ov.crop(b).save(os.path.join(a.review_outer, 'rvo_%02d.png' % k))
        print('outer review tiles written to', a.review_outer)
    m = np.isin(lab, KEEP_OUTER) & ~railway_mask((H, W), a.osm, FULL)
    Y, X = np.mgrid[0:H, 0:W]
    for bid, f in CUTS_OUTER: m &= ~((lab == bid) & f(X, Y))
    m = ndi.binary_opening(m, iterations=2)
    lab2, n2 = ndi.label(m); sizes = ndi.sum(m, lab2, range(1, n2 + 1))
    m &= ~np.isin(lab2, [i + 1 for i, s in enumerate(sizes) if s * 16 < 3000])
    full = old[FULL[1]:FULL[3], FULL[0]:FULL[2]] > 0
    full = np.where(inner, full, m)                        # the reviewed centre stays exactly as it was
    old[FULL[1]:FULL[3], FULL[0]:FULL[2]] = np.where(full, 255, 0).astype(np.uint8)
    print('built-up 1941, outer ring: %.2f %% (raw ink before: %.2f %%)' % (100 * m[~inner].mean(), 100 * (np.asarray(Image.open(a.mask_out)).copy()[FULL[1]:FULL[3], FULL[0]:FULL[2]][~inner] > 0).mean()))
    # polygons of the outer ring: eroded on the whole mask (no 40 m gap at the old rectangle's edge), outer part only
    vm = ndi.binary_erosion(full, iterations=10) & ~inner
    lab3, n3 = ndi.label(vm); polys = []
    for i, sl in enumerate(ndi.find_objects(lab3), 1):
        mm = lab3[sl] == i
        if mm.sum() * 16 < 2000: continue
        ids, cnt = np.unique(lab[sl][mm], return_counts=True); src = int(ids[np.argmax(cnt)])
        for cnt_ in measure.find_contours(np.pad(mm, 1).astype(float), 0.5):
            poly = measure.approximate_polygon(np.array([(x + sl[1].start - 1, y + sl[0].start - 1) for y, x in cnt_]), tolerance=2.0)
            if len(poly) < 3: continue
            dem = [[int(round((x + FULL[0]) * 4)), int(round(24576 - (y + FULL[1]) * 4))] for x, y in poly]
            area = abs(sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(dem, dem[1:] + dem[:1]))) / 2
            if area >= 3000: polys.append(dict(name=f"{NAMES_OUTER.get(src, '1941 built-up')} (RKKA 1:100 000 sheet, outer blob {src})", pts=dem))
    return old, polys


def blobs(sheet, box=BLOCK):
    """black-ink density blobs of the block: label image, ids as reviewed"""
    rk = np.asarray(sheet.convert('RGB').crop(box)).astype(int)
    g = rk.mean(-1); r, b = rk[..., 0], rk[..., 2]
    ink = (g < 95) & ((b - r) < 5) & ((rk.max(-1) - rk.min(-1)) < 70)     # black print, not the blue pencil (b - r > 15)
    solid = ndi.binary_erosion(ink, iterations=4)                          # 16 m: roads, contours and lettering go, house blocks stay
    rr = 20; k = 2 * rr + 1
    p = np.pad(solid.astype(np.float32), rr, mode='edge'); c = np.pad(np.cumsum(np.cumsum(p, 0), 1), ((1, 0), (1, 0)))
    dens = (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)
    blob = ndi.binary_closing(dens > 0.04, iterations=6)
    lab, n = ndi.label(blob)
    sizes = ndi.sum(blob, lab, range(1, n + 1))
    lab[np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s * 16 < 3000])] = 0   # < 0.3 ha
    return lab


def railway_mask(shape, osm_path, box=BLOCK):
    sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
    import prokh_gen as G
    feats, _ = G.load_osm(osm_path)
    im = Image.new('L', shape[::-1], 0); d = ImageDraw.Draw(im)
    for (k, t, p, c) in feats:
        if k == 'line' and t.get('railway') == 'rail' and t.get('usage') == 'main':
            d.line([(x / 4 - box[0], (24576 - y) / 4 - box[1]) for x, y in p], fill=255, width=30)
    return np.asarray(im) > 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sheet'); ap.add_argument('layout'); ap.add_argument('mask_out')
    ap.add_argument('--osm', default='docs/m12_terrain/osm/prokh.osm.json'); ap.add_argument('--review', default=None)
    ap.add_argument('--outer', action='store_true', help='redo only the outer ring of the 9 x 9 block (the centre and its polygons stay)')
    ap.add_argument('--review-outer', default=None); ap.add_argument('--roads', default=None, help='also write the road-ink raster here')
    a = ap.parse_args()
    Image.MAX_IMAGE_PIXELS = None
    sheet = Image.open(a.sheet)
    if a.roads:
        Image.fromarray(road_ink(sheet)).save(a.roads); print('road ink ->', a.roads)
    if a.outer:
        old = np.asarray(Image.open(a.mask_out).convert('L')).copy()
        old, polys = outer(sheet, a, old)
        Image.fromarray(old).save(a.mask_out)
        L = json.load(open(a.layout, encoding='utf-8'))
        keep = [v for v in L.get('villages_1943', []) if 'outer blob' not in v.get('name', '')]
        L['villages_1943'] = keep + polys
        json.dump(L, open(a.layout, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
        print(f'{len(polys)} outer polygons + {len(keep)} kept -> {a.layout}; mask -> {a.mask_out}')
        return
    lab = blobs(sheet)
    if a.review:
        import os; os.makedirs(a.review, exist_ok=True)
        from skimage import measure
        ov = sheet.convert('RGB').crop(BLOCK); d = ImageDraw.Draw(ov, 'RGBA')
        try: font = ImageFont.load_default(size=22)
        except Exception: font = ImageFont.load_default()
        for i, sl in enumerate(ndi.find_objects(lab), 1):
            if sl is None: continue
            m = lab[sl] == i; ys, xs = np.nonzero(m)
            for cnt in measure.find_contours(np.pad(m, 1).astype(float), 0.5):
                pts = [(x + sl[1].start - 1, y + sl[0].start - 1) for y, x in cnt[::3]]
                if len(pts) > 2: d.polygon(pts, outline=(255, 0, 255, 255), fill=(255, 0, 255, 40))
            d.text((xs.mean() + sl[1].start - 12, ys.mean() + sl[0].start - 12), str(i), fill=(0, 120, 0, 255), font=font)
        for X in range(0, 15): d.line([(X * 256, 0), (X * 256, ov.size[1])], fill=(0, 0, 0, 60))
        for Y in range(0, 11): d.line([(0, Y * 256), (ov.size[0], Y * 256)], fill=(0, 0, 0, 60))
        for ty in range(3):
            for tx in range(4):
                x = tx * 896; y = ty * 853
                ov.crop((x, y, min(x + 1024, ov.size[0]), min(y + 1024, ov.size[1]))).save(os.path.join(a.review, f'rv_{ty}{tx}.png'))
        print('review tiles written to', a.review)
    mask = np.isin(lab, KEEP)
    mask &= ~railway_mask(mask.shape, a.osm)
    Y, X = np.mgrid[0:mask.shape[0], 0:mask.shape[1]]; Xs = X / 256.0; Ys = Y / 256.0
    for bid, f in CUTS: mask &= ~((lab == bid) & f(Xs, Ys))
    mask = ndi.binary_opening(mask, iterations=2)
    lab2, n2 = ndi.label(mask); sizes = ndi.sum(mask, lab2, range(1, n2 + 1))
    mask &= ~np.isin(lab2, [i + 1 for i, s in enumerate(sizes) if s * 16 < 3000])
    print('built-up 1941: %.2f %% of the block' % (100 * mask.mean()))
    # trim mask (whole 11 x 12 lattice canvas; outside the block the old content stays)
    try: old = np.asarray(Image.open(a.mask_out)).copy()
    except Exception: old = np.zeros((sheet.size[1], sheet.size[0]), np.uint8)
    old[BLOCK[1]:BLOCK[3], BLOCK[0]:BLOCK[2]] = np.where(mask, 255, 0).astype(np.uint8)
    Image.fromarray(old).save(a.mask_out)
    # polygons
    from skimage import measure
    vm = ndi.binary_erosion(mask & ~np.isin(lab, MASK_ONLY), iterations=10)
    lab3, n3 = ndi.label(vm); polys = []
    for i, sl in enumerate(ndi.find_objects(lab3), 1):
        m = lab3[sl] == i
        if m.sum() * 16 < 2000: continue
        ids, cnt = np.unique(lab[sl][m], return_counts=True); src = int(ids[np.argmax(cnt)])
        for cnt_ in measure.find_contours(np.pad(m, 1).astype(float), 0.5):
            poly = measure.approximate_polygon(np.array([(x + sl[1].start - 1, y + sl[0].start - 1) for y, x in cnt_]), tolerance=2.0)
            if len(poly) < 3: continue
            dem = [[int(round((x + BLOCK[0]) * 4)), int(round(24576 - (y + BLOCK[1]) * 4))] for x, y in poly]
            area = abs(sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(dem, dem[1:] + dem[:1]))) / 2
            if area >= 3000: polys.append(dict(name=f"{NAMES.get(src, '1941 built-up blob %d' % src)} (RKKA 1:100 000 sheet, blob {src})", pts=dem))
    L = json.load(open(a.layout, encoding='utf-8'))
    hand = [v for v in L.get('villages_1943', []) if 'RKKA 1:100 000 sheet, blob' not in v.get('name', '')]
    L['villages_1943'] = hand + polys
    json.dump(L, open(a.layout, 'w', encoding='utf-8'), indent=1)
    print(f'{len(polys)} sheet polygons + {len(hand)} hand-traced -> {a.layout}; mask -> {a.mask_out}')


if __name__ == '__main__':
    main()

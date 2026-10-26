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


def blobs(sheet):
    """black-ink density blobs of the block: label image, ids as reviewed"""
    rk = np.asarray(sheet.convert('RGB').crop(BLOCK)).astype(int)
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


def railway_mask(shape, osm_path):
    sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
    import prokh_gen as G
    feats, _ = G.load_osm(osm_path)
    im = Image.new('L', shape[::-1], 0); d = ImageDraw.Draw(im)
    for (k, t, p, c) in feats:
        if k == 'line' and t.get('railway') == 'rail' and t.get('usage') == 'main':
            d.line([(x / 4 - BLOCK[0], (24576 - y) / 4 - BLOCK[1]) for x, y in p], fill=255, width=30)
    return np.asarray(im) > 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sheet'); ap.add_argument('layout'); ap.add_argument('mask_out')
    ap.add_argument('--osm', default='docs/m12_terrain/osm/prokh.osm.json'); ap.add_argument('--review', default=None)
    a = ap.parse_args()
    sheet = Image.open(a.sheet)
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

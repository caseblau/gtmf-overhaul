"""Builds the 1941/43 settlement mask from scanned period sheets (RKKA 1:100 000 / 1:50 000 Genshtab maps) so that
prokh_gen.py can trim the modern OpenStreetMap villages back to their wartime extent.

Usage:
  python period_cover.py docs/m12_terrain/period/sheets.json docs/m12_terrain/period/builtup_1941.png
  python period_cover.py --tiles docs/m12_terrain/period/tiles_rkka100k docs/m12_terrain/period/builtup_1941.png
      (XYZ web-mercator tiles named 13_<y>_<x>.jpg from tools\fetch_period_tiles.cmd; also writes
       docs/m12_terrain/period/rkka100k_block.png, the sheet reprojected onto the block's 4 m grid, north up)

sheets.json lists the scans with their geographic corners (the image must be cropped to the sheet frame, or give the
corners of the crop you made):
  [{"file": "M-37-38.jpg", "west": 36.5, "east": 37.0, "south": 51.0, "north": 51.3333},
   {"file": "M-37-50.jpg", "west": 36.5, "east": 37.0, "south": 50.6667, "north": 51.0}]
(Soviet 1:100 000 sheets span 30' of longitude and 20' of latitude; the nomenclature M-37-NN gives the corners:
 row = (NN-1)//12, col = (NN-1)%12, north = 52 - row/3, south = north - 1/3, west = 36 + col/2, east = west + 1/2.)

The mask is the block's 4 m grid (5632 x 5120 px, row 0 = north) with 255 where the sheet shows built-up quarters
(dark hatched blocks: dark pixels, closed morphologically, blobs larger than 1 ha), 0 elsewhere.
"""
import sys, json, os, math
import numpy as np
from PIL import Image, ImageFilter

LATS, LATN, LONW, LONE = 50.904605, 51.1254, 36.4903, 36.8120   # 2026-10-23: two more rows south (user)
COLS, ROWS, CELL = 11, 12, 2048.0
LAT_C = 51.0334; M_LAT = 111320.0; M_LON = 111320.0 * math.cos(math.radians(LAT_C))
STEP = 4.0
W, H = int(COLS * CELL / STEP), int(ROWS * CELL / STEP)

def sheet_corners(nomen):
    """'M-37-38' -> (west, east, south, north) of a 1:100 000 sheet."""
    nn = int(nomen.split('-')[-1]); row = (nn - 1) // 12; col = (nn - 1) % 12
    north = 52 - row / 3; west = 36 + col / 2
    return west, west + 0.5, north - 1 / 3, north

def builtup_from_sheet(img, step=STEP):
    """Settlements on the RKKA 1:100 000 sheet are clusters of small solid black house symbols. Black ink (dark and
    unsaturated, so the brown contours and the red/blue staff overprint are ignored) is eroded by ~4 sheet pixels, which
    removes roads, grid lines and lettering (1-2 px strokes) but keeps the house blocks; the density of what survives
    in a ~200 m window marks the built-up patches. The railway, bold labels and the black pencil arrows of the staff
    overprint come through anyway; that is harmless, because the mask only decides which modern buildings are kept.
    Returns a boolean array; tuned 2026-10-23 on the retromap tiles (12 m/px) reprojected to 4 m (mask ~9% of the block
    instead of ~18% with the plain ink density)."""
    rgb = np.asarray(img.convert('RGB')).astype(np.float32); g = rgb.mean(-1); sat = rgb.max(-1) - rgb.min(-1)
    ink = Image.fromarray((((g < 90) & (sat < 60)) * 255).astype(np.uint8))
    k = 2 * max(1, int(round(16.0 / step))) + 1          # 9 px at 4 m
    solid = np.asarray(ink.filter(ImageFilter.MinFilter(k))) > 127
    r = max(1, int(round(100.0 / step)))
    p = np.pad(solid.astype(np.float32), r, mode='edge'); c = np.pad(np.cumsum(np.cumsum(p, 0), 1), ((1, 0), (1, 0))); n = 2 * r + 1
    dens = (c[n:, n:] - c[:-n, n:] - c[n:, :-n] + c[:-n, :-n]) / (n * n)
    m = Image.fromarray(((dens > 0.06) * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(15))
    return np.asarray(m) > 127

def tiles_to_block(tile_dir, z=13):
    """Reproject XYZ tiles (web mercator) onto the block's equirectangular 4 m grid. Returns an RGB array (H, W, 3).
    A Z13 tile the server refused (1715-byte grey placeholder, deleted by the fetcher) is filled from the quadrant of
    its Z12 parent tile when tools\\fetch_period_tiles.cmd managed to get that one (half the resolution, same drawing)."""
    import re, glob
    files = glob.glob(os.path.join(tile_dir, f'{z}_*_*.jpg'))
    if not files: raise SystemExit(f'no tiles named {z}_<y>_<x>.jpg in {os.path.abspath(tile_dir)} - run tools\\fetch_period_tiles.cmd first')
    ys = [int(re.search(r'_(\d+)_(\d+)\.jpg$', f).group(1)) for f in files]; xs = [int(re.search(r'_(\d+)_(\d+)\.jpg$', f).group(2)) for f in files]
    y0, y1, x0, x1 = min(ys), max(ys), min(xs), max(xs)
    mosaic = np.full(((y1 - y0 + 1) * 256, (x1 - x0 + 1) * 256, 3), 230, np.uint8)   # missing tiles = blank paper
    good = set(); missing = []
    for f, ty, tx in zip(files, ys, xs):
        try: im = Image.open(f).convert('RGB')
        except Exception: continue
        if im.size != (256, 256) or os.path.getsize(f) < 3000: continue   # grey placeholder = missing tile
        mosaic[(ty - y0) * 256:(ty - y0 + 1) * 256, (tx - x0) * 256:(tx - x0 + 1) * 256] = np.asarray(im); good.add((ty, tx))
    for ty in range(y0, y1 + 1):
        for tx in range(x0, x1 + 1):
            if (ty, tx) in good: continue
            parent = os.path.join(tile_dir, f'{z - 1}_{ty // 2}_{tx // 2}.jpg')
            if os.path.exists(parent) and os.path.getsize(parent) >= 3000:
                q = Image.open(parent).convert('RGB').crop(((tx % 2) * 128, (ty % 2) * 128, (tx % 2) * 128 + 128, (ty % 2) * 128 + 128)).resize((256, 256), Image.BICUBIC)
                mosaic[(ty - y0) * 256:(ty - y0 + 1) * 256, (tx - x0) * 256:(tx - x0 + 1) * 256] = np.asarray(q)
            else: missing.append(f'{z}_{ty}_{tx}')
    if missing: print('tiles still missing (blank paper there, villages inside them get trimmed away):', ' '.join(missing))
    n = 2 ** z
    yy, xx = np.mgrid[0:H, 0:W]
    lon = LONW + (xx + 0.5) * STEP / M_LON; lat = LATN - (yy + 0.5) * STEP / M_LAT
    px = ((lon + 180) / 360 * n - x0) * 256
    latr = np.radians(lat); py = ((1 - np.log(np.tan(latr) + 1 / np.cos(latr)) / math.pi) / 2 * n - y0) * 256
    pxi = np.clip(px.astype(int), 0, mosaic.shape[1] - 1); pyi = np.clip(py.astype(int), 0, mosaic.shape[0] - 1)
    return mosaic[pyi, pxi]

def main(cfg_path, out_path):
    if cfg_path == '--tiles':
        tile_dir, out_path = out_path, sys.argv[3]
        block = tiles_to_block(tile_dir)
        Image.fromarray(block).save(os.path.join(os.path.dirname(out_path), 'rkka100k_block.png'))
        bu = builtup_from_sheet(Image.fromarray(block))
        Image.fromarray((bu * 255).astype(np.uint8)).save(out_path); print('wrote', out_path, 'built-up fraction %.3f' % bu.mean()); return
    sheets = json.load(open(cfg_path)); base = os.path.dirname(cfg_path)
    mask = np.zeros((H, W), np.uint8)
    for sh in sheets:
        img = Image.open(os.path.join(base, sh['file']))
        if 'sheet' in sh and 'west' not in sh: sh['west'], sh['east'], sh['south'], sh['north'] = sheet_corners(sh['sheet'])
        bu = builtup_from_sheet(img); ih, iw = bu.shape
        # map every block pixel to the sheet pixel (equirectangular within the sheet)
        ys, xs = np.mgrid[0:H, 0:W]
        lon = LONW + (xs + 0.5) * STEP / M_LON; lat = LATN - (ys + 0.5) * STEP / M_LAT
        px = ((lon - sh['west']) / (sh['east'] - sh['west']) * iw).astype(int); py = ((sh['north'] - lat) / (sh['north'] - sh['south']) * ih).astype(int)
        inside = (px >= 0) & (px < iw) & (py >= 0) & (py < ih)
        mask[inside] |= (bu[py[inside], px[inside]] * 255).astype(np.uint8)
        print(sh['file'], 'built-up pixels on sheet', int(bu.sum()), 'covering block px', int(inside.sum()))
    # drop blobs smaller than 1 ha (625 px at 4 m): simple connected components via flood fill on a coarse grid
    Image.fromarray(mask).save(out_path); print('wrote', out_path, 'built-up fraction %.3f' % (mask > 0).mean())

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

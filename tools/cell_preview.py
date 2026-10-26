"""Top-down preview of a generated (or vanilla, unpacked) cell: hillshade x soil colour, with plants, objects and
entrenchments drawn on top.  Not the game's rendering - a structural check (fields, roads, villages, works, water).

  python cell_preview.py <cell dir> <out.png> [--scale 2] [--crop x0,y0,w,h]
"""
import sys, os, argparse, struct
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pha6 import decode as pha6_decode
import cellfmt as C

# soil colours (season_ua_summer, roughly as the game shows them in July): GRAS0 MARS1 BLAC2 CLAY3 STON4 SAND5 FIEL6 FIGR7 CONC8 ASPH9 PAVE10 RBAC11 FORG12 LEAV13 TREN14 BUMP15
PAL = np.array([[118, 138, 62], [96, 118, 70], [40, 36, 30], [150, 124, 84], [140, 136, 128], [190, 176, 130], [196, 170, 86], [110, 150, 60],
                [150, 148, 140], [70, 68, 64], [170, 156, 118], [92, 74, 50], [70, 92, 44], [104, 92, 56], [88, 70, 46], [138, 116, 74]], np.float32)
FLORA_COL = {3: (40, 90, 30), 4: (34, 80, 26), 5: (28, 70, 22), 7: (60, 110, 40), 8: (50, 100, 36), 10: (70, 120, 50), 11: (60, 110, 48), 13: (90, 140, 50),
             15: (80, 130, 60), 16: (60, 120, 70), 17: (170, 150, 40), 6: (90, 130, 90), 12: (50, 110, 80), 18: (160, 140, 60), 14: (40, 90, 40)}


def load(cell):
    p = lambda e: os.path.join(cell, f'{e}.cell.loc_def.bin')
    mat = np.fromfile(p('mat_map'), np.uint8).reshape(2048, 2048); soil = mat & 15; hi = mat >> 4
    hu, _ = pha6_decode(p('hei_map')); h = hu.astype(np.float32) * (320.0 / 65535.0)
    h2 = h.reshape(2048, 2, 2048, 2).mean((1, 3))
    fl = C.read_flora(p('flora_quads')) if os.path.exists(p('flora_quads')) else None
    objs = C.read_objects(p('obj_quads')) if os.path.exists(p('obj_quads')) else []
    tr = []
    if os.path.exists(p('trench_pos')):
        b = open(p('trench_pos'), 'rb').read()
        if len(b) >= 4:
            n = struct.unpack_from('<I', b, 0)[0]; off = 4
            for _ in range(n):
                if off + 24 > len(b): break
                tag = b[off:off + 4]; x, y, r = struct.unpack_from('<fff', b, off + 4); tr.append((x, y)); off += 24
    water = None
    if os.path.exists(p('water_levels')):
        w = np.fromfile(p('water_levels'), np.uint8).reshape(512, 512) if os.path.getsize(p('water_levels')) == 262144 else None
        water = w
    return soil, hi, h2, fl, objs, tr, water


def render(cell, out, scale=1, crop=None):
    soil, hi, h2, fl, objs, tr, water = load(cell)
    # hillshade (sun from the NW, rows run south -> north so flip for the picture at the end)
    gy, gx = np.gradient(h2); nz = 1.0 / np.sqrt(1 + gx ** 2 + gy ** 2)
    shade = np.clip(0.55 + 0.45 * (nz * 0.8 - gx * 0.45 * nz + gy * 0.35 * nz), 0.3, 1.2)
    col = PAL[soil]
    v = ((hi.astype(np.float32) - 9.0) * 4.0)[..., None]   # micro tile as a slight brightness variation
    img = np.clip(col * shade[..., None] + v, 0, 255).astype(np.uint8)
    im = Image.fromarray(img); d = ImageDraw.Draw(im)
    if fl is not None:
        x, y, r, t = fl if isinstance(fl, tuple) else (fl['x'], fl['y'], fl['rnd'], fl['typ'])
        for xi, yi, ti in zip(x.astype(int), y.astype(int), t):
            if 0 <= xi < 2048 and 0 <= yi < 2048:
                c = FLORA_COL.get(int(ti), (40, 90, 30)); rr = 2 if ti in (3, 4, 5, 10, 11, 14) else 1
                d.ellipse([xi - rr, yi - rr, xi + rr, yi + rr], fill=c)
    for o in objs:
        tab, node, x, y = o[0], o[1], o[2], o[3]
        if not (0 <= x < 2048 and 0 <= y < 2048): continue
        if 'build' in tab or 'build' in node or 'saray' in node or 'farm' in node: d.rectangle([x - 5, y - 4, x + 5, y + 4], fill=(120, 60, 40), outline=(60, 30, 20))
        elif 'fence' in tab: d.point((x, y), fill=(80, 60, 40))
        elif node == 'rail': d.ellipse([x - 1, y - 1, x + 1, y + 1], fill=(40, 40, 40))
        else: d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(200, 200, 60))
    for (x, y) in tr:
        if 0 <= x < 2048 and 0 <= y < 2048: d.ellipse([x - 2, y - 2, x + 2, y + 2], outline=(230, 40, 40))
    if water is not None:
        wm = Image.fromarray(((water > 0) * 255).astype(np.uint8)).resize((2048, 2048), Image.NEAREST)
        blue = Image.new('RGB', (2048, 2048), (70, 110, 160)); im = Image.composite(blue, im, wm)
    im = im.transpose(Image.FLIP_TOP_BOTTOM)   # north up
    if crop:
        x0, y0, w, h = crop; im = im.crop((x0, y0, x0 + w, y0 + h))
    if scale != 1: im = im.resize((int(im.width * scale), int(im.height * scale)), Image.NEAREST if scale > 1 else Image.BOX)
    im.save(out); return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cell'); ap.add_argument('out'); ap.add_argument('--scale', type=float, default=1); ap.add_argument('--crop', default='')
    a = ap.parse_args()
    crop = tuple(int(v) for v in a.crop.split(',')) if a.crop else None
    sc = a.scale
    render(a.cell, a.out, scale=int(sc) if sc >= 1 else sc, crop=crop)

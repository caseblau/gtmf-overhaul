"""List every off-reference stretch >= 60 m (C1 red) of a roads json, with a crop each (sheet 3x | C1 layers).
  python3 red_stretches.py <roads.json> <outdir>"""
import sys, os, json, importlib.util, numpy as np
from PIL import Image, ImageDraw
Image.MAX_IMAGE_PIXELS = None
spec = importlib.util.spec_from_file_location('ev', '/mnt/user-data/outputs/roadgraph/n1/eval_roads.py')
ev = importlib.util.module_from_spec(spec); spec.loader.exec_module(ev)
RD = '/mnt/user-data/outputs/roadgraph/n1'
dt, _, rok = ev.c1_masks(RD); void = ev.load_mask(RD + '/void.png'); cen = ev.load_mask(RD + '/c1_centre.png')
sheet = Image.open('/mnt/user-data/uploads/gtmf-overhaul/docs/m12_terrain/period/rkka100k_block.png').convert('RGB')
H, W = dt.shape
REG = {'R11': (0, 14336, 6144, 20480), 'R12': (6144, 14336, 12288, 20480), 'R13': (12288, 14336, 18432, 20480),
       'R21': (0, 8192, 6144, 14336), 'R22': (6144, 8192, 12288, 14336), 'R23': (12288, 8192, 18432, 14336),
       'R31': (0, 2048, 6144, 8192), 'R32': (6144, 2048, 12288, 8192), 'R33': (12288, 2048, 18432, 8192)}
def region(x, y): return next(k for k, b in REG.items() if b[0] <= x < b[2] and b[1] <= y < b[3]) if 0 <= x < 18432 and 2048 <= y < 20480 else 'out'
J = json.load(open(sys.argv[1], encoding='utf-8')); out = sys.argv[2]; os.makedirs(out + '/crops', exist_ok=True)
items = []; k = 0
for r in J['roads']:
    p = np.asarray(r['pts'], float)
    if len(p) < 2: continue
    q, w = ev.densify(p, 4.0); px, py = ev.m_to_px(q[:, 0], q[:, 1])
    ix = np.clip(np.round(px).astype(int), 0, W - 1); iy = np.clip(np.round(py).astype(int), 0, H - 1)
    off = ~((dt[iy, ix] <= 8) | rok[iy, ix] | void[iy, ix])
    i = 0
    while i < len(q):
        if not off[i]: i += 1; continue
        j = i
        while j + 1 < len(q) and off[j + 1]: j += 1
        L = w[i:j + 1].sum()
        if L >= 60:
            k += 1; sid = 'S%04d' % k; mid = q[(i + j) // 2]
            cx, cy = int(px[(i + j) // 2]), int(py[(i + j) // 2]); half = int(max(60, min(160, L / 8 + 30)))
            box = (cx - half, cy - half, cx + half, cy + half); sc = 300 / (2 * half)
            a = sheet.crop(box).resize((300, 300), Image.LANCZOS); b = Image.new('RGB', (300, 300), 'white')
            cc = cen[max(0, box[1]):box[3], max(0, box[0]):box[2]]
            if cc.size: b.paste(Image.fromarray((~cc * 255).astype(np.uint8)).convert('RGB').resize((300, 300), Image.NEAREST))
            for im in (a, b):
                d = ImageDraw.Draw(im)
                pp = [((x - box[0]) * sc, (y - box[1]) * sc) for x, y in zip(px, py)]
                d.line(pp, fill=(0, 150, 255), width=1)
                d.line(pp[i:j + 1], fill=(255, 0, 0), width=2)
            c = Image.new('RGB', (604, 320), 'white'); c.paste(a, (0, 20)); c.paste(b, (304, 20))
            ImageDraw.Draw(c).text((4, 4), '%s %s (%s) %.0f m  centre x %.0f y %.0f' % (sid, r.get('name'), r.get('highway'), L, mid[0], mid[1]), fill=(0, 0, 0))
            c.save('%s/crops/%s.png' % (out, sid))
            items.append(dict(id=sid, road=r.get('name'), cls=r.get('highway'), length_m=round(float(L)), x=round(float(mid[0])), y=round(float(mid[1])),
                              region=region(*mid), from_m=[round(float(v), 1) for v in q[i]], to_m=[round(float(v), 1) for v in q[j]], crop='crops/%s.png' % sid))
        i = j + 1
json.dump(items, open(out + '/red.json', 'w'), indent=1)
from collections import defaultdict
agg = defaultdict(lambda: [0, 0])
for it in items: agg[it['region']][0] += 1; agg[it['region']][1] += it['length_m']
print(len(items), 'stretches', sum(it['length_m'] for it in items), 'm'); print({k: (v[0], v[1]) for k, v in sorted(agg.items())})

r"""Trace trench lines painted on an op-map screenshot into the layout's field works.

The user paints the trenches in red on a screenshot of the operation map (the 14 x 10 square grid, 1024 m squares);
this reads the red strokes, thins them to centre lines, converts the pixels to DEM-lattice metres and writes them into
docs/m11_prokhorovka/layout_10jul.json as 'works' entries of type trench (name prefix 'painted'), replacing the previous
painted set.  Anti-tank ditches and other hand-written works entries are kept.

  py -3 tools\trace_paint.py docs\m11_prokhorovka\painted_trenches_25oct.png docs\m11_prokhorovka\layout_10jul.json
        [--grid px_per_square,px_x0,px_y0]   (default: detected from the heavy grid lines every 2 squares)
        [--side USSR] [--check out.png]        (overlay of the traced lines on the screenshot)

Grid: the screenshot must show the map's west and north edges at known pixels, or the heavy 2048 m lines (cell borders)
must be visible - they are detected as the strongest grey peaks every ~2 squares.  Squares: X from the west edge,
Y from the north edge; DEM-lattice metres: x = 4096 + X * 1024, y = 16384 - Y * 1024 (tools/prokh_op.py frame).
"""
import sys, json, argparse, math
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

BLOCK_X0, BLOCK_YTOP, SQ = 4096.0, 16384.0, 1024.0


def detect_grid(im):
    """px per square and the pixel of the west / north edge from the heavy grey lines (every 2 squares)"""
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    grey = (abs(r - g) < 18) & (abs(g - b) < 18) & (r < 175) & (r > 60)
    H, W = grey.shape
    def peaks(v, thr):
        return [i for i in range(1, len(v) - 1) if v[i] >= thr and v[i] >= v[i - 1] and v[i] >= v[i + 1]]
    cols = peaks(grey.sum(0), 0.35 * H); rows = peaks(grey.sum(1), 0.35 * W)
    def spacing(p):
        d = [b_ - a_ for a_, b_ in zip(p, p[1:]) if 150 < b_ - a_ < 400]
        return float(np.median(d)) if d else None
    sc = spacing(cols) or spacing(rows)
    if sc is None: raise SystemExit('grid not found - pass --grid px_per_square,px_x0,px_y0')
    px = sc / 2.0
    # the first heavy line = an even square boundary; assume it is the map edge when it is within half a square of the image edge
    x0 = cols[0] if cols and cols[0] < px else cols[0] - 2 * px * round((cols[0]) / (2 * px))
    y0 = rows[0] if rows and rows[0] < px else rows[0] - 2 * px * round((rows[0]) / (2 * px))
    return px, float(x0), float(y0)


def red_mask(im):
    r, g, b = im[..., 0].astype(int), im[..., 1].astype(int), im[..., 2].astype(int)
    m = (r > 150) & (g < 120) & (b < 120) & (r - g > 60)
    from skimage.morphology import closing, disk
    return closing(m, disk(2))


def skeleton_paths(mask):
    """thin each red blob and decompose its skeleton into polylines (longest path first, then the remaining branches)"""
    from skimage.morphology import skeletonize
    lab, n = ndi.label(mask, structure=np.ones((3, 3)))
    out = []
    for k in range(1, n + 1):
        m = lab == k
        if m.sum() < 25: continue
        ys, xs = np.nonzero(skeletonize(m))
        pts = set(zip(xs.tolist(), ys.tolist()))
        while len(pts) >= 6:
            start = next(iter(pts)); comp = {start}; q = [start]
            for p in q:
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        q2 = (p[0] + dx, p[1] + dy)
                        if (dx or dy) and q2 in pts and q2 not in comp: comp.add(q2); q.append(q2)
            def nb(p): return [(p[0] + dx, p[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx or dy) and (p[0] + dx, p[1] + dy) in comp]
            def bfs(s):
                dist = {s: 0}; prev = {s: None}; qq = [s]
                for p in qq:
                    for q2 in nb(p):
                        if q2 not in dist: dist[q2] = dist[p] + 1; prev[q2] = p; qq.append(q2)
                far = max(dist, key=dist.get); return far, prev
            a, _ = bfs(start); bpt, prev = bfs(a)
            path = []; p = bpt
            while p is not None: path.append(p); p = prev[p]
            path = path[::-1]
            if len(path) >= 6: out.append(path)
            rm = {(x + dx, y + dy) for (x, y) in path for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
            pts -= rm
            if len(path) < 6: pts -= comp
    return out


def smooth_resample(path, win=9, step=6.0):
    P = np.array(path, float)
    if len(P) > win:
        k = np.ones(win) / win
        P = np.stack([np.convolve(np.pad(P[:, i], win // 2, mode='edge'), k, mode='valid') for i in range(2)], 1)
    seg = np.hypot(*np.diff(P, axis=0).T); s = np.concatenate([[0], np.cumsum(seg)]); L = s[-1]
    if L < 7: return None
    ss = np.append(np.arange(0, L, step), L)
    return np.stack([np.interp(ss, s, P[:, i]) for i in range(2)], 1), L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('image'); ap.add_argument('layout')
    ap.add_argument('--grid', default=None, help='px_per_square,px_x0,px_y0'); ap.add_argument('--side', default='USSR')
    ap.add_argument('--check', default=None, help='write an overlay png'); ap.add_argument('--min-m', type=float, default=60.0)
    a = ap.parse_args()
    im = np.asarray(Image.open(a.image).convert('RGB'))
    if a.grid: px, x0, y0 = [float(v) for v in a.grid.split(',')]
    else: px, x0, y0 = detect_grid(im)
    print(f'grid: {px:.2f} px per square, west edge at px {x0:.0f}, north edge at px {y0:.0f}')
    strokes = []
    for path in skeleton_paths(red_mask(im)):
        r = smooth_resample(path)
        if r is None: continue
        rs, L = r
        if L / px * SQ < a.min_m: continue
        pts = [[int(round(BLOCK_X0 + (x - x0) / px * SQ)), int(round(BLOCK_YTOP - (y - y0) / px * SQ))] for x, y in rs]
        strokes.append((pts, L / px * SQ, rs))
    strokes.sort(key=lambda s: (-s[0][0][1], s[0][0][0]))   # north to south
    L = json.load(open(a.layout, encoding='utf-8'))
    kept = [w for w in L.get('works', []) if not str(w.get('name', '')).startswith('painted')]
    new = [dict(type='trench', side=a.side, name=f'painted trench line {i + 1} ({len_m:.0f} m)', pts=pts) for i, (pts, len_m, _) in enumerate(strokes)]
    L['works'] = kept + new
    json.dump(L, open(a.layout, 'w', encoding='utf-8'), indent=1)
    print(f'{len(new)} painted lines, {sum(s[1] for s in strokes) / 1000:.1f} km, written to {a.layout} ({len(kept)} other works kept)')
    if a.check:
        ov = Image.open(a.image).convert('RGB'); d = ImageDraw.Draw(ov)
        for _, _, rs in strokes: d.line([tuple(p) for p in rs.tolist()], fill=(0, 0, 255), width=2)
        ov.save(a.check)


if __name__ == '__main__':
    main()

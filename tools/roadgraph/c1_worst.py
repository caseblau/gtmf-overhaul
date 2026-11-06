#!/usr/bin/env python3
"""C1 sanity crops: python3 c1_worst.py <roads.json> <outdir> [--n 15] [--min-len 300] [--shift-m 0] [--cls secondary]
For the n roads with the lowest C1 share (length >= min-len) a crop round the longest off-ink stretch: left the sheet
(2x), right the C1 layers (grey ink_clean, light blue double-line band, dark green C1 centre lines (c1_centre)) and the road (green
where C1 counts it on ink, red where off).  --shift-m moves every road sideways (synthetic test)."""
import os, sys, json, math, argparse, importlib.util
import numpy as np
from PIL import Image, ImageDraw
Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('ev', os.path.join(HERE, 'eval_roads.py')); ev = importlib.util.module_from_spec(spec); spec.loader.exec_module(ev)
SHEET = '/mnt/user-data/uploads/gtmf-overhaul/docs/m12_terrain/period/rkka100k_block.png'

def shift(p, d):
    if d == 0: return p
    t = np.gradient(p, axis=0); t /= np.maximum(np.hypot(*t.T), 1e-9)[:, None]
    return p + np.c_[-t[:, 1], t[:, 0]] * d

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('roads'); ap.add_argument('outdir')
    ap.add_argument('--n', type=int, default=15); ap.add_argument('--min-len', type=float, default=300); ap.add_argument('--shift-m', type=float, default=0); ap.add_argument('--cls', default=None)
    a = ap.parse_args(); os.makedirs(a.outdir, exist_ok=True)
    ink = ev.load_mask(os.path.join(HERE, 'ink_clean.png')); dbl = ev.load_mask(os.path.join(HERE, 'c1_centre.png'))
    band = ev.load_mask(os.path.join(HERE, 'dbl_band.png')); void = ev.load_mask(os.path.join(HERE, 'void.png'))
    dt_ink, dt_sec, res_ok = ev.c1_masks(HERE)
    sheet = np.asarray(Image.open(SHEET).convert('RGB'))
    J = json.load(open(a.roads, encoding='utf-8')); rows = []
    for k, r in enumerate(J['roads']):
        if a.cls and r.get('highway') != a.cls: continue
        p = shift(np.asarray(r['pts'], float), a.shift_m)
        q, w = ev.densify(p, 2.0)
        px, py = ev.m_to_px(q[:, 0], q[:, 1]); ix = np.clip(np.round(px).astype(int), 0, ink.shape[1] - 1); iy = np.clip(np.round(py).astype(int), 0, ink.shape[0] - 1)
        cls = r.get('highway', '')
        d = dt_sec[iy, ix] if cls == 'secondary' else dt_ink[iy, ix]
        on = d <= ev.TOL_C1
        on |= res_ok[iy, ix]
        sc = ~void[iy, ix]
        L = w[sc].sum()
        if L < a.min_len: continue
        rows.append((float(w[sc & on].sum() / L), str(r.get('name', k)), cls, L, q, on))
    rows.sort(key=lambda t: (t[0], t[1]))
    idx = ['# C1: lowest on-ink roads', '', '| # | road | class | length m | on-ink | crop |', '|---|---|---|---|---|---|']
    for n_, (s, name, cls, L, q, on) in enumerate(rows[:a.n]):
        # longest off stretch
        best = (0, 0, 0); i = 0
        while i < len(on):
            if not on[i]:
                j = i
                while j < len(on) and not on[j]: j += 1
                if j - i > best[0]: best = (j - i, i, j)
                i = j
            else: i += 1
        mid = q[(best[1] + best[2]) // 2] if best[0] else q[len(q) // 2]
        cx, cy = ev.m_to_px(*mid); H = 100
        x0, y0 = int(cx) - H, int(cy) - H
        raw = sheet[max(0, y0):y0 + 2 * H, max(0, x0):x0 + 2 * H]
        if raw.shape[0] < 2 * H or raw.shape[1] < 2 * H:
            pad = np.full((2 * H, 2 * H, 3), 255, np.uint8); pad[:raw.shape[0], :raw.shape[1]] = raw; raw = pad
        sl = np.s_[max(0, y0):y0 + 2 * H, max(0, x0):x0 + 2 * H]
        o = np.full((2 * H, 2 * H, 3), 255, np.uint8)
        for m, col in ((band, (205, 225, 255)), (ink, (160, 160, 160)), (dbl, (0, 120, 0))):
            mm = np.zeros((2 * H, 2 * H), bool); sub = m[sl]; mm[:sub.shape[0], :sub.shape[1]] = sub; o[mm] = col
        Lp = Image.fromarray(raw).resize((400, 400), Image.LANCZOS); Rp = Image.fromarray(o).resize((400, 400), Image.NEAREST)
        dr = ImageDraw.Draw(Rp); dl = ImageDraw.Draw(Lp)
        P = [((ev.m_to_px(x, y)[0] - x0) * 2, (ev.m_to_px(x, y)[1] - y0) * 2) for x, y in q]
        for (u, v), (u2, v2), o_ in zip(P[:-1], P[1:], on[:-1]):
            dr.line([(u, v), (u2, v2)], fill=(0, 200, 0) if o_ else (230, 0, 0), width=2)
            dl.line([(u, v), (u2, v2)], fill=(255, 0, 255), width=1)
        im = Image.new('RGB', (806, 420), 'white'); im.paste(Lp, (0, 20)); im.paste(Rp, (406, 20))
        ImageDraw.Draw(im).text((2, 2), '%s (%s) %.0f m  C1 %.1f %%  crop centre x %.0f y %.0f' % (name, cls, L, 100 * s, mid[0], mid[1]), fill=(0, 0, 0))
        fn = '%02d_%s.png' % (n_ + 1, name); im.save(os.path.join(a.outdir, fn))
        idx.append('| %d | %s | %s | %.0f | %.1f %% | %s |' % (n_ + 1, name, cls, L, 100 * s, fn))
    open(os.path.join(a.outdir, 'index.md'), 'w').write('\n'.join(idx) + '\n')
    print('\n'.join(idx[4:]))

if __name__ == '__main__':
    main()

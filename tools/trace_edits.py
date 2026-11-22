r"""Hand corrections of the period traces of a block (M16 step 2; user 11 Nov 2026: "automatic draft plus area-by-area
correction ... keep working on it until it's 1 to 1 with the maps").

docs/<block>/period/trace_edits.json, one entry per reviewed area (the review tiles of tools/trace_review.py):
  {"areas": {"<area>": {"done": true, "note": "...",
       "roads_add":   [{"highway": "secondary|track|path", "px": [[x, y], ...]}],
       "roads_drop":  [{"px": [[x, y], ...], "tol": 12}],          # roads lying along this polyline (within tol px) go
       "roads_class": [{"px": [[x, y], ...], "tol": 12, "highway": "track"}],
       "houses_add":  [{"px": [x, y], "w": 12, "d": 8, "ang": 0}],  # w, d metres, ang degrees (image, clockwise)
       "houses_drop": [[x0, y0, x1, y1]],                           # boxes, px
       "yards_add":   [[[x, y], ...]], "yards_drop": [[[x, y], ...]] }}}
px = pixels of the 2 m period mosaics (wig_block.png), x right, y down; block metres x = 2 px, y = 2 (n - py).
apply_roads / apply_houses / apply_yards are used by tools/prokh_gen.py and tools/trace_review.py.
"""
import os, json
import numpy as np
STEP = 2.0

def load(pdir):
    p = os.path.join(pdir, 'trace_edits.json')
    if not os.path.exists(p): return {'areas': {}}
    return json.load(open(p, encoding='utf-8'))

def _m(px, n): return [[round(x * STEP, 1), round((n - y) * STEP, 1)] for x, y in px]

def _along(pts_m, line_px, tol, n):
    """share of a road's points within tol px of a polyline (px)"""
    L = np.array(line_px, float); P = np.array([(x / STEP, n - y / STEP) for x, y in pts_m], float)
    if len(L) < 2 or len(P) == 0: return 0.0
    a = L[:-1][None]; b = L[1:][None]; p = P[:, None]
    ab = b - a; t = np.clip(((p - a) * ab).sum(-1) / np.maximum((ab * ab).sum(-1), 1e-9), 0, 1)
    d = np.hypot(*(p - (a + t[..., None] * ab)).transpose(2, 0, 1)).min(1)
    return float((d <= tol).mean())

def apply_roads(roads, E, n):
    out = list(roads)
    for name, A in E.get('areas', {}).items():
        for poly in A.get('roads_drop_area', []):   # every traced road mostly inside the polygon (px) goes (a town traced by hand)
            from matplotlib.path import Path as MP_
            pp = MP_(np.array(poly, float))
            def inside_share(r):
                P = np.array([(x / STEP, n - y / STEP) for x, y in r['pts']]); return pp.contains_points(P).mean()
            out = [r for r in out if r.get('source') == 'edit' or inside_share(r) < 0.5]
        for d in A.get('roads_drop', []):
            out = [r for r in out if _along(r['pts'], d['px'], d.get('tol', 12), n) < 0.6]
        for c in A.get('roads_class', []):
            for r in out:
                if _along(r['pts'], c['px'], c.get('tol', 12), n) >= 0.6: r['highway'] = c['highway']
        for r in A.get('roads_add', []):   # a road added by hand replaces the traced ones along it
            out = [q for q in out if q.get('source') == 'edit' or _along(q['pts'], r['px'], 16, n) < 0.5]
        for k, r in enumerate(A.get('roads_add', [])):
            out.append(dict(id='e_%s_%d' % (name, k), highway=r['highway'], source='edit', pts=_m(r['px'], n),
                            length_m=int(sum(np.hypot(*np.diff(np.array(r['px'], float), axis=0).T)) * STEP)))
    for r in out: r['pts'] = despike(r['pts'])
    return [r for r in out if _len(r['pts']) >= 24]     # stubs under 24 m: snapping leftovers at junctions, not roads

def _len(pts):
    P = np.asarray(pts, float); return float(np.hypot(*np.diff(P, axis=0).T).sum()) if len(P) > 1 else 0.0

def despike(pts, leg=50.0):
    """remove the V-notches the snapping leaves on a line (m): a vertex b where the line turns by > 60 degrees with both legs
    under `leg` m while it turns the other way at both neighbours and comes back near its heading (within 0.6 of the turn: a notch); a vertex
    where it doubles back (> 110 degrees) on legs under `leg` m. A real corner is one turn, and is kept."""
    P = [tuple(q) for q in pts]
    def turn(k):
        a, b, c = np.array(P[k - 1]), np.array(P[k]), np.array(P[k + 1])
        u, v = b - a, c - b; lu, lv = np.hypot(*u), np.hypot(*v)
        if lu < 1e-6 or lv < 1e-6: return 0.0, lu, lv
        return float(np.degrees(np.arctan2(u[0] * v[1] - u[1] * v[0], u @ v))), lu, lv
    ch = True
    while ch and len(P) > 2:
        ch = False
        for k in range(1, len(P) - 1):
            t, lu, lv = turn(k)
            if lu < 1e-6 or lv < 1e-6: del P[k]; ch = True; break
            if lu >= leg or lv >= leg: continue
            if abs(t) > 110: del P[k]; ch = True; break
            if abs(t) > 60 and 1 < k < len(P) - 2:
                tp, tn = turn(k - 1)[0], turn(k + 1)[0]
                if np.sign(tp) == -np.sign(t) and np.sign(tn) == -np.sign(t) and abs(tp + t + tn) < 0.6 * abs(t):
                    del P[k]; ch = True; break
    return [list(q) for q in P]

def apply_houses(houses, E, n):
    out = list(houses)
    for name, A in E.get('areas', {}).items():
        for x0, y0, x1, y1 in A.get('houses_drop', []):
            out = [h for h in out if not (x0 <= h['px'][0] <= x1 and y0 <= h['px'][1] <= y1)]
        for h in A.get('houses_add', []):
            x, y = h['px']
            out.append(dict(x=round(x * STEP, 1), y=round((n - y) * STEP, 1), w=h.get('w', 12.0), d=h.get('d', 8.0), ang=h.get('ang', 0.0),
                            area=h.get('w', 12.0) * h.get('d', 8.0), yard=False, px=[int(x), int(y)], source='edit'))
    return out

def apply_yards(mask4, E, n):
    """mask4: the farmyard mask at 4 m (row 0 = north); polygons in 2 m px"""
    from PIL import Image, ImageDraw
    im = Image.fromarray((mask4 > 0).astype(np.uint8) * 255); d = ImageDraw.Draw(im)
    for name, A in E.get('areas', {}).items():
        for poly in A.get('yards_add', []): d.polygon([(x / 2.0, y / 2.0) for x, y in poly], fill=255)
        for poly in A.get('yards_drop', []): d.polygon([(x / 2.0, y / 2.0) for x, y in poly], fill=0)
    return np.asarray(im) > 0

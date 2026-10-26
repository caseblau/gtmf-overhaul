"""One water surface for the whole Psel (25 Oct, user: 'the Psel looks bad' - terraced slabs, walls between them, water
sheets lying on the slopes).

The first water pass set the level per cell from a 100 m running minimum of the DEM + 0.3 m. On the 30 m Copernicus DEM
that minimum jumps by metres from one 100 m window to the next (trees, banks, noise), so one cell got 39 levels over
9 m: the engine draws every level as a flat slab with a vertical wall where it meets the next one - the stairs in the
screenshots - and branches of the OSM water polygon that climb a gully side got their own higher slab lying on the
slope. A river surface only ever falls downstream, and the Psel falls ~0.3 m/km here.

So the level is computed ONCE for the whole block, along the river: the water pixels on a 16 m grid, the local DEM
minimum at each, a walk from the highest end downstream (Dijkstra distance inside the water), and the level = the
running minimum of those minima in walk order, quantised to 0.5 m - monotone, the same on both sides of a cell border,
and changing in steps of 0.5 m a few times per cell instead of 39 times. Water pixels whose ground stands more than
LIFT_MAX above that level (the climbing branches) are given back as wet meadow. prokh_gen then carves the channel
under the level and lifts the banks above it, so the water plane is only seen inside the channel.
"""
import math
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

G = 16.0          # grid, metres
STEP = 0.5        # level quantum (m)
LIFT_MAX = 1.8    # a water pixel whose local ground is more than this above the river level becomes wet meadow
FREEBOARD = 0.3   # level above the local channel ground (the old pass used the same)

LEVEL = None      # (level grid, x0, y0) in old-frame metres, row 0 = south
DRY = None


def build(feats, water_of, heights, x0, y0, w, h):
    """feats: OSM features (old-frame metres); water_of(kind, tags) -> line width m (> 0) or 0 for water lines, True for
    water areas; heights(x, y) -> DEM height (vectorised, old-frame metres). The area x0..x0+w, y0..y0+h."""
    global LEVEL, DRY
    nx, ny = int(math.ceil(w / G)), int(math.ceil(h / G))
    img = Image.new('L', (nx, ny), 0); d = ImageDraw.Draw(img)
    riv = Image.new('L', (nx, ny), 0); dr_ = ImageDraw.Draw(riv)   # the river / stream lines themselves: never 'dry'
    def px(p): return [((x - x0) / G, ny - 1 - (y - y0) / G) for x, y in p]
    for kind, t, p, closed in feats:
        r = water_of(kind, t)
        if not r: continue
        if kind == 'area': d.polygon(px(p), fill=1)
        else: d.line(px(p), fill=1, width=max(1, int(round(r / G)))); dr_.line(px(p), fill=1, width=max(1, int(round(r / G))))
    wm = np.asarray(img)[::-1] > 0                    # row 0 = south
    if not wm.any(): LEVEL = None; return 0
    yy, xx = np.mgrid[0:ny, 0:nx]
    hg = heights(x0 + (xx + 0.5) * G, y0 + (yy + 0.5) * G).astype(np.float32)
    wd = ndi.binary_dilation(wm, iterations=1)        # the 16 m raster breaks thin channels: one pixel of slack
    m = ndi.minimum_filter(np.where(wd, hg, np.inf), size=5)   # local channel ground: lowest DEM within 32 m
    m = np.where(np.isfinite(m), m, hg)
    lvl = np.full(wd.shape, np.nan, np.float32)
    lab, nl = ndi.label(wd, structure=np.ones((3, 3)))
    for k in range(1, nl + 1):
        ys, xs = np.nonzero(lab == k)
        if len(ys) < 3: lvl[ys, xs] = m[ys, xs]; continue
        idx = -np.ones(wd.shape, np.int64); idx[ys, xs] = np.arange(len(ys))
        rows, cols, wts = [], [], []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0: continue
                y2, x2 = ys + dy, xs + dx
                ok = (y2 >= 0) & (y2 < ny) & (x2 >= 0) & (x2 < nx)
                j = np.full(len(ys), -1); j[ok] = idx[y2[ok], x2[ok]]
                ok &= j >= 0
                rows.append(np.nonzero(ok)[0]); cols.append(j[ok]); wts.append(np.full(ok.sum(), math.hypot(dx, dy)))
        A = csr_matrix((np.concatenate(wts), (np.concatenate(rows), np.concatenate(cols))), shape=(len(ys), len(ys)))
        mv = m[ys, xs]
        # the two ends of the river: double sweep (farthest from any pixel, then farthest from that); the higher end
        # (mean ground of the 30 pixels nearest it) is upstream. Side branches and oxbows are never picked as ends.
        d0 = dijkstra(A, indices=0); d0[~np.isfinite(d0)] = -1; a = int(np.argmax(d0))
        da = dijkstra(A, indices=a); da[~np.isfinite(da)] = -1; b = int(np.argmax(da))
        db = dijkstra(A, indices=b); db[~np.isfinite(db)] = -1
        ha = mv[np.argsort(np.where(da >= 0, da, 1e9))[:30]].mean(); hb = mv[np.argsort(np.where(db >= 0, db, 1e9))[:30]].mean()
        src = a if ha >= hb else b
        dist = dijkstra(A, indices=src)
        dist[~np.isfinite(dist)] = dist[np.isfinite(dist)].max() + 1
        order = np.argsort(dist, kind='stable')
        run = np.minimum.accumulate(mv[order])
        lv = np.empty(len(ys), np.float32); lv[order] = run
        lvl[ys, xs] = lv
    lvl = np.floor((lvl + FREEBOARD) / STEP) * STEP        # quantised; floor keeps the surface at or under the bank
    # 26 Oct (user: a stretch of the Psel was a dry trench): the dry test is for OSM water POLYGONS climbing a gully side;
    # the river line itself always carries water (prokh_gen carves the bed down to the level)
    rv = ndi.binary_dilation(np.asarray(riv)[::-1] > 0, iterations=1)
    dry = wd & (m - lvl > LIFT_MAX) & ~rv
    # extend the level field 400 m beyond the water (nearest water pixel), so the cells can look it up at any bank pixel
    filled = ~np.isnan(lvl)
    _, (iy, ix) = ndi.distance_transform_edt(~filled, return_indices=True)
    lvl_ext = lvl[iy, ix]
    LEVEL = (lvl_ext.astype(np.float32), x0, y0); DRY = (dry, x0, y0)
    return int(len(np.unique(lvl[filled])))


def sample(grid, xs, ys):
    """nearest lookup of a 16 m grid at old-frame metres"""
    a, x0, y0 = grid
    c = np.clip(((xs - x0) / G).astype(np.int64), 0, a.shape[1] - 1); r = np.clip(((ys - y0) / G).astype(np.int64), 0, a.shape[0] - 1)
    return a[r, c]

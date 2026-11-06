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
4 Nov (user's screenshot: a vertical wall of water across the Psel where two cells meet). The running minimum walked the
whole water network from ONE source in order of distance from it, so on a river with tributaries (the Olshanka joins
the Psel at the west edge, the Solotinka at the block's corner) the branches were interleaved: the Olshanka got the
Psel's downstream minimum (164 m on ground of 172-176 m), and the main stem fell in big steps wherever the 30 m DEM had a
dip - 191 -> 188 m and 182.5 -> 179.5 m in single 3 m walls, one of them at the corner of four cells - plus a step at
every 0.5 m quantum. Now the levels come from the river NETWORK: the river lines are a graph (16 m nodes, tributary
ends joined to the stem), the outlet is its lowest end, every node's ground is the robust (median, +-250 m along the
river) channel minimum, and the level is the running minimum from upstream (lifted by UPPER_W of the gap to the running maximum from
downstream), never falling faster than MAX_FALL - monotone along every branch, continuous at the confluences, a sharp
dip of the DEM spread over the reach above it instead of a wall. The water
pixels take the level of the nearest river node. The quantum is the finest of 0.1 / 0.2 / 0.25 / 0.5 m that leaves
every cell <= 63 levels (the water_pal limit), chosen once for the whole block, and prokh_gen uses the values as they are
(it used to re-round per cell, which could give two neighbouring cells different quanta).
"""

import math
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

G = 16.0          # grid, metres
STEP = 0.5        # level quantum (m); build() picks the finest of 0.1 / 0.2 / 0.25 / 0.5 that fits 63 levels per cell
LIFT_MAX = 1.8    # a water pixel whose local ground is more than this above the river level becomes wet meadow
FREEBOARD = 0.3   # level above the local channel ground (the old pass used the same) - ponds
UPPER_W = 0.15     # level = running minimum from upstream + this share of the gap to the running maximum from downstream
MAX_FALL = 0.002   # m per m along the river (2 m/km; the DEM gives the Psel ~1.1 m/km over the block)
FREEBOARD_NET = 0.1   # river network: the level is already a robust mean of the channel ground, not its minimum

LEVEL = None      # (level grid, x0, y0) in old-frame metres, row 0 = south
DRY = None
RAW = [None]      # the levels on the water pixels only (NaN elsewhere), for checks


def build(feats, water_of, heights, x0, y0, w, h, cell=2048.0):
    """feats: OSM features (old-frame metres); water_of(kind, tags) -> line width m (> 0) or 0 for water lines, True for
    water areas; heights(x, y) -> DEM height (vectorised, old-frame metres). The area x0..x0+w, y0..y0+h."""
    global LEVEL, DRY, STEP
    from scipy.spatial import cKDTree
    nx, ny = int(math.ceil(w / G)), int(math.ceil(h / G))
    img = Image.new('L', (nx, ny), 0); d = ImageDraw.Draw(img)
    riv = Image.new('L', (nx, ny), 0); dr_ = ImageDraw.Draw(riv)   # the river / stream lines themselves: never 'dry'
    def px(p): return [((x - x0) / G, ny - 1 - (y - y0) / G) for x, y in p]
    lines = []
    for kind, t, p, closed in feats:
        r = water_of(kind, t)
        if not r: continue
        if kind == 'area': d.polygon(px(p), fill=1)
        else:
            d.line(px(p), fill=1, width=max(1, int(round(r / G)))); dr_.line(px(p), fill=1, width=max(1, int(round(r / G))))
            lines.append(p)
    wm = np.asarray(img)[::-1] > 0                    # row 0 = south
    if not wm.any(): LEVEL = None; return 0
    yy, xx = np.mgrid[0:ny, 0:nx]
    hg = heights(x0 + (xx + 0.5) * G, y0 + (yy + 0.5) * G).astype(np.float32)
    wd = ndi.binary_dilation(wm, iterations=1)        # the 16 m raster breaks thin channels: one pixel of slack
    m = ndi.minimum_filter(np.where(wd, hg, np.inf), size=5)   # local channel ground: lowest DEM within 32 m
    m = np.where(np.isfinite(m), m, hg)
    lvl = np.full(wd.shape, np.nan, np.float32)
    # ---- the river network: nodes every G m along the river lines inside the area (+ 200 m)
    P, own, pos = [], [], []
    for li, p in enumerate(lines):
        q = np.asarray(p, np.float64)
        if len(q) < 2: continue
        seg = np.hypot(*np.diff(q, axis=0).T); S = np.concatenate([[0], np.cumsum(seg)])
        if S[-1] <= 0: continue
        t = np.append(np.arange(0, S[-1], G), S[-1])
        X = np.interp(t, S, q[:, 0]); Y = np.interp(t, S, q[:, 1])
        ok = (X > x0 - 200) & (X < x0 + w + 200) & (Y > y0 - 200) & (Y < y0 + h + 200)
        if ok.sum() < 2: continue
        k = np.flatnonzero(ok)
        for a, b in zip(np.r_[k[0], k[1:][np.diff(k) > 1]], np.r_[k[:-1][np.diff(k) > 1], k[-1]]):   # runs inside the area
            if b - a < 1: continue
            P.append(np.stack([X[a:b + 1], Y[a:b + 1]], 1)); own.append(li)
    if P:
        starts = np.cumsum([0] + [len(q) for q in P[:-1]]); N = sum(len(q) for q in P)
        XY = np.concatenate(P)
        rows, cols, wts = [], [], []
        for s0, q in zip(starts, P):
            a = np.arange(s0, s0 + len(q) - 1); rows += [a]; cols += [a + 1]; wts += [np.hypot(*np.diff(q, axis=0).T) + 1e-3]
        T = cKDTree(XY)
        for k, (s0, q) in enumerate(zip(starts, P)):   # the ends of every run join the nearest node of another run within 60 m
            for e in (s0, s0 + len(q) - 1):
                cand = [j for j in T.query_ball_point(XY[e], 60.0) if not (s0 <= j < s0 + len(q))]
                if cand:
                    j = min(cand, key=lambda j: np.hypot(*(XY[j] - XY[e]))); rows.append(np.array([e])); cols.append(np.array([j])); wts.append(np.array([np.hypot(*(XY[j] - XY[e])) + 1e-3]))
        r_ = np.concatenate(rows); c_ = np.concatenate(cols); w_ = np.concatenate(wts)
        A = csr_matrix((np.r_[w_, w_], (np.r_[r_, c_], np.r_[c_, r_])), shape=(N, N))
        ci = np.clip(((XY[:, 0] - x0) / G).astype(int), 0, nx - 1); ri = np.clip(((XY[:, 1] - y0) / G).astype(int), 0, ny - 1)
        g0 = m[ri, ci]
        # robust ground along the river: median of the channel minima within 250 m along the network
        D = dijkstra(A, limit=250.0)
        gs = np.array([np.median(g0[np.isfinite(D[k])]) for k in range(N)], np.float32); del D
        deg = np.asarray((A > 0).sum(1)).ravel()
        from scipy.sparse.csgraph import connected_components
        ncomp, comp = connected_components(A, directed=False)
        L = np.full(N, np.nan, np.float32)
        for cc in range(ncomp):
            idx = np.flatnonzero(comp == cc)
            ends = idx[deg[idx] <= 1] if (deg[idx] <= 1).any() else idx
            out = int(ends[np.argmin(gs[ends])])       # the outlet: the lowest end
            dist, pred = dijkstra(A, indices=out, return_predecessors=True)
            order = idx[np.argsort(-dist[idx])]          # from the far upstream ends towards the outlet
            L1 = gs.copy(); L2 = gs.copy()
            for n in order:                              # running minimum from upstream
                pa = pred[n]
                if pa >= 0 and L1[n] < L1[pa]: L1[pa] = L1[n]
            for n in order[::-1]:                        # running maximum from downstream
                pa = pred[n]
                if pa >= 0 and L2[pa] > L2[n]: L2[n] = L2[pa]
            Lc = L1 + UPPER_W * (L2 - L1)
            # no fall steeper than MAX_FALL along the river: where the DEM drops sharply (a 2-3 m dip of the 30 m model) the
            # drop is spread upstream by lowering the levels there (the bed is carved under them), never by raising them
            for n in order[::-1]:
                pa = pred[n]
                if pa >= 0: Lc[n] = min(Lc[n], Lc[pa] + MAX_FALL * (dist[n] - dist[pa]))
            L[idx] = Lc[idx]
        # every water pixel: the level of the nearest river node (wide reaches, oxbows, the bank polygons)
        ys, xs = np.nonzero(wd)
        dq, jq = T.query(np.stack([x0 + (xs + 0.5) * G, y0 + (ys + 0.5) * G], 1))
        near = dq < 150.0
        lvl[ys[near], xs[near]] = L[jq[near]] + FREEBOARD_NET
    # water not reached from a river line (ponds when the layout keeps them): the old per-component minimum
    rest = wd & np.isnan(lvl)
    if rest.any():
        lab, nl = ndi.label(rest, structure=np.ones((3, 3)))
        mins = ndi.minimum(m, lab, range(1, nl + 1))
        lvl[rest] = np.asarray(mins, np.float32)[lab[rest] - 1] + FREEBOARD
    # the quantum: the finest that leaves every cell (and the 32 m around it) <= 63 levels
    for STEP in (0.1, 0.2, 0.25, 0.5, 1.0):
        q = np.round(np.floor(lvl / STEP + 1e-6) * STEP, 3)
        nc = int(math.ceil(cell / G)); worst = 0
        for r0 in range(0, ny, nc):
            for c0 in range(0, nx, nc):
                sub = q[max(0, r0 - 2):r0 + nc + 2, max(0, c0 - 2):c0 + nc + 2]
                worst = max(worst, len(np.unique(sub[np.isfinite(sub)])))
        if worst <= 63: break
    lvl = q.astype(np.float32)
    # 26 Oct (user: a stretch of the Psel was a dry trench): the dry test is for OSM water POLYGONS climbing a gully side;
    # the river line itself always carries water (prokh_gen carves the bed down to the level)
    rv = ndi.binary_dilation(np.asarray(riv)[::-1] > 0, iterations=1)
    dry = wd & (m - lvl > LIFT_MAX) & ~rv
    # extend the level field 400 m beyond the water (nearest water pixel), so the cells can look it up at any bank pixel
    filled = ~np.isnan(lvl)
    _, (iy, ix) = ndi.distance_transform_edt(~filled, return_indices=True)
    lvl_ext = lvl[iy, ix]
    LEVEL = (lvl_ext.astype(np.float32), x0, y0); DRY = (dry, x0, y0); RAW[0] = lvl
    return int(len(np.unique(lvl[filled])))


def sample(grid, xs, ys):
    """nearest lookup of a 16 m grid at old-frame metres"""
    a, x0, y0 = grid
    c = np.clip(((xs - x0) / G).astype(np.int64), 0, a.shape[1] - 1); r = np.clip(((ys - y0) / G).astype(np.int64), 0, a.shape[0] - 1)
    return a[r, c]

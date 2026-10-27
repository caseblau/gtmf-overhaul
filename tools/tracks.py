"""Roads, field tracks and village streets painted the vanilla way.

26 Oct (user: 'the roads look bad'), measured again on the whole of Petropolye PgD5 (tools/cell_preview.py): EVERY road
there - the main road, the field tracks and the village street alike - is one to three thin lines of pave (soil 10,
2 m wide) with smooth, gentle curves, lying in a grass corridor 10-20 m wide between the fields; the dark road_back
(11) bands are the field margins, not the roads. Where the traffic is heavier the lines run in parallel 3-5 m apart and
split and rejoin. The earlier versions painted a 6 m road_back band (main roads), 1 m black-earth ruts (tracks) and a
14 m trampled band (village streets); the engine blends the soils over a couple of metres, so all of them came out
as the brown blotches of the screenshots.
"""
import math
import numpy as np
from PIL import Image, ImageDraw
import texsynth as TX
import works as W
from scipy import ndimage as ndi

PAVE, CLAY, SAND, GRASS = 10, 3, 5, 0


def _global(pp, origin):
    return [[x + origin[0], y + origin[1]] for x, y in pp]


def _local(pts, origin):
    return [(x - origin[0], y - origin[1]) for x, y in pts]


def _segments(pts, seg_len, frac, salt):
    """split a polyline (2 m samples) into stretches of ~seg_len m; return the stretches that are 'on' (hash < frac)"""
    out = []; n = max(2, int(seg_len / 2.0))
    h0 = W._hash(round(pts[0][0]), round(pts[0][1]), salt)
    for k, i in enumerate(range(0, len(pts) - 1, n)):
        if W._hash(h0, k, 1) % 100 < frac * 100:
            out.append(pts[i:i + n + 1])
    return out


def paint(soil, cov, lines, origin, codes, vil_mask=None):
    """soil / cov: (2048, 2048) 1 m; lines: (pp, col, dash, cover) in cell px; origin: block metres of the cell (seam-free noise)."""
    ROAD, TRACK = codes['ROAD'], codes['TRACK']
    pave = Image.new('L', (2048, 2048), 0); dp = ImageDraw.Draw(pave)       # the pave lines, 2 m
    trod = Image.new('L', (2048, 2048), 0); dt = ImageDraw.Draw(trod)       # trodden village street ground
    corr = Image.new('L', (2048, 2048), 0); dc = ImageDraw.Draw(corr)        # the grass corridor: kept free of crops
    def lane(line, off, salt, lam=(61.0, 173.0)):
        r = W._offset(line, off) if off else line
        r = W.wavy(r, amp=(0.25, 0.4), lam=(lam[0] + salt, lam[1] + 3 * salt), step=2.0, taper=4.0)
        dp.line(_local(r, origin), fill=255, width=2, joint='curve')
    for (pp, col, dash, c) in lines:
        if c not in (ROAD, TRACK) or len(pp) < 2: continue
        g = _global(pp, origin)
        main = W.wavy(g, amp=(0.5, 0.8), lam=(53.0, 151.0), step=2.0, taper=6.0)   # the trace: smooth, long curves
        side = 1.0 if W._hash(round(g[0][0]), round(g[0][1]), 5) % 2 else -1.0
        if c == TRACK:
            # field track: one line; a second beside it 3-4 m off on a quarter of the length (carts round a wet spot)
            lane(main, 0.0, 0); dc.line(_local(main, origin), fill=255, width=8, joint='curve')
            for seg in _segments(main, 120.0, 0.12, 6):
                lane(seg, side * (3.0 + (W._hash(round(seg[0][0]), round(seg[0][1]), 7) % 10) / 10.0), 3)
        else:
            # main road / village street: the two wheel tracks 2.2 m apart (26 Oct, user: the three-pronged roads look bad)
            lane(main, -1.1, 1); lane(main, 1.1, 2)
            dc.line(_local(main, origin), fill=255, width=12, joint='curve')
            if vil_mask is not None:   # in the villages: a trodden street 12-16 m wide (pale earth with grass islands) the yards open onto
                dt.line(_local(main, origin), fill=255, width=14, joint='curve')
    pm = np.asarray(pave) > 0; cm = np.asarray(corr) > 0
    keep = ~np.isin(cov, (codes['WATER'], codes['MARSH'], codes['RAIL'], codes['BUILDING']))
    pm &= keep; cm &= keep
    # the corridor: no crop texture across it (ragged field edges had pushed the crops over the tracks)
    tr_ = cm & (cov == codes.get('FIELD', 1))
    cov[tr_] = TRACK
    # road and track ground is grass (the old road_back band / clay strip go), then the pave lines on it
    soil[np.isin(cov, (ROAD, TRACK)) & keep] = GRASS
    n_patch = TX.gnoise(soil.shape, origin, 2.0, 62)
    if vil_mask is not None:
        tz = (np.asarray(trod) > 0) & vil_mask & keep & np.isin(cov, (ROAD, TRACK, GRASS, codes.get('VILLAGE', 5)))
        nt = TX.gnoise(soil.shape, origin, 4.0, 67) + 0.5 * TX.gnoise(soil.shape, origin, 1.5, 68)
        soil[tz & (nt > -0.15)] = PAVE
    soil[pm] = PAVE
    soil[pm & (n_patch > 0.8)] = CLAY   # a few clay specks in the lines, as in the vanilla cells
    return int(pm.sum()), int(cm.sum()), 0


# ------------------------------------------------------------------------------------------------ roads by example
LIB = None        # vstamps.Library (set by prokh_gen): road strips unrolled from the Petropolye roads
BUF = {}          # per cell: mask / hi / det / grass of the painted road strips (written over texref's layers)
CORE_MASK = None  # per cell: the road cores (wheel-track zone), whatever soil the strip copied there
LOWER = None      # per cell: (2048, 2048) float32 m - how much the ground is lowered under the wheel tracks
CORE = {'track': 3.5, 'main': 6.0}
NOGO_SOILS = (4, 6, 7, 8, 9, 12, 13, 14, 15)   # crops, leaves, forest ground, concrete, trench: never copied with a road


def paint_strips(soil, cov, lines, origin, codes, vil_mask=None):
    """every OSM road / track is painted with a strip of a real Petropolye road bent along it (27 Oct, user: 'same with
    roads'): a piece of 120-220 m of one strip after another, the strips chosen by global coordinates so that a road is
    painted the same way in both cells of a border. Returns the number of road pixels painted."""
    from scipy.spatial import cKDTree
    ROAD, TRACK = codes['ROAD'], codes['TRACK']
    kinds = {k: [r for r in LIB.roads if r['kind'] == k and len(r['soil']) >= 60] for k in ('track', 'main', 'street')}
    kinds['main'] = kinds['main'] + kinds['street']
    if not kinds['track']: kinds['track'] = kinds['main']
    if not kinds['main']: kinds['main'] = kinds['track']
    corr = Image.new('L', (2048, 2048), 0); dc = ImageDraw.Draw(corr)
    S_xy, S_t, S_info = [], [], []   # samples (cell px), tangents, (strip id, strip row, core half width)
    strips = []
    for (pp, col, dash, c) in lines:
        if c not in (ROAD, TRACK) or len(pp) < 2: continue
        kind = 'track' if c == TRACK else 'main'
        g = W._chaikin(_global(pp, origin), 3)
        P = np.array(g, np.float64); seg = np.hypot(*np.diff(P, axis=0).T); Sx = np.concatenate([[0], np.cumsum(seg)])
        if Sx[-1] < 5: continue
        s = np.arange(0.0, Sx[-1], 1.0)
        X = np.interp(s, Sx, P[:, 0]); Y = np.interp(s, Sx, P[:, 1])
        T = np.stack([np.gradient(X), np.gradient(Y)], 1); T /= np.maximum(np.hypot(T[:, 0], T[:, 1]), 1e-6)[:, None]
        lx, ly = X - origin[0], Y - origin[1]
        # keep the samples near the cell only
        near = (lx > -40) & (lx < 2088) & (ly > -40) & (ly < 2088)
        if not near.any(): continue
        # strip pieces along the line
        rows = np.zeros(len(s), np.int64); sid = np.zeros(len(s), np.int64)
        h0 = W._hash(round(g[0][0]), round(g[0][1]), 11); k = 0; i = 0
        lst = kinds[kind]
        while i < len(s):
            r = lst[W._hash(h0, k, 1) % len(lst)]; n_r = len(r['soil'])
            ln = min(n_r - 1, 120 + W._hash(h0, k, 2) % 100)
            o = W._hash(h0, k, 3) % max(1, n_r - ln)
            j = min(len(s), i + ln)
            sid[i:j] = len(strips); rows[i:j] = o + np.arange(j - i)
            strips.append(r); i = j; k += 1
        core = CORE[kind]
        sel = np.flatnonzero(near)
        S_xy.append(np.stack([lx[sel], ly[sel]], 1)); S_t.append(T[sel]); S_info.append(np.stack([sid[sel], rows[sel], np.full(len(sel), int(core * 10))], 1))
        dc.line(list(zip(lx[::4].tolist() + [lx[-1]], ly[::4].tolist() + [ly[-1]])), fill=255, width=int(2 * (core + 3)) + 1, joint='curve')
    BUF.clear()
    global LOWER, CORE_MASK
    LOWER = None; CORE_MASK = None
    if not S_xy: return 0
    S_xy = np.concatenate(S_xy); S_t = np.concatenate(S_t); S_info = np.concatenate(S_info)
    cm = np.asarray(corr) > 0
    keep = ~np.isin(cov, (codes['WATER'], codes['MARSH'], codes['RAIL'], codes['BUILDING']))
    cm &= keep
    # the corridor stays free of crops (ragged field edges had pushed the crops over the tracks)
    cov[cm & (cov == codes.get('FIELD', 1))] = TRACK
    yy, xx = np.nonzero(cm)
    if not len(yy): return 0
    tree = cKDTree(S_xy)
    _, j = tree.query(np.stack([xx + 0.5, yy + 0.5], 1))
    d = np.stack([xx + 0.5, yy + 0.5], 1) - S_xy[j]; t = S_t[j]
    n = d[:, 0] * -t[:, 1] + d[:, 1] * t[:, 0]   # signed offset across the road
    core = S_info[j, 2] / 10.0
    an = np.abs(n)
    noise = ((xx.astype(np.int64) * 73856093) ^ (yy.astype(np.int64) * 19349663)) % 1000 / 1000.0
    CORE_MASK = np.zeros((2048, 2048), bool); CORE_MASK[yy[an <= core - 1.0], xx[an <= core - 1.0]] = True
    take = (an <= core) | ((an <= core + 3) & (noise * 3 > an - core))
    xx, yy, n, j = xx[take], yy[take], n[take], j[take]
    col = np.clip(np.rint(n).astype(int) + 12, 0, 24)
    sidv = S_info[j, 0]; rowv = S_info[j, 1]
    n2 = 2048
    BUF.update(mask=np.zeros((n2, n2), bool), hi=np.zeros((n2, n2), np.uint8), det=np.zeros((n2, n2, 4), np.uint8), grass=np.zeros((n2, n2), np.uint8))
    lower = np.zeros((n2, n2), np.float32)
    for q in np.unique(sidv):
        m = sidv == q; r = strips[q]
        rr = np.clip(rowv[m], 0, len(r['soil']) - 1); cc = col[m]
        ss = r['soil'][rr, cc].copy()
        ss[np.isin(ss, NOGO_SOILS)] = 0
        ty, tx = yy[m], xx[m]
        soil[ty, tx] = ss
        BUF['mask'][ty, tx] = True; BUF['hi'][ty, tx] = r['hi'][rr, cc]; BUF['det'][ty, tx] = r['det'][rr, cc]; BUF['grass'][ty, tx] = r['grass'][rr, cc]
        lower[ty, tx] = np.where(ss == 10, 0.14, np.where(ss == 11, 0.06, 0.0))
    LOWER = ndi.uniform_filter(lower, 3)
    return int(BUF['mask'].sum())

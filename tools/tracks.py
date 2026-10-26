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

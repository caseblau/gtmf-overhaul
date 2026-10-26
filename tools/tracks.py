"""Field tracks and village streets painted the vanilla way (25 Oct, user: "some roads can be like in vanilla, just 2 tracks").

Measured on Petropolye PgD5 (tools/cell_preview.py + mat_map cross-sections): a field track is NOT a 3.5 m clay band but a
2-3 m wide strip of PAVE (soil 10 - packed bare earth) with ragged edges, running in the grass; where carts avoided ruts
a second strip runs 3-6 m beside it for a stretch; clay (3) and sand (5) patches speckle it.  A village street is a wide
trampled zone (clay / pave / dark earth, 15-30 m) crossed by two or three parallel pave tracks 1-2 m wide that wander
3-8 m from the axis.  The graded main roads keep their 4-6 m road_back (11) band, with a "summer track" of pave beside
them on a quarter of their length.
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
    pave = Image.new('L', (2048, 2048), 0); dp = ImageDraw.Draw(pave)
    pave2 = Image.new('L', (2048, 2048), 0); dp2 = ImageDraw.Draw(pave2)
    tramp = Image.new('L', (2048, 2048), 0); dt = ImageDraw.Draw(tramp)
    for (pp, col, dash, c) in lines:
        if c not in (ROAD, TRACK) or len(pp) < 2: continue
        g = _global(pp, origin)
        if c == TRACK:
            # main strip: the OSM line with a gentle wander, 2-3 m wide
            main = W.wavy(g, amp=(1.0, 1.4), lam=(23.0, 71.0), step=2.0, taper=6.0)
            dp.line(_local(main, origin), fill=255, width=4, joint='curve')   # 3.5-4 m (user 25 Oct: the road beside the railway was too narrow)
            # a second strip beside it on ~35 % of the length (stretches of 60-160 m), 4-6 m to one side
            side = 1.0 if W._hash(round(g[0][0]), round(g[0][1]), 5) % 2 else -1.0
            for seg in _segments(main, 110.0, 0.35, 6):
                off = W._offset(seg, side * (4.0 + (W._hash(round(seg[0][0]), round(seg[0][1]), 7) % 20) / 10.0))
                dp2.line(_local(off, origin), fill=255, width=2, joint='curve')
        else:
            invil = vil_mask is not None and any(0 <= x < 2048 and 0 <= y < 2048 and vil_mask[int(y), int(x)] for x, y in pp[::max(1, len(pp) // 12)])
            smooth = W.wavy(g, amp=(0.6, 0.8), lam=(31.0, 97.0), step=2.0, taper=6.0)
            if invil:
                # village street: two or three wandering pave tracks across a trampled zone
                for k, d in enumerate((-5.5, 4.5, 9.0)):
                    if k == 2 and W._hash(round(g[0][0]), round(g[0][1]), 8) % 100 < 50: continue
                    off = W._offset(W.wavy(g, amp=(1.2, 1.8), lam=(29.0 + 7 * k, 83.0 + 11 * k), step=2.0, taper=6.0), d)
                    dp2.line(_local(off, origin), fill=255, width=2, joint='curve')
                dt.line(_local(smooth, origin), fill=255, width=22, joint='curve')
            else:
                # graded road: the 6 m road_back band with a 4 m firm pave centre (vanilla main roads: light packed surface, dark earth shoulders)
                dp.line(_local(smooth, origin), fill=255, width=5, joint='curve')
                # a summer track beside it on a quarter of the length
                side = 1.0 if W._hash(round(g[0][0]), round(g[0][1]), 9) % 2 else -1.0
                for seg in _segments(smooth, 260.0, 0.25, 10):
                    off = W._offset(seg, side * (6.0 + (W._hash(round(seg[0][0]), round(seg[0][1]), 11) % 25) / 10.0))
                    dp2.line(_local(off, origin), fill=255, width=2, joint='curve')
    pm = np.asarray(pave) > 0; p2 = np.asarray(pave2) > 0; tm = np.asarray(tramp) > 0
    n_edge = TX.gnoise(soil.shape, origin, 1.5, 61); n_patch = TX.gnoise(soil.shape, origin, 2.0, 62); n_tr = TX.gnoise(soil.shape, origin, 3.0, 63)
    # the old 3.5 m clay band of the tracks goes back to grass, except where fields run up to the track
    tr = cov == TRACK
    soil[tr & (soil == CLAY)] = GRASS
    # the 6 m road_back band of the main roads stays as drawn (an earlier 4.5 m version read as a cart track in game)
    # ragged edges: the outer pixel of the strips drops out where the noise says so
    core = ndi.binary_erosion(pm, iterations=1)
    strip = core | (pm & (n_edge > -0.2))
    keep = ~np.isin(cov, (codes['WATER'], codes['MARSH'], codes['RAIL'], codes['BUILDING']))
    strip &= keep; p2 &= keep; tm &= keep & (cov != ROAD)
    # trampled village street zone: mixed clay / pave / dark earth on grass only (yards and gardens are painted later by settle.py)
    zone = tm & (soil == GRASS)
    soil[zone & (n_tr > 0.35)] = CLAY
    soil[zone & (n_tr < -0.45)] = PAVE
    soil[zone & (n_tr >= -0.45) & (n_tr <= 0.35) & (n_patch > 0.55)] = 11
    # the tracks themselves
    soil[strip | p2] = PAVE
    speck = (strip | p2) & (n_patch > 0.6)
    soil[speck] = CLAY
    soil[(strip | p2) & (n_patch > 0.9)] = SAND
    return int(strip.sum()), int(p2.sum()), int(zone.sum())

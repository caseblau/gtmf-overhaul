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
    tramp = Image.new('L', (2048, 2048), 0); dt = ImageDraw.Draw(tramp)
    ruts = Image.new('L', (2048, 2048), 0); dr = ImageDraw.Draw(ruts)        # the wheel ruts: dark earth, 1 m
    corr = Image.new('L', (2048, 2048), 0); dc = ImageDraw.Draw(corr)        # the track corridor: kept free of crops
    def two_ruts(line, gauge, salt):
        for sgn in (-1.0, 1.0):
            r = W._offset(line, sgn * gauge / 2.0)
            r = W.wavy(r, amp=(0.15, 0.25), lam=(9.0 + salt, 27.0 + salt), step=2.0, taper=4.0)
            dr.line(_local(r, origin), fill=255, width=1, joint='curve')
    for (pp, col, dash, c) in lines:
        if c not in (ROAD, TRACK) or len(pp) < 2: continue
        g = _global(pp, origin)
        if c == TRACK:
            # field track (25 Oct, user: the pale 4 m strips read as broken concrete): two dark wheel ruts 1.6 m apart
            # with grass between them, in a 4 m corridor the crops do not cross; a second pair beside it where carts
            # went round a wet spot (~25 % of the length)
            main = W.wavy(g, amp=(1.0, 1.4), lam=(23.0, 71.0), step=2.0, taper=6.0)
            two_ruts(main, 1.6, 0); dc.line(_local(main, origin), fill=255, width=4, joint='curve')
            side = 1.0 if W._hash(round(g[0][0]), round(g[0][1]), 5) % 2 else -1.0
            for seg in _segments(main, 110.0, 0.25, 6):
                off = W._offset(seg, side * (3.5 + (W._hash(round(seg[0][0]), round(seg[0][1]), 7) % 15) / 10.0))
                two_ruts(off, 1.6, 3); dc.line(_local(off, origin), fill=255, width=3, joint='curve')
        else:
            invil = vil_mask is not None and any(0 <= x < 2048 and 0 <= y < 2048 and vil_mask[int(y), int(x)] for x, y in pp[::max(1, len(pp) // 12)])
            smooth = W.wavy(g, amp=(0.6, 0.8), lam=(31.0, 97.0), step=2.0, taper=6.0)
            if invil:
                # village street: a 14 m trampled band of dark earth with grass islands, two worn rut pairs in it
                dt.line(_local(smooth, origin), fill=255, width=14, joint='curve')
                two_ruts(W._offset(smooth, -1.8), 1.6, 1); two_ruts(W._offset(smooth, 2.2), 1.6, 2)
            else:
                # graded road: the 6 m band of dark road earth (soil 11) with one rut pair in the middle
                two_ruts(smooth, 1.8, 4)
    rm = np.asarray(ruts) > 0; cm = np.asarray(corr) > 0; tm = np.asarray(tramp) > 0
    n_patch = TX.gnoise(soil.shape, origin, 2.0, 62); n_tr = TX.gnoise(soil.shape, origin, 3.0, 63)
    keep = ~np.isin(cov, (codes['WATER'], codes['MARSH'], codes['RAIL'], codes['BUILDING']))
    rm &= keep; cm &= keep; tm &= keep & (cov != ROAD)
    # the track corridor: no crop texture across it (ragged field edges had pushed the crops over the tracks - the gaps)
    tr_ = cm & np.isin(cov, (codes.get('FIELD', 1), GRASS))
    cov[tr_] = TRACK
    soil[(cov == TRACK) & np.isin(soil, (CLAY, PAVE, 6, 7, 15))] = GRASS
    # village street band: dark earth (11) with grass islands where the noise is high, no pale pave / clay patches
    zone = tm & (soil == GRASS)
    soil[zone & (n_tr < 0.35)] = 11
    # the ruts: black earth (2), a few clay specks
    soil[rm] = 2
    soil[rm & (n_patch > 0.75)] = CLAY
    strip = rm; p2 = cm
    return int(strip.sum()), int(p2.sum()), int(zone.sum())

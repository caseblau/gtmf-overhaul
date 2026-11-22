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
CLS = {}          # per cell: id(pixel list of a road line) -> 'paved' | 'road' | 'field' | 'path' (prokh_gen.road_class)
# 14 Nov: look class -> (strip kind, core half width m, ragged verge m, code). The core of the old two looks was 3.5 / 6 m for every
# road; the sheet's classes are a metalled road ~6 m, a dirt road ~4-5 m, a cart track ~2.5 m and a footpath under 1 m.
LOOK = {'paved': ('main', 4.0, 2.0, 1), 'road': ('main', 2.6, 2.5, 2), 'field': ('track', 1.7, 1.2, 3), 'ride': ('track', 1.6, 0.0, 4), 'path': ('track', 0.7, 0.0, 5),
        # 14 Nov (user: "there are 9 road types"): the WIG signs 18 - 26, widths as the legend gives them
        'w18': ('main', 6.5, 1.5, 11),   # szosa wyborowa: a stone carriageway 10 m wide, earth shoulders
        'w19': ('main', 5.0, 1.5, 12),   # szosa I klasy: stone carriageway 7 m
        'w20': ('main', 3.7, 1.5, 13),   # szosa II klasy: stone carriageway 4.5 m
        'w21': ('main', 4.2, 2.0, 1),    # trakt / droga wzmocniona: hard trodden earth 5.5 m, cobbled in patches, shoulders
        'w22': ('main', 2.6, 2.5, 2),    # droga wiejska IIIa: two wheel tracks, a verge (a copied strip of a village road)
        'w23': ('track', 2.0, 1.5, 6),   # droga gospodarcza IIIb: a farm road, two ruts with grass between
        'w24': ('track', 1.5, 0.8, 3),   # drozyna IIIc: the field track, ruts in the grass, the crop at its edge
        'w25': ('track', 1.2, 0.0, 7),   # droga zimowa: in summer a faint line over the wet ground
        'w26': ('track', 0.7, 0.0, 5)}   # sciezka
STONE = {11: 5.0, 12: 3.5, 13: 2.25}   # look code -> half width of the stone carriageway
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
    NLOOK = {}
    NLINE = [0]
    S_xy, S_t, S_info = [], [], []   # samples (cell px), tangents, (strip id, strip row, core half width)
    strips = []
    for (pp, col, dash, c) in lines:
        if c not in (ROAD, TRACK) or len(pp) < 2: continue
        look = CLS.get(id(pp)) or ('w24' if c == TRACK else 'w22')
        if look in ('field', 'w24'):   # a cart track that runs through a wood is a forest ride (WIG no. 151)
            xs_ = np.clip(np.array([q[0] for q in pp]).astype(int), 0, 2047); ys_ = np.clip(np.array([q[1] for q in pp]).astype(int), 0, 2047)
            if codes.get('WOOD') is not None and (cov[ys_, xs_] == codes['WOOD']).mean() > 0.6: look = 'ride'
        if look in ('paved', 'w21'):   # a short piece inside a settlement is a street of the village / town grid, not the metalled highway
            xs_ = np.clip(np.array([q[0] for q in pp]).astype(int), 0, 2047); ys_ = np.clip(np.array([q[1] for q in pp]).astype(int), 0, 2047)
            ln_ = float(sum(math.hypot(b_[0] - a_[0], b_[1] - a_[1]) for a_, b_ in zip(pp, pp[1:])))
            if vil_mask is not None and ln_ < 350.0 and vil_mask[ys_, xs_].mean() > 0.5: look = 'w22' if look == 'w21' else 'road'
        kind, core_, verge_, lcode = LOOK[look]
        NLOOK[look] = NLOOK.get(look, 0) + 1
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
        core = core_
        sel = np.flatnonzero(near)
        S_xy.append(np.stack([lx[sel], ly[sel]], 1)); S_t.append(T[sel]); S_info.append(np.stack([sid[sel], rows[sel], np.full(len(sel), int(core * 10)), np.full(len(sel), lcode), np.full(len(sel), int(verge_ * 10)), np.full(len(sel), NLINE[0])], 1)); NLINE[0] += 1
        dc.line(list(zip(lx[::4].tolist() + [lx[-1]], ly[::4].tolist() + [ly[-1]])), fill=255, width=int(2 * (core + verge_)) + 1, joint='curve')
    print('  road looks (lines):', dict(NLOOK), ' classed by the sheet:', sum(1 for l_ in lines if id(l_[0]) in CLS), flush=True)
    BUF.clear()
    global LOWER, CORE_MASK
    LOWER = None; CORE_MASK = None
    if not S_xy: return 0
    S_xy = np.concatenate(S_xy); S_t = np.concatenate(S_t); S_info = np.concatenate(S_info)
    cm = np.asarray(corr) > 0
    keep = ~np.isin(cov, (codes['WATER'], codes['MARSH'], codes['RAIL'], codes['BUILDING']))
    cm &= keep
    # the corridor stays free of crops (ragged field edges had pushed the crops over the tracks)
    # (14 Nov: only under the carriageway itself - a footpath or a cart track runs THROUGH the crop, the corn stands right at its edge)
    yy, xx = np.nonzero(cm)
    if not len(yy): return 0
    tree = cKDTree(S_xy)
    # 14 Nov (user: "the roads collide"): where two roads meet, every pixel went to the road whose centre line was nearest - a field
    # track running into a highway cut a wedge of its own ground out of the carriageway. Now the better road wins wherever its
    # carriageway reaches: of the 16 nearest samples the one of the highest class within its own core takes the pixel, and only
    # where no carriageway reaches does the nearest line.
    pts_ = np.stack([xx + 0.5, yy + 0.5], 1)
    dd_, jj_ = tree.query(pts_, k=min(16, len(S_xy)))
    if jj_.ndim == 1: dd_, jj_ = dd_[:, None], jj_[:, None]
    RANK = np.zeros(16, np.int32)
    for q_, c_ in enumerate((5, 7, 4, 3, 6, 2, 1, 13, 12, 11)): RANK[c_] = q_ + 1   # footpath lowest ... szosa wyborowa highest
    rk_ = RANK[S_info[jj_, 3]]; ok_ = dd_ <= S_info[jj_, 2] / 10.0 + 0.3
    sc_ = np.where(ok_, rk_ * 100.0 - dd_, -1.0)
    bj_ = sc_.argmax(1); none_ = sc_.max(1) < 0; bj_[none_] = 0
    j = jj_[np.arange(len(bj_)), bj_]
    # the junction: ground that lies inside the carriageway of two different roads at once. Each road brought its own ruts, grass
    # strip and verge there, cut off along the line where the other road began (user: the roads collide with "Other roads"). It
    # becomes one piece of plain trodden ground instead (the stone of a highway stays stone).
    lid_ = S_info[jj_, 5]
    tc_ = S_t[j]; ta_ = S_t[jj_]
    turn_ = np.abs(ta_[:, :, 0] * tc_[:, None, 0] + ta_[:, :, 1] * tc_[:, None, 1]) < 0.9   # the other road runs off at more than ~25 degrees: a junction, not the next piece of the same road
    junc = (ok_ & turn_ & (lid_ != lid_[np.arange(len(bj_)), bj_][:, None])).any(1)
    del tc_, ta_, turn_
    del dd_, jj_, rk_, ok_, sc_, lid_
    d = np.stack([xx + 0.5, yy + 0.5], 1) - S_xy[j]; t = S_t[j]
    n = d[:, 0] * -t[:, 1] + d[:, 1] * t[:, 0]   # signed offset across the road
    core = S_info[j, 2] / 10.0
    an = np.abs(n)
    noise = ((xx.astype(np.int64) * 73856093) ^ (yy.astype(np.int64) * 19349663)) % 1000 / 1000.0
    CORE_MASK = np.zeros((2048, 2048), bool); CORE_MASK[yy[an <= core - 1.0], xx[an <= core - 1.0]] = True
    verge = S_info[j, 4] / 10.0
    take = (an <= core) | ((an <= core + verge) & (noise * verge > an - core))
    xx, yy, n, j = xx[take], yy[take], n[take], j[take]
    an = an[take]; noise = noise[take]; lookv = S_info[j, 3]; corev = core[take]; junc = junc[take]
    fld_ = (cov[yy, xx] == codes.get('FIELD', 1)) & (an <= corev)
    cov[yy[fld_], xx[fld_]] = TRACK
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
        # the looks that are not copied from a Petropolye strip (the game's reference villages have no metalled road, no forest
        # ride and no footpath): painted by the offset from the centre line
        lk = lookv[m]; a_ = an[m]; nz_ = noise[m]; c_ = corev[m]
        pv = lk == 1   # tract: a hard even carriageway 5.5 m wide, cobbled in patches, earth shoulders, no grass strip in the middle
        ss[pv] = np.where(a_[pv] <= 2.75, np.where(nz_[pv] < 0.15, 4, 10), np.where(a_[pv] <= c_[pv], 11, ss[pv]))
        for sc_, sw_ in STONE.items():   # the metalled highways: stone from edge to edge, earth shoulders
            st_ = lk == sc_
            ss[st_] = np.where(a_[st_] <= sw_, 4, np.where(a_[st_] <= c_[st_], 11, ss[st_]))
            pv = pv | st_
        wn_ = lk == 7   # winter road: only a faint pair of ruts in the wet grass
        ss[wn_] = np.where((np.abs(a_[wn_] - 0.8) <= 0.3) & (nz_[wn_] < 0.35), 3, 0)
        rd = lk == 4   # forest ride: leaf litter, two faint ruts, no verge
        ss[rd] = np.where((np.abs(a_[rd] - 0.9) <= 0.35) & (nz_[rd] < 0.75), 3, 13)
        ph = lk == 5   # footpath: a trodden line of bare earth 1 - 1.5 m wide
        ss[ph] = np.where(nz_[ph] < 0.85, 3, 0)
        jn = junc[m] & ~pv & (lk != 5) & (lk != 7)
        ss[jn] = np.where(nz_[jn] < 0.9, 10, 0)
        fl = (lk == 3) | (lk == 6)   # farm road and cart track in the open: two ruts in the grass (the strip gives the ruts; outside them grass, not road earth)
        ss[fl & (ss == 11)] = 0
        soil[ty, tx] = ss
        BUF['mask'][ty, tx] = True; BUF['hi'][ty, tx] = r['hi'][rr, cc]; BUF['det'][ty, tx] = r['det'][rr, cc]; BUF['grass'][ty, tx] = r['grass'][rr, cc]
        lower[ty, tx] = np.where(pv, 0.05, np.where(ss == 10, 0.14, np.where(ss == 11, 0.06, np.where((ss == 3) & (rd | ph), 0.05, 0.0))))
        gz_ = pv | rd | ph | jn
        if gz_.any(): BUF['grass'][ty[gz_], tx[gz_]] = 0
    LOWER = ndi.uniform_filter(lower, 3)
    return int(BUF['mask'].sum())

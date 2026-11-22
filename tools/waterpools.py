r"""Summer water for a block of small lowland streams and ponds (M16 Okuniew, 14 Nov 2026).

The user: "check the water and how it behaves in game, remember its summer so the water is evaporating and the rivers might be
shallow, the exeption are the ponds and some other areas. make it as realistic as possible".

Why a new model. tools/waterlevel.py gives a river ONE monotone surface (made for the Psel, which falls 0.3 m/km): a running
minimum along the network with a fall of at most 2 m/km. On a net of small streams and ditches that fall faster the surface is
pushed far under the ground - measured on the Okuniew cells of 13 Nov: the water of the streams lay a median 1.8 m below the
DEM ground, a third of it more than 3 m, a tenth more than 6 m, up to 24 m - and gen_cell then cut the bed down to it: streams in
canyons. And the carving worked from the water of one cell only, so the cell beside a stream kept its bank: steps of up to 8 m
along 6.9 km of cell borders.

The model here:
  * the water surface FOLLOWS THE GROUND: at every station of a stream (its own vertices, about 3 m apart) the low ground of the
    corridor (lowest 4 m DEM value within one pixel, median-filtered along the stream) minus a freeboard; the surface is that
    value floored to a band of 0.5 m with hysteresis. Banks stand 0.1 - 0.9 m above the water everywhere, never metres.
  * a run of stations in one band is a POOL of one flat level. Where the band changes the stream is dry for a few metres (a
    sill / ford): the engine draws every level as a flat sheet and a step between two sheets as a wall of water (seen on the Psel
    25 Oct and 4 Nov), so two levels never touch.
  * August: a share of the pools of the small (thin-line) streams is dry - a damp bed with sedge - and the rest shallow; the
    thick-line rivers keep their water but shallow; ponds and the wide (double-line) reaches are full and deep.
  * ponds: one level each, the low ground round the shore minus a freeboard; long narrow water areas (the double-line river
    reaches) get bands along their length like the lines.
  * everything is a function of block coordinates (stations, levels, tiles of 8 m), and the cell works on masks rasterised with
    a margin, so the two cells of a border carve the same ground.

build()  once per block: splits the water lines into pool / dry-bed features and keeps the stations.
cell()   per cell: the final water mask, the dry beds, the new ground, the level index (4 m) with its tight patches.
"""
import math, struct, zlib
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

G4 = 4.0      # block DEM pixel, metres
TILE = 8      # metres: the unit of the level index (2 x 2 index pixels); a tile is wet only when it and its 8 neighbours have one level
PARAM = dict(
    fb=0.25,            # surface below the low ground of the corridor (m), before the band floor
    max_cut=1.2,        # the level line lies at most this far under the stream's own ground (m)
    low_pct=15, low_win=41, smooth_win=15,   # the level line: this percentile of the corridor ground over low_win stations (3 m apart), smoothed over smooth_win
    band=0.5,           # level quantum of the streams (m)
    hyst_up=0.2, hyst_dn=0.15,
    min_pool=12.0,      # a pool shorter than this (m) is a dry bed
    piece=90.0,         # a pool is judged wet / dry in pieces of at most this length (m)
    wet_stream=0.50,    # share of the thin-line stream pieces that carry water in August (the game's own summer maps: 3 - 30 %
                        # of the small beds on the steppe maps, 70 - 85 % on the wet northern one; Mazovia after the rain of 20 - 26 July 1944)
    wet_river=1.0,      # the same for the thick-line rivers
    near_wet=40.0,      # a stream piece this close (m) to a pond / wide water always carries water
    ch_dry=0.35,        # depth of a dry bed under the corridor ground (m)
    # greatest water depth by kind (m). The engine (read from its code, 14 Nov): soldiers are not slowed up to 0.40 m and swim above
    # 1.25 m; a vehicle is flooded when its water line (jeep 0.75 m ... T-34 1.39 ... Panther 1.74) stays under water; the game's own
    # ponds and small rivers have a flat bed 2.0 m down. So: a stream never stops anybody, a thick-line river slows men a little, a
    # wide reach drowns jeeps and armoured cars but not tanks, a pond drowns everything.
    wet_w0=0.15, wet_k=0.30, wet_min=0.15,   # with a width in metres on the line (w_m, read off the sheet's line weight): share wet = wet_w0 + wet_k x (w - 1), at least wet_min
    cap_w0=0.25, cap_k=0.09, cap_min=0.30, cap_max=0.65, cap_wide=0.70,   # ... and the depth cap = cap_w0 + cap_k x w (a ribbon river: cap_wide)
    cap_stream=0.40, cap_river=0.60, cap_rivarea=0.90, cap_pond=2.0,
    edge_depth=-0.05, depth_slope=0.25,                               # depth at the waterline and its growth per metre inward
    pond_fb=0.3, pond_pct=25.0, pond_q=0.25,                          # pond level: this percentile of the shore ground minus pond_fb, floored to pond_q
    zone=50.0, bank0=0.12, bank_d1=2.0, bank_s2=0.10,                # beside the channel the ground may rise bank0 + (bank slope) x d for bank_d1 metres, then bank_s2 per metre, out to zone metres
    pond_reach=60.0, pond_above=1.0, pond_below=0.5, pond_join=1.0, pond_gap=24.0,                 # a stream within pond_reach of a pond stands no more than pond_above over / pond_below under the pond's level
    pond_zone=60.0, pond_rise0=0.3, pond_rise=0.08,                  # round a pond the ground rises no faster than pond_rise0 + pond_rise x distance over the pond's level, out to pond_zone
    dam_top=0.5, dam_w=20.0, dam_fall=0.1, pond_smooth=2.5,           # ... and stands on an embankment: dam_top over the level for dam_w metres, then falling dam_fall per metre; the shore ground is smoothed (sigma, m)
    raise_d=4.0, raise_h=0.10,                                       # ground within raise_d of water (and all ground of a wet tile) is held raise_h above it (the generator adds a micro-relief of 0.12 m afterwards)
    max_station_d=20.0,                                              # a water pixel further than this from every station of the model has no level and stays ground
)
ST = None     # wet stations: dict(xy, L, cap, area)   (old-frame metres)
DR = None     # dry stations: dict(xy, zb)
INFO = {}


def _h01(x, y, salt=0):
    return (zlib.crc32(struct.pack('<iii', int(round(x)), int(round(y)), salt)) & 0xffffffff) / 4294967296.0


def build(feats, wline, warea, dem4, x0, y0, cell=2048.0, params=None, log=print, area_mask=None):
    """feats: features in old-frame metres; wline(tags) -> True for a water line, warea(tags) -> True for a water area;
    dem4: the block's ground at 4 m, row 0 = south, origin (x0, y0). Returns the new feature list."""
    global ST, DR, INFO
    P = dict(PARAM); P.update(params or {})
    ny, nx = dem4.shape
    gmin = ndi.minimum_filter(dem4, size=3)
    # ---------------- water areas on the 4 m grid
    if area_mask is None:
        img = Image.new('L', (nx, ny), 0); d = ImageDraw.Draw(img)
        for kind, t, p, closed in feats:
            if kind == 'area' and warea(t) and len(p) >= 3: d.polygon([((x - x0) / G4, (y - y0) / G4) for x, y in p], fill=1)
        A = np.asarray(img) > 0
    else: A = area_mask
    AL = np.full(A.shape, np.nan, np.float32); AC = np.zeros(A.shape, np.float32)
    # 14 Nov (user: "Just fix the ponds", "fix everything thats wrong"): the retraced ponds keep the dikes of the sheet, but a row
    # of fish ponds still hangs together through a gap in a dike or a feeder ditch - one water area 900 m long, which took one
    # level (or, as a 'long narrow area', a level in bands across all its ponds). The areas are cut at every neck under ~20 m:
    # each pond between its dikes is a pond of its own, with its own level.
    core_ = ndi.binary_opening(A, iterations=2)
    lab, n = ndi.label(core_)
    if n:
        try:
            from skimage.segmentation import watershed
            lab = watershed(-ndi.distance_transform_edt(A), markers=lab, mask=A).astype(np.int32)
        except Exception:
            for _ in range(60):
                g_ = ndi.grey_dilation(lab, size=3); m_ = (lab == 0) & A & (g_ > 0)
                if not m_.any(): break
                lab = np.where(m_, g_, lab)
    rest_, nr_ = ndi.label(A & (lab == 0))
    if nr_: lab = np.where(rest_ > 0, rest_ + n, lab); n += nr_
    npond = nriv = 0; PL = np.full(n + 1, np.nan)
    for k, sl in enumerate(ndi.find_objects(lab)):
        ys = slice(max(0, sl[0].start - 8), min(ny, sl[0].stop + 8)); xs = slice(max(0, sl[1].start - 8), min(nx, sl[1].stop + 8))
        sub = lab[ys, xs] == k + 1; g = gmin[ys, xs]
        ring = ndi.binary_dilation(sub, iterations=2) & ~A[ys, xs]
        if not sub.any(): continue
        gr = g[ring] if ring.sum() >= 4 else g[sub]
        din = ndi.distance_transform_edt(sub); wmax = 2.0 * din.max() * G4
        yy, xx = np.nonzero(sub); diag = G4 * math.hypot(np.ptp(yy) + 1, np.ptp(xx) + 1)
        spread = float(np.percentile(gr, 60) - np.percentile(gr, 10))      # the low side of the shore: trees and roofs lift the top of the surface model
        riverlike = diag > 6.0 * max(wmax, G4) and diag > 120.0 and wmax <= 48.0      # (a pond with long arms is no river)
        tl = AL[ys, xs]; tc = AC[ys, xs]
        if not riverlike or spread <= P['band'] or ring.sum() < 8:
            L = math.floor((float(np.percentile(gr, P['pond_pct'])) - P['pond_fb']) / P['pond_q'] + 1e-6) * P['pond_q']
            tl[sub] = L; tc[sub] = P['cap_rivarea'] if riverlike else P['cap_pond']; npond += 1; PL[k + 1] = L
        else:
            # a long narrow water area on falling ground: bands along it. The low shore ground (minimum within 12 m), carried to
            # the nearest water pixel and smoothed over ~40 m inside the water
            lowr = ndi.minimum_filter(np.where(ring, g, np.inf), size=7); lowr = np.where(np.isfinite(lowr), lowr, np.inf)
            src = np.isfinite(lowr) & ring
            _, (iy, ix) = ndi.distance_transform_edt(~src, return_indices=True)
            gn = np.where(src.any(), lowr[iy, ix], g).astype(np.float32)
            wgt = ndi.gaussian_filter(sub.astype(np.float32), 8.0); gs = ndi.gaussian_filter(np.where(sub, gn, 0.0).astype(np.float32), 8.0) / np.maximum(wgt, 1e-6)
            bandi = np.floor((gs - P['pond_fb']) / P['band'] + 1e-6)
            bandi = ndi.median_filter(bandi, size=5)
            tl[sub] = (bandi * P['band'])[sub]; tc[sub] = P['cap_rivarea']; nriv += 1
    near_area = ndi.binary_dilation(A, iterations=int(round(P['near_wet'] / G4))) if A.any() else A
    # 14 Nov (user: "Just fix the ponds"): ponds that lie side by side (the fish ponds, a dike between them) took levels up to
    # 2.5 m apart from the noise of the height data, so one stood over the other and the land between was under water level.
    # Neighbours (within pond_gap) whose levels differ by no more than pond_join share the lowest level of their group.
    if n > 1 and np.isfinite(PL).sum() > 1:
        r_ = int(round(P['pond_gap'] / G4 / 2)) * 2 + 1
        hi_ = ndi.maximum_filter(lab, size=r_); lo_ = -ndi.maximum_filter(np.where(lab > 0, -lab, -(n + 1)), size=r_)
        m_ = (hi_ > 0) & (lo_ <= n) & (hi_ != lo_)
        pairs = np.unique(np.c_[lo_[m_], hi_[m_]], axis=0) if m_.any() else np.zeros((0, 2), int)
        par = list(range(n + 1))
        def find(x):
            while par[x] != x: par[x] = par[par[x]]; x = par[x]
            return x
        for a_, b_ in sorted(pairs.tolist(), key=lambda q_: abs(PL[q_[0]] - PL[q_[1]]) if np.isfinite(PL[q_[0]] + PL[q_[1]]) else 9e9):
            if not np.isfinite(PL[a_] + PL[b_]): continue
            ra, rb = find(a_), find(b_)
            if ra != rb and abs(PL[ra] - PL[rb]) <= P['pond_join']: lo2 = min(PL[ra], PL[rb]); par[ra] = rb; PL[rb] = lo2
        newL = np.array([PL[find(k_)] if np.isfinite(PL[k_]) else np.nan for k_ in range(n + 1)])
        ch = np.isfinite(newL) & (np.abs(newL - np.where(np.isfinite(PL), PL, newL)) >= 0) & np.isfinite(PL)
        nj_ = int(sum(1 for k_ in range(1, n + 1) if np.isfinite(newL[k_]) and find(k_) != k_))
        sel_ = ch[lab] & (lab > 0); AL[sel_] = newL[lab][sel_].astype(np.float32)
        log('ponds side by side put on one level: %d' % nj_)
    near_pond = ndi.binary_dilation(A, iterations=int(round(P['pond_reach'] / G4))) if A.any() else A
    if A.any():      # the level of the nearest water area, for the stream stations within reach of it (backwater)
        _, (iy_, ix_) = ndi.distance_transform_edt(~(A & np.isfinite(AL)), return_indices=True); ALn = AL[iy_, ix_]
    else: ALn = AL
    # ---------------- the lines: pools and dry beds
    out = []; W = [[], [], [], [], []]; D = [[], [], []]; stat = dict(river=[0.0, 0.0], stream=[0.0, 0.0]); nband = 0; npool = 0; cuts = []
    # the traced water lines come in short pieces (a third of them under 40 m); a level line taken piece by piece changed band at
    # every joint. Pieces of one class that meet end to end (within 1.5 m, where exactly two ends meet) are chained first.
    pieces = []
    for f in feats:
        kind, t, p, closed = f
        if kind != 'line' or not wline(t): out.append(f); continue
        q = np.asarray(p, np.float64)
        if len(q) < 2: continue
        hw = list(t.get('_hw') or []); hw = (hw + [hw[-1] if hw else 1.0] * len(q))[:len(q)]
        pieces.append((q, hw, 'river' if t.get('waterway') == 'river' else 'stream', t))
    chains = []
    if pieces:
        E = np.array([pc[0][k] for pc in pieces for k in (0, -1)]); te = cKDTree(E)
        par = list(range(len(E)))
        def find(a):
            while par[a] != a: par[a] = par[par[a]]; a = par[a]
            return a
        for a, b in te.query_pairs(1.5): par[find(a)] = find(b)
        node = [find(k) for k in range(len(E))]; adj = {}
        for k, nd in enumerate(node): adj.setdefault(nd, []).append(k)
        used = [False] * len(pieces)
        def grow(i, e):      # from end e (0 start, 1 end) of piece i: the pieces that follow, as (piece, entered at its end)
            res = []
            while True:
                ends = adj[node[2 * i + e]]
                if len(ends) != 2: break
                k = ends[0] if ends[1] == 2 * i + e else ends[1]; j, ej = k // 2, k % 2
                if used[j] or pieces[j][2] != pieces[i][2]: break
                used[j] = True; res.append((j, ej == 1)); i, e = j, 1 - ej
            return res
        for i in range(len(pieces)):
            if used[i]: continue
            used[i] = True
            fwd = grow(i, 1); back = grow(i, 0)
            # forward pieces entered at their start run as they are, entered at their end run reversed; the backward ones are
            # walked away from the start of piece i, so in the chain they come first, each one turned round
            seq = [(j, not rev) for j, rev in back[::-1]] + [(i, False)] + fwd
            qs = []; hs = []; wsq = []
            for j, rev in seq:
                q, hw = pieces[j][0], pieces[j][1]
                if rev: q = q[::-1]; hw = hw[::-1]
                if qs: q = q[1:]; hw = hw[1:]
                wj = pieces[j][3].get('w_m')      # the width of the piece each station comes from (None: no width on the line)
                qs.append(q); hs += list(hw); wsq += [float(wj) if wj else np.nan] * len(q)
            chains.append((np.vstack(qs), hs, pieces[i][2], pieces[i][3], np.asarray(wsq, np.float64)))
    for (q, hw, cls, t, wst) in chains:
        n = len(q)
        if n < 2: continue
        ci = np.clip(((q[:, 0] - x0) / G4).astype(int), 0, nx - 1); ri = np.clip(((q[:, 1] - y0) / G4).astype(int), 0, ny - 1)
        g = gmin[ri, ci].astype(np.float64); ina = A[ri, ci]; nearA = near_area[ri, ci]; La = ALn[ri, ci]; nearP = near_pond[ri, ci]
        # the stream's own level line: the LOW ground along it (15th percentile over about 120 m, then smoothed). The surface
        # model carries the trees of the banks (bumps of 1 - 3 m right on the stream line, measured) and 30 m facets; a level
        # that followed every station changed band every 27 m (first trial). The channel is cut through the bumps, and a dip
        # under the line gets a low bank (the ground next to water is held above it).
        if n >= 5:
            w1 = min(P['low_win'], n if n % 2 else n - 1); w2 = min(P['smooth_win'], n if n % 2 else n - 1)
            gl = ndi.median_filter(g, size=min(11, n if n % 2 else n - 1), mode='nearest')
            g = ndi.uniform_filter1d(ndi.percentile_filter(g, P['low_pct'], size=w1, mode='nearest'), w2, mode='nearest')
            # never more than max_cut under the stream's own ground: where the traced line climbs over a rise (a dune, a line
            # set a few tens of metres off its valley) it follows the rise - and is dry there - instead of being cut through it
            g = np.maximum(g, gl - P['max_cut'])
        z = g - P['fb']; Q = P['band']
        L = np.empty(n); cur = math.floor(z[0] / Q) * Q
        for i in range(n):
            if z[i] < cur - P['hyst_dn'] or z[i] >= cur + Q + P['hyst_up']: cur = math.floor(z[i] / Q) * Q
            L[i] = cur
            # beside a pond the stream stands at the pond's level, unless that would put it more than a metre off its own line
            if nearA[i] and np.isfinite(La[i]) and abs(La[i] - z[i]) <= 1.0: L[i] = La[i]
            # 14 Nov (user: "the ground heights near ponds needs fixing"): the height data carries the trees, and a stream 30 m from
            # a pond stood 4 m over it on one side and 3 m under it on the other. Within reach of a pond a stream keeps near its level.
            elif nearP[i] and np.isfinite(La[i]):
                L[i] = min(max(L[i], math.floor((La[i] - P['pond_below']) / Q) * Q), math.floor((La[i] + P['pond_above']) / Q) * Q)
        s = np.r_[0.0, np.cumsum(np.hypot(*np.diff(q, axis=0).T))]
        # 14 Nov (audit: pools standing on crests, 2 - 5 m above the water on both sides): a station more than 0.5 m above the
        # lowest level on BOTH sides of it along the chain is on a rise the surface model put there - its pool is a dry bed
        crest = (L - np.maximum(np.minimum.accumulate(L), np.minimum.accumulate(L[::-1])[::-1])) > 0.5
        # state per station: -1 inside a water area (the area carries the water), 0 dry bed, 1 pool
        state = np.zeros(n, np.int8)
        a = 0
        while a < n:
            b = a
            while b + 1 < n and L[b + 1] == L[a]: b += 1
            if b > a and a > 0: nband += 1
            ln = s[b] - s[a]
            if ln >= P['min_pool']:
                npiece = max(1, int(math.ceil(ln / P['piece']))); cutp = np.linspace(s[a], s[b], npiece + 1)
                for k in range(npiece):
                    i0 = int(np.searchsorted(s, cutp[k], 'left')); i1 = int(np.searchsorted(s, cutp[k + 1], 'right')) - 1
                    i0 = max(a, min(b, i0)); i1 = max(i0, min(b, i1))
                    prob = P['wet_river'] if cls == 'river' else P['wet_stream']
                    wloc = wst[i0:i1 + 1]; wloc = float(np.nanmean(wloc)) if np.isfinite(wloc).any() else None
                    if wloc is not None: prob = min(1.0, max(P['wet_min'], P['wet_w0'] + P['wet_k'] * (wloc - 1.0)))
                    wet = nearA[i0:i1 + 1].any() or _h01(q[i0, 0], q[i0, 1], 7) < prob
                    if crest[i0:i1 + 1].mean() > 0.5 and not nearA[i0:i1 + 1].any(): wet = False   # (a pool on a rise)
                    if t.get('isolated'): wet = False      # a short network that reaches no pond, river or block edge (tools/streams_fix.py): a headwater ditch, dry in August
                    state[i0:i1 + 1] = 1 if wet else 0
            a = b + 1
        state[ina] = -1
        # features: consecutive stations of one state (and one level when wet); neighbours share their end point
        a = 0
        while a < n:
            b = a
            while b + 1 < n and state[b + 1] == state[a] and (state[a] != 1 or L[b + 1] == L[a]): b += 1
            e = min(n - 1, b + 1) if state[a] != 1 else b      # a dry piece runs on to the first station of what follows
            if state[a] == 1 and b > a:
                t2 = dict(t); t2['_hw'] = hw[a:b + 1]; t2['_L'] = float(L[a])
                out.append(('line', t2, [tuple(v) for v in q[a:b + 1]], False)); npool += 1
                cap = P['cap_river'] if cls == 'river' else P['cap_stream']
                wloc = wst[a:b + 1]; wloc = float(np.nanmean(wloc)) if np.isfinite(wloc).any() else None
                if wloc is not None: cap = P['cap_wide'] if wloc >= 7.0 else min(P['cap_max'], max(P['cap_min'], P['cap_w0'] + P['cap_k'] * wloc))
                for i in range(a, b + 1):
                    W[0].append(q[i, 0]); W[1].append(q[i, 1]); W[2].append(L[a]); W[3].append(cap); W[4].append(0)
                stat[cls][0] += s[b] - s[a]; cuts += (g[a:b + 1] - L[a]).tolist()
            elif state[a] == 0 or (state[a] == 1 and b == a):
                if e > a:
                    t2 = dict(t); t2['_ww'] = t.get('waterway'); t2['waterway'] = 'drybed'; t2['_hw'] = hw[a:e + 1]
                    out.append(('line', t2, [tuple(v) for v in q[a:e + 1]], False))
                    for i in range(a, e + 1):
                        D[0].append(q[i, 0]); D[1].append(q[i, 1]); D[2].append(g[i] - P['ch_dry'])
                    stat[cls][1] += s[e] - s[a]
            a = b + 1
    # the area water as stations too (pixel centres of the 4 m grid)
    yy, xx = np.nonzero(A & np.isfinite(AL))
    na = len(yy)
    W[0] += (x0 + (xx + 0.5) * G4).tolist(); W[1] += (y0 + (yy + 0.5) * G4).tolist(); W[2] += AL[yy, xx].tolist(); W[3] += AC[yy, xx].tolist(); W[4] += [1] * na
    ST = dict(xy=np.c_[W[0], W[1]].astype(np.float64) if W[0] else np.zeros((0, 2)), L=np.asarray(W[2], np.float32), cap=np.asarray(W[3], np.float32), area=np.asarray(W[4], bool))
    DR = dict(xy=np.c_[D[0], D[1]].astype(np.float64) if D[0] else np.zeros((0, 2)), zb=np.asarray(D[2], np.float32))
    # levels per cell (the game's water palette holds 63)
    worst = 0
    if len(ST['L']):
        ci = np.floor((ST['xy'][:, 0] - x0) / cell).astype(int); cj = np.floor((ST['xy'][:, 1] - y0) / cell).astype(int)
        for key in set(zip(ci.tolist(), cj.tolist())):
            m = (ci == key[0]) & (cj == key[1]); worst = max(worst, len(np.unique(np.round(ST['L'][m], 3))))
    cuts = np.asarray(cuts) if cuts else np.zeros(1)
    INFO = dict(pools=npool, ponds=npond, river_areas=nriv, wet_km={k: v[0] / 1000 for k, v in stat.items()}, dry_km={k: v[1] / 1000 for k, v in stat.items()},
                levels_worst_cell=worst, bank_median=float(np.median(cuts)), bank_p95=float(np.percentile(cuts, 95)))
    log('water pools: %d traced pieces in %d chains; ' % (len(pieces), len(chains)) + '%d pools on the lines (river %.1f km wet / %.1f km dry, stream %.1f km wet / %.1f km dry), %d ponds, %d long water areas in bands; '
        'banks above the water: median %.2f m, 95th %.2f m; most levels in one cell %d'
        % (npool, stat['river'][0] / 1000, stat['river'][1] / 1000, stat['stream'][0] / 1000, stat['stream'][1] / 1000, npond, nriv, INFO['bank_median'], INFO['bank_p95'], worst))
    return out


def smooth_shores(wet, sigma=6.0, wide_it=4):
    """14 Nov (user: "smoothen the water areas of water reservoirs so 'tis not in squares"): the ponds come from the sheet's blue
    at 2 - 4 m a pixel, cut out with a square opening - shores in steps of 4 - 16 m. The wide water (over 9 m across) is blurred
    and cut again at one half, which rounds every step and corner off; the narrow water (streams) stays as it is, the teeth of the
    old pond edge go. wet: bool mask at 1 m. -> bool mask."""
    wide = ndi.binary_opening(wet, iterations=wide_it)
    if not wide.any(): return wet
    sm = ndi.gaussian_filter(wide.astype(np.float32), sigma) > 0.5
    rest = wet & ~wide                                     # streams and the fringe of the ponds
    far = rest & ~ndi.binary_dilation(wide, iterations=8)
    lab, n = ndi.label(rest, structure=np.ones((3, 3)))
    if n:
        keep = np.zeros(n + 1, bool); keep[np.unique(lab[far])] = True; keep[0] = False
        rest = keep[lab]                                   # a piece of narrow water stays only if it runs on beyond the pond's edge
    return sm | rest

def cell(wet_pad, dry_pad, road, h2w, x0c, y0c, pad, bslope, params=None):
    """One cell. wet_pad / dry_pad: bool (n + 2 pad)^2, the wet features / the dry beds rasterised with a margin (row 0 =
    south; pixel (r, c) is at x0c - pad + c + 0.5, y0c - pad + r + 0.5); road: bool n^2 (roads, railway, buildings: never
    dug out as a bed); h2w: the cell's ground at 1 m (n^2); bslope: bank slope per pixel (n^2, from seam-free noise).
    -> dict: h (new ground), wet (final water), dry (dry beds), dam (pixels of a wet feature left as ground: the fords between
    two pools), idx / vals / recs (level index at 4 m, its levels, the patch rectangles in metres; idx None = no water),
    d_out (distance to the water, measured with the margin), d_wide (distance to water over 8 m across), lvl (level of the
    water a pixel lies in or stands next to, NaN elsewhere)."""
    P = dict(PARAM); P.update(params or {})
    n = h2w.shape[0]; N = n + 2 * pad
    assert wet_pad.shape == (N, N) and dry_pad.shape == (N, N) and N % TILE == 0 and pad % TILE == 0
    core = (slice(pad, pad + n), slice(pad, pad + n))
    res = dict(h=h2w.astype(np.float32).copy(), wet=np.zeros((n, n), bool), dry=np.zeros((n, n), bool), dam=np.zeros((n, n), bool), idx=None, vals=None, recs=[],
               pond_lvl=np.full((n, n), np.nan, np.float32), d_out=np.full((n, n), 1e6, np.float32), d_wide=np.full((n, n), 1e6, np.float32), lvl=np.full((n, n), np.nan, np.float32))
    cx0, cy0 = x0c - pad, y0c - pad
    def sub(S, margin=60.0):
        if S is None or not len(S['xy']): return None
        m = (S['xy'][:, 0] > cx0 - margin) & (S['xy'][:, 0] < cx0 + N + margin) & (S['xy'][:, 1] > cy0 - margin) & (S['xy'][:, 1] < cy0 + N + margin)
        return np.flatnonzero(m) if m.any() else None
    iw = sub(ST); idr = sub(DR)
    wetf = np.zeros((N, N), bool); ltp = None
    h = res['h']; lvl = res['lvl']
    if iw is not None and wet_pad.any():
        tree = cKDTree(ST['xy'][iw]); Lw = ST['L'][iw]; Cw = ST['cap'][iw]
        nt = N // TILE
        # 14 Nov (user: "Just fix the ponds"): the level of a tile used to come from the station nearest its middle, and a tile kept
        # its water only when no tile round it had another level - every dike between two ponds of different level cost both ponds a
        # strip of 8 - 24 m in squares, and the fish ponds of the sheet (dikes 10 - 16 m wide) came out as a patchwork. Now:
        #   * every water pixel has the level of its nearest station - a pixel of wide water of the nearest water-area station;
        #   * a tile has the level most of its water stands at (wide water counts fourfold); water of another level in it is ground;
        #   * where water of two levels would stand within 4 m of each other, the narrow water gives way to the wide (a ford at the
        #     pond's edge), and two wide waters both give way (a dike).
        # The ground rules further down (everything in a wet tile that is not water stands above the tile's level, the ground within
        # 4 m of water above that water) keep every plane's edge inside ground, which is all the renderer needs.
        Aw = ST['area'][iw]; treeA = None; widep0 = None
        if Aw.any():
            widep0 = ndi.binary_opening(wet_pad, iterations=6)
            if widep0.any(): treeA = cKDTree(ST['xy'][iw][Aw]); LA = Lw[Aw]; CA = Cw[Aw]
            else: widep0 = None
        Lpix = np.full((N, N), np.nan, np.float32); capw = np.zeros((N, N), np.float32)
        wy, wx = np.nonzero(wet_pad)
        dist, j = tree.query(np.c_[cx0 + wx + 0.5, cy0 + wy + 0.5], workers=-1)
        Lq = Lw[j].copy(); Cq = Cw[j].copy(); dq = dist.copy(); isw = np.zeros(len(wy), bool)
        if treeA is not None:
            isw = widep0[wy, wx]
            if isw.any():
                dA, jA = treeA.query(np.c_[cx0 + wx[isw] + 0.5, cy0 + wy[isw] + 0.5], workers=-1)
                Lq[isw] = LA[jA]; Cq[isw] = CA[jA]; dq[isw] = dA
        okd = dq <= P['max_station_d']
        Lpix[wy[okd], wx[okd]] = Lq[okd]; capw[wy[okd], wx[okd]] = Cq[okd]
        lt = np.full((nt, nt), np.nan, np.float32)
        if okd.any():
            key = (wy[okd] // TILE).astype(np.int64) * nt + wx[okd] // TILE; lvq = np.round(Lq[okd] * 1000.0).astype(np.int64); wts = np.where(isw[okd], 4.0, 1.0)
            o1 = np.lexsort((lvq, key)); ks, ls, ws_ = key[o1], lvq[o1], wts[o1]
            newg = np.r_[True, (ks[1:] != ks[:-1]) | (ls[1:] != ls[:-1])]
            gw = np.bincount(np.cumsum(newg) - 1, weights=ws_); gk = ks[newg]; gl = ls[newg]
            o2 = np.lexsort((-gw, gk)); first = np.r_[True, gk[o2][1:] != gk[o2][:-1]]
            bk = gk[o2][first]; lt[bk // nt, bk % nt] = gl[o2][first] / 1000.0
        ltp = np.repeat(np.repeat(lt, TILE, 0), TILE, 1)
        with np.errstate(invalid='ignore'): wetf = np.isfinite(Lpix) & (np.abs(Lpix - ltp) < 1e-3)
        if wetf.any():
            hi = ndi.maximum_filter(np.where(wetf, Lpix, -np.inf), size=9); lo = ndi.minimum_filter(np.where(wetf, Lpix, np.inf), size=9)
            conf = wetf & (hi - lo > 1e-3)
            if conf.any():
                widef = (widep0 & wetf) if widep0 is not None else np.zeros((N, N), bool)
                gone = conf & ~widef
                if widef.any():
                    hiw = ndi.maximum_filter(np.where(widef, Lpix, -np.inf), size=9); low = ndi.minimum_filter(np.where(widef, Lpix, np.inf), size=9)
                    gone |= widef & (hiw - low > 1e-3)
                wetf &= ~gone
        if wetf.any():
            d_in = ndi.distance_transform_edt(wetf); d_out = ndi.distance_transform_edt(~wetf)
            wide = ndi.binary_opening(wetf, iterations=4)
            if wide.any(): res['d_wide'] = ndi.distance_transform_edt(~wide)[core].astype(np.float32)
            wc = wetf[core]
            by, bx = np.nonzero((d_out[core] > 0) & (d_out[core] <= P['raise_d']))
            if len(by):       # the level of the water a pixel stands next to (the ground there is held above it, further down)
                _, j = tree.query(np.c_[x0c + bx + 0.5, y0c + by + 0.5], workers=-1)
                lvl[by, bx] = Lw[j]
            wett = np.isfinite(lt) & wetf.reshape(nt, TILE, nt, TILE).any((1, 3))        # the tiles that get a patch
            tw = np.repeat(np.repeat(wett, TILE, 0), TILE, 1)[core] & ~wc
            lvl[tw] = np.fmax(lvl[tw], ltp[core][tw])                      # ... and everything in them that is not water stands above their level
            if wc.any():
                bed = ltp[core] - np.minimum(capw[core], P['edge_depth'] + P['depth_slope'] * d_in[core])
                h[wc] = bed[wc]; lvl[wc] = ltp[core][wc]
                if road.any() and P.get('culvert_k', 0.4) > 0:
                    # 14 Nov (user: "crossings should be more detailed"): where a road crosses on a culvert the bed stopped at the road's
                    # edge in a sheer wall 0.5 - 1 m high; it now rises to the road at 1:2.5, so the water ends on a sloping face
                    dr_ = ndi.distance_transform_edt(~road)
                    nr_ = wc & (dr_ <= 4.0)
                    if nr_.any(): h[nr_] = np.maximum(h[nr_], ltp[core][nr_] + 0.15 - P.get('culvert_k', 0.4) * dr_[nr_])
            res['wet'] = wc; res['d_out'] = d_out[core].astype(np.float32)
            # the level index (4 m) over the wet tiles of the cell, and the patches the renderer draws: runs of wet tiles in a tile row
            t0 = pad // TILE; t1 = (pad + n) // TILE
            okc = wett[t0:t1, t0:t1]; ltc = lt[t0:t1, t0:t1]
            if okc.any():
                vals = np.unique(np.round(ltc[okc], 3))[:63]     # (the palette holds 63 levels; the block has at most 52 in a cell)
                idt = np.zeros(okc.shape, np.uint8)
                for k, v in enumerate(vals): idt[okc & (np.abs(ltc - v) < 1e-3)] = k + 1
                f = TILE // 4; res['idx'] = np.repeat(np.repeat(idt, f, 0), f, 1); res['vals'] = vals.astype(np.float32)
                # the patches: runs of wet tiles of one level in a tile row, at most 64 m long; a run that repeats exactly in the
                # next row is grown downwards (to 64 m), so a pond is a few dozen rectangles instead of one per row
                recs = []; open_ = {}
                for r in range(idt.shape[0]):
                    row = idt[r]; c = 0; seen = {}
                    while c < len(row):
                        if row[c] == 0: c += 1; continue
                        e = c
                        while e + 1 < len(row) and row[e + 1] == row[c] and (e + 1 - c) * TILE < 64: e += 1
                        key = (c, e, int(row[c])); k = open_.get(key)
                        if k is not None and (r - recs[k][5]) * TILE < 64: recs[k][3] = (r + 1) * TILE; seen[key] = k
                        else: recs.append([c * TILE, r * TILE, (e + 1) * TILE, (r + 1) * TILE, int(row[c]), r]); seen[key] = len(recs) - 1
                        c = e + 1
                    open_ = seen
                recs = [tuple(q[:5]) for q in recs]
                res['recs'] = recs
    # the channel as a whole - water, the dams between pools, the dry beds - and its sides. Every station has a reference height:
    # a pool's level, a dry bed's floor. Inside the channel a dam stands a foot over its pool's level and a dry bed lies on its
    # floor. Beside the channel the ground may rise by the bank profile only (a short bank, then a gentle slope out to `zone`
    # metres): the surface model carries the trees along a stream as a ridge of 1 - 5 m, and a channel cut through it with the
    # banks trimmed for 10 m only stood in a slot again (trial of 14 Nov: cuts of 6.7 m). Only ever lowering; the ground next
    # to water is raised last, so no water plane ends in the air.
    wetc = res['wet']; damp = wet_pad & ~wetf; dryp = dry_pad & ~wet_pad
    chan = wetf | damp | dryp
    if chan.any():
        refs = []; xy = []
        if iw is not None: xy.append(ST['xy'][iw]); refs.append(ST['L'][iw].astype(np.float32))
        if idr is not None: xy.append(DR['xy'][idr]); refs.append(DR['zb'][idr].astype(np.float32) - 0.05)
        if xy:
            treec = cKDTree(np.vstack(xy)); ref = np.concatenate(refs)
            d_ch = ndi.distance_transform_edt(~chan)[core]
            ky, kx = np.nonzero(d_ch <= P['zone'])
            q = np.c_[x0c + kx + 0.5, y0c + ky + 0.5]
            if len(ref) >= 2:      # two nearest stations, weighted: the nearest alone drew a comb of small steps across the banks
                dd, jj = treec.query(q, k=2, workers=-1)
                w_ = 1.0 / (dd + 1.0) ** 2; rj = ((ref[jj] * w_).sum(1) / w_.sum(1)).astype(np.float32); dn = dd[:, 0]
            else:
                dn, j = treec.query(q, workers=-1); rj = ref[j]
            dz = d_ch[ky, kx]; bs = bslope[ky, kx]
            rise = np.minimum(P['bank0'] + bs * dz, P['bank0'] + bs * P['bank_d1'] + P['bank_s2'] * np.maximum(dz - P['bank_d1'], 0.0))
            isdam = damp[core][ky, kx]; isdry = dryp[core][ky, kx] & ~road[ky, kx]
            tgt = np.where(dz <= 0, np.where(isdam, rj + 0.30, np.where(isdry, rj + 0.05, rj + P['bank0'])), rj + rise)
            keep = wetc[ky, kx] | (dn > P['zone'] + 30.0)      # (a channel pixel with no station anywhere near keeps its ground)
            hv = h[ky, kx]
            # 14 Nov (audit: walls up to 12 m at 50 m from the streams): the clamp eases out over the outer half of the zone
            wz_ = np.clip((P['zone'] - dz) / (0.5 * P['zone']), 0.0, 1.0)
            hv = np.where(keep, hv, hv + wz_ * (np.minimum(hv, tgt) - hv))
            lv = lvl[ky, kx]
            hv = np.where(~wetc[ky, kx] & np.isfinite(lv), np.maximum(hv, lv + P['raise_h']), hv)
            h[ky, kx] = hv
    # 14 Nov (user: "the ground heights near ponds needs fixing"): the ponds of the 1941 sheet are not in today's height data -
    # the ground inside one spreads over 1 - 7 m. Measured on the first pools cells: shore slopes of 88 %, a rim 4 m wide with
    # ground 1 - 4 m under the pond level behind it, banks 4 m high 30 m away. Round a pond (water over 13 m across) the ground
    # now (1) rises no faster than a gentle slope from the shore, (2) is smoothed, (3) stands on an embankment where the land
    # is lower than the pond - the dike the sheet draws round the fish ponds.
    if ltp is not None and wetf.any():
        widep = ndi.binary_opening(wetf, iterations=6)
        if widep.any():
            dp, (py_, px_) = ndi.distance_transform_edt(~widep, return_indices=True)
            dpc = dp[core].astype(np.float32); notw = ~res['wet']
            sel = (dpc > 0) & (dpc <= P['pond_zone']) & notw
            if sel.any():
                Lp = ltp[py_[core], px_[core]]
                up = Lp + P['pond_rise0'] + P['pond_rise'] * dpc
                res['pond_lvl'] = np.where(sel, Lp, np.nan).astype(np.float32)
                wp_ = np.clip((P['pond_zone'] - dpc) / (0.5 * P['pond_zone']), 0.0, 1.0)   # (eased out over the outer half: no wall at 60 m)
                h[:] = np.where(sel & np.isfinite(Lp), h + wp_ * (np.minimum(h, up) - h), h)
                if P['pond_smooth'] > 0:
                    m_ = notw.astype(np.float32)
                    hs = ndi.gaussian_filter(h * m_, P['pond_smooth'], mode='nearest') / np.maximum(ndi.gaussian_filter(m_, P['pond_smooth'], mode='nearest'), 1e-3)
                    wgt = np.clip((P['pond_zone'] - dpc) / 15.0, 0.0, 1.0) * sel
                    ed = np.minimum.outer(np.minimum(np.arange(n), n - 1 - np.arange(n)), np.minimum(np.arange(n), n - 1 - np.arange(n))).astype(np.float32)
                    wgt = wgt * np.clip(ed / 8.0, 0.0, 1.0)      # (not at the cell's edge: the neighbour smooths its own side)
                    h[:] = h + wgt * (hs - h)
                lo = Lp + np.where(dpc <= P['dam_w'], np.minimum(P['dam_top'], P['raise_h'] + 0.1 * dpc), P['dam_top'] - P['dam_fall'] * (dpc - P['dam_w']))
                h[:] = np.where(sel & np.isfinite(Lp), h + wp_ * (np.maximum(h, lo) - h), h)
                fl = notw & np.isfinite(lvl)                 # ground next to any water stays above that water
                h[:] = np.where(fl, np.maximum(h, lvl + P['raise_h']), h)
    res['dry'] = dryp[core] & ~road
    res['dam'] = damp[core]
    return res

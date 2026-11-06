#!/usr/bin/env python3
r"""Frozen evaluator (v2) for the 1941 road digitisation of the Prokhorovka block (roadgraph node N1).

  python3 eval_roads.py <roads.json> <outdir> [--region x0 y0 x1 y1] [--allow-border] [--ref-dir DIR]

<roads.json>  roads_1941.json format: {"roads": [{"highway": cls, "name": id, "pts": [[x, y], ...]}, ...]} in DEM-lattice
              metres (x east, y north; sheet raster px = (x / 4, (24576 - y) / 4), pixel index = pixel centre).
<outdir>      metrics.json and report.md are written there.
--region      restrict every check to the box x0 <= x < x1, y0 <= y < y1 (lattice m); tiles overlapping it are reported.
--allow-border  line ends on the region border count as 'border' stubs (region nodes).
--ref-dir     where the frozen files are (default: the directory of this script).

Frozen files (made by N1 from the SHEET ONLY - nothing from any roads json):
  ink_clean.png     255 = the sheet's black line work after removing lettering / digits / symbols (component shape filter
                    and letter rows), 2 km grid and sheet-frame lines, brown contours / ravine edges, the railway symbol,
                    staff pencil (by hue + the pencil masks), wood / orchard dots and rings, blue water line work (by hue),
                    house blocks; full sheet grid 5632 x 6144
  ink_skel.png      centre-line skeleton for C2 (single lines, bridged dash chains, double-line centres; pieces >= 60 m)
  dbl_centre.png    centre line of the double-line (main road) symbol (medial axis of the band between its two lines)
  dbl_band.png      the double-line band (both lines and the gap)
  c1_centre.png     the C1 reference: centre lines of all line work (ink_skel without the 60 m minimum)
  house_blocks.png  the house blocks removed from ink_clean (solid ink inside the villages)
  builtup_ref.png   frozen copy of builtup_1941.png;  void.png  unreadable sheet (missing tiles + pencil masks);  blank.png
  railway.json      railway centre line;  crossings.json  road / railway crossings drawn on the sheet
Optional next to <roads.json>: deadends.json = [{"road": id, "end": "start" | "end", "why": .., "crop": ..} |
  {"x": m, "y": m, "r": m, "why": ..}] whitelists reviewed dead ends for C3.

Checks (metres; 1 km tiles = 1024 m squares of the block named Trrcc, row 0 at the north edge):
  C1 on-ink (gate >= 98 %)  share of traced length within 8 m of the ink mask = ink_clean closed with an 11 px disk
                    (dash gaps and the double-line gap closed) plus dbl_centre.  Class 'secondary' is measured against
                    dbl_centre and the closed ink outside dbl_band (the two edge lines of the double-line symbol are
                    replaced by its centre).  Inside the villages (built-up mask or house blocks, +8 m) a point of any
                    class counts as on: streets and through roads run in the lanes between the house rows.  Length inside void is not scored.
  C2a coverage (NOT a gate, a number)  per tile, share of ink_skel length within 12 m of a traced line.  The gate is the
                    reviewer's verdict on the review sheets of make_review.py (every uncovered skeleton piece >= 60 m).
  C3 topology  every line end: junction (a vertex of another line within 2 m), block edge (<= 24 m), blank patch
               (<= 24 m), street end in the built-up mask (residential), border (--allow-border, <= 10 m of the region
               border), whitelisted, else dangling.
  C4 railway   traced segments crossing a railway line farther than 25 m from every crossings.json point.
  C5 villages  built-up blobs (8-connected) of >= 0.3 ha without a residential line inside the blob.
Deterministic: no randomness, sorted output.
"""
import sys, os, json, math, argparse, time
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
Image.MAX_IMAGE_PIXELS = None

BLOCK = (0.0, 2048.0, 18432.0, 20480.0)      # lattice m (x0, y0, x1, y1)
TILE = 1024.0
NT = 18
TOL_C1, TOL_C2, JUNC, EDGE, BLANK_R, BORDER, RAIL_OK = 8.0, 12.0, 2.0, 24.0, 24.0, 10.0, 25.0
C1_PASS, C2_PASS, C5_HA = 0.98, 0.95, 0.3
STEP = 2.0

def px_to_m(px, py): return 4.0 * px, 24576.0 - 4.0 * py
def m_to_px(x, y): return x / 4.0, (24576.0 - y) / 4.0

def tile_of(x, y):
    c = np.floor((np.asarray(x) - BLOCK[0]) / TILE).astype(int); r = np.floor((BLOCK[3] - np.asarray(y)) / TILE).astype(int)
    return r, c

def tile_name(r, c): return 'T%02d%02d' % (r, c)

def tile_box(r, c): return [BLOCK[0] + c * TILE, BLOCK[3] - (r + 1) * TILE, BLOCK[0] + (c + 1) * TILE, BLOCK[3] - r * TILE]

def densify(p, step):
    p = np.asarray(p, float)
    if len(p) < 2: return p, np.zeros(len(p))
    seg = np.hypot(*np.diff(p, axis=0).T); s = np.r_[0.0, np.cumsum(seg)]
    if s[-1] <= 0: return p[:1], np.zeros(1)
    n = max(1, int(math.ceil(s[-1] / step))); t = np.linspace(0.0, s[-1], n + 1)
    q = np.c_[np.interp(t, s, p[:, 0]), np.interp(t, s, p[:, 1])]
    w = np.full(len(q), s[-1] / n); w[0] = w[-1] = s[-1] / n / 2.0
    return q, w

def load_mask(path):
    return np.asarray(Image.open(path).convert('L')) > 0

def sample(mask, xy):
    px, py = m_to_px(xy[:, 0], xy[:, 1])
    ix = np.clip(np.round(px).astype(int), 0, mask.shape[1] - 1); iy = np.clip(np.round(py).astype(int), 0, mask.shape[0] - 1)
    return mask[iy, ix]

def seg_intersections(A, B, C, D):
    """all intersections of segments A[i]B[i] with C[j]D[j]; returns (i, j, point)"""
    out = []
    if not len(A) or not len(C): return out
    # bbox prefilter with a KD-tree on segment midpoints of the railway
    mid = (C + D) / 2; half = np.hypot(*(D - C).T) / 2; T = cKDTree(mid); R = half.max() if len(half) else 0
    for i in range(len(A)):
        a, b = A[i], B[i]; m = (a + b) / 2; r = math.hypot(*(b - a)) / 2
        for j in T.query_ball_point(m, r + R + 1e-6):
            c, d = C[j], D[j]
            r_ = b - a; s_ = d - c; den = r_[0] * s_[1] - r_[1] * s_[0]
            if abs(den) < 1e-12: continue
            t = ((c[0] - a[0]) * s_[1] - (c[1] - a[1]) * s_[0]) / den
            u = ((c[0] - a[0]) * r_[1] - (c[1] - a[1]) * r_[0]) / den
            if 0 <= t <= 1 and 0 <= u <= 1: out.append((i, j, a + t * r_))
    return out

def c1_masks(RD, ink=None, hb=None, bu=None):
    """C1 distance rasters (metres): distance to c1_centre.png = the CENTRE LINES of the sheet's line work (skeleton of
    ink_clean closed with an 11 px disk - dash gaps up to ~40 m bridged - with the two edge lines of every double-line
    symbol replaced by its centre, dbl_centre); res_ok = built-up mask or house blocks (+8 m)"""
    ink = load_mask(os.path.join(RD, 'ink_clean.png')) if ink is None else ink
    hb = load_mask(os.path.join(RD, 'house_blocks.png')) if hb is None else hb
    bu = load_mask(os.path.join(RD, 'builtup_ref.png')) if bu is None else bu
    cen = load_mask(os.path.join(RD, 'c1_centre.png'))
    y0b, y1b = 1024, 1024 + 4608; B = np.s_[y0b:y1b, :4608]
    dt_ink = np.full(ink.shape, np.inf, np.float32); dt_ink[B] = 4.0 * ndi.distance_transform_edt(~cen[B])
    dt_sec = dt_ink
    res_ok = np.zeros(ink.shape, bool); res_ok[B] = ndi.binary_dilation(bu[B] | hb[B], iterations=2)
    return dt_ink, dt_sec, res_ok

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('roads'); ap.add_argument('outdir')
    ap.add_argument('--region', nargs=4, type=float, default=None, metavar=('X0', 'Y0', 'X1', 'Y1'))
    ap.add_argument('--allow-border', action='store_true')
    ap.add_argument('--ref-dir', default=os.path.dirname(os.path.abspath(__file__)))
    a = ap.parse_args(argv); t0 = time.time()
    RD = a.ref_dir; os.makedirs(a.outdir, exist_ok=True)
    reg = tuple(a.region) if a.region else BLOCK
    inreg = lambda x, y: (x >= reg[0]) & (x < reg[2]) & (y >= reg[1]) & (y < reg[3])

    J = json.load(open(a.roads, encoding='utf-8'))
    roads = []
    for k, r in enumerate(J['roads']):
        p = np.asarray(r['pts'], float)
        if p.ndim != 2 or len(p) < 2: continue
        roads.append(dict(id=str(r.get('name', 'idx%d' % k)), cls=r.get('highway', ''), p=p))
    ink = load_mask(os.path.join(RD, 'ink_clean.png')); skel = load_mask(os.path.join(RD, 'ink_skel.png'))
    hb = load_mask(os.path.join(RD, 'house_blocks.png'))
    void = load_mask(os.path.join(RD, 'void.png')); blank = load_mask(os.path.join(RD, 'blank.png'))
    bu = load_mask(os.path.join(RD, 'builtup_ref.png'))
    rails = json.load(open(os.path.join(RD, 'railway.json')))['lines']
    cr = json.load(open(os.path.join(RD, 'crossings.json')))
    cr_pts = np.array([[c['x'], c['y']] for c in cr['crossings']], float).reshape(-1, 2)
    zones = cr.get('zones', [])
    in_zone = lambda X: next((z['id'] for z in zones if z['box_m'][0] <= X[0] <= z['box_m'][2] and z['box_m'][1] <= X[1] <= z['box_m'][3]), None)
    dead = []
    dpath = os.path.join(os.path.dirname(os.path.abspath(a.roads)), 'deadends.json')
    if os.path.exists(dpath):
        dd = json.load(open(dpath, encoding='utf-8')); dead = dd['deadends'] if isinstance(dd, dict) else dd

    # ---- the C1 ink masks (block rows only, for speed)
    dt_ink, dt_sec, res_ok = c1_masks(RD, ink, hb, bu)
    # ---- skeleton of the ink as points (lattice m) with a length weight per pixel
    ry, rx = np.nonzero(skel)
    K = ndi.convolve(skel.astype(np.uint8), np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]], np.uint8), mode='constant')
    D = ndi.convolve(skel.astype(np.uint8), np.array([[1, 0, 1], [0, 0, 0], [1, 0, 1]], np.uint8), mode='constant')
    wref = 4.0 * np.maximum((K[ry, rx] * 1.0 + D[ry, rx] * math.sqrt(2)) / 2.0, 0.5)
    RX, RY = px_to_m(rx, ry)
    RP = np.c_[RX, RY]

    # ---- traced samples
    S = []; Sw = []; Sid = []; Scls = []
    for k, r in enumerate(roads):
        q, w = densify(r['p'], STEP); S.append(q); Sw.append(w); Sid += [k] * len(q); Scls += [r['cls']] * len(q)
    S = np.vstack(S) if S else np.zeros((0, 2)); Sw = np.concatenate(Sw) if Sw else np.zeros(0)
    Sid = np.array(Sid, int); Scls = np.array(Scls)
    sel = inreg(S[:, 0], S[:, 1])
    px_, py_ = m_to_px(S[:, 0], S[:, 1])
    ix = np.clip(np.round(px_).astype(int), 0, ink.shape[1] - 1); iy = np.clip(np.round(py_).astype(int), 0, ink.shape[0] - 1)
    res = Scls == 'residential'
    sec = Scls == 'secondary'
    dS = np.where(sec, dt_sec[iy, ix], dt_ink[iy, ix])
    vS = sample(void, S)
    on_strict = dS <= TOL_C1
    # inside the 1941 villages (built-up mask or house blocks, + 8 m) every class counts as on: the sheet draws the
    # streets and the roads through a village as the light lane between the house rows, not as lines
    on = on_strict | res_ok[iy, ix]
    on_hb_all = on_strict | (res & res_ok[iy, ix])     # info: the v2 rule (village allowance for residential only)
    scored = sel & ~vS
    per_cls = {}
    def share(m, o=None):
        o = on if o is None else o
        L = Sw[m].sum(); return (float(Sw[m & o].sum() / L) if L > 0 else None), float(L)
    c1_tot, L_tot = share(scored)
    c1_all, L_all = share(scored & ~res)
    c1_res, L_res = share(scored & res)
    c1_hb, _ = share(scored, on_hb_all)
    for cl in sorted(set(Scls.tolist())):
        s_, L_ = share(scored & (Scls == cl)); per_cls[cl] = dict(on_ink=round(s_, 4) if s_ is not None else None, length_m=round(L_))
    per_road = {}
    for k, r in enumerate(roads):
        m = scored & (Sid == k)
        if not m.any(): continue
        s, L = share(m)
        per_road[r['id']] = dict(cls=r['cls'], length_m=round(L), on_ink=round(s, 4) if s is not None else None)
    tr_, tc_ = tile_of(S[:, 0], S[:, 1])
    per_tile_c1 = {}
    for (r_, c_) in sorted(set(zip(tr_[scored], tc_[scored]))):
        m = scored & (tr_ == r_) & (tc_ == c_); s, L = share(m)
        per_tile_c1[tile_name(r_, c_)] = dict(on_ink=round(s, 4), length_m=round(L))
    void_len = float(Sw[sel & vS].sum())

    # ---- C2 coverage
    TS = cKDTree(S) if len(S) else None
    dR = TS.query(RP)[0] if TS is not None else np.full(len(RP), np.inf)
    rsel = inreg(RP[:, 0], RP[:, 1]) & ~sample(void, RP)
    cov = dR <= TOL_C2
    rr, rc_ = tile_of(RP[:, 0], RP[:, 1])
    per_tile_c2 = {}; fails = []
    for r_ in range(NT):
        for c_ in range(NT):
            b = tile_box(r_, c_)
            if b[2] <= reg[0] or b[0] >= reg[2] or b[3] <= reg[1] or b[1] >= reg[3]: continue
            m = rsel & (rr == r_) & (rc_ == c_); L = float(wref[m].sum())
            if L <= 0: per_tile_c2[tile_name(r_, c_)] = dict(ref_m=0, covered=None); continue
            s = float(wref[m & cov].sum() / L)
            per_tile_c2[tile_name(r_, c_)] = dict(ref_m=round(L), covered=round(s, 4))
            if s < C2_PASS and L >= 60: fails.append(dict(tile=tile_name(r_, c_), box_m=b, covered=round(s, 4), ref_m=round(L),
                                                         missed_m=round(L - float(wref[m & cov].sum()))))
    Lr = float(wref[rsel].sum()); c2_all = float(wref[rsel & cov].sum() / Lr) if Lr > 0 else None

    # ---- C3 ends
    verts = []; vown = []
    for k, r in enumerate(roads):
        verts.append(r['p']); vown += [k] * len(r['p'])
    V = np.vstack(verts); vown = np.array(vown); TV = cKDTree(V)
    blank_d = ndi.binary_dilation(blank, iterations=int(BLANK_R / 4))
    bu_d = ndi.binary_dilation(bu, iterations=1)
    ends = []; counts = {}
    for k, r in enumerate(roads):
        for at, P in (('start', r['p'][0]), ('end', r['p'][-1])):
            x, y = P
            if not inreg(x, y): continue
            kind = None
            if any(vown[j] != k for j in TV.query_ball_point(P, JUNC)): kind = 'junction'
            elif x <= BLOCK[0] + EDGE or x >= BLOCK[2] - EDGE or y <= BLOCK[1] + EDGE or y >= BLOCK[3] - EDGE: kind = 'block_edge'
            elif sample(blank_d, np.array([P]))[0]: kind = 'blank_edge'
            elif r['cls'] == 'residential' and sample(bu_d, np.array([P]))[0]: kind = 'residential_end'
            elif a.allow_border and a.region and (abs(x - reg[0]) <= BORDER or abs(x - reg[2]) <= BORDER or abs(y - reg[1]) <= BORDER or abs(y - reg[3]) <= BORDER):
                kind = 'border'
            else:
                for e in dead:
                    if 'road' in e and str(e['road']) == r['id'] and e.get('end', at) == at: kind = 'whitelisted'; break
                    if 'x' in e and math.hypot(e['x'] - x, e['y'] - y) <= e.get('r', 5.0): kind = 'whitelisted'; break
            kind = kind or 'dangling'
            counts[kind] = counts.get(kind, 0) + 1
            if kind == 'dangling':
                tr1, tc1 = tile_of(x, y)
                # diagnostic only: distance to the nearest segment of another line (a T-junction without a shared vertex)
                dmin = np.inf
                for j in TV.query_ball_point(P, 200.0):
                    o = vown[j]
                    if o == k: continue
                    q = roads[o]['p']; A0, B0 = q[:-1], q[1:]; AB = B0 - A0; L2 = np.maximum((AB ** 2).sum(1), 1e-9)
                    t = np.clip(((P - A0) * AB).sum(1) / L2, 0, 1); dmin = min(dmin, float(np.hypot(*(A0 + AB * t[:, None] - P).T).min()))
                ends.append(dict(road=r['id'], end=at, x=round(float(x), 1), y=round(float(y), 1), tile=tile_name(int(tr1), int(tc1)),
                                 nearest_other_line_m=round(dmin, 1) if np.isfinite(dmin) else None))

    # ---- C4 railway
    A_ = []; B_ = []; own = []
    for k, r in enumerate(roads):
        A_.append(r['p'][:-1]); B_.append(r['p'][1:]); own += [k] * (len(r['p']) - 1)
    A_ = np.vstack(A_); B_ = np.vstack(B_); own = np.array(own)
    C_ = []; D_ = []
    for l in rails:
        q = np.asarray(l['pts'], float); C_.append(q[:-1]); D_.append(q[1:])
    C_ = np.vstack(C_); D_ = np.vstack(D_)
    bad = []; legal = 0; unj = []
    TC = cKDTree(cr_pts) if len(cr_pts) else None
    for i, j, X in seg_intersections(A_, B_, C_, D_):
        if not inreg(*X): continue
        d = TC.query(X)[0] if TC is not None else np.inf
        if d <= RAIL_OK: legal += 1; continue
        tr1, tc1 = tile_of(X[0], X[1])
        z = in_zone(X)
        if z:
            unj.append(dict(road=roads[own[i]]['id'], x=round(float(X[0]), 1), y=round(float(X[1]), 1), zone=z, tile=tile_name(int(tr1), int(tc1)))); continue
        bad.append(dict(road=roads[own[i]]['id'], x=round(float(X[0]), 1), y=round(float(X[1]), 1), nearest_crossing_m=round(float(d), 1) if np.isfinite(d) else None,
                        tile=tile_name(int(tr1), int(tc1))))

    # ---- C5 villages
    lab, n = ndi.label(bu, structure=np.ones((3, 3)))
    area = ndi.sum(bu, lab, range(1, n + 1)) * 16.0
    com = ndi.center_of_mass(bu, lab, range(1, n + 1))
    Rm = (Scls == 'residential')
    rs = S[Rm]
    hit = set()
    if len(rs):
        px, py = m_to_px(rs[:, 0], rs[:, 1])
        ix = np.clip(np.round(px).astype(int), 0, bu.shape[1] - 1); iy = np.clip(np.round(py).astype(int), 0, bu.shape[0] - 1)
        hit = set(np.unique(lab[iy, ix]).tolist()) - {0}
    vill = []; nv = 0
    for k in range(n):
        if area[k] < C5_HA * 10000: continue
        cx, cy = px_to_m(com[k][1], com[k][0])
        if not inreg(cx, cy): continue
        nv += 1
        if (k + 1) not in hit:
            tr1, tc1 = tile_of(cx, cy)
            vill.append(dict(blob=k + 1, x=round(cx, 1), y=round(cy, 1), area_ha=round(area[k] / 10000.0, 2), tile=tile_name(int(tr1), int(tc1))))

    M = dict(
        meta=dict(roads=os.path.abspath(a.roads), ref_dir=os.path.abspath(RD), region=list(reg), allow_border=a.allow_border,
                  n_roads=len(roads), tolerances_m=dict(C1=TOL_C1, C2=TOL_C2, junction=JUNC, block_edge=EDGE, blank=BLANK_R, border=BORDER, railway_crossing=RAIL_OK),
                  deadends_file=dpath if os.path.exists(dpath) else None, seconds=round(time.time() - t0, 1)),
        C1=dict(on_ink=round(c1_tot, 4) if c1_tot is not None else None, length_m=round(L_tot), passed=bool(c1_tot is not None and c1_tot >= C1_PASS),
                non_residential_on_ink=round(c1_all, 4) if c1_all is not None else None, non_residential_length_m=round(L_all),
                per_class=per_cls, info_village_allowance_residential_only=round(c1_hb, 4) if c1_hb is not None else None,
                residential_on_ink=round(c1_res, 4) if c1_res is not None else None, residential_length_m=round(L_res),
                void_length_m=round(void_len), per_road=dict(sorted(per_road.items())), per_tile=per_tile_c1),
        C2a=dict(gate=False, note='number only; the C2 gate is the review of make_review.py sheets',
                covered=round(c2_all, 4) if c2_all is not None else None, ink_skeleton_length_m=round(Lr),
                tiles_below_95=sorted(fails, key=lambda f: f['tile']), per_tile=per_tile_c2),
        C3=dict(counts=dict(sorted(counts.items())), dangling=sorted(ends, key=lambda e: (e['tile'], e['road'], e['end'])), passed=not ends),
        C4=dict(crossings_ok=legal, unjudged_in_zone=sorted(unj, key=lambda b: (b['tile'], b['road'], b['x'])), illegal=sorted(bad, key=lambda b: (b['tile'], b['road'], b['x'])), passed=not bad),
        C5=dict(villages=nv, without_street=sorted(vill, key=lambda v: v['blob']), passed=not vill))
    json.dump(M, open(os.path.join(a.outdir, 'metrics.json'), 'w'), indent=1)

    f = lambda v: '-' if v is None else '%.1f %%' % (100 * v)
    L = ['# Road evaluation', '', 'roads: `%s`  region: %s%s  (%d lines, %.1f s)' % (a.roads, list(reg), '  border stubs allowed' if a.allow_border else '', len(roads), M['meta']['seconds']), '',
         '| check | result | pass rule | verdict |', '|---|---|---|---|',
         '| C1 on-ink (all classes) | %s of %.1f km | >= 98 %% | %s |' % (f(c1_tot), L_tot / 1000, 'pass' if M['C1']['passed'] else 'FAIL'),
         '| C1 non-residential / residential (info) | %s of %.1f km / %s of %.1f km | - | - |' % (f(c1_all), L_all / 1000, f(c1_res), L_res / 1000),
         '| C1 with the village allowance for residential only (info) | %s | - | - |' % f(c1_hb),
         '| C2a ink-skeleton coverage (number, not a gate) | %s of %.1f km; %d tiles < 95 %% | review sheets (make_review.py) | review |' % (f(c2_all), Lr / 1000, len(fails)),
         '| C3 ends | %s | no dangling | %s |' % (', '.join('%s %d' % kv for kv in sorted(counts.items())), 'pass' if not ends else 'FAIL'),
         '| C4 railway | %d at drawn crossings, %d elsewhere, %d unjudged (zone) | 0 elsewhere | %s |' % (legal, len(bad), len(unj), 'pass' if not bad else 'FAIL'),
         '| C5 villages | %d of %d blobs >= 0.3 ha without a street | 0 | %s |' % (len(vill), nv, 'pass' if not vill else 'FAIL'), '',
         'Traced length inside void (pencil / missing tiles, not scored): %.1f km' % (void_len / 1000), '']
    L += ['C1 per class: ' + ', '.join('%s %s of %.1f km' % (k, f(v['on_ink']), v['length_m'] / 1000) for k, v in per_cls.items()), '']
    worst = sorted([(v['on_ink'], k, v['length_m'], v['cls']) for k, v in per_road.items() if v['on_ink'] is not None])[:25]
    L += ['## C1: roads with the lowest on-ink share', '', '| road | class | length m | on-ink |', '|---|---|---|---|']
    L += ['| %s | %s | %d | %s |' % (k, c, l, f(s)) for s, k, l, c in worst] + ['']
    L += ['## C2a: tiles below 95 % ink-skeleton coverage (information; judged on the review sheets)', '', '| tile | box (m) | covered | skeleton m | missed m |', '|---|---|---|---|---|']
    L += ['| %s | %s | %s | %d | %d |' % (t['tile'], [int(v) for v in t['box_m']], f(t['covered']), t['ref_m'], t['missed_m']) for t in M['C2a']['tiles_below_95']] + ['']
    nT = sum(1 for e in M['C3']['dangling'] if e['nearest_other_line_m'] is not None and e['nearest_other_line_m'] <= JUNC)
    L += ['## C3: dangling ends', '', '%d of them lie on another line within %.0f m but not at one of its vertices (T-junction without a shared vertex).' % (nT, JUNC), '',
          '| road | end | x | y | tile | nearest other line m |', '|---|---|---|---|---|---|']
    L += ['| %s | %s | %.0f | %.0f | %s | %s |' % (e['road'], e['end'], e['x'], e['y'], e['tile'], e['nearest_other_line_m']) for e in M['C3']['dangling']] + ['']
    L += ['## C4: railway crossed away from a drawn crossing', '', '| road | x | y | nearest crossing m | tile |', '|---|---|---|---|---|']
    L += ['| %s | %.0f | %.0f | %s | %s |' % (b['road'], b['x'], b['y'], b['nearest_crossing_m'], b['tile']) for b in M['C4']['illegal']] + ['']
    L += ['C4 unjudged (inside a zone of crossings.json): ' + (', '.join('%s at (%.0f, %.0f) %s' % (u['road'], u['x'], u['y'], u['zone']) for u in M['C4']['unjudged_in_zone']) or 'none'), '']
    L += ['## C5: villages without a street', '', '| blob | x | y | ha | tile |', '|---|---|---|---|---|']
    L += ['| %d | %.0f | %.0f | %.2f | %s |' % (v['blob'], v['x'], v['y'], v['area_ha'], v['tile']) for v in M['C5']['without_street']] + ['']
    open(os.path.join(a.outdir, 'report.md'), 'w').write('\n'.join(L))
    print('C1 %s  C2a %s (%d tiles < 95 %%, not gated)  C3 dangling %d  C4 illegal %d  C5 %d/%d  -> %s  (%.1f s)' % (
        f(c1_tot), f(c2_all), len(fails), len(ends), len(bad), len(vill), nv, a.outdir, time.time() - t0))
    return M

if __name__ == '__main__':
    main()

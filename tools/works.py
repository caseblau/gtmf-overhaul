"""Field works for the generated cells: trenches, anti-tank ditches and strongpoints from docs/m11_prokhorovka/layout_10jul.json.

How the vanilla terrain does it (measured on Mius MgG3, Korotich KgC3 and Petropolye PgF2, 2026-10-25, tools/cell_preview.py
and cross-sections through the soil-14 skeleton):
  * the trace is a smooth, gently wandering curve (lateral deviation ~4 m over 50 m) - no zigzag traverses;
  * the dug ground is a band of soil TREN (14) about 6-7 m wide (100 % to +-2 m, 95 % at 2-3 m, 1/3 at 3-4 m), then
    road_back (11) 3-6 m out (50-70 %) and clay (3) 5-9 m out (20-35 %); the ground around the works is trampled: bare
    patches (clay) ~30 % above the background within 12 m, fading out by ~45 m; plants removed within 10 m;
  * the heightmap carries a U-shaped trough ~3.5 m wide at the top, 0.8 m deep (quartiles 0.3-1.2 m; Korotich 2.6 m)
    with a slight rise of 0.2-0.3 m beside it;
  * `trench_pos` records (tag, x, y, w, x2, y2): INF every ~4 m ON the fire trenches (w 8.3-9.2), sparser on the
    communication trenches (w 3.2); MG / GUN / MORT / TANK in their own dug patches (MG 6 x 12 m, GUN ~12 m, MORT in
    threes ~12 m apart) with the second point 10 / 15 / 25 m away = the facing; a quarter of the positions are single
    rifle pits (soil-14 squares ~4 m) scattered round the system.
The anti-tank ditch (none in the vanilla cells; Wheatley 2019 Figs. 11-22) is a trapezoid: 2 m floor, steep walls, 6.5 m
wide at the top, 3 m deep, the spoil heaped on the defender's side - the one obstacle tanks cannot cross.
The trench traces are the lines the user painted on the op map (25 Oct, docs/m11_prokhorovka/painted_trenches_25oct.png,
traced by tools/trace_paint.py into layout 'works'); sectionise() breaks each into dug sections, rifle-pit chains and gaps.

apply_cell(h, soil, x0, y0, works, open_mask, origin) carves the works that touch the cell into h (4096 x 4096 metres,
0.5 m, row 0 = south) and soil (2048 x 2048, 1 m) in place and returns the trench_pos records (cell metres).
"""
import json, math
import numpy as np
from PIL import Image, ImageDraw

TREN = 14
# the vanilla fire trench in the 0.5 m heightmap (raw cross-sections, Mius MgG3 / Petropolye / Korotich): a slot with
# near-vertical walls - floor 1 m wide 1.8-2.2 m (Korotich 3-4 m) below the shoulder, 3 m wide at half depth, a parapet
# 0.5-0.8 m high 1-1.5 m wide at the rim on the enemy side, no smoothing.  The black interior seen in game is the
# per-cell ambient-occlusion map (tools/aomap.py) darkening the slot - with the template's AO map (first builds) the same
# slot looked like a lit notch.
# 25 Oct (user): the fire trenches must stay passable for tanks, only the anti-tank ditch is the obstacle - so the slot is
# narrower than the vanilla 3 m: 0.9 m floor, 2.0 m wide at half depth, 1.6 m deep (a T-34 / Pz IV track bridges 2 m).
TRENCH = dict(depth=1.6, floor_w=0.9, top_w=2.0, par_h=0.5, par_off=1.9, par_w=1.4, rear_h=0.2, rear_off=1.7, rear_w=1.0, band=3.2)
DITCH = dict(depth=3.0, floor_hw=1.0, top_hw=3.25, spoil_hw=6.5, spoil_h=1.2, berm_hw=4.5, berm_h=0.3)
PITS = dict(GUN=dict(r14=4.5, floor=1.75, top=2.5, par=4.0, depth=0.6, par_h=0.3), MORT=dict(r14=3.0, floor=1.25, top=1.9, par=3.0, depth=0.5, par_h=0.25),
            INF=dict(r14=2.0, floor=0.75, top=1.25, par=2.2, depth=0.5, par_h=0.25))

def _hash(*vals):
    h = 2166136261
    for v in vals:
        h ^= int(v) & 0xffffffff; h = (h * 16777619) & 0xffffffff
    return h

def load(path):
    d = json.load(open(path, encoding='utf-8'))
    works = list(d.get('works', []))
    # 25 Oct (user): the trench lines are the ones he painted on the op map (layout 'works', type trench); the generated
    # strongpoint systems below are only used when the layout asks for them (works_from_strongpoints: true)
    for sp in (d.get('strongpoints', []) if d.get('works_from_strongpoints', False) else []):
        # a company / battalion strongpoint as in the 1943 photographs and the vanilla Mius cells: a main trench of
        # straight segments across the enemy direction (shallow chevron ~2 r wide, flanks bent back), a shorter second
        # line behind it, two communication trenches, weapon pits and single rifle pits round the system
        cx, cy = sp['xy']; r = sp.get('r', 250)
        face = math.radians(45.0) if sp.get('side', '') == 'GER' else math.radians(225.0)   # towards the enemy
        fx, fy = math.cos(face), math.sin(face); lx, ly = -fy, fx                           # forward / left
        def P(fw, lt): return [cx + fx * fw + lx * lt, cy + fy * fw + ly * lt]
        main = [P(-0.25 * r, -1.15 * r), P(0.15 * r, -0.85 * r), P(0.3 * r, -0.3 * r), P(0.3 * r, 0.3 * r), P(0.15 * r, 0.85 * r), P(-0.25 * r, 1.15 * r)]
        second = [P(-0.35 * r, -0.6 * r), P(-0.3 * r, 0.0), P(-0.35 * r, 0.6 * r)]
        works.append(dict(type='trench', side=sp.get('side', ''), name=sp['name'], pts=main, strongpoint=True, centre=[cx, cy], r=r, face=face))
        works.append(dict(type='trench', side=sp.get('side', ''), name=sp['name'] + ' (second line)', pts=second, strongpoint=False, centre=[cx, cy], r=r))
        for lt in (-0.45, 0.45):
            works.append(dict(type='trench', side=sp.get('side', ''), name=sp['name'] + ' (communication trench)', pts=[P(0.3 * r if abs(lt) < 0.4 else 0.22 * r, lt * r), P(-0.33 * r, lt * r * 0.9)], comm=True))
    return expand_systems(works)

def _chaikin(pts, n=3):
    pts = [tuple(p) for p in pts]
    for _ in range(n):
        if len(pts) < 3: break
        out = [pts[0]]
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            out.append((0.75 * x1 + 0.25 * x2, 0.75 * y1 + 0.25 * y2)); out.append((0.25 * x1 + 0.75 * x2, 0.25 * y1 + 0.75 * y2))
        out.append(pts[-1]); pts = out
    return pts

def wavy(pts, amp=(2.8, 4.0), lam=(37.0, 115.0), step=2.0, taper=15.0):
    """the vanilla trace: corners cut, resampled every `step` m, two sine waves of lateral offset (phases from the first
    point) tapered to zero at the ends so the trace keeps the layout's end points"""
    if len(pts) < 2: return [list(p) for p in pts]
    sm = _chaikin(pts, 3)
    sm = [p for k, p in enumerate(sm) if k == 0 or math.hypot(p[0] - sm[k - 1][0], p[1] - sm[k - 1][1]) > 1e-6]
    if len(sm) < 2: return [list(pts[0]), list(pts[-1])]
    seg = [(x2 - x1, y2 - y1) for (x1, y1), (x2, y2) in zip(sm, sm[1:])]
    L = sum(math.hypot(dx, dy) for dx, dy in seg)
    if L < 1e-6: return [list(sm[0]), list(sm[-1])]
    ph = [(_hash(round(pts[0][0]), round(pts[0][1]), k) % 1000) / 1000.0 * 2 * math.pi for k in (0, 1)]
    out = []; s = 0.0; i = 0; t = 0.0
    while True:
        while i < len(seg) and t > math.hypot(*seg[i]): t -= math.hypot(*seg[i]); i += 1
        if i >= len(seg): break
        dx, dy = seg[i]; ln = math.hypot(dx, dy); ux, uy = dx / ln, dy / ln
        x, y = sm[i][0] + ux * t, sm[i][1] + uy * t
        w = min(1.0, s / taper, (L - s) / taper)
        off = w * (amp[0] * math.sin(2 * math.pi * s / lam[0] + ph[0]) + amp[1] * math.sin(2 * math.pi * s / lam[1] + ph[1]))
        out.append([x - uy * off, y + ux * off]); s += step; t += step
    out.append(list(sm[-1]))
    return out

def traverse(pts, bay=12.0, amp=2.5):   # kept for callers; the vanilla trace is smooth
    return wavy(pts)

def sectionise(w):
    """The 1943 photographs (Wheatley Figs. 3-4, 6: user's crops of 25 Oct) show no uniform lines: a fire trench is a chain of
    pieces - continuous dug sections of 25-140 m, stretches where only single rifle pits were dug 8-14 m apart (dotted
    lines), and gaps of 5-30 m - with short slit trenches to the rear every ~80 m.  Splits a (wavy) trench polyline into
    such pieces; communication trenches and stubs stay continuous."""
    if w.get('comm') or w.get('stub') or w.get('at_ditch'): return [w]
    pts = w['pts']
    samp = _positions(pts, 2.0)
    if len(samp) < 8: return [w]
    out = []; i = 0; k = 0; first = True
    h0 = _hash(round(pts[0][0]), round(pts[0][1]), 7)
    while i < len(samp) - 2:
        hv = _hash(h0, k, 1) % 100; k += 1
        if hv < 55: style, ln = 'dug', 25 + _hash(h0, k, 2) % 116
        elif hv < 80: style, ln = 'pits', 30 + _hash(h0, k, 2) % 71
        else: style, ln = 'gap', 5 + _hash(h0, k, 2) % 26
        n = max(2, int(ln / 2.0)); piece = samp[i:i + n + 1]; i += n
        if style == 'gap' or len(piece) < 2: continue
        pp = [[p[0], p[1]] for p in piece]
        if style == 'dug':
            out.append(dict(w, pts=pp, pitchain=False, sp_pits=bool(w.get('strongpoint')) and first)); first = False
            if _hash(h0, k, 3) % 100 < 45:   # slit trench to the rear, 6-14 m
                # parallel to the line, 10-14 m behind it (user, 25 Oct: the slits standing across the line looked wrong)
                x, y, nx, ny = piece[len(piece) // 2]; sg = _rear_sign(pts, w.get('side', 'USSR')); sl = 6 + _hash(h0, k, 4) % 9
                cx, cy = x + sg * nx * (10 + _hash(h0, k, 5) % 5), y + sg * ny * (10 + _hash(h0, k, 5) % 5); tx, ty = ny, -nx
                out.append(dict(w, pts=[[cx - tx * sl / 2, cy - ty * sl / 2], [cx + tx * sl / 2, cy + ty * sl / 2]], comm=True, stub=True, strongpoint=False))
        else:
            out.append(dict(w, pts=pp, pitchain=True, strongpoint=False, sp_pits=bool(w.get('strongpoint')) and first)); first = False
    return out or [dict(w, sp_pits=bool(w.get('strongpoint')))]

def expand_systems(works):
    """trench systems: main line + a second line 150 m behind + communication trenches every ~500 m;
    'behind_ditch' lines become short firing stubs every 160 m; the ditch itself keeps its smooth trace (with gaps)."""
    out = []
    for w in works:
        if w['type'] != 'trench':
            out.append(w); continue
        pts = w['pts']
        if w.get('behind_ditch'):
            for (x, y, nx, ny) in _positions(pts, 160.0):   # firing pits along the line behind the ditch, 12 m long, PARALLEL to it
                tx, ty = ny, -nx
                out.append(dict(w, pts=[[x - tx * 6, y - ty * 6], [x + tx * 6, y + ty * 6]], stub=True, behind_ditch=False))
            continue
        out.append(dict(w, pts=wavy(pts, amp=(1.5, 2.0)) if w.get('comm') else wavy(pts)))
        if w.get('system') and not w.get('strongpoint'):
            rear = 1.0 if w.get('side', '') == 'USSR' else -1.0   # Soviet rear is to the NE (+x,+y), German rear to the SW
            ux, uy = pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1]; L = math.hypot(ux, uy) or 1.0; ux, uy = ux / L, uy / L
            nx, ny = -uy, ux
            if (nx + ny) * rear < 0: nx, ny = -nx, -ny
            second = [[x + nx * 150, y + ny * 150] for x, y in pts]
            out.append(dict(w, pts=wavy(second), system=False, name=w['name'] + ' (second line)'))
            for (x, y, _, _) in _positions(pts, 500.0)[1:]:
                comm = wavy([[x, y], [x + nx * 150, y + ny * 150]], amp=(1.5, 2.0))
                out.append(dict(w, pts=comm, system=False, name=w['name'] + ' (communication trench)', comm=True))
    # the ditches get a slight wander too (the photographed ditch is dug in short straight lengths with small kinks),
    # and a trench that was painted across a ditch stops at its rim
    out = [dict(w, pts=wavy(w['pts'], amp=(0.8, 1.6), lam=(60.0, 190.0), step=4.0, taper=30.0)) if w['type'] == 'at_ditch' else w for w in out]
    out = _cut_at_ditches(out)
    pieces = []
    for w in out: pieces += sectionise(w) if w['type'] == 'trench' else [w]
    return pieces

def _cut_at_ditches(works, margin=3.0, min_len=10.0):
    """split trench polylines where they come within the ditch's top width + margin of an anti-tank ditch"""
    ditches = [w for w in works if w['type'] == 'at_ditch']
    if not ditches: return works
    from scipy.spatial import cKDTree
    samp = [(x, y) for d in ditches for (x, y, _, _) in _positions(d['pts'], 2.0)]
    if not samp: return works
    tree = cKDTree(np.array(samp)); lim = DITCH['top_hw'] + margin
    out = []
    for w in works:
        if w['type'] != 'trench': out.append(w); continue
        pts = w['pts']
        if len(pts) < 2: out.append(w); continue
        dist, _ = tree.query(np.array(pts), distance_upper_bound=lim)
        keep = np.isfinite(dist) == False
        run = []
        for p, k in zip(pts, keep):
            if k: run.append(p)
            elif run:
                if sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(run, run[1:])) >= min_len: out.append(dict(w, pts=run))
                run = []
        if run and sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(run, run[1:])) >= min_len: out.append(dict(w, pts=run))
    return out

def _touches(pts, x0, y0, m=60):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return not (max(xs) < x0 - m or min(xs) > x0 + 2048 + m or max(ys) < y0 - m or min(ys) > y0 + 2048 + m)

def _positions(pts, step=10.0):
    """points every `step` m along the polyline with the unit normal: (x, y, nx, ny)"""
    out = []; carry = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        L = math.hypot(x2 - x1, y2 - y1)
        if L < 1e-6: continue
        ux, uy = (x2 - x1) / L, (y2 - y1) / L; t = carry
        while t < L:
            out.append((x1 + ux * t, y1 + uy * t, -uy, ux)); t += step
        carry = t - L
    return out

def _point_at(pts, s):
    """point at arc length s along the polyline with the unit normal: (x, y, nx, ny)"""
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        L = math.hypot(x2 - x1, y2 - y1)
        if L < 1e-6: continue
        if s <= L:
            ux, uy = (x2 - x1) / L, (y2 - y1) / L
            return (x1 + ux * s, y1 + uy * s, -uy, ux)
        s -= L
    (x1, y1), (x2, y2) = pts[-2], pts[-1]; L = math.hypot(x2 - x1, y2 - y1) or 1.0
    return (x2, y2, -(y2 - y1) / L, (x2 - x1) / L)

def _blur(a, r, times):
    a = a.astype(np.float64)
    for _ in range(times):
        c = np.cumsum(np.cumsum(np.pad(a, r, mode='edge'), 0), 1); c = np.pad(c, ((1, 0), (1, 0))); k = 2 * r + 1
        a = (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)
    return a.astype(np.float32)

def _offset(pts, d):
    """polyline offset by d (metres) along the normal (-uy, ux) of each segment (positive = left of the direction of travel)"""
    out = []
    for i, (x, y) in enumerate(pts):
        (x1, y1) = pts[max(0, i - 1)]; (x2, y2) = pts[min(len(pts) - 1, i + 1)]
        ux, uy = x2 - x1, y2 - y1; L = math.hypot(ux, uy) or 1.0
        out.append((x - uy / L * d, y + ux / L * d))
    return out

def _rear_sign(pts, side):
    """+1 if the left normal of the polyline points to the side's rear (USSR rear NE, German rear SW), else -1"""
    ux, uy = pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1]; nx, ny = -uy, ux
    rear = 1.0 if side == 'USSR' else -1.0
    return 1.0 if (nx + ny) * rear >= 0 else -1.0

def _pits(w, x0, y0):
    """the dug positions of a strongpoint in cell metres: (tag, x, y, facing): four gun pits on a ring of 0.6 r, a mortar
    section of three pits 12 m apart behind the centre, eight single rifle pits scattered round the system"""
    cx, cy = w['centre']; r = w['r']; face = w.get('face', math.radians(225.0)); out = []
    for k in range(4):
        ang = math.pi / 4 + k * math.pi / 2
        out.append(('GUN', cx + 0.6 * r * math.cos(ang) - x0, cy + 0.6 * r * math.sin(ang) - y0, ang))
    bx, by = cx - 0.45 * r * math.cos(face), cy - 0.45 * r * math.sin(face)   # behind the centre
    for k in (-1, 0, 1):
        out.append(('MORT', bx - 12 * k * math.sin(face) - x0, by + 12 * k * math.cos(face) - y0, face))
    for k in range(8):
        hv = _hash(round(cx), round(cy), k); ang = (hv % 3600) / 1800.0 * math.pi; rr = r * (0.55 + 0.6 * ((hv >> 12) % 1000) / 1000.0)
        out.append(('INF', cx + rr * math.cos(ang) - x0, cy + rr * math.sin(ang) - y0, face))
    return [p for p in out if 8 <= p[1] < 2040 and 8 <= p[2] < 2040]

def apply_cell(h, soil, x0, y0, works, open_mask=None, origin=(0.0, 0.0)):
    """carve the works touching cell (x0, y0) into h (4096, 0.5 m) and soil (2048, 1 m); returns trench_pos records.
    open_mask (2048 x 2048): where the trampled ground round the works may be painted (open land, not roads / water / woods)."""
    hit = [w for w in works if _touches(w['pts'], x0, y0)]
    if not hit: return []
    from scipy import ndimage as ndi
    import texsynth as TX
    recs = []
    delta = np.zeros((4096, 4096), np.float32)
    bare_p = np.zeros((2048, 2048), np.float32)          # probability of a trampled bare patch
    if open_mask is None: open_mask = np.ones((2048, 2048), bool)
    # ---- trenches: U trough drawn as line bands on the 0.5 m grid; the dug band and the spoil from the distance to the trace
    tr = [w for w in hit if w['type'] == 'trench' and not w.get('pitchain')]
    chains = [w for w in hit if w['type'] == 'trench' and w.get('pitchain')]
    chain_pits = []
    for w in chains:   # single rifle pits 8-14 m apart along the piece (dotted lines on the photographs)
        h0 = _hash(round(w['pts'][0][0]), round(w['pts'][0][1]), 9); s_ = 0.0; L = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(w['pts'], w['pts'][1:]))
        k = 0
        while s_ < L:
            x, y, nx, ny = _point_at(w['pts'], s_)
            if 8 <= x - x0 < 2040 and 8 <= y - y0 < 2040: chain_pits.append(('INF', x - x0 + nx * ((_hash(h0, k, 5) % 100) / 100.0 - 0.5), y - y0 + ny * ((_hash(h0, k, 6) % 100) / 100.0 - 0.5), math.atan2(ny, nx)))
            s_ += 8.0 + _hash(h0, k, 7) % 7; k += 1
    if tr or chain_pits:
        T = TRENCH
        # cut (floor / wall levels, crisp) and parapet (soft) drawn separately on the 0.5 m grid: a 'floor' line 1 m wide
        # at -depth inside a 'top' line 2.5 m wide at half depth gives the vanilla slot with one wall sample each side
        imgs = {k: Image.new('L', (4096, 4096), 0) for k in ('floor', 'top')}; dr = {k: ImageDraw.Draw(v) for k, v in imgs.items()}
        par = np.zeros((4096, 4096), np.float32)
        pim = Image.new('F', (4096, 4096), 0.0); d_p = ImageDraw.Draw(pim)
        cl = Image.new('L', (2048, 2048), 0); d_cl = ImageDraw.Draw(cl)
        for w in tr:
            pts = [(p[0] - x0, p[1] - y0) for p in w['pts']]; pts2 = [(2 * x, 2 * y) for x, y in pts]
            if len(pts) < 2: continue
            dr['floor'].line(pts2, fill=255, width=max(1, int(round(2 * T['floor_w']))), joint='curve')
            dr['top'].line(pts2, fill=255, width=int(round(2 * T['top_w'])), joint='curve')
            d_cl.line(pts, fill=255, width=1, joint='curve')
            sg = _rear_sign(pts, w.get('side', 'USSR'))            # +1: the left normal points to the rear
            hgt = 0.5 if w.get('comm') else 1.0
            d_p.line([(2 * x, 2 * y) for x, y in _offset(pts, -sg * T['par_off'])], fill=T['par_h'] * hgt, width=int(round(2 * T['par_w'])), joint='curve')   # parapet, enemy side
            d_p.line([(2 * x, 2 * y) for x, y in _offset(pts, sg * T['rear_off'])], fill=T['rear_h'] * hgt, width=int(round(2 * T['rear_w'])), joint='curve')  # spoil, rear
        pits = [(tag, px, py, ang) for w in hit if w.get('sp_pits') for (tag, px, py, ang) in _pits(w, x0, y0)] + chain_pits
        for (tag, px, py, _) in pits:
            P = PITS[tag]
            d_p.ellipse([2 * (px - P['par']), 2 * (py - P['par']), 2 * (px + P['par']), 2 * (py + P['par'])], fill=P['par_h'])
        fl = np.asarray(imgs['floor']) > 0; top = np.asarray(imgs['top']) > 0
        d = np.where(fl, -T['depth'], np.where(top, -0.55 * T['depth'], 0.0)).astype(np.float32)
        cut = top.copy()
        for (tag, px, py, _) in pits:   # round pits: floor / wall / rim
            P = PITS[tag]; r2 = int(2 * P['par']) + 2; ys, xs = int(2 * py), int(2 * px)
            sl = (slice(max(0, ys - r2), ys + r2 + 1), slice(max(0, xs - r2), xs + r2 + 1))
            yy, xx = np.mgrid[sl]; rr = np.hypot(yy - 2 * py, xx - 2 * px) * 0.5
            d[sl] = np.where(rr <= P['floor'], -P['depth'], np.where(rr <= P['top'], -0.5 * P['depth'], d[sl]))
            cut[sl] |= rr <= P['top']
        par = _blur(np.asarray(pim, dtype=np.float32), 1, 1)
        delta += np.where(cut, d, par).astype(np.float32)
        del fl, top, d, imgs, par, pim, cut
        dist = ndi.distance_transform_edt(~(np.asarray(cl) > 0))
        for (tag, px, py, _) in pits:
            P = PITS[tag]; r2 = int(P['par']) + 3; ys, xs = int(py), int(px)
            sl = (slice(max(0, ys - r2), ys + r2 + 1), slice(max(0, xs - r2), xs + r2 + 1))
            yy, xx = np.mgrid[sl]; rr = np.hypot(yy - py, xx - px)
            dist[sl] = np.minimum(dist[sl], np.maximum(0.0, rr - P['r14'] + T['band']))   # a pit counts as a short piece of trace
        n1 = TX.gnoise(soil.shape, origin, 4.0, 71)
        band = dist <= T['band'] + 0.7 * n1
        bare_p = np.maximum(bare_p, _trample_profile(dist))
        soil[band] = TREN
        rng_ = TX.gnoise(soil.shape, origin, 2.5, 72) * 0.6 + TX.gnoise(soil.shape, origin, 1.0, 73) * 0.4
        near = ~band & (dist <= T['band'] + 3.2) & open_mask                         # spoil: road_back, some clay
        soil[near & (rng_ > -0.55)] = 11; soil[near & (rng_ <= -0.55) & (rng_ > -0.8)] = 3
        del n1, rng_, near, dist
    # ---- anti-tank ditch: trapezoid profile from the distance to the centreline, spoil on the defender's side
    dt = [w for w in hit if w['type'] == 'at_ditch']
    if dt:
        D = DITCH
        cl = Image.new('L', (4096, 4096), 0); d_cl = ImageDraw.Draw(cl)
        rear = Image.new('L', (4096, 4096), 0); d_rear = ImageDraw.Draw(rear)
        gaps = Image.new('L', (4096, 4096), 0); d_g = ImageDraw.Draw(gaps)
        for w in dt:
            pts = [(p[0] - x0, p[1] - y0) for p in w['pts']]
            d_cl.line([(2 * x, 2 * y) for x, y in pts], fill=255, width=1, joint='curve')
            sg = _rear_sign(pts, w.get('side', 'USSR'))
            # the rear half-plane along the ditch: polygon between the line and its offset 40 m to the rear
            poly = [(2 * x, 2 * y) for x, y in pts] + [(2 * x, 2 * y) for x, y in reversed(_offset(pts, sg * 40.0))]
            d_rear.polygon(poly, fill=255)
            for g in w.get('gaps', []):   # crossings left for the road (the bridge the tanks of 29 TC crowded onto)
                gx, gy = 2 * (g[0] - x0), 2 * (g[1] - y0); d_g.ellipse([gx - 18, gy - 18, gx + 18, gy + 18], fill=255)
        clm = np.asarray(cl) > 0; rearm = np.asarray(rear) > 0; gapm = np.asarray(gaps) > 0
        dist = ndi.distance_transform_edt(~clm) * 0.5   # metres from the centreline
        prof = np.zeros((4096, 4096), np.float32)
        body = dist <= D['top_hw']
        prof[body] = -D['depth'] * np.clip((D['top_hw'] - dist[body]) / (D['top_hw'] - D['floor_hw']), 0, 1)
        sp = rearm & (dist > D['top_hw']) & (dist <= D['spoil_hw'])
        prof[sp] = D['spoil_h'] * np.sin(np.pi * (dist[sp] - D['top_hw']) / (D['spoil_hw'] - D['top_hw']))
        bm = ~rearm & (dist > D['top_hw']) & (dist <= D['berm_hw'])
        prof[bm] = D['berm_h'] * np.sin(np.pi * (dist[bm] - D['top_hw']) / (D['berm_hw'] - D['top_hw']))
        prof[gapm] = 0.0
        delta += _blur(prof, 1, 1)
        d1 = dist.reshape(2048, 2, 2048, 2).min((1, 3)); g1 = gapm.reshape(2048, 2, 2048, 2).max((1, 3)); r1m = rearm.reshape(2048, 2, 2048, 2).max((1, 3))
        soil[(d1 <= D['top_hw']) & ~g1] = TREN                                   # floor and walls: dug earth
        soil[(d1 > D['top_hw']) & (d1 <= D['spoil_hw']) & r1m & ~g1] = 11       # the spoil heap
        soil[(d1 > D['top_hw']) & (d1 <= D['berm_hw']) & ~r1m & ~g1] = 11
        bare_p = np.maximum(bare_p, 0.7 * _trample_profile(np.maximum(0.0, d1 - 4.0)))
        del clm, rearm, gapm, dist, prof, body, sp, bm, d1, g1, r1m
    h += delta
    del delta
    # ---- trampled ground round the works (vanilla MgG3: bare clay patches ~30 % above the background within 12 m of
    #      the trenches, fading out by 45 m), small patches: fine noise thresholded at the local probability
    if bare_p.any():
        g = TX.gnoise(soil.shape, origin, 2.5, 74) * 0.55 + TX.gnoise(soil.shape, origin, 1.0, 75) * 0.45
        zone = (bare_p > 0.01) & open_mask & ~np.isin(soil, (14, 11))
        if zone.any():
            q = np.quantile(g[zone], 0.5); s = np.std(g[zone]) or 1.0
            z = (g - q) / s                                   # ~N(0,1) in the zone
            from scipy.special import ndtri
            thr = ndtri(np.clip(1.0 - bare_p, 1e-4, 1 - 1e-4))
            soil[zone & (z > thr)] = 3
    # ---- dug positions: INF every ~4.2 m on the fire trenches (w 8.3 / 9.2), every 9 m on communication trenches
    #      (w 3.2), MG with a facing point every ~38 m on the strongpoint lines, GUN / MORT / rifle pits of the strongpoints
    for w in tr:
        comm = w.get('comm')
        for k, (x, y, nx, ny) in enumerate(_positions(w['pts'], 9.0 if comm else 4.2)):
            if not (4 <= x - x0 < 2044 and 4 <= y - y0 < 2044): continue
            recs.append(('INF', x - x0, y - y0, 3.2 if comm else (8.3 if k % 3 else 9.2)))
            if w.get('strongpoint') and k % 9 == 4: recs.append(('MG', x - x0, y - y0, 8.5, x - x0 + nx * 10.0, y - y0 + ny * 10.0))   # second point = facing (vanilla MG: 10 m)
    for w in hit:
        if w.get('sp_pits'):
            for (tag, px, py, ang) in _pits(w, x0, y0):
                if tag == 'MORT': recs.append(('MORT', px, py, 8.8))
                elif tag == 'GUN': recs.append(('GUN', px, py, 8.3, px + 15 * math.cos(ang), py + 15 * math.sin(ang)))   # facing outwards, 15 m
                else: recs.append(('INF', px, py, 8.3))
    for (tag, px, py, ang) in chain_pits: recs.append(('INF', px, py, 8.3))
    return [r for r in recs if 1.0 <= r[1] < 2047.0 and 1.0 <= r[2] < 2047.0 and (len(r) < 6 or (1.0 <= r[4] < 2047.0 and 1.0 <= r[5] < 2047.0))]

def _trample_profile(dist):
    """probability of a bare patch at `dist` m from the trace: 0.55 just outside the spoil, 0.3 at 12 m, 0 at 45 m"""
    p = np.where(dist <= 6.0, 0.55, np.where(dist <= 12.0, 0.55 - 0.25 * (dist - 6.0) / 6.0, 0.3 * np.clip((45.0 - dist) / 33.0, 0, 1)))
    return p.astype(np.float32)

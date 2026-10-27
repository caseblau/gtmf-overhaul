"""Villages and roads by example (27 Oct, user: 'the villages still look off ... same with roads').

The ground textures already come from Graviteam's own Petropolye cells (tools/texref.py); this module does the same for
the two things that were still drawn from invented rules:

  * HOMESTEADS - every house of the Petropolye village cells is cut out together with its yard: the house, sheds, front
    and side fences, gates, posts, firewood, haystacks, benches, garden trees and bushes, and the ground under them
    (soil, micro-tile weight, detail, grass) from the street edge back through the garden plot. The cut is made in the
    street's own frame (u along the street, v away from it), so a homestead can be set down along any of our streets,
    turned to the street direction.
  * ROAD STRIPS - the roads of the Petropolye cells are traced (centre lines of the pave tracks) and unrolled into straight
    strips 25 m wide: soil, micro-tile, detail and grass across the road for every metre of its length. Our roads are
    painted by bending these strips along the OSM lines, so the tracks wander, split and fade exactly as the game's do.

Everything is in cell pixels (1 px = 1 m); arrays are indexed [row, col] = [y, x] as the cell files store them, objects
use the same x / y. Object headings: rot = pi - (standard angle of the object's long axis), measured on the vanilla
fences, so turning a frame by phi (counter-clockwise in x / y) turns every object by -phi.
"""
import math, os
import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
import atf1

KEEP_OBJ = ('build', 'saray', 'fence', 'gates', 'kalitka', 'fpost', 'drova', 'seno_', 'skameyka', 'well', 'bochka', 'telega')
DROP_OBJ = ('farm', 'windmill', 'ostov', 'cross', 'pristan', 'boat')
ROAD_HALF = 12          # strip half width (m)
V0, VMAX = 3.0, 125.0   # homestead window: from the street edge to the back of the garden plot (m from the street axis)


def _grid(path, n=2048):
    return np.fromfile(path, np.uint8).reshape(n, n)


def _read_objects(path):
    import cellfmt as C
    return C.read_objects(path)


def _read_flora(path):
    import cellfmt as C
    return C.read_flora(path)


def thin(mask, max_iter=60):
    """Zhang-Suen thinning (numpy); a 1 px skeleton of a boolean mask"""
    img = np.pad(mask.astype(np.uint8), 1)
    for _ in range(max_iter):
        changed = False
        for step in (0, 1):
            P = img
            p2 = P[:-2, 1:-1]; p3 = P[:-2, 2:]; p4 = P[1:-1, 2:]; p5 = P[2:, 2:]
            p6 = P[2:, 1:-1]; p7 = P[2:, :-2]; p8 = P[1:-1, :-2]; p9 = P[:-2, :-2]
            c = P[1:-1, 1:-1]
            B = p2 + p3 + p4 + p5 + p6 + p7 + p8 + p9
            seq = [p2, p3, p4, p5, p6, p7, p8, p9, p2]
            A = sum(((seq[k] == 0) & (seq[k + 1] == 1)).astype(np.uint8) for k in range(8))
            if step == 0: m = (p2 * p4 * p6 == 0) & (p4 * p6 * p8 == 0)
            else: m = (p2 * p4 * p8 == 0) & (p2 * p6 * p8 == 0)
            rem = (c == 1) & (B >= 2) & (B <= 6) & (A == 1) & m
            if rem.any():
                img[1:-1, 1:-1][rem] = 0; changed = True
        if not changed: break
    return img[1:-1, 1:-1] > 0


def prune(sk, n=35):
    """remove spurs shorter than n px (end points peeled n times; the long lines lose n px at their ends)"""
    sk = sk.copy()
    k = np.ones((3, 3), np.uint8); k[1, 1] = 0
    for _ in range(n):
        nbc = ndi.convolve(sk.astype(np.uint8), k, mode='constant')
        end = sk & (nbc <= 1)
        if not end.any(): break
        sk[end] = False
    return sk


def trace_paths(sk, min_len=40):
    """split a skeleton into pixel paths between end points / junctions; returns list of (N, 2) arrays [x, y]"""
    ys, xs = np.nonzero(sk); pts = set(zip(ys.tolist(), xs.tolist()))
    def nb(p): return [(p[0] + a, p[1] + b) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a or b) and (p[0] + a, p[1] + b) in pts]
    deg = {p: len(nb(p)) for p in pts}
    nodes = {p for p in pts if deg[p] != 2}
    used = set(); paths = []
    for s in nodes:
        for n in nb(s):
            if (s, n) in used: continue
            path = [s, n]; used.add((s, n)); used.add((n, s)); prev, cur = s, n
            while cur not in nodes:
                nx = [q for q in nb(cur) if q != prev and (cur, q) not in used]
                if not nx: break
                q = nx[0]; used.add((cur, q)); used.add((q, cur)); path.append(q); prev, cur = cur, q
            if len(path) >= min_len: paths.append(np.array([(x, y) for (y, x) in path], np.float32))
    return paths


def _smooth_path(p, w=9):
    if len(p) < w + 2: return p
    k = np.ones(w) / w
    x = np.convolve(np.pad(p[:, 0], w // 2, mode='edge'), k, 'valid'); y = np.convolve(np.pad(p[:, 1], w // 2, mode='edge'), k, 'valid')
    return np.stack([x, y], 1)


def _resample_path(p, step=1.0):
    d = np.hypot(*np.diff(p, axis=0).T); s = np.concatenate([[0], np.cumsum(d)])
    if s[-1] < step * 3: return None
    t = np.arange(0, s[-1], step)
    return np.stack([np.interp(t, s, p[:, 0]), np.interp(t, s, p[:, 1])], 1)


class Library:
    def __init__(self, ref_dirs, verbose=True):
        self.homesteads = []; self.roads = []
        for d in ref_dirs:
            if not os.path.exists(os.path.join(d, 'obj_quads.cell.loc_def.bin')): continue
            self._load_cell(d)
        if verbose:
            kinds = {}
            for r in self.roads: kinds[r['kind']] = kinds.get(r['kind'], 0) + len(r['soil'])
            print('  vstamps: %d homesteads, road strips (m): %s' % (len(self.homesteads), kinds), flush=True)

    # ------------------------------------------------------------------ extraction
    def _load_cell(self, d):
        p = lambda e: os.path.join(d, e + '.cell.loc_def.bin')
        mat = _grid(p('mat_map')); soil = mat & 15; hi = mat >> 4
        det = atf1.top(p('det_map')); grass = _grid(p('grass_map'))
        objs = _read_objects(p('obj_quads'))
        fx, fy, fr, ft = _read_flora(p('flora_quads'))
        houses = [(x, y) for (t, n, x, y, *r) in objs if n.startswith('build') and 'builds.cfgpack' in (t or '')]
        if not houses and not (soil == 10).any(): return
        # road centre lines: the pave tracks (soil 10), parallel tracks merged, yard patches left out (small components)
        pave = soil == 10
        m = ndi.binary_closing(ndi.binary_dilation(pave, iterations=2), iterations=2)
        lab, nl = ndi.label(m)
        if nl:
            sizes = ndi.sum(m, lab, range(1, nl + 1))
            sl = ndi.find_objects(lab)
            big = np.zeros(nl + 1, bool)
            for k in range(nl):
                h = sl[k][0].stop - sl[k][0].start; w = sl[k][1].stop - sl[k][1].start
                big[k + 1] = math.hypot(h, w) > 250
            m = big[lab]
        sk = prune(thin(m), 35)
        paths = [_smooth_path(q) for q in trace_paths(sk, 40)]
        hx = np.array([h[0] for h in houses], np.float32) if houses else np.zeros(0, np.float32)
        hy = np.array([h[1] for h in houses], np.float32) if houses else np.zeros(0, np.float32)
        # ---- road strips
        for q in paths:
            q = _resample_path(q, 1.0)
            if q is None or len(q) < 80: continue
            q = q[15:-15]   # junction ends left out
            if len(q) < 50: continue
            t = np.gradient(q, axis=0); t /= np.maximum(np.hypot(t[:, 0], t[:, 1]), 1e-6)[:, None]
            n = np.stack([-t[:, 1], t[:, 0]], 1)
            off = np.arange(-ROAD_HALF, ROAD_HALF + 1, dtype=np.float32)
            X = q[:, 0][:, None] + n[:, 0][:, None] * off[None]; Y = q[:, 1][:, None] + n[:, 1][:, None] * off[None]
            xi = np.clip(np.rint(X).astype(int), 0, 2047); yi = np.clip(np.rint(Y).astype(int), 0, 2047)
            S = soil[yi, xi]
            # classify: village street (houses within 45 m), main road (2+ tracks in the core), field track
            near = 0.0
            if len(hx):
                T = cKDTree(np.stack([hx, hy], 1)); dd, _ = T.query(q[::10]); near = float((dd < 45).mean())
            core = S[:, ROAD_HALF - 5:ROAD_HALF + 6] == 10
            runs = (np.diff(core.astype(np.int8), axis=1) == 1).sum(1) + core[:, 0]
            kind = 'street' if near > 0.4 else ('main' if np.median(runs) >= 2 else 'track')
            # strips crossing fields keep their crop pixels out of the copy (handled when painting)
            self.roads.append(dict(kind=kind, soil=S.astype(np.uint8), hi=hi[yi, xi].astype(np.uint8), det=det[yi, xi].astype(np.uint8),
                                   grass=grass[yi, xi].astype(np.uint8), cell=os.path.basename(d.rstrip('/\\'))))
        # ---- homesteads. The street frame comes from the house's gate: the gate stands in the front fence, so its
        # heading is the street direction, and the street axis lies a few metres beyond it (first pave pixel + 2 m)
        if not houses: return
        gates = [(x, y, r) for (t, n, x, y, r, *_) in objs if n.startswith(('gates', 'kalitka'))]
        if not gates: return
        G = np.array([(g[0], g[1]) for g in gates], np.float32); Tg = cKDTree(G)
        keep_o = [(t, n, x, y, r) for (t, n, x, y, r, *_) in objs if n.startswith(KEEP_OBJ) and not n.startswith(DROP_OBJ)]
        ox = np.array([o[2] for o in keep_o], np.float32); oy = np.array([o[3] for o in keep_o], np.float32)
        for (x, y) in houses:
            dd, j = Tg.query((x, y))
            if dd > 32: continue
            gx, gy, gr = gates[j]
            th = math.pi - gr   # standard angle of the fence line through the gate
            u = np.array([math.cos(th), math.sin(th)], np.float32); v = np.array([-u[1], u[0]], np.float32)
            if np.dot((x - gx, y - gy), v) < 0: v = -v
            dp = None
            for t_ in range(1, 22):
                px, py = int(round(gx - v[0] * t_)), int(round(gy - v[1] * t_))
                if 0 <= px < 2048 and 0 <= py < 2048 and soil[py, px] == 10 and t_ > 2: dp = t_; break
            c = np.array([gx, gy], np.float32) - v * ((dp if dp else 6) + 2.0)
            # frame (u, v) right handed with v towards the house: if not, flip u (no mirroring)
            if u[0] * v[1] - u[1] * v[0] < 0: u = -u
            # neighbours on the same side
            ru = (hx - c[0]) * u[0] + (hy - c[1]) * u[1]; rv = (hx - c[0]) * v[0] + (hy - c[1]) * v[1]
            hu0 = (x - c[0]) * u[0] + (y - c[1]) * u[1]
            same = (rv > 4) & (rv < 60) & (np.abs(ru - hu0) > 6)
            plus = ru[same & (ru > hu0)]; minus = ru[same & (ru < hu0)]
            hp = min(40.0, (plus.min() - hu0) / 2) if len(plus) else 32.0
            hm = min(40.0, (hu0 - minus.max()) / 2) if len(minus) else 32.0
            if hp < 12 or hm < 12: continue
            behind = rv[(rv > 45) & (np.abs(ru - hu0) < 40)]
            vmax = min(VMAX, behind.min() - 25) if len(behind) else VMAX
            if vmax < 50: continue
            # raster window [v, u] at 1 m, u from -hm..hp (relative to the house), v from V0..vmax
            uu = np.arange(-hm, hp, 1.0, dtype=np.float32) + hu0; vv = np.arange(V0, vmax, 1.0, dtype=np.float32)
            U, Vv = np.meshgrid(uu, vv)
            X = c[0] + U * u[0] + Vv * v[0]; Y = c[1] + U * u[1] + Vv * v[1]
            ok = (X >= 0) & (X < 2047) & (Y >= 0) & (Y < 2047)
            if ok.mean() < 0.9: continue
            xi = np.clip(np.rint(X).astype(int), 0, 2047); yi = np.clip(np.rint(Y).astype(int), 0, 2047)
            # objects / flora in the window, in frame coordinates relative to (house u, 0)
            def frame(px, py):
                du = (px - c[0]) * u[0] + (py - c[1]) * u[1] - hu0; dv = (px - c[0]) * v[0] + (py - c[1]) * v[1]
                return du, dv
            du, dv = frame(ox, oy); sel = (du >= -hm) & (du < hp) & (dv >= V0) & (dv < vmax)
            phi = math.atan2(u[1], u[0])
            ob = [(keep_o[k][0], keep_o[k][1], float(du[k]), float(dv[k]), float(keep_o[k][4]) + phi) for k in np.flatnonzero(sel)]
            fdu, fdv = frame(fx, fy); fs = (fdu >= -hm) & (fdu < hp) & (fdv >= V0) & (fdv < vmax)
            fl = np.stack([fdu[fs], fdv[fs], ft[fs].astype(np.float32)], 1)
            self.homesteads.append(dict(hm=hm, hp=hp, v0=V0, v1=vmax, soil=soil[yi, xi].astype(np.uint8), hi=hi[yi, xi].astype(np.uint8),
                                        det=det[yi, xi].astype(np.uint8), grass=grass[yi, xi].astype(np.uint8), ok=ok, objs=ob, flora=fl,
                                        cell=os.path.basename(d.rstrip('/\\')), at=(float(x), float(y))))


# ---------------------------------------------------------------------------------------------- placing homesteads
def _h32(*v):
    h = 0x811c9dc5
    for q in v: h = ((h ^ (int(q) & 0xffffffff)) * 16777619) & 0xffffffff
    h ^= h >> 15; h = (h * 2246822519) & 0xffffffff; h ^= h >> 13
    return h


def trim_wet(lib):
    """garden plots that run down to the Petropolye river: cut the window where the marsh / water ground begins, so the
    upland villages of our block do not get a strip of river bank behind every garden"""
    for h in lib.homesteads:
        wet = (h['soil'] == 1).mean(1)
        rows = np.flatnonzero(wet > 0.15)
        cut = rows[0] if len(rows) else len(wet)
        cut = max(cut, 40)
        if cut < len(wet):
            for k in ('soil', 'hi', 'det', 'grass', 'ok'): h[k] = h[k][:cut]
            h['v1'] = h['v0'] + cut
            h['objs'] = [o for o in h['objs'] if o[3] < h['v1']]
            h['flora'] = h['flora'][h['flora'][:, 1] < h['v1']] if len(h['flora']) else h['flora']
        fr = [o[3] for o in h['objs'] if o[1].startswith('fence') and abs(math.sin(math.pi - o[4])) < 0.35 and o[3] < 30 and abs(o[2]) < 25]
        h['front_v'] = float(np.median(fr)) if fr else 10.0
        hs = [o for o in h['objs'] if o[1].startswith('build')]
        h['house_v'] = float(np.median([o[3] for o in hs])) if hs else 18.0


def place_street(lib, pp, origin, in_ext, house_ok, allowed, soil, buf, objs, flora, salt=0, taken=None, min_front=8.5):
    """walk one street (cell px polyline) and set homesteads down on both sides.
    in_ext(x, y): is the point inside the village extent; house_ok(x, y): may a house stand there;
    allowed: (2048, 2048) bool, where stamp ground may be painted; buf: dict(mask, hi, det, grass) layer buffers."""
    if len(pp) < 2: return 0
    P = np.array(pp, np.float64)
    seg = np.hypot(*np.diff(P, axis=0).T); S = np.concatenate([[0], np.cumsum(seg)]); L = S[-1]
    if L < 30: return 0
    def at(s):
        s = min(max(s, 0.0), L - 1e-3); k = int(np.searchsorted(S, s, 'right') - 1); k = min(k, len(seg) - 1)
        t = (s - S[k]) / max(seg[k], 1e-6); p = P[k] + (P[k + 1] - P[k]) * t
        # tangent smoothed over +-12 m (the OSM vertices make kinks)
        a = P[max(0, int(np.searchsorted(S, s - 12) - 1))]; b = P[min(len(P) - 1, int(np.searchsorted(S, s + 12)))]
        d = b - a; n = math.hypot(*d) or 1.0
        return p, d / n
    g0 = (round(pp[0][0] + origin[0]), round(pp[0][1] + origin[1]))   # global street seed: both cells walk it the same way
    nh = len(lib.homesteads); placed = 0
    for side in (1.0, -1.0):
        runs = []   # (s0, s1, front offset, gate s) of the homesteads on this side, in street order
        s = 4.0 + (_h32(g0[0], g0[1], side > 0, 7, salt) % 20); k = 0
        while s < L - 10:
            hh = lib.homesteads[_h32(g0[0], g0[1], side > 0, k, salt) % nh]; k += 1
            sc = s + hh['hm']
            if sc > L - 5: break
            c, t = at(sc)
            u = t * side; v = np.array([-t[1], t[0]]) * side
            hx, hy = c + v * hh['house_v']
            if not in_ext(c[0] + v[0] * 15, c[1] + v[1] * 15) or not house_ok(hx, hy) or \
               (taken is not None and any((hx - a) ** 2 + (hy - b) ** 2 < 34.0 ** 2 for a, b in taken)):
                s += 6.0; continue
            r = _h32(g0[0], g0[1], side > 0, k, salt + 1)
            if r % 100 < 12:   # an empty plot now and then
                s = sc + hh['hp'] + 15 + (r >> 8) % 25; continue
            contiguous = bool(runs) and sc - hh['hm'] - runs[-1][1] < 8.0
            fv = max(min_front, hh['front_v'])
            # no homestead over another one (junctions, where the yards of two streets meet)
            gu, gv = np.meshgrid(np.arange(-hh['hm'] + 3, hh['hp'] - 3, 4.0), np.arange(fv + 2, fv + 45, 4.0))
            qx = (c[0] + u[0] * gu + v[0] * gv).astype(int); qy = (c[1] + u[1] * gu + v[1] * gv).astype(int)
            inn = (qx >= 0) & (qx < 2048) & (qy >= 0) & (qy < 2048)
            if inn.any() and buf['mask'][qy[inn], qx[inn]].mean() > 0.12:
                s += 6.0; continue
            _stamp(hh, c, u, v, allowed, soil, buf, objs, flora, front_v=fv, drop_left=contiguous)
            if taken is not None: taken.append((hx, hy))
            runs.append((sc - hh['hm'] + 1.0, sc + hh['hp'] - 1.0, fv, sc + 3.0 + (r >> 4) % 4))
            placed += 1
            s = sc + hh['hp'] + ((r >> 8) % 7)
        # the front fence: one continuous run along the street in front of each row of homesteads (vanilla Petropolye:
        # fence2a every 2.6 m with a gate at every yard), following the street's curve, joined across gaps under 12 m
        node = ('fence2a', 'fence2a', 'fence2a', 'fence4a')[_h32(g0[0], g0[1], side > 0, 99) % 4]
        for n, (a0, a1, fv, gs) in enumerate(runs):
            b1 = a1
            if n + 1 < len(runs) and runs[n + 1][0] - a1 < 12.0: b1 = runs[n + 1][0]
            _front(objs, at, side, a0, b1, fv, gs, node, post0=(n == 0 or a0 - runs[n - 1][1] >= 12.0), post1=(b1 == a1))
    return placed


def _front(objs, at, side, s0, s1, off, gate_s, node, post0=True, post1=True):
    TF, TP = 'tabs\\fences.cfgpack', 'tabs\\posts.cfgpack'
    def pose(s):
        c, t = at(s); v = np.array([-t[1], t[0]]) * side; p = c + v * off
        return p, math.atan2(t[0], t[1]) + math.pi / 2
    if post0:
        p, a = pose(s0); objs.append((TP, 'fpost2', float(p[0]), float(p[1]), float(a), 'front'))
    t = s0 + 1.3
    while t < s1 - 0.5:
        p, a = pose(t)
        if abs(t - gate_s) < 1.3: objs.append((TF, 'gates1', float(p[0]), float(p[1]), float(a), 'front'))
        elif abs(t - gate_s - 2.6) < 1.3: objs.append((TF, 'kalitka2', float(p[0]), float(p[1]), float(a), 'front'))
        else: objs.append((TF, node, float(p[0]), float(p[1]), float(a), 'front'))
        t += 2.6
    if post1:
        p, a = pose(s1); objs.append((TP, 'fpost2', float(p[0]), float(p[1]), float(a), 'front'))


FENCE = ('fence', 'gates', 'kalitka', 'fpost')


def _stamp(h, c, u, v, allowed, soil, buf, objs, flora, front_v=None, drop_left=False):
    hm, hp, v0, v1 = h['hm'], h['hp'], h['v0'], h['v1']
    if front_v is not None: c = c + v * (front_v - h.get('front_v', 10.0))   # the whole homestead moves so its front fence line lies at front_v
    prev_mask = buf['mask'].copy() if buf.get('mask') is not None else np.zeros((2048, 2048), bool)
    corners = [c + u * a + v * b for a in (-hm, hp) for b in (v0, v1)]
    xs = [q[0] for q in corners]; ys = [q[1] for q in corners]
    x0, x1 = max(0, int(min(xs))), min(2048, int(max(xs)) + 1); y0, y1 = max(0, int(min(ys))), min(2048, int(max(ys)) + 1)
    phi = math.atan2(u[1], u[0])
    if x0 < x1 and y0 < y1:
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float64)
        dx = xx + 0.5 - c[0]; dy = yy + 0.5 - c[1]
        du = dx * u[0] + dy * u[1]; dv = dx * v[0] + dy * v[1]
        j = np.floor(du + hm).astype(int); i = np.floor(dv - v0).astype(int)
        H, W = h['soil'].shape
        ok = (i >= 0) & (i < H) & (j >= 0) & (j < W)
        ii = np.clip(i, 0, H - 1); jj = np.clip(j, 0, W - 1)
        ok &= h['ok'][ii, jj] & allowed[y0:y1, x0:x1]
        # ragged window edge: within 4 m of the side / back edges the pixel is taken with a falling probability
        e = np.minimum.reduce([du + hm, hp - du, v1 - dv])
        noise = ((xx.astype(np.int64) * 73856093) ^ (yy.astype(np.int64) * 19349663)) % 1000 / 1000.0
        ok &= (e > 4) | (noise * 4 < e)
        if ok.any():
            sy, sx = np.nonzero(ok); ty = sy + y0; tx = sx + x0; si = ii[sy, sx]; sj = jj[sy, sx]
            soil[ty, tx] = h['soil'][si, sj]
            buf['mask'][ty, tx] = True; buf['hi'][ty, tx] = h['hi'][si, sj]; buf['det'][ty, tx] = h['det'][si, sj]; buf['grass'][ty, tx] = h['grass'][si, sj]
    fv0 = h.get('front_v', 10.0)
    for (tab, n, du, dv, r) in h['objs']:
        if n.startswith(FENCE) or n.startswith(('build', 'saray')):
            p_ = c + u * du + v * dv
            if 0 <= p_[0] < 2048 and 0 <= p_[1] < 2048 and prev_mask[int(p_[1]), int(p_[0])]: continue   # inside an earlier homestead
        if n.startswith(FENCE):
            par = abs(math.sin(math.pi - r)) < 0.35   # parallel to the street
            perp = abs(math.cos(math.pi - r)) < 0.35
            if n.startswith('fence') and not (par or perp): continue   # diagonal pieces (plot corners of the source village) look wrong along our streets
            if dv < fv0 + 4.0 and (par or not n.startswith('fence')): continue   # the source's front fence, gates and posts: redrawn along our street
            if dv < fv0 - 1.0: continue                                            # nothing between the street and the front fence
            if drop_left and du < -h['hm'] + 6.0 and not par: continue             # the neighbour's side fence already stands there
            if du < -h['hm'] - 1 or du > h['hp'] + 1: continue
        p = c + u * du + v * dv
        objs.append((tab, n, float(p[0]), float(p[1]), float(r - phi)))
    for (du, dv, t) in h['flora']:
        p = c + u * du + v * dv
        flora.append((float(p[0]), float(p[1]), int(t)))

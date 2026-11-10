r"""Superseded on 11 Nov by t3485_lp.py (the user's textured T-34-85 model); kept as the print-kit route.

T-34-85 (11 Nov, user): the game's own T-34 mod. 1942 (t34_42_utz) - hull, running gear, fittings, crew stations, damage
boxes - with only the turret, mantlet and gun taken from the user's purchased T-34-85 model (Downloads\T-34-85\Turret.stl, a
3D-print kit: one fused solid, about 1:29, peg under the turret, +x on the vehicle's left).

The 76 mm turret's nodes are dropped; the STL turret is cut into turret / mantlet / barrel, reduced to the game's budgets with
quadric simplification, mirrored into the game's hand and set on the T-34's turret ring.  Texture: a 2048 sheet whose top-left
quarter is the game's T-34 sheet (the kept geometry's uv halved, so it looks exactly as before) and the other three quarters
paint for the new parts, quilted from the old turret's painted areas of that sheet (sides with grime towards the bottom, roof,
gun).  Source files and outputs never go in the repo.

  python t3485.py <t34_42_utz mesh> <Turret.stl> <reg_t34_42_utz_dift> <bump_t34_42_utz_norsp> <out dir> [rtank_ostov01 mesh] [arm_t34_42_utz_dift armor]
"""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import bought as B, azg2, su122_mesh as SM, m3lee_mesh as OLD

S = 0.034                                   # STL units -> m: muzzle 2.05 m ahead of the hull front, as on the real tank
PEG = np.array([-4.12, 129.2])              # turret ring centre (the print peg) in STL x, y
BASE_Z = 159.3                              # underside of the turret casting (the peg is below)
RING = np.array([0.0, 0.472, 0.534])        # the game T-34's ring, 6 cm up (11 Nov, user: the 85 mm turret's wider base cut 5.6 cm into the hull roof)
TURRET_NODES = ('d_head', 'd_gunmask', 'd_gun', 'd_hatch_02', 'd_hatch_03', 'd_headparts_early', 'd_headparts_late',
                'd_headporuchni', 'd_minigun', 'd_sight_01')
MATERIAL = (b't34_42_utz_dift', b't3485__utz_dift')   # same length, the same 'tz_dift' tail: the second material (tz_dift) is stored as that tail
BUDGET = {'tur': (40000, 9000, 3000), 'mask': (1800, 700, 250), 'bar': (600, 250, 90)}   # 11 Nov (user's close-up): 7000 left the cast turret rippled
DARK_UV = np.array((0.02, 0.98))
CUPX, CUPZ = -(6.45 - PEG[0]) * S, -(138.5 - PEG[1]) * S + RING[2]     # the commander's cupola (turret left rear)
# 11 Nov (user: do the periscopes move): the three MK-4 periscopes, found on the roof height map - the gunner's left front, the
# loader's right front, the commander's in the cupola lid; each becomes its own turning node
PERI = {'d_sight_01': (-0.55, 0.75), 'd_sight_02': (0.47, 0.95), 'd_sight_03': (CUPX, CUPZ + 0.07)}
# 11 Nov (user): the loader's hatch (front hinge) and the cupola lid (rear hinge) open; xdir points from the hinge into the lid
LIDS = {'d_hatch_03': dict(c=(0.355, 0.27), r=0.262, xdir=(0, 0, -1.0), keep=((0.26, 0.45), (0.36, 0.53))),
        'd_hatch_04': dict(c=(CUPX, CUPZ), r=0.30, xdir=(0, 0, 1.0), keep=None, roof=1.36)}   # the cupola's rim, not the turret roof round it
# the spare track links (user: remove the tracks at the railings): (box lo, box hi, outward direction of the wall under them)
LINKS = [((-1.10, 0.76, -0.47), (-0.80, 1.09, 0.04), (-1.0, 0, 0)),     # left side rail
         ((-0.29, 0.60, -1.25), (0.29, 1.15, -0.80), (0, 0, -1.0))]     # rear stack
# 11 Nov (user: real T-34-85 values): the armour map stores 2 x mm; four free 4x4 blocks of the T-34's map get the turret's
# plates - 90 mm front and mantlet, 75 mm sides, 52 mm rear, 20 mm roof (the 76 mm turret had 52 / 52 / 52 / 20)
ARM_BLOCKS = {'front': (18, 22, 180), 'side': (18, 24, 150), 'rear': (18, 26, 104), 'roof': (19, 22, 40)}
ARM85 = {k: ((bx * 4 + 2) / 256.0, (by * 4 + 2) / 256.0) for k, (by, bx, v) in ARM_BLOCKS.items()}            # a black texel in an unused corner of the roof quarter: the inside behind the mantlet


def load_stl(path):
    n = (os.path.getsize(path) - 84) // 50
    a = np.fromfile(path, dtype=np.dtype([('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')]), count=n, offset=84)
    P = a['v'].astype(np.float64)
    V, inv = np.unique(np.round(P.reshape(-1, 3), 4), axis=0, return_inverse=True)
    return V, inv.reshape(-1, 3)


def to_game(V):
    """STL -> game metres: x mirrored (the kit has +x on the vehicle's left, the game on its right), z up -> y, -y forward -> z"""
    return np.c_[-(V[:, 0] - PEG[0]) * S, (V[:, 2] - BASE_Z) * S + RING[1], -(V[:, 1] - PEG[1]) * S + RING[2]]


def reduce(V, F, target):
    import fast_simplification as fs
    if len(F) <= target: return V, F
    v, f = fs.simplify(V.astype(np.float32), F.astype(np.int32), target_reduction=1.0 - target / len(F), agg=4)   # 11 Nov (user's slivers): the default agg 7 folded ~40 faces, 4 none
    return v.astype(np.float64), f


def part(V, F, uvf):
    """game-space triangles -> Part: windings reversed (the mirror), normals rebuilt, planar uv per face"""
    P = V[F][:, ::-1]
    N = B.recompute_normals(P, 35.0)
    return B.Part(P, uvf(P), N)


# ---- uv: planar projection by the face's main axis into the three paint quarters of the 2048 sheet
def uv_turret(P):
    n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]); a = np.argmax(np.abs(n), 1); T = np.zeros(P.shape[:2] + (2,))
    side, top = a != 1, a == 1
    # walls: u along the wall (z for the sides, x for front / back), v down from 1.8 m (the grime gets heavier downwards), 4 m per quarter
    u = np.where((a == 0)[:, None], P[..., 2], P[..., 0]); v = 1.8 - P[..., 1]
    T[side, :, 0] = 0.5 + np.clip((u[side] + 2.0) / 4.0, 0, 1) * 0.5; T[side, :, 1] = np.clip(v[side] / 4.0, 0, 1) * 0.5
    T[top, :, 0] = np.clip((P[top][..., 0] + 2.0) / 4.0, 0, 1) * 0.5; T[top, :, 1] = 0.5 + np.clip((P[top][..., 2] + 1.5) / 4.0, 0, 1) * 0.5
    return T


def uv_gun(P):
    n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]); a = np.argmax(np.abs(n), 1); T = np.zeros(P.shape[:2] + (2,))
    u = P[..., 2]; v = np.where((a == 0)[:, None], P[..., 1], P[..., 0])          # along the barrel, around it
    T[..., 0] = 0.5 + np.clip((u - 0.8) / 4.6, 0, 1) * 0.5; T[..., 1] = 0.5 + np.clip((v + 1.0) / 4.6, 0, 1) * 0.5
    return T


def uv_mantlet(P):
    """planar by the face's main axis, 2 m per quarter (11 Nov: the barrel's along-the-gun mapping smeared the mantlet's front)"""
    n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]); a = np.argmax(np.abs(n), 1); T = np.zeros(P.shape[:2] + (2,))
    u = np.where((a == 0)[:, None], P[..., 2], P[..., 0]); v = np.where((a == 1)[:, None], P[..., 2], P[..., 1])
    T[..., 0] = 0.5 + np.clip((u + 1.0) / 2.0, 0, 1) * 0.5; T[..., 1] = 0.5 + np.clip(v / 2.0 - 0.2, 0, 1) * 0.5
    return T


def turret_parts(stl):
    V, F = load_stl(stl)
    c = V[F].mean(1)
    keep = c[:, 2] > BASE_Z - 0.2                                                     # the print peg goes
    keep &= ~((np.abs(c[:, 0] - 14.05) < 1.2) & (np.abs(c[:, 1] - 128.85) < 1.2) & (c[:, 2] > 186.0))   # the aerial (thin mast)
    F = F[keep]; c = c[keep]
    far = V[V[:, 1] < 40]; bore = far[:, [0, 2]].mean(0)                               # bore axis from the barrel's front half
    r = np.hypot(c[:, 0] - bore[0], c[:, 2] - bore[1])
    bar = (c[:, 1] < 88.0) & (r < 2.9)                                                 # the barrel only: its sleeve (r 4-5) is the mantlet's and does not recoil (11 Nov, user)
    mask = ~bar & (c[:, 1] < 97.0) & (np.abs(c[:, 0] - bore[0]) < 17.5) & (c[:, 2] > 160.5) & (c[:, 2] < 178.0)   # the cast mantlet
    tur = ~bar & ~mask
    G = to_game(V)
    cg = G[F].mean(1); peri = {}; taken = np.zeros(len(F), bool)
    for nm, (gx, gz) in PERI.items():
        d = np.hypot(cg[:, 0] - gx, cg[:, 2] - gz); ring = (d > 0.15) & (d < 0.24)
        base = float(np.median(cg[ring, 1])) if ring.any() else float(cg[d < 0.15, 1].min())
        hi = (d < 0.15) & (cg[:, 1] > base + 0.03); cx, cz = float(cg[hi, 0].mean()), float(cg[hi, 2].mean())
        d = np.hypot(cg[:, 0] - cx, cg[:, 2] - cz); sel = (d < 0.12) & (cg[:, 1] > base + 0.008) & tur
        taken |= sel; f = F[sel]; used = np.unique(f); remap = np.full(len(V), -1); remap[used] = np.arange(len(used))
        lods = [part(*reduce(G[used], remap[f], t), uv_turret) for t in (60, 400, 160, 60)]
        peri[nm] = (lods, np.array([cx, base, cz]), float(G[used][:, 1].max()))
        print(nm, 'periscope at', np.round(peri[nm][1], 3), 'top', round(peri[nm][2], 3), 'faces', int(sel.sum()))
    tur &= ~taken
    bore_g = to_game(np.array([[bore[0], 0.0, bore[1]]]))[0]
    trun = np.array([bore_g[0], bore_g[1], to_game(np.array([[0, 103.0, 0]]))[0][2]])   # trunnion inside the turret front
    muz = to_game(np.array([[bore[0], V[:, 1].min(), bore[1]]]))[0]
    out = {}
    # spare track links: the faces standing more than 1 cm proud of the wall plane fitted round each box; a painted patch on the
    # plane closes whatever the links had fused over
    P3 = G[F]; nf = -np.cross(P3[:, 1] - P3[:, 0], P3[:, 2] - P3[:, 0]); nf /= np.linalg.norm(nf, axis=1, keepdims=True) + 1e-12   # outward (the mirror reversed the windings)
    patches = []
    for lo, hi, out_ in LINKS:
        lo, hi, out_ = np.array(lo), np.array(hi), np.array(out_) / np.linalg.norm(out_)
        inb = np.all((cg >= lo) & (cg <= hi), 1); ring = np.all((cg >= lo - 0.10) & (cg <= hi + 0.10), 1) & ~inb & (nf @ out_ > 0.7) & tur
        q = cg[ring]; c0 = q.mean(0); _, _, vt = np.linalg.svd(q - c0); nn = vt[2] * np.sign(vt[2] @ out_)
        rem = inb & ((cg - c0) @ nn > 0.010) & tur; tur &= ~rem
        cb = (lo + hi) / 2; cb = cb - ((cb - c0) @ nn) * nn - nn * 0.004
        e1 = np.cross(nn, [0, 1.0, 0]); e1 /= np.linalg.norm(e1); e2 = np.cross(e1, nn); ext = (hi - lo) / 2
        patches.append(B.quad(cb, e1 * abs(ext @ e1) * 1.05, e2 * abs(ext @ e2) * 1.05, nn, (0.75, 0.25)))
        print('track links removed', int(rem.sum()), 'faces; wall normal', np.round(nn, 2))
    # the lids: everything inside the hatch circle down to 3 cm under the surrounding roof; a dark box closes the opening
    lids = {}
    for nm, L_ in LIDS.items():
        cx, cz = L_['c']; d = np.hypot(cg[:, 0] - cx, cg[:, 2] - cz); r_ = L_['r']
        ann = (d > r_ + 0.02) & (d < r_ + 0.10) & (nf[:, 1] > 0.6); roof_y = L_.get('roof') or float(np.median(cg[ann, 1]))
        sel = (d < r_) & (cg[:, 1] > roof_y - (0.0 if L_.get('roof') else 0.03)) & tur
        if L_['keep']: sel &= ~((cg[:, 0] > L_['keep'][0][0]) & (cg[:, 0] < L_['keep'][0][1]) & (cg[:, 2] > L_['keep'][1][0]) & (cg[:, 2] < L_['keep'][1][1]))
        tur &= ~sel; f = F[sel]; used = np.unique(f); remap = np.full(len(V), -1); remap[used] = np.arange(len(used))
        top = float(G[used][:, 1].max()); xd = np.array(L_['xdir']); hinge = np.array([cx, top, cz]) - xd * r_
        lods = [part(*reduce(G[used], remap[f], t), uv_turret) for t in (120, 2400, 800, 250)]
        hb_ = r_ * (0.98 if L_.get('roof') is None else 0.66); dark = B.dark_box((cx, roof_y - 0.005, cz), (0, 1.0, 0), (1.0, 0, 0), hb_, hb_, 0.35, DARK_UV)   # inside the cupola's wall
        lids[nm] = (lods, hinge, xd, top, roof_y, dark); print(nm, 'lid faces', int(sel.sum()), 'roof', round(roof_y, 3), 'top', round(top, 3), 'hinge', np.round(hinge, 3))
    for key, sel, uvf in (('tur', tur, uv_turret), ('mask', mask, uv_mantlet), ('bar', bar, uv_gun)):
        f = F[sel]; used = np.unique(f); remap = np.full(len(V), -1); remap[used] = np.arange(len(used)); vv, ff = G[used], remap[f]
        lods = []
        for t in BUDGET[key]:
            v_, f_ = reduce(vv, ff, t); lods.append(part(v_, f_, uvf))
        hv, hf = reduce(vv, ff, {'tur': 700, 'mask': 160, 'bar': 60}[key]); lods.insert(0, part(hv, hf, uvf))
        out[key] = lods; print(key, 'source tris', len(f), '-> lods', [len(p) for p in lods])
    return out, trun, muz, bore_g, peri, lids, patches


def build(t34, stl):
    K = SM.Src(t34); arm = OLD.arm_points(K)
    parts, TRUN, MUZ, BORE, PERIS, LIDS_, PATCHES = turret_parts(stl)
    nodes = []
    def add(name, kind, parent, M, geo=None): nodes.append(dict(name=name, kind=kind, parent=parent, M=M, geo=geo or {}))
    def tr(p): M = np.eye(4); M[3, :3] = p; return M
    def pname(n):
        p = n['parent']; return K.nodes[p]['name'] if p is not None and p < len(K.nodes) and K.nodes[p]['name'] != 's_root' else None
    def under_head(n):
        while n is not None:
            if n['name'] == 'd_head': return True
            p = n['parent']; n = K.nodes[p] if p is not None and p < len(K.nodes) else None
        return False
    world = {n['name']: n['world'][3, :3].copy() for n in K.nodes}
    # the game T-34 as it is, minus the 76 mm turret's visual nodes; its uv into the top-left quarter of the 2048 sheet
    for n in K.nodes[1:]:
        nm = n['name']
        if nm in TURRET_NODES or (under_head(n) and nm.startswith('d_')): continue
        geo = {}
        for L in range(4):
            if (nm, L) in K.geo:
                A, Fv = K.geo[(nm, L)]; A = A.copy()
                if L > 0: A[:, 3:5] *= 0.5
                geo[L] = (A, Fv)
        if under_head(n):   # turret sockets, damage boxes and cameras: kept, re-hung below
            continue
        add(nm, n['kind'], pname(n), K.local(nm), geo)
    def g(lods, pivot):
        return {L: lods[L].moved(pivot).gxt() for L in (1, 2, 3)}
    # 11 Nov (user: light through the seams round the mantlet): the mantlet is cut out of the fused turret, so its outline leaves
    # open seams; a dark box behind the turret's front opening shows shadow there instead of the far side of the world
    zf = -(97.0 - PEG[1]) * S + RING[2]
    PLUG = B.dark_box((BORE[0], BORE[1] - 0.02, zf + 0.04), (0, 0, 1.0), (1.0, 0, 0), 0.45, 0.21, 0.66, DARK_UV)   # right behind the mantlet, narrower than it: edges hidden, side walls close the gap   # set back inside the cut so its edges stay hidden
    tl = parts['tur']; ml = parts['mask']; bl = parts['bar']
    TV = tl[1].P.reshape(-1, 3)
    def roof(x, z, r=0.12):
        q = TV[np.hypot(TV[:, 0] - x, TV[:, 2] - z) < r]; return float(q[:, 1].max()) if len(q) else 1.45
    def wall(y, z, r=0.10):
        q = TV[(np.abs(TV[:, 1] - y) < r) & (np.abs(TV[:, 2] - z) < r)]; return float(np.abs(q[:, 0]).max()) if len(q) else 0.95
    # roof plates under the periscopes (the turning housings leave their footprint open), in the roof paint
    feet = [B.quad(c_ + [0, -0.002, 0], (0.12, 0, 0), (0, 0, 0.12), (0, 1.0, 0), (0.25, 0.75)) for k_, (_, c_, _) in PERIS.items() if k_ != 'd_sight_03']   # the cupola's sits on the opening lid
    add('d_head', 4, 'd_hull', tr(RING), {0: OLD.hit(*tl[0].moved(RING).plain(), ARM85), **{L: B.join([tl[L], PLUG] + feet + PATCHES + [v[5] for v in LIDS_.values()]).moved(RING).gxt() for L in (1, 2, 3)}})
    add('d_gunmask', 4, 'd_head', tr(TRUN - RING), {0: OLD.hit(*ml[0].moved(TRUN).plain(), ARM85, 'front'), **g(ml, TRUN)})
    add('d_gun', 4, 'd_gunmask', np.eye(4), {0: OLD.hit(*bl[0].moved(TRUN).plain(), ARM85, 'roof'), **g(bl, TRUN)})
    def backed(p, t=0.008):
        q = p.moved((0, t, 0)); return B.join([p, B.Part(q.P[:, ::-1], q.T[:, ::-1], -q.N[:, ::-1])])
    HR = {}
    for nm, (lods, hinge, xd, top, roof_y, dark) in LIDS_.items():   # hatch frame: x from the hinge into the lid, y up, z along the hinge (hatchs column 7 = 2)
        Rm = np.array([xd, [0, 1.0, 0], np.cross(xd, [0, 1.0, 0])]); M = np.eye(4); M[:3, :3] = Rm; M[3, :3] = hinge - RING; HR[nm] = (Rm, hinge)
        add(nm, 4, 'd_head', M, {0: OLD.hit(*lods[0].moved(hinge, Rm).plain(), ARM85, 'roof'), **{L: backed(lods[L].moved(hinge, Rm)).gxt() for L in (1, 2, 3)}})
    for nm, (lods, c_, top) in PERIS.items():
        geo_ = {0: OLD.hit(*lods[0].moved(c_).plain(), ARM85, 'roof'), **g(lods, c_)}
        if nm == 'd_sight_03':   # rides on the cupola lid
            Rh, ph = HR['d_hatch_04']; M_ = np.eye(4); M_[:3, :3] = Rh.T; M_[3, :3] = (c_ - ph) @ Rh.T; add(nm, 4, 'd_hatch_04', M_, geo_)
        else:
            add(nm, 4, 'd_head', tr(c_ - RING), geo_)
    add('s_gun', 0, 'd_gun', tr(MUZ + [0, 0, 0.05] - TRUN))
    coax = np.array([BORE[0] + 0.24, BORE[1] + 0.02, TRUN[2] + 0.30])               # the co-axial DT right of the gun
    add('d_minigun', 1, 'd_gunmask', tr(coax - TRUN)); add('s_mgun', 0, 'd_minigun', tr((0, 0, 0.05)))
    # the old turret's sockets: crew, cameras, damage boxes, exits - same place relative to the ring (the new turret is larger);
    # gun-side ones follow the trunnion
    for n in K.nodes[1:]:
        nm = n['name']
        if not under_head(n) or nm.startswith('d_') or nm in ('s_gun', 's_mgun', 's_camera_pt4_7'): continue
        wp = n['world'][3, :3].copy()
        par = 'd_gunmask' if nm in ('s_camera_tmfd7', 'p_rotgun') else 'd_head'
        if nm == 's_camera_tmfd7': wp = np.array([BORE[0] - 0.30, BORE[1] + 0.06, TRUN[2] + 0.30])   # the TSh telescope, left of the gun
        if nm in ('s_camera_gunner', 's_camera_loader'): wp = np.array([np.sign(wp[0]) * (wall(wp[1], wp[2]) + 0.03), wp[1], wp[2]])   # side ports on the new walls
        M = np.eye(4); M[:3, :3] = n['world'][:3, :3]; M[3, :3] = wp - (TRUN if par == 'd_gunmask' else RING)
        A0 = K.geo.get((nm, 0)); add(nm, n['kind'], par, M, {0: A0} if A0 is not None and nm.startswith('p_') else {})
    # the commander (the T-34-85's fifth man) under the cupola on the turret's left rear: seat, damage box, exit, the MK-4 on the
    # cupola roof and five vision slits round it
    CUP = np.array([CUPX, 0.0, CUPZ]); lid = PERIS['d_sight_03'][1][1]
    # the cupola wall: the outermost turret points round the cupola 5-13 cm under its lid (11 Nov: the slits were 6 cm inside it)
    dc = np.hypot(TV[:, 0] - CUPX, TV[:, 2] - CUPZ); band = (TV[:, 1] > lid - 0.07) & (TV[:, 1] < lid - 0.01) & (dc < 0.50)   # the wall stands 1.26-1.36 m, r 0.46
    rc = float(np.percentile(dc[band], 97)) if band.any() else 0.36; ctop = lid
    def look(d):
        z = np.asarray(d, float); z /= np.linalg.norm(z); x = np.cross([0, 1.0, 0], z); x /= np.linalg.norm(x); return np.array([x, np.cross(z, x), z])
    def sock(name, wp, d=(0, 0, 1.0), geo=None):
        M = np.eye(4); M[:3, :3] = look(d); M[3, :3] = np.asarray(wp, float) - RING; add(name, 0 if geo is None else 1, 'd_head', M, geo or {})
    sock('s_commander', (CUP[0], 0.70, CUP[2]))
    pg = K.geo.get(('p_gunner', 0)); sock('p_commander', (CUP[0], 0.70, CUP[2]), geo={0: pg} if pg is not None else None)
    sock('s_commander_exit', (CUP[0] - 2.0, 1.35, CUP[2]))
    sock('s_commander_out', (CUPX, LIDS_['d_hatch_04'][3] - 0.07, CUPZ))                       # head out of the cupola
    for n_ in nodes:                                                                            # the loader's out socket under his hatch
        if n_['name'] == 's_loader_out': lc = LIDS['d_hatch_03']['c']; n_['M'] = tr(np.array([lc[0], LIDS_['d_hatch_03'][3] - 0.07, lc[1]]) - RING); n_['parent'] = 'd_head'
    for k, ang in enumerate((0, 60, 120, 240, 300)):
        dv = np.array([np.sin(np.radians(ang)), 0, np.cos(np.radians(ang))]); sock('s_camera_mk4_%02d' % (k + 2), CUP + dv * (rc + 0.03) + [0, ctop - 0.03, 0], dv)
    # periscope cameras on the turning heads, at the head's front face just under its top
    for nm, cam in (('d_sight_01', 's_camera_pt4_7'), ('d_sight_02', 's_camera_loader_02'), ('d_sight_03', 's_camera_mk4_01')):
        lods, c_, top = PERIS[nm]; front = float(lods[1].hi()[2])
        M = np.eye(4); M[3, :3] = [0.0, top - c_[1] - 0.03, front - c_[2] + 0.02]; add(cam, 0, nm, M)
    print('nodes', len(nodes), 'cupola', np.round(CUP, 3), 'lid', round(ctop, 3), 'cupola radius', round(rc, 3), 'trunnion', np.round(TRUN, 3), 'muzzle', np.round(MUZ, 3), 'bore', np.round(BORE, 3))
    return nodes, (tl, ml, bl, PERIS, TRUN)


def textures(dift, norsp, out):
    import atf1
    from PIL import Image
    vd = np.asarray(atf1.top(dift))[..., :3].astype(np.float32); vn = np.asarray(atf1.top(norsp)).astype(np.float32)
    N = 2048; h = vd.shape[0]
    dif = np.zeros((N, N, 3), np.float32); nrm = np.zeros((N, N, 4), np.float32)
    dif[:N // 2, :N // 2] = np.asarray(Image.fromarray(vd.astype(np.uint8)).resize((N // 2, N // 2), Image.LANCZOS), np.float32)
    nrm[:N // 2, :N // 2] = np.asarray(Image.fromarray(vn.astype(np.uint8), 'RGBA').resize((N // 2, N // 2), Image.LANCZOS), np.float32)
    # paint source: calm patches of the painted plates anywhere on the sheet - mid brightness (40-75th percentile), low
    # detail (lowest 30 % of contrast), almost no black (holes, shadows, rubber)
    rng = np.random.default_rng(34); P_ = 96 * h // 1024; cand = []
    for y in range(0, h - P_, P_ // 3):
        for x in range(0, h - P_, P_ // 3):
            q = vd[y:y + P_, x:x + P_]; lum = q.mean(2); cand.append((lum.mean(), lum.std(), (lum < 12).mean(), y, x))
    C = np.array(cand); lo_, hi_ = np.percentile(C[:, 0], [40, 75]); sd_ = np.percentile(C[:, 1], 30)
    src = [vd[int(y):int(y) + P_, int(x):int(x) + P_] for m_, sd, dk, y, x in C if lo_ < m_ < hi_ and sd < sd_ and dk < 0.03]
    tone = np.median(np.array([q.reshape(-1, 3).mean(0) for q in src]), 0)
    src = [(q - q.reshape(-1, 3).mean(0)) * 0.55 + tone for q in src]   # one paint tone: each patch keeps only its fine wear (the first quilt was blotchy)
    print('paint patches', len(src), 'tone', np.round(tone))
    def quilt(size):
        acc = np.zeros((size, size, 3), np.float32); w = np.zeros((size, size, 1), np.float32)
        k = int(P_ * size / 1024 * 2); win = np.outer(np.hanning(k), np.hanning(k))[..., None] + 1e-3
        for y in range(-k // 2, size, k // 3):
            for x in range(-k // 2, size, k // 3):
                q = np.asarray(Image.fromarray(src[rng.integers(len(src))].astype(np.uint8)).resize((k, k), Image.BILINEAR), np.float32)
                if rng.random() < 0.5: q = q[:, ::-1]
                y0, x0 = max(0, y), max(0, x); y1, x1 = min(size, y + k), min(size, x + k)
                acc[y0:y1, x0:x1] += q[y0 - y:y1 - y, x0 - x:x1 - x] * win[y0 - y:y1 - y, x0 - x:x1 - x]; w[y0:y1, x0:x1] += win[y0 - y:y1 - y, x0 - x:x1 - x]
        return acc / w
    Hq = N // 2
    # 11 Nov (user: check the textures): the quilt carried the patches' panel edges and rivet lines as hard blocks; the paint is
    # now the T-34's tone with soft weathering mottles (smooth noise, several scales) and only the fine grain of the game's paint
    # (each patch high-passed, so no edges or lighting of its own)
    from scipy.ndimage import gaussian_filter
    hp = [np.clip(q - gaussian_filter(q, (5, 5, 0)), -14, 14) for q in src]
    def grain(size, seed):
        r_ = np.random.default_rng(seed); acc = np.zeros((size, size, 3), np.float32); w = np.zeros((size, size, 1), np.float32)
        k = P_ * 2; win = np.outer(np.hanning(k), np.hanning(k))[..., None] + 1e-3
        for y in range(-k // 2, size, k // 3):
            for x in range(-k // 2, size, k // 3):
                q = np.asarray(Image.fromarray((hp[r_.integers(len(hp))] + 128).astype(np.uint8)).resize((k, k), Image.BILINEAR), np.float32) - 128
                q = np.rot90(q, r_.integers(4))
                y0, x0 = max(0, y), max(0, x); y1, x1 = min(size, y + k), min(size, x + k)
                acc[y0:y1, x0:x1] += q[y0 - y:y1 - y, x0 - x:x1 - x] * win[y0 - y:y1 - y, x0 - x:x1 - x]; w[y0:y1, x0:x1] += win[y0 - y:y1 - y, x0 - x:x1 - x]
        return acc / w
    def fbm(size, seed):
        r_ = np.random.default_rng(seed); out = np.zeros((size, size), np.float32)
        for cells, amp in ((6, 1.0), (14, 0.6), (32, 0.35), (80, 0.2)):
            g = r_.standard_normal((cells, cells)).astype(np.float32)
            out += amp * np.asarray(Image.fromarray(g).resize((size, size), Image.BICUBIC), np.float32)
        return out / out.std()
    def paint(seed, light=1.0):
        # 11 Nov (user's close-ups): plain T-34 green - faint large-scale variation and soft grain only. The grime and dust
        # colours were lighter than the paint and made pale bands; any pattern also showed edges where faces change paint area
        m = fbm(Hq, seed)[..., None]
        return tone * light * (1.0 + 0.025 * m) + gaussian_filter(grain(Hq, seed + 3), (1.2, 1.2, 0)) * 0.45
    side = paint(1)
    dif[:Hq, Hq:] = side; dif[Hq:, :Hq] = paint(2); dif[Hq:, Hq:] = paint(3)            # one tone in every quarter: faces switching quarter show no edge
    dy, dx = int(DARK_UV[1] * N), int(DARK_UV[0] * N); dif[dy - 16:dy + 16, dx - 16:dx + 16] = 6   # the dark texel
    # normal / gloss for the paint: flat, with the old sheet's median gloss
    flat = np.array([128, 128, np.median(vn[..., 2]), np.median(vn[..., 3]) * 0.75], np.float32)   # a little less shine than the hull's median: the cast turret read glossy
    nrm[:Hq, Hq:] = flat; nrm[Hq:, :] = flat
    dif = np.clip(dif, 0, 255).astype(np.uint8); nrm = np.clip(nrm, 0, 255).astype(np.uint8)
    B.write_textures(dif, nrm, out, MATERIAL[1].decode()[:-5])
    Image.fromarray(dif).resize((1024, 1024)).save(os.path.join(out, 't3485_dift_preview.png'))



def armour_map(src, out):
    """the T-34's armour map with the turret plates written into four free blocks (ART8: 4x4 blocks of two 8-bit values and a
    16-bit mask choosing between them; the values are 2 x mm)"""
    import atf1
    b = bytearray(open(src, 'rb').read())
    for k, (by, bx, v) in ARM_BLOCKS.items():
        o = atf1.HDR + (by * 64 + bx) * 4; assert b[o:o + 4] == bytes(4), (k, bytes(b[o:o + 4]))
        b[o:o + 4] = bytes((v, v, 0, 0))
    open(os.path.join(out, 'arm_t3485_dift.armor.loc_def.bin'), 'wb').write(bytes(b))


def _spin(p, R, piv):
    piv = np.asarray(piv, float); return B.Part((p.P - piv) @ R.T + piv, p.T, p.N @ R.T)


def _turret_pieces(A, F, y_cut=0.585):
    """faces of every separate piece of the wreck that reaches above the hull roof (the old turret, its mantlet and the drooping
    76 mm barrel), the hull piece itself excepted (11 Nov: a height cut left the barrel's lower half lying on the glacis)"""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    P = A[:, :3]; _, inv = np.unique(np.round(P, 3), axis=0, return_inverse=True); inv = inv.ravel(); Fw = inv[F]; n = inv.max() + 1
    e = np.r_[Fw[:, [0, 1]], Fw[:, [1, 2]]]; nc, lab = connected_components(coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(n, n)), directed=False)
    fl = lab[Fw[:, 0]]; c = P[F].mean(1); cnt = np.bincount(fl, minlength=nc); big = cnt.argmax()
    top = np.full(nc, -9.0); np.maximum.at(top, fl, P[F].max(1)[:, 1])          # a piece's highest point: the fallen 76 mm barrel lies low but its breech end is up at 0.77
    rm = [h for h in np.nonzero(top > y_cut)[0] if h != big and cnt[h] < 0.4 * len(F)]
    return np.isin(fl, rm)


def wreck(ostov, parts, out, yaw=-22.0, droop=3.0):
    """the game's generic T-34 wreck (rtank_ostov01: one burnt d_hull with the running gear, two collision boxes, a centre of
    mass) with its 76 mm turret cut away (everything above the hull roof, y > 0.585) and the 85 mm turret set on the ring,
    turned off the centre line with the gun drooping, as the game's wrecks stand.  The turret takes the burnt texture of the
    old turret's own area of the wreck sheet, so the wreck keeps the game's material and texture."""
    tl, ml, bl, peris, trun = parts
    W = SM.Src(ostov); nodes = []
    A1, F1 = W.geo[('d_hull', 1)]; cut1 = _turret_pieces(A1, F1)
    uvs = A1[:, 3:5][F1[cut1]].reshape(-1, 2); u0, v0 = np.percentile(uvs, 5, 0); u1, v1 = np.percentile(uvs, 95, 0)
    A0, F0 = W.geo[('d_hull', 0)]; cut0 = _turret_pieces(A0, F0); arm_uv = A0[F0[cut0]][:, :, 6:8].reshape(-1, 2).mean(0)
    c, s_ = np.cos(np.radians(droop)), np.sin(np.radians(droop)); Rx = np.array([[1, 0, 0], [0, c, -s_], [0, s_, c]])
    c, s_ = np.cos(np.radians(yaw)), np.sin(np.radians(yaw)); Ry = np.array([[c, 0, s_], [0, 1, 0], [-s_, 0, c]])
    def turret(L):
        p = B.join([tl[L]] + [v[0][L] for v in peris.values()] + [_spin(ml[L], Rx, trun), _spin(bl[L], Rx, trun)])
        p = _spin(p, Ry, RING); T = p.T.copy()
        T[..., 0] = u0 + (T[..., 0] % 0.5) * 2 * (u1 - u0); T[..., 1] = v0 + (T[..., 1] % 0.5) * 2 * (v1 - v0)
        return B.Part(p.P, T, p.N)
    def keep(A, F, cut):
        f = F[~cut]; used = np.unique(f); remap = np.full(len(A), -1); remap[used] = np.arange(len(used)); return A[used], remap[f]
    geo = {0: B.cat([keep(A0, F0, cut0), OLD.hit(*turret(0).plain(), {'side': tuple(arm_uv)}, 'side')])}
    for L, lod in ((1, 2), (2, 3), (3, 3)):   # the wreck is a distance object: the tank's 2nd / 3rd detail
        A, F = W.geo[('d_hull', L)]; cut = _turret_pieces(A, F); geo[L] = B.cat([keep(A, F, cut), turret(lod).gxt()])
    for n in W.nodes[1:]:
        nm = n['name']; p = n['parent']; pn = W.nodes[p]['name'] if p is not None and p < len(W.nodes) and W.nodes[p]['name'] != 's_root' else None
        g_ = geo if nm == 'd_hull' else {L: W.geo[(nm, L)] for L in range(4) if (nm, L) in W.geo}
        nodes.append(dict(name=nm, kind=n['kind'], parent=pn, M=W.local(nm), geo=g_))
    data = SM.assemble(nodes, ostov); pth = os.path.join(out, 't3485_ostov01.mesh.loc_def.bin'); open(pth, 'wb').write(data)
    m = azg2.read(pth); print('wreck', pth, len(data), 'bytes;', [(b_['tag'], b_['nv'], b_['ni']) for b_ in m['blocks']], 'old turret faces cut', int(cut1.sum()))

if __name__ == '__main__':
    t34, stl, dift, norsp, out = sys.argv[1:6]; ostov = sys.argv[6] if len(sys.argv) > 6 else None; arm_src = sys.argv[7] if len(sys.argv) > 7 else None
    os.makedirs(out, exist_ok=True)
    nodes, parts = build(t34, stl)
    data = B.rename_material(SM.assemble(nodes, t34), (MATERIAL[0],), (MATERIAL[1],))
    p = os.path.join(out, 't3485.mesh.loc_def.bin'); open(p, 'wb').write(data)
    m = azg2.read(p); print('written', p, len(data), 'bytes;', len(m['nodes']), 'nodes;', [(b['tag'], b['nv'], b['ni']) for b in m['blocks']], [x['name'] for x in m['materials']])
    textures(dift, norsp, out); print('textures written')
    if ostov: wreck(ostov, parts, out)
    if arm_src: armour_map(arm_src, out); print('armour map written')

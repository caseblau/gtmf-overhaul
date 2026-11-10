r"""IS-2 from the low-poly model (Downloads\low-poly-is-2-soviet-heavy-tank.zip, Kado3D) - 10 Nov, user: total rebuild on the second
model, the unditching log replaced by fuel drums.  10 256 triangles in all: no reduction, so none of the folds, holes and dark
wedges the 536 000-triangle model left.  Running gear, crew stations, damage boxes and tables are the KV-1S's, as in is2_bought.

  python is2_lp.py <kv1s_late mesh> <Kado_3D_IS_2.obj> <its textures dir> <out dir> [kv1s diffuse, for the paint]
"""
import sys, os, re, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bought as B, azg2, geom, su122_mesh as SM, m3lee_mesh as OLD, is2_bought as I, armour

OFF = np.array([0.0, -1.079, -0.293])      # model -> game: road wheel axles on the KV-1S's (y -0.721), road wheel span on the old IS-2's
MATERIAL = I.MATERIAL
UVS = []
DARK_UV = np.array((0.5, 0.5))
ARM_BLOCKS = []

def find_dark_uv(lp_tex, parts):
    from PIL import Image, ImageDraw
    a = np.asarray(Image.open(os.path.join(lp_tex, 'IS_2_Albedo.png')).convert('L').resize((256, 256)), float)
    m = Image.new('L', (256, 256), 0); dr = ImageDraw.Draw(m)
    for T in parts:
        for tri in T * 256: dr.polygon([tuple(x) for x in tri], fill=255)
    from scipy.ndimage import binary_erosion
    free = binary_erosion(np.asarray(m) == 0, iterations=4); iy, ix = np.argwhere(free)[len(np.argwhere(free)) // 2]   # 10 Nov: a free texel, painted black (user: not fully dark)
    return np.array(((ix + 0.5) / 256, (iy + 0.5) / 256))


def read_groups(path):
    V, VT, VN, G = [], [], [], {}; cur = None
    for l in open(path, errors='replace'):
        t = l.split()
        if not t: continue
        if t[0] == 'v': V.append([float(a) for a in t[1:4]])
        elif t[0] == 'vt': VT.append([float(a) for a in t[1:3]])
        elif t[0] == 'vn': VN.append([float(a) for a in t[1:4]])
        elif t[0] == 'g': cur = ' '.join(t[1:]) if t[1] != 'default' else cur
        elif t[0] == 'f':
            q = [tuple(int(x) - 1 if x else 0 for x in a.split('/')) for a in t[1:]]
            for k in range(1, len(q) - 1): G.setdefault(cur, []).append((q[0], q[k], q[k + 1]))
    V = np.array(V) * 0.01; VT = np.array(VT); VN = np.array(VN); out = {}
    for g, fs in G.items():
        f = np.array(fs)[:, [0, 2, 1]]                      # x changes hand below: the windings reverse
        P = V[f[:, :, 0]] * [-1.0, 1.0, 1.0]; N = VN[f[:, :, 2]] * [-1.0, 1.0, 1.0]
        T = VT[f[:, :, 1]].copy(); T -= np.floor(T.mean(1, keepdims=True)); T = np.clip(T, 0, 1); T[..., 1] = 1.0 - T[..., 1]
        out[g] = B.Part(P + OFF, T, N)
    return out


def tr(p): M = np.eye(4); M[3, :3] = p; return M


def mirror_x(p):
    """a part mirrored to the other side (x -> -x), windings turned so it still faces out"""
    return B.Part((p.P * [-1.0, 1, 1])[:, ::-1], p.T[:, ::-1], (p.N * [-1.0, 1, 1])[:, ::-1])


def clip_part(p, f):
    P_, T_, N_ = [], [], []
    for i in range(len(p.P)):
        poly = B._clip([(p.P[i, k], p.T[i, k], p.N[i, k]) for k in range(3)], f)
        for k in range(1, len(poly) - 1):
            P_.append([poly[0][0], poly[k][0], poly[k + 1][0]]); T_.append([poly[0][1], poly[k][1], poly[k + 1][1]]); N_.append([poly[0][2], poly[k][2], poly[k + 1][2]])
    return B.Part(np.array(P_).reshape(-1, 3, 3), np.array(T_).reshape(-1, 3, 2), np.array(N_).reshape(-1, 3, 3))


def subdivide(p, max_edge):
    """split triangles at their longest edge until every edge is under max_edge (uv and normals interpolated)"""
    P, T, N = list(p.P), list(p.T), list(p.N); oP, oT, oN = [], [], []
    while P:
        a, t, n = P.pop(), T.pop(), N.pop(); e = [np.linalg.norm(a[(k + 1) % 3] - a[k]) for k in range(3)]; k = int(np.argmax(e))
        if e[k] < max_edge: oP.append(a); oT.append(t); oN.append(n); continue
        i, j, o = k, (k + 1) % 3, (k + 2) % 3; mp = (a[i] + a[j]) / 2; mt = (t[i] + t[j]) / 2; mn = (n[i] + n[j]) / 2
        P.append(np.array([a[i], mp, a[o]])); T.append(np.array([t[i], mt, t[o]])); N.append(np.array([n[i], mn, n[o]]))
        P.append(np.array([mp, a[j], a[o]])); T.append(np.array([mt, t[j], t[o]])); N.append(np.array([mn, n[j], n[o]]))
    return B.Part(np.array(oP), np.array(oT), np.array(oN))


def backed(p, t=0.008):
    """a reversed copy t under the lid (local -y): an open lid's inside is painted, not see-through"""
    q = p.moved((0, t, 0)); return B.join([p, B.Part(q.P[:, ::-1], q.T[:, ::-1], -q.N[:, ::-1])])


def build(kv_path, obj_path):
    K = SM.Src(kv_path); arm = OLD.arm_points(K)
    G = read_groups(obj_path)
    pcs = B.split(G['IS_2']); cen = lambda q: q.centre()
    # ---- the log on the left (with its three brackets and feet) goes; the right side's drums, caps, straps and fittings are mirrored there
    log = [q for q in pcs if cen(q)[0] < -1.2 and 0.1 < cen(q)[1] < 0.75 and -2.5 < cen(q)[2] < 0.6 and len(q) in (180, 60, 20)]
    drums = [q for q in pcs if cen(q)[0] > 1.2 and cen(q)[1] > 0.2 and -2.9 < cen(q)[2] < -0.55]
    print('log pieces removed', sorted(len(q) for q in log), '| drum pieces mirrored', sorted(len(q) for q in drums))
    # 10 Nov (user: the drums should be the same size): the front drum (0.48 m across) is replaced by a copy of the rear one (0.36 m),
    # 1.09 m forward - body, caps, straps and filler cap
    front = [q for q in drums if cen(q)[2] > -1.55]; rear = [q for q in drums if cen(q)[2] <= -1.55]
    pcs = [q for q in pcs if not any(q is f_ for f_ in front)]
    drums = rear + [B.Part(q.P + [0, 0, 1.09], q.T.copy(), q.N.copy()) for q in rear]
    pcs = pcs + drums[len(rear):]
    hull_pcs = [q for q in pcs if not any(q is l for l in log)] + [mirror_x(q) for q in drums]
    lamp = max((q for q in hull_pcs if len(q) == 120), key=lambda q: q.centre()[2])   # the headlight on the glacis, left of the visor (was taken for the bow MG)
    visor = next(q for q in hull_pcs if len(q) == 52 and abs(q.centre()[0]) < 0.1 and q.centre()[2] > 2.0)
    hull = B.join(hull_pcs)
    shell = max(hull_pcs, key=len)
    tower = B.split(G['IS_2 Tower']); body = tower[0]
    Pb = body.P.reshape(-1, 3); low = Pb[Pb[:, 1] < Pb[:, 1].min() + 0.03]
    RING = np.array([(low[:, 0].min() + low[:, 0].max()) / 2, Pb[:, 1].min(), (low[:, 2].min() + low[:, 2].max()) / 2])
    # ---- lids: the loader's round plate with its hinge block; the cupola's flat top inside its rim, with its MK-4
    cup = tower[1]; cc = cup.centre(); top = cup.hi()[1]
    # 10 Nov (user: hinges wrong): the lid's arm (79 faces) goes with the lid; it turns on the hinge rod fixed on the roof
    lid_l = [q for q in tower if len(q) in (63, 41) and 0.15 < q.centre()[0] < 0.75 and q.centre()[1] > RING[1] + 0.7 and 0.0 < q.centre()[2] < 0.7]   # plate, arm, strap
    rod = next(q for q in tower if len(q) == 64 and (q.hi() - q.lo())[0] > 0.6 and (q.hi() - q.lo())[1] < 0.1)   # thin: not the mantlet cover
    peris = [q for q in tower if len(q) == 160]; cup_peri = max(peris, key=lambda q: q.centre()[1])
    # the cupola's split lid: two half-discs (31 faces each) on the top - the front one carries the MK-4 and hinges at its front edge,
    # the rear one at its rear edge; their knuckles stay on the cupola
    halves = sorted([q for q in tower if len(q) == 31 and np.hypot(q.centre()[0] - cc[0], q.centre()[2] - cc[2]) < 0.3], key=lambda q: q.centre()[2])
    lid_r, lid_f = halves[0], halves[1]   # the MK-4 on the front leaf is its own turning node (d_sight_03)
    knuck = [q for q in tower if len(q) == 64 and np.hypot(q.centre()[0] - cc[0], q.centre()[2] - cc[2]) < 0.4]
    brk = [q for q in tower if len(q) == 50 and np.hypot(q.centre()[0] - cc[0], q.centre()[2] - cc[2]) < 0.4]
    zr = float(np.mean([q.centre()[2] for q in brk if q.centre()[2] < cc[2]])); zf = float(np.mean([q.centre()[2] for q in brk if q.centre()[2] > cc[2]]))
    yk = float(np.mean([q.centre()[1] for q in brk]))
    lid_r = B.join([lid_r] + [q for q in knuck if q.centre()[2] < cc[2]]); lid_f = B.join([lid_f] + [q for q in knuck if q.centre()[2] > cc[2]])
    # openings (10 Nov, user: no cutaway under the hatches): the roof under the loader's lid and the cupola top under the leaves are cut
    # round, with a dark box below
    def cut_circle(p, c, r, ylo):
        cn = p.P.mean(1); bx = (p.P[:, :, 0].min(1) < c[0] + r) & (p.P[:, :, 0].max(1) > c[0] - r) & (p.P[:, :, 2].min(1) < c[2] + r) & (p.P[:, :, 2].max(1) > c[2] - r)
        sel = bx & (p.N.mean(1)[:, 1] > 0.5) & (cn[:, 1] > ylo)
        out = clip_part(subdivide(p.sub(sel), 0.035), lambda x: r - np.hypot(x[0] - c[0], x[2] - c[2])) if sel.any() else None   # big roof triangles span the circle
        return B.join([p.sub(~sel)] + ([out] if out is not None and len(out) else [])), int(sel.sum())
    plate = next(q for q in lid_l if len(q) == 63); Lc_ = plate.centre(); r_l = float(min((plate.hi() - plate.lo())[[0, 2]])) / 2 - 0.025
    body2, n1 = cut_circle(body, Lc_, r_l, plate.lo()[1] - 0.12)
    cup2, n2 = cut_circle(cup, cc, 0.22, top - 0.05)
    print('openings: roof faces cut', n1, 'cupola faces cut', n2)
    dk = DARK_UV
    darks = [B.dark_box((Lc_[0], plate.lo()[1] - 0.04, Lc_[2]), (0, 1.0, 0), (1.0, 0, 0), r_l, r_l, 0.45, dk),
             B.dark_box((cc[0], top - 0.03, cc[2]), (0, 1.0, 0), (1.0, 0, 0), 0.22, 0.22, 0.45, dk)]
    tur = B.join([q for q in tower if not any(q is l for l in lid_l + halves + knuck + peris + [body, cup])] + [body2, cup2] + darks)   # periscopes turn on their own
    print('ring', np.round(RING, 3), 'cupola centre', np.round(cc, 3), 'cupola hinges z %.3f / %.3f' % (zr, zf), 'loader lid pieces', [len(q) for q in lid_l])
    # gun: the mantlet (Tower Gun) elevates on its trunnion, the barrel recoils
    gm = G['IS_2 Tower Gun']; bar = G['IS_2 Tower Gun Barrel']
    BORE = np.array([(bar.lo()[0] + bar.hi()[0]) / 2, (bar.lo()[1] + bar.hi()[1]) / 2])
    TRUN = np.array([BORE[0], BORE[1], gm.lo()[2] + 0.10]); MUZ = np.array([BORE[0], BORE[1], bar.hi()[2]])
    nodes = []
    def add(name, kind, parent, M, geo=None): nodes.append(dict(name=name, kind=kind, parent=parent, M=M, geo=geo or {}))
    # 11 Nov (user: real values): the IS-2's own armour map (armour.py) - hull 120 mm front, 90 sides, 60 rear, 30 roof; turret and
    # mantlet 100 front, 90 sides and rear, 30 roof.  The KV-1S spots it used read 37 / 4 / 29 / 22 mm (arm_points picks odd faces).
    ARM_UV, blocks = armour.plates(os.path.join(os.path.dirname(os.path.abspath(kv_path)), 'arm_kv1s_dift.armor.loc_def.bin'), K,
                                   {'front': 120, 'side': 90, 'rear': 60, 'roof': 30, 'tfront': 100})
    ARM_BLOCKS[:] = blocks
    AH = {k: ARM_UV[k] for k in ('front', 'side', 'rear', 'roof')}; AT = dict(front=ARM_UV['tfront'], side=ARM_UV['side'], rear=ARM_UV['side'], roof=ARM_UV['roof'])
    def hit(p, cls=None, a=None): return OLD.hit(*p.plain(), a or AH, cls)
    def g3(p): g = p.gxt(); return {1: g, 2: g, 3: g}
    far = B.join([q for q in hull_pcs if float(np.max(q.hi() - q.lo())) > 0.5])
    add('d_hull', 4, None, np.eye(4), {0: hit(shell), 1: hull.gxt(), 2: hull.gxt(), 3: far.gxt()})
    # ---- running gear: the KV-1S's nodes at the model's wheel centres; the balance arms keep their offset from their wheel
    wc = lambda k: G[k].centre().copy(); W = {}
    for side, ids in (('L', range(2, 8)), ('R', range(13, 19))):
        for i, k in zip(range(2, 8), ids): W['d_wheel_%02d' % k] = wc('IS_2 Wheels_%s Wheel_%s_%02d' % (side, side, i))
    W['d_wheel_01'] = wc('IS_2 Wheel_L_01 Wheels_L'); W['d_wheel_12'] = wc('IS_2 Wheel_R_01 Wheels_R')
    W['d_wheel_08'] = wc('IS_2 Wheels_L Wheel_L_08'); W['d_wheel_19'] = wc('IS_2 Wheels_R Wheel_R_08')
    for i, k in zip((9, 10, 11), (9, 10, 11)): W['d_wheel_%02d' % k] = wc('IS_2 Wheels_L Wheel_L_%02d' % i)
    for i, k in zip((9, 10, 11), (22, 21, 20)): W['d_wheel_%02d' % k] = wc('IS_2 Wheels_R Wheel_R_%02d' % i)
    for k in ('d_wheel_09', 'd_wheel_10', 'd_wheel_11', 'd_wheel_20', 'd_wheel_21', 'd_wheel_22'): W[k][1] -= 0.05   # 10 Nov (user: the fenders sat on the track): the KV-1S's rollers are larger than the model's; the top run 5 cm lower
    TRACK = float(np.mean([abs(p[0]) for p in W.values()]))
    for k in W: W[k][0] = np.sign(W[k][0]) * TRACK
    world = {n['name']: n['world'][3, :3].copy() for n in K.nodes}
    pairs = [('d_balansir_%02d' % (i + 1), 'd_wheel_%02d' % w_) for i, w_ in enumerate(list(range(2, 8)) + list(range(13, 19)))]
    for name, p in W.items():
        M = K.local(name).copy(); M[3, :3] = p; add(name, K.node(name)['kind'], 'd_hull', M, {0: K.geo[(name, 0)]} if (name, 0) in K.geo else {})
    for name, wh in pairs:
        p = W[wh] + (world[name] - world[wh]) * [TRACK / 1.331, 1, 1]; M = K.local(name).copy(); M[3, :3] = p; g = {}
        for L in range(4):
            if (name, L) in K.geo:
                A, F = K.geo[(name, L)]; A = A.copy()
                if L > 0: A[:, 3:5] = I.PLAIN_UV
                g[L] = (A, F)
        add(name, K.node(name)['kind'], 'd_hull', M, g)
    # ---- turret, gun, lids, machine guns
    PW = {'d_hull': np.zeros(3), 'd_head': RING, 'd_gunmask': TRUN}
    add('d_head', 4, 'd_hull', tr(RING), {0: hit(body.moved(RING), None, AT), **g3(tur.moved(RING))})
    # 10 Nov (user): the gunner's sight port in the mantlet, left of the gun (mirrors the DT stub on the right): cut, dark behind
    SP = np.array([2 * BORE[0] - 0.287, 1.031, 0.0]); ff = sorted(set(B.ray_faces(gm, (SP[0] + dx, SP[1] + dy, 9.0), (0, 0, -1.0), 0, 9)[0][0] for dx in (-0.02, 0, 0.02) for dy in (-0.03, 0, 0.03) if len(B.ray_faces(gm, (SP[0] + dx, SP[1] + dy, 9.0), (0, 0, -1.0), 0, 9)[0])))
    SP[2] = 9.0 - float(min(B.ray_faces(gm, (SP[0], SP[1], 9.0), (0, 0, -1.0), 0, 9)[1]))
    gm, ncut = B.cut_rect(gm, SP, (0, 0, 1.0), (1.0, 0, 0), 0.03, 0.045, only=ff)
    gm = B.join([gm, B.dark_box(SP, (0, 0, 1.0), (1.0, 0, 0), 0.03, 0.045, 0.25, DARK_UV)]); print('sight port at', np.round(SP, 3), 'faces cut', ncut)
    add('d_gunmask', 4, 'd_head', tr(TRUN - RING), {0: hit(gm.moved(TRUN), 'front', AT), **g3(gm.moved(TRUN))})
    b_l = bar.moved(TRUN); add('d_gun', 4, 'd_gunmask', np.eye(4), {0: hit(b_l, 'roof', AT), **g3(b_l)})
    add('s_gun', 0, 'd_gun', tr(MUZ + [0, 0, 0.065] - TRUN));   # 11 Nov (user: the SU-152's ML-20S): 6.5 cm ahead of the brake's face, as on the SU-152
    add('s_mgun', 0, 'd_gunmask', tr(np.array([0.287, 1.031, 2.43]) - TRUN))   # 10 Nov: the co-axial DT's muzzle on the stub right of the gun (fired from inside the barrel)
    def hatch(name, lid, piv, xdir):
        """local z along the hinge (hatch axis 2), x from the hinge into the lid, y up"""
        x = np.asarray(xdir, float); x /= np.linalg.norm(x); y = np.array([0, 1.0, 0]); Rm = np.array([x, y, np.cross(x, y)])
        M = np.eye(4); M[:3, :3] = Rm; M[3, :3] = np.asarray(piv, float) - RING; L_l = backed(lid.moved(piv, Rm))
        add(name, 4, 'd_head', M, {0: hit(L_l, 'roof', AT), **g3(L_l)})
    Ll = B.join(lid_l); lo_, hi_ = Ll.lo(), Ll.hi()
    rc = rod.centre(); hatch('d_hatch_03', Ll, ((lo_[0] + hi_[0]) / 2, rc[1], rc[2]), (0, 0, -1.0))   # loader's lid: turns on the rod's axis
    hatch('d_hatch_04', lid_f, (cc[0], yk, zf), (0, 0, -1.0))          # cupola front leaf: opens forward on its front knuckle
    hatch('d_hatch_05', lid_r, (cc[0], yk, zr), (0, 0, 1.0))           # cupola rear leaf: opens backward on its rear knuckles
    # 10 Nov (user): the periscopes turn 360 deg - the gunner's PT4 (left), the loader's MK-4 (right), the commander's MK-4 on the
    # front leaf of the cupola lid; each is its own node, named in its sight row (column 5), with its camera on it
    # 11 Nov (user: the roof periscopes look off - dark faceted blobs): the model maps each small periscope face over a wide patch of the
    # atlas (0.2-0.6 of the sheet for a 20 cm part), so every face shows a squeezed slice of paint, decals and normal-map relief. They
    # take a plain patch of the turret roof's paint instead, and the forward glass the dark texel.
    ar = np.linalg.norm(np.cross(body.P[:, 1] - body.P[:, 0], body.P[:, 2] - body.P[:, 0]), axis=1) * (body.N.mean(1)[:, 1] > 0.9)
    from PIL import Image   # the roof face whose paint is nearest the roof's median colour (the largest one was a pale scuff)
    alb = np.asarray(Image.open(os.path.join(os.path.dirname(os.path.abspath(obj_path)), 'tex', 'IS_2_Albedo.png')).convert('RGB')).astype(float); hh, ww = alb.shape[:2]
    roof = np.where(ar > 0)[0]; uvc = body.T[roof].mean(1) % 1.0; colr = alb[(uvc[:, 1] * (hh - 1)).astype(int), (uvc[:, 0] * (ww - 1)).astype(int)]
    PAINT = uvc[int(np.argmin(np.linalg.norm(colr - np.median(colr, 0), axis=1)))]; print('periscope paint', np.round(np.median(colr, 0)), 'at uv', np.round(PAINT, 3))
    def painted(q):
        T_ = np.empty_like(q.T); fn = q.N.mean(1); fn /= np.linalg.norm(fn, axis=1)[:, None] + 1e-9; yc = q.P.mean(1)[:, 1]
        glass = (fn[:, 2] > 0.85) & (yc > q.centre()[1])
        for i in range(len(q)): T_[i] = (DARK_UV if glass[i] else PAINT) + np.array([[0, 0], [0.002, 0], [0, 0.002]])
        print('periscope faces', len(q), 'glass', int(glass.sum())); return B.Part(q.P.copy(), T_, q.N.copy())
    gp_ = min((q for q in peris if q is not cup_peri), key=lambda q: q.centre()[0]); lp_ = max((q for q in peris if q is not cup_peri), key=lambda q: q.centre()[0])
    for nm_, q in (('d_sight', gp_), ('d_sight_02', lp_)):
        c_ = q.centre(); PW[nm_] = c_; add(nm_, 4, 'd_head', tr(c_ - RING), {**g3(painted(q).moved(c_))})
    hm = next(n_ for n_ in nodes if n_['name'] == 'd_hatch_04'); Rh = hm['M'][:3, :3]; ph = hm['M'][3, :3] + RING
    c_ = cup_peri.centre(); M_ = np.eye(4); M_[:3, :3] = Rh.T; M_[3, :3] = (c_ - ph) @ Rh.T; PW['d_sight_03'] = c_
    add('d_sight_03', 4, 'd_hatch_04', M_, {**g3(painted(cup_peri).moved(c_))})
    # rear ball MG (10 Nov, user: wrong): the mesh is expressed in the KV-1S socket's own turned frame, so it stays where the model has it;
    # the muzzle socket at the barrel's rear end in that frame
    mg = G['IS_2 Tower MG']; ball = mg.centre(); M = K.local('s_bow_rot_03').copy(); Rb = M[:3, :3].copy(); M[3, :3] = ball - RING; add('s_bow_rot_03', 0, 'd_head', M)
    m_l = mg.moved(ball, Rb); add('d_mgun_02', 4, 's_bow_rot_03', np.eye(4), {0: hit(m_l, 'side', AT), **g3(m_l)})
    muz = np.array([ball[0], ball[1], mg.lo()[2]]); add('s_mgun3', 0, 'd_mgun_02', tr((muz - ball) @ Rb.T))
    # the fixed bow DT fired from a port right of the visor (the model has no part for it): socket and damage box only
    bc = np.array([0.30, 0.30, 2.48]); M = K.local('s_bow_rot_02').copy(); M[3, :3] = bc; add('s_bow_rot_02', 0, 'd_hull', M)
    Vb, Fb = geom.box((0, 0, 0.05), (0.08, 0.08, 0.20)); add('d_mgun_01', 1, 's_bow_rot_02', np.eye(4), {0: OLD.hit(Vb, Fb, AH, 'front')}); add('s_mgun2', 0, 'd_mgun_01', tr((0, 0, 0.15)))
    lc = lamp.centre(); add('d_light_01', 1, 'd_hull', tr((lc[0], lc[1], lamp.hi()[2] - 0.02)), {0: K.geo[('d_light_01', 0)]} if ('d_light_01', 0) in K.geo else {})
    add('s_light_01', 0, 'd_light_01', tr((0, 0, 0.04)))
    # ---- the KV-1S's crew stations, damage boxes, fires, marks, riders: turret ones follow the ring, gun ones the trunnion
    done = {n['name'] for n in nodes}
    def parent_of(n):
        while True:
            pn = K.nodes[n['parent']]['name'] if n['parent'] < len(K.nodes) else None
            if pn is None or pn in ('s_root', 'd_hull'): return 'd_hull'
            if pn in ('d_head', 'd_gunmask'): return pn
            n = K.node(pn)
    drop_visual = re.compile(r'd_(wing|mwing|tank|sparetrack|zipbox|tros|bukserga|gabarit|signal|schitok|koziryok|rearlight|maskgruz|antena|wingholder)')
    for n in K.nodes[1:]:
        nm = n['name']
        if nm in done or drop_visual.match(nm) or not nm.startswith(('p_', 's_', 'd_hatch_', 'd_comsight_cap', 'd_sight', 'd_light')): continue
        wp = n['world'][3, :3].copy(); par = parent_of(n)
        M = np.eye(4); M[:3, :3] = n['world'][:3, :3]; M[3, :3] = wp - {'d_hull': np.zeros(3), 'd_head': world['d_head'], 'd_gunmask': world['d_gunmask']}[par]
        kind = 0 if nm.startswith(('d_hatch_', 'd_comsight', 'd_sight', 'd_light')) else n['kind']
        add(nm, kind, par, M, {0: K.geo[(nm, 0)]} if nm.startswith('p_') and (nm, 0) in K.geo else {})
    # ---- this model's vision ports
    def look(d):
        z = np.asarray(d, float); z /= np.linalg.norm(z); yv = np.array([0, 1.0, 0]); x = np.cross(yv, z); x /= np.linalg.norm(x); return np.array([x, np.cross(z, x), z])
    def setcam(name, parent, wpos, d):
        Mc = np.eye(4); Mc[:3, :3] = look(d); Mc[3, :3] = np.asarray(wpos, float) - PW[parent]
        for n_ in nodes:
            if n_['name'] == name: n_.update(parent=parent, M=Mc, kind=0, geo={}); return
        add(name, 0, parent, Mc)
    def surf(p, o, d):
        i_, t_ = B.ray_faces(p, o, d, 0.0, 9.0); return None if not len(t_) else np.asarray(o, float) + np.asarray(d, float) * float(t_.min())
    # 10 Nov (user: sectors did not follow): the rear ball MG's sight turns with the ball, as on the KV-1S
    for n_ in nodes:
        if n_['name'] == 's_sight_pu':
            wp_ = np.array([ball[0] + 0.06, ball[1] + 0.06, mg.lo()[2] + 0.04])   # at the ball, just over the gun (was the KV-1S's spot, 30 cm off)
            if wp_ is not None: Mb = np.eye(4); Mb[:3, :3] = np.array([[-1.0, 0, 0], [0, 1.0, 0], [0, 0, -1.0]]) @ Rb.T; Mb[3, :3] = (wp_ - ball) @ Rb.T; n_.update(parent='d_mgun_02', M=Mb)
    vc = visor.centre()
    for nm in ('s_camera_driver_01', 's_camera_driver_02', 's_camera_driver_03'): setcam(nm, 'd_hull', (vc[0], vc[1], visor.lo()[2]), (0, 0, 1.0))
    setcam('s_camera_gunner_02', 'd_gunmask', SP + [0, 0, 0.02], (0, 0, 1.0))   # 2 cm in front of the sight port: from behind it the mantlet's own hit shape blocked his view (user: never fired)
    for q in peris:
        if q is cup_peri: continue
        c_ = q.centre(); setcam('s_camera_gunner_03' if c_[0] < 0 else 's_camera_loader_02', 'd_sight' if c_[0] < 0 else 'd_sight_02', c_ + [0, 0.03, 0.06], (0, 0, 1.0))
    # side vision / pistol ports: the plug on the right cheek (x 0.874, y 0.863, z 1.657), mirrored on the left (10 Nov)
    for nm, s in (('s_camera_gunner_01', -1.0), ('s_camera_loader_01', 1.0)):
        setcam(nm, 'd_head', (s * 0.84, 0.863, 1.657), (s * 0.94, 0, 0.34))
    setcam('s_camera_mk4_01', 'd_sight_03', cup_peri.centre() + [0, 0.03, 0.06], (0, 0, 1.0))
    for k, ang in enumerate(range(0, 360, 60)):
        dv = np.array([np.sin(np.radians(ang)), 0, np.cos(np.radians(ang))]); o = np.array([cc[0], top - 0.08, cc[2]])
        p_ = surf(cup, o + dv * 1.5, -dv); setcam('s_camera_mk4_%02d' % (k + 2), 'd_head', (p_ if p_ is not None else o + dv * 0.5) - dv * 0.04, dv)
    UVS.clear(); UVS.extend(p.T for p in [hull, tur, gm, bar, mg, Ll, lid_f, lid_r])
    print('nodes', len(nodes), 'trunnion', np.round(TRUN, 3), 'muzzle', np.round(MUZ, 3), 'track', round(TRACK, 3), 'visor', np.round(vc, 3))
    return nodes


def textures(lp_tex, out, ref=None):
    f = lambda n: os.path.join(lp_tex, n)
    dif, nrm = B.build_textures([((0, 0, 1, 1), f('IS_2_Albedo.png'), f('IS_2_Normal.png'), (f('IS_2_AO.png'), 0), (f('IS_2_Rougnes.png'), 0))], None, None, None)   # 10 Nov: its own paint (matching the KV-1S brightened it 30 %)
    dif = I.fill_gaps(dif, UVS, [], dif.shape[0]); nrm = I.fill_gaps(nrm, UVS, [], nrm.shape[0])
    n_ = dif.shape[0]; cy, cx = int(DARK_UV[1] * n_), int(DARK_UV[0] * n_); r_ = max(4, n_ // 128)
    dif[cy - r_:cy + r_, cx - r_:cx + r_] = 6; nrm[cy - r_:cy + r_, cx - r_:cx + r_] = (128, 128, 10, 0)
    B.write_textures(dif, nrm, out, 'is2')


if __name__ == '__main__':
    kv, obj, lp_tex, out = sys.argv[1:5]; ref = sys.argv[5] if len(sys.argv) > 5 else None
    DARK_UV[:] = find_dark_uv(lp_tex, [v.T for v in read_groups(obj).values()]); print('dark uv', DARK_UV)
    nodes = build(kv, obj)
    data = B.rename_material(SM.assemble(nodes, kv), (b'kv1s_dift', b'kv1s_late_dift', b'kv1s_late_norsp'), (MATERIAL[0],) + MATERIAL)
    p = os.path.join(out, 'is2.mesh.loc_def.bin'); open(p, 'wb').write(data)
    m = azg2.read(p); print('written', p, len(data), 'bytes;', len(m['nodes']), 'nodes;', [(b['tag'], b['nv'], b['ni']) for b in m['blocks']])
    textures(lp_tex, out, ref); print('textures written')
    armour.write(os.path.join(os.path.dirname(os.path.abspath(kv)), 'arm_kv1s_dift.armor.loc_def.bin'), os.path.join(out, 'arm_is2_dift.armor.loc_def.bin'), ARM_BLOCKS); print('armour map written', ARM_BLOCKS)

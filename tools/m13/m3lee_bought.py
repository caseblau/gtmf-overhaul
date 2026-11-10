"""M3 Lee game mesh from the user's purchased model (Downloads\\m3-lee-tank, m3_lee_obj.zip and m3_lee_textures.zip), on the
Mius-Front M4A2's skeleton and running gear.

  python m3lee_bought.py <m4a2_sherman mesh> <m3_lee.obj> <textures dir> <out dir> [m4a2 diffuse, for the brightness]

Frame: game = (-x, y - 1.138, z - 0.32): the model's bogie centres land within 4 cm of the M4A2's, its wheel track within
2.3 cm, so the game's own bogies, wheels, sprockets, idlers and tracks stand where the model's stood (the model's own are
left out).  The M4A2's belly add-ins go too (m3lee_config.py): the model has its own lower hull and final-drive covers.

Nodes and socket names are those of m3lee_mesh.py, so m3lee_config.py and the crew / gun tables stay as they were.
"""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import azg2, geom, bought as B, su122_mesh as SM
import m3lee_mesh as OLD

Y_OFF, Z_OFF = -1.138, -0.32
BOGIE_Z = (1.52, 0.094, -1.332)     # the model's bogie brackets (game frame), within 4 cm of the M4A2's carets
ATLAS = {'m3_lee_chassis': (0.0, 0.0, 0.75, 0.75), 'chassis_gun': (0.0, 0.0, 0.75, 0.75),
         'm3_lee_turret': (0.75, 0.0, 0.25, 0.25), 'turret_gun': (0.75, 0.0, 0.25, 0.25), 'comanders_cupola': (0.75, 0.0, 0.25, 0.25)}
DARK_RECT = (0.75, 0.25, 0.25, 0.25); DARK_UV = np.array((0.875, 0.375))
MATERIAL = (b'mlee_dift', b'mlee_norsp')   # no longer than the template's m4a2_dift / m4a2_norsp

def to_game(V): return np.c_[-V[:, 0], V[:, 1] + Y_OFF, V[:, 2] + Z_OFF]

def tr(p): M = np.eye(4); M[3, :3] = p; return M

def is_running_gear(q):
    """bogies, axles and their mounts between the fenders' underside and the ground: the game's M4A2 parts stand there"""
    lo, hi = q.lo(), q.hi(); c = q.centre(); s = hi - lo
    return abs(c[0]) > 0.4 and ((hi[1] < -0.17 and s[2] < 0.72 and s[1] < 0.75) or hi[1] < -0.45)

def build(m4a2_path, obj_path):
    T = SM.Src(m4a2_path); arm = OLD.arm_points(T)
    O = B.load_obj(obj_path, to_game, ATLAS)
    chassis = B.split(O['m3_lee_chassis'])
    # of the running gear the fixed parts stay: bogie brackets, springs and their rocker levers, pivot bosses, return roller mounts,
    # sprocket and idler housings (all above y -0.66).  The arms, hubs and axle pins below are the game's M4A2 parts, which move.
    # Until 9 Nov all of it went, and the game's arms hung from nothing.
    keep = [q for q in chassis if not is_running_gear(q) or q.centre()[1] > -0.66]
    print('chassis pieces', len(chassis), 'kept', len(keep), 'tris', sum(len(q) for q in keep))
    def take(pred):
        hit_ = [q for q in keep if pred(q)]
        for q in hit_: keep.remove(q)
        return hit_
    # ---- the hatches: the door plates and what is fixed on them, the roof hatch beside the turret
    doors = {}
    for s, name in ((-1, 'd_hatch_02'), (1, 'd_hatch_03')):
        doors[name] = take(lambda q: s * q.centre()[0] > 1.25 and -0.40 < q.centre()[2] < 0.40 and 0.14 < q.centre()[1] < 0.80 and q.hi()[1] - q.lo()[1] < 0.70 and q.hi()[2] - q.lo()[2] < 0.70)
        print(' ', name, [len(q) for q in doors[name]])
    lid4 = take(lambda q: 0.60 < q.centre()[0] < 1.10 and -0.40 < q.centre()[2] < 0.30 and q.lo()[1] > 0.97 and q.hi()[1] < 1.03)
    print('  roof hatch', [len(q) for q in lid4])
    # hinge knuckles stay on the hull (10 Nov): the door knuckles at z 0.358, the roof hatch's knuckles and leaves behind z -0.36
    for nm in doors:
        kn = [q for q in doors[nm] if len(q) == 28 and abs(q.centre()[2] - 0.358) < 0.03]; keep.extend(kn); doors[nm] = [q for q in doors[nm] if not any(q is k_ for k_ in kn)]
    kn = [q for q in lid4 if q.centre()[2] < -0.36]; keep.extend(kn); lid4 = [q for q in lid4 if not any(q is k_ for k_ in kn)]
    # the driver's visor door on the upper front plate (door plate + vision block; its hinge bar and knuckles stay on the hull).
    # The model's hull is a single skin and the plate behind the door two big triangles: the opening is cut out of them, with a
    # dark box behind it, so the driver's head shows when the door is up (9 Nov, user: crew visible at open hatches).
    visor = take(lambda q: 40 <= len(q) <= 200 and abs(q.centre()[0] + 0.01) < 0.03 and 0.74 < q.centre()[1] < 0.83 and 1.38 < q.centre()[2] < 1.41)
    VD = B.join(visor); vc = VD.centre(); n0 = VD.N.reshape(-1, 3).mean(0); n0 /= np.linalg.norm(n0)
    big = max(keep, key=len); bn = np.cross(big.P[:, 1] - big.P[:, 0], big.P[:, 2] - big.P[:, 0]); bn /= np.linalg.norm(bn, axis=1, keepdims=True) + 1e-12
    under = set()
    for dx in np.linspace(-0.21, 0.21, 7):                          # the plate's faces under the opening, by rays through the door
        for dy in np.linspace(-0.11, 0.11, 5):
            under.update(B.ray_faces(big, vc + [dx, dy, 0] + n0 * 0.5, -n0, 0.3, 0.7)[0].tolist())
    under = sorted(under); VN = bn[under].mean(0); VN /= np.linalg.norm(VN)
    vc = vc - VN * float(((vc - big.P[under].reshape(-1, 3).mean(0)) @ VN))            # the opening's centre on the plate itself
    cut, n_cut = B.cut_rect(big, vc, VN, (1.0, 0, 0), 0.21, 0.11, only=under); keep = [cut if q is big else q for q in keep]
    print('  visor door', [len(q) for q in visor], 'plate normal', np.round(VN, 3), 'plate faces cut', n_cut)
    # 10 Nov (user: no openings behind the open hatches): the side doors and the roof hatch get real openings in the single-skin hull,
    # cut from the plate faces under each lid (rays through it), with a dark box behind - as the visor
    hole_darks = []
    def open_hole(c, n, u, ha, hb, depth):
        c, n, u = (np.asarray(x, float) for x in (c, n, u)); v = np.cross(n, u); total = 0
        for i, q in enumerate(keep):
            under = set()
            for du in np.linspace(-ha, ha, 7):
                for dv in np.linspace(-hb, hb, 5):
                    under.update(B.ray_faces(q, c + du * u + dv * v + n * 0.3, -n, 0.2, 0.42)[0].tolist())
            if under: keep[i], k_ = B.cut_rect(q, c, n, u, ha, hb, only=sorted(under)); total += k_
        hole_darks.append(B.dark_box(c - n * 0.005, n, u, ha, hb, depth, DARK_UV)); return total
    for s, nm in ((-1, 'd_hatch_02'), (1, 'd_hatch_03')):
        d = B.join(doors[nm]); lo, hi = d.lo(), d.hi()
        k_ = open_hole((s * 1.291, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2), (s, 0, 0), (0, 0, 1.0), (hi[2] - lo[2]) / 2 - 0.07, (hi[1] - lo[1]) / 2 - 0.07, 0.5)
        print('  %s opening: plate faces cut %d' % (nm, k_))
    L4 = B.join(lid4); lo4, hi4 = L4.lo(), L4.hi()
    k_ = open_hole(((lo4[0] + hi4[0]) / 2, lo4[1] + 0.002, (lo4[2] + hi4[2]) / 2), (0, 1.0, 0), (1.0, 0, 0), (hi4[0] - lo4[0]) / 2 - 0.07, (hi4[2] - lo4[2]) / 2 - 0.07, 0.5)
    print('  roof hatch opening: plate faces cut %d' % k_)
    # hull LODs: everything, the large and medium pieces, the shell only
    size = lambda q: float(np.max(q.hi() - q.lo()))
    hull_all = B.join(keep); mid = B.join([q for q in keep if size(q) > 0.30 or len(q) > 200]); far = B.join([q for q in keep if size(q) > 0.9])
    hit_h = B.join([q for q in keep if size(q) > 1.2])
    def arm_hit(p, cls=None):
        return OLD.hit(*p.plain(), arm, cls)
    nodes = []
    def add(name, kind, parent, M, geo=None): nodes.append(dict(name=name, kind=kind, parent=parent, M=M, geo=geo or {}))
    def lods(p, far_p=None): g = p.gxt(); return {1: g, 2: g, 3: (far_p or p).gxt()}
    # the dark insides under the door and hatch plates: only seen when they stand open
    darks = hole_darks + [B.dark_box(vc, VN, (1.0, 0, 0), 0.21, 0.11, 0.60, DARK_UV)]
    hull_all = B.join([hull_all] + darks); mid = B.join([mid] + darks)
    add('d_hull', 4, None, np.eye(4), {0: arm_hit(hit_h), 1: hull_all.gxt(), 2: mid.gxt(), 3: far.gxt()})
    # ---- kept M4A2 nodes
    for n in T.nodes[1:]:
        nm = n['name']
        if nm == 'd_hull' or nm in OLD.DROP or not (nm in OLD.KEEP or nm.startswith(OLD.KEEP_PREFIX)): continue
        par = T.nodes[n['parent']]['name'] if n['parent'] < len(T.nodes) else 'd_hull'
        if par in OLD.DROP: continue
        g = {L: T.geo[(nm, L)] for L in range(4) if (nm, L) in T.geo}
        if nm in ('d_bottom', 'd_bottom_fr'): g = {0: g[0]} if 0 in g else {}     # the hit shape stays, the model's lower hull is what shows
        Ml = T.local(nm).copy()
        # 9 Nov (user: the wheels did not line up): the M4A2's return rollers ride on trailing arms behind its bogies; the M3's sat on
        # top of the bogie bracket, where the model has their mounts - same height, moved forward onto the brackets
        if nm.startswith('d_wheel_') and par == 'd_hull' and Ml[3, 1] > -0.3 and abs(Ml[3, 2]) < 2.2:
            Ml[3, 2] = min(BOGIE_Z, key=lambda z: abs(z - Ml[3, 2]))
        if nm in ('s_smoke_01', 's_smoke_02'):      # into the model's two exhaust elbows behind the rear plate (were mid-door)
            Ml[3, :3] = (0.58 if nm == 's_smoke_01' else -0.58, 0.0, -2.62)
        add(nm, n['kind'], par if par != 's_root' else None, Ml, g)
    PW = {'d_hull': np.zeros(3)}
    def pbox(name, parent, p, size_=(0.35, 0.5, 0.35)):
        Vb, Fb = geom.box((0, 0, 0), size_); add(name, 1, parent, tr(np.asarray(p, float) - PW[parent]), {0: OLD.hit(Vb, Fb, arm, 'side')})
    def sock(name, parent, p, R=None):
        M = tr(np.asarray(p, float) - PW.get(parent, 0))
        if R is not None: M[:3, :3] = R
        add(name, 0, parent, M)
    def mg_socket(name, parent, lo_, hi_):
        sock(name, parent, ((lo_[0] + hi_[0]) / 2, (lo_[1] + hi_[1]) / 2 - OLD.MG_BORE_Y, hi_[2] - OLD.MG_MUZZLE_Z))
    # ---- crew stations, as m3lee_mesh.py (the hull roof is at the same height within 4 cm)
    pbox('p_driver', 'd_hull', (-0.30, 0.40, 1.05)); sock('s_driver', 'd_hull', (-0.30, 0.70, 1.05))
    sock('s_driver_exit', 'd_hull', (-1.95, -0.20, 0.3)); sock('s_camera_driver_01', 'd_hull', (0.0, 0.82, 1.47))
    sock('s_camera_driver_02', 'd_hull', (-0.60, 1.06, 1.10))
    pbox('p_gunner_02', 'd_hull', (0.45, 0.35, 0.55)); sock('s_gunner_02', 'd_hull', (0.45, 0.66, 0.55))
    pbox('p_loader_02', 'd_hull', (0.85, 0.35, -0.10)); sock('s_loader_02', 'd_hull', (0.85, 0.68, -0.10))
    sock('s_gunner_02_exit', 'd_hull', (1.95, -0.20, 0.3)); sock('s_loader_02_exit', 'd_hull', (1.95, -0.20, -0.4))
    pbox('p_radio', 'd_hull', (0.30, 0.65, -0.70), (0.4, 0.3, 0.3))
    # ---- 75 mm: rotor traverses, a hidden sleeve elevates, the barrel recoils
    cg = sorted(B.split(O['chassis_gun']), key=lambda q: q.lo()[2]); rotor, barrel = cg[0], cg[-1]
    bc = barrel.centre(); G75 = np.array([bc[0], bc[1], rotor.centre()[2]]); PW['d_gun_rot'] = PW['d_gunmask_02'] = PW['d_gun_02'] = G75
    r_l = rotor.moved(G75); add('d_gun_rot', 4, 'd_hull', tr(G75), {**lods(r_l), 0: arm_hit(r_l, 'front')})
    sock('s_camera_gunner_04', 'd_gun_rot', (0.75, 1.07, 1.0))   # 10 Nov: the M1 periscope on the sponson roof, turning with the 75 mm (was on the hull: its sector did not follow the gun)
    Vb, Fb = geom.box((0, 0, 0), (0.12, 0.12, 0.20)); add('d_gunmask_02', 1, 'd_gun_rot', np.eye(4), {0: OLD.hit(Vb, Fb, arm, 'front')})
    b_l = barrel.moved(G75); add('d_gun_02', 4, 'd_gunmask_02', np.eye(4), {**lods(b_l), 0: arm_hit(b_l, 'front')})
    sock('s_gun_02', 'd_gun_02', G75 + [0, 0, barrel.hi()[2] - G75[2]]); PW['s_gun_02'] = PW['d_gun_02']
    # ---- the two fixed bow .30s: socket in the front plate left of the driver, the game's Browning add-ins
    # 9 Nov (user): the guns stand in the model's two port bosses on the small armoured box left of the driver's plate: bores at
    # x -0.655 / -0.435, y 0.24; the bosses' faces at z 1.99 (measured on the model)
    BOW = np.array([-0.545, 0.24, 1.88]); BOW_HALF = 0.11; PW['s_bow_rot'] = PW['d_bow_rot'] = BOW
    sock('s_bow_rot', 'd_hull', BOW)
    Vb, Fb = geom.box((0, 0, 0.10), (0.24, 0.10, 0.34)); add('d_bow_rot', 1, 's_bow_rot', np.eye(4), {0: OLD.hit(Vb, Fb, arm, 'front')})
    MUZ = 0.11              # muzzles at z 1.99, flush with the bosses: the real guns barely showed
    for nm, x in (('s_addin_mg_bow_l', BOW[0] - BOW_HALF), ('s_addin_mg_bow_r', BOW[0] + BOW_HALF)):
        mg_socket(nm, 'd_bow_rot', (x, BOW[1], BOW[2]), (x, BOW[1], BOW[2] + MUZ))
    for nm, x in (('s_mgun_01', BOW[0] - BOW_HALF), ('s_mgun_04', BOW[0] + BOW_HALF)): sock(nm, 'd_bow_rot', (x, BOW[1], BOW[2] + MUZ))
    def backed(p, t=0.008):   # a reversed copy t under the lid (local -y): the inside of an open lid is painted, not see-through
        q = p.moved((0, t, 0)); return B.join([p, B.Part(q.P[:, ::-1], q.T[:, ::-1], -q.N[:, ::-1])])
    # ---- side doors: hinged on their front edge, the node's local z is the hinge
    for s, nm in ((-1, 'd_hatch_02'), (1, 'd_hatch_03')):
        # 10 Nov (user: the hinges were wrong, the insides see-through): the hinge knuckles stay on the hull and the door turns on their
        # axis (x +-1.311, z 0.358); the door gets a painted inner side (local -y is inward)
        d = B.join(doors[nm]); lo, hi = d.lo(), d.hi()
        pivot = np.array([s * 1.311, (lo[1] + hi[1]) / 2, 0.358])
        R = np.array([[0, 0, -1.0], [s, 0, 0], [0, -s, 0]], float); d_l = backed(d.moved(pivot, R))
        M = np.eye(4); M[:3, :3] = R; M[3, :3] = pivot
        add(nm, 4, 'd_hull', M, {**lods(d_l), 0: arm_hit(d_l, 'side')})
    # ---- roof hatch right of the turret, hinged at its rear edge, turned as in m3lee_mesh.py
    # hinge about local z (hatch axis 2): x forward into the lid, y up, z = x cross y = -x world (until 9 Nov the hinge was the
    # vertical axis, so the lid spun flat)
    L4m = B.join(lid4)
    pv = np.array([(lo4[0] + hi4[0]) / 2, 1.017, -0.374]); R4 = np.array([[0, 0, 1.0], [0, 1.0, 0], [-1.0, 0, 0]]); l_l = backed(L4m.moved(pv, R4))
    M = np.eye(4); M[:3, :3] = R4; M[3, :3] = pv
    add('d_hatch_04', 4, 'd_hull', M, {**lods(l_l), 0: arm_hit(l_l, 'roof')})
    sock('s_loader_02_out', 'd_hull', ((lo4[0] + hi4[0]) / 2, hi4[1] - 0.07, (lo4[2] + hi4[2]) / 2))   # 7 cm under the rim, as the Sherman's
    # ---- driver's visor door, hinged on its top edge (the knuckles): local x down the door, y out of the plate, z = -x world
    VV = np.cross(VN, (1.0, 0, 0)); RV = np.array([-VV, VN, (-1.0, 0, 0)]); hv = np.array([vc[0], 0.95, 1.301])
    v_l = backed(VD.moved(hv, RV)); M = np.eye(4); M[:3, :3] = RV; M[3, :3] = hv
    add('d_hatch_05', 4, 'd_hull', M, {**lods(v_l), 0: arm_hit(v_l, 'front')})
    sock('s_driver_out', 'd_hull', (vc[0], vc[1] - 0.40, vc[2] - 0.19))
    # ---- turret
    tur = O['m3_lee_turret']; c = tur.centre(); AX = np.array([c[0], 1.0, c[2]]); PW['d_head'] = AX
    t_l = tur.moved(AX); add('d_head', 4, 'd_hull', tr(AX), {**lods(t_l), 0: arm_hit(t_l, 'front')})
    pbox('p_rothead', 'd_head', AX + [0, -0.20, 0], (1.3, 0.25, 1.3))
    tx, tz = AX[0], AX[2]
    pbox('p_gunner', 'd_head', (tx - 0.35, 0.65, tz + 0.25)); sock('s_gunner', 'd_head', (tx - 0.35, 1.05, tz + 0.25))
    pbox('p_loader', 'd_head', (tx + 0.35, 0.62, tz - 0.10)); sock('s_loader', 'd_head', (tx + 0.35, 1.02, tz - 0.10))
    pbox('p_commander', 'd_head', (tx - 0.32, 0.80, tz - 0.25)); sock('s_commander', 'd_head', (tx - 0.32, 1.25, tz - 0.25))
    sock('s_gunner_exit', 'd_head', (-1.9, -0.2, 0.30)); sock('s_loader_exit', 'd_head', (1.9, -0.2, -0.5)); sock('s_commander_exit', 'd_head', (-1.9, -0.2, -0.5))
    sock('s_camera_loader_01', 'd_head', (tx + 0.40, 1.60, tz + 0.10))
    # ---- 37 mm: the mantlet and the coax elevate, the barrel recoils
    tg = B.split(O['turret_gun']); mant = max(tg, key=len)
    coax = min((q for q in tg if q is not mant), key=lambda q: q.centre()[0] if False else -abs(q.centre()[0] - mant.centre()[0]) if False else (q.hi() - q.lo())[1])
    rest = [q for q in tg if q is not mant and q is not coax]; gun37 = B.join(rest)
    gc = gun37.centre(); G37 = np.array([gc[0], gc[1], mant.centre()[2]]); PW['d_gunmask'] = PW['d_gun'] = G37
    m_l = mant.moved(G37); add('d_gunmask', 4, 'd_head', tr(G37 - AX), {**lods(m_l), 0: arm_hit(m_l, 'front')})
    sock('s_camera_gunner_01', 'd_gunmask', (G37[0] + 0.14, G37[1] + 0.05, mant.hi()[2] + 0.02))   # the M40 telescope elevates with the 37 mm (was fixed to the turret)
    mg_socket('s_addin_mg_coax', 'd_gunmask', coax.lo(), coax.hi())
    pbox('p_rotgun', 'd_gunmask', G37, (0.4, 0.3, 0.3))
    g_l = gun37.moved(G37); add('d_gun', 4, 'd_gunmask', np.eye(4), {**lods(g_l), 0: arm_hit(g_l, 'front')})
    sock('s_gun', 'd_gun', G37 + [0, 0, gun37.hi()[2] - G37[2]]); PW['s_gun'] = PW['d_gun']
    sock('s_mgun_02', 'd_gunmask', (coax.centre()[0], coax.centre()[1], coax.hi()[2]))
    # ---- cupola with its .30; the lid is the top of the cupola's casting, cut out along its flat
    cup = B.split(O['comanders_cupola']); body = max(cup, key=lambda q: (q.hi() - q.lo())[1]); ring = [q for q in cup if q is not body and (q.hi() - q.lo())[0] > 0.5]
    cmg = [q for q in cup if q is not body and q not in ring and (q.hi() - q.lo())[2] > 0.2]; studs = [q for q in cup if q is not body and q not in ring and q not in cmg]
    cc = body.centre(); CUP = np.array([cc[0], body.lo()[1], cc[2]]); PW['d_cupola'] = CUP
    # The lid is the D-shaped top (y above 1.85, behind the flat front edge), in two halves split at the middle knuckles.  As on the
    # real cupola the front half rises on the front knuckles and the rear half folds over onto it, so the pair stands up at the front.
    # Both hinge about their node's local z (hatch axis 2, as the side doors): local x runs from the hinge into the lid, y up.
    tc = body.P.mean(1); top_y = body.hi()[1]
    knuck = sorted(studs, key=lambda q: -q.centre()[2]); k_front, k_fold = knuck[:2], knuck[2:]
    zf = float(np.mean([q.centre()[2] for q in k_front])); zm = float(np.mean([q.centre()[2] for q in k_fold])); ypin = float(np.mean([q.centre()[1] for q in knuck]))
    # 9 Nov, round 3 (user: the cupola looked off - jagged teeth round the opening and the lid): the lid is the faces lying flat on
    # top (every corner within 8 mm of the top), cut exactly at a straight front edge just ahead of the front knuckles and at the
    # fold line, instead of whole triangles picked by their centres
    flat = body.P[:, :, 1].min(1) > top_y - 0.008; zc = zf   # the lid ends at the pin, so opened it does not lap back over the opening
    def clip_part(p, f):
        P_, T_, N_ = [], [], []
        for i in range(len(p.P)):
            poly = B._clip([(p.P[i, k], p.T[i, k], p.N[i, k]) for k in range(3)], f)
            for k in range(1, len(poly) - 1):
                P_.append([poly[0][0], poly[k][0], poly[k + 1][0]]); T_.append([poly[0][1], poly[k][1], poly[k + 1][1]]); N_.append([poly[0][2], poly[k][2], poly[k + 1][2]])
        return B.Part(np.array(P_).reshape(-1, 3, 3), np.array(T_).reshape(-1, 3, 2), np.array(N_).reshape(-1, 3, 3))
    F_ = body.sub(flat)
    lid_all = clip_part(F_, lambda x: x[2] - zc); ahead = clip_part(F_, lambda x: zc - x[2])
    front_p = clip_part(lid_all, lambda x: zm - x[2]); rear_p = clip_part(lid_all, lambda x: x[2] - zm)
    print('  cupola faces', len(body), 'lid faces front / rear', len(front_p), len(rear_p), 'hinges z %.3f / %.3f, pin y %.3f' % (zf, zm, ypin))
    wall = body.sub(~flat); inside = B.Part(wall.P[:, ::-1], wall.T[:, ::-1], -wall.N[:, ::-1])   # 10 Nov (user: see-through): the wall's inner side
    shell = B.join([wall, inside, ahead] + ring + k_front)
    # the dark floor under the open lid: the lid's own outline flattened 10 cm down inside the cupola (9 Nov, user: a rectangle
    # 3 cm under the rim stuck its corners out past the D-shaped opening)
    L_ = lid_all; Pd = L_.P.copy(); Pd[..., 1] = top_y - 0.10
    dark_c = B.Part(Pd, np.tile(DARK_UV, Pd.shape[:2] + (1,)), np.tile((0.0, 1.0, 0.0), Pd.shape[:2] + (1,)))   # the lid's winding: seen from above
    c_l = B.join([shell, dark_c]).moved(CUP)
    add('d_cupola', 4, 'd_head', tr(CUP - AX), {**lods(c_l), 0: arm_hit(body.moved(CUP), 'front')})
    m_ = B.join(cmg); lo_, hi_ = m_.lo(), m_.hi(); CMG = np.array([(lo_[0] + hi_[0]) / 2, (lo_[1] + hi_[1]) / 2, lo_[2] + 0.02]); PW['d_mgun_body'] = CMG
    Vb, Fb = geom.box((0, 0, 0.10), (0.08, 0.08, 0.30)); add('d_mgun_body', 1, 'd_cupola', tr(CMG - CUP), {0: OLD.hit(Vb, Fb, arm, 'front')})
    mg_socket('s_addin_mg_cup', 'd_mgun_body', lo_, hi_)
    sock('s_mgun_03', 'd_mgun_body', (CMG[0], CMG[1], hi_[2]))
    sock('s_commander_out', 'd_cupola', CUP + [0, top_y - CUP[1] - 0.15, 0.0])   # 15 cm under the rim, as the Sherman's
    sock('s_camera_commander', 'd_cupola', CUP + [0, 0.20, 0.30])   # 10 Nov: restored - an earlier comment had swallowed it (his M6 periscope had no camera)
    RL = np.array([[0, 0, -1.0], [0, 1.0, 0], [1.0, 0, 0]])           # x rearward into the lid, y up, z along +x: a proper rotation
    H1 = np.array([cc[0], ypin, zf]); H2 = np.array([cc[0], ypin, zm])
    # the lid halves are only the cupola's top faces: give each an underside 12 mm down (9 Nov, user: the open lid showed as a
    # black jagged plate - its back faces were culled and the dark plate under it showed through)
    def plated(p): q = p.moved((0, 0.012, 0)); return B.join([p, B.Part(q.P[:, ::-1], q.T[:, ::-1], -q.N[:, ::-1])])
    # 10 Nov (user: the lid floated): the game turns each hatch on its own, so a folding second leaf parented to the first was left
    # behind in mid-air.  One lid now, both halves, rising on the front knuckles.
    # 10 Nov (user): two leaves, each on its own hinge on the cupola, swinging through their full range - the front leaf on the front
    # knuckles opening forward, the rear leaf on the lid's rear edge opening backward.  Both children of the cupola (the game turns
    # each hatch on its own; a leaf parented to the other was left in mid-air)
    # 10 Nov (user: the rear leaf stayed behind when the tank moved): one lid, both leaves together on the front knuckles - the game
    # turns each hatch on its own and cannot carry one leaf on the other
    # 10 Nov (user: folded when open): the rear leaf is the front leaf's child on the middle knuckles - it folds 180 deg over onto the
    # front leaf (pin 1 cm over the leaves, so the folded leaf lies on top, not through it) and the front leaf carries the pair forward
    # 10 Nov (user: the folded leaf floated / was left behind): the game does not place a hatch hung on another hatch, so the lid is one
    # piece - both leaves and the middle knuckles - turning on the front knuckles' pin (its centre: x of the cupola, y / z of the studs)
    # 10 Nov (user: the folded rear leaf floated off the tank): the game does not carry a hatch on another hatch - the rear leaf was
    # placed relative to the cupola and ended up off the vehicle.  One lid, both leaves, on the front knuckles' pin
    kf = B.join(k_front); H1 = np.array([cc[0], kf.centre()[1], kf.centre()[2]])
    f_l = B.join([plated(front_p), plated(rear_p)] + k_fold).moved(H1, RL)
    M1 = tr(H1 - CUP); M1[:3, :3] = RL; add('d_hatch_01', 4, 'd_cupola', M1, {**lods(f_l), 0: arm_hit(f_l, 'roof')})
    # ---- vision ports (9 Nov, user: most of the model's ports gave nobody a view): a camera behind each, its local z out of the port.
    # Positions measured on the model: door slit blocks, the front-left corner block, the visor's vision block, the sponson side,
    # the 37 mm turret's side slits, the cupola's two front slits.
    def look(d):
        z = np.asarray(d, float); z /= np.linalg.norm(z); y = np.array([0, 1.0, 0]); x = np.cross(y, z); x /= np.linalg.norm(x); return np.array([x, np.cross(z, x), z])
    # 10 Nov: the ports the user marked in red in game: visor, front-left corner block, both door slits, the slit block on the
    # right-rear corner bevel, the 37 mm turret's front slit (right of the gun) and side slits, the cupola's front slit
    for nm, par, p, d in (('s_camera_driver_03', 'd_hull', (vc[0], vc[1], vc[2] - 0.04), (0, 0, 1.0)),
                          ('s_camera_driver_04', 'd_hull', (-1.29, 0.749, 0.02), (-1.0, 0, 0)),
                          ('s_camera_driver_05', 'd_hull', (-0.944, 0.86, 1.15), (-0.5, 0, 0.87)),
                          ('s_camera_loader_02_01', 'd_hull', (1.29, 0.749, 0.02), (1.0, 0, 0)),
                          ('s_camera_loader_02_02', 'd_hull', (1.17, 0.88, -0.53), (0.71, 0, -0.71)),
                          ('s_camera_gunner_02', 'd_head', (-1.03, 1.30, -0.25), (-1.0, 0, 0)),
                          ('s_camera_gunner_03', 'd_head', (-0.55, 1.40, 0.10), (0, 0, 1.0)),
                          ('s_camera_loader_02', 'd_head', (0.41, 1.30, -0.25), (1.0, 0, 0)),
                          ('s_camera_commander_01', 'd_cupola', (-0.80, 1.78, -0.26), (0, 0, 1.0))):
        sock(nm, par, p, look(d))
    # ---- lights, fires, marks, riders (positions from m3lee_mesh.py; the deck and box tops are the model's)
    for s, nm in ((-1, 's_light_02'), (1, 's_light_03')): sock(nm, 'd_hull', (s * 0.88, 0.25, 2.17))
    sock('s_fire_01', 'd_hull', (-0.20, 0.60, 0.9)); sock('s_fire_02', 'd_hull', (0.60, 0.60, 0.3)); sock('s_fire_03', 'd_head', (tx, 1.45, tz))
    sock('s_fire_05', 'd_head', (tx + 0.2, 1.3, tz - 0.2))
    Rl = np.array([[0, 0, 1.0], [0, 1.0, 0], [-1.0, 0, 0]]); Rr = np.array([[0, 0, -1.0], [0, 1.0, 0], [1.0, 0, 0]])
    for nm, p, R in (('s_mark_04', (tx - 0.82, 1.32, tz - 0.10), Rl), ('s_mark_04f', (tx - 0.82, 1.32, tz + 0.10), Rl),
                     ('s_mark_05', (tx + 0.82, 1.32, tz + 0.10), Rr), ('s_mark_05f', (tx + 0.82, 1.32, tz - 0.10), Rr)):
        M = tr(np.asarray(p) - PW['d_head']); M[:3, :3] = R.T; add(nm, 0, 'd_head', M)
    for nm, p, R in (('s_mark_03', (1.30, 0.40, -0.75), Rr), ('s_mark_03f', (1.30, 0.40, -1.00), Rr),
                     ('s_mark_02', (-1.30, 0.40, -1.00), Rl), ('s_mark_02f', (-1.30, 0.40, -0.75), Rl)):
        M = tr(p); M[:3, :3] = R.T; add(nm, 0, 'd_hull', M)
    des = [(-0.40, 0.72, -1.60), (0.40, 0.72, -1.60), (-0.40, 0.62, -2.20), (0.40, 0.62, -2.20), (0.0, 0.66, -1.90), (1.0, 0.16, -1.95), (-1.0, 0.16, -1.95), (0.0, 0.58, -2.50)]
    for k, p in enumerate(des, 1): sock('s_des_%02d' % k, 'd_hull', p)
    for k, p in enumerate([(-1.9, -0.2, -2.4), (1.9, -0.2, -2.4), (0.2, -0.2, -3.5)], 1): sock('s_des_out_%02d' % k, 'd_hull', p)
    print('pivots: 75 mm %s bow %s turret %s 37 mm %s cupola %s' % tuple(np.round(p, 3).tolist() for p in (G75, BOW, AX, G37, CUP)))
    return nodes

def textures(tex, out, ref=None):
    L = lambda s: os.path.join(tex, 'm3_lee_%s' % s)
    layers = [(ATLAS['m3_lee_chassis'], L('chassis_alb.tga'), L('chassis_norm.tga'), (L('chassis_ao.tga'), 0), (L('chassis_rough.tga'), 0)),
              (ATLAS['m3_lee_turret'], L('turret_alb.tga'), L('turret_norm.tga'), (L('turret_ao.tga'), 0), (L('turret_rough.tga'), 0))]
    dif, nrm = B.build_textures(layers, None, DARK_RECT, ref)
    B.write_textures(dif, nrm, out, 'mlee')
    return dif

if __name__ == '__main__':
    m4a2, obj, tex, out = sys.argv[1:5]; ref = sys.argv[5] if len(sys.argv) > 5 else None
    nodes = build(m4a2, obj)
    # the GXT2 blocks draw with the template's third material record (block header byte = material index): m4a2_sherman_dift /
    # m4a2_sherman_norsp.  Until 9 Nov only the name-only first record was renamed and the Lee was painted with the Sherman's sheet.
    data = B.rename_material(SM.assemble(nodes, m4a2), (b'm4a2_dift', b'm4a2_sherman_dift', b'm4a2_sherman_norsp'), (MATERIAL[0],) + MATERIAL)
    p = os.path.join(out, 'm3lee.mesh.loc_def.bin'); open(p, 'wb').write(data)
    m = azg2.read(p); print('written', p, len(data), 'bytes;', len(m['nodes']), 'nodes;', [(b['tag'], b['nv'], b['ni']) for b in m['blocks']], [mt['name'] for mt in m['materials']])
    textures(tex, out, ref)
    print('textures written')

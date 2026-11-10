"""IS-2 game mesh, on the KV-1S's skeleton, from two of the user's models: everything from the detailed one (Downloads\\is2: IS-2.glb, Textures.zip),
except the gun, which is the barrel and muzzle brake of the low-poly one (Downloads\\low-poly-is-2-soviet-heavy-tank.zip: Kado_3D_IS_2.obj, IS_2_Textures.zip).

  python is2_bought.py <kv1s_late mesh> <IS-2.glb> <textures dir> <Kado_3D_IS_2.obj> <low-poly textures dir> <out dir> [game diffuse, for the paint]

The models are licensed to the user: they and everything made from them stay out of the repository.  The detailed model's 3.36 million triangles are
cut to about 40 000 by tools\\m13\\glb_reduce.py; its tracks and moving suspension are not used.

Frame: game = (-Z, Y - 0.261, -X - 2.79): the model's nose points to -X, its sprocket axle lies at the origin and lands on the
KV-1S's (-2.771).  Its turret is posed turned 15 deg and its gun raised 4.4 deg: both are put straight here.
The barrel keeps its own length (BARREL_SCALE 1.0), its root sunk SEAT metres into the mantlet's collar on the detailed model's bore.
From the KV-1S: road wheels, sprockets, idlers, rollers, track, the balance arms and the tables; crew positions and damage
boxes as its nodes, re-laid on the IS-2's hull and turret.  The wheels stand where the model's stood.
"""
import sys, os, re, tempfile, numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import azg2, geom, bought as B, su122_mesh as SM, m3lee_mesh as OLD, glb_reduce as R

Y_OFF, Z_OFF = -0.261, -2.79
ATLAS = {'Chassis': (0.0, 0.0, 0.625, 0.625), 'Turret': (0.625, 0.0, 0.375, 0.375), 'Fittings': (0.625, 0.375, 0.25, 0.25),
         'SuspensionLeft': (0.625, 0.625, 0.1875, 0.1875), 'SuspensionRight': (0.8125, 0.625, 0.1875, 0.1875)}
GUN_RECT = (0.0, 0.625, 0.296, 0.375)   # the low-poly model's barrel, cropped from its sheet
PLAIN_UV = np.array((0.31, 0.31))   # a plain olive spot of the chassis for the KV-1S's own balance arms: they are hidden behind the game's wheels
MATERIAL = (b'is2_dift', b'is2_norsp')
TOTAL = 19000                       # 10 Nov: 40 000 overflowed the 16-bit indices once vertex normals were split more finely
BARREL_SCALE = 1.0                  # 1.0: the barrel as the low-poly model has it
SEAT = 0.05                         # how far the barrel's root sits inside the mantlet's collar

ROAD_Y = -0.721                     # the KV-1S's axle height: its 0.60 m wheels on the same ground line
L_X = [-4.893, -4.013, -3.133, -2.253, -1.323, -0.573]; R_X = [-5.028, -4.148, -3.268, -2.388, -1.458, -0.708]   # raw X, front to rear
IDLER_X, IDLER_Y, ROLL_X, ROLL_Y, TRACK = -5.69, 0.04, (-4.5, -2.7, -1.0), 0.175, 1.21

def weight(name, mat):
    if name.startswith(('TurretBody',)): return 3.2
    if name.startswith('122mm') or name.startswith('MuzzleBrake'): return 2.0
    if name.startswith('SideSkirt'): return 50.0          # thin sheets: reducing them leaves spikes along their edges
    if name.startswith(('Cupola', 'TurretPeriscope', 'CupolaPeriscope', 'ChassisPeriscope', 'TurretGunHousing', 'Mantlet', 'LoaderHatch')): return 5.0   # 10 Nov: holes when cut hard
    if name.startswith(('GasTank', 'GasTankBase')): return 4.0             # 10 Nov: the drums' skins tore when cut down hard
    if name.startswith(('EngineDeckPlate', 'EngineDeckAirIntake', 'ChassisBackPlate', 'EngineBackHatch')): return 6.0   # thin sheets: folds when cut hard
    if mat == 'Chassis' or name.startswith('TurretTopPlate'): return 6.0
    if mat.startswith('Suspension'): return 0.7
    if name.startswith('EngineDeckGrill'): return 0.40
    if name.startswith('Hook'): return 0.35
    if name.startswith('Ring'): return 0.25
    return 1.0

def to_game(p):
    return np.stack([-p[..., 2], p[..., 1] + Y_OFF, -p[..., 0] + Z_OFF], -1)

def tr(p): M = np.eye(4); M[3, :3] = p; return M

def _rot(axis, ang):
    a = np.asarray(axis, float); a /= np.linalg.norm(a); K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(ang) * K + (1 - np.cos(ang)) * K @ K

def _spin(v, R_, pivot):
    """column-vector rotation about a pivot, in the model's frame"""
    v['P'] = (v['P'] - pivot) @ R_.T + pivot; v['N'] = v['N'] @ R_.T

def under(nodes, name, roots):
    while name:
        if name in roots: return True
        name = nodes[name]['parent'] if name in nodes else None
    return False

def load(glb, wheels=False):
    # parents that carry no mesh of their own do not occur in this file: every node has geometry
    # the axle housings, roller brackets and stops are fixed to the hull and stay; what moves is the game's.  The spare track links
    # (120 000 triangles of small holes) do not survive any reduction: only their racks stay
    # wheels=True keeps the model's own wheels and arms, for the wreck (is2_wreck.py), where nothing moves and the game adds no running gear
    FIXED = re.compile(r'(DriveWheelBase|ArmBase|RollerBase|SwingArmStop|IdlerWheelArmBase|IdlerTensor)')
    N = R.load_glb(glb, skip=lambda n, m: m == 'Track' or (m.startswith('Suspension') and not wheels and not FIXED.match(n)))
    # straighten the pose: gun elevation about the trunnion, then the turret about the ring's axis
    trun = N['Mantlet_1.1']['pos'].copy(); muz = N['MuzzleBrake']['pos'].copy(); ring = N['Ring_1']['pos'].copy()
    d = muz - trun; h = np.array([d[0], 0.0, d[2]]); elev = np.arctan2(d[1], np.linalg.norm(h))
    axis = np.cross(d, h); Re = _rot(axis, np.arctan2(np.linalg.norm(np.cross(d, h)), d @ h))
    yaw = np.arctan2(d[2], -d[0]); print('pose: gun raised %.2f deg, turret turned %.2f deg' % (np.degrees(elev), np.degrees(yaw)))
    Ry = _rot((0, 1, 0), yaw)     # takes a vector in the (-X, Z) direction of the gun back onto -X
    if np.linalg.norm((d @ Re.T) @ Ry.T * [0, 0, 1]) > np.linalg.norm((d @ Re.T) @ Ry * [0, 0, 1]): Ry = Ry.T
    for k, v in N.items():
        if under(N, k, ('Mantlet_1.1',)): _spin(v, Re, trun)
        if under(N, k, ('Ring_1',)): _spin(v, Ry, ring)
    for k, v in N.items():
        if under(N, k, ('Ring_1',)): v['pos'] = (v['pos'] - ring) @ Ry.T + ring
    trun2 = (trun - ring) @ Ry.T + ring; muz2 = ((muz - trun) @ Re.T + trun - ring) @ Ry.T + ring
    print('after: trunnion %s muzzle %s' % (np.round(trun2, 3).tolist(), np.round(muz2, 3).tolist()))
    # game frame, atlas uvs; x changes hand, so the windings reverse
    for v in N.values():
        v['P'] = to_game(v['P'])[:, [0, 2, 1]]; v['N'] = np.stack([-v['N'][..., 2], v['N'][..., 1], -v['N'][..., 0]], -1)[:, [0, 2, 1]]; v['T'] = v['T'][:, [0, 2, 1]]
        u0, v0, w, h_ = ATLAS[v['mat']]; v['T'] = np.stack([u0 + np.clip(v['T'][..., 0], 0, 1) * w, v0 + np.clip(v['T'][..., 1], 0, 1) * h_], -1)
    return N, to_game(trun2), to_game(muz2), to_game(ring)

def part(N, names, targets, f=1.0):
    ps = []
    for k in names:
        v = N[k]; t = max(4, int(targets[k] * f)); P, T, Nn = R.reduce_part(v['P'], v['T'], v['N'], t); Nn = B.recompute_normals(P); ps.append(B.Part(P, T, Nn))
        if k.startswith(DOUBLE): ps.append(B.Part(P[:, ::-1], T[:, ::-1], -Nn[:, ::-1]))   # back side drawn too
    return B.join(ps)

# 10 Nov (user: dark wedges on the engine deck and rear plates): thin sheets whose backs show once reduced (the air intake's sawtooth
# ramps, the deck and rear plates, the exhaust hatches) get a reversed copy - their backs are drawn painted instead of see-through
DOUBLE = ('EngineDeckAirIntake', 'EngineDeckPlate', 'EngineDeckHatch', 'ChassisBackPlate', 'EngineBackHatch')   # the rear plates keep half their faces instead (KEEP) and no longer fold

def load_lp_barrel(path):
    """the low-poly model's barrel and muzzle brake (one piece, the one that reaches furthest forward), metres, game axes, uvs of its own sheet with v down"""
    V, VT, VN, G = [], [], [], []
    for l in open(path, errors='replace'):
        t = l.split()
        if not t: continue
        if t[0] == 'v': V.append([float(a) for a in t[1:4]])
        elif t[0] == 'vt': VT.append([float(a) for a in t[1:3]])
        elif t[0] == 'vn': VN.append([float(a) for a in t[1:4]])
        elif t[0] == 'f':
            q = [tuple(int(x) - 1 if x else 0 for x in a.split('/')) for a in t[1:]]
            for k in range(1, len(q) - 1): G.append((q[0], q[k], q[k + 1]))
    V = np.array(V) * 0.01 * [-1.0, 1.0, 1.0]; VT = np.array(VT); VN = np.array(VN) * [-1.0, 1.0, 1.0]; VN /= np.maximum(np.linalg.norm(VN, axis=1, keepdims=True), 1e-9)
    f = np.array(G)[:, [0, 2, 1]]; uv = VT[f[:, :, 1]].copy(); uv -= np.floor(uv.mean(1, keepdims=True)); uv = np.clip(uv, 0, 1); uv[..., 1] = 1.0 - uv[..., 1]
    return max(B.split(B.Part(V[f[:, :, 0]], uv, VN[f[:, :, 2]])), key=lambda q: q.hi()[2])

def fit_gun(bar, trun, collar_z):
    """on the detailed model's bore, the root SEAT inside the collar; uvs into GUN_RECT.  Returns the part and the crop of the low-poly sheet"""
    lo, hi = bar.lo(), bar.hi(); P = bar.P - [(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]]; P = P * [1.0, 1.0, BARREL_SCALE] + [trun[0], trun[1], collar_z - SEAT]
    t = bar.T.reshape(-1, 2); crop = (t.min(0) - 0.002).clip(0, 1).tolist() + (t.max(0) + 0.002).clip(0, 1).tolist(); u0, v0, w, h = GUN_RECT
    T = np.stack([u0 + (bar.T[..., 0] - crop[0]) / (crop[2] - crop[0]) * w, v0 + (bar.T[..., 1] - crop[1]) / (crop[3] - crop[1]) * h], -1)
    return B.Part(P, T, bar.N), crop, bar.T

def build(kv_path, glb, lp_obj):
    K = SM.Src(kv_path); arm = OLD.arm_points(K)
    N, TRUN, MUZ, RING = load(glb)
    N.pop('122mm_D25_T'); N.pop('MuzzleBrake')          # its own gun is replaced; the mantlet and collar stay
    Pc = N['Mantlet_1.2']['P'].reshape(-1, 3); collar = float(Pc[:, 2].max())
    # the bore on the collar ring's centre (9 Nov, user: gun misaligned - on the trunnion's height it stood 2.8 cm over the ring's centre)
    ring_ = Pc[Pc[:, 2] > collar - 0.05]; BORE = np.array([(ring_[:, 0].min() + ring_[:, 0].max()) / 2, (ring_[:, 1].min() + ring_[:, 1].max()) / 2, TRUN[2]])
    print('collar ring centre x %.3f y %.3f, trunnion x %.3f y %.3f' % (BORE[0], BORE[1], TRUN[0], TRUN[1]))
    Gun, crop, bar_uv = fit_gun(load_lp_barrel(lp_obj), BORE, collar); MUZ = np.array([BORE[0], BORE[1], Gun.hi()[2]])
    print('gun: %d tris, collar front z %.3f, root z %.3f, muzzle z %.3f' % (len(Gun), collar, Gun.lo()[2], MUZ[2]))
    # 10 Nov (user: black wedges on drums, rear plate, turret roof): the inner walls of hollow parts are removed before reduction
    dropped = 0
    for k, v in N.items():
        if len(v['P']) > 9000: continue
        hid = B.hidden_faces(v['P'], min_hits=3 if k.startswith('GasTank_') else 5)   # the drums: thin tubes open at the ends
        if hid.any() and hid.sum() < len(hid):
            for key in ('P', 'T', 'N'): v[key] = v[key][~hid]
            dropped += int(hid.sum())
    print('hidden inner faces removed:', dropped)
    for k in [k for k in N if k.startswith(('ScapeBottomHatch', 'EngineBottomHatch'))]: N.pop(k)   # 10 Nov: under the belly, never seen; vertices for the plates that are
    SRC_UV.clear(); SRC_UV.extend(v['T'] for v in N.values())     # the source islands, for the texture gap fill
    counts = {k: len(v['P']) for k, v in N.items()}
    w = {k: weight(k, N[k]['mat']) for k in N}
    # the budget: count ** 0.62 shares, multiplied by the part's weight, scaled to TOTAL
    c = np.array([counts[k] for k in N], float); ww = np.array([w[k] for k in N]); lo, hi = 1e-4, 1e4
    for _ in range(60):
        s = (lo * hi) ** 0.5; t = np.minimum(c, np.maximum(8, s * ww * c ** 0.62))
        if t.sum() > TOTAL: hi = s
        else: lo = s
    targets = dict(zip(N, t.astype(int)))
    # 10 Nov: the visible plates folded into zigzags when cut to a tenth (mantlet 1804 -> 186, rear plate 1676 -> 212); they keep a
    # share of their own, paid for by the running gear mounts that stand behind the game's wheels
    KEEP = {'Mantlet': 0.6, 'ChassisBackPlate': 0.3, 'TurretGunHousing': 0.3, 'EngineBackHatch': 0.3, 'TurretPeriscope': 0.35,
            'CupolaPeriscope': 0.35, 'ChassisPeriscope': 0.35}
    for k in N:
        for pre, fr in KEEP.items():
            if k.startswith(pre): targets[k] = max(targets[k], int(counts[k] * fr))
        if N[k]['mat'].startswith('Suspension'): targets[k] = max(8, targets[k] // 3)
    print('parts', len(N), 'source tris', int(c.sum()), 'target', int(t.sum()), {k: targets[k] for k in ('TurretBody_1.1', 'ChassisFront_1', 'TurretGunHousing_1.1', 'EngineDeckGrill_1')})
    names = list(N)
    gun = []
    mask = [k for k in names if under(N, k, ('Mantlet_1.1',)) and k not in gun]
    lid_a = [k for k in names if re.match(r'(Cupola_1\.2|CupolaPeriscope_)', k)]; lid_b = ['Cupola_1.3']
    lid_c = [k for k in ('LoaderHatch_1.1', 'LoaderHatch_1.2', 'LoaderHatch_1.3') if k in N]
    moved = set(gun + mask + lid_a + lid_b + lid_c + ['MG_Port_1.2'])
    turret = [k for k in names if under(N, k, ('Ring_1',)) and k not in moved]
    hull = [k for k in names if not under(N, k, ('Ring_1',))]
    print('turret parts', len(turret), 'hull parts', len(hull), 'gun', gun, 'mask', mask)
    nodes = []
    def add(name, kind, parent, M, geo=None): nodes.append(dict(name=name, kind=kind, parent=parent, M=M, geo=geo or {}))
    def hit(p, cls=None): return OLD.hit(*p.plain(), arm, cls)
    def lods(fn):
        """LOD 1 at the budget, LOD 2 half of it, LOD 3 a tenth"""
        return {1: fn(1.0).gxt(), 2: fn(0.45).gxt(), 3: fn(0.10).gxt()}
    # ---- hull
    H1 = part(N, hull, targets); shell = [k for k in hull if N[k]['mat'] == 'Chassis']; S = part(N, shell, targets, 0.5)
    print('hull LOD1 tris', len(H1), 'hit tris', len(S))
    add('d_hull', 4, None, np.eye(4), {0: hit(S), 1: H1.gxt(), 2: part(N, hull, targets, 0.45).gxt(), 3: part(N, shell + ['Ring_5'], targets, 0.15).gxt()})
    # ---- running gear: KV-1S nodes at the model's positions; the balance arms keep their offset from their wheel
    W = {}
    def gear(name, x, y, z): W[name] = np.array([x, y, z], float)
    for side, xs, ids, s in (('l', L_X, range(2, 8), -1.0), ('r', R_X, range(13, 19), 1.0)):
        for k, X in zip(ids, xs): gear('d_wheel_%02d' % k, s * TRACK, ROAD_Y, -X + Z_OFF)
    gear('d_wheel_01', -TRACK, IDLER_Y + Y_OFF, -IDLER_X + Z_OFF); gear('d_wheel_12', TRACK, IDLER_Y + Y_OFF, -IDLER_X + Z_OFF)
    gear('d_wheel_08', -TRACK, Y_OFF, Z_OFF); gear('d_wheel_19', TRACK, Y_OFF, Z_OFF)
    for k, X in zip((9, 10, 11), ROLL_X): gear('d_wheel_%02d' % k, -TRACK, ROLL_Y + Y_OFF, -X + Z_OFF)
    for k, X in zip((22, 21, 20), ROLL_X): gear('d_wheel_%02d' % k, TRACK, ROLL_Y + Y_OFF, -X + Z_OFF)
    world = {n['name']: n['world'][3, :3].copy() for n in K.nodes}
    # KV-1S wheels in the same order: which swing arm belongs to which wheel comes from the vehicle's carets table (row order)
    pairs = [('d_balansir_%02d' % (i + 1), 'd_wheel_%02d' % w_) for i, w_ in enumerate(list(range(2, 8)) + list(range(13, 19)))]
    arm_of = dict(pairs)
    for name, p in W.items():
        M = K.local(name).copy(); M[3, :3] = p; g = {0: K.geo[(name, 0)]} if (name, 0) in K.geo else {}
        add(name, K.node(name)['kind'], 'd_hull', M, g)
    for name, wh in pairs:
        p = W[wh] + (world[name] - world[wh]) * [TRACK / 1.331, 1, 1]
        M = K.local(name).copy(); M[3, :3] = p
        g = {}
        for L in range(4):
            if (name, L) in K.geo:
                A, F = K.geo[(name, L)]; A = A.copy()
                if L > 0: A[:, 3:5] = PLAIN_UV
                g[L] = (A, F)
        add(name, K.node(name)['kind'], 'd_hull', M, g)
    # ---- turret: the KV-1S's turret-local sockets and boxes stay relative to the ring
    PW = {'d_hull': np.zeros(3), 'd_head': RING}
    tur_keep = lambda f: part(N, turret, targets, f)
    T0 = {L: None for L in range(4)}
    add('d_head', 4, 'd_hull', tr(RING), {0: hit(part(N, [k for k in turret if k.startswith(('TurretBody', 'TurretGunHousing', 'TurretTopPlate'))], targets, 0.6).moved(RING), 'side'),
                                         **lods(lambda f: tur_keep(f).moved(RING))})
    # gun: the mantlet elevates, the barrel recoils
    PW['d_gunmask'] = PW['d_gun'] = TRUN
    add('d_gunmask', 4, 'd_head', tr(TRUN - RING), {0: hit(part(N, mask, targets).moved(TRUN), 'front'), **lods(lambda f: part(N, mask, targets, f).moved(TRUN))})
    G_l = Gun.moved(TRUN); add('d_gun', 4, 'd_gunmask', np.eye(4), {0: hit(G_l, 'front'), **lods(lambda f: G_l)})
    add('s_gun', 0, 'd_gun', tr(MUZ - TRUN))
    add('s_mgun', 0, 'd_gunmask', tr((0.12, -0.02, 0.62)))     # co-axial DT in the mantlet, to the gun's right
    # hatches: local z along the hinge (hatch axis 2), local x from the hinge into the lid, y up; the tables open them with a positive
    # angle (9 Nov: they were hinged about local x with axis 1, which is the vertical - the lids spun flat into the roof)
    def hatch(name, lid, h0, h1, parent='d_head'):
        L = part(N, lid, targets); h0, h1 = np.asarray(h0, float), np.asarray(h1, float); a = h1 - h0; a[1] = 0; a /= np.linalg.norm(a); y = np.array([0, 1.0, 0])
        c = L.P.reshape(-1, 3).mean(0); piv = (h0 + h1) / 2; x = np.cross(a, y)
        if (c - piv) @ x < 0: x = -x
        Rm = np.array([x, y, np.cross(x, y)]); M = np.eye(4); M[:3, :3] = Rm; M[3, :3] = piv - PW[parent]
        L_l = L.moved(piv, Rm)
        # 10 Nov (user: a black hole on the roof): the lids have no underside - opened, only their back faces show and the game culls
        # them.  A reversed copy 8 mm under the lid (local y down) gives the open lid a painted inside, as on the M3's cupola
        q_ = L_l.moved((0, 0.008, 0)); L_l = B.join([L_l, B.Part(q_.P[:, ::-1], q_.T[:, ::-1], -q_.N[:, ::-1])])
        def lid_lod(f):
            Lf = part(N, lid, targets, f).moved(piv, Rm); qf = Lf.moved((0, 0.008, 0)); return B.join([Lf, B.Part(qf.P[:, ::-1], qf.T[:, ::-1], -qf.N[:, ::-1])]).gxt()
        add(name, 4, parent, M, {0: hit(L_l, 'roof'), 1: lid_lod(0.5), 2: lid_lod(0.25), 3: lid_lod(0.08)})   # 10 Nov: lids were full detail at every distance
    def world_of(k): return to_game(((N[k]['pos'] - N['Ring_1']['pos']) if False else N[k]['pos'])[None])[0]
    # the cupola's two-leaf lid: hinge lines through the hinge blocks (positions were straightened with the turret)
    hatch('d_hatch_04', lid_a, world_of('CupolaHinge_3.1'), world_of('CupolaHinge_4.1'))
    hatch('d_hatch_05', lid_b, world_of('CupolaHinge_1.1'), world_of('CupolaHinge_2.1'))
    Lc = part(N, lid_c, targets); lo, hi = Lc.lo(), Lc.hi()
    hatch('d_hatch_03', lid_c, (lo[0], hi[1], hi[2]), (hi[0], hi[1], hi[2]))     # the loader's lid, hinged at its front edge
    # machine guns: the rear ball in the turret (head3) and the fixed bow gun (head2), their rotation kept from the KV-1S
    ball = to_game(N['MG_Port_1.2']['pos'][None])[0]; PW['s_bow_rot_03'] = PW['d_mgun_02'] = ball
    M = K.local('s_bow_rot_03').copy(); M[3, :3] = ball - RING; add('s_bow_rot_03', 0, 'd_head', M)
    b_l = part(N, ['MG_Port_1.2'], targets).moved(ball)
    add('d_mgun_02', 4, 's_bow_rot_03', np.eye(4), {0: hit(b_l, 'side'), 1: b_l.gxt(), 2: b_l.gxt(), 3: b_l.gxt()})
    add('s_mgun3', 0, 'd_mgun_02', tr((0, 0, 0.25)))
    bow = N['MG_Port_2.1']['P'].reshape(-1, 3).mean(0); PW['s_bow_rot_02'] = PW['d_mgun_01'] = bow
    M = K.local('s_bow_rot_02').copy(); M[3, :3] = bow; add('s_bow_rot_02', 0, 'd_hull', M)
    Vb, Fb = geom.box((0, 0, 0.05), (0.08, 0.08, 0.20)); add('d_mgun_01', 1, 's_bow_rot_02', np.eye(4), {0: OLD.hit(Vb, Fb, arm, 'front')})
    add('s_mgun2', 0, 'd_mgun_01', tr((0, 0, 0.25)))
    # ---- the KV-1S's crew stations, cameras, damage boxes, fires, marks, riders; hatches that have no part here stand empty
    done = {n['name'] for n in nodes}; turret_side = {'d_head'}
    def in_turret(n):
        while True:
            pn = K.nodes[n['parent']]['name'] if n['parent'] < len(K.nodes) else None
            if pn is None or pn in ('s_root', 'd_hull'): return False
            if pn == 'd_head': return True
            n = K.node(pn)
    drop_visual = re.compile(r'd_(wing|mwing|tank|sparetrack|zipbox|tros|bukserga|gabarit|signal|schitok|koziryok|rearlight|maskgruz|antena|wingholder)')
    def in_mask(n):
        while True:
            pn = K.nodes[n['parent']]['name'] if n['parent'] < len(K.nodes) else None
            if pn is None or pn in ('s_root', 'd_hull', 'd_head'): return False
            if pn == 'd_gunmask': return True
            n = K.node(pn)
    for n in K.nodes[1:]:
        nm = n['name']
        if nm in done or drop_visual.match(nm) or nm == 'd_hull': continue
        if not nm.startswith(('p_', 's_', 'd_hatch_', 'd_comsight_cap', 'd_sight', 'd_light')): continue
        wp = n['world'][3, :3].copy()
        kv_head = world['d_head']
        if in_mask(n):                                     # sights and the gun's damage box follow the gun's elevation
            M = np.eye(4); M[:3, :3] = n['world'][:3, :3]; M[3, :3] = wp - world['d_gunmask']; parent = 'd_gunmask'
        elif in_turret(n):
            M = K.local(nm).copy() if K.nodes[n['parent']]['name'] == 'd_head' else np.eye(4)
            if K.nodes[n['parent']]['name'] != 'd_head': M[:3, :3] = n['world'][:3, :3]
            M[3, :3] = wp - kv_head; parent = 'd_head'
        else:
            M = K.local(nm).copy() if K.nodes[n['parent']]['name'] == 'd_hull' else np.eye(4)
            if K.nodes[n['parent']]['name'] != 'd_hull': M[:3, :3] = n['world'][:3, :3]
            M[3, :3] = wp + [0, 0, 0]; parent = 'd_hull'
        kind = n['kind']; g = {}
        if nm.startswith('p_') and (nm, 0) in K.geo: g = {0: K.geo[(nm, 0)]}
        if nm.startswith(('d_hatch_', 'd_comsight', 'd_sight', 'd_light')): kind = 0     # no part of their own: empty, the table rows stay valid
        add(nm, kind, parent, M, g)
    # ---- vision ports (9 Nov, user: the sight sectors from the vision ports).  The KV-1S's cameras stood where the KV's ports are;
    # each now sits behind the IS-2 model's own device (named parts: ChassisPeriscope_1/2, TurretPeriscope_1/2, CupolaPeriscope_1)
    # or on its surfaces found with rays (glacis visor, mantlet telescope aperture, turret side ports, the cupola's six slits).
    def look(d):
        z = np.asarray(d, float); z /= np.linalg.norm(z); yv = np.array([0, 1.0, 0]); x = np.cross(yv, z); x /= np.linalg.norm(x); return np.array([x, np.cross(z, x), z])
    def setcam(name, parent, wpos, d):
        base = {'d_hull': np.zeros(3), 'd_head': RING, 'd_gunmask': TRUN}[parent]; Mc = np.eye(4); Mc[:3, :3] = look(d); Mc[3, :3] = np.asarray(wpos, float) - base
        for n_ in nodes:
            if n_['name'] == name: n_.update(parent=parent, M=Mc, kind=0, geo={}); return
        add(name, 0, parent, Mc)
    def surf(p, o, d):
        i_, t_ = B.ray_faces(p, o, d, 0.0, 8.0); return None if not len(t_) else np.asarray(o, float) + np.asarray(d, float) * float(t_.min())
    TP = tur_keep(1.0); MP = part(N, mask, targets); CP = B.Part(N['Cupola_1.1']['P'], N['Cupola_1.1']['T'], N['Cupola_1.1']['N'])
    g = surf(H1, (0.0, 0.42, 6.0), (0, 0, -1.0)); setcam('s_camera_driver_01', 'd_hull', g - [0, 0, 0.04], (0, 0, 1.0))                       # driver's visor
    setcam('s_camera_driver_02', 'd_hull', (0.24, 0.66, 2.05), (0, 0, 1.0)); setcam('s_camera_driver_03', 'd_hull', (-0.24, 0.66, 2.05), (0, 0, 1.0))   # his two roof periscopes
    tg = surf(MP, (-0.23, 1.084, 6.0), (0, 0, -1.0)); setcam('s_camera_gunner_02', 'd_gunmask', (tg if tg is not None else (-0.23, 1.084, 2.38)) - [0, 0, 0.03], (0, 0, 1.0))   # telescope
    setcam('s_camera_gunner_03', 'd_head', (-0.45, 1.50, 1.36), (0, 0, 1.0))                                                                 # PT4 periscope (TurretPeriscope_2)
    setcam('s_camera_loader_02', 'd_head', (0.46, 1.47, 1.18), (0, 0, 1.0))                                                                  # MK-4 (TurretPeriscope_1)
    for nm, s in (('s_camera_gunner_01', -1.0), ('s_camera_loader_01', 1.0)):                                                                # turret side ports
        p_ = surf(TP, (s * 3.0, 1.18, RING[2]), (-s, 0, 0)); setcam(nm, 'd_head', p_ - [s * 0.04, 0, 0], (s, 0, 0))
    setcam('s_camera_mk4_01', 'd_head', (-0.46, 1.74, 0.30), (0, 0, 1.0))                                                                    # cupola MK-4
    cc = np.array([-0.46, 1.62, 0.14])
    for k, ang in enumerate(range(0, 360, 60)):                                                                                              # the cupola's six slits
        dvec = np.array([np.sin(np.radians(ang)), 0, np.cos(np.radians(ang))]); p_ = surf(CP, cc + dvec * 1.5, -dvec)
        setcam('s_camera_mk4_%02d' % (k + 2), 'd_head', (p_ if p_ is not None else cc + dvec * 0.42) - dvec * 0.04, dvec)
    print('vision ports: visor', np.round(g, 3), 'telescope', None if tg is None else np.round(tg, 3))
    print('nodes', len(nodes), 'ring', np.round(RING, 3).tolist(), 'kv head', np.round(world['d_head'], 3).tolist(), 'trunnion', np.round(TRUN, 3).tolist(), 'muzzle', np.round(MUZ, 3).tolist())
    return nodes, crop, bar_uv

def gun_sheets(lp_tex, tex, crop, bar_uv, d):
    """the barrel's part of the low-poly sheets, with its colour brought to the detailed model's turret paint"""
    im = Image.open(os.path.join(lp_tex, 'IS_2_Enchanded_Diffuse.png')).convert('RGB'); W, H = im.size; mask = Image.new('L', (W, H), 0); dr = ImageDraw.Draw(mask)
    for tri in bar_uv: dr.polygon([(float(u) * W, float(v) * H) for u, v in tri], fill=255)
    a = np.asarray(im, np.float32); m = np.asarray(mask) > 0
    box = (int(crop[0] * W), int(crop[1] * H), int(np.ceil(crop[2] * W)), int(np.ceil(crop[3] * H)))
    paint = B.clean_paint(np.asarray(Image.open(os.path.join(tex, 'Turret_Base_color.png')).convert('RGB').resize((512, 512), Image.LANCZOS), np.float32))
    occ = np.asarray(Image.open(os.path.join(tex, 'Turret_Mixed_AO.png')).convert('RGB').resize((512, 512), Image.LANCZOS), np.float32)[..., 0] / 255.0; paint = paint * (0.35 + 0.65 * occ)[..., None]   # as the turret's layer is built
    s = np.median(paint.reshape(-1, 3), axis=0) / np.maximum(np.median(a[m], axis=0), 1.0); print('  gun colour scaled by', np.round(s, 2), 'sheet', (W, H), 'crop', box)
    out = {}
    Image.fromarray(np.clip(a * s, 0, 255).astype(np.uint8)).crop(box).save(os.path.join(d, 'gun_d.png')); out['d'] = os.path.join(d, 'gun_d.png')
    for k, n in (('n', 'IS_2_Normal.png'), ('r', 'IS_2_Rougnes.png')):
        p = os.path.join(d, 'gun_%s.png' % k); Image.open(os.path.join(lp_tex, n)).convert('RGB').crop(box).save(p); out[k] = p
    return out

SRC_UV = []

def fill_gaps(img, uvs, rects, n_px):
    """10 Nov (user: dark wedges): the sheets are dark between their UV islands, and reduced faces whose corners are pinned to an
    island's edge sample that dark gap.  Every pixel outside the source islands takes the colour of the nearest island pixel."""
    from scipy.ndimage import distance_transform_edt, binary_dilation
    m = Image.new('L', (n_px, n_px), 0); dr = ImageDraw.Draw(m)
    for T in uvs:
        for tri in (T * n_px):
            dr.polygon([tuple(x) for x in tri], fill=255)
    for u0, v0, w, h in rects: dr.rectangle([u0 * n_px, v0 * n_px, (u0 + w) * n_px, (v0 + h) * n_px], fill=255)
    cov = binary_dilation(np.asarray(m) > 0, iterations=1)
    _, (iy, ix) = distance_transform_edt(~cov, return_indices=True)
    print('  texture gap fill: %.1f %% of the sheet refilled' % (100.0 * (~cov).mean()))
    return img[iy, ix]

def textures(tex, lp_tex, crop, bar_uv, out, ref=None):
    L = []
    for k in ('Chassis', 'Turret', 'Fittings', 'SuspensionLeft', 'SuspensionRight'):
        f = lambda s: os.path.join(tex, '%s_%s.png' % (k, s)); ao = f('Mixed_AO')
        L.append((ATLAS[k], f('Base_color'), f('Normal_OpenGL'), (ao, 0) if os.path.exists(ao) else None, (f('Roughness'), 0)))
    with tempfile.TemporaryDirectory() as d:
        g = gun_sheets(lp_tex, tex, crop, bar_uv, d); L.append((GUN_RECT, g['d'], g['n'], None, (g['r'], 0)))
        dif, nrm = B.build_textures(L, None, None, ref, clean=True)
    dif = fill_gaps(dif, SRC_UV, [GUN_RECT], dif.shape[0]); nrm = fill_gaps(nrm, SRC_UV, [GUN_RECT], nrm.shape[0])
    B.write_textures(dif, nrm, out, 'is2')

if __name__ == '__main__':
    kv, glb, tex, lp_obj, lp_tex, out = sys.argv[1:7]; ref = sys.argv[7] if len(sys.argv) > 7 else None
    nodes, crop, bar_uv = build(kv, glb, lp_obj)
    # the kv1s_late template has two material records: an untextured 'kv1s_dift' and the one that draws, kv1s_late_dift / kv1s_late_norsp
    for L in (1, 2, 3):
        cnt = sorted(((len(n['geo'][L][0]), n['name']) for n in nodes if L in n['geo'] and n['geo'][L][0] is not None), reverse=True)
        print('LOD%d vertices %d, largest %s' % (L, sum(c for c, _ in cnt), cnt[:4]))
    print('faces turned back outward:', getattr(SM.new_gxt, 'flipped', 0))
    data = B.rename_material(SM.assemble(nodes, kv), (b'kv1s_dift', b'kv1s_late_dift', b'kv1s_late_norsp'), (MATERIAL[0],) + MATERIAL)
    p = os.path.join(out, 'is2.mesh.loc_def.bin'); open(p, 'wb').write(data)
    m = azg2.read(p); print('written', p, len(data), 'bytes;', len(m['nodes']), 'nodes;', [(b['tag'], b['nv'], b['ni']) for b in m['blocks']], [mt['name'] for mt in m['materials']])
    textures(tex, lp_tex, crop, bar_uv, out, ref); print('textures written')

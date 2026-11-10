"""IS-2 wreck ('ostov'): the same two models as is2_bought.py as one static burnt piece, built the way the game's own wrecks are (kv1s_ostov01): a single d_hull
with the running gear in it, two collision boxes, a centre of mass, its turret off centre and a hatch open, and a dark 1024 texture.
Hull, turret and mantlet come from the detailed model.  Gun, wheels and tracks come from the low-poly one: the detailed wheels (35 000 triangles each) break up at wreck
budgets, the low-poly ones are clean as they are.

  python is2_wreck.py <kv1s_late mesh> <kv1s_ostov01 mesh> <reg_kv1s_ostov_dift> <IS-2.glb> <textures dir> <Kado_3D_IS_2.obj> <low-poly textures dir> <out dir>

Writes is2_ostov01.mesh, reg_is2_ostov_dift and bump_is2_ostov_norsp.  Like the tank's own files they are made from models licensed to the user: never committed.
"""
import sys, os, re, tempfile, numpy as np
from scipy.ndimage import gaussian_filter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import azg2, atf1, bought as B, su122_mesh as SM, m3lee_mesh as OLD, is2_bought as I

TURRET_YAW = 24.0      # degrees off the centre line, as the game's KV-1S wreck stands
GUN_DROP = 2.5         # degrees below level: the elevating gear gone
LID_OPEN = 118.0       # the loader's hatch thrown open
TOTAL = 19000          # triangles at LOD 1; the game's KV-1S wreck has 7 400
DARK_UV = np.array((0.93, 0.45))   # the atlas's unused dark corner
WHEEL_RECT, TRACK_RECT = (0.296, 0.625, 0.329, 0.25), (0.296, 0.875, 0.329, 0.125)   # the low-poly model's wheel and track sheets

def yrot(a): c, s = np.cos(np.radians(a)), np.sin(np.radians(a)); return np.array([[c, 0, -s], [0, 1, 0], [s, 0, c]])
def xrot(a): c, s = np.cos(np.radians(a)), np.sin(np.radians(a)); return np.array([[1, 0, 0], [0, c, s], [0, -s, c]])

def spin(v, Rm, pivot):
    """row-vector rotation of a load() entry or a Part about a pivot"""
    if isinstance(v, dict): v['P'] = (v['P'] - pivot) @ Rm.T + pivot; v['N'] = v['N'] @ Rm.T
    else: v.P = (v.P - pivot) @ Rm.T + pivot; v.N = v.N @ Rm.T

def load_lp_gear(path):
    """{group name: Part} of the low-poly model's wheels and tracks: metres, game axes, uvs in their atlas rectangles"""
    V, VT, VN, G = [], [], [], {}; cur = None
    for l in open(path, errors='replace'):
        t = l.split()
        if not t: continue
        if t[0] == 'v': V.append([float(a) for a in t[1:4]])
        elif t[0] == 'vt': VT.append([float(a) for a in t[1:3]])
        elif t[0] == 'vn': VN.append([float(a) for a in t[1:4]])
        elif t[0] == 'g': cur = next((a for a in t[1:] if re.fullmatch(r'(Wheel_[LR]_\d+|Track_[LR])', a)), None)
        elif t[0] == 'f' and cur:
            q = [tuple(int(x) - 1 if x else 0 for x in a.split('/')) for a in t[1:]]
            for k in range(1, len(q) - 1): G.setdefault(cur, []).append((q[0], q[k], q[k + 1]))
    V = np.array(V) * 0.01 * [-1.0, 1.0, 1.0]; VT = np.array(VT); VN = np.array(VN) * [-1.0, 1.0, 1.0]; VN /= np.maximum(np.linalg.norm(VN, axis=1, keepdims=True), 1e-9); out = {}
    for name, tris in G.items():
        f = np.array(tris)[:, [0, 2, 1]]; uv = VT[f[:, :, 1]].copy(); uv -= np.floor(uv.mean(1, keepdims=True)); uv = np.clip(uv, 0, 1); uv[..., 1] = 1.0 - uv[..., 1]; u0, v0, w, h = TRACK_RECT if name.startswith('Track') else WHEEL_RECT
        out[name] = B.Part(V[f[:, :, 0]], np.stack([u0 + uv[..., 0] * w, v0 + uv[..., 1] * h], -1), VN[f[:, :, 2]])
    return out

def fit_gear(gear):
    """the two sides on the game's track line and the detailed model's axles: side by side, height and length from the road wheels and tracks"""
    out = []
    for s, sg in (('L', -1.0), ('R', 1.0)):
        tr_ = gear['Track_' + s]; wh = [gear[k] for k in gear if k.startswith('Wheel_' + s)]; lo, hi = tr_.lo(), tr_.hi()
        d = np.array([sg * I.TRACK - (lo[0] + hi[0]) / 2, I.ROAD_Y - 0.30 - 0.06 - lo[1], 0.0])
        rx = I.L_X if s == 'L' else I.R_X; z_game = np.mean(-np.array(rx) + I.Z_OFF)
        zw = sorted((w.centre()[2] for w in wh)); d[2] = z_game - (zw[len(zw) // 2 - 1] + zw[len(zw) // 2]) / 2
        print('  side', s, 'shift', np.round(d, 3).tolist(), 'wheels', len(wh), 'track z', np.round([lo[2] + d[2], hi[2] + d[2]], 2).tolist(), 'bottom y', round(lo[1] + d[1], 3))
        for p in [tr_] + wh: out.append(B.Part(p.P + d, p.T, p.N))
    return B.join(out)

def build(kv, ostov, glb, lp_obj):
    K = SM.Src(kv); arm = OLD.arm_points(K); T = SM.Src(ostov)
    N, TRUN, MUZ, RING = I.load(glb)
    N.pop('122mm_D25_T'); N.pop('MuzzleBrake')
    collar = float(N['Mantlet_1.2']['P'].reshape(-1, 3)[:, 2].max())
    Gun, crop, bar_uv = I.fit_gun(I.load_lp_barrel(lp_obj), TRUN, collar)
    names = list(N); c = np.array([len(N[k]['P']) for k in names], float); ww = np.array([I.weight(k, N[k]['mat']) for k in names]); lo, hi = 1e-4, 1e4
    for _ in range(60):
        s = (lo * hi) ** 0.5; t = np.minimum(c, np.maximum(8, s * ww * c ** 0.62))
        if t.sum() > TOTAL: hi = s
        else: lo = s
    targets = dict(zip(names, t.astype(int))); print('parts', len(names), 'source tris', int(c.sum()), 'target', int(t.sum()))
    # the loader's hatch, thrown forward over its front hinge, a dark floor under it
    lid = [k for k in ('LoaderHatch_1.1', 'LoaderHatch_1.2', 'LoaderHatch_1.3') if k in N]
    Pl = np.vstack([N[k]['P'].reshape(-1, 3) for k in lid]); a, b = Pl.min(0), Pl.max(0); hinge = np.array([(a[0] + b[0]) / 2, b[1], b[2]]); mid = (a + b) / 2
    sign = 1.0 if ((mid - hinge) @ xrot(LID_OPEN).T)[1] > 0 else -1.0
    for k in lid: spin(N[k], xrot(sign * LID_OPEN), hinge)
    floor = B.quad(mid * [1, 0, 1] + [0, a[1] + 0.012, 0], np.array([(b[0] - a[0]) * 0.46, 0, 0]), np.array([0, 0, (b[2] - a[2]) * 0.46]), (0, 1, 0), DARK_UV)
    gear = fit_gear(load_lp_gear(lp_obj))
    # the gun down, then everything on the ring round
    mask = [k for k in names if I.under(N, k, ('Mantlet_1.1',))]; turret = [k for k in names if I.under(N, k, ('Ring_1',))]
    for k in mask: spin(N[k], xrot(GUN_DROP), TRUN)
    spin(Gun, xrot(GUN_DROP), TRUN)
    Ry = yrot(TURRET_YAW)
    for k in turret: spin(N[k], Ry, RING)
    spin(Gun, Ry, RING); spin(floor, Ry, RING)
    Lid = I.part(N, lid, targets); Lid = B.Part(Lid.P[:, [0, 2, 1]], Lid.T[:, [0, 2, 1]], -Lid.N[:, [0, 2, 1]])    # its underside, which the model never shows
    big = [k for k in names if N[k]['mat'] == 'Chassis' or k.startswith(('TurretBody', 'TurretGunHousing', 'TurretTopPlate', 'Mantlet', 'Cupola_1', 'Ring_5', 'SideSkirt'))]
    def lod(f, keep=None): return B.join([I.part(N, keep or names, targets, f), Gun, floor, gear, Lid]).gxt()
    shell = [k for k in names if N[k]['mat'] == 'Chassis'] + [k for k in turret if k.startswith(('TurretBody', 'TurretGunHousing', 'TurretTopPlate', 'Mantlet'))]
    H = B.join([I.part(N, shell, targets, 0.25), Gun, gear])
    print('LOD1 tris', len(I.part(N, names, targets, 1.0)), 'hit tris', len(H))
    hull = [k for k in names if k not in turret and not N[k]['mat'].startswith('Suspension')]
    Ph = np.vstack([N[k]['P'].reshape(-1, 3) for k in hull]); Pt = np.vstack([N[k]['P'].reshape(-1, 3) for k in turret if k.startswith(('TurretBody', 'TurretGunHousing'))])
    def box(name, P):
        """the wreck's own collision box on the game's, sized to these points; its local origin is at the middle of the box's floor"""
        A, F = T.geo[(name, 0)]; A = A.copy(); lo, hi = P.min(0), P.max(0); q = A[:, :3]; s0 = (q.max(0) - q.min(0)) / 2; s1 = (hi - lo) / 2
        A[:, :3] = q * (s1 / s0); M = np.eye(4); M[3, :3] = ((lo + hi) / 2) * [1, 0, 1] + [0, lo[1], 0]
        print(' ', name, 'centre', np.round((lo + hi) / 2, 2).tolist(), 'half', np.round(s1, 2).tolist())
        return dict(name=name, kind=T.node(name)['kind'], parent='d_hull', M=M, geo={0: (A, F)})
    nodes = [dict(name='d_hull', kind=4, parent=None, M=np.eye(4), geo={0: OLD.hit(*H.plain(), arm, None), 1: lod(1.0), 2: lod(0.45), 3: lod(0.25, big)}),
             box('d_coll_01', Ph), dict(name='s_cmass', kind=0, parent='d_hull', M=T.local('s_cmass').copy(), geo={}), box('d_coll_02', Pt)]
    data = B.rename_material(SM.assemble(nodes, ostov), (b'kv1s_ostov_dift', b'kv1s_ostov_norsp'), (b'is2_ostov_dift', b'is2_ostov_norsp'))
    return data, crop, bar_uv

def burn(dif, ref):
    """the model's paint as the game's burnt wrecks have it: colour mostly gone, soot and a little rust in blotches, then the brightness of reg_kv1s_ostov_dift"""
    g = np.random.default_rng(1943); n = dif.shape[0]
    def noise(sig):
        f = gaussian_filter(g.standard_normal((n, n)).astype(np.float32), sig, mode='wrap'); return (f - f.mean()) / f.std()
    d = dif.astype(np.float32); used = d.mean(2) > 25.0
    grey = d.mean(2, keepdims=True); d = d * 0.42 + grey * np.array((1.0, 0.97, 0.72), np.float32) * 0.58
    soot = np.clip((noise(45) * 0.7 + noise(11) * 0.45 + noise(3) * 0.2 + 0.1) * 0.75, 0, 1)[..., None]; d *= 1.0 - 0.72 * soot
    rust = np.clip((noise(22) * 0.6 + noise(5) * 0.5 - 0.75) * 1.3, 0, 1)[..., None] * (1.0 - soot); d = d * (1.0 - 0.55 * rust) + np.array((88.0, 56.0, 32.0), np.float32) * 0.55 * rust
    d *= (0.9 + 0.1 * noise(2))[..., None]
    r = np.asarray(atf1.top(ref))[..., :3].astype(np.float32); s = np.percentile(r.reshape(-1, 3), 50, axis=0) / np.maximum(np.percentile(d[used], 50, axis=0), 1.0)
    print('  burnt: scaled by', np.round(s, 2), 'to the KV-1S wreck'); d[used] *= s
    return np.clip(d, 0, 255).astype(np.uint8)

def textures(tex, lp_tex, crop, bar_uv, ref, out):
    L = []
    for k in ('Chassis', 'Turret', 'Fittings', 'SuspensionLeft', 'SuspensionRight'):
        f = lambda s: os.path.join(tex, '%s_%s.png' % (k, s)); ao = f('Mixed_AO')
        L.append((I.ATLAS[k], f('Base_color'), f('Normal_OpenGL'), (ao, 0) if os.path.exists(ao) else None, (f('Roughness'), 0)))
    with tempfile.TemporaryDirectory() as d:
        g = I.gun_sheets(lp_tex, tex, crop, bar_uv, d); L.append((I.GUN_RECT, g['d'], g['n'], None, (g['r'], 0)))
        for rect, a, b in ((WHEEL_RECT, 'Wheels', 'Enchanced'), (TRACK_RECT, 'Tracks', 'Enchanded')):
            f = lambda n: os.path.join(lp_tex, 'IS_2_%s_%s.png' % (a, n)); L.append((rect, f(b + '_Diffuse'), f('Normal'), None, (f('Rougnes'), 0)))
        dif, nrm = B.build_textures(L, None, None, None, N=1024, clean=True)
    nrm[..., 3] = (nrm[..., 3] * 0.35).astype(np.uint8)    # burnt steel hardly shines
    B.write_textures(burn(dif, ref), nrm, out, 'is2_ostov')

if __name__ == '__main__':
    kv, ostov, ref, glb, tex, lp_obj, lp_tex, out = sys.argv[1:9]
    data, crop, bar_uv = build(kv, ostov, glb, lp_obj)
    p = os.path.join(out, 'is2_ostov01.mesh.loc_def.bin'); open(p, 'wb').write(data)
    m = azg2.read(p); print('written', p, len(data), 'bytes;', [n['name'] for n in m['nodes']], [(b['tag'], b['nv'], b['ni']) for b in m['blocks']], [mt['name'] for mt in m['materials']])
    textures(tex, lp_tex, crop, bar_uv, ref, out); print('textures written')

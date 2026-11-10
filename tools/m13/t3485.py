r"""T-34-85 (11 Nov, user): the game's own T-34 mod. 1942 (t34_42_utz) - hull, running gear, fittings, crew stations, damage
boxes - with only the turret, mantlet and gun taken from the user's purchased T-34-85 model (Downloads\T-34-85\Turret.stl, a
3D-print kit: one fused solid, about 1:29, peg under the turret, +x on the vehicle's left).

The 76 mm turret's nodes are dropped; the STL turret is cut into turret / mantlet / barrel, reduced to the game's budgets with
quadric simplification, mirrored into the game's hand and set on the T-34's turret ring.  Texture: a 2048 sheet whose top-left
quarter is the game's T-34 sheet (the kept geometry's uv halved, so it looks exactly as before) and the other three quarters
paint for the new parts, quilted from the old turret's painted areas of that sheet (sides with grime towards the bottom, roof,
gun).  Source files and outputs never go in the repo.

  python t3485.py <t34_42_utz mesh> <Turret.stl> <reg_t34_42_utz_dift> <bump_t34_42_utz_norsp> <out dir>
"""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import bought as B, azg2, su122_mesh as SM, m3lee_mesh as OLD

S = 0.034                                   # STL units -> m: muzzle 2.05 m ahead of the hull front, as on the real tank
PEG = np.array([-4.12, 129.2])              # turret ring centre (the print peg) in STL x, y
BASE_Z = 159.3                              # underside of the turret casting (the peg is below)
RING = np.array([0.0, 0.412, 0.534])        # the game T-34's d_head origin: the ring
TURRET_NODES = ('d_head', 'd_gunmask', 'd_gun', 'd_hatch_02', 'd_hatch_03', 'd_headparts_early', 'd_headparts_late',
                'd_headporuchni', 'd_minigun', 'd_sight_01')
MATERIAL = (b't34_42_utz_dift', b't3485__utz_dift')   # same length, the same 'tz_dift' tail: the second material (tz_dift) is stored as that tail
BUDGET = {'tur': (7000, 2800, 1100), 'mask': (900, 400, 160), 'bar': (360, 160, 70)}


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
    v, f = fs.simplify(V.astype(np.float32), F.astype(np.int32), target_reduction=1.0 - target / len(F))
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


def turret_parts(stl):
    V, F = load_stl(stl)
    c = V[F].mean(1)
    keep = c[:, 2] > BASE_Z - 0.2                                                     # the print peg goes
    keep &= ~((np.abs(c[:, 0] - 14.05) < 1.2) & (np.abs(c[:, 1] - 128.85) < 1.2) & (c[:, 2] > 186.0))   # the aerial (thin mast)
    F = F[keep]; c = c[keep]
    far = V[V[:, 1] < 40]; bore = far[:, [0, 2]].mean(0)                               # bore axis from the barrel's front half
    r = np.hypot(c[:, 0] - bore[0], c[:, 2] - bore[1])
    bar = (c[:, 1] < 86.0) & (r < 6.0)                                                 # barrel with its collar
    mask = ~bar & (c[:, 1] < 97.0) & (np.abs(c[:, 0] - bore[0]) < 17.5) & (c[:, 2] > 160.5) & (c[:, 2] < 178.0)   # the cast mantlet
    tur = ~bar & ~mask
    G = to_game(V)
    bore_g = to_game(np.array([[bore[0], 0.0, bore[1]]]))[0]
    trun = np.array([bore_g[0], bore_g[1], to_game(np.array([[0, 103.0, 0]]))[0][2]])   # trunnion inside the turret front
    muz = to_game(np.array([[bore[0], V[:, 1].min(), bore[1]]]))[0]
    out = {}
    for key, sel, uvf in (('tur', tur, uv_turret), ('mask', mask, uv_gun), ('bar', bar, uv_gun)):
        f = F[sel]; used = np.unique(f); remap = np.full(len(V), -1); remap[used] = np.arange(len(used)); vv, ff = G[used], remap[f]
        lods = []
        for t in BUDGET[key]:
            v_, f_ = reduce(vv, ff, t); lods.append(part(v_, f_, uvf))
        hv, hf = reduce(vv, ff, {'tur': 700, 'mask': 160, 'bar': 60}[key]); lods.insert(0, part(hv, hf, uvf))
        out[key] = lods; print(key, 'source tris', len(f), '-> lods', [len(p) for p in lods])
    return out, trun, muz, bore_g


def build(t34, stl):
    K = SM.Src(t34); arm = OLD.arm_points(K)
    parts, TRUN, MUZ, BORE = turret_parts(stl)
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
    tl = parts['tur']; ml = parts['mask']; bl = parts['bar']
    TV = tl[1].P.reshape(-1, 3)
    def roof(x, z, r=0.12):
        q = TV[np.hypot(TV[:, 0] - x, TV[:, 2] - z) < r]; return float(q[:, 1].max()) if len(q) else 1.45
    def wall(y, z, r=0.10):
        q = TV[(np.abs(TV[:, 1] - y) < r) & (np.abs(TV[:, 2] - z) < r)]; return float(np.abs(q[:, 0]).max()) if len(q) else 0.95
    add('d_head', 4, 'd_hull', tr(RING), {0: OLD.hit(*tl[0].moved(RING).plain(), arm, 'side'), **g(tl, RING)})
    add('d_gunmask', 4, 'd_head', tr(TRUN - RING), {0: OLD.hit(*ml[0].moved(TRUN).plain(), arm, 'front'), **g(ml, TRUN)})
    add('d_gun', 4, 'd_gunmask', np.eye(4), {0: OLD.hit(*bl[0].moved(TRUN).plain(), arm, 'front'), **g(bl, TRUN)})
    add('s_gun', 0, 'd_gun', tr(MUZ + [0, 0, 0.05] - TRUN))
    coax = np.array([BORE[0] + 0.24, BORE[1] + 0.02, TRUN[2] + 0.30])               # the co-axial DT right of the gun
    add('d_minigun', 1, 'd_gunmask', tr(coax - TRUN)); add('s_mgun', 0, 'd_minigun', tr((0, 0, 0.05)))
    # the old turret's sockets: crew, cameras, damage boxes, exits - same place relative to the ring (the new turret is larger);
    # gun-side ones follow the trunnion
    for n in K.nodes[1:]:
        nm = n['name']
        if not under_head(n) or nm.startswith('d_') or nm in ('s_gun', 's_mgun'): continue
        wp = n['world'][3, :3].copy()
        par = 'd_gunmask' if nm in ('s_camera_tmfd7', 'p_rotgun') else 'd_head'
        if nm == 's_camera_tmfd7': wp = np.array([BORE[0] - 0.30, BORE[1] + 0.06, TRUN[2] + 0.30])   # the TSh telescope, left of the gun
        if nm == 's_camera_pt4_7': wp = np.array([wp[0], roof(wp[0], wp[2]) + 0.05, wp[2]])          # the PT4-7 on the new, higher roof
        if nm in ('s_camera_gunner', 's_camera_loader'): wp = np.array([np.sign(wp[0]) * (wall(wp[1], wp[2]) + 0.03), wp[1], wp[2]])   # side ports on the new walls
        M = np.eye(4); M[:3, :3] = n['world'][:3, :3]; M[3, :3] = wp - (TRUN if par == 'd_gunmask' else RING)
        A0 = K.geo.get((nm, 0)); add(nm, n['kind'], par, M, {0: A0} if A0 is not None and nm.startswith('p_') else {})
    # the commander (the T-34-85's fifth man) under the cupola on the turret's left rear: seat, damage box, exit, the MK-4 on the
    # cupola roof and five vision slits round it
    CUP = np.array([-(6.45 - PEG[0]) * S, 0.0, -(138.5 - PEG[1]) * S + RING[2]]); ctop = roof(CUP[0], CUP[2]); rc = 0.30
    def look(d):
        z = np.asarray(d, float); z /= np.linalg.norm(z); x = np.cross([0, 1.0, 0], z); x /= np.linalg.norm(x); return np.array([x, np.cross(z, x), z])
    def sock(name, wp, d=(0, 0, 1.0), geo=None):
        M = np.eye(4); M[:3, :3] = look(d); M[3, :3] = np.asarray(wp, float) - RING; add(name, 0 if geo is None else 1, 'd_head', M, geo or {})
    sock('s_commander', (CUP[0], 0.70, CUP[2]))
    pg = K.geo.get(('p_gunner', 0)); sock('p_commander', (CUP[0], 0.70, CUP[2]), geo={0: pg} if pg is not None else None)
    sock('s_commander_exit', (CUP[0] - 2.0, 1.35, CUP[2]))
    sock('s_camera_mk4_01', (CUP[0], ctop + 0.04, CUP[2] + 0.12))
    for k, ang in enumerate((0, 60, 120, 240, 300)):
        dv = np.array([np.sin(np.radians(ang)), 0, np.cos(np.radians(ang))]); sock('s_camera_mk4_%02d' % (k + 2), CUP + dv * (rc + 0.03) + [0, ctop - 0.10, 0], dv)
    print('nodes', len(nodes), 'cupola', np.round(CUP, 3), 'roof', round(ctop, 3), 'trunnion', np.round(TRUN, 3), 'muzzle', np.round(MUZ, 3), 'bore', np.round(BORE, 3))
    return nodes


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
    side = quilt(Hq); rows = (np.arange(Hq) / Hq * 4.0)[:, None, None]                      # metres below 1.8 m (v * 4 m)
    grime = np.clip((rows - 0.9) / 0.9, 0, 1) * 0.35                                       # the turret's lower edge dirtier
    side = side * (1 - grime) + np.array([62, 55, 40], np.float32) * grime
    dif[:Hq, Hq:] = side; dif[Hq:, :Hq] = quilt(Hq) * 1.04; dif[Hq:, Hq:] = quilt(Hq) * 0.92
    # normal / gloss for the paint: flat, with the old sheet's median gloss
    flat = np.array([128, 128, np.median(vn[..., 2]), np.median(vn[..., 3])], np.float32)
    nrm[:Hq, Hq:] = flat; nrm[Hq:, :] = flat
    dif = np.clip(dif, 0, 255).astype(np.uint8); nrm = np.clip(nrm, 0, 255).astype(np.uint8)
    B.write_textures(dif, nrm, out, MATERIAL[1].decode()[:-5])
    Image.fromarray(dif).resize((1024, 1024)).save(os.path.join(out, 't3485_dift_preview.png'))


if __name__ == '__main__':
    t34, stl, dift, norsp, out = sys.argv[1:6]
    os.makedirs(out, exist_ok=True)
    nodes = build(t34, stl)
    data = B.rename_material(SM.assemble(nodes, t34), (MATERIAL[0],), (MATERIAL[1],))
    p = os.path.join(out, 't3485.mesh.loc_def.bin'); open(p, 'wb').write(data)
    m = azg2.read(p); print('written', p, len(data), 'bytes;', len(m['nodes']), 'nodes;', [(b['tag'], b['nv'], b['ni']) for b in m['blocks']], [x['name'] for x in m['materials']])
    textures(dift, norsp, out); print('textures written')

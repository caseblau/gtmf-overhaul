r"""T-34-85 from the user's purchased textured model (Downloads\T-34-85+Medium+tank.rar: T-34-85.obj with PBR textures; 11 Nov,
user: use this one, turret only).  As t3485.py, the game's T-34 mod. 1942 keeps hull, running gear, fittings and crew stations;
only the turret, mantlet, gun, periscopes and lids come from the model.  The model is game-ready (low poly, own textures and
normal maps, separate hatch objects with real openings under them), so nothing is reduced or cut out of a fused solid:
  turret body, ventilators, fittings      -> d_head
  mantlet and gun sleeve                  -> d_gunmask, the barrel -> d_gun (recoils)
  gunner's / loader's MK-4 periscopes     -> d_sight_01 / d_sight_02 (turn), the cupola's -> d_sight_03 on the cupola's fixed front part
  loader's hatch (front hinge)            -> d_hatch_03; the cupola lid behind the fixed MK-4 part (front hinge) -> d_hatch_04
Model frame: metres at about 84 % of real size (hull 2.53 m wide), y up, front -z, +x the vehicle's right; scale 1.19.
Texture: a 2048 sheet - top left the game's T-34 sheet (kept geometry uv halved), top right the model's main sheet, bottom left
its hatch sheet, bottom right dark and glass texels.  OpenGL normal maps get their green flipped.

  python t3485_lp.py <t34_42_utz mesh> <model dir> <reg_t34_42_utz_dift> <bump_t34_42_utz_norsp> <out dir> [rtank_ostov01] [arm_t34_42_utz_dift]
"""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import bought as B, azg2, su122_mesh as SM, m3lee_mesh as OLD, t3485 as A
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

S = 1.19                                    # model -> real size (hull 2.53 m wide; the real T-34-85 is 3.0 m)
RC = np.array([-0.014, 1.387, -0.419])      # the model's turret ring centre (bottom circle) at its hull roof height
RING = np.array([0.0, 0.412, 0.534])        # the game T-34's ring
ROOF_G = 0.55                               # the game hull's roof at the ring, where the model's hull roof goes
MATERIAL = A.MATERIAL
UV_MAIN, UV_HATCH = (0.5, 0.0), (0.0, 0.5)   # quarter offsets
DARK_UV, GLASS_UV = np.array((0.70, 0.70)), np.array((0.80, 0.70))
A.RING = RING                               # the wreck builder turns the turret about it


def to_game(P):
    return np.stack([(P[..., 0] - RC[0]) * S, (P[..., 1] - RC[1]) * S + ROOF_G, -(P[..., 2] - RC[2]) * S + RING[2]], -1)


def read_obj(path):
    V, VT, VN, out = [], [], [], {}; obj = cur = None
    for l in open(path, errors='replace'):
        t = l.split()
        if not t: continue
        if t[0] == 'v': V.append([float(a) for a in t[1:4]])
        elif t[0] == 'vt': VT.append([float(a) for a in t[1:3]])
        elif t[0] == 'vn': VN.append([float(a) for a in t[1:4]])
        elif t[0] == 'o': obj = t[1]
        elif t[0] == 'usemtl': cur = t[1]
        elif t[0] == 'f':
            q = [tuple(int(x) - 1 for x in a.split('/')) for a in t[1:]]
            for k in range(1, len(q) - 1): out.setdefault(obj, []).append((q[0], q[k], q[k + 1], cur))
    V, VT, VN = np.array(V), np.array(VT), np.array(VN); res = {}
    for o, tris in out.items():
        idx = np.array([[c[0] for c in t[:3]] for t in tris]); tdx = np.array([[c[1] for c in t[:3]] for t in tris]); ndx = np.array([[c[2] for c in t[:3]] for t in tris])
        res[o] = dict(P=V[idx], T=VT[tdx], N=VN[ndx], M=np.array([t[3] for t in tris]))
    return res


def comps(P):
    _, inv = np.unique(np.round(P.reshape(-1, 3), 4), axis=0, return_inverse=True); W = inv.reshape(-1, 3); n = W.max() + 1
    e = np.r_[W[:, [0, 1]], W[:, [1, 2]]]; _, lab = connected_components(coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(n, n)), directed=False)
    return lab[W[:, 0]]


def part(o, sel):
    """triangles of an object -> game Part: mirrored (windings turned), uv into the sheet's quarters by material"""
    P = to_game(o['P'][sel])[:, ::-1]; N = (o['N'][sel] * [1.0, 1.0, -1.0])[:, ::-1]; M = o['M'][sel]
    T = o['T'][sel][:, ::-1].copy(); T[..., 1] = 1.0 - T[..., 1]; T = np.clip(T, 0.0, 1.0)
    out = T * 0.5
    out[M == 'Texture'] += UV_MAIN; out[M == 'Hatches'] += UV_HATCH
    out[M == 'Black'] = DARK_UV; out[M == 'Optics'] = GLASS_UV
    return B.Part(P, out, N)


def split(objs):
    tur = objs['Turret_Cube.004']; lab = comps(tur['P']); c = tur['P'].mean(1); n = lab.max() + 1
    lo = np.array([tur['P'][lab == k].reshape(-1, 3).min(0) for k in range(n)]); hi = np.array([tur['P'][lab == k].reshape(-1, 3).max(0) for k in range(n)])
    cen = (lo + hi) / 2
    role = np.full(n, 'tur', object)
    role[hi[:, 1] > 2.5] = 'drop'                                               # the aerial (the game T-34 has its own on the hull)
    role[lo[:, 2] < -2.0] = 'bar'                                               # the barrel
    role[(role == 'tur') & (hi[:, 2] < -1.05)] = 'mask'                         # mantlet and gun sleeve
    for nm, (px, pz) in (('d_sight_01', (-0.51, -0.49)), ('d_sight_02', (0.42, -0.66))):
        role[(np.hypot(cen[:, 0] - px, cen[:, 2] - pz) < 0.12) & (lo[:, 1] > 1.96)] = nm
    parts = {r: part(tur, role[lab] == r) for r in set(role) - {'drop'}}
    print('turret pieces:', {r: int((role == r).sum()) for r in set(role)})
    lf = objs['Commander_Hatch_2_Cube.001']; lb = comps(lf['P']); n2 = lb.max() + 1
    cen2 = np.array([lf['P'][lb == k].reshape(-1, 3).mean(0) for k in range(n2)]); tri2 = np.bincount(lb)
    peri = [k for k in range(n2) if -0.42 < cen2[k, 0] < -0.18 and -0.25 < cen2[k, 2] < -0.03 and (tri2[k] >= 70 or set(lf['M'][lb == k]) == {'Optics'})]
    # 11 Nov (user's reference renders): the late cupola's front part with the MK-4 is fixed and the single lid behind it hinges at
    # its front edge, standing up when open - the model's front 'leaf' joins the turret, its rear leaf is the lid
    parts['d_sight_03'] = part(lf, np.isin(lb, peri)); parts['tur'] = B.join([parts['tur'], part(lf, ~np.isin(lb, peri))])
    parts['d_hatch_04'] = part(objs['Commander_Hatch_1_Cube.006'], np.ones(len(objs['Commander_Hatch_1_Cube.006']['P']), bool))
    parts['d_hatch_03'] = part(objs['Gunnet_Hatch__Cube.010'], np.ones(len(objs['Gunnet_Hatch__Cube.010']['P']), bool))
    bar = tur['P'][role[lab] == 'bar'].reshape(-1, 3); mk = tur['P'][role[lab] == 'mask'].reshape(-1, 3)
    bore = to_game(np.array([[(bar[:, 0].min() + bar[:, 0].max()) / 2, (bar[:, 1].min() + bar[:, 1].max()) / 2, bar[:, 2].min()]]))[0]
    trun = to_game(np.array([[bore[0] / S + RC[0], (bar[:, 1].min() + bar[:, 1].max()) / 2, mk[:, 2].max()]]))[0]
    return parts, bore, trun


def build(t34, model):
    K = SM.Src(t34); objs = read_obj(os.path.join(model, 'T-34-85.obj'))
    P_, MUZ, TRUN = split(objs); BORE = MUZ.copy()
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
    for n in K.nodes[1:]:   # the game T-34 minus its 76 mm turret; its uv into the sheet's top-left quarter
        nm = n['name']
        if nm in A.TURRET_NODES or under_head(n): continue
        geo = {}
        for L in range(4):
            if (nm, L) in K.geo:
                a, f = K.geo[(nm, L)]; a = a.copy()
                if L > 0: a[:, 3:5] *= 0.5
                geo[L] = (a, f)
        add(nm, n['kind'], pname(n), K.local(nm), geo)
    AR = A.ARM85
    def geo(p, pivot, cls=None, R=None):
        q = p.moved(pivot, R); g = q.gxt(); return {0: OLD.hit(*q.plain(), AR, cls), 1: g, 2: g, 3: g}
    add('d_head', 4, 'd_hull', tr(RING), geo(P_['tur'], RING))
    add('d_gunmask', 4, 'd_head', tr(TRUN - RING), geo(P_['mask'], TRUN, 'front'))
    add('d_gun', 4, 'd_gunmask', np.eye(4), geo(P_['bar'], TRUN, 'roof'))
    add('s_gun', 0, 'd_gun', tr(np.array([BORE[0], BORE[1], BORE[2] + 0.05]) - TRUN))
    coax = np.array([BORE[0] + 0.24, BORE[1] + 0.02, TRUN[2] + 0.30]); add('d_minigun', 0, 'd_gunmask', tr(coax - TRUN)); add('s_mgun', 0, 'd_minigun', tr((0, 0, 0.05)))
    # hatches: frame x from the hinge into the lid, y up, z along the hinge (hatchs column 7 = 2); hinge at the lid's top edge
    HR = {}
    for nm, front in (('d_hatch_03', True), ('d_hatch_04', True)):   # both hinge at their front edge
        p = P_[nm]; lo, hi = p.lo(), p.hi(); xd = np.array([0, 0, -1.0 if front else 1.0])
        hinge = np.array([(lo[0] + hi[0]) / 2, hi[1], hi[2] if front else lo[2]])
        Rm = np.array([xd, [0, 1.0, 0], np.cross(xd, [0, 1.0, 0])]); M = np.eye(4); M[:3, :3] = Rm; M[3, :3] = hinge - RING; HR[nm] = (Rm, hinge)
        add(nm, 4, 'd_head', M, geo(P_[nm], hinge, 'roof', Rm))
    PERIS = {}
    for nm in ('d_sight_01', 'd_sight_02', 'd_sight_03'):
        p = P_[nm]; c_ = np.array([(p.lo()[0] + p.hi()[0]) / 2, p.lo()[1], (p.lo()[2] + p.hi()[2]) / 2]); PERIS[nm] = c_
        add(nm, 4, 'd_head', tr(c_ - RING), geo(p, c_, 'roof'))   # the cupola's sits on its fixed front part
        M = np.eye(4); M[3, :3] = [0.0, p.hi()[1] - c_[1] - 0.03, p.hi()[2] - c_[2] + 0.02]
        add({'d_sight_01': 's_camera_pt4_7', 'd_sight_02': 's_camera_loader_02', 'd_sight_03': 's_camera_mk4_01'}[nm], 0, nm, M)
    # the old turret's sockets at the same place relative to the ring; gun-side ones on the trunnion
    TV = P_['tur'].P.reshape(-1, 3)
    def wall(y, z, r=0.10):
        q = TV[(np.abs(TV[:, 1] - y) < r) & (np.abs(TV[:, 2] - z) < r)]; return float(np.abs(q[:, 0]).max()) if len(q) else 0.95
    for n in K.nodes[1:]:
        nm = n['name']
        if not under_head(n) or nm.startswith('d_') or nm in ('s_gun', 's_mgun', 's_camera_pt4_7'): continue
        wp = n['world'][3, :3].copy(); par = 'd_gunmask' if nm in ('s_camera_tmfd7', 'p_rotgun') else 'd_head'
        if nm == 's_camera_tmfd7': wp = np.array([BORE[0] - 0.30, BORE[1] + 0.06, TRUN[2] + 0.30])
        if nm in ('s_camera_gunner', 's_camera_loader'): wp = np.array([np.sign(wp[0]) * (wall(wp[1], wp[2]) + 0.03), wp[1], wp[2]])
        if nm == 's_loader_out': h = P_['d_hatch_03']; wp = np.array([(h.lo()[0] + h.hi()[0]) / 2, h.lo()[1] - 0.07, (h.lo()[2] + h.hi()[2]) / 2])
        M = np.eye(4); M[:3, :3] = n['world'][:3, :3]; M[3, :3] = wp - (TRUN if par == 'd_gunmask' else RING)
        A0 = K.geo.get((nm, 0)); add(nm, n['kind'], par, M, {0: A0} if A0 is not None and nm.startswith('p_') else {})
    # the commander under the cupola: seat, damage box, exit, head-out, five slits round the cupola wall
    lf = B.join([P_['d_hatch_04'], P_['d_sight_03']]); CUP = np.array([(lf.lo()[0] + lf.hi()[0]) / 2, 0.0, (lf.lo()[2] + lf.hi()[2]) / 2]); lid = lf.lo()[1]
    dc = np.hypot(TV[:, 0] - CUP[0], TV[:, 2] - CUP[2]); band = (TV[:, 1] > lid - 0.12) & (TV[:, 1] < lid) & (dc < 0.55)
    rc = float(np.percentile(dc[band], 97)) if band.any() else 0.38
    def look(d):
        z = np.asarray(d, float); z /= np.linalg.norm(z); x = np.cross([0, 1.0, 0], z); x /= np.linalg.norm(x); return np.array([x, np.cross(z, x), z])
    def sock(name, wp, d=(0, 0, 1.0), geo_=None):
        M = np.eye(4); M[:3, :3] = look(d); M[3, :3] = np.asarray(wp, float) - RING; add(name, 0 if geo_ is None else 1, 'd_head', M, geo_ or {})
    sock('s_commander', (CUP[0], 0.70, CUP[2])); pg = K.geo.get(('p_gunner', 0)); sock('p_commander', (CUP[0], 0.70, CUP[2]), geo_={0: pg} if pg is not None else None)
    sock('s_commander_exit', (CUP[0] - 2.0, 1.35, CUP[2])); sock('s_commander_out', (CUP[0], lid - 0.07, CUP[2]))
    for k, ang in enumerate((0, 60, 120, 240, 300)):
        dv = np.array([np.sin(np.radians(ang)), 0, np.cos(np.radians(ang))]); sock('s_camera_mk4_%02d' % (k + 2), CUP + dv * (rc + 0.03) + [0, lid - 0.05, 0], dv)
    print('nodes', len(nodes), 'ring', RING, 'trunnion', np.round(TRUN, 3), 'muzzle', np.round(BORE, 3), 'cupola', np.round(CUP, 3), 'lid', round(lid, 3), 'r', round(rc, 3))
    lods = lambda p: [p, p, p, p]
    return nodes, (lods(P_['tur']), lods(P_['mask']), lods(P_['bar']), {k: (lods(P_[k]), PERIS[k], P_[k].hi()[1]) for k in ('d_sight_01', 'd_sight_02')}, TRUN)


def textures(model, dift, norsp, out):
    import atf1
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    t = lambda n: os.path.join(model, 'textures', n)
    N, H = 2048, 1024; dif = np.zeros((N, N, 3), np.float32); nrm = np.zeros((N, N, 4), np.float32)
    def img(p, mode='RGB'): return np.asarray(Image.open(p).convert(mode).resize((H, H), Image.LANCZOS), np.float32)
    dif[:H, :H] = np.asarray(Image.fromarray(np.asarray(atf1.top(dift))[..., :3]).resize((H, H), Image.LANCZOS), np.float32)
    nrm[:H, :H] = np.asarray(Image.fromarray(np.asarray(atf1.top(norsp)), 'RGBA').resize((H, H), Image.LANCZOS), np.float32)
    for (ox, oy), stem in ((UV_MAIN, 'UV'), (UV_HATCH, 'Hatches')):
        x0, y0 = int(ox * N), int(oy * N)
        d = img(t(stem + '_Base_Color.png')); ao = img(t(stem + '_Mixed_AO.png'), 'L')[..., None] / 255.0
        dif[y0:y0 + H, x0:x0 + H] = d * (0.45 + 0.55 * ao)
        n_ = img(t(stem + '_Normal_OpenGL.png')); r = img(t(stem + '_Roughness.png'), 'L') / 255.0
        nrm[y0:y0 + H, x0:x0 + H, 0] = n_[..., 0]; nrm[y0:y0 + H, x0:x0 + H, 1] = 255.0 - n_[..., 1]   # OpenGL -> the game's green
        nrm[y0:y0 + H, x0:x0 + H, 2] = 10.0; nrm[y0:y0 + H, x0:x0 + H, 3] = 100.0 + 100.0 * (1.0 - r)
    dif[H:, H:] = 30; nrm[H:, H:] = (128, 128, 10, 60)
    for uv, c in ((DARK_UV, 6), (GLASS_UV, (40, 48, 58))):
        y, x = int(uv[1] * N), int(uv[0] * N); dif[y - 24:y + 24, x - 24:x + 24] = c
    y, x = int(GLASS_UV[1] * N), int(GLASS_UV[0] * N); nrm[y - 24:y + 24, x - 24:x + 24, 3] = 230
    # 11 Nov: the model's red stars painted out (the game puts its own numbers on), with the paint round them
    from scipy.ndimage import binary_dilation, gaussian_filter
    for y0, x0 in ((0, H), (H, 0)):
        q = dif[y0:y0 + H, x0:x0 + H]; red = (q[..., 0] > q[..., 1] * 1.35) & (q[..., 0] > 70); red = binary_dilation(red, iterations=3)
        if red.any():
            w = gaussian_filter((~red).astype(np.float32), 12)[..., None]; fill = np.stack([gaussian_filter(q[..., k] * ~red, 12) for k in range(3)], -1) / np.maximum(w, 1e-3)
            q[red] = fill[red]; print('stars painted out:', int(red.sum()), 'texels')
    # the paint matched to the game T-34's: green paint pixels of each sheet (green over red and blue, mid brightness), per channel
    def paint_tone(q):
        q = q.reshape(-1, 3); l = q.mean(1); m = (q[:, 1] > q[:, 0]) & (q[:, 1] > q[:, 2]) & (l > np.percentile(l, 20)) & (l < np.percentile(l, 80))
        return np.median(q[m], 0)
    r_ = paint_tone(dif[:H, :H]) / np.maximum(paint_tone(dif[:H, H:]), 1); lum = r_.mean()
    s_ = np.clip(lum * (r_ / lum) ** 0.5, 0.3, 1.2)   # brightness matched in full, the hue only half way (fully it went yellow-olive)
    dif[:H, H:] *= s_; dif[H:, :H] *= s_; print('model paint scaled by', np.round(s_, 2), 'to the game T-34 paint', np.round(paint_tone(dif[:H, :H])))
    dif = np.clip(dif, 0, 255).astype(np.uint8); nrm = np.clip(nrm, 0, 255).astype(np.uint8)
    B.write_textures(dif, nrm, out, MATERIAL[1].decode()[:-5]); Image.fromarray(dif).resize((1024, 1024)).save(os.path.join(out, 't3485_dift_preview.png'))


if __name__ == '__main__':
    t34, model, dift, norsp, out = sys.argv[1:6]; ostov = sys.argv[6] if len(sys.argv) > 6 else None; arm_src = sys.argv[7] if len(sys.argv) > 7 else None
    os.makedirs(out, exist_ok=True)
    nodes, parts = build(t34, model)
    data = B.rename_material(SM.assemble(nodes, t34), (MATERIAL[0],), (MATERIAL[1],))
    p = os.path.join(out, 't3485.mesh.loc_def.bin'); open(p, 'wb').write(data)
    m = azg2.read(p); print('written', p, len(data), 'bytes;', len(m['nodes']), 'nodes;', [(b['tag'], b['nv'], b['ni']) for b in m['blocks']])
    textures(model, dift, norsp, out); print('textures written')
    if ostov: A.wreck(ostov, parts, out)
    if arm_src: A.armour_map(arm_src, out); print('armour map written')

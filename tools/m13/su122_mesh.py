"""Build the SU-122 game mesh (AZG2) from the Mius-Front T-34 mod. 1942 (t34_42_utz) and the M-30 howitzer (m30m38).

  python su122_mesh.py <t34_42_utz mesh> <m30m38 mesh> <out su122.mesh.loc_def.bin> [preview.obj]

Hull, running-gear nodes, damage points and sockets come from the T-34; the turret and bow MG are removed, the hull
is clipped by the casemate (su122_geom.py), the casemate / mantlet / roof parts are added, and the M-30 barrel
geometry becomes d_gun. Crew sockets follow the SU-152 layout, scaled into the smaller casemate. Everything uses
the T-34 texture (material 1) and the T-34 armour map (armour UV = diffuse UV, as on every vanilla vehicle).
"""
import sys, os, struct, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import azg2, geom, su122_geom as G, uvtools as U

# ---------------------------------------------------------------- vertex codecs
def gxt_decode(raw):
    raw = np.asarray(raw)
    pos = raw[:, :12].copy().view(np.float32).astype(np.float64)
    uv = raw[:, 12:16].copy().view(np.int16).reshape(-1, 2) / 32767.0
    nrm = raw[:, 20:23] / 127.5 - 1; tan = raw[:, 24:27] / 127.5 - 1; bin_ = raw[:, 28:31] / 127.5 - 1
    return np.c_[pos, uv, nrm, tan, bin_]                       # 14 floats

def gxt_encode(A, bone):
    n = len(A); out = np.zeros((n, 32), np.uint8)
    out[:, :12] = A[:, :3].astype(np.float32).view(np.uint8).reshape(n, 12)
    out[:, 12:16] = np.clip(np.round(A[:, 3:5] * 32767), -32767, 32767).astype(np.int16).view(np.uint8).reshape(n, 4)
    out[:, 16] = bone
    for k, c in ((20, 5), (24, 8), (28, 11)):
        v = A[:, c:c + 3]; v = v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-12)
        out[:, k:k + 3] = np.clip(np.round((v + 1) * 127.5), 0, 255)
    return out

def tangent_frame(V, F, UV):
    """flat normal + tangent / binormal per face from the UV gradient"""
    n = geom.normals(V, F); t = np.zeros_like(n); b = np.zeros_like(n)
    for k, f in enumerate(F):
        p = V[f]; q = UV[f]
        e1, e2 = p[1] - p[0], p[2] - p[0]; d1, d2 = q[1] - q[0], q[2] - q[0]
        r = d1[0] * d2[1] - d2[0] * d1[1]
        if abs(r) < 1e-12: tt = np.cross([0, 1, 0], n[k]) if abs(n[k][1]) < 0.9 else np.array([1.0, 0, 0]); bv = None
        else: tt = (e1 * d2[1] - e2 * d1[1]) / r; bv = (e2 * d1[0] - e1 * d2[0]) / r
        tt = tt - n[k] * (tt @ n[k]); tt /= np.linalg.norm(tt) + 1e-12
        # the binormal points along +v, as in the game's own meshes (kv1s_late, zis3, t34: 99.9 % of faces): mirrored UV
        # islands get -(n x t).  Until 9 Nov it was always n x t, which turned the bump map upside down on mirrored parts.
        bb = np.cross(n[k], tt); t[k] = tt; b[k] = -bb if bv is not None and bb @ bv < 0 else bb
    return n, t, b

def _nondegenerate(V, F):
    t = V[F]; return np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), axis=1) > 1e-10

def new_gxt(V, F, UV, N=None):
    """unshared (flat) vertices for new parts: returns attribute array (n,14), faces. N: optional per-vertex normals
    (one per row of V, for flat input) to shade curved parts smoothly"""
    if len(UV) == len(F) * 3 and len(V) == len(UV):       # flat input: one UV per (unshared) vertex
        k = _nondegenerate(V, F); F = F[k]
    if N is not None:
        # 10 Nov: mesh reduction turns some faces inside out (the IS-2's drums, rear plate, turret roof: drawn from behind, as black
        # wedges).  The source normals still point outward: a face whose winding opposes all three of its normals is turned back.
        fn0 = geom.normals(V, F); dots = np.einsum('fj,fkj->fk', fn0, N[F])
        flip = (dots < 0).all(1) & (dots.mean(1) < -0.2); F = F.copy(); F[flip] = F[flip][:, [0, 2, 1]]
        if flip.any(): new_gxt.flipped = getattr(new_gxt, 'flipped', 0) + int(flip.sum())
    n, t, b = tangent_frame(V, F, UV); n, t, b = (np.nan_to_num(x) for x in (n, t, b))
    Vf = V[F].reshape(-1, 3); UVf = UV[F].reshape(-1, 2)
    rep = lambda a: np.repeat(a, 3, axis=0)
    n, t, b = rep(n), rep(t), rep(b)
    if N is not None:
        fn = np.repeat(geom.normals(V, F), 3, axis=0); n = N[F].reshape(-1, 3).astype(float)
        # a vertex normal turned away from its face (mesh reduction folds them: 1320 faces of the IS-2, drawn as black slivers,
        # 9 Nov) takes the face's own normal
        away = np.sum(n * fn, 1) < 0.85; n[away] = fn[away]   # 10 Nov: > 32 deg off (was 75): long reduced faces kept a curved detail's sideways normal and shaded dark
        hand = np.sign(np.sum(b * np.cross(fn, t), 1, keepdims=True)); hand[hand == 0] = 1
        t = t - n * np.sum(t * n, 1, keepdims=True); t /= np.linalg.norm(t, axis=1, keepdims=True) + 1e-12
        b = np.cross(n, t) * hand                       # keeps the face's handedness (binormal along +v)
    return np.c_[Vf, UVf, n, t, b], np.arange(len(Vf)).reshape(-1, 3)

# texture areas for the new parts (T-34 diffuse): a plain, weathered plate area of the (now unused) turret wall unwrap
PLATE_RECT = (0.207, 0.046, 0.371, 0.115); PLATE_SCALE = 0.10       # clean part of the turret-wall unwrap (no baked vision slot,
                                                                    # edge lines or shadow); uv per metre (the T-34 hull is ~0.11)
MASK_RECT = PLATE_RECT                      # the cap / gun box use the same plain weathered steel
GUN_RECT = (0.38, 0.072, 0.595, 0.125)      # T-34 barrel island: length along u, circumference along v
DARK_RECT = (0.768, 0.674, 0.786, 0.692)    # black area of the T-34 texture
DARK_UV = (0.777, 0.683)                    # v28: centre of DARK_RECT - vision slit and periscope window
INNER_UV = (0.738, 0.645)                   # plain dark olive (50, 52, 24) of the T-34 texture: shadowed interior of the opening
                                            # behind the frame (v22; pure black made it look like a hole in the 3/4 photo view)
TANK_RECT = (0.72, 0.795, 0.875, 0.855)     # light part of the T-34 external-tank island

def plate_part(V, F):
    Vo, Fo, UV = U.plate_uv(V, F, PLATE_RECT, PLATE_SCALE); return new_gxt(Vo, Fo, UV)

def plate_part_smooth(V, F, rect=None, scale=None, crease=40.0):
    Vo, Fo, UV = U.plate_uv(V, F, rect or PLATE_RECT, scale or PLATE_SCALE, jitter=False)
    return new_gxt(Vo, Fo, UV, U.smooth_flat(Vo, Fo, crease))

def bead_part(V, F, rect=None):
    """small round beads (weld seams): one texel of plain steel for every vertex, smooth normals (no UV cell splitting)"""
    r = rect or PLATE_RECT; uv = np.array([(r[0] + r[2]) / 2, (r[1] + r[3]) / 2])
    Vo = V[F].reshape(-1, 3); Fo = np.arange(len(Vo)).reshape(-1, 3)
    return new_gxt(Vo, Fo, np.tile(uv, (len(Vo), 1)), U.smooth_normals(V, F, Vo, 70.0))

def cast_part(V, F, rect):
    Vo, Fo, UV = U.box_uv(V, F, rect, 0.07); N = U.smooth_normals(V, F, Vo)
    return new_gxt(Vo, Fo, UV, N)

def swept_part(V, F, origin, axis, mode, rect=None, crease=40.0):
    """castings that are prisms (gun box) or bodies of revolution (shield): sweep UVs (streaks run down the surface),
    smooth normals within the crease angle (sharp at the rim and the end faces)"""
    Vo, Fo, UV = U.sweep_uv(V, F, origin, axis, rect or MASK_RECT, PLATE_SCALE, mode=mode)
    N = U.smooth_normals(V, F, Vo, crease)
    return new_gxt(Vo, Fo, UV, N)

def round_part(V, F, origin, axis, rect):
    Vo, Fo, UV = U.cyl_uv(V, F, origin, axis, rect); N = U.smooth_normals(V, F, Vo)
    return new_gxt(Vo, Fo, UV, N)

def pnt_decode(raw, nv):
    a = np.frombuffer(np.asarray(raw).tobytes(), np.float32)
    return np.c_[a[:nv * 4].reshape(nv, 4)[:, :3], a[nv * 4:nv * 8].reshape(nv, 4)[:, :3], a[nv * 8:].reshape(nv, 4)[:, :2]].astype(np.float64)  # 8

def pnt_encode(A):
    n = len(A); z = np.zeros((n, 1))
    pos = np.c_[A[:, :3], z]; nrm = np.c_[A[:, 3:6], z]; tex = np.c_[A[:, 6:8], z, z]
    return np.concatenate([pos.astype(np.float32).ravel(), nrm.astype(np.float32).ravel(), tex.astype(np.float32).ravel()]).tobytes()

def new_pnt(V, F, tex_uv):
    if np.ndim(tex_uv) == 1: F = F[_nondegenerate(V, F)]
    n = geom.normals(V, F); Vf = V[F].reshape(-1, 3)
    T = np.tile(np.asarray(tex_uv, float), (len(Vf), 1)) if np.ndim(tex_uv) == 1 else tex_uv
    return np.c_[Vf, np.repeat(n, 3, axis=0), T], np.arange(len(Vf)).reshape(-1, 3)

# ---------------------------------------------------------------- source meshes
class Src:
    """per node, per block: local attribute arrays + local triangle list"""
    def __init__(self, path):
        self.m = m = azg2.read(path); self.d = m['data']; self.nodes = m['nodes']
        self.blocks = m['blocks']; self.geo = {}
        for L, b in enumerate(self.blocks):
            if b['tag'] == 'PNTl': A = pnt_decode(b['raw'], b['nv']); I = b['idx']
            else: A = gxt_decode(b['raw']); I = b['idx']
            for n in self.nodes:
                o = 0x90 + n['index'] * 0x140 + 0x40 + L * 0x40
                nv, ni, vs, is_ = struct.unpack_from('<4I', self.d, o)
                if not nv: continue
                f = I[is_:is_ + ni].reshape(-1, 3) - vs
                self.geo[(n['name'], L)] = (A[vs:vs + nv].copy(), f.copy())
    def node(self, name): return next(n for n in self.nodes if n['name'] == name)
    def local(self, name):
        n = self.node(name)
        return self.m['matrices'][n['matrix']].astype(np.float64) if n['matrix'] >= 0 and n['matrix'] < len(self.m['matrices']) else np.eye(4)

def xform(A, M, kind):
    """transform attribute rows by a 4x4 (row-vector) matrix: positions and direction vectors"""
    A = A.copy(); R = M[:3, :3]
    A[:, :3] = A[:, :3] @ R + M[3, :3]
    dirs = (5, 8, 11) if kind == 'gxt' else (3,)
    for c in dirs: A[:, c:c + 3] = A[:, c:c + 3] @ R
    return A

# ---------------------------------------------------------------- build
SIDE_STRIP = (0.184, 0.472, 0.802, 0.545)
ARM = dict(front=(0.35, 0.20), side=(0.45, 0.51), roof=(0.22, 0.30), rear=(0.545, 0.80))
DROP_ROOTS = ('d_head', 's_bow_rot')
DROP_NAMES = {'s_mgunner', 's_mgunner_exit', 'p_mgunner', 's_des_10', 's_des_11', 's_des_04', 's_camera_driver_03',   # riders inside the casemate
              'd_fueltank_01', 'd_fueltank_02',
              'd_saw', 'd_sawholder'}   # the T-34 saw ran half inside the casemate wall   # T-34 rear fuel tanks -> four side tanks below

def drop_pieces_inside(A, F, M, L):
    """remove connected pieces of a part that touch the casemate volume (world = local @ M)"""
    from scipy.sparse.csgraph import connected_components
    from scipy.sparse import coo_matrix
    if not len(F): return (A, F)
    P = A[:, :3] @ M[:3, :3] + M[3, :3]
    key = {}; lab = np.array([key.setdefault(tuple(p), len(key)) for p in np.round(P, 4)])
    r = np.r_[lab[F[:, 0]], lab[F[:, 1]], lab[F[:, 2]]]; c = np.r_[lab[F[:, 1]], lab[F[:, 2]], lab[F[:, 0]]]
    n, comp = connected_components(coo_matrix((np.ones(len(r)), (r, c)), shape=(len(key), len(key))), directed=False)
    bad = np.zeros(n, bool)
    hit = G.inside_any(P, -0.005); bad[np.unique(comp[lab[hit]])] = True
    keepf = ~bad[comp[lab[F[:, 0]]]]
    F = F[keepf]; used = np.unique(F); remap = np.full(len(A), -1); remap[used] = np.arange(len(used))
    return (A[used], remap[F])                                           # unreferenced vertices dropped too

HOOK_X, HOOK_Y = 0.72, -0.09        # SU-122 towing hooks on the front plate: top-front photo x +-0.73..0.74, drawing A front
                                    # view x +-0.72, y -0.03..-0.14
T34_GLACIS = (np.array([0, 0.863, 0.506]) / np.linalg.norm([0, 0.863, 0.506]), 1.0806 / np.linalg.norm([0, 0.863, 0.506]))

def hook_assembly(sx):
    """rigid move of a T-34 towing-hook assembly (the hook node + its two welded lugs in the hull mesh, at x +-0.555 on the
    59.6 deg glacis) onto the SU-122 front plate: p' = (p - b) @ R + q maps the T-34 glacis plane onto the plate, so the
    lugs sit on the plate exactly as they sat on the glacis. Returns (b, R, q)."""
    nt, dt = T34_GLACIS; n, d = G.FRONT
    t34 = np.array([sx * 0.555, -0.186, 2.6])
    b = t34 - nt * (t34 @ nt - dt)                                       # under the hook, on the T-34 glacis
    phi = np.arctan2(n[1], n[2]) - np.arctan2(nt[1], nt[2]); c, s_ = np.cos(phi), np.sin(phi)
    R = np.array([[1, 0, 0], [0, c, -s_], [0, s_, c]])                  # row vectors: nt @ R = n
    assert np.allclose(nt @ R, n, atol=1e-3)
    q = G.on_plate(G.FRONT, sx * HOOK_X, HOOK_Y) - n * 0.0035                 # lugs 0.5 mm into the plate (on the T-34 they hover 3 mm)
    return b, R, q

def move_attrs(A, b, R, q, local_off=None):
    """apply p' = (p - b) @ R + q to an attribute array (GXT 14 floats or PNT 8 floats); local_off: subtract after (node
    origin)"""
    A = A.copy(); P = A[:, :3] - b
    A[:, :3] = P @ R + q - (local_off if local_off is not None else 0)
    for cc in ((5, 8, 11) if A.shape[1] == 14 else (3,)): A[:, cc:cc + 3] = A[:, cc:cc + 3] @ R
    return A

def split_hook_lugs(A, F):
    """take the two T-34 hook lugs (connected pieces of the hull mesh inside the hook region at x +-0.555) out of the hull
    geometry; returns (rest, {sx: lugs})"""
    from scipy.sparse.csgraph import connected_components
    from scipy.sparse import coo_matrix
    P = A[:, :3]; key = {}; lab = np.array([key.setdefault(tuple(p), len(key)) for p in np.round(P, 4)])
    r = np.r_[lab[F[:, 0]], lab[F[:, 1]], lab[F[:, 2]]]; c = np.r_[lab[F[:, 1]], lab[F[:, 2]], lab[F[:, 0]]]
    nc, comp = connected_components(coo_matrix((np.ones(len(r)), (r, c)), shape=(len(key), len(key))), directed=False)
    fc = comp[lab[F[:, 0]]]; take = {1: np.zeros(len(F), bool), -1: np.zeros(len(F), bool)}
    for k in np.unique(fc):
        m = fc == k; Q = P[F[m]].reshape(-1, 3)
        for sx in (1, -1):
            if (Q[:, 0] * sx).min() > 0.47 and (Q[:, 0] * sx).max() < 0.64 and Q[:, 1].min() > -0.32 and Q[:, 1].max() < -0.06 \
               and Q[:, 2].min() > 2.3 and Q[:, 2].max() < 2.72:
                take[sx] |= m
    def sub(mask):
        Fm = F[mask]; used = np.unique(Fm); remap = np.full(len(A), -1); remap[used] = np.arange(len(used))
        return A[used], remap[Fm]
    rest = sub(~(take[1] | take[-1]))
    return rest, {sx: sub(take[sx]) for sx in (1, -1) if take[sx].any()}

def su152_sockets(path):
    """SU-152 crew / camera / exit sockets mapped into the SU-122 casemate (z scaled, gun-relative)"""
    s = Src(path); out = {}
    want = ('s_driver', 's_driver_exit', 's_camera_driver', 's_camera_loader_01', 's_camera_loader_02', 's_camera_gunner_01',
            's_loader_exit', 's_loader_02_exit', 's_commander_exit', 's_loader_01', 's_loader_02', 's_gunner', 's_commander',
            's_loader_01_out', 's_commander_out', 's_gunner_out', 's_gunner_exit', 's_smk_gun', 's_fire_02', 's_fire_03', 's_fire_04',
            's_mark_01f', 's_mark_02f', 's_mark_03f', 's_mark_04', 's_mark_01', 's_mark_02', 's_mark_03',
            'p_loader_01', 'p_loader_02', 'p_gunner', 'p_commander', 'p_ammo_02', 'p_ammo_03', 'p_ammo_04',
            's_camera_loader_03', 's_camera_gunner_03', 's_camera_commander_01', 's_fire_01a')
    for n in s.nodes:
        if n['name'] in want:
            x, y, z = n['world'][3, :3]
            z2 = -0.12 + (z + 0.55) * (1.84 / 3.10)                 # su152 fighting compartment -0.55..2.55 -> -0.12..1.72
            y2 = -0.80 + (y + 0.637) * 0.952 * (G.ROOF + 0.80) / 1.72   # su152 floor / roof -> T-34 floor / SU-122 roof
            x2 = x * 0.90
            if n['name'].endswith('_exit') or n['name'].startswith('s_mark'): x2, y2, z2 = x, y - 0.05, z - 1.2
            out[n['name']] = (np.array([x2, y2, z2]), n['world'][:3, :3].copy())
    # positions tied to the SU-122 roof fittings (the SU-152 hatches and sights sit elsewhere)
    R = G.ROOF
    def put(name, p): out[name] = (np.asarray(p, float), out[name][1])        # new position, SU-152 orientation / scale
    put('s_camera_gunner_01', G.PANO_C + [0, 0.10, 0.12])                          # Hertz panorama head behind the hood's view ports
    put('s_commander_out', G.HATCH_C + [0.10, 0.45, 0.0])                          # heads out of the single roof hatch
    put('s_loader_01_out', G.HATCH_C + [-0.18, 0.40, 0.05])
    put('s_gunner_out', G.HATCH_C + [-0.12, 0.42, 0.10])
    put('s_camera_commander_01', G.PTK_C + [0, 0.22, 0])
    Rp = G.plate_frame(G.FRONT[0])                                                 # driver's periscope: behind the hood on his hatch
    put('s_camera_driver', G.on_plate(G.FRONT, G.DRV_X, G.DRV_Y1) + G.FRONT[0] * 0.03 - Rp[:, 1] * 0.16 - G.FRONT[0] * 0.10)
    return out, s

def build(t34_path, m30_path, su152_path):
    T = Src(t34_path); M30 = Src(m30_path)
    N = T.nodes
    def under(i, roots):
        while i != 0xffffffff and i < len(N):
            if N[i]['name'] in roots: return True
            i = N[i]['parent']
        return False
    keep = [n for n in N[1:] if not under(n['index'], DROP_ROOTS) and n['name'] not in DROP_NAMES]
    (cV, cF), planes = G.casemate(); (lV, lF), lplanes = G.casemate_lower()
    # 3 Nov (user: "the hull is not fully enclosed in some spaces"): the T-34 lower hull side plates stand at x -0.8967 /
    # +0.8987, the lower casemate's side planes at |x| 0.897 - the LEFT plate lay inside the clip volume and was cut away
    # over z -0.3..2.4 (a 2.6 x 0.65 m hole behind the road wheels, seen under the fender). Clip with the side planes
    # 4 mm further in so both side plates stay; the casemate plates themselves keep LOWER_X.
    lplanes = [(n_, d_ - 0.004) if abs(abs(n_[0]) - 1.0) < 1e-9 else (n_, d_) for n_, d_ in lplanes]
    nodes = []          # dict(name, kind, parent(name), M local 4x4, geo{L: (A, F)})
    def add(name, kind, parent, M, geo=None):
        nodes.append(dict(name=name, kind=kind, parent=parent, M=M, geo=geo or {}))
    # ---- d_hull: clipped T-34 hull + new casemate parts (all LODs)
    hull_geo = {}
    for L in range(4):
        A, F = T.geo[('d_hull', L)]
        A2, F2 = geom.subtract_convex(A, F, planes)
        A2, F2 = geom.subtract_convex(A2, F2, lplanes)
        used = np.unique(F2); remap = np.full(len(A2), -1); remap[used] = np.arange(len(used)); A2, F2 = A2[used], remap[F2]   # drop clipped-away vertices
        if L >= 1:   # renormalise interpolated direction vectors
            for c in (5, 8, 11): A2[:, c:c + 3] /= np.linalg.norm(A2[:, c:c + 3], axis=1, keepdims=True) + 1e-12
        # v24: the T-34 towing-hook lugs move with their hooks to the SU-122 hook positions (user: the hooks had no seams with
        # the hull - v20-v23 left the lugs at the T-34 positions x +-0.555 and the hooks at +-0.72)
        (A2, F2), lugs = split_hook_lugs(A2, F2)
        # v24: the T-34 bow machine-gun ball mount stood up to 7 cm out of the SU-122 front plate right of the gun mount (x
        # 0.36-0.73, y 0.05-0.28): a rounded lump beside the right cheek - cut away (in front of the plate, x 0.30-0.80, y
        # -0.02-0.36; nothing else of the T-34 hull lies there)
        nF, dF = G.FRONT
        A2, F2 = geom.subtract_convex(A2, F2, [(-nF, -(dF - 0.001)), (np.array([1.0, 0, 0]), 0.80), (np.array([-1.0, 0, 0]), -0.30),
                                               (np.array([0, 1.0, 0]), 0.36), (np.array([0, -1.0, 0]), 0.02)])
        used = np.unique(F2); remap = np.full(len(A2), -1); remap[used] = np.arange(len(used)); A2, F2 = A2[used], remap[F2]
        hull_geo[L] = [(A2, F2)] + [(move_attrs(La, *hook_assembly(sx)), Lf) for sx, (La, Lf) in lugs.items()]
    # casemate faces (bottom dropped), grouped by plate for the armour map
    cn = geom.normals(cV, cF); cF = cF[cn[:, 1] > -0.99]; cn = geom.normals(cV, cF)
    ln = geom.normals(lV, lF); lF = lF[ln[:, 2] > 0.5]                  # lower part: only its front plate is outside
    cV, cF = geom.subtract_convex(cV, cF, G.slot_planes()); lV, lF = geom.subtract_convex(lV, lF, G.slot_planes())   # gun slot
    cV0, cF0 = cV, cF                                                    # v32: hit mesh and weld seams from the plates without the hatch holes
    for planes in G.hatch_openings(): cV, cF = geom.subtract_convex(cV, cF, planes)   # v32: holes under the two hatch lids
    cn = geom.normals(cV, cF)
    def plate(nrm):
        if nrm[1] > 0.95: return 'roof'
        if nrm[2] > 0.5: return 'front'
        if nrm[2] < -0.5: return 'rear'
        return 'side'
    import su122_build as B
    rp = G.roof_parts()
    mask_box = MASK_RECT
    extra = [('casemate', cV, cF), ('casemate_low', lV, lF), ('fan', *rp[3]), ('pano', *rp[2])] + [('visor%d' % k, v, f) for k, (v, f) in enumerate(G.visors())] \
            + [('roofcoaming%d' % k, v, f) for k, (v, f) in enumerate(G.coaming())] + [('shield%d' % k, v, f) for k, (v, f) in enumerate(G.cap_shields())] \
            + [('detail%d' % k, v, f) for k, (v, f) in enumerate(G.hull_details())] \
            + [('detailfront%d' % k, v, f) for k, (v, f) in enumerate(G.front_fittings())] \
            + [('detailweld%d' % k, v, f) for k, (v, f) in enumerate(G.weld_beads(cV0, cF0))] \
            + [('darkdetail%d' % k, v, f) for k, (v, f) in enumerate(G.dark_fittings())] \
            + [('detailpano%d' % k, v, f) for k, (v, f) in enumerate(G.pano_details())]
    # entry hatch (d_hatch_02) and PTK (d_sight) are own nodes
    for name, V, F in extra:
        if name == 'fan': A, Fa = cast_part(V, F, mask_box)
        elif name.startswith('darkdetail'): A, Fa = new_gxt(V[F].reshape(-1, 3), np.arange(F.size).reshape(-1, 3), np.tile(DARK_UV, (F.size, 1)))
        else: A, Fa = plate_part(V, F)
        small = name.startswith(('detail', 'visor', 'roofcoaming', 'darkdetail'))
        for L in ((1, 2) if small else (1, 2, 3)): hull_geo[L].append((A, Fa))    # small fittings: not in the far LOD
        if small: continue                                                       # nor in the hit-test mesh
        if name == 'casemate': V, F = cV0, cF0                                   # v32: the armour stays closed under the hatch lids
        nn = geom.normals(V, F)
        for k, f in enumerate(F):
            P, Fp = new_pnt(V, f[None], ARM['roof' if name.startswith('roof') else plate(nn[k])])
            hull_geo[0].append((P, Fp))
    # opening in the front plate under the cap (the cap itself is node d_gunmount, below)
    V, F = G.slot_pocket()                                              # dark recess seen under a raised gun
    A, Fa = new_gxt(V[F].reshape(-1, 3), np.arange(F.size).reshape(-1, 3), np.tile(INNER_UV, (F.size, 1)))
    for L in (1, 2): hull_geo[L].append((A, Fa))
    # v32: recesses behind the hatch openings (user: the opened hatches showed no opening) - dark olive walls, black backs
    (Wv, Wf), (Bv, Bf) = G.hatch_pockets()
    Aw, Faw = new_gxt(Wv[Wf].reshape(-1, 3), np.arange(Wf.size).reshape(-1, 3), np.tile(INNER_UV, (Wf.size, 1)))
    Ab, Fab = new_gxt(Bv[Bf].reshape(-1, 3), np.arange(Bf.size).reshape(-1, 3), np.tile(DARK_UV, (Bf.size, 1)))
    for L in (1, 2, 3): hull_geo[L] += [(Aw, Faw), (Ab, Fab)]
    merged = {}
    for L, lst in hull_geo.items():
        As = []; Fs = []; o = 0
        for A, F in lst: As.append(A); Fs.append(F + o); o += len(A)
        merged[L] = (np.vstack(As), np.vstack(Fs))
    add('d_hull', 4, None, np.eye(4), merged)
    # ---- kept T-34 nodes (original local matrices, original geometry)
    a10r = np.radians(10.0); Rx = np.eye(4); Rx[1, 1] = Rx[2, 2] = np.cos(a10r); Rx[1, 2] = np.sin(a10r); Rx[2, 1] = -np.sin(a10r)
    for n in keep:
        if n['name'] == 'd_hull': continue
        g = {L: T.geo[(n['name'], L)] for L in range(4) if (n['name'], L) in T.geo}
        M = T.local(n['name'])
        if n['name'] == 'd_box_02':       # T-34 right rear fender box: on the SU-122 it rides on the right fender beside the casemate
            M = M.copy(); M[3, 2] += 2.475   # (drawing 36929 plan / front views: z 0.55-1.52, the tanks take the rear fender)
        if n['name'].startswith('d_hullparts'):   # T-34 riders' rails / brackets that ran where the casemate now is
            g = {L: drop_pieces_inside(A, F, M, L) for L, (A, F) in g.items()}
        if n['name'] == 'd_hatch_01':     # driver's hatch: the SU-122's own hatch, hinged at its top edge
            (V, F), hinge, _ = G.driver_hatch()
            A, Fa = plate_part_smooth(V, F, crease=35.0); P, Fp = new_pnt(V, F, ARM['front'])   # v28: rounded corners shade smoothly
            (Vs, Fs), _, _ = G.driver_hatch(simple=True)                     # far LOD and hit mesh: lid and housing only
            As, Fas = plate_part(Vs, Fs); P, Fp = new_pnt(Vs, Fs, ARM['front'])
            g = {0: (P, Fp), 1: (A, Fa), 2: (A, Fa), 3: (As, Fas)}
            M = np.eye(4); M[3, :3] = hinge
        if n['name'] == 'd_light':        # headlight on a bracket beside the front-left corner of the casemate (v20: drawing A
            M = M.copy(); M[3, :3] = [-1.28, 0.34, 1.80]                    # side z 1.74-1.91, y 0.20-0.39; front x -1.22, y 0.24-0.48)
        if n['name'] in ('d_antena_wire', 'd_noantena'):   # v20: antenna base on the right side plate at the front corner, its
            # top at roof height (drawings A / B: x 1.11 / 1.14, z 1.25-1.29, base box 0.15 high under the roof edge); the
            # whip is shortened to the drawings' 0.6-0.7 m above the base
            M = M.copy(); off = T.local(n['name'])[3, :3] - T.local('d_antena_wire')[3, :3]
            M[3, :3] = np.array([1.075, G.ROOF - 0.07, 1.27]) + off              # v24: x 1.075 so the base stands on the side plate (1.10 left a 2 cm gap)
            if n['name'] == 'd_antena_wire':
                g = {L: (A.copy(), F) for L, (A, F) in g.items()}
                for L in g:
                    yv = g[L][0][:, 1]; g[L][0][:, 1] = np.where(yv > 0.08, 0.08 + (yv - 0.08) * 0.5, yv)
        if n['name'] in ('d_kryuk_01', 'd_kryuk_02'):   # front towing hooks (drawing A front view: x +-0.72, y -0.03..-0.14)
            # v24 (user: the hooks have no seam with the hull): the T-34 hook is tilted 8.4 deg back so it stands on the 51.2 deg
            # plate as it stood on the T-34's 59.6 deg glacis, its foot sits on a welded pad on the plate and weld beads run
            # round the pad and round the hook's foot (v20-v23: tilted wrongly, foot 2-7 cm off the plate)
            sx = np.sign(M[3, 0]); b, R, q = hook_assembly(sx); t34 = T.node(n['name'])['world'][3, :3]
            g = {L: (move_attrs(np.c_[A[:, :3] + t34, A[:, 3:]], b, R, q, q), F) for L, (A, F) in g.items()}
            M = np.eye(4); M[3, :3] = q
        if n['name'] in ('d_cap_01', 'd_cap_02'):       # periscope flaps (kind 3, fixed to the driver's hatch)
            # v23: the SU-122's own flaps - two small armoured covers lying on the lower part of the periscope housing's top,
            # below the vanes (hatch frame: the housing spans 0.06-0.20 down the plate, its top 0.06 out). v19-v22 reused the
            # T-34 flap geometry, which lies at the T-34 glacis angle: squashed onto the 51 deg plate it stood up to 0.26 m out
            # in front of the hatch (a floating 'leaf' over the headlight in the side view)
            Rp = G.plate_frame(G.FRONT[0]); sx = -1 if n['name'] == 'd_cap_01' else 1
            # v28: the photos show one plain housing block - the flap nodes stay (kind 3, the game may use them) but their
            # plates lie inside the housing, just under its top
            M = np.eye(4); M[3, :3] = -Rp[:, 1] * (0.07 + G.DRV_HOFF[0]) + G.FRONT[0] * (0.050 - G.DRV_HOFF[1]) + Rp[:, 0] * (0.0265 + sx * 0.05)
            V, Fc = geom.box([0, 0, 0], [0.075, 0.045, 0.003], Rp)
            A, Fa = plate_part(V, Fc); P, Fp = new_pnt(V, Fc, ARM['front'])
            g = {0: (P, Fp), 1: (A, Fa), 2: (A, Fa)}
        if n['name'] in ('s_driver', 'p_driver', 's_camera_driver_02', 's_driver_exit'):   # driver sits under his hatch, left of the gun
            M = M.copy(); M[3, 0] -= 0.28
        add(n['name'], n['kind'], N[n['parent']]['name'] if n['parent'] != 0xffffffff else None, M, g)
    # four external 90 l fuel tanks along the engine-compartment sides (T-34 tank model, turned along the hull)
    # 90 l cylinders, 0.36 m x 0.95 m, two per side end to end on the fenders from the casemate rear (photos, drawings)
    tank_box = TANK_RECT
    tank_arm = np.median(T.geo[('d_fueltank_01', 0)][0][:, 6:8], 0)
    def tank_geo(inward):
        # brackets run from under the tank in to the hull's sloping upper side (drawings: tanks sit high, 0.19-0.53 m)
        br = [geom.box([inward * 0.14, -0.16, zz], [0.26, 0.04, 0.05]) for zz in (-0.34, 0.24)]
        br += [geom.box([0.0, -0.24, zz], [0.05, 0.14, 0.06]) for zz in (-0.34, 0.24)]       # legs (drawn as dark straps down to y 0.07)
        return geom.merge(geom.revolve([(-0.475, 0.16), (-0.45, 0.18), (0.45, 0.18), (0.475, 0.16)], [0, 0, 0], [0, 0, 1], seg=16),
                     geom.revolve([(0.17, 0.035), (0.20, 0.035), (0.21, 0.025)], [0, 0, 0.03], [0, 1, 0], seg=10),   # filler cap (drawing plan view: dot mid-tank)
                     *br,
                     geom.revolve([(-0.36, 0.19), (-0.32, 0.19)], [0, 0, 0], [0, 0, 1], seg=16),
                     geom.revolve([(0.22, 0.19), (0.26, 0.19)], [0, 0, 0], [0, 0, 1], seg=16))
    fts = {}
    for side in (1, -1):
        cyl = tank_geo(-side)
        A, Fa = round_part(*cyl, [0, 0, 0], [0, 0, 1], tank_box); P, Fp = new_pnt(*cyl, tank_arm)
        fts[side] = {0: (P, Fp), 1: (A, Fa), 2: (A, Fa), 3: (A, Fa)}
    for k, (x, z) in enumerate(((1.25, -0.80), (1.25, -1.82), (-1.25, -0.80), (-1.25, -1.82)), 1):
        M = np.eye(4); M[3, :3] = [x, 0.37, z]; add('d_fueltank_%02d' % k, 4, 'd_hull', M, fts[1 if x > 0 else -1])
    # rider exit points (on the T-34 they hang under the turret)
    for n in N:
        if n['name'].startswith('s_des_out_'):
            M = np.eye(4); M[3, :3] = n['world'][3, :3]; add(n['name'], 0, 'd_hull', M)
    # ---- gun: s_rotation (traverse axis) -> d_gunmask (trunnion; box + shield) -> d_gun (M-30 barrel) -> s_gun
    # v30: the traverse axis is TRAVERSE_DZ in front of the trunnion (v19-v29 on it); d_gunmask elevates about its own origin
    piv = np.eye(4); piv[3, :3] = G.TRAVERSE
    add('s_rotation', 0, 'd_hull', piv)
    pm = T.geo[('d_gunmask', 0)][0]; mask_arm = np.median(pm[:, 6:8], 0)
    parts = [G.mantlet(), G.shield()] + G.gun_box_details() + G.shield_details()   # v19: recoil-gear box, curved shield in the cap slot, bolts, boss
    Al = []; Fl = []; Pl = []; Pf = []; o = 0; op = 0; Al3 = []; Fl3 = []; o3 = 0
    bore_o = np.array([0, G.BORE_Y - G.PIVOT[1], 0.0])
    for pi, (V, F) in enumerate(parts):
        # v23: box and shield are castings: sweep UVs along the box / round the trunnion axis so the texture's weathering
        # streaks run down them (v22's triplanar UVs made 'wood grain' rings on the shield and stripes along the box)
        if pi == 0: A, Fa = swept_part(V, F, bore_o, [0, 0, 1.0], 'prism', crease=G.BOX_SMOOTH)   # v25: sharp side edges
        elif pi == 1: A, Fa = swept_part(V, F, [0, 0, 0], [1.0, 0, 0], 'revolve', crease=50.0)
        elif pi == len(parts) - 1: A, Fa = bead_part(V, F, MASK_RECT)          # v24: weld seam round the box (last part)
        else: A, Fa = plate_part_smooth(V, F, MASK_RECT)
        Al.append(A); Fl.append(Fa + o); o += len(A)
        if pi <= 1:
            if pi == 1:                                                 # far LOD and hit mesh: the coarse shield
                V, F = G.shield(coarse=True); A, Fa = swept_part(V, F, [0, 0, 0], [1.0, 0, 0], 'revolve', crease=50.0)
            else:                                                       # v27: and the coarse box (fewer rounding steps)
                V, F = G.mantlet(coarse=True); A, Fa = swept_part(V, F, bore_o, [0, 0, 1.0], 'prism', crease=G.BOX_SMOOTH)
            P, Fp = new_pnt(V, F, mask_arm); Pl.append(P); Pf.append(Fp + op); op += len(P)
            Al3.append(A); Fl3.append(Fa + o3); o3 += len(A)
    gl = (np.vstack(Al), np.vstack(Fl))
    gm = {1: gl, 2: gl, 3: (np.vstack(Al3), np.vstack(Fl3)), 0: (np.vstack(Pl), np.vstack(Pf))}
    trn = np.eye(4); trn[3, :3] = G.PIVOT - G.TRAVERSE                 # trunnion relative to the traverse axis
    add('d_gunmask', 4, 's_rotation', trn, gm)
    # M-30 barrel and breech block: d_gun (recoil) and d_zatvor (breech, the M-30's own child node and local matrix, so
    # the M-30's weapons row animates it as on the towed gun). v31 (user: "use the M-30 gun as source for the gun", both
    # the config rows and the texture): the visible geometry is no longer in this file - it comes as two add-in meshes
    # (su122_barrel, su122_breech: the M-30's d_gun / d_zatvor geometry with the M-30's own UVs, see addin_meshes /
    # assemble_addin) attached by the config's addins table straight to d_gun and d_zatvor, the way the Pz III L / M carry
    # their gun (PZ3_GUN on d_gun): the holder is a kind-1 node with a hit shape only, the add-in file has one kind-3 node
    # named like the holder. The add-in's name, mesh and TEXTURES come from the common_res_mod 'addins' registry
    # (su122_config.py writes the rows; without them the game shows no barrel at all - seen in the encyclopedia, v31a).
    # v19-v30 re-UVed the barrel onto the T-34 barrel strip and folded the breech into d_gun.
    g34p = T.geo[('d_gun', 0)][0]; gun_arm = np.median(g34p[:, 6:8], 0)
    m30_gun_world = M30.node('d_gun')['world']; m30_head_world = M30.node('d_head')['world']
    off = np.eye(4); off[3, :3] = m30_gun_world[3, :3] - m30_head_world[3, :3]      # d_gun origin relative to trunnion
    mz_z = M30.node('s_gun')['world'][3, 2] - m30_gun_world[3, 2]
    off[3, 2] = G.MUZZLE_Z - G.PIVOT[2] - mz_z                                    # M-30S sits so the muzzle is at 6.95 m overall
    def hit_only(name):
        A, F = M30.geo[(name, 0)]; A = A.copy(); A[:, 6:8] = gun_arm; return {0: (A, F)}
    add('d_gun', 1, 'd_gunmask', off, hit_only('d_gun'))                          # add-in holder (Pz III: d_gun kind 1, hit shape)
    add('d_zatvor', 1, 'd_gun', M30.local('d_zatvor'), hit_only('d_zatvor'))       # add-in holder for the breech block
    mz = np.eye(4); mz[3, :3] = M30.node('s_gun')['world'][3, :3] - m30_gun_world[3, :3]
    add('s_gun', 0, 'd_gun', mz)
    # damage points that moved with the gun: p_rotgun (gun cradle), p_rothead (mount) - both centred on the trunnion as in
    # v19-v29 (p_rothead is the T-34's turret-ring disc, r 0.84: centred on the new traverse axis it would stand 0.65 m out
    # in front of the plate)
    box = T.geo[('p_rotgun', 0)] if ('p_rotgun', 0) in T.geo else T.geo[('p_ammo_01', 0)]
    add('p_rotgun', 1, 'd_gunmask', np.eye(4), {0: box})
    add('p_rothead', 1, 's_rotation', trn, {0: T.geo[('p_rothead', 0)]})
    # ---- the cast cap (cheeks, slot walls, bridge, bolts): v30 fixed to the hull (user: "the gunmount should stay fixed to
    # the hull"); v19-v29 it was a child of s_rotation and swung with the gun through the traverse. Own node (kind 3) at the
    # trunnion, so its geometry stays in the frame it is built in
    mask_arm_c = np.median(T.geo[('d_gunmask', 0)][0][:, 6:8], 0)
    V, F = G.cap(); V = V - G.PIVOT
    A, Fa = cast_part(V, F, MASK_RECT); P, Fp = new_pnt(V, F, mask_arm_c)
    Vw, Fw = G.cap_slot_walls(); Vw = Vw - G.PIVOT
    Aw, Faw = plate_part(Vw, Fw)                                         # slot walls: same cast steel as the cap (v19: was black)
    Vg, Fg = G.cap_bridge(); Vg = Vg - G.PIVOT                           # v26: the cap's top over the slot, under the shield plate
    Ag, Fag = swept_part(Vg, Fg, [0, 0, 0], [1.0, 0, 0], 'revolve', crease=50.0); Pg, Fpg = new_pnt(Vg, Fg, mask_arm_c)
    det = [plate_part(v - G.PIVOT, f) for v, f in G.cap_details()]
    full = [(A, Fa), (Aw, Faw), (Ag, Fag)] + det
    def cat(lst):
        As, Fs, o = [], [], 0
        for a_, f_ in lst: As.append(a_); Fs.append(f_ + o); o += len(a_)
        return np.vstack(As), np.vstack(Fs)
    cap_m = np.eye(4); cap_m[3, :3] = G.PIVOT
    add('d_gunmount', 3, 'd_hull', cap_m, {0: cat([(P, Fp), (Pg, Fpg)]), 1: cat(full), 2: cat(full), 3: cat([(A, Fa), (Ag, Fag)])})
    # ---- the single roof entry hatch (d_hatch_02); v34d (user): hinged on a rod along its FRONT edge again, opens to
    # the front (the hatchs row's +120 deg tips it over forward); v34c had the rod along the right edge
    for hname, (V, F), hinge in (('d_hatch_02', rp[0], G.HATCH_C + [0, G.HATCH_S[1] + 0.018, G.HATCH_S[2] / 2]),):   # v34i: knuckle axis on the front edge
        Rh = np.eye(3)                                                                # local x = world x (the rod)
        Vl = (V - hinge) @ Rh.T
        A, Fa = plate_part(Vl, F)
        P, Fp = new_pnt(Vl, F, ARM['roof'])
        Mh = np.eye(4); Mh[:3, :3] = Rh; Mh[3, :3] = hinge
        add(hname, 4, 'd_hull', Mh, {0: (P, Fp), 1: (A, Fa), 2: (A, Fa), 3: (A, Fa)})
    # ---- SU-152 crew layout
    sock, S152 = su152_sockets(su152_path)
    have = {n['name'] for n in nodes}
    pbox = T.geo[('p_ammo_01', 0)]
    marks = G.mark_sockets()
    for name, p in sock.items():
        if name in have: continue
        if name in marks: add(name, 0, 'd_hull', marks[name]); continue
        p, Rs = p if isinstance(p, tuple) else (p, np.eye(3))
        M = np.eye(4); M[3, :3] = p
        if not name.startswith('p_'): M[:3, :3] = Rs
        if name.startswith('p_'): add(name, 1, 'd_hull', M, {0: pbox})
        else: add(name, 0, 'd_hull', M)
    # gunner's sight moves with the gun; commander's periscope d_sight with its camera
    cam = np.eye(4); cam[3, :3] = [-0.32, 0.20, 0.50]   # gunner's direct-fire sight, left of the gun inside the casemate
    add('s_camera_gunner_02', 0, 'd_gunmask', cam)
    ds = np.eye(4); ds[3, :3] = G.PTK_C + [0, 0.12, 0]
    V, F = rp[1]; Vl = V - ds[3, :3]                                    # v29: round head, band, lugs (G.ptk)
    A, Fa = plate_part_smooth(Vl, F, crease=35.0)
    Vw, Fw = G.ptk_window(); Vw = Vw - ds[3, :3]                         # dark window on its front
    Aw, Faw = new_gxt(Vw[Fw].reshape(-1, 3), np.arange(Fw.size).reshape(-1, 3), np.tile(DARK_UV, (Fw.size, 1)))
    A, Fa = np.vstack([A, Aw]), np.vstack([Fa, Faw + len(A)])
    Vs, Fs = G.ptk(simple=True); Vs = Vs - ds[3, :3]                     # far LOD and hit mesh
    As, Fas = plate_part_smooth(Vs, Fs, crease=35.0); P, Fp = new_pnt(Vs, Fs, ARM['roof'])
    add('d_sight', 4, 'd_hull', ds, {0: (P, Fp), 1: (A, Fa), 2: (A, Fa), 3: (As, Fas)})
    return nodes

# ---------------------------------------------------------------- writer
def assemble(nodes, template_path):
    tpl = azg2.parse(open(template_path, 'rb').read())
    names = [n['name'] for n in nodes]; idx = {n: i + 1 for i, n in enumerate(names)}
    allnodes = [dict(name='s_root', kind=0, parent=None, M=np.eye(4), geo={})] + nodes
    idx['s_root'] = 0
    # children lists in table order
    kids = {i: [] for i in range(len(allnodes))}
    for i, n in enumerate(allnodes[1:], 1):
        p = idx[n['parent']] if n['parent'] else (0 if n['name'] == 'd_hull' else idx['d_hull'])
        n['pi'] = p; kids[p].append(i)
    allnodes[0]['pi'] = None
    # matrices: every node but s_root / d_hull
    mats = []; mindex = {}
    for i, n in enumerate(allnodes):
        if n['name'] in ('s_root', 'd_hull'): continue
        mindex[i] = len(mats); mats.append(n['M'].astype(np.float32))
    # model-space matrices (row vectors: local times the parent's world) - the block headers carry the LOD's bounding box in
    # MODEL space, as in 465 of 474 vanilla GXT2 blocks (4 Nov: ours held the box of the node-local coordinates, e.g. the
    # M3 Lee LOD1 centre at y 1.24 instead of 1.35 and z -0.05 instead of +0.18, the SU-122 LOD3 centre 0.31 m to the left)
    Wm = {}
    def world(i):
        if i not in Wm:
            n = allnodes[i]; M = np.asarray(n['M'], np.float64)
            Wm[i] = M if n['pi'] is None else M @ world(n['pi'])
        return Wm[i]
    # per block: concatenate node geometry in table order
    blocks = []
    for L, tb in enumerate(tpl['blocks']):
        Vs = []; Is = []; slot = {}; vs = 0; is_ = 0; bone = 0; order = []; Ws = []
        for i, n in enumerate(allnodes):
            if L not in n['geo']: continue
            A, F = n['geo'][L]
            if tb['tag'] == b'PNTl':
                Vs.append(A); Is.append((F + vs).ravel())
            else:
                Vs.append(gxt_encode(A, bone)); Is.append((F + vs).ravel()); bone += 1; order.append(i)
            P = A[:, :3]; c = (P.max(0) + P.min(0)) / 2; h = (P.max(0) - P.min(0)) / 2
            slot[i] = (len(A), F.size, vs, is_, c, h); vs += len(A); is_ += F.size
            Pw = np.c_[np.asarray(P, np.float64), np.ones(len(P))] @ world(i); Ws.append(Pw[:, :3])
        if tb['tag'] == b'PNTl':
            A = np.vstack(Vs); vtx = pnt_encode(A); I = np.concatenate(Is).astype(np.uint32); P = A[:, :3]
        else:
            vtx = np.vstack(Vs).tobytes(); I = np.concatenate(Is); assert I.max() < 65536, 'too many vertices for u16 indices'
            I = I.astype(np.uint16); P = np.vstack([np.frombuffer(v[:, :12].tobytes(), np.float32).reshape(-1, 3) for v in Vs])
        P = np.vstack(Ws); c = (P.max(0) + P.min(0)) / 2; h = (P.max(0) - P.min(0)) / 2      # model space (see above)
        head = bytearray(tb['head']); struct.pack_into('<8f', head, 0, c[0], c[1], c[2], 1.0, h[0], h[1], h[2], 0.0)
        blocks.append(dict(tag=tb['tag'], ver=tb['ver'], lod=tb['lod'], li=tb['li'], head=bytes(head), isz=tb['isz'],
                           idx=I.tobytes(), ni=len(I), vtx=vtx, nv=len(vtx) // (48 if tb['tag'] == b'PNTl' else 32), slots=slot, order=order))
    # node records
    recs = []
    for i, n in enumerate(allnodes):
        r = bytearray(0x140); r[:0x20] = n['name'].encode('cp1251')[:0x1f].ljust(0x20, b'\0')
        ident = np.allclose(n['M'][:3, :3], np.eye(3), atol=1e-5)     # bit 31: matrix has no rotation (checked on 1 800 vanilla nodes)
        mi = 0xffffffff if i not in mindex else ((0x80000000 if ident else 0) | mindex[i])
        par = 0xffffffff if n['pi'] is None else n['pi']
        ch = kids[i]
        struct.pack_into('<5I', r, 0x20, mi, n['kind'], par, ch[0] if ch else 0, len(ch))
        if n['name'] == 's_root': struct.pack_into('<5I', r, 0x20, 0xffffffff, 0, 0xffffffff, 1, 1)
        for L, b in enumerate(blocks):
            so = 0x40 + L * 0x40
            if i in b['slots']:
                nv, ni, vs, is_, c, h = b['slots'][i]
                struct.pack_into('<4IIi', r, so, nv, ni, vs, is_, L if L else 0, -1)
                struct.pack_into('<8f', r, so + 0x20, c[0], c[1], c[2], 0, h[0], h[1], h[2], 0)
        recs.append(bytes(r))
    itabs = [dict(items=b['order'], a=64, b=1, rest=bytes(16)) for b in blocks if b['tag'] != b'PNTl']
    s = dict(nodes=recs, mats=tpl['mats'], mtx=np.array(mats, np.float32).tobytes(), nx=len(mats), itabs=itabs,
             blocks=[{k: b[k] for k in ('tag', 'ver', 'lod', 'li', 'head', 'isz', 'idx', 'ni', 'vtx', 'nv')} for b in blocks],
             hash_n=None, packed=True)
    return azg2.write(s)

def assemble_addin(node_name, geo, template_path):
    """v31: an add-in mesh like the Pz III's gun (m_pz3_gun) or the SU-152's gun shield: s_root + one kind-3 node named
    like the holder node of the vehicle mesh, three GXT2 LOD blocks, no hit mesh, no matrices, one material - the
    template's (the M-30 file: m30m38_dift; the game takes the textures from the common_res_mod addins registry anyway).
    geo: {1: (A, F), 2: ..., 3: ...} attribute arrays (14 columns) in the holder node's frame."""
    tpl = azg2.parse(open(template_path, 'rb').read())
    gxt = [b for b in tpl['blocks'] if b['tag'] == b'GXT2']
    recs = []
    for i, name in enumerate(('s_root', node_name)):
        r = bytearray(0x140); r[:0x20] = name.encode('cp1251')[:0x1f].ljust(0x20, b'\0')
        if i == 0: struct.pack_into('<5I', r, 0x20, 0xffffffff, 0, 0xffffffff, 1, 1)
        else: struct.pack_into('<5I', r, 0x20, 0xffffffff, 3, 0, 0, 0)
        recs.append(r)
    blocks = []
    for L in (1, 2, 3):
        A, F = geo[L]; tb = gxt[L - 1]
        vtx = gxt_encode(A, 0); I = (F.ravel()).astype(np.uint16); P = A[:, :3]
        c = (P.max(0) + P.min(0)) / 2; h = (P.max(0) - P.min(0)) / 2
        head = bytearray(tb['head']); struct.pack_into('<8f', head, 0, c[0], c[1], c[2], 1.0, h[0], h[1], h[2], 0.0)
        so = 0x40 + (L - 1) * 0x40
        struct.pack_into('<4IIi', recs[1], so, len(A), len(I), 0, 0, L - 1, -1)
        struct.pack_into('<8f', recs[1], so + 0x20, c[0], c[1], c[2], 0, h[0], h[1], h[2], 0)
        blocks.append(dict(tag=b'GXT2', ver=tb['ver'], lod=0, li=L - 1, head=bytes(head), isz=2, idx=I.tobytes(), ni=len(I), vtx=vtx.tobytes(), nv=len(A)))
    s = dict(nodes=[bytes(r) for r in recs], mats=[tpl['mats'][0]], mtx=b'', nx=0, itabs=[dict(items=[1], a=64, b=1, rest=bytes(16)) for _ in blocks],
             blocks=blocks, hash_n=None, packed=False)     # 64 KB-aligned like every vanilla add-in (the main mesh is packed like the T-34)
    return azg2.write(s)

def addin_meshes(m30_path):
    """the two add-ins: (file stem, holder node, bytes). The breech block has no far LOD in the M-30 file - LOD2 is reused."""
    M30 = Src(m30_path); out = []
    for stem, node, src in (('su122_barrel', 'd_gun', 'd_gun'), ('su122_breech', 'd_zatvor', 'd_zatvor')):
        geo = {}
        for L in (1, 2, 3):
            A, F = M30.geo[(src, L)] if (src, L) in M30.geo else M30.geo[(src, L - 1)] if (src, L - 1) in M30.geo else geo[L - 1]
            geo[L] = (A, F)
        out.append((stem, node, assemble_addin(node, geo, m30_path)))
    return out

if __name__ == '__main__':
    t34, m30, su152, out = sys.argv[1:5]
    nodes = build(t34, m30, su152)
    data = assemble(nodes, t34)
    open(out, 'wb').write(data)
    m = azg2.read(out)
    print('written', out, len(data), 'bytes;', len(m['nodes']), 'nodes;', [(b['tag'], b['nv'], b['ni']) for b in m['blocks']])
    for stem, node, blob in addin_meshes(m30):                      # v31: the gun add-ins go next to the main mesh
        p = os.path.join(os.path.dirname(os.path.abspath(out)), stem + '.mesh.loc_def.bin'); open(p, 'wb').write(blob)
        a = azg2.read(p); print('written', p, len(blob), 'bytes; holder', node, [(b['tag'], b['nv'], b['ni']) for b in a['blocks']], [mt['name'] for mt in a['materials']])
    if len(sys.argv) > 5:                                           # preview OBJ: the main mesh plus the add-ins on their holders
        azg2.export_obj(m, 1, sys.argv[5])
        with open(sys.argv[5], 'a') as f:
            o = sum(1 for ln in open(sys.argv[5]) if ln.startswith('v '))
            for stem, node, blob in addin_meshes(m30):
                a = azg2.read(os.path.join(os.path.dirname(os.path.abspath(out)), stem + '.mesh.loc_def.bin')); b = a['blocks'][0]
                W = next(n for n in m['nodes'] if n['name'] == node)['world']
                P = np.c_[b['pos'], np.ones(len(b['pos']))] @ W
                f.write('o %s\n' % stem)
                for x, y, z, _ in P: f.write('v %.5f %.5f %.5f\n' % (x, y, -z))
                for u, v in b['uv']: f.write('vt %.5f %.5f\n' % (u, 1 - v))
                for t in b['idx'][:len(b['idx']) // 3 * 3].reshape(-1, 3) + 1 + o: f.write('f %d/%d %d/%d %d/%d\n' % (t[0], t[0], t[2], t[2], t[1], t[1]))
                o += len(P)

"""The user's reference M3 model (Downloads\\m3c\\M3c\\M3c.obj - not in the repo): loading, registration to the game
frame and the split of its parts into the Lee's nodes.

The OBJ is a low-poly game model in a left-handed frame (x forward, y up, z right; 1 unit = 0.4295 m, rolled 1.7 deg
about x). It is registered on the game's M4A2 running gear: its sprocket / idler axles go to the game's z 2.459 /
-2.414, the road-wheel axles to y -0.788, the hull sides centred on x = 0. Its own running gear, lower hull and nose
are dropped (the game's M4A2 parts replace them); the upper hull, turret, guns, cupola, doors, lights and fittings
are used as they are (windings reversed: the file's faces are clockwise in the game frame).

  parts = m3lee_obj.load(path)   ->  dict name -> (V, F) in the game frame (vertices shared across parts)
"""
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

K = 4.873 / (5.70 + 5.647)            # metres per model unit: sprocket / idler axle distance = the game's 4.873 m
X0, Y0, Z0 = -0.0254, 0.556, 0.0985   # model-frame offsets: sprocket axle z 2.459, road-wheel axles y -0.788, hull sides centred
ROLL = np.arctan2(0.03, 1.0)          # the model is rolled about its x axis (its floor normal is (0, -1, 0.03))
LIP = (0.147, 2.14)                   # (y, z): the game's transmission cover lip where the lower front plate must end

def read_obj(path):
    V = []; objs = {}; cur = None; mat = None
    for line in open(path):
        t = line.split()
        if not t: continue
        if t[0] == 'v': V.append([float(a) for a in t[1:4]])
        elif t[0] == 'o': cur = t[1]; objs[cur] = []
        elif t[0] == 'usemtl': mat = t[1]
        elif t[0] == 'f': objs[cur].append(([int(a.split('/')[0]) - 1 for a in t[1:4]], mat))
    return np.array(V), objs

def to_game(V):
    c, s = np.cos(ROLL), np.sin(ROLL)
    y = V[:, 1] * c - V[:, 2] * s; z = V[:, 1] * s + V[:, 2] * c
    return np.c_[(z - Z0) * K, (y - Y0) * K - 0.788, (V[:, 0] - X0) * K]

def _ray_hits(O, D, T):
    """number of triangles T (m,3,3) hit by each ray O + t D (t > 1e-4), Moller-Trumbore, chunked"""
    e1 = T[:, 1] - T[:, 0]; e2 = T[:, 2] - T[:, 0]; cnt = np.zeros(len(O), int)
    for s in range(0, len(O), 256):
        o = O[s:s + 256, None, :]; d = D[s:s + 256, None, :]
        p = np.cross(d, e2[None]); det = np.einsum('rmk,mk->rm', p, e1)
        ok = np.abs(det) > 1e-12; inv = np.where(ok, 1 / np.where(ok, det, 1), 0)
        tv = o - T[None, :, 0]; u = np.einsum('rmk,rmk->rm', tv, p) * inv
        q = np.cross(tv, e1[None]); v = np.einsum('rmk,rmk->rm', d, q) * inv; t = np.einsum('rmk,mk->rm', q, e2) * inv
        cnt[s:s + 256] = (ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 1e-4)).sum(1)
    return cnt

def orient_outward(V, F):
    """3 Nov (user: "the hull is not fully enclosed in some spaces"): the reference OBJ is wound inconsistently - parts of
    it (the right side plate, the roof right of the turret, the left front cheek) face inward and only showed in a
    double-sided viewer; the game culls back faces, so those plates were see-through holes. Every face is turned to face
    out of its own connected part: three slightly spread rays from its centroid along its normal, an odd number of
    crossings with the part (majority of the three) = the normal points inside = flip. Open single plates never flip."""
    F = F.copy(); lab = components(V, F)
    rng = np.random.default_rng(7)
    for c in np.unique(lab):
        ii = np.where(lab == c)[0]
        if len(ii) < 4: continue
        T = V[F[ii]]; n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); L = np.linalg.norm(n, axis=1); ok = L > 1e-12
        n = n / np.maximum(L, 1e-12)[:, None]; cen = T.mean(1)
        odd = np.zeros(len(ii), int)
        for k in range(3):
            d = n + rng.normal(0, 0.04, n.shape); d /= np.linalg.norm(d, axis=1)[:, None]
            odd += _ray_hits(cen + n * 1e-4, d, T) % 2
        flip = ok & (odd == 3)
        F[ii[flip]] = F[ii[flip]][:, [0, 2, 1]]
    # the outer side plates (|x| > 1.15, normal along x) face outward whatever the parity said (their bottom strips along
    # the fenders are open below)
    T = V[F]; n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); n /= np.maximum(np.linalg.norm(n, axis=1), 1e-12)[:, None]
    cx = T.mean(1)[:, 0]; side = (np.abs(n[:, 0]) > 0.95) & (np.abs(cx) > 1.15) & (np.sign(n[:, 0]) != np.sign(cx))
    F[side] = F[side][:, [0, 2, 1]]
    return F

def components(V, F):
    key = np.round(V, 4); _, inv = np.unique(key, axis=0, return_inverse=True); inv = inv.ravel(); Fi = inv[F]
    m = inv.max() + 1
    g = coo_matrix((np.ones(3 * len(Fi)), (np.r_[Fi[:, 0], Fi[:, 1], Fi[:, 2]], np.r_[Fi[:, 1], Fi[:, 2], Fi[:, 0]])), shape=(m, m))
    nc, lab = connected_components(g, directed=False)
    return lab[Fi[:, 0]]

def _boxes(V, F, lab):
    out = {}
    for c in np.unique(lab):
        P = V[F[lab == c]].reshape(-1, 3); out[c] = (P.min(0), P.max(0))
    return out

def pick(boxes, centre, tol=0.06):
    """the component whose bounding-box centre is nearest `centre` (within tol)"""
    best = None
    for c, (lo, hi) in boxes.items():
        d = np.linalg.norm((lo + hi) / 2 - np.asarray(centre, float))
        if d < tol and (best is None or d < best[0]): best = (d, c)
    if best is None: raise KeyError('no component near %s' % (centre,))
    return best[1]

# component centres (game frame) of the parts we need, per object
TURRET_OBJ = 'Mesh_0009out.016'; HULL_OBJ = 'Mesh_0012out.016'
T_PARTS = {   # name -> list of component centres in the turret object
    'turret':     [(-0.335, 1.355, -0.185)],
    'tur_sight':  [(-0.62, 1.46, 0.265)],
    'tur_port_r': [(0.305, 1.32, -0.61)],
    'cupola':     [(-0.655, 1.58, -0.415), (-0.655, 1.78, -0.375), (-0.58, 1.77, -0.32), (-0.845, 1.78, -0.045), (-0.475, 1.78, -0.045), (-0.655, 1.78, -0.045)],
    'cup_lid':    [(-0.66, 1.91, -0.40)],
    'cup_mg':     [(-0.575, 1.775, 0.195)],
    'mantlet':    [(-0.27, 1.46, 0.265), (-0.305, 1.37, 0.395), (-0.265, 1.415, 0.285)],
    'coax':       [(-0.145, 1.425, 0.44)],
    'gun37':      [(-0.305, 1.395, 1.24), (-0.305, 1.395, 0.695)],
    'shield75':   [(0.795, 0.54, 1.315)],      # the 75 mm mount's shield plate (traverses with the rotor)
    'rotor75':    [(0.785, 0.565, 1.41)],      # the vertical rotor the gun passes through
    'gun75':      [(0.78, 0.61, 2.345)],
    'box_l':      [(-1.015, 0.595, -1.96)], 'box_r': [(1.005, 0.59, -1.96)],
    'exhaust':    [(-0.50, 0.06, -2.475), (0.49, 0.055, -2.475), (-0.50, 0.265, -2.62), (0.485, 0.26, -2.62)],
    'door_l':     [(-1.275, 0.53, 0.035), (-1.285, 0.36, 0.335), (-1.285, 0.53, 0.335), (-1.285, 0.70, 0.335), (-1.315, 0.62, -0.005)],
    'door_r':     [(1.28, 0.525, 0.04), (1.295, 0.35, 0.335), (1.295, 0.52, 0.335), (1.295, 0.69, 0.335), (1.325, 0.62, 0.0)],
    'handles':    [(-1.29, 0.46, -0.34), (1.285, 0.46, -0.35)],
    'antenna':    [(-0.955, 1.915, -0.925)],
    'headlights': [(-0.935, 0.22, 2.26), (0.89, 0.215, 2.26), (0.89, 0.15, 2.22), (-0.94, 0.16, 2.22)],
    'lenses':     [(-0.935, 0.225, 2.32), (0.89, 0.22, 2.32), (-0.825, 0.34, -2.69), (0.825, 0.33, -2.69)],
    'taillights': [(-0.825, 0.34, -2.635), (0.825, 0.335, -2.635)],
    'bow_mg':     [(-0.64, 0.155, 2.165), (-0.48, 0.155, 2.165)],
    'roof_panel': [(0.84, 1.045, -0.105)],
}
H_PARTS = {   # hull object
    'hull_main':  [(0.0, 0.195, 0.025)],
    'hull_fc':    [(0.005, 0.59, 0.675)],
    'splash':     [(0.125, 1.075, 0.64)],
    'mount75':    [(0.805, 0.58, 0.74)],
    'disc':       [(0.765, 1.065, 1.05)],
    'shield_frame': [(0.795, 0.545, 1.35)],
    'visor':      [(-0.05, 0.83, 1.48), (-0.05, 0.975, 1.42)],
    'rear_fenders': [(1.025, 0.035, -2.63), (-1.025, 0.04, -2.63)],
    'cheek_port': [(-1.03, 0.785, 1.185)],
    'roof_panel_base': [(0.85, 1.01, -0.095)],
    'hl_guards':  [(-0.93, 0.24, 2.375), (0.90, 0.235, 2.375)],
    'ant_base':   [(-0.935, 0.895, -0.91)],
    'disc_box':   [(0.53, 1.145, 0.985)],
    'roof_rail':  [(0.525, 1.07, -0.26)],
    'rear_vent':  [(0.50, 0.90, -1.125)],
    'rain_strips': [(-1.295, 0.91, -0.01), (1.30, 0.90, -0.01)],
    'panel_blocks': [(0.935, 1.055, -0.43), (0.745, 1.055, -0.43)],
}
DARK_OBJS = ('Mesh_0014out.015', 'Mesh_0015out.015', 'Mesh_0016out.017', 'Mesh_0017out.017')

def load(path):
    """returns (V, parts): V (n,3) game-frame vertices, parts: name -> face array (m,3) into V, outward windings"""
    V0, objs = read_obj(path); V = to_game(V0)
    parts = {}
    for obj, table in ((TURRET_OBJ, T_PARTS), (HULL_OBJ, H_PARTS)):
        F = np.array([f for f, m in objs[obj]])[:, [0, 2, 1]]          # reverse the windings (clockwise in the game frame)
        if obj == HULL_OBJ: F = orient_outward(V, F)                     # ... and fix the hull faces the model has wound inward
                                                                        # (the turret object is consistent; its cupola seat
                                                                        # openings confuse the parity test)
        lab = components(V, F); boxes = _boxes(V, F, lab)
        used = set()
        for name, centres in table.items():
            ids = [pick(boxes, c) for c in centres]; used.update(ids)
            parts[name] = F[np.isin(lab, ids)]
        if obj == HULL_OBJ:
            # the main shell without the model's lower hull, nose, floor plate and bogie mounts (all of it lies below the
            # floor level, y 0.125; the side plates' bottom strips at |x| 1.267 stay): the game's M4A2 parts replace them
            Fm = parts['hull_main']; cen = V[Fm].mean(1); n = np.cross(V[Fm[:, 1]] - V[Fm[:, 0]], V[Fm[:, 2]] - V[Fm[:, 0]])
            n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
            floor = (np.abs(n[:, 1]) > 0.95) & (cen[:, 1] < 0.13) & (cen[:, 1] > 0.08)      # the full-length floor / fender plate
            low = (V[Fm][:, :, 1].max(1) < 0.125) & (np.abs(cen[:, 0]) < 1.2)
            parts['hull_main'] = Fm[~low & ~floor]
            parts['floor'] = Fm[floor]
    for obj in DARK_OBJS:
        if obj in objs: parts['dark_' + obj[5:9]] = np.array([f for f, m in objs[obj]])[:, [0, 2, 1]]
    # the lower front plate's foot: from the model's nose (y 0.11, z 2.29) back to the game's cover lip
    used = np.zeros(len(V), bool); used[np.unique(np.vstack([parts['hull_main'], parts['hull_fc']]))] = True
    foot = used & (V[:, 2] > 2.2) & (V[:, 1] < 0.2) & (np.abs(V[:, 0]) < 1.1)
    V = V.copy(); V[foot, 1] = LIP[0]; V[foot, 2] = LIP[1]
    return V, parts

def part(V, F):
    """compact (V, F) of one part"""
    ids, inv = np.unique(F, return_inverse=True); return V[ids], inv.reshape(F.shape)

def dedupe(V, F):
    """drop faces whose reversed copy is present (double-sided plates), keeping the outward one of each pair"""
    key = {}
    for k, f in enumerate(F):
        s = tuple(sorted(f)); key.setdefault(s, []).append(k)
    keep = np.ones(len(F), bool); cen = V[F].mean(1); n = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    c0 = V[np.unique(F)].mean(0)
    for s, ks in key.items():
        if len(ks) < 2: continue
        # keep the face whose normal points away from the part's centre
        best = max(ks, key=lambda k: n[k] @ (cen[k] - c0));
        for k in ks:
            if k != best: keep[k] = False
    return F[keep]

if __name__ == '__main__':
    import sys
    V, parts = load(sys.argv[1])
    for k, F in parts.items():
        P = V[np.unique(F)]; print('%-14s %4d tris  x %5.2f..%5.2f y %5.2f..%5.2f z %5.2f..%5.2f' % (k, len(F), *P.min(0)[[0]], *P.max(0)[[0]], *P.min(0)[[1]], *P.max(0)[[1]], *P.min(0)[[2]], *P.max(0)[[2]]))

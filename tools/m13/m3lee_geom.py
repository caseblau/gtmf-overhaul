"""Geometry added to the user's reference M3 model (m3lee_obj.py) for the Lee's game mesh, and the rivet rows.

Frame: the game's vehicle frame (x right, y up, z forward, metres). Ground at y -1.149 (add-ins at (0, 0, 0.15)).
The reference model's own floor plate (y 0.09 .. 0.12, full width, with its nose) is dropped: the game's M4A2 lower
hull (top y 0.123, x +-0.777) and transmission cover (top lip y 0.147 at z 2.14) take its place. What is left of the
reference's sponsons is open underneath, so the sponson floors / mudguards are added here, flush with the cover's lip.
"""
import numpy as np
from geom import revolve, box, merge
import geom

FLOOR_Y = (0.112, 0.147)            # the sponson floor / mudguard plates: underside, top (= the transmission cover's lip)
FLOOR_X = (0.76, 1.262)             # from inside the lower hull's wall (x 0.777) to inside the side plates (1.266)
FLOOR_Z = (-2.45, 2.43)             # the reference's floor plate: rear edge / the side plates' front-bottom corners
NOSE = [(1.262, 2.43), (1.12, 2.593), (1.01, 2.72), (0.76, 2.72)]      # the mudguards' chamfered front corners (the reference's nose outline)
RECESS = dict(x=(0.437, 0.76), z=(1.30, 2.14))   # the 75 mm sponson's floor ahead of its front plate, back from the cover's lip

def _hull(P):
    from scipy.spatial import ConvexHull
    P = np.asarray(P, float); h = ConvexHull(P); F = []
    for sx, eq in zip(h.simplices, h.equations):
        a, b, c = P[sx]
        if np.dot(np.cross(b - a, c - a), eq[:3]) < 0: sx = sx[[0, 2, 1]]
        F.append(sx)
    return P, np.array(F)

def _prism(xz, y0, y1):
    return _hull([(x, y, z) for x, z in xz for y in (y0, y1)])

def floors():
    """the sponson floors with the front mudguards (both sides) and the 75 mm recess's floor"""
    y0, y1 = FLOOR_Y; out = []
    for s in (-1, 1):
        xz = [(s * FLOOR_X[0], FLOOR_Z[0]), (s * FLOOR_X[1], FLOOR_Z[0])] + [(s * x, z) for x, z in NOSE]
        out.append(_prism(xz, y0, y1))
    (x0, x1), (z0, z1) = RECESS['x'], RECESS['z']
    out.append(_prism([(x0, z0), (x1, z0), (x1, z1), (x0, z1)], y0, y1))
    return merge(*out)

# ---------------------------------------------------------------- hatch openings (the reference's plates are solid under its hatches)
def _x2(a, b): return a[0] * b[1] - a[1] * b[0]

def _clip(poly, p, n):
    """Sutherland-Hodgman: keep the part of the 2D polygon with (x - p) . n >= 0"""
    out = []
    for i in range(len(poly)):
        a, b = poly[i - 1], poly[i]; da, db = (a - p) @ n, (b - p) @ n
        if db >= 0:
            if da < 0: out.append(a + (b - a) * da / (da - db))
            out.append(b)
        elif da >= 0: out.append(a + (b - a) * da / (da - db))
    return out

def cut_hole(V, F, normal, hole, tol=0.02):
    """cut a convex opening through every face of (V, F) lying in the hole's plane: `hole` = its corners (3D, in order,
    on the plate); the faces overlapping it are replaced by their parts outside it (each kept in its own plane)"""
    n0 = np.asarray(normal, float); n0 /= np.linalg.norm(n0); H = np.asarray(hole, float); c0 = H.mean(0)
    u = np.cross(n0, [0, 1.0, 0] if abs(n0[1]) < 0.9 else [1.0, 0, 0]); u /= np.linalg.norm(u); v = np.cross(n0, u)
    def uv(P): return np.c_[P @ u, P @ v]
    H2 = uv(H); hc = H2.mean(0)
    edges = []                                   # (point, inward normal) of the hole's sides
    for i in range(len(H2)):
        a, b = H2[i], H2[(i + 1) % len(H2)]; e = b - a; m = np.array([-e[1], e[0]])
        if (hc - a) @ m < 0: m = -m
        edges.append((a, m / np.linalg.norm(m)))
    n = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]); n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    cen = V[F].mean(1)
    sel = (np.abs(n @ n0) > 0.995) & (np.abs((cen - c0) @ n0) < tol)
    keep = [f for f, s_ in zip(F, sel) if not s_]; newV = [V]; off = len(V); newF = []
    for f in F[sel]:
        T = V[f]; T2 = uv(T); area0 = _x2(T2[1] - T2[0], T2[2] - T2[0])
        # the triangle minus the hole: for each side i the part outside side i and inside sides 0..i-1
        for i, (a, m) in enumerate(edges):
            piece = _clip([T2[0], T2[1], T2[2]], a, -m)
            for a2, m2 in edges[:i]:
                if len(piece) > 2: piece = _clip(piece, a2, m2)
            if len(piece) < 3: continue
            P2 = np.array(piece); P3 = T[0] + (P2[:, 0] - T2[0, 0])[:, None] * u + (P2[:, 1] - T2[0, 1])[:, None] * v
            newV.append(P3)
            for k in range(1, len(P3) - 1):
                tri = [off, off + k, off + k + 1]
                if _x2(P2[k] - P2[0], P2[k + 1] - P2[0]) * area0 < 0: tri = [off, off + k + 1, off + k]
                if abs(_x2(P2[k] - P2[0], P2[k + 1] - P2[0])) > 1e-7: newF.append(tri)
            off += len(P3)
    if not sel.any(): raise ValueError('no faces in the hole plane')
    return np.vstack(newV), np.array(keep + newF, int)

def hole_rim(normal, hole, depth):
    """the dark inside of an opening: walls going `depth` in from the hole's edge and a floor, facing the viewer outside"""
    n0 = np.asarray(normal, float); n0 /= np.linalg.norm(n0); H = np.asarray(hole, float); k = len(H); c = H.mean(0)
    V = np.vstack([H, H - n0 * depth]); F = []
    for i in range(k):
        j = (i + 1) % k; F += [[i, j, k + j], [i, k + j, k + i]]
    F += [[k, k + i, k + i + 1] for i in range(1, k - 1)]
    F = np.array(F); T = V[F]; nf = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); cen = T.mean(1)
    want = np.where((np.arange(len(F)) < 2 * k)[:, None], (c - n0 * depth / 2) - cen, np.tile(n0, (len(F), 1)))   # walls look to the axis, the floor out
    flip = np.einsum('ij,ij->i', nf, want) < 0; F[flip] = F[flip][:, [0, 2, 1]]
    return V, F

def rect3(axis, lo, hi, const):
    """a rectangle in the plane `axis` = const: (lo, hi) over the two other axes"""
    o = [i for i in range(3) if i != axis]; P = []
    for a, b in ((lo[0], lo[1]), (hi[0], lo[1]), (hi[0], hi[1]), (lo[0], hi[1])):
        p = [0.0, 0.0, 0.0]; p[axis] = const; p[o[0]] = a; p[o[1]] = b; P.append(p)
    return np.array(P)

def circle3(c, r, y, seg=16):
    a = np.linspace(0, 2 * np.pi, seg, endpoint=False); return np.c_[c[0] + r * np.cos(a), np.full(seg, y), c[1] + r * np.sin(a)]

def rod(p, q, r=0.009, seg=6):
    p, q = np.asarray(p, float), np.asarray(q, float); d = q - p; L = np.linalg.norm(d)
    return revolve([(0, r), (L, r)], p, d / L, seg=seg)

def gun_sleeve(z0, z1, r=0.11, seg=16):
    """the 75 mm's elevating sleeve inside the traversing rotor (hidden; gives d_gunmask_02 its shape and hit box)"""
    return revolve([(z0, 0.0), (z0, r), (z1, r), (z1, 0.0)], (0, 0, 0), (0, 0, 1.0), seg=seg)

# ---------------------------------------------------------------- rivets
RIVET_PITCH = 0.09
def rivet_mesh(pts, nrms, r=0.02, h=0.012):
    """six-sided rivet heads at pts, standing on the surface with normals nrms"""
    V = []; F = []
    for p, n in zip(pts, nrms):
        n = np.asarray(n, float); n = n / np.linalg.norm(n)
        u = np.cross(n, [0, 1.0, 0] if abs(n[1]) < 0.9 else [1.0, 0, 0]); u /= np.linalg.norm(u); v = np.cross(n, u)
        b = len(V)
        for k in range(6):
            a = np.pi / 3 * k; V.append(p - n * 0.002 + r * (np.cos(a) * u + np.sin(a) * v))
        V.append(p + n * h)
        F += [[b + k, b + (k + 1) % 6, b + 6] for k in range(6)]
    if not V: return np.zeros((0, 3)), np.zeros((0, 3), int)
    V = np.array(V); F = np.array(F)
    T = V[F]; nr = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); ref = np.repeat(np.asarray(nrms, float), 6, axis=0)
    flip = np.einsum('ij,ij->i', nr, ref) < 0; F[flip] = F[flip][:, [0, 2, 1]]
    return V, F

def _row(p, q, pitch=RIVET_PITCH, end=0.05):
    """rivet centres along p -> q, keeping `end` clear of both ends"""
    p, q = np.asarray(p, float), np.asarray(q, float); d = q - p; L = np.linalg.norm(d)
    if L < 2 * end + 0.02: return np.zeros((0, 3))
    k = max(int(round((L - 2 * end) / pitch)), 1); t = np.linspace(end, L - end, k + 1) if k > 1 else np.array([L / 2])
    return p + d / L * t[:, None]

def seam_rivets(V, F, pitch=RIVET_PITCH, inset=0.04, min_area=0.02, min_len=0.18, angles=(22.0, 125.0)):
    """rivet rows along the seams of a riveted plate hull: every edge shared by two large faces meeting at an angle
    (a plate joint) gets a row on each plate, `inset` in from the edge"""
    key = np.round(V, 4); _, inv = np.unique(key, axis=0, return_inverse=True); inv = inv.ravel(); Fw = inv[F]
    n = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]); area = np.linalg.norm(n, axis=1) / 2
    n = n / np.maximum(2 * area[:, None], 1e-12)
    edges = {}
    for k, f in enumerate(Fw):
        for i in range(3):
            a, b = f[i], f[(i + 1) % 3]
            edges.setdefault((min(a, b), max(a, b)), []).append((k, i))
    pts, nrms = [], []
    for (a, b), fs in edges.items():
        if len(fs) != 2: continue
        (k1, i1), (k2, i2) = fs
        if area[k1] < min_area or area[k2] < min_area: continue
        p0, p1 = V[F[k1][i1]], V[F[k1][(i1 + 1) % 3]]; e = p1 - p0; L = np.linalg.norm(e)
        if L < min_len: continue
        ang = np.degrees(np.arccos(np.clip(n[k1] @ n[k2], -1, 1)))
        if not (angles[0] <= ang <= angles[1]): continue
        for k, i in fs:
            third = V[F[k][(i + 2) % 3]]; d = np.cross(n[k], e / L)
            if d @ (third - p0) < 0: d = -d
            row = _row(p0 + d * inset, p1 + d * inset, pitch)
            pts.append(row); nrms.append(np.tile(n[k], (len(row), 1)))
    if not pts: return np.zeros((0, 3)), np.zeros((0, 3), int)
    return rivet_mesh(np.vstack(pts), np.vstack(nrms))

def ring_rivets(c, r, y, pitch=0.10):
    """a ring of rivets (bolt heads) on a horizontal plate: the round roof plate's bolt circle"""
    k = max(int(round(2 * np.pi * r / pitch)), 6); a = np.linspace(0, 2 * np.pi, k, endpoint=False)
    pts = np.c_[c[0] + r * np.sin(a), np.full(k, y), c[1] + r * np.cos(a)]
    return rivet_mesh(pts, np.tile([0, 1.0, 0], (k, 1)))

# ---------------------------------------------------------------- 4 Nov (user: "there is a hole in the back"): the
# reference hull ends at the rear in a plate whose lower edge is y 0.29 at z -2.78 (x +-0.76), while the game's M4A2 belly
# (add-in M4A2_BOTTOM on d_bottom) ends 0.21 m lower and 0.27 m further forward (top edge y 0.08 at z -2.51): from behind
# and below one looked into the empty hull between them. A sloped 13 mm lower rear plate now closes it, as on the M3.
REAR_LOWER = dict(top=(0.30, -2.785), bot=(0.02, -2.46), hw_top=0.775, hw_bot=0.82, t=0.013)

def rear_lower_plate():
    r = REAR_LOWER; (yt, zt), (yb, zb) = r['top'], r['bot']
    pts = [[-r['hw_top'], yt, zt], [r['hw_top'], yt, zt], [-r['hw_bot'], yb, zb], [r['hw_bot'], yb, zb]]
    e = np.array([0.0, yt - yb, zt - zb]); n = np.array([0.0, e[2], -e[1]]); n /= np.linalg.norm(n)
    if n[2] > 0: n = -n                                                     # outward = rearward and down
    P = np.asarray(pts, float); c = P.mean(0); d = n @ P[0]
    planes = [(n, d), (-n, -(d - r['t']))]
    s = np.array([1.0, 0, 0]); u = np.cross(n, s)
    q = np.c_[(P - c) @ s, (P - c) @ u]; Q = P[np.argsort(np.arctan2(q[:, 1], q[:, 0]))]
    for i in range(len(Q)):
        a, b = Q[i], Q[(i + 1) % len(Q)]; e2 = np.cross(b - a, n); e2 /= np.linalg.norm(e2)
        if e2 @ (c - a) > 0: e2 = -e2
        planes.append((e2, e2 @ a))
    return geom.polytope(planes, c - n * r['t'] / 2)

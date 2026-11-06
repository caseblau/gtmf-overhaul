"""small procedural geometry kit for the M13 vehicles: convex polytopes from planes, revolved solids, boxes.
Every mesh is (V (n,3) float, F (m,3) int) with outward winding (counter-clockwise seen from outside)."""
import numpy as np
from scipy.spatial import HalfspaceIntersection, ConvexHull

def polytope(planes, interior):
    """planes: list of (normal (3,), d) meaning n.x <= d. Returns a convex mesh, flat faces triangulated."""
    hs = np.array([list(n) + [-d] for n, d in planes], float)
    pts = HalfspaceIntersection(hs, np.asarray(interior, float)).intersections
    hull = ConvexHull(pts)
    F = []
    for s, eq in zip(hull.simplices, hull.equations):
        a, b, c = pts[s]
        if np.dot(np.cross(b - a, c - a), eq[:3]) < 0: s = s[[0, 2, 1]]
        F.append(s)
    return pts, np.array(F)

def revolve(profile, axis_origin, axis_dir, seg=16, cap_start=True, cap_end=True):
    """profile: [(t, r), ...] along the axis; returns a closed solid of revolution"""
    o = np.asarray(axis_origin, float); a = np.asarray(axis_dir, float); a /= np.linalg.norm(a)
    u = np.cross(a, [0, 1, 0] if abs(a[1]) < 0.9 else [1, 0, 0]); u /= np.linalg.norm(u); v = np.cross(a, u)
    V = []; F = []
    for t, r in profile:
        for k in range(seg):
            ang = 2 * np.pi * k / seg
            V.append(o + a * t + r * (np.cos(ang) * u + np.sin(ang) * v))
    n = len(profile)
    for i in range(n - 1):
        for k in range(seg):
            p0 = i * seg + k; p1 = i * seg + (k + 1) % seg; q0 = p0 + seg; q1 = p1 + seg
            F += [[p0, q0, q1], [p0, q1, p1]]
    V = np.array(V)
    if cap_start:
        c = len(V); V = np.vstack([V, o + a * profile[0][0]])
        F += [[c, k, (k + 1) % seg] for k in range(seg)]   # 3 Nov: the caps were wound against the sides (inward after the
                                                              # outward flip below) - back-face culled in game: every revolved
                                                              # part (fuel tanks, rolls, silencers, bolts) showed open ends
    if cap_end:
        c = len(V); V = np.vstack([V, o + a * profile[-1][0]]); b = (n - 1) * seg
        F += [[c, b + (k + 1) % seg, b + k] for k in range(seg)]
    F = np.array(F)
    # make winding outward
    cen = V.mean(0); tri = V[F]; nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    if np.mean(np.einsum('ij,ij->i', nrm, tri.mean(1) - cen)) < 0: F = F[:, [0, 2, 1]]
    return V, F

def box(c, size, R=np.eye(3)):
    c = np.asarray(c, float); h = np.asarray(size, float) / 2
    planes = []
    for ax in range(3):
        n = R[:, ax]
        planes += [(n, n @ c + h[ax]), (-n, -(n @ c) + h[ax])]
    return polytope(planes, c)

def merge(*meshes):
    V = []; F = []; o = 0
    for v, f in meshes:
        V.append(v); F.append(f + o); o += len(v)
    return np.vstack(V), np.vstack(F)

def flat(V, F):
    """unshare vertices so each triangle gets its own flat normal (game meshes are faceted this way)"""
    V2 = V[F].reshape(-1, 3); F2 = np.arange(len(V2)).reshape(-1, 3)
    return V2, F2

def normals(V, F):
    t = V[F]; n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]); n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    return n

def write_obj(path, parts):
    """parts: list of (name, V, F)"""
    with open(path, 'w') as f:
        o = 1
        for name, V, F in parts:
            f.write('o %s\n' % name)
            for x, y, z in V: f.write('v %.5f %.5f %.5f\n' % (x, y, -z))
            for a, b, c in F + o: f.write('f %d %d %d\n' % (a, c, b))
            o += len(V)

def _clip_poly(poly, n, d, keep_inside):
    """Sutherland-Hodgman on one plane. poly: list of attribute vectors whose first 3 entries are xyz."""
    out = []
    def inside(v): return (v[:3] @ n <= d) if keep_inside else (v[:3] @ n > d)
    for i in range(len(poly)):
        a = poly[i]; b = poly[(i + 1) % len(poly)]
        ia, ib = inside(a), inside(b)
        if ia: out.append(a)
        if ia != ib:
            da = a[:3] @ n - d; db = b[:3] @ n - d
            t = da / (da - db); out.append(a + (b - a) * t)
    return out

def subtract_convex(A, F, planes, eps=1e-6):
    """remove the part of a triangle mesh lying inside a convex polytope (planes n.x <= d).
    A: (n, k) per-vertex attributes, xyz first (other attributes are interpolated linearly).
    Returns (A2, F2): untouched triangles keep their vertices, cut ones are re-triangulated."""
    P = A[:, :3]
    newA = [A]; newF = []; base = len(A)
    for tri in F:
        pts = P[tri]
        ins = np.array([[p @ n <= d + eps for n, d in planes] for p in pts])   # (3, nplanes)
        if not np.any(np.all(ins, 0) == False) or np.all(ins.all(1)):           # all three inside every plane
            if np.all(ins.all(1)): continue
        # fully outside one plane -> untouched
        if np.any((~ins).all(0)): newF.append(tri); continue
        poly = [A[i].astype(float) for i in tri]
        rest = poly
        for n, d in planes:
            if len(rest) < 3: break
            out = _clip_poly(rest, np.asarray(n), d, keep_inside=False)
            if len(out) >= 3:
                verts = np.array(out); o = base; newA.append(verts); base += len(verts)
                newF += [[o, o + j, o + j + 1] for j in range(1, len(verts) - 1)]
            rest = _clip_poly(rest, np.asarray(n), d, keep_inside=True)
    return np.vstack(newA), np.array(newF, int)

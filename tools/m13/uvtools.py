"""UV mapping for the new SU-122 parts.

plate_uv: flat armour parts get real-scale UVs on a plain plate area of the T-34 texture. Each plate is projected on its
own plane (texture 'up' = up the plate), cut into cells the size of the source rectangle and every cell is mapped onto
the rectangle, so the texel density is the same everywhere (the old mapping stretched every face over a whole strip).
cyl_uv: bodies of revolution (cap, fuel tanks) get a wrapped cylindrical mapping.
smooth_normals: per-vertex normals for curved parts, so they shade round instead of faceted.
"""
import numpy as np
import geom

def plate_basis(n):
    n = np.asarray(n, float); n = n / np.linalg.norm(n)
    up = np.array([0, 1.0, 0]) if abs(n[1]) < 0.9 else np.array([0, 0, 1.0])
    t = up - n * (up @ n); t /= np.linalg.norm(t)
    s = np.cross(t, n); s /= np.linalg.norm(s)
    return s, t

def _clip(poly, axis, val, keep_greater):
    """Sutherland-Hodgman on a polygon of (a, b, x, y, z) rows against a = val or b = val"""
    out = []
    for i in range(len(poly)):
        P, Q = poly[i], poly[(i + 1) % len(poly)]
        pin = (P[axis] >= val) if keep_greater else (P[axis] <= val)
        qin = (Q[axis] >= val) if keep_greater else (Q[axis] <= val)
        if pin: out.append(P)
        if pin != qin:
            t = (val - P[axis]) / (Q[axis] - P[axis]); out.append(P + t * (Q - P))
    return out

def plate_uv(V, F, rect, scale, normal_tol=0.999, jitter=True):
    """returns Vo (n,3), Fo (m,3), UV (n,2): flat, unshared vertices; faces split at cell borders"""
    u0, v0, u1, v1 = rect; cw, ch = (u1 - u0) / scale, (v1 - v0) / scale        # cell size in metres
    n = geom.normals(V, F)
    Vo = []; UV = []; Fo = []
    for k, f in enumerate(F):
        if not np.isfinite(n[k]).all() or np.linalg.norm(n[k]) < 0.5: continue
        s, t = plate_basis(n[k])
        P = V[f]; a = P @ s; b = P @ t
        poly0 = [np.r_[a[i], b[i], P[i]] for i in range(3)]
        ia = range(int(np.floor(a.min() / cw)), int(np.floor(a.max() / cw)) + 1)
        ib = range(int(np.floor(b.min() / ch)), int(np.floor(b.max() / ch)) + 1)
        # per-plate offset so different plates do not start on the same texel (less visible repetition)
        off = ((abs(n[k][0]) * 0.37 + abs(n[k][2]) * 0.61) % 1.0) * cw * 0.5 if jitter else 0.0
        for i in ia:
            for j in ib:
                poly = poly0
                for axis, val, g in ((0, i * cw, True), (0, (i + 1) * cw, False), (1, j * ch, True), (1, (j + 1) * ch, False)):
                    if len(poly) < 3: break
                    poly = _clip(poly, axis, val, g)
                if len(poly) < 3: continue
                pts = np.array(poly)
                la = pts[:, 0] - i * cw; lb = pts[:, 1] - j * ch
                if i % 2: la = cw - la                    # mirrored tiling: neighbouring cells meet edge to edge,
                if j % 2: lb = ch - lb                    # so there is no visible seam in the weathering
                uv = np.c_[u0 + la * scale, v1 - lb * scale]
                uv[:, 0] = np.clip(uv[:, 0], u0, u1); uv[:, 1] = np.clip(uv[:, 1], v0, v1)
                base = len(Vo)
                for p, q in zip(pts, uv): Vo.append(p[2:]); UV.append(q)
                for m in range(1, len(pts) - 1):
                    tri = [base, base + m, base + m + 1]
                    e = np.cross(pts[m, 2:] - pts[0, 2:], pts[m + 1, 2:] - pts[0, 2:])
                    if np.linalg.norm(e) < 1e-10: continue
                    if e @ n[k] < 0: tri = [base, base + m + 1, base + m]
                    Fo.append(tri)
    Vo = np.array(Vo); UV = np.array(UV); Fo = np.array(Fo, int)
    # unshare (one vertex per corner, the game meshes are faceted)
    return Vo[Fo].reshape(-1, 3), np.arange(Fo.size).reshape(-1, 3), UV[Fo].reshape(-1, 2)

def cyl_uv(V, F, origin, axis, rect, h0=None, h1=None):
    """wrapped cylindrical mapping about an axis; returns flat Vo, Fo, UV"""
    o = np.asarray(origin, float); a = np.asarray(axis, float); a /= np.linalg.norm(a)
    e1 = np.cross(a, [0, 1.0, 0] if abs(a[1]) < 0.9 else [1.0, 0, 0]); e1 /= np.linalg.norm(e1); e2 = np.cross(a, e1)
    u0, v0, u1, v1 = rect
    Vo = V[F].reshape(-1, 3); d = Vo - o
    h = d @ a; ang = np.arctan2(d @ e2, d @ e1) / (2 * np.pi) % 1.0
    ang = ang.reshape(-1, 3)
    for r in ang:                                   # seam: keep each triangle's angles together
        if r.max() - r.min() > 0.5: r[r < 0.5] += 1.0
    ang = ang.ravel() / 2.0                         # 0..1 -> half the rectangle width per turn, the rest wraps below
    h0 = h.min() if h0 is None else h0; h1 = h.max() if h1 is None else h1
    UV = np.c_[u0 + np.clip(ang, 0, 1) * (u1 - u0), v0 + (h - h0) / max(h1 - h0, 1e-6) * (v1 - v0)]
    return Vo, np.arange(len(Vo)).reshape(-1, 3), UV

def smooth_normals(V, F, Vo, crease_deg=50.0):
    """per flat vertex: average of the normals of the faces sharing that corner position, within a crease angle"""
    n = geom.normals(V, F); key = {}
    for k, f in enumerate(F):
        for i in f: key.setdefault(tuple(np.round(V[i], 5)), []).append(k)
    out = np.zeros((len(F) * 3, 3)); c = np.cos(np.radians(crease_deg))
    for k, f in enumerate(F):
        for m, i in enumerate(f):
            fs = key[tuple(np.round(V[i], 5))]; acc = np.zeros(3)
            for g in fs:
                if n[g] @ n[k] >= c: acc += n[g]
            out[3 * k + m] = acc / (np.linalg.norm(acc) + 1e-12)
    return out

def box_uv(V, F, rect, scale):
    """triplanar-style mapping for compact curved parts: each face is projected along its dominant normal axis, in metres
    from the part's bounding-box corner; avoids the swirl a cylindrical mapping makes on a flat-topped casting"""
    u0, v0, u1, v1 = rect; n = geom.normals(V, F); lo = V.min(0)
    Vo = V[F].reshape(-1, 3); UV = np.zeros((len(Vo), 2))
    for k in range(len(F)):
        ax = int(np.argmax(np.abs(n[k])))
        a, b = [(2, 1), (0, 2), (0, 1)][ax]                 # x-facing: (z, y); y-facing: (x, z); z-facing: (x, y)
        p = Vo[3 * k:3 * k + 3] - lo
        UV[3 * k:3 * k + 3] = np.c_[p[:, a] * scale, p[:, b] * scale]
    # mirrored repeat inside the rectangle (no clamped, stretched strips)
    W, H = u1 - u0, v1 - v0
    def mirror(x, L):
        m = np.mod(x, 2 * L); return np.where(m > L, 2 * L - m, m)
    UV = np.c_[u0 + mirror(UV[:, 0], W), v1 - mirror(UV[:, 1], H)]
    return Vo, np.arange(len(Vo)).reshape(-1, 3), UV

def smooth_flat(Vo, Fo, crease_deg=40.0):
    """smooth normals for already-unshared vertices (e.g. plate_uv output): corners at the same position share the
    average of the face normals within the crease angle"""
    n = geom.normals(Vo, Fo); c = np.cos(np.radians(crease_deg)); key = {}
    for k, f in enumerate(Fo):
        for i in f: key.setdefault(tuple(np.round(Vo[i], 4)), []).append(k)
    N = np.zeros((len(Vo), 3))
    for k, f in enumerate(Fo):
        for i in f:
            acc = np.zeros(3)
            for g in key[tuple(np.round(Vo[i], 4))]:
                if n[g] @ n[k] >= c: acc += n[g]
            N[i] = acc / (np.linalg.norm(acc) + 1e-12)
    return N

def sweep_uv(V, F, origin, axis, rect, scale, mode='prism', cap_thresh=0.7, seam_dir=(0, -1.0, 0)):
    """texture mapping for castings that are prisms or bodies of revolution, so the texture's vertical weathering streaks
    run DOWN the surface everywhere (box_uv flips them between faces and makes 'wood grain' rings on curved parts).
    mode 'prism' (a section swept along `axis`): side faces get u = position along the axis, v = arc length round the
    axis; mode 'revolve' (a surface of revolution about `axis`): side faces get u = position along the axis, v = arc
    length round it at the vertex's own radius. Faces whose normal is within acos(cap_thresh) of the axis (end faces)
    get a planar projection. The angular seam is put in `seam_dir` (hidden underneath). Returns flat Vo, Fo, UV."""
    o = np.asarray(origin, float); a = np.asarray(axis, float); a /= np.linalg.norm(a)
    sd = np.asarray(seam_dir, float); sd = sd - a * (sd @ a); sd /= np.linalg.norm(sd)
    e2 = -sd; e1 = np.cross(e2, a)                     # e2 points away from the seam (up), e1 completes the frame
    n = geom.normals(V, F); u0, v0, u1, v1 = rect
    Vo = V[F].reshape(-1, 3); d = Vo - o
    along = d @ a; p1, p2 = d @ e1, d @ e2
    ang = np.arctan2(p1, p2)                            # 0 = away from the seam, +-pi at the seam
    rad = np.hypot(p1, p2)
    Rref = np.median(rad)
    UV = np.zeros((len(Vo), 2))
    for k in range(len(F)):
        sl = slice(3 * k, 3 * k + 3)
        if abs(n[k] @ a) >= cap_thresh:                 # end face: planar
            UV[sl] = np.c_[p1[sl], -p2[sl]]
        else:
            t = ang[sl].copy()
            if t.max() - t.min() > np.pi: t[t < 0] += 2 * np.pi
            r = rad[sl] if mode == 'revolve' else np.full(3, Rref)
            UV[sl] = np.c_[along[sl], t * r]
    UV *= scale
    W, H = u1 - u0, v1 - v0
    def mirror(x, L):
        m = np.mod(x, 2 * L); return np.where(m > L, 2 * L - m, m)
    UV = np.c_[u0 + mirror(UV[:, 0], W), v0 + mirror(UV[:, 1], H)]
    return Vo, np.arange(len(Vo)).reshape(-1, 3), UV

"""Shared code for the user's purchased vehicle models (9 Nov): OBJ with UVs and normals -> game frame, parts by connected
component, atlas UVs, welded game vertices, and the DXT1 / DXT5 texture pair built from the model's PBR maps.

The models themselves are licensed to the user: they are read from outside the repository and neither they nor the meshes
and textures made from them are committed or published (src\\m13_vehicles\\mfo_gos is gitignored for the meshes; the
textures are added to .gitignore too).

Frames: the OBJs are right-handed, y up, z forward; the game is left-handed with x to the vehicle's right, so x changes
sign and the windings reverse.  That is a change of frame, not a mirror: the vehicle stays the same way round.
"""
import os, sys
import numpy as np
from PIL import Image
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import su122_mesh as SM
import su76_texture as ST
Image.MAX_IMAGE_PIXELS = None


class Part:
    """triangles as corners: P (m,3,3) positions, T (m,3,2) atlas uv, N (m,3,3) normals"""
    def __init__(self, P, T, N):
        self.P, self.T, self.N = P, T, N

    def __len__(self): return len(self.P)

    def lo(self): return self.P.reshape(-1, 3).min(0)

    def hi(self): return self.P.reshape(-1, 3).max(0)

    def centre(self): return (self.lo() + self.hi()) / 2

    def sub(self, mask): return Part(self.P[mask], self.T[mask], self.N[mask])

    def moved(self, pivot, R=None):
        P = self.P - np.asarray(pivot, float); N = self.N
        if R is not None: P = P @ np.asarray(R, float).T; N = N @ np.asarray(R, float).T
        return Part(P, self.T, N)

    def gxt(self):
        """game vertices (welded) and faces"""
        if not len(self.P): return None, None
        Vf = self.P.reshape(-1, 3); Tf = self.T.reshape(-1, 2); Nf = self.N.reshape(-1, 3); Fo = np.arange(len(Vf)).reshape(-1, 3)
        A, F = SM.new_gxt(Vf, Fo, Tf, Nf)
        return weld(A, F)

    def plain(self):
        """(V, F) without UVs (hit meshes)"""
        Vf = self.P.reshape(-1, 3); return Vf, np.arange(len(Vf)).reshape(-1, 3)


def join(parts):
    parts = [p for p in parts if p is not None and len(p)]
    return Part(np.vstack([p.P for p in parts]), np.vstack([p.T for p in parts]), np.vstack([p.N for p in parts]))


def weld(A, F):
    """merge vertices with the same position, uv and normal (the 16-bit index limit counts vertices); tangents are per face, the first one stays"""
    # 9 Nov: the tangent frame is part of the key (signs of tangent and binormal, coarsely): merging only on position / uv / normal
    # gave faces of mirrored uv islands the neighbour's frame, and the game drew their bump black (the IS-2's black wedges)
    hand = np.sign(np.sum(np.cross(A[:, 5:8], A[:, 8:11]) * A[:, 11:14], 1)); tq = np.argmax(np.abs(A[:, 8:11]), 1) * 2 + (np.take_along_axis(A[:, 8:11], np.argmax(np.abs(A[:, 8:11]), 1)[:, None], 1)[:, 0] > 0)
    key = np.c_[np.round(A[:, :8], 3), hand, tq]; _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True); inv = inv.ravel()
    return A[first], inv[F]


def cat(lst):
    As, Fs, o = [], [], 0
    for A, F in lst:
        if A is None or not len(F): continue
        As.append(A); Fs.append(F + o); o += len(A)
    return (np.vstack(As), np.vstack(Fs)) if As else None


def load_obj(path, to_game, atlas, wanted=None):
    """{object name: Part}.  to_game: (n,3) raw -> game frame positions (a translation / flip of x).  atlas: object name ->
    (u0, v0, w, h) rectangle, v measured down from the top of the atlas; texture coordinates wrap inside the rectangle."""
    V, VT, VN = [], [], []; objs = {}; cur = '_'
    for line in open(path, errors='replace'):
        t = line.split()
        if not t: continue
        if t[0] == 'v': V.append([float(a) for a in t[1:4]])
        elif t[0] == 'vt': VT.append([float(a) for a in t[1:3]])
        elif t[0] == 'vn': VN.append([float(a) for a in t[1:4]])
        elif t[0] in ('o', 'g'): cur = t[1]; objs.setdefault(cur, [])
        elif t[0] == 'f':
            q = []
            for a in t[1:]:
                b = a.split('/'); q.append((int(b[0]) - 1, int(b[1]) - 1 if len(b) > 1 and b[1] else 0, int(b[2]) - 1 if len(b) > 2 and b[2] else 0))
            for k in range(1, len(q) - 1): objs.setdefault(cur, []).append((q[0], q[k], q[k + 1]))
    V = to_game(np.array(V, float)); VT = np.array(VT, float); VN = np.array(VN, float) * [-1.0, 1.0, 1.0]
    VN /= np.maximum(np.linalg.norm(VN, axis=1, keepdims=True), 1e-9)
    out = {}
    for name, tris in objs.items():
        if not tris or (wanted and name not in wanted) or name not in atlas: continue
        f = np.array(tris)[:, [0, 2, 1]]            # windings reversed with the change of hand
        uv = VT[f[:, :, 1]].copy()
        uv -= np.floor(uv.mean(1, keepdims=True))   # wrapped islands back into the tile, face by face
        uv = np.clip(uv, 0.0, 1.0)
        u0, v0, w, h = atlas[name]
        T = np.stack([u0 + uv[:, :, 0] * w, v0 + (1.0 - uv[:, :, 1]) * h], -1)
        out[name] = Part(V[f[:, :, 0]], T, VN[f[:, :, 2]])
    return out


def components(p, digits=3):
    """component label per triangle (touching corners, rounded)"""
    pts = np.round(p.P.reshape(-1, 3), digits); _, inv = np.unique(pts, axis=0, return_inverse=True); inv = inv.ravel().reshape(-1, 3)
    m = inv.max() + 1
    g = coo_matrix((np.ones(3 * len(inv)), (np.r_[inv[:, 0], inv[:, 1], inv[:, 2]], np.r_[inv[:, 1], inv[:, 2], inv[:, 0]])), shape=(m, m))
    _, lab = connected_components(g, directed=False)
    return lab[inv[:, 0]]


def split(p):
    """[Part] per connected component, largest first"""
    lab = components(p); out = [p.sub(lab == u) for u in np.unique(lab)]
    return sorted(out, key=lambda q: -len(q))


def _clip(poly, f):
    """Sutherland-Hodgman: poly = [(p, t, n)], keeps f(p) <= 0, attributes interpolated"""
    out = []
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]; fa, fb = f(a[0]), f(b[0])
        if fa <= 0: out.append(a)
        if (fa <= 0) != (fb <= 0):
            s = fa / (fa - fb); out.append(tuple(x + (y - x) * s for x, y in zip(a, b)))
    return out


def ray_faces(p, o, d, t0, t1):
    """indices of p's faces hit by the ray o + t d, t0 < t < t1 (Moller-Trumbore), and the hit distances"""
    P = p.P; d = np.asarray(d, float); e1 = P[:, 1] - P[:, 0]; e2 = P[:, 2] - P[:, 0]; h = np.cross(d, e2); a = np.einsum('ij,ij->i', e1, h); ok = np.abs(a) > 1e-12
    f = np.where(ok, 1 / np.where(ok, a, 1), 0); s = np.asarray(o, float) - P[:, 0]; u = f * np.einsum('ij,ij->i', s, h); q = np.cross(s, e1)
    v = f * (q @ d); t = f * np.einsum('ij,ij->i', e2, q); m = ok & (u >= 0) & (u <= 1) & (v >= 0) & (u + v <= 1) & (t > t0) & (t < t1)
    return np.where(m)[0], t[m]


def recompute_normals(P, crease_deg=35.0):
    """per corner: area-weighted average of the normals of the faces meeting at that position within the crease angle.
    For reduced meshes (10 Nov, the IS-2): normals carried over from the detailed source tilt flat plates by 15 - 30 deg
    and shade whole triangles dark; normals rebuilt from the reduced faces keep plates flat and curves smooth."""
    P = np.asarray(P, float)
    if not len(P): return np.zeros((0, 3, 3))
    fn = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]); area = np.linalg.norm(fn, axis=1)
    un = fn / np.maximum(area, 1e-12)[:, None]; c = np.cos(np.radians(crease_deg))
    q = np.round(P.reshape(-1, 3), 4); _, inv = np.unique(q, axis=0, return_inverse=True); inv = inv.ravel()
    face = np.repeat(np.arange(len(P)), 3); order = np.argsort(inv, kind='stable'); out = np.zeros((len(P) * 3, 3))
    bounds = np.flatnonzero(np.r_[True, inv[order][1:] != inv[order][:-1], True])
    for a, b in zip(bounds[:-1], bounds[1:]):
        corners = order[a:b]; fs = face[corners]; nn = un[fs]; w = fn[fs]
        allv = w.sum(0); allv /= np.linalg.norm(allv) + 1e-12
        if (nn @ allv).min() >= c: out[corners] = allv; continue          # one smooth group: one shared normal (keeps vertices welded)
        m = (nn @ nn.T) >= c; acc = m @ w
        out[corners] = acc / (np.linalg.norm(acc, axis=1, keepdims=True) + 1e-12)
    return out.reshape(-1, 3, 3)


def hidden_faces(P, cone=0.5, chunk=256, min_hits=5):
    """faces that cannot be seen from outside their own part: rays from the face centre along the normal and four directions
    tilted by `cone` (radians) all hit the part again.  The inner walls of hollow parts (a fuel drum's shell, a plate's back
    side) - removed before mesh reduction, which otherwise lets them cross the outer skin and show through as dark wedges."""
    P = np.asarray(P, float); n = len(P)
    fn = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]); a = np.linalg.norm(fn, axis=1); fn = fn / np.maximum(a, 1e-12)[:, None]
    c = P.mean(1) + fn * 1e-4
    ref = np.where(np.abs(fn[:, :1]) < 0.9, np.array([[1.0, 0, 0]]), np.array([[0, 1.0, 0]])); u = np.cross(fn, ref); u /= np.linalg.norm(u, axis=1, keepdims=True) + 1e-12; v = np.cross(fn, u)
    dirs = [fn] + [fn * np.cos(cone) + s * np.sin(cone) for s in (u, -u, v, -v)]
    e1 = P[:, 1] - P[:, 0]; e2 = P[:, 2] - P[:, 0]; hits_n = np.zeros(n, int); first = None
    for j, d in enumerate(dirs):
        hit = np.zeros(n, bool)
        for s0 in range(0, n, chunk):
            o = c[s0:s0 + chunk, None, :]; dd = d[s0:s0 + chunk, None, :]
            h = np.cross(dd, e2[None]); det = np.einsum('rtj,tj->rt', h, e1); ok = np.abs(det) > 1e-12; f = np.where(ok, 1 / np.where(ok, det, 1), 0)
            s = o - P[None, :, 0]; uu = f * np.einsum('rtj,rtj->rt', s, h); q = np.cross(s, e1[None]); vv = f * np.einsum('rtj,rtj->rt', q, dd)
            t = f * np.einsum('rtj,tj->rt', q, e2); m = ok & (uu >= 0) & (uu <= 1) & (vv >= 0) & (uu + vv <= 1) & (t > 2e-4)
            hit[s0:s0 + chunk] = m.any(1)
        hits_n += hit
        if j == 0: first = hit
    # the straight-out ray blocked and min_hits of the 5 (5: strict; 3 also takes a tube's inner wall near its open ends, 10 Nov)
    return first & (hits_n >= min_hits) & (a > 1e-12)


def cut_rect(p, c, n, u, ha, hb, tol=0.02, only=None):
    """p with a rectangular hole: faces lying on the plane through c (normal n) within tol are cut along the rectangle
    |(x - c).u| <= ha, |(x - c).v| <= hb (v = n x u); what lies outside it stays, with its texture coordinates.  For an
    opening in a plate whose triangles are far larger than the opening (the M3 driver's visor)."""
    c, n, u = (np.asarray(x, float) for x in (c, n, u)); n = n / np.linalg.norm(n); u = u / np.linalg.norm(u); v = np.cross(n, u)
    d = np.abs((p.P - c) @ n).max(1); A = (p.P - c) @ u; Bv = (p.P - c) @ v
    hit = (d < tol) & (A.min(1) < ha) & (A.max(1) > -ha) & (Bv.min(1) < hb) & (Bv.max(1) > -hb)
    if only is not None: hit = np.zeros(len(p.P), bool); hit[only] = True      # the plate's faces, picked by the caller
    keep = p.sub(~hit); P, T, N = [keep.P], [keep.T], [keep.N]
    fa = lambda s, lim: (lambda x: s * ((x - c) @ u) - lim)      # keep s * a <= lim
    fb = lambda s, lim: (lambda x: s * ((x - c) @ v) - lim)
    for i in np.where(hit)[0]:
        tri = [(p.P[i, k], p.T[i, k], p.N[i, k]) for k in range(3)]
        regions = [[fa(1, -ha)], [fa(-1, -ha)], [fa(1, ha), fa(-1, ha), fb(1, -hb)], [fa(1, ha), fa(-1, ha), fb(-1, -hb)]]
        for fs in regions:                                          # left, right, then below and above the hole
            poly = tri
            for f in fs:
                poly = _clip(poly, f)
                if len(poly) < 3: break
            for k in range(1, len(poly) - 1):
                P.append(np.array([[poly[0][0], poly[k][0], poly[k + 1][0]]])); T.append(np.array([[poly[0][1], poly[k][1], poly[k + 1][1]]]))
                N.append(np.array([[poly[0][2], poly[k][2], poly[k + 1][2]]]))
    return Part(np.vstack(P), np.vstack(T), np.vstack(N)), int(hit.sum())


def dark_box(c, n, u, ha, hb, depth, uv):
    """an open box behind an opening, its faces turned inward: back wall and four sides in the dark uv spot, so a hole in a
    single-skin hull shows a dark inside (and whatever sits in it, the driver's head) instead of the far side of the tank"""
    c, n, u = (np.asarray(x, float) for x in (c, n, u)); n = n / np.linalg.norm(n); u = u / np.linalg.norm(u); v = np.cross(n, u)
    m = c - n * depth / 2
    parts = [quad(c - n * depth, u * ha, v * hb, n, uv),
             quad(m + u * ha, n * depth / 2, v * hb, -u, uv), quad(m - u * ha, n * depth / 2, v * hb, u, uv),
             quad(m + v * hb, n * depth / 2, u * ha, -v, uv), quad(m - v * hb, n * depth / 2, u * ha, v, uv)]
    return join(parts)


def quad(c, u, v, normal, uv):
    """a two-triangle plate on one uv point, facing `normal`: the dark insides under hatches"""
    c, u, v, n = (np.asarray(a, float) for a in (c, u, v, normal))
    a, b, d, e = c - u - v, c + u - v, c + u + v, c - u + v
    if np.cross(b - a, d - a) @ n < 0: b, e = e, b
    P = np.array([[a, b, d], [a, d, e]]); T = np.tile(uv, (2, 3, 1)); N = np.tile(n / np.linalg.norm(n), (2, 3, 1))
    return Part(P, T, N)


# ---------------------------------------------------------------- textures
def _load(path, n, mode='RGB'):
    return np.asarray(Image.open(path).convert(mode).resize(n, Image.LANCZOS), np.float32)


def clean_paint(d, lum_above=118.0):
    """paint out what is not the vehicle's base coat: the light sheet between the UV islands and the model's white bands, numbers and
    emblems, filled from the surrounding paint.  The game adds its own numbers; the light sheet would bleed into reduced faces."""
    from scipy.ndimage import gaussian_filter, binary_dilation
    lum = d.mean(2); red = (d[..., 0] > 1.35 * d[..., 1]) & (d[..., 0] > 70)
    bad = binary_dilation((lum > lum_above) | red, iterations=2); good = (~bad).astype(np.float32); out = d.copy()
    for sig in (3, 8, 24, 80):
        w = gaussian_filter(good, sig); ok = bad & (w > 0.02)
        for c in range(3):
            f = gaussian_filter(d[..., c] * good, sig) / np.maximum(w, 1e-4); out[..., c][ok] = f[ok]
        bad = bad & ~ok; good = np.where(ok, 1.0, good).astype(np.float32)
    if bad.any(): out[bad] = np.median(d[good > 0], axis=0)
    print('  painted out %.1f %% of the sheet' % (100.0 * (1.0 - float((~binary_dilation((lum > lum_above) | red, iterations=2)).mean()))))
    return out


def build_textures(layers, out_prefixes, dark_rect, ref_dift=None, N=2048, clean=False, match=50):
    """layers: [(rect, diffuse path, normal path, ao, rough)] with rect = (u0, v0, w, h) in the atlas; ao / rough are
    (path, channel).  Writes the DXT1 diffuse and the DXT5 normal + gloss pair: normal x in R, y in G, B 10 and gloss in A,
    as the game's own bump_*_norsp.  The diffuse is multiplied by the AO and scaled to ref_dift's mean brightness, so it
    sits with the game's own weathered vehicles."""
    dif = np.full((N, N, 3), 18.0, np.float32); nrm = np.zeros((N, N, 4), np.float32); nrm[..., 0] = nrm[..., 1] = 128.0; nrm[..., 2] = 10.0; nrm[..., 3] = 60.0
    used = np.zeros((N, N), bool)
    for rect, d_p, n_p, ao, ro in layers:
        x0, y0, w, h = int(rect[0] * N), int(rect[1] * N), int(rect[2] * N), int(rect[3] * N); size = (w, h)
        d = _load(d_p, size)
        if clean: d = clean_paint(d)
        occ = _load(ao[0], size, 'RGB')[..., ao[1]] / 255.0 if ao else 1.0
        dif[y0:y0 + h, x0:x0 + w] = d * (0.35 + 0.65 * occ)[..., None] if ao else d
        n_ = _load(n_p, size); r = _load(ro[0], size, 'RGB')[..., ro[1]] / 255.0 if ro else np.full(size[::-1], 0.6)
        nrm[y0:y0 + h, x0:x0 + w, 0] = n_[..., 0]; nrm[y0:y0 + h, x0:x0 + w, 1] = n_[..., 1]
        nrm[y0:y0 + h, x0:x0 + w, 3] = 100.0 + 100.0 * (1.0 - r)
        used[y0:y0 + h, x0:x0 + w] = True
    if ref_dift:
        import atf1
        ref = np.asarray(atf1.top(ref_dift))[..., :3].astype(np.float32)
        # channel by channel: brightness and the green-brown balance of the game's own paint
        # match: the percentile compared (50 for the plain albedos; 90 for a sheet with its shading baked in, whose shadows would mislead a median)
        s = np.percentile(ref.reshape(-1, 3), match, axis=0) / np.maximum(np.percentile(dif[used], match, axis=0), 1.0)
        s = np.clip(s, 0.45, 1.3); dif[used] *= s; print('  diffuse scaled by %s to the game paint' % np.round(s, 2))
    return np.clip(dif, 0, 255).astype(np.uint8), np.clip(nrm, 0, 255).astype(np.uint8)


def write_textures(dif, nrm, out_dir, stem):
    open(os.path.join(out_dir, 'reg_%s_dift.texture.loc_def.bin' % stem), 'wb').write(ST.atf(dif, 'DXT1'))
    open(os.path.join(out_dir, 'bump_%s_norsp.texture.loc_def.bin' % stem), 'wb').write(ST.atf(nrm, 'DXT5'))


def rename_material(data, olds, news):
    """same-length-or-shorter rename in the template's material table; the arm_ map named by the vehicle config is untouched"""
    out = bytearray(data)
    for old, new in zip(olds, news):
        if len(new) > len(old): raise ValueError(new)
        i = 0
        while True:
            i = out.find(old + b'\0', i)
            if i < 0: break
            out[i:i + len(old)] = new.ljust(len(old), b'\0'); i += len(old)
    return bytes(out)

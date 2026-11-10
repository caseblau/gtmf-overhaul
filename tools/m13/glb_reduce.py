"""Read a very detailed GLB by named node and reduce each node to a game budget, keeping its texture mapping (9 Nov, IS-2).

The reducer works on positions only, so closed shapes stay closed across UV seams; the texture coordinates and normals are
then taken back from the original surface, corner by corner, restricted to the UV island the new face lies on, so a face
never picks up a neighbouring island's texture.

  nodes = load_glb(path)                  -> {node name: dict(P (m,3,3) world corners, T (m,3,2), N (m,3,3), mat, parent, pos)}
  reduce_part(P, T, N, target)            -> P, T, N of about `target` triangles
  budget(counts, total)                   -> {name: target}: small parts nearly whole, big parts cut hardest
"""
import json, struct
import numpy as np
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components


def load_glb(path, skip=lambda name, material: False):
    f = open(path, 'rb'); f.read(12); n = struct.unpack('<I', f.read(4))[0]; f.read(4); j = json.loads(f.read(n))
    ln = struct.unpack('<I', f.read(4))[0]; f.read(4); base = f.tell(); f.close()
    data = np.memmap(path, np.uint8, 'r', offset=base, shape=(ln,))
    A, BV, M, mats = j['accessors'], j['bufferViews'], j['meshes'], [m['name'] for m in j['materials']]
    CT = {5126: ('<f4', 4), 5125: ('<u4', 4), 5123: ('<u2', 2), 5121: ('u1', 1)}; NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}
    def acc(i):
        a = A[i]; bv = BV[a['bufferView']]; dt, sz = CT[a['componentType']]; k = NC[a['type']]; off = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
        stride = bv.get('byteStride', sz * k)
        if stride == sz * k:
            out = np.frombuffer(data[off:off + a['count'] * stride].tobytes(), dt).reshape(-1, k)
        else:
            raw = np.frombuffer(data[off:off + a['count'] * stride].tobytes(), np.uint8).reshape(-1, stride)[:, :sz * k]
            out = np.frombuffer(raw.tobytes(), dt).reshape(-1, k)
        return out.astype(np.float64) if dt == '<f4' else out.astype(np.int64)
    def mat(nd):
        if 'matrix' in nd: return np.array(nd['matrix'], float).reshape(4, 4)
        x, y, z, w = nd.get('rotation', [0, 0, 0, 1])
        R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y + z * w), 2 * (x * z - y * w), 0], [2 * (x * y - z * w), 1 - 2 * (x * x + z * z), 2 * (y * z + x * w), 0],
                      [2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (x * x + y * y), 0], [0, 0, 0, 1.0]])
        T = np.eye(4); T[3, :3] = nd.get('translation', [0, 0, 0]); s = np.diag(list(nd.get('scale', [1, 1, 1])) + [1.0])
        return s @ R @ T
    out = {}
    def walk(i, W, parent):
        nd = j['nodes'][i]; w = mat(nd) @ W; name = nd['name']
        if 'mesh' in nd:
            Ps, Ts, Ns, m_ = [], [], [], None
            for pr in M[nd['mesh']]['primitives']:
                m_ = mats[pr['material']]
                if skip(name, m_): continue
                p = acc(pr['attributes']['POSITION']); t = acc(pr['attributes']['TEXCOORD_0']); n_ = acc(pr['attributes']['NORMAL']); ix = acc(pr['indices']).reshape(-1, 3)
                pw = np.c_[p, np.ones(len(p))] @ w; nw = n_ @ np.linalg.inv(w[:3, :3]).T
                nw /= np.maximum(np.linalg.norm(nw, axis=1, keepdims=True), 1e-9)
                Ps.append(pw[:, :3][ix]); Ts.append(t[ix]); Ns.append(nw[ix])
            if Ps:
                out[name] = dict(P=np.vstack(Ps), T=np.vstack(Ts), N=np.vstack(Ns), mat=m_, parent=parent, pos=w[3, :3].copy())
        for c in nd.get('children', []): walk(c, w, name)
    for r in j['scenes'][0]['nodes']: walk(r, np.eye(4), None)
    return out


def budget(counts, total, power=0.62, floor=8):
    """targets per part: count ** power, scaled so they add up to `total`; a part is never given more than it has"""
    names = list(counts); c = np.array([counts[k] for k in names], float); lo, hi = 1e-4, 1e4
    for _ in range(60):
        s = (lo * hi) ** 0.5; t = np.minimum(c, np.maximum(floor, s * c ** power))
        if t.sum() > total: hi = s
        else: lo = s
    return {k: int(v) for k, v in zip(names, np.minimum(c, np.maximum(floor, lo * c ** power)))}


def _islands(T, digits=4):
    """UV island label per face: faces sharing texture corners"""
    pts = np.round(T.reshape(-1, 2), digits); _, inv = np.unique(pts, axis=0, return_inverse=True); inv = inv.ravel().reshape(-1, 3); m = inv.max() + 1
    g = coo_matrix((np.ones(3 * len(inv)), (np.r_[inv[:, 0], inv[:, 1], inv[:, 2]], np.r_[inv[:, 1], inv[:, 2], inv[:, 0]])), shape=(m, m))
    _, lab = connected_components(g, directed=False); return lab[inv[:, 0]]


def _closest_bary(p, a, b, c):
    """barycentric weights of the closest points on triangles (a, b, c) to points p (Ericson), arrays of the same length"""
    ab, ac, ap = b - a, c - a, p - a
    d00, d01, d11 = (ab * ab).sum(1), (ab * ac).sum(1), (ac * ac).sum(1); d20, d21 = (ap * ab).sum(1), (ap * ac).sum(1)
    den = d00 * d11 - d01 * d01; den = np.where(np.abs(den) < 1e-18, 1e-18, den)
    v = (d11 * d20 - d01 * d21) / den; w = (d00 * d21 - d01 * d20) / den
    v = np.clip(v, 0, 1); w = np.clip(w, 0, 1); s = v + w; over = s > 1
    v = np.where(over, v / s, v); w = np.where(over, w / s, w)
    return 1 - v - w, v, w


def reduce_part(P, T, N, target, k=8):
    if len(P) <= target: return P, T, N
    import fast_simplification as FS
    pts = np.round(P.reshape(-1, 3), 5); uq, inv = np.unique(pts, axis=0, return_inverse=True); inv = inv.ravel().reshape(-1, 3)
    good = (inv[:, 0] != inv[:, 1]) & (inv[:, 1] != inv[:, 2]) & (inv[:, 0] != inv[:, 2])
    tr = max(0.0, min(0.995, 1.0 - target / max(1, good.sum())))
    Vn, Fn = FS.simplify(uq.astype(np.float32), inv[good].astype(np.int32), target_reduction=tr, agg=5)
    Vn = np.asarray(Vn, np.float64); Fn = np.asarray(Fn, np.int64)
    if not len(Fn): return P[:0], T[:0], N[:0]
    lab = _islands(T); cen = P.mean(1); tree = cKDTree(cen)
    Pn = Vn[Fn]; cn = Pn.mean(1); dd, near = tree.query(cn, k=min(k, len(cen)))
    near = near.reshape(len(cn), -1); first = near[:, 0]
    Tn = np.zeros((len(Fn), 3, 2)); Nn = np.zeros((len(Fn), 3, 3))
    for L in np.unique(lab[first]):
        sel = np.where(lab[first] == L)[0]; ids = np.where(lab == L)[0]
        t2 = cKDTree(cen[ids]); q = Pn[sel].reshape(-1, 3); kk = min(k, len(ids)); _, nn = t2.query(q, k=kk); nn = np.asarray(nn).reshape(len(q), -1)
        best_d = np.full(len(q), np.inf); bt = np.zeros((len(q), 2)); bn = np.zeros((len(q), 3))
        for c in range(nn.shape[1]):
            tri = ids[nn[:, c]]; a, b, d = P[tri, 0], P[tri, 1], P[tri, 2]
            u, v, w = _closest_bary(q, a, b, d)
            h = a * u[:, None] + b * v[:, None] + d * w[:, None]; dist = np.linalg.norm(q - h, axis=1); better = dist < best_d
            best_d[better] = dist[better]
            bt[better] = (T[tri, 0] * u[:, None] + T[tri, 1] * v[:, None] + T[tri, 2] * w[:, None])[better]
            bn[better] = (N[tri, 0] * u[:, None] + N[tri, 1] * v[:, None] + N[tri, 2] * w[:, None])[better]
        Tn[sel] = bt.reshape(-1, 3, 2); Nn[sel] = bn.reshape(-1, 3, 3)
    Nn /= np.maximum(np.linalg.norm(Nn, axis=2, keepdims=True), 1e-9)
    # keep the original outward sense: a face wound against the original normals is turned over
    fn = np.cross(Pn[:, 1] - Pn[:, 0], Pn[:, 2] - Pn[:, 0]); flip = (fn * Nn.mean(1)).sum(1) < 0
    Pn[flip] = Pn[flip][:, [0, 2, 1]]; Tn[flip] = Tn[flip][:, [0, 2, 1]]; Nn[flip] = Nn[flip][:, [0, 2, 1]]
    return Pn, Tn, Nn

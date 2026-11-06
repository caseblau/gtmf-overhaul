"""SU-122 parts with UVs (T-34 texture by reference) -> OBJ + MTL for Blender, and the data the AZG2 writer needs.

  python su122_build.py <t34_42_utz mesh> <m30m38 mesh> <outdir> [t34 diffuse png]
Objects: t34_hull (clipped hull, original UVs), t34_parts (kept T-34 sub-parts), casemate, mantlet, roof_*, m30_barrel.
"""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import azg2, geom, subtree_obj, su122_geom as G

SIDE_STRIP = (0.184, 0.472, 0.802, 0.545)     # T-34 texture: upper side plate (plain armour), u0 v0 u1 v1
MASK_BOX = None                               # filled from the T-34 d_gunmask UVs

def planar_uv(V, F, box):
    """per face: project on its plane, fit the face's 2D bbox into box (keeps faces readable, stretches long ones)"""
    u0, v0, u1, v1 = box; UV = np.zeros((len(F) * 3, 2)); Vo = V[F].reshape(-1, 3); Fo = np.arange(len(Vo)).reshape(-1, 3)
    n = geom.normals(V, F)
    for k, f in enumerate(F):
        a = n[k]; up = np.array([0, 1.0, 0]) if abs(a[1]) < 0.9 else np.array([0, 0, 1.0])
        s = np.cross(up, a); s /= np.linalg.norm(s); t = np.cross(a, s)
        p = V[f]; q = np.c_[p @ s, p @ t]
        q = (q - q.min(0)) / np.maximum(np.ptp(q, 0), 1e-6)
        UV[3 * k:3 * k + 3] = np.c_[u0 + q[:, 0] * (u1 - u0), v0 + q[:, 1] * (v1 - v0)]
    UV = np.nan_to_num(UV, nan=u0)          # degenerate faces (dropped later)
    return Vo, Fo, UV

def build(t34_path, m30_path):
    m = azg2.read(t34_path); L = 1; b = m['blocks'][L]; nodes = azg2.lod_nodes(m, L); N = m['nodes']
    def under(i, root):
        while i != 0xffffffff and i < len(N):
            if N[i]['name'] == root: return True
            i = N[i]['parent']
        return False
    drop = {k for k, n in enumerate(nodes) if under(n['index'], 'd_head') or under(n['index'], 's_bow_rot')}
    W = np.array([n['world'] for n in nodes])
    P = np.einsum('ni,nij->nj', np.c_[b['pos'], np.ones(len(b['pos']))], W[b['bone']])[:, :3]
    I = b['idx'].reshape(-1, 3); uv = b['uv']
    gm = [k for k, n in enumerate(nodes) if n['name'] == 'd_gunmask'][0]
    mu = uv[b['bone'] == gm]; mask_box = (*mu.min(0), *mu.max(0))
    bone_t = b['bone'][I[:, 0]]
    (cV, cF), planes = G.casemate()
    hull = bone_t == 0
    hv, hf = geom.subtract_convex(np.c_[P, uv], I[hull], planes)
    parts = {}
    parts['t34_hull'] = (hv[:, :3], hf, hv[:, 3:5])
    keep = ~hull & ~np.isin(bone_t, list(drop))
    parts['t34_parts'] = (P, I[keep], uv)
    cn = geom.normals(cV, cF); cF = cF[cn[:, 1] > -0.99]
    parts['casemate'] = planar_uv(cV, cF, SIDE_STRIP)
    v, f = G.mantlet(); parts['mantlet'] = planar_uv(v + G.PIVOT, f, mask_box)
    v, f = G.sleeve(); parts['sleeve'] = planar_uv(v + G.PIVOT, f, mask_box)
    for k, (v, f) in enumerate(G.roof_parts()): parts['roof_%d' % k] = planar_uv(v, f, SIDE_STRIP)
    m30 = azg2.read(m30_path); bb = m30['blocks'][1]; mn = azg2.lod_nodes(m30, 1)
    gv, gf = subtree_obj.subtree_geo(m30, {'d_gun'})
    org = next(n for n in m30['nodes'] if n['name'] == 'd_head')['world'][3, :3]
    parts['m30_barrel'] = (gv - org + G.PIVOT, gf, bb['uv'])
    return parts

def write_obj(path, parts, tex_png=None):
    mtl = os.path.splitext(path)[0] + '.mtl'
    with open(mtl, 'w') as f:
        f.write('newmtl t34_42_utz\nKd 1 1 1\n' + ('map_Kd %s\n' % os.path.basename(tex_png) if tex_png else ''))
        f.write('newmtl m30m38\nKd 0.33 0.36 0.24\n')
    with open(path, 'w') as f:
        f.write('mtllib %s\n' % os.path.basename(mtl)); o = 1
        for name, (V, F, UV) in parts.items():
            used = np.unique(F); remap = np.full(len(V), -1); remap[used] = np.arange(len(used))
            V, UV, F = V[used], UV[used], remap[F]
            f.write('o %s\nusemtl %s\n' % (name, 'm30m38' if name.startswith('m30') else 't34_42_utz'))
            for x, y, z in V: f.write('v %.5f %.5f %.5f\n' % (x, y, -z))
            for u, v in UV: f.write('vt %.5f %.5f\n' % (u, 1 - v))
            for a, b_, c in F + o: f.write('f %d/%d %d/%d %d/%d\n' % (a, a, c, c, b_, b_))
            o += len(V)

if __name__ == '__main__':
    parts = build(sys.argv[1], sys.argv[2]); os.makedirs(sys.argv[3], exist_ok=True)
    write_obj(os.path.join(sys.argv[3], 'su122_v1.obj'), parts, sys.argv[4] if len(sys.argv) > 4 else None)
    print({k: (len(v[0]), len(v[1])) for k, v in parts.items()})

"""Automatic checks of the built SU-122 mesh: python su122_audit.py <su122.mesh.loc_def.bin>

1. no casemate walls hanging over the track run below the sponsons
2. no part (except the gun, its mask and the headlight base) inside the casemate volume
3. marking sockets lie on the casemate side plates, facing out
4. the gun mount: the cap (d_gunmount) is fixed to the hull, and at every corner of the gun's range (traverse +-10 deg
   about s_rotation, elevation -3..+25 deg about d_gunmask) the box, the shield and their fittings cut none of the cap's
   outer surfaces, the frame or its bolts in front of the front plate (they may only slide in through the slot walls),
   stay under the roof and in front of the plate below the opening, and the bridge never shows through the shield
5. vertex counts within the u16 index limit
6. the gun add-ins (v31): d_gun (under d_gunmask) and d_zatvor (under d_gun, at the M-30's breech offset) are kind-1
   holders with hit shapes only, the add-in files su122_barrel / su122_breech next to the mesh carry one kind-3 node named
   like the holder, three LODs and the M-30 material, and the barrel ends just behind the muzzle socket s_gun
Prints one line per check and exits with code 1 if any check fails.
"""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import azg2, geom, su122_geom as G

def _seg_tri(p0, p1, T):
    """points where segments p0-p1 (n,3) cross triangles T (n,3,3); NaN where they do not"""
    e1 = T[:, 1] - T[:, 0]; e2 = T[:, 2] - T[:, 0]; d = p1 - p0
    h = np.cross(d, e2); a = np.einsum('ij,ij->i', e1, h)
    ok = np.abs(a) > 1e-14; f = np.where(ok, 1.0 / np.where(ok, a, 1.0), 0.0)
    s = p0 - T[:, 0]; u = f * np.einsum('ij,ij->i', s, h)
    q = np.cross(s, e1); v = f * np.einsum('ij,ij->i', d, q); t = f * np.einsum('ij,ij->i', e2, q)
    hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t >= 0) & (t <= 1)
    return np.where(hit[:, None], p0 + t[:, None] * d, np.nan)

def crossings(Va, Fa, Vb, Fb, chunk=300):
    """points on the curves where two triangle meshes cut each other (an edge of one through a face of the other)"""
    A, B = Va[Fa], Vb[Fb]; alo, ahi, blo, bhi = A.min(1), A.max(1), B.min(1), B.max(1); out = []
    for s in range(0, len(A), chunk):
        i, j = np.nonzero(np.all((alo[s:s + chunk, None] <= bhi[None] + 1e-6) & (ahi[s:s + chunk, None] >= blo[None] - 1e-6), axis=2))
        if not len(i): continue
        a, b = A[s + i], B[j]
        for k, l in ((0, 1), (1, 2), (2, 0)):
            for p in (_seg_tri(a[:, k], a[:, l], b), _seg_tri(b[:, k], b[:, l], a)):
                out.append(p[~np.isnan(p[:, 0])])
    return np.vstack(out) if out else np.zeros((0, 3))

def sample(V, F, n=12, seed=1):
    """points spread over every triangle (and the vertices)"""
    T = V[F]; u = np.random.default_rng(seed).random((len(T), n, 2)); u = np.where(u.sum(-1, keepdims=True) > 1, 1 - u, u)
    P = T[:, None, 0] * (1 - u.sum(-1, keepdims=True)) + T[:, None, 1] * u[..., :1] + T[:, None, 2] * u[..., 1:]
    return np.vstack([V, P.reshape(-1, 3)])

def main(path):
    m = azg2.read(path); ok = True
    b = m['blocks'][1]; nodes = azg2.lod_nodes(m, 1)
    W = np.array([n['world'] for n in nodes]); bone = np.clip(b['bone'], 0, len(W) - 1)
    P = np.einsum('ni,nij->nj', np.c_[b['pos'], np.ones(len(b['pos']))], W[bone])[:, :3]
    I = b['idx'][:len(b['idx']) // 3 * 3].reshape(-1, 3); n = geom.normals(P, I); c = P[I].mean(1)
    hub = (np.abs(c[:, 2] - 2.60) < 0.08) & (np.abs(c[:, 1] + 0.51) < 0.08)          # idler hub caps are legitimate
    wall = (np.abs(n[:, 0]) > 0.95) & (np.abs(c[:, 0]) > 1.10) & (c[:, 1] < -0.06) & (c[:, 2] > -0.5) & (c[:, 2] < 2.8) & ~hub
    r = not wall.any(); ok &= r; print('1 casemate walls over the tracks:', int(wall.sum()), 'OK' if r else 'FAIL')
    allowed = {'d_hull', 'd_gun', 'd_gunmask', 'd_gunmount', 'd_light', 'd_hatch_02'}   # the cap's skirt runs on 0.15 m behind the plate; v34j: the roof lid is sunk 1.1 cm into the roof
    bad = {nd['name']: round(float(G.inside_any(P[bone == k], -0.01).mean()), 2) for k, nd in enumerate(nodes)
           if nd['name'] not in allowed and (bone == k).any() and G.inside_any(P[bone == k], -0.01).mean() > 0.02}
    r = not bad; ok &= r; print('2 parts inside the casemate:', bad or 'none', 'OK' if r else 'FAIL')
    wd = wa = 0.0
    for nd in m['nodes']:
        if not nd['name'].startswith('s_mark'): continue
        p = nd['world'][3, :3]; sx = np.sign(p[0]); q, nrm = G.side_point(p[1], p[2], sx, 0.0)
        z = nd['world'][2, :3] / np.linalg.norm(nd['world'][2, :3])
        wd = max(wd, abs((p - q) @ nrm) * 100); wa = max(wa, np.degrees(np.arccos(np.clip(z @ nrm, -1, 1))))
    r = wd < 2.0 and wa < 2.0; ok &= r; print('3 marking sockets: worst offset %.1f cm, worst angle %.1f deg' % (wd, wa), 'OK' if r else 'FAIL')
    # gun mount (v30): the cap is fixed to the hull (v19-v29 it traversed with the gun); the gun mask traverses about
    # s_rotation and elevates about its own origin (the trunnion), both taken from the built mesh
    names = {nd['name']: nd for nd in m['nodes']}
    def chain(nm):
        out, i = [], names[nm]['index']
        while i != 0xffffffff and i < len(m['nodes']): out.append(m['nodes'][i]['name']); i = m['nodes'][i]['parent']
        return out
    fixed = 's_rotation' not in chain('d_gunmount') and 'd_gunmask' not in chain('d_gunmount')
    Tax = names['s_rotation']['world'][3, :3]; C = names['d_gunmask']['world'][3, :3]
    rig_ok = np.allclose(Tax, G.TRAVERSE, atol=1e-4) and np.allclose(C, G.PIVOT, atol=1e-4)
    def pose(V, t, e):
        e, t = np.radians(e), np.radians(t)
        Rx = np.array([[1, 0, 0], [0, np.cos(e), -np.sin(e)], [0, np.sin(e), np.cos(e)]])     # row vectors: +e = muzzle up
        Ry = np.array([[np.cos(t), 0, -np.sin(t)], [0, 1, 0], [np.sin(t), 0, np.cos(t)]])
        return (V @ Rx + C - Tax) @ Ry + Tax
    def unpose(P, t, e):
        e, t = np.radians(e), np.radians(t)
        Rx = np.array([[1, 0, 0], [0, np.cos(e), -np.sin(e)], [0, np.sin(e), np.cos(e)]])
        Ry = np.array([[np.cos(t), 0, -np.sin(t)], [0, 1, 0], [np.sin(t), 0, np.cos(t)]])
        return ((P - Tax) @ Ry.T + Tax - C) @ Rx.T
    moving = [G.mantlet(), G.shield(), geom.merge(*G.gun_box_details()), geom.merge(*G.shield_details())]
    outer = [G.cap(), geom.merge(*G.cap_shields(), *G.frame_bolts()), geom.merge(*G.cap_details())]   # not the slot walls
    Vg, Fg = G.cap_bridge(); bridge = sample(Vg, Fg)
    n_, d_ = G.FRONT; tl = G.TRAVERSE_LIMIT
    cuts = through = 0; worst = []
    for t in (-tl, -tl / 2, 0.0, tl / 2, tl):
        for el in (-3, 0, 5, 12, 20, 25):
            for k, (Vm, Fm) in enumerate(moving):
                W = pose(Vm, t, el)
                for Vf, Ff in outer:                    # crossings in front of the front plate are visible
                    X = crossings(W, Fm, Vf, Ff)
                    X = X[X @ n_ > d_ + 0.002]
                    if len(X): cuts += len(X); worst.append((t, el, k, X[:, 0].min() - G.GUN_X, X[:, 0].max() - G.GUN_X, X[:, 1].min(), X[:, 1].max()))
                under_roof = (W[:, 2] < G.ROOF_EDGE_Z - 0.01) & (W[:, 1] > G.ROOF - 0.002)   # v22: nothing through the roof
                through += int(under_roof.sum())
            S, _ = moving[1]; W = pose(S, t, el)
            below_open = (W[:, 1] < G.OPEN_Y0) & (W @ n_ > d_ + 0.005)                  # nor through the plate below the opening
            through += int(below_open.sum())
            if t == 0:                                  # v22: centred, the shield stays behind the cap face
                cf = np.array([G.cap_front_z(y) for y in W[:, 1]])
                through += int(((W[:, 1] > G.CAP_MEET_Y) & (W[:, 1] < G.CAP_TOP) & (W[:, 2] > cf + 0.01)).sum())
            # the bridge over the slot stays under the shield plate wherever the plate is over it
            L = unpose(bridge, t, el); r = np.hypot(L[:, 1], L[:, 2]); a = np.degrees(np.arctan2(L[:, 1], L[:, 2]))
            through += int(((np.abs(L[:, 0]) < G.SHIELD_HW - 0.002) & (a > G.SHIELD_A0 + 0.5) & (a < G.SHIELD_A1 - 0.5) &
                            (r > G.SHIELD_R - 0.001)).sum())
    r = fixed and rig_ok and cuts == 0 and through == 0; ok &= r
    print('4 gun mount: cap fixed %s, axes %s, %d crossings with the cap / frame, %d points through roof / plate / shield'
          % (fixed, 'ok' if rig_ok else 'MOVED', cuts, through), 'OK' if r else 'FAIL')
    for w in worst[:6]: print('   traverse %+.0f elevation %+d part %d: x %+.3f..%+.3f y %.3f..%.3f' % w)
    nv = [blk['nv'] for blk in m['blocks'][1:]]; r = max(nv) < 65536; ok &= r
    print('5 LOD vertex counts', nv, 'OK' if r else 'FAIL')
    # v31: barrel and breech block as add-in meshes with the M-30's texture, on the nodes themselves (Pz III pattern)
    probs = []
    for holder, parent in (('d_gun', 'd_gunmask'), ('d_zatvor', 'd_gun')):
        h = names.get(holder)
        if h is None: probs.append('node %s missing' % holder); continue
        if h['kind'] != 1 or m['nodes'][h['parent']]['name'] != parent: probs.append('%s not a kind-1 child of %s' % (holder, parent))
        if not h['slots'][0]['nv'] or any(s['nv'] for s in h['slots'][1:]): probs.append('%s must carry a hit shape only' % holder)
        p = os.path.join(os.path.dirname(os.path.abspath(path)), 'su122_%s.mesh.loc_def.bin' % {'d_gun': 'barrel', 'd_zatvor': 'breech'}[holder])
        if not os.path.exists(p): probs.append('add-in file %s missing' % os.path.basename(p)); continue
        a_ = azg2.read(p); tags = [b['tag'] for b in a_['blocks']]
        if [n['name'] for n in a_['nodes']] != ['s_root', holder] or a_['nodes'][1]['kind'] != 3: probs.append('%s: nodes %s' % (os.path.basename(p), [n['name'] for n in a_['nodes']]))
        if tags != ['GXT2'] * 3 or any(b['nv'] == 0 for b in a_['blocks']): probs.append('%s: blocks %s' % (os.path.basename(p), tags))
        if [mt['name'] for mt in a_['materials']] != ['m30m38_dift']: probs.append('%s: material %s' % (os.path.basename(p), [mt['name'] for mt in a_['materials']]))
        if holder == 'd_gun' and len(a_['blocks']) == 3:
            zmax = a_['blocks'][0]['pos'][:, 2].max(); zs = names['s_gun']['world'][3, 2] - h['world'][3, 2]
            if not 0.0 < zs - zmax < 0.12: probs.append('barrel ends %.3f m from the muzzle socket' % (zs - zmax))
    if 'd_zatvor' in names and 'd_gun' in names:
        dz = names['d_zatvor']['world'][3, :3] - names['d_gun']['world'][3, :3]
        if not np.allclose(dz, [0.1552, -0.0108, -2.0136], atol=0.002): probs.append('d_zatvor offset %s' % np.round(dz, 3))
    r = not probs; ok &= r; print('6 gun add-ins (M-30 barrel and breech block):', probs or 'barrel and breech files OK', 'OK' if r else 'FAIL')
    return ok

if __name__ == '__main__':
    sys.exit(0 if main(sys.argv[1]) else 1)

import sys, numpy as np
sys.path.insert(0, '/mnt/user-data/outputs/m13')
import azg2, geom, su122_geom as G
T34 = sys.argv[1]; out = sys.argv[2]
m = azg2.read(T34); L = 1; b = m['blocks'][L]
nodes = azg2.lod_nodes(m, L); N = m['nodes']
def under(i, root):
    while i != 0xffffffff and i < len(N):
        if N[i]['name'] == root: return True
        i = N[i]['parent']
    return False
drop = {k for k, n in enumerate(nodes) if under(n['index'], 'd_head') or under(n['index'], 's_bow_rot')}
W = np.array([n['world'] for n in nodes])
P = np.einsum('ni,nij->nj', np.c_[b['pos'], np.ones(len(b['pos']))], W[b['bone']])[:, :3]
I = b['idx'].reshape(-1, 3)
keep = ~np.isin(b['bone'][I[:, 0]], list(drop))
(cV, cF), planes = G.casemate()
cen = P[I].mean(1)
hull_tri = b['bone'][I[:, 0]] == 0
rest = keep & ~hull_tri
hv, hf = geom.subtract_convex(P, I[keep & hull_tri], planes)
parts = [('t34_rest', P, I[rest]), ('t34_hull_cut', hv, hf)]
cut = hull_tri
# casemate: drop the bottom face and the faces lying in the glacis plane
n = geom.normals(cV, cF); tc = cV[cF].mean(1)
on_glacis = np.zeros(len(cF), bool)
parts.append(('casemate', cV, cF[(n[:, 1] > -0.99) & ~on_glacis]))
R = np.eye(3)
v, f = G.mantlet(); parts.append(('mantlet', v + G.PIVOT, f))
# the in-game M-30 howitzer: cradle, recoil cylinders, barrel and breech (node d_head of m30m38), trunnion on PIVOT
import subtree_obj
m30 = azg2.read(sys.argv[3]); gv, gf = subtree_obj.subtree_geo(m30, {'d_gun'})
org = next(n for n in m30['nodes'] if n['name'] == 'd_head')['world'][3, :3]
parts.append(('m30', gv - org + G.PIVOT, gf))
sv, sf = G.sleeve(); parts.append(('sleeve', sv + G.PIVOT + [0, 0.47 - 0.41 - (0.47 - 0.41), 0], sf))
print('muzzle z', (gv - org + G.PIVOT)[:, 2].max())
for k, (v, f) in enumerate(G.roof_parts()): parts.append(('roof%d' % k, v, f))
geom.write_obj(out, parts)
print('hull triangles cut', int(cut.sum()), 'turret/MG nodes dropped', len(drop))

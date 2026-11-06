"""export LOD1 OBJ with the gun elevated by E degrees about the trunnion: python export_elev.py mesh.bin out.obj E"""
import sys, numpy as np
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import azg2
m = azg2.read(sys.argv[1]); E = np.radians(float(sys.argv[3]))
nodes = azg2.lod_nodes(m, 1); N = m['nodes']
def under(n, root):
    i = n['index']
    while i != 0xffffffff and i < len(N):
        if N[i]['name'] == root: return True
        i = N[i]['parent']
    return False
piv = next(n for n in N if n['name'] == 's_rotation')['world'][3, :3]
b = m['blocks'][1]; pos = b['pos'].astype(float)
W = np.array([n['world'] for n in nodes]); bone = np.clip(b['bone'], 0, len(W) - 1)
P = np.einsum('ni,nij->nj', np.c_[pos, np.ones(len(pos))], W[bone])[:, :3]
sel = np.array([under(nodes[i], 'd_gunmask') for i in bone])
c, s = np.cos(E), np.sin(E); d = P[sel] - piv
P[sel] = piv + np.c_[d[:, 0], d[:, 1] * c + d[:, 2] * s, -d[:, 1] * s + d[:, 2] * c]
with open(sys.argv[2], 'w') as f:
    for x, y, z in P: f.write('v %.5f %.5f %.5f\n' % (x, y, -z))
    for u, v in b['uv']: f.write('vt %.5f %.5f\n' % (u, 1 - v))
    t = b['idx'][:len(b['idx']) // 3 * 3].reshape(-1, 3) + 1
    for a, cc, e in t: f.write('f %d/%d %d/%d %d/%d\n' % (a, a, e, e, cc, cc))

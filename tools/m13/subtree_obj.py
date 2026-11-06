"""export chosen node subtrees of an AZG2 mesh (world coords, LOD 1) to OBJ: subtree_obj.py mesh.bin out.obj node1,node2"""
import sys, numpy as np
sys.path.insert(0, '/mnt/user-data/outputs/m13')
import azg2, geom
def subtree_geo(m, roots, L=1, exclude=()):
    b = m['blocks'][L]; nodes = azg2.lod_nodes(m, L); N = m['nodes']
    def under(i, names):
        while i != 0xffffffff and i < len(N):
            if N[i]['name'] in names: return N[i]['name']
            i = N[i]['parent']
        return None
    W = np.array([n['world'] for n in nodes])
    P = np.einsum('ni,nij->nj', np.c_[b['pos'], np.ones(len(b['pos']))], W[b['bone']])[:, :3]
    I = b['idx'].reshape(-1, 3)
    sel = np.array([under(n['index'], roots) is not None and under(n['index'], exclude) is None for n in nodes])
    return P, I[sel[b['bone'][I[:, 0]]]]
if __name__ == '__main__':
    m = azg2.read(sys.argv[1]); P, F = subtree_geo(m, set(sys.argv[3].split(',')), exclude=set(sys.argv[4].split(',')) if len(sys.argv) > 4 else ())
    geom.write_obj(sys.argv[2], [('part', P, F)])

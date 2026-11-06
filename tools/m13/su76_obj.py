"""Export the SU-76M as a Blender-ready OBJ + MTL: the vehicle mesh (LOD1) with every node posed, the ZiS-3 barrel and
breech add-ins, the T-70M running-gear add-ins on their holder nodes (wheels, sprockets, idlers, rollers, bogie arms,
the spare wheel), and a stand-in track (the game builds the real one). Materials: the SU-76M's own texture (PNG next to
the OBJ); the game parts get plain colours (their game textures are not in the repo).

  python su76_obj.py <su76m mesh> <dir with su76m_barrel / su76m_breech> <game mesh dir (m_t70m_*.bin)> <su76m dift ATF> <outdir>
"""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import azg2, atf, render_scene, su76_mesh as SMM
from PIL import Image

def posed(m, lod):
    b = m['blocks'][lod]; nodes = azg2.lod_nodes(m, lod); W = np.array([n['world'] for n in nodes]); bone = np.clip(b['bone'], 0, len(W) - 1)
    P = np.einsum('ni,nij->nj', np.c_[b['pos'], np.ones(len(b['pos']))], W[bone])[:, :3]
    N = np.einsum('ni,nij->nj', b['nrm'].astype(np.float64), W[bone][:, :3, :3])
    F = b['idx'][:len(b['idx']) // 3 * 3].reshape(-1, 3)
    return P, N, b['uv'], F, bone, nodes

def main(mesh, addin_dir, game, dift, out):
    os.makedirs(out, exist_ok=True)
    img = atf.decode(open(dift, 'rb').read(), -1)[..., :3]
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(os.path.join(out, 'su76m_dift.png'))
    m = azg2.read(mesh); Wn = {n['name']: n['world'] for n in m['nodes']}
    objs = []                                   # (name, material, P, N, UV, F)
    P, N, UV, F, bone, nodes = posed(m, 1)
    names = [n['name'] for n in nodes]
    for k, nm in enumerate(names):              # one object per node: hull, hatches, gun mask, seat, fittings
        sel = bone[F[:, 0]] == k
        if sel.any(): objs.append((nm, 'su76m', P, N, UV, F[sel]))
    def instance(path, W, name, mat):
        a = azg2.read(path); p, n, uv, f, _, _ = posed(a, 0)
        p = np.c_[p, np.ones(len(p))] @ W; n = n @ W[:3, :3]
        objs.append((name, mat, p[:, :3], n, uv, f))
    for stem, holder in (('su76m_barrel', 'd_gun'), ('su76m_breech', 'd_zatvor')):
        instance(os.path.join(addin_dir, stem + '.mesh.loc_def.bin'), Wn[holder], stem, 'gun_steel')
    part = {'star': 't70m_star', 'road': 't70m_wheel', 'lazy': 't70m_lazy', 'roller': 't70m_roller'}
    circles = {}
    for name, _, p, kind in SMM.wheel_layout():
        W = Wn[name]
        instance(os.path.join(game, 'm_%s.bin' % part[kind]), W, name, 'running_gear')
        r = {'star': 0.30, 'road': 0.28, 'lazy': 0.28, 'roller': 0.135}[kind]
        circles.setdefault(np.sign(p[0]), []).append((p[2], p[1], r, p[0]))
    for name, _, p, _ in SMM.caret_layout():
        instance(os.path.join(game, 'm_%s.bin' % ('t70m_lcaret' if p[0] < 0 else 't70m_rcaret')), Wn[name], name, 'running_gear')
    instance(os.path.join(game, 'm_t70m_wheel.bin'), Wn['d_wheel_23'], 'spare_wheel', 'running_gear')
    sc = render_scene.Scene()
    for side, cs in circles.items():
        sc._track(cs, side, width=0.26, pitch=0.11, t=0.035)
        V, Nn, _, Ff, _ = sc.parts[-1]; objs.append(('track_%s' % ('right' if side > 0 else 'left'), 'track', V, Nn, np.zeros((len(V), 2)), Ff))
    with open(os.path.join(out, 'su76m.mtl'), 'w') as f:
        f.write('newmtl su76m\nKd 1 1 1\nmap_Kd su76m_dift.png\n\n')
        f.write('newmtl gun_steel\nKd 0.22 0.23 0.21\n\nnewmtl running_gear\nKd 0.27 0.30 0.18\n\nnewmtl track\nKd 0.13 0.12 0.11\n')
    with open(os.path.join(out, 'su76m.obj'), 'w') as f:
        f.write('# SU-76M (MF Overhaul) - tools\\m13\\su76_obj.py; game frame x right, y up, z forward (OBJ z flipped)\nmtllib su76m.mtl\n')
        o = 1
        for name, mat, P, N, UV, F in objs:
            u = np.unique(F); r = np.full(len(P), -1); r[u] = np.arange(len(u)); P2, N2, UV2, F2 = P[u], N[u], UV[u], r[F]
            f.write('o %s\nusemtl %s\n' % (name, mat))
            for x, y, z in P2: f.write('v %.5f %.5f %.5f\n' % (x, y, -z))
            for a, b in UV2: f.write('vt %.5f %.5f\n' % (a, 1 - b))
            for x, y, z in N2: f.write('vn %.4f %.4f %.4f\n' % (x, y, -z))
            for a, b, c in F2 + o: f.write('f %d/%d/%d %d/%d/%d %d/%d/%d\n' % (a, a, a, c, c, c, b, b, b))
            o += len(P2)
    print('written', os.path.join(out, 'su76m.obj'), len(objs), 'objects')

if __name__ == '__main__':
    main(*sys.argv[1:6])

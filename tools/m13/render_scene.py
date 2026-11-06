"""Offline preview renderer for Graviteam AZG2 vehicle meshes: the vehicle with its road wheels, idler, sprocket and a
generated track, on a ground plane, lit by a sun with shadows, sky ambient light and screen-space ambient occlusion,
2x supersampled. Close to how the game shows a vehicle, so the model can be judged without the game.

  from render_scene import Scene
  sc = Scene(); sc.add_vehicle(mesh_path, hull_texture_png, elevation=0)
  sc.add_running_gear(wheel_mesh, wheel_tex, sprocket_mesh, idler_mesh, gear_tex, node_source=mesh_path)
  img = sc.render(cam=(x, y, z), target=(x, y, z), fov=40, size=(1200, 800))
"""
import os, sys, numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import azg2, geom

def _tex(path):
    return np.asarray(Image.open(path).convert('RGB'), np.float32) / 255.0

class Scene:
    def __init__(self):
        self.parts = []          # (V world (n,3), N (n,3), UV (n,2) or None, F (m,3), texture or rgb)

    # ------------------------------------------------------------------ geometry
    def add(self, V, N, UV, F, tex):
        self.parts.append((np.asarray(V, np.float64), np.asarray(N, np.float64), UV, np.asarray(F, np.int64), tex))

    def add_vehicle(self, path, texture, elevation=0.0, traverse=0.0, lod_block=None, skip=(), addins=()):
        """addins: [(mesh path, holder node name, texture or rgb)] - add-in meshes (v31: the SU-122's barrel and breech
        block with the M-30 texture) drawn in the holder node's frame and posed with it"""
        m = azg2.read(path)
        blocks = [i for i, b in enumerate(m['blocks']) if (b['tag'] if isinstance(b['tag'], str) else b['tag'].decode()) != 'PNTl']
        L = lod_block if lod_block is not None else blocks[0]
        b = m['blocks'][L]; nodes = azg2.lod_nodes(m, L); N = m['nodes']
        W = np.array([n['world'] for n in nodes]); bone = np.clip(b['bone'], 0, len(W) - 1)
        P = np.einsum('ni,nij->nj', np.c_[b['pos'], np.ones(len(b['pos']))], W[bone])[:, :3]
        Nr = np.einsum('ni,nij->nj', b['nrm'].astype(np.float64), W[bone][:, :3, :3])
        def under(n, root):
            i = n['index']
            while i != 0xffffffff and i < len(N):
                if N[i]['name'] == root: return True
                i = N[i]['parent']
            return False
        parts = [(P, Nr, b['uv'].astype(np.float64), b['idx'][:len(b['idx']) // 3 * 3].reshape(-1, 3).astype(np.int64), texture,
                  np.array([under(nodes[i], 'd_gunmask') for i in range(len(nodes))])[bone],
                  np.array([under(nodes[i], 's_rotation' if any(n['name'] == 's_rotation' for n in N) else 'd_head') for i in range(len(nodes))])[bone],
                  np.array([nodes[i]['name'] in skip for i in range(len(nodes))])[bone] if skip else None)]
        for apath, holder, atex in addins:
            a = azg2.read(apath); ab = a['blocks'][0]; H = next(n for n in N if n['name'] == holder)
            Pa = np.einsum('ni,nij->nj', np.c_[ab['pos'], np.ones(len(ab['pos']))], np.tile(H['world'], (len(ab['pos']), 1, 1)))[:, :3]
            Na = ab['nrm'].astype(np.float64) @ H['world'][:3, :3]
            root = 's_rotation' if any(n['name'] == 's_rotation' for n in N) else 'd_head'
            parts.append((Pa, Na, ab['uv'].astype(np.float64), ab['idx'][:len(ab['idx']) // 3 * 3].reshape(-1, 3).astype(np.int64), atex,
                          np.full(len(Pa), under(H, 'd_gunmask')), np.full(len(Pa), under(H, root)), None))
        for P, Nr, UV, F, tex, sel_e, sel_t, drop in parts:
            if elevation or traverse:
                # traverse about the traverse node's vertical axis, elevation about the gun mask's own origin (v30: on the
                # SU-122 the traverse axis s_rotation is 0.40 m in front of the trunnion; v25-v29 turned both about s_rotation)
                piv = next(n for n in N if n['name'] in ('s_rotation', 'd_head'))['world'][3, :3]
                piv_e = next((n['world'][3, :3] for n in N if n['name'] == 'd_gunmask'), piv)
                e, a_ = np.radians(elevation), np.radians(traverse)
                Rx = np.array([[1, 0, 0], [0, np.cos(e), -np.sin(e)], [0, np.sin(e), np.cos(e)]])     # row vectors: +e = muzzle up
                Ry = np.array([[np.cos(a_), 0, -np.sin(a_)], [0, 1, 0], [np.sin(a_), 0, np.cos(a_)]])
                P[sel_e] = (P[sel_e] - piv_e) @ Rx + piv_e; Nr[sel_e] = Nr[sel_e] @ Rx
                P[sel_t] = (P[sel_t] - piv) @ Ry + piv; Nr[sel_t] = Nr[sel_t] @ Ry
            if drop is not None: F = F[~drop[F[:, 0]]]
            self.add(P, Nr, UV, F, _tex(tex) if isinstance(tex, str) else tex)
        self.nodes = {n['name']: n['world'] for n in N}
        return self

    def _instance(self, path, texture, M, mirror=False):
        m = azg2.read(path); b = m['blocks'][0]; nodes = azg2.lod_nodes(m, 0)
        W = np.array([n['world'] for n in nodes]); bone = np.clip(b['bone'], 0, len(W) - 1)
        P = np.einsum('ni,nij->nj', np.c_[b['pos'], np.ones(len(b['pos']))], W[bone])[:, :3]
        Nr = np.einsum('ni,nij->nj', b['nrm'].astype(np.float64), W[bone][:, :3, :3])
        F = b['idx'][:len(b['idx']) // 3 * 3].reshape(-1, 3).astype(np.int64)
        if mirror:
            P = P * [-1, 1, 1]; Nr = Nr * [-1, 1, 1]; F = F[:, [0, 2, 1]]
        P = P @ M[:3, :3] + M[3, :3]; Nr = Nr @ M[:3, :3]
        self.add(P, Nr, b['uv'].astype(np.float64), F, texture)

    def add_running_gear(self, wheel, wheel_tex, sprocket, idler, gear_tex, wheel_r=0.415, sprocket_r=0.32, idler_r=0.31):
        """road wheels / idler / sprocket at the vehicle's d_wheel_XX nodes, and a generated 0.5 m track"""
        wt = _tex(wheel_tex) if isinstance(wheel_tex, str) else wheel_tex
        gt = _tex(gear_tex) if isinstance(gear_tex, str) else gear_tex
        circles = {}
        for name, Wm in self.nodes.items():
            if not name.startswith('d_wheel_'): continue
            p = Wm[3, :3]; k = int(name[-2:]); side = 1 if p[0] > 0 else -1
            M = np.eye(4); M[3, :3] = p
            if p[2] > 2.3: self._instance(idler, gt, M, mirror=side < 0); r = idler_r
            elif p[2] < -2.3: self._instance(sprocket, gt, M, mirror=side < 0); r = sprocket_r
            else: self._instance(wheel, wt, M, mirror=side < 0); r = wheel_r
            circles.setdefault(side, []).append((p[2], p[1], r, p[0]))
        for side, cs in circles.items():
            self._track(cs, side)
        return self

    def _track(self, cs, side, width=0.50, pitch=0.172, t=0.05):
        from scipy.spatial import ConvexHull
        pts = []
        for z, y, r, _ in cs:
            a = np.linspace(0, 2 * np.pi, 90, endpoint=False); R = r + t / 2
            pts.append(np.c_[z + R * np.cos(a), y + R * np.sin(a)])
        pts = np.vstack(pts); h = ConvexHull(pts); loop = pts[h.vertices]
        seg = np.roll(loop, -1, 0) - loop; L = np.linalg.norm(seg, axis=1); cum = np.r_[0, np.cumsum(L)]
        x0 = np.mean([c[3] for c in cs]); V = []; F = []; col = []
        for s in np.arange(0, cum[-1], pitch):
            i = np.searchsorted(cum, s, 'right') - 1; f = (s - cum[i]) / L[i]
            c = loop[i] + f * seg[i]; tz, ty = seg[i] / L[i]; nz, ny = ty, -tz      # outward normal (counter-clockwise hull)
            Rm = np.array([[1, 0, 0], [0, ty, tz], [0, ny, nz]])                    # rows: x, along, outward (in (x,y,z))
            Rm = np.array([[1.0, 0, 0], [0, tz * 0 + ty, tz], [0, ny, nz]])
            ax_along = np.array([0, ty, tz]); ax_out = np.array([0, ny, nz])
            base = np.array([x0, c[1], c[0]])
            boxes = [(base, (width, pitch * 0.92, t)), (base + ax_out * (t / 2 + 0.012), (width * 0.9, 0.03, 0.024))]
            if int(round(s / pitch)) % 2 == 0: boxes.append((base - ax_out * (t / 2 + 0.05), (0.05, 0.10, 0.10)))   # guide horn
            for cen, (sx_, sa, so) in boxes:
                Rb = np.c_[[1.0, 0, 0], ax_along, ax_out]
                v, fa = geom.box(cen, [sx_, sa, so], Rb); F.append(fa + sum(len(q) for q in V)); V.append(v)
        V = np.vstack(V); F = np.vstack(F); n = geom.normals(V, F)
        Vf = V[F].reshape(-1, 3); Nf = np.repeat(n, 3, 0); Ff = np.arange(len(Vf)).reshape(-1, 3)
        self.add(Vf, Nf, None, Ff, np.array([0.17, 0.16, 0.14]))

    def add_ground(self, y, size=40.0):
        n = 64; g = np.linspace(-size / 2, size / 2, n + 1); X, Z = np.meshgrid(g, g)
        V = np.c_[X.ravel(), np.full(X.size, y), Z.ravel()]; F = []
        for i in range(n):
            for j in range(n):
                a = i * (n + 1) + j; F += [[a, a + n + 1, a + 1], [a + 1, a + n + 1, a + n + 2]]
        UV = np.c_[(V[:, 0] + size / 2) / size * 24, (V[:, 2] + size / 2) / size * 24]
        rng = np.random.default_rng(3); tex = 0.42 + 0.06 * rng.standard_normal((256, 256, 1))
        tex = np.clip(np.concatenate([tex * 0.92, tex * 0.88, tex * 0.70], 2), 0, 1).astype(np.float32)
        self.add(V, np.tile([0, 1.0, 0], (len(V), 1)), UV, np.array(F), ('tile', tex))

    # ------------------------------------------------------------------ raster
    @staticmethod
    def _raster(X, Y, Z, F, W, H, closest_is_smaller=True):
        zb = np.full((H, W), np.inf); tid = np.full((H, W), -1, np.int64)
        b0 = np.zeros((H, W), np.float32); b1 = np.zeros((H, W), np.float32)
        for k, (a, b, c) in enumerate(F):
            zs = (Z[a], Z[b], Z[c])
            if min(zs) <= 0.05: continue
            xs = np.array([X[a], X[b], X[c]]); ys = np.array([Y[a], Y[b], Y[c]])
            x0, x1 = int(max(0, np.floor(xs.min()))), int(min(W - 1, np.ceil(xs.max()))); y0, y1 = int(max(0, np.floor(ys.min()))), int(min(H - 1, np.ceil(ys.max())))
            if x1 < x0 or y1 < y0: continue
            d = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
            if abs(d) < 1e-12: continue
            gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            w0 = ((ys[1] - ys[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gy - ys[2])) / d
            w1 = ((ys[2] - ys[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gy - ys[2])) / d; w2 = 1 - w0 - w1
            m = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
            if not m.any(): continue
            iz = w0 / zs[0] + w1 / zs[1] + w2 / zs[2]; z = 1 / iz
            sub = zb[y0:y1 + 1, x0:x1 + 1]; upd = m & (z < sub)
            if not upd.any(): continue
            sub[upd] = z[upd]; tid[y0:y1 + 1, x0:x1 + 1][upd] = k
            b0[y0:y1 + 1, x0:x1 + 1][upd] = w0[upd]; b1[y0:y1 + 1, x0:x1 + 1][upd] = w1[upd]
        return zb, tid, b0, b1

    def render(self, cam, target, fov=40.0, size=(1200, 800), sun=(-0.45, 0.78, 0.43), ss=2, ao=True, view=None,
               shadow_focus=None):
        """view: optional exact pinhole camera for photo comparisons, dict(R=3x3 rows right/up/forward (photo_match
        Camera.R, roll included), f=focal length in output pixels, cx, cy=principal point in output pixels); cam is then
        the camera position and target / fov are ignored.
        shadow_focus: optional (centre, radius) - the shadow map covers only that sphere (finer shadows for close-ups; v25:
        the 6 mm texels of the whole-scene map drew jagged 'cracks' along thin gaps in zoomed renders)"""
        Wo, Ho = size; W, H = Wo * ss, Ho * ss
        cam = np.asarray(cam, float)
        if view is None:
            f = np.asarray(target, float) - cam; f /= np.linalg.norm(f)
            r = np.cross([0, 1.0, 0], f); r /= np.linalg.norm(r); u = np.cross(f, r); Rv = np.array([r, u, f])
            fp = (W / 2) / np.tan(np.radians(fov) / 2); cxp, cyp = W / 2, H / 2
        else:
            Rv = np.asarray(view['R'], float); fp = view['f'] * ss; cxp, cyp = view['cx'] * ss, view['cy'] * ss
        Vs, Ns, UVs, Fs, mat = [], [], [], [], []; off = 0
        for i, (V, N, UV, F, tex) in enumerate(self.parts):
            Vs.append(V); Ns.append(N); UVs.append(UV if UV is not None else np.zeros((len(V), 2))); Fs.append(F + off)
            mat.append(np.full(len(F), i)); off += len(V)
        V = np.vstack(Vs); N = np.vstack(Ns); UV = np.vstack(UVs); F = np.vstack(Fs); mat = np.concatenate(mat)
        Pc = (V - cam) @ Rv.T
        X = cxp + fp * Pc[:, 0] / np.maximum(Pc[:, 2], 1e-3); Y = cyp - fp * Pc[:, 1] / np.maximum(Pc[:, 2], 1e-3)
        zb, tid, b0, b1 = self._raster(X, Y, Pc[:, 2], F, W, H)
        # ---- shadow map (orthographic from the sun)
        L = np.asarray(sun, float); L /= np.linalg.norm(L)
        lr = np.cross([0, 1.0, 0] if abs(L[1]) < 0.99 else [1.0, 0, 0], -L); lr /= np.linalg.norm(lr); lu = np.cross(-L, lr)
        Rl = np.array([lr, lu, -L]); veh = np.vstack([p[0] for p in self.parts if p[0].shape[0] < 20000 or True])
        core = V[np.abs(V[:, 0]) < 6]; core = core[np.abs(core[:, 2]) < 8]
        if shadow_focus is None:
            sctr = core.mean(0); ext = np.abs(((core - sctr) @ Rl.T)[:, :2]).max() * 1.15
        else:
            sctr = np.asarray(shadow_focus[0], float); ext = float(shadow_focus[1])
        Pl = (V - sctr) @ Rl.T
        SM = 2048; sc = SM / (2 * ext); texel = 2 * ext / SM
        Xl = SM / 2 + Pl[:, 0] * sc; Yl = SM / 2 - Pl[:, 1] * sc; Zl = Pl[:, 2] + 50
        szb, _, _, _ = self._raster(Xl, Yl, Zl, F, SM, SM)
        # ---- shading
        hit = tid >= 0; t = tid[hit]; w0 = b0[hit]; w1 = b1[hit]; w2 = 1 - w0 - w1
        a, b, c = F[t, 0], F[t, 1], F[t, 2]
        iz0, iz1, iz2 = 1 / Pc[a, 2], 1 / Pc[b, 2], 1 / Pc[c, 2]
        q0, q1, q2 = w0 * iz0, w1 * iz1, w2 * iz2; qs = q0 + q1 + q2; q0 /= qs; q1 /= qs; q2 /= qs
        Pw = V[a] * q0[:, None] + V[b] * q1[:, None] + V[c] * q2[:, None]
        Nw = N[a] * q0[:, None] + N[b] * q1[:, None] + N[c] * q2[:, None]
        Nw /= np.linalg.norm(Nw, axis=1, keepdims=True) + 1e-9
        vd = cam - Pw; vd /= np.linalg.norm(vd, axis=1, keepdims=True)
        flip = np.sum(Nw * vd, 1) < 0; Nw[flip] *= -1                                   # two-sided lighting
        uvp = UV[a] * q0[:, None] + UV[b] * q1[:, None] + UV[c] * q2[:, None]
        alb = np.zeros((len(t), 3), np.float32); mt = mat[t]
        for i, part in enumerate(self.parts):
            s = mt == i
            if not s.any(): continue
            tex = part[4]
            if isinstance(tex, tuple):        # tiled procedural texture
                img = tex[1]; th, tw = img.shape[:2]; uu = (uvp[s, 0] % 1) * tw; vv = (uvp[s, 1] % 1) * th
                alb[s] = img[vv.astype(int) % th, uu.astype(int) % tw]
            elif tex.ndim == 1: alb[s] = tex
            else:                              # bilinear
                th, tw = tex.shape[:2]; uu = np.clip(uvp[s, 0], 0, 1) * tw - 0.5; vv = np.clip(uvp[s, 1], 0, 1) * th - 0.5
                x0 = np.floor(uu).astype(int); y0 = np.floor(vv).astype(int); fx = (uu - x0)[:, None]; fy = (vv - y0)[:, None]
                x0c, x1c = np.clip(x0, 0, tw - 1), np.clip(x0 + 1, 0, tw - 1); y0c, y1c = np.clip(y0, 0, th - 1), np.clip(y0 + 1, 0, th - 1)
                alb[s] = (tex[y0c, x0c] * (1 - fx) * (1 - fy) + tex[y0c, x1c] * fx * (1 - fy) + tex[y1c, x0c] * (1 - fx) * fy + tex[y1c, x1c] * fx * fy)
        # shadow lookup with slope bias
        pl = (Pw - sctr) @ Rl.T; sx = (SM / 2 + pl[:, 0] * sc).astype(int); sy = (SM / 2 - pl[:, 1] * sc).astype(int)
        inb = (sx >= 0) & (sx < SM) & (sy >= 0) & (sy < SM); ndl = np.sum(Nw * L, 1)
        bias = (3.4 + 6.8 * np.sqrt(np.clip(1 - ndl ** 2, 0, 1))) * texel           # 2 + 4 cm with the whole-scene map
        lit = np.ones(len(t), np.float32)
        # v25: 3x3 percentage-closer filtering (soft shadow edges instead of texel staircases)
        acc = np.zeros(int(inb.sum()), np.float32); zq = pl[inb, 2] + 50 - bias[inb]
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                acc += (zq <= szb[np.clip(sy[inb] + dy, 0, SM - 1), np.clip(sx[inb] + dx, 0, SM - 1)]).astype(np.float32)
        lit[inb] = acc / 9.0
        # ambient occlusion (hemisphere samples tested against the camera depth buffer)
        occ = np.zeros(len(t), np.float32)
        if ao:
            rng = np.random.default_rng(7); K = 14
            tang = np.cross(Nw, [0, 1.0, 0]); bad = np.linalg.norm(tang, axis=1) < 0.1; tang[bad] = np.cross(Nw[bad], [1.0, 0, 0])
            tang /= np.linalg.norm(tang, axis=1, keepdims=True); bit = np.cross(Nw, tang)
            for k in range(K):
                v = rng.standard_normal(3); v[2] = abs(v[2]) + 0.15; v /= np.linalg.norm(v); rad = 0.06 + 0.22 * (k + 1) / K
                sp = Pw + (tang * v[0] + bit * v[1] + Nw * v[2]) * rad
                sc_ = (sp - cam) @ Rv.T; sxp = (cxp + fp * sc_[:, 0] / np.maximum(sc_[:, 2], 1e-3)).astype(int); syp = (cyp - fp * sc_[:, 1] / np.maximum(sc_[:, 2], 1e-3)).astype(int)
                ok = (sxp >= 0) & (sxp < W) & (syp >= 0) & (syp < H)
                dz = np.full(len(t), np.inf); dz[ok] = zb[syp[ok], sxp[ok]]
                o = (dz < sc_[:, 2] - 0.02) & (sc_[:, 2] - dz < 0.6)
                occ += o
            occ /= K
        aof = 1 - 0.75 * occ
        sky = np.array([0.55, 0.62, 0.72]); gnd = np.array([0.32, 0.30, 0.24]); suncol = np.array([1.05, 0.98, 0.86])
        hemi = sky * (0.5 + 0.5 * Nw[:, 1:2]) + gnd * (0.5 - 0.5 * Nw[:, 1:2])
        diff = np.clip(ndl, 0, None)[:, None] * lit[:, None] * suncol
        hv = L + vd; hv /= np.linalg.norm(hv, axis=1, keepdims=True)
        spec = (np.clip(np.sum(Nw * hv, 1), 0, 1) ** 40 * 0.18 * lit)[:, None]
        col = alb * (hemi * 0.85 * aof[:, None] + diff * 1.05) + spec * aof[:, None]
        img = np.zeros((H, W, 3), np.float32)
        gy = np.linspace(0, 1, H)[:, None, None]; img[:] = (np.array([0.70, 0.78, 0.86]) * (1 - gy) + np.array([0.88, 0.89, 0.88]) * gy)
        img[hit] = col
        img = img.reshape(Ho, ss, Wo, ss, 3).mean((1, 3))
        img = np.clip(img, 0, 1) ** (1 / 1.15)
        return Image.fromarray((img * 255).astype(np.uint8))

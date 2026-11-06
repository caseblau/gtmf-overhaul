"""textured z-buffer preview of an exported LOD OBJ: python tex_preview.py in.obj texture.png out.png"""
import sys, numpy as np
from PIL import Image
def load(p):
    V = []; T = []; F = []
    for l in open(p):
        if l.startswith('v '): V.append([float(x) for x in l.split()[1:4]])
        elif l.startswith('vt '): T.append([float(x) for x in l.split()[1:3]])
        elif l.startswith('f '): F.append([int(t.split('/')[0]) - 1 for t in l.split()[1:4]])
    V = np.array(V); V[:, 2] *= -1
    return V, np.array(T), np.array(F)
def render(V, T, F, tex, R, size, s, c=np.zeros(3)):
    P = (V - c) @ R.T; X = size / 2 + P[:, 0] * s; Y = size / 2 - P[:, 1] * s; Z = P[:, 2]
    tri = P[F]; n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]); n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    L = np.array([-0.4, 0.8, 0.45]); L /= np.linalg.norm(L); sh = np.abs(n @ L) * 0.75 + 0.35
    th, tw = tex.shape[:2]
    zb = np.full((size, size), -1e9); img = np.full((size, size, 3), 230.0)
    for k, (a, b, c_) in enumerate(F):
        xs = X[[a, b, c_]]; ys = Y[[a, b, c_]]; zs = Z[[a, b, c_]]
        x0, x1 = int(max(0, np.floor(xs.min()))), int(min(size - 1, np.ceil(xs.max()))); y0, y1 = int(max(0, np.floor(ys.min()))), int(min(size - 1, np.ceil(ys.max())))
        if x1 < x0 or y1 < y0: continue
        d = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
        if abs(d) < 1e-12: continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        w0 = ((ys[1] - ys[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gy - ys[2])) / d; w1 = ((ys[2] - ys[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gy - ys[2])) / d; w2 = 1 - w0 - w1
        m = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        if not m.any(): continue
        z = w0 * zs[0] + w1 * zs[1] + w2 * zs[2]
        sub = zb[y0:y1 + 1, x0:x1 + 1]; upd = m & (z > sub)
        if not upd.any(): continue
        sub[upd] = z[upd]
        uv = T[[a, b, c_]]
        u = w0 * uv[0, 0] + w1 * uv[1, 0] + w2 * uv[2, 0]; v = 1 - (w0 * uv[0, 1] + w1 * uv[1, 1] + w2 * uv[2, 1])
        px = np.clip((u * tw).astype(int), 0, tw - 1); py = np.clip((v * th).astype(int), 0, th - 1)
        col = tex[py, px] * sh[k]
        img[y0:y1 + 1, x0:x1 + 1][upd] = col[upd]
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
if __name__ == '__main__':
    V, T, F = load(sys.argv[1]); tex = np.asarray(Image.open(sys.argv[2]).convert('RGB'), float)
    def yaw_pitch(yaw, pitch):
        R0 = np.array([[-1, 0, 0], [0, 1, 0], [0, 0, 1]], float)
        a, b = np.radians(yaw), np.radians(pitch)
        Ry = np.array([[np.cos(a), 0, np.sin(a)], [0, 1, 0], [-np.sin(a), 0, np.cos(a)]]); Rx = np.array([[1, 0, 0], [0, np.cos(b), -np.sin(b)], [0, np.sin(b), np.cos(b)]])
        return Rx @ Ry @ R0
    ims = [render(V, T, F, tex, yaw_pitch(-35, 18), 800, 110, np.array([0, 0.0, 0.3])),
           render(V, T, F, tex, yaw_pitch(150, 22), 800, 110, np.array([0, 0.0, 0.0]))]
    W = Image.new('RGB', (1600, 800)); W.paste(ims[0], (0, 0)); W.paste(ims[1], (800, 0)); W.save(sys.argv[3])

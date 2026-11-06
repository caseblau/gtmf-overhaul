"""perspective textured render of an exported OBJ (game frame), to compare with photographs.
render(V, T, F, tex, cam, target, fov_deg, W, H, elev_gun=0)"""
import numpy as np
from PIL import Image
def look(cam, target):
    f = np.asarray(target, float) - cam; f /= np.linalg.norm(f)
    r = np.cross([0, 1.0, 0], f); r /= np.linalg.norm(r)       # left-handed game frame: screen right = up x forward
    u = np.cross(f, r)
    return np.array([r, u, f])
def render(V, T, F, tex, cam, target, fov, W=800, H=600, light=(-0.4, 0.8, 0.45)):
    cam = np.asarray(cam, float); R = look(cam, target)
    P = (V - cam) @ R.T; z = P[:, 2]; fpx = (W / 2) / np.tan(np.radians(fov) / 2)
    X = W / 2 + fpx * P[:, 0] / np.maximum(z, 1e-3); Y = H / 2 - fpx * P[:, 1] / np.maximum(z, 1e-3)
    tri = V[F]; n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]); n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    L = np.asarray(light, float); L /= np.linalg.norm(L); sh = np.abs(n @ L) * 0.7 + 0.35
    th, tw = tex.shape[:2]; zb = np.full((H, W), 1e9); img = np.full((H, W, 3), 225.0)
    for k, (a, b, c) in enumerate(F):
        if min(z[a], z[b], z[c]) < 0.05: continue
        xs = X[[a, b, c]]; ys = Y[[a, b, c]]; iz = 1 / z[[a, b, c]]
        x0, x1 = int(max(0, np.floor(xs.min()))), int(min(W - 1, np.ceil(xs.max()))); y0, y1 = int(max(0, np.floor(ys.min()))), int(min(H - 1, np.ceil(ys.max())))
        if x1 < x0 or y1 < y0: continue
        d = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
        if abs(d) < 1e-12: continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        w0 = ((ys[1] - ys[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gy - ys[2])) / d; w1 = ((ys[2] - ys[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gy - ys[2])) / d; w2 = 1 - w0 - w1
        m = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        if not m.any(): continue
        izp = w0 * iz[0] + w1 * iz[1] + w2 * iz[2]; zz = 1 / izp
        sub = zb[y0:y1 + 1, x0:x1 + 1]; upd = m & (zz < sub)
        if not upd.any(): continue
        sub[upd] = zz[upd]
        uv = T[[a, b, c]]
        u = (w0 * uv[0, 0] * iz[0] + w1 * uv[1, 0] * iz[1] + w2 * uv[2, 0] * iz[2]) / izp
        v = 1 - (w0 * uv[0, 1] * iz[0] + w1 * uv[1, 1] * iz[1] + w2 * uv[2, 1] * iz[2]) / izp
        px = np.clip((u * tw).astype(int), 0, tw - 1); py = np.clip((v * th).astype(int), 0, th - 1)
        img[y0:y1 + 1, x0:x1 + 1][upd] = (tex[py, px] * sh[k])[upd]
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))

"""orthographic line render (outline + creases) of an exported OBJ for overlaying on scale drawings.
python overlay_render.py in.obj out.png view px_per_m  ->  prints the world coords of pixel (0,0)
views: side (left side, front to the left), top (front left, right side up), front"""
import sys, numpy as np
from PIL import Image
sys.path.insert(0, __import__('os').path.dirname(__file__))
from tex_preview import load
import geom
VIEWS = {'side': np.array([[0, 0, -1], [0, 1, 0], [-1, 0, 0]], float),
         'top': np.array([[0, 0, -1], [1, 0, 0], [0, 1, 0]], float),
         'front': np.array([[-1, 0, 0], [0, 1, 0], [0, 0, 1]], float)}
def main(obj, out, view, s, extra=None):
    V, T, F = load(obj)
    if extra:
        for v, f in extra: F = np.vstack([F, f + len(V)]); V = np.vstack([V, v])
    R = VIEWS[view]; P = V @ R.T
    x0, y1 = P[:, 0].min() - 0.05, P[:, 1].max() + 0.05; x1, y0 = P[:, 0].max() + 0.05, P[:, 1].min() - 0.05
    W, H = int((x1 - x0) * s) + 1, int((y1 - y0) * s) + 1
    X = (P[:, 0] - x0) * s; Y = (y1 - P[:, 1]) * s; Z = P[:, 2]
    n = geom.normals(V, F)
    zb = np.full((H, W), -1e9); fid = np.full((H, W), -1)
    for k, (a, b, c) in enumerate(F):
        xs = X[[a, b, c]]; ys = Y[[a, b, c]]; zs = Z[[a, b, c]]
        xa, xb = int(max(0, np.floor(xs.min()))), int(min(W - 1, np.ceil(xs.max()))); ya, yb = int(max(0, np.floor(ys.min()))), int(min(H - 1, np.ceil(ys.max())))
        if xb < xa or yb < ya: continue
        d = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
        if abs(d) < 1e-12: continue
        gx, gy = np.meshgrid(np.arange(xa, xb + 1) + 0.5, np.arange(ya, yb + 1) + 0.5)
        w0 = ((ys[1] - ys[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gy - ys[2])) / d; w1 = ((ys[2] - ys[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gy - ys[2])) / d; w2 = 1 - w0 - w1
        m = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        z = w0 * zs[0] + w1 * zs[1] + w2 * zs[2]
        sub = zb[ya:yb + 1, xa:xb + 1]; upd = m & (z > sub); sub[upd] = z[upd]; fid[ya:yb + 1, xa:xb + 1][upd] = k
    nb = np.where(fid[..., None] >= 0, n[np.maximum(fid, 0)], 0)
    edge = np.zeros((H, W), bool)
    for dy, dx in ((0, 1), (1, 0)):
        a = nb[:H - dy, :W - dx]; b = nb[dy:, dx:]
        dn = 1 - np.sum(a * b, -1); dz = np.abs(zb[:H - dy, :W - dx] - zb[dy:, dx:])
        fa, fb = fid[:H - dy, :W - dx] >= 0, fid[dy:, dx:] >= 0
        e = (fa & fb & ((dn > 0.15) | (dz > 0.05))) | (fa != fb)
        edge[:H - dy, :W - dx] |= e
    img = np.zeros((H, W, 4), np.uint8); img[edge] = [230, 0, 0, 255]
    img[(fid >= 0) & ~edge] = [255, 60, 0, 40]
    Image.fromarray(img, 'RGBA').save(out, optimize=True)
    # pixel (0,0) in world terms
    print('origin', view, 'screen_x0=%.4f screen_y1=%.4f size %dx%d' % (x0, y1, W, H))
if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]))

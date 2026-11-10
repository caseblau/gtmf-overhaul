"""Offline look at a built mesh: side, front, three-quarter and top views at LOD 1 with the atlas colours, flat shaded.
  python bought_preview.py <mesh> <diffuse texture file> <out.png> [wheels mesh for the running gear circles]
Hidden faces are culled as the game does (a see-through plate in this picture is a see-through plate in the game)."""
import sys, os, re, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import azg2, atf1
from PIL import Image, ImageDraw

def load(mesh):
    m = azg2.read(mesh); tmp = mesh + '.preview.obj'; azg2.export_obj(m, 1, tmp)
    V, T, F = [], [], []
    for l in open(tmp):
        t = l.split()
        if not t: continue
        if t[0] == 'v': V.append(list(map(float, t[1:4])))
        elif t[0] == 'vt': T.append(list(map(float, t[1:3])))
        elif t[0] == 'f':
            q = [a.split('/') for a in t[1:4]]; F.append([[int(a[0]) - 1, int(a[1]) - 1 if len(a) > 1 and a[1] else 0] for a in q])
    os.remove(tmp)
    return np.array(V), np.array(T) if T else np.zeros((1, 2)), np.array(F)

def subdivide(V, T, F, big=0.004, n=4):
    """large faces in small flat pieces, so the colours in the picture follow the texture as they will in the game"""
    pts = V[F[:, :, 0]]; area = np.linalg.norm(np.cross(pts[:, 1] - pts[:, 0], pts[:, 2] - pts[:, 0]), axis=1) / 2
    vs, ts, fs = [V], [T[np.clip(np.arange(len(V)), 0, len(T) - 1)]], [np.stack([F[area <= big, :, 0], F[area <= big, :, 0]], -1)]; o = len(V)
    bary = [(i / n, j / n, 1 - (i + j) / n) for i in range(n + 1) for j in range(n + 1 - i)]; idx = {(i, j): k for k, (i, j) in enumerate((i, j) for i in range(n + 1) for j in range(n + 1 - i))}
    tri = []
    for i in range(n):
        for j in range(n - i):
            tri.append((idx[(i, j)], idx[(i + 1, j)], idx[(i, j + 1)]))
            if i + j < n - 1: tri.append((idx[(i + 1, j)], idx[(i + 1, j + 1)], idx[(i, j + 1)]))
    B = np.array(bary); tri = np.array(tri)
    for f in F[area > big]:
        p = V[f[:, 0]]; t = T[f[:, 1]]
        vs.append(B @ p); ts.append(B @ t); q = tri + o; fs.append(np.stack([q, q], -1)); o += len(B)
    return np.vstack(vs), np.vstack(ts), np.vstack(fs)

def view(V, T, F, tex, R, S, wheels=None):
    P = V @ R.T
    pts = P[F[:, :, 0]]; n = np.cross(pts[:, 1] - pts[:, 0], pts[:, 2] - pts[:, 0]); L = np.linalg.norm(n, axis=1); n = n / np.maximum(L, 1e-9)[:, None]
    uv = T[F[:, :, 1]].mean(1); uv[:, 1] = 1.0 - uv[:, 1]; h, w = tex.shape[:2]   # the export writes v upward
    col = tex[np.clip((uv[:, 1] * h).astype(int), 0, h - 1), np.clip((uv[:, 0] * w).astype(int), 0, w - 1), :3].astype(float)
    front = n[:, 2] < 0                                    # looking along +z of the view frame; left-handed game frame
    lo = P[:, :2].min(0); hi = P[:, :2].max(0); k = (S - 20) / max(hi - lo)
    im = Image.new('RGB', (S, S), (235, 235, 230)); dr = ImageDraw.Draw(im)
    light = np.abs(n @ (np.array([-0.4, 0.8, -0.45]) / np.linalg.norm([-0.4, 0.8, -0.45]))) * 0.75 + 0.45
    for i in np.argsort(-pts[:, :, 2].mean(1)):
        if not front[i]: continue
        c = tuple(np.clip(col[i] * light[i] * 1.6, 0, 255).astype(int).tolist())
        dr.polygon([(10 + (a - lo[0]) * k, S - 10 - (b - lo[1]) * k) for a, b in pts[i, :, :2]], fill=c)
    if wheels is not None:
        Q = wheels[0] @ R.T
        for p, r in zip(Q, wheels[1]):
            x, y = 10 + (p[0] - lo[0]) * k, S - 10 - (p[1] - lo[1]) * k; dr.ellipse((x - r * k, y - r * k, x + r * k, y + r * k), outline=(200, 30, 30), width=2)
    return im

def rot(yaw, pitch=0.0):
    a, b = np.radians(yaw), np.radians(pitch); Y = np.array([[np.cos(a), 0, -np.sin(a)], [0, 1, 0], [np.sin(a), 0, np.cos(a)]]); X = np.array([[1, 0, 0], [0, np.cos(b), np.sin(b)], [0, -np.sin(b), np.cos(b)]])
    return X @ Y

if __name__ == '__main__':
    mesh, texp, out = sys.argv[1:4]
    V, T, F = load(mesh); tex = np.asarray(atf1.top(texp)); print('faces', len(F), 'verts', len(V), 'bbox', V.min(0).round(2), V.max(0).round(2)); V, T, F = subdivide(V, T, F)
    wheels = None
    if len(sys.argv) > 4:
        m = azg2.read(sys.argv[4]) if False else None
    S = 900; W = Image.new('RGB', (S * 2, S * 2), 'white')
    for k, (yaw, pitch) in enumerate(((90, 0), (0, 0), (135, 25), (45, 25))):
        W.paste(view(V, T, F, tex, rot(yaw, pitch), S), ((k % 2) * S, (k // 2) * S))
    W.save(out)

"""N11c: remove pixel staircase / jitter: Gaussian smoothing (sigma 12 m) along each line between its fixed
vertices (ends and vertices shared with other lines stay exact), then simplify (1.5 m) and keep vertices <= 25 m."""
import json, numpy as np
from scipy.ndimage import gaussian_filter1d
D = '/mnt/user-data/outputs/roadgraph/n11/'
J = json.load(open(D + 'roads_1941.json', encoding='utf-8')); R = J['roads']
from collections import Counter
cnt = Counter((round(p[0], 1), round(p[1], 1)) for r in R for p in r['pts'])
ends = set((round(r['pts'][i][0], 1), round(r['pts'][i][1], 1)) for r in R for i in (0, -1))
def rdp(p, eps):
    if len(p) < 3: return p
    a, b = p[0], p[-1]; ab = b - a; L = np.hypot(*ab)
    d = np.abs(ab[0] * (p[:, 1] - a[1]) - ab[1] * (p[:, 0] - a[0])) / L if L > 0 else np.hypot(*(p - a).T)
    i = int(np.argmax(d))
    if d[i] <= eps: return np.array([a, b])
    return np.vstack([rdp(p[:i + 1], eps)[:-1], rdp(p[i:], eps)])
def piece(seg):
    s = np.r_[0, np.cumsum(np.hypot(*np.diff(seg, axis=0).T))]
    if s[-1] < 20: return seg
    n = max(3, int(s[-1] / 4) + 1); t = np.linspace(0, s[-1], n)
    q = np.c_[np.interp(t, s, seg[:, 0]), np.interp(t, s, seg[:, 1])]
    sm = np.c_[gaussian_filter1d(q[:, 0], 3, mode='nearest'), gaussian_filter1d(q[:, 1], 3, mode='nearest')]
    w = np.minimum(1, np.minimum(t, s[-1] - t) / 12.0)[:, None]      # ease back to the exact fixed vertices
    q = q * (1 - w) + sm * w
    return rdp(q, 1.5)
for r in R:
    p = np.asarray(r['pts'], float); key = [(round(x, 1), round(y, 1)) for x, y in p]
    fx = [0] + [i for i in range(1, len(p) - 1) if cnt[key[i]] > 1 or key[i] in ends] + [len(p) - 1]
    out = [p[:1]]
    for a, b in zip(fx[:-1], fx[1:]): out.append(piece(p[a:b + 1])[1:])
    q = np.vstack(out); dense = [q[0]]
    for a, b in zip(q[:-1], q[1:]):
        k = max(1, int(np.ceil(np.hypot(*(b - a)) / 25)))
        for j in range(1, k + 1): dense.append(a + (b - a) * j / k)
    pts = [[round(float(x), 1), round(float(y), 1)] for x, y in dense]
    for i in fx: pts[[0, -1][i == len(p) - 1] if i in (0, len(p) - 1) else 0]  # no-op, fixed handled below
    pts[0] = list(p[0]); pts[-1] = list(p[-1])
    r['pts'] = pts
json.dump(J, open(D + 'roads_1941.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('smoothed', len(R))

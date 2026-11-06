"""N11d: natural road geometry. Removes the pixel staircase, small wobble and junction zigzags left by tracing and
map-matching, while keeping every line within TOL of where it was (so it stays on the drawn road) and keeping line
ends and shared junction vertices exact.
Per line, between fixed vertices: drop spikes (turns > 100 deg), resample 5 m, then 40 rounds of Gaussian smoothing
(sigma 25 m) each followed by a clamp back to <= TOL from the original line; ease into the fixed vertices over 25 m.
  python3 natural.py <in.json> <out.json>"""
import sys, json, numpy as np
from collections import Counter
from scipy.ndimage import gaussian_filter1d
from scipy.spatial import cKDTree
import importlib.util
_sp = importlib.util.spec_from_file_location('ev', '/mnt/user-data/outputs/roadgraph/n1/eval_roads.py'); ev = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(ev)
DT, _, ROK = ev.c1_masks('/mnt/user-data/outputs/roadgraph/n1')
def on_ink(q):
    px, py = ev.m_to_px(q[:, 0], q[:, 1]); ix = np.clip(np.round(px).astype(int), 0, DT.shape[1] - 1); iy = np.clip(np.round(py).astype(int), 0, DT.shape[0] - 1)
    return (DT[iy, ix] <= 7.0) | ROK[iy, ix]
TOL = {'secondary': 4.0, 'track': 4.0, 'path': 4.0, 'residential': 3.0}

def resample(p, step):
    s = np.r_[0, np.cumsum(np.hypot(*np.diff(p, axis=0).T))]
    if s[-1] == 0: return p[:1]
    n = max(2, int(np.ceil(s[-1] / step)) + 1); t = np.linspace(0, s[-1], n)
    return np.c_[np.interp(t, s, p[:, 0]), np.interp(t, s, p[:, 1])]

def despike(p):
    keep = True
    while keep and len(p) > 2:
        keep = False
        d = np.diff(p, axis=0); a = np.arctan2(d[:, 1], d[:, 0])
        da = np.degrees(np.abs((np.diff(a) + np.pi) % (2 * np.pi) - np.pi))
        i = np.nonzero(da > 100)[0]
        if len(i): p = np.delete(p, i[0] + 1, axis=0); keep = True
    return p

def rdp(p, eps):
    if len(p) < 3: return p
    a, b = p[0], p[-1]; ab = b - a; L = np.hypot(*ab)
    d = np.abs(ab[0] * (p[:, 1] - a[1]) - ab[1] * (p[:, 0] - a[0])) / L if L > 0 else np.hypot(*(p - a).T)
    i = int(np.argmax(d))
    if d[i] <= eps: return np.array([a, b])
    return np.vstack([rdp(p[:i + 1], eps)[:-1], rdp(p[i:], eps)])

def smooth_piece(seg, tol):
    seg = despike(seg)
    if len(seg) < 2: return seg
    ref = resample(seg, 1.0); T = cKDTree(ref); ref_on = on_ink(ref)
    q = resample(seg, 5.0)
    if len(q) < 5: return seg
    s = np.r_[0, np.cumsum(np.hypot(*np.diff(q, axis=0).T))]; ease = np.clip(np.minimum(s, s[-1] - s) / 25.0, 0, 1)[:, None]
    a, b = q[0].copy(), q[-1].copy()
    for _ in range(25):
        sm = np.c_[gaussian_filter1d(q[:, 0], 3, mode='nearest'), gaussian_filter1d(q[:, 1], 3, mode='nearest')]
        q = q * (1 - ease) + sm * ease
        d, i = T.query(q); over = d > tol
        if over.any():
            v = q[over] - ref[i[over]]; q[over] = ref[i[over]] + v * (tol / d[over])[:, None]
        # a point that was on the drawn centre line stays on it
        bad = ~on_ink(q) & ref_on[i]
        q[bad] = ref[i[bad]]
        q[0], q[-1] = a, b
    return rdp(q, 0.5)

def main():
    J = json.load(open(sys.argv[1], encoding='utf-8')); R = J['roads']
    key = lambda p: (round(p[0], 1), round(p[1], 1))
    cnt = Counter(key(p) for r in R for p in r['pts'])
    ends = set(key(r['pts'][i]) for r in R for i in (0, -1))
    for r in R:
        p = np.asarray(r['pts'], float); tol = TOL.get(r.get('highway'), 5.0)
        fx = [0] + [i for i in range(1, len(p) - 1) if cnt[key(r['pts'][i])] > 1 or key(r['pts'][i]) in ends] + [len(p) - 1]
        parts = [p[:1]]
        for a, b in zip(fx[:-1], fx[1:]): parts.append(smooth_piece(p[a:b + 1], tol)[1:])
        q = np.vstack(parts); dense = [q[0]]
        for a, b in zip(q[:-1], q[1:]):
            k = max(1, int(np.ceil(np.hypot(*(b - a)) / 25)))
            for j in range(1, k + 1): dense.append(a + (b - a) * j / k)
        pts = [[round(float(x), 1), round(float(y), 1)] for x, y in dense]
        for i in fx: pass
        pts[0] = r['pts'][0]; pts[-1] = r['pts'][-1]
        r['pts'] = pts
    json.dump(J, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

if __name__ == '__main__':
    main()

"""Take the scan noise out of the road lines traced from the 1941 sheet (9 Nov, user: 'some roads are jittery').

The traces follow map ink at 12 m per source pixel, so a road the sheet draws straight comes out with steps of 5-15 m, and
the ink of a street bends round the house symbols.  Anything below that scale is noise, not road: short spikes are removed
and the line is resampled and averaged along its length (Gaussian, SIGMA metres), which straightens the straights and only
rounds the real bends a little.  Simplifying with Douglas-Peucker was tried first and kept the noise as longer zigzags.
Ends never move except to stay on the road they joined.
"""
import math
import numpy as np

SIGMA = {'secondary': 40.0, 'track': 35.0, 'path': 35.0, 'residential': 22.0}
STEP = 4.0
SNAP = 6.0          # a line end this close to another line is a junction on it


def _despike(pts, max_turn=120.0, max_len=25.0):
    """drop vertices where the line doubles back over a short distance (trace errors at house symbols and junctions)"""
    p = [tuple(q[:2]) for q in pts]
    changed = True
    while changed and len(p) > 2:
        changed = False
        for i in range(1, len(p) - 1):
            ax, ay = p[i][0] - p[i - 1][0], p[i][1] - p[i - 1][1]
            bx, by = p[i + 1][0] - p[i][0], p[i + 1][1] - p[i][1]
            la, lb = math.hypot(ax, ay), math.hypot(bx, by)
            if la < 1e-6 or lb < 1e-6:
                del p[i]; changed = True; break
            turn = math.degrees(math.acos(max(-1.0, min(1.0, (ax * bx + ay * by) / (la * lb)))))
            if turn > max_turn and min(la, lb) < max_len:
                del p[i]; changed = True; break
    return p


def _gauss(p, sigma):
    """resample every STEP m and average along the line; the ends stay fixed (odd reflection about each end)"""
    a = np.asarray(p, np.float64); s_ = np.r_[0.0, np.cumsum(np.hypot(*np.diff(a, axis=0).T))]
    L = s_[-1]
    if L < 2 * STEP: return [tuple(q) for q in a]
    n = int(L / STEP) + 1; t = np.linspace(0.0, L, n)
    q = np.c_[np.interp(t, s_, a[:, 0]), np.interp(t, s_, a[:, 1])]
    sig = min(sigma, L / 6.0) / (L / (n - 1))          # short lines: no more than a sixth of their length
    if sig < 0.5: return [tuple(v) for v in q]
    from scipy.ndimage import gaussian_filter1d
    m = min(n - 1, int(4 * sig) + 1)
    pad = np.r_[2 * q[0] - q[m:0:-1], q, 2 * q[-1] - q[-2:-m - 2:-1]]
    out = gaussian_filter1d(pad, sig, axis=0, mode='nearest')[m:m + n]
    out[0] = q[0]; out[-1] = q[-1]
    return [tuple(v) for v in out]


def _nearest(p, line):
    """nearest point on a polyline to p: (distance, point)"""
    a = np.asarray(line, np.float64); s = a[:-1]; d = a[1:] - s
    t = np.clip(((np.asarray(p) - s) * d).sum(1) / np.maximum((d * d).sum(1), 1e-9), 0, 1)
    q = s + d * t[:, None]; e = np.hypot(*(q - np.asarray(p)).T); k = int(e.argmin())
    return float(e[k]), tuple(q[k])


def smooth(roads):
    """new list of road dicts with cleaned 'pts'; the input is left alone"""
    orig = [[tuple(q[:2]) for q in r['pts']] for r in roads]
    new = []
    for r, p in zip(roads, orig):
        q = _gauss(_despike(p), SIGMA.get(r.get('highway'), 30.0)) if len(p) > 2 else p
        new.append(q)
    # junctions: an end that met another road keeps meeting it; only roads with no shared end point move
    ok = [i for i, p in enumerate(orig) if len(p) >= 2]
    box = {i: (min(x for x, _ in orig[i]) - SNAP, max(x for x, _ in orig[i]) + SNAP, min(y for _, y in orig[i]) - SNAP, max(y for _, y in orig[i]) + SNAP) for i in ok}
    for i in ok:
        for end in (0, -1):
            x, y = orig[i][end]; best = None
            for j in ok:
                if j == i: continue
                b = box[j]
                if not (b[0] <= x <= b[1] and b[2] <= y <= b[3]): continue
                e, _ = _nearest((x, y), orig[j])
                if e <= SNAP and (best is None or e < best[0]): best = (e, j)
            if best is not None:
                _, q = _nearest((x, y), new[best[1]])
                new[i][end] = q
    return [dict(r, pts=[list(q) for q in p]) for r, p in zip(roads, new)]

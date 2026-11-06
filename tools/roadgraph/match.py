"""Code node N10b: map-match every traced line onto the drawn centre lines (frozen v3 c1_centre).
The region nodes decided WHICH lines are roads; this pass puts each one exactly on the centre of the drawn symbol.
Between consecutive fixed vertices (line ends, shared junction vertices) a least-cost path is routed inside a 40 m
corridor round the trace: cost 1 per px on the centre line, 30 per px on paper, so the route follows the drawn
line and crosses only short gaps (dash gaps, lettering, junction knots) straight. Village points are free (streets
are drawn as light lanes). A line takes the matched geometry only if its C1 share rises and the route never leaves
the corridor.   python3 match.py <in.json> <out.json>"""
import sys, json, importlib.util, numpy as np
from scipy import ndimage as ndi
from skimage.graph import MCP_Geometric
from PIL import Image, ImageDraw
spec = importlib.util.spec_from_file_location('ev', '/mnt/user-data/outputs/roadgraph/n1/eval_roads.py')
ev = importlib.util.module_from_spec(spec); spec.loader.exec_module(ev)
RD = '/mnt/user-data/outputs/roadgraph/n1'
dt, _, rok = ev.c1_masks(RD)
cen = ev.load_mask(RD + '/c1_centre.png')
H, W = dt.shape
# the railway is a wall except at the drawn crossings (crossings.json), so a route never jumps sides
_rl = json.load(open(RD + '/railway.json'))['lines']; _cr = json.load(open(RD + '/crossings.json'))['crossings']
_im = Image.new('L', (W, H), 0); _d = ImageDraw.Draw(_im)
for L in _rl: _d.line([ev.m_to_px(x, y) for x, y in L['pts']], fill=255, width=5)
for c in _cr:
    cx, cy = ev.m_to_px(c['x'], c['y']); _d.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=0)
WALL = np.asarray(_im) > 0
CORR_PX = 10; PAPER = 30.0

def share(p):
    q, w = ev.densify(p, 4.0); px, py = ev.m_to_px(q[:, 0], q[:, 1])
    ix = np.clip(np.round(px).astype(int), 0, W - 1); iy = np.clip(np.round(py).astype(int), 0, H - 1)
    on = (dt[iy, ix] <= 8) | rok[iy, ix]
    return float((w * on).sum() / max(w.sum(), 1e-9))

def rdp(p, eps):
    if len(p) < 3: return p
    a, b = p[0], p[-1]; ab = b - a; L = np.hypot(*ab)
    d = np.abs(ab[0] * (p[:, 1] - a[1]) - ab[1] * (p[:, 0] - a[0])) / L if L > 0 else np.hypot(*(p - a).T)
    i = int(np.argmax(d))
    if d[i] <= eps: return np.array([a, b])
    return np.vstack([rdp(p[:i + 1], eps)[:-1], rdp(p[i:], eps)])

def dense25(p):
    out = [p[0]]
    for a, b in zip(p[:-1], p[1:]):
        L = np.hypot(*(b - a)); k = max(1, int(np.ceil(L / 25.0)))
        for j in range(1, k + 1): out.append(a + (b - a) * j / k)
    return np.array(out)

def route(seg_m):
    """seg_m: trace polyline (lattice m) between two fixed vertices -> matched polyline (lattice m)"""
    px, py = ev.m_to_px(seg_m[:, 0], seg_m[:, 1]); P = np.c_[px, py]
    x0 = int(max(0, P[:, 0].min() - CORR_PX - 2)); x1 = int(min(W, P[:, 0].max() + CORR_PX + 3))
    y0 = int(max(0, P[:, 1].min() - CORR_PX - 2)); y1 = int(min(H, P[:, 1].max() + CORR_PX + 3))
    im = Image.new('L', (x1 - x0, y1 - y0), 0)
    ImageDraw.Draw(im).line([(x - x0, y - y0) for x, y in P], fill=255, width=1)
    corr = ndi.distance_transform_edt(np.asarray(im) == 0) <= CORR_PX
    c = np.where(cen[y0:y1, x0:x1] | rok[y0:y1, x0:x1], 1.0, PAPER)
    c = np.where(corr & ~WALL[y0:y1, x0:x1], c, np.inf)
    s = (int(round(P[0, 1])) - y0, int(round(P[0, 0])) - x0); e = (int(round(P[-1, 1])) - y0, int(round(P[-1, 0])) - x0)
    if not (corr[s] and corr[e]): return None
    if not (np.isfinite(c[s]) and np.isfinite(c[e])): return None
    m = MCP_Geometric(c, fully_connected=True); cum, _ = m.find_costs([s], [e])
    if not np.isfinite(cum[e]): return None
    path = np.array(m.traceback(e), float)
    q = np.c_[path[:, 1] + x0, path[:, 0] + y0]
    xm, ym = ev.px_to_m(q[:, 0], q[:, 1]); out = np.c_[xm, ym]
    out[0] = seg_m[0]; out[-1] = seg_m[-1]          # the fixed vertices stay exact
    return rdp(out, 3.0)

def match(p, fixed):
    idx = [0] + sorted(fixed) + [len(p) - 1]; parts = []
    for a, b in zip(idx[:-1], idx[1:]):
        r = route(p[a:b + 1])
        if r is None: return None
        parts.append(r[:-1])
    return dense25(np.vstack(parts + [p[-1:]]))

if __name__ == '__main__':
    J = json.load(open(sys.argv[1], encoding='utf-8')); log = []
    ends = set()
    for r in J['roads']:
        q = r['pts']
        if len(q) >= 2: ends.add((round(q[0][0], 1), round(q[0][1], 1))); ends.add((round(q[-1][0], 1), round(q[-1][1], 1)))
    for r in J['roads']:
        p = np.asarray(r['pts'], float)
        if len(p) < 2: continue
        fixed = [i for i in range(1, len(p) - 1) if (round(p[i][0], 1), round(p[i][1], 1)) in ends]
        s0 = share(p); p2 = match(p, fixed)
        if p2 is None: log.append((r.get('name'), 'no-route')); continue
        s1 = share(p2)
        if s1 > s0 + 0.005:
            r['pts'] = [[round(float(x), 1), round(float(y), 1)] for x, y in p2]; r['matched'] = True
            log.append((r.get('name'), round(100 * s0, 1), round(100 * s1, 1)))
    json.dump(J, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    n = sum(1 for g in log if len(g) == 3); print('matched', n, 'of', len(J['roads']), 'lines;', sum(1 for g in log if g[1] == 'no-route'), 'no route')

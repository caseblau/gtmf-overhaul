"""N11b: connect dangling ends (C3) to the nearest other line within 60 m: the end gets a straight link to the
closest point of that line and that point becomes a shared vertex of both lines."""
import json, numpy as np
D = '/mnt/user-data/outputs/roadgraph/'
J = json.load(open(D + 'n11/roads_1941.json', encoding='utf-8')); R = J['roads']
dang = json.load(open(D + 'n12/eval/metrics.json'))['C3']['dangling']
byname = {r['name']: r for r in R}; log = []
def closest(p, pts):
    best = (1e18, None, None)
    for i, (a, b) in enumerate(zip(pts[:-1], pts[1:])):
        a = np.array(a); b = np.array(b); ab = b - a; t = np.clip(((p - a) @ ab) / max(ab @ ab, 1e-9), 0, 1); q = a + t * ab
        d = np.hypot(*(p - q))
        if d < best[0]: best = (d, i, q)
    return best
for d in dang:
    if d['nearest_other_line_m'] is None or d['nearest_other_line_m'] > 60: continue
    r = byname[d['road']]; idx = 0 if d['end'] == 'start' else -1; p = np.array(r['pts'][idx], float)
    best = (1e18,)
    for o in R:
        if o is r: continue
        c = closest(p, o['pts'])
        if c[0] < best[0]: best = c + (o,)
    dist, i, q, o = best
    if dist > 60: continue
    q = [round(float(q[0]), 1), round(float(q[1]), 1)]
    if q not in o['pts']: o['pts'].insert(i + 1, q)
    if idx == 0: r['pts'].insert(0, q)
    else: r['pts'].append(q)
    en = r.get('ends') or ['?', '?']; en[0 if idx == 0 else 1] = 'junction'; r['ends'] = en
    log.append((r['name'], d['end'], o['name'], round(dist, 1)))
json.dump(J, open(D + 'n11/roads_1941.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('connected', len(log)); [print(' ', l) for l in log]

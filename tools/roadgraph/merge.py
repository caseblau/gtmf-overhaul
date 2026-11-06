"""N11 merge: the corrected group files -> one roads_1941.json. Border ends within 15 m of another line end
become one shared vertex (the mean). Duplicate names get a region suffix. Writes roads_1941.json + merge_log.json."""
import json, numpy as np, sys
from scipy.spatial import cKDTree
D = '/mnt/user-data/outputs/roadgraph/n11/'
roads = []
for g in 'ABCDE':
    for r in json.load(open(D + 'fix/%s/out.json' % g, encoding='utf-8'))['roads']:
        if len(r.get('pts', [])) >= 2: r['_g'] = g; roads.append(r)
# ends
E = []
for k, r in enumerate(roads):
    e = r.get('ends') or ['?', '?']
    for side, idx in ((0, 0), (1, -1)):
        E.append((k, idx, tuple(r['pts'][idx]), e[side] if side < len(e) else '?'))
P = np.array([e[2] for e in E], float); T = cKDTree(P)
border = [i for i, e in enumerate(E) if e[3] == 'border']
joined = 0; unmatched = []
done = set()
for i in border:
    if i in done: continue
    nb = [j for j in T.query_ball_point(P[i], 15.0) if j != i and E[j][0] != E[i][0]]
    if not nb: unmatched.append(dict(road=roads[E[i][0]].get('name'), x=P[i][0], y=P[i][1])); continue
    grp = [i] + nb; m = P[grp].mean(0)
    for j in grp:
        k, idx = E[j][0], E[j][1]; roads[k]['pts'][idx] = [round(float(m[0]), 1), round(float(m[1]), 1)]
        en = roads[k].get('ends') or ['?', '?']
        if en[0 if idx == 0 else 1] == 'border': en[0 if idx == 0 else 1] = 'junction'
        roads[k]['ends'] = en; done.add(j)
    joined += 1
# every other end that coincides within 2 m with another end: make the vertex identical
for i in range(len(E)):
    for j in T.query_ball_point(P[i], 2.0):
        if j > i and E[j][0] != E[i][0]:
            k, idx = E[j][0], E[j][1]; roads[k]['pts'][idx] = list(roads[E[i][0]]['pts'][E[i][1]])
seen = {}
for r in roads:
    n = r.get('name', 'x')
    if n in seen: r['name'] = '%s_%s' % (n, r['_g'])
    seen[r['name']] = 1
    r.pop('_g', None); r.pop('matched', None)
meta = {'source': 'RKKA 1941 1:100 000 sheet (rkka100k_block.png); region traces N2-N10, map-matched to the drawn centre lines (n11/match.py), corrected N10c (fix/A-E), merged N11',
        'crs': 'lattice metres, x = 4 px, y = 24576 - 4 py of the sheet raster',
        'ends': "per line [start, end]: junction / street_end / village_edge / dead_end / block_edge / border (left only where no partner)"}
json.dump({'meta': meta, 'roads': roads}, open(D + 'roads_1941.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump({'border_groups_joined': joined, 'border_ends_unmatched': unmatched}, open(D + 'merge_log.json', 'w'), indent=1)
print('roads', len(roads), 'border joins', joined, 'unmatched border ends', len(unmatched))

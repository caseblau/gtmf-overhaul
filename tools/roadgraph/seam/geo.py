"""global grid -> lattice transform: fit on the railway (sheet symbol centre vs OSM main line) by ICP"""
import numpy as np, json, math, sys
from scipy.spatial import cKDTree
import warp
LATS, LONW, LAT_C = 50.904605, 36.4903, 51.0334

def osm_rail():
    data = json.load(open('/mnt/user-data/uploads/gtmf-overhaul/docs/m12_terrain/osm/prokh.osm.json'))
    M_LAT = 111320.0; M_LON = 111320.0 * math.cos(math.radians(LAT_C))
    nodes = {e['id']: ((e['lon'] - LONW) * M_LON, (e['lat'] - LATS) * M_LAT) for e in data['elements'] if e['type'] == 'node'}
    pts = []
    for e in data['elements']:
        t = e.get('tags', {})
        if e['type'] == 'way' and t.get('railway') == 'rail' and t.get('usage') == 'main':
            p = np.array([nodes[n] for n in e['nodes'] if n in nodes])
            for a, b in zip(p[:-1], p[1:]):
                n = max(2, int(np.hypot(*(b - a)) / 4)); pts += list(a + (b - a) * np.linspace(0, 1, n)[:, None])
    O = np.array(pts); return np.c_[O[:, 0] / 4, (20480 - O[:, 1]) / 4]

def uv_all(xy):
    pid = np.searchsorted(warp.SEAMS, xy[:, 1]); U = np.zeros(len(xy)); V = np.zeros(len(xy))
    for P in range(3):
        m = pid == P
        if m.any(): U[m], V[m] = warp.F(P, xy[m, 0], xy[m, 1])
    return np.c_[U, V], pid

def report(M, UV, pid, T, tag):
    A = np.c_[UV, np.ones(len(UV))]; d, i = T.query(A @ M)
    for P in range(3):
        m = pid == P
        if m.any(): print(tag, 'piece', P, 'n', m.sum(), 'median %.1f m  p90 %.1f m' % (4 * np.median(d[m]), 4 * np.percentile(d[m], 90)))

if __name__ == '__main__':
    O = osm_rail(); T = cKDTree(O)
    rc = np.load('../rail_centre.npy'); UV, pid = uv_all(rc)
    A = np.c_[UV, np.ones(len(UV))]
    # reference-piece frame (piece 1 unchanged), as an affine on the rail points
    M1, *_ = np.linalg.lstsq(A[pid == 1], rc[pid == 1], rcond=None)
    report(M1, UV, pid, T, 'piece1 frame')
    M = M1.copy()
    for it in range(40):
        d, i = T.query(A @ M); w = d < np.percentile(d, 90)
        M, *_ = np.linalg.lstsq(A[w], O[i[w]], rcond=None)
    report(M, UV, pid, T, 'OSM-fit frame')
    print('px per grid unit: u %.1f v %.1f; angle of u %.2f deg' % (np.hypot(*M[0]), np.hypot(*M[1]), math.degrees(math.atan2(M[0, 1], M[0, 0]))))
    np.save('G.npy', M); np.save('G1.npy', M1)

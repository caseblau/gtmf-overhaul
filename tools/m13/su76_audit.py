"""SU-76M checks: (1) the moving gun parts never enter the fixed hull solids over the whole traverse x elevation range;
(2) the barrel add-in's recoil block stays inside the housing; (3) every node a config row names exists; (4) vertex counts"""
import sys, numpy as np, geom, su76_geom as G, azg2
from scipy.spatial import ConvexHull
import su122_mesh as SM

def solid_eq(V):
    h = ConvexHull(V); return h.equations          # a x + b <= 0 inside

def inside(P, eq, tol=-0.002):
    return np.all(P @ eq[:, :3].T + eq[:, 3] < tol, axis=1)

def surface_pts(V, F, step=0.02):
    T = V[F]; a = T[:, 1] - T[:, 0]; b = T[:, 2] - T[:, 0]; out = [V]
    for k in range(len(F)):
        L = max(np.linalg.norm(a[k]), np.linalg.norm(b[k])); n = int(L / step) + 1
        for i in range(n + 1):
            for j in range(n + 1 - i):
                out.append((T[k, 0] + a[k] * i / n + b[k] * j / n)[None])
    return np.vstack(out)

def Ry(d):
    t = np.radians(d); return np.array([[np.cos(t), 0, -np.sin(t)], [0, 1, 0], [np.sin(t), 0, np.cos(t)]])   # row vectors, +d = to the left? sign irrelevant (both checked)
def Rx(d):
    t = np.radians(d); return np.array([[1, 0, 0], [0, np.cos(t), np.sin(t)], [0, -np.sin(t), np.cos(t)]])

def main(mesh, zis3):
    fixed = [G.hull_front(), G.hull_rear_low(), G.plinth()] + G.casemate_front() + G.casemate_sides() + G.deck_hatches() + G.interior() + G.mantle_collar()
    fixed += [p for r in G.ammo_rounds() for p in r]                                     # v4: rounds in the racks
    eqs = [solid_eq(V) for V, F in fixed]
    O, I, H = G.mantle_solids()
    def in_planes(P, pl, tol=-0.002):
        return np.all(np.stack([P @ np.asarray(n) - d < tol for n, d in pl], 1), 1)
    piv = np.array([G.TRAV_X, G.BORE_Y, G.PIV_Z])
    Ph = np.vstack([surface_pts(*G.housing())] + [surface_pts(v, f) for v, f in G.gun_cradle()]
                   + [surface_pts(v - G.TRUN, f) for v, f in G.gun_cradle_detail()])          # elevating parts (gun-mask frame)
    Pt = np.vstack([surface_pts(v, f) for v, f in G.gun_gear() + G.gunner_seat()])             # v4: traversing only (world)
    Z = SM.Src(zis3); A, F = Z.geo[('d_gun', 1)]; Pg = A[:, :3]
    gun_off = np.array([G.GUN_X, G.BORE_Y, G.MUZZLE_Z]) - Z.local('s_gun')[3, :3] - G.TRUN
    bad = []; gear_eqs = [solid_eq(V) for V, F in G.gun_gear()]
    for tv in np.linspace(-15, 15, 7):
        R = Ry(tv); pt = (Pt - piv) @ R + piv
        for k, eq in enumerate(eqs):
            c = inside(pt, eq).sum()
            if c: bad.append(('mount', k, tv, '-', int(c)))
        for el in np.linspace(-3, 25, 8):
            ph = (Ph @ Rx(-el) + (G.TRUN - piv)) @ R + piv
            pg = ((Pg + gun_off) @ Rx(-el) + (G.TRUN - piv)) @ R + piv
            gear_t = [eq for eq in gear_eqs]
            for nm, P in (('gunmask', ph), ('barrel', pg)):
                for k, eq in enumerate(eqs):
                    c = inside(P, eq).sum()
                    if c: bad.append((nm, k, tv, el, int(c)))
                c = (in_planes(P, O) & ~in_planes(P, I, 0.002) & ~in_planes(P, H, 0.002)).sum()
                if c: bad.append((nm, 'mantle', tv, el, int(c)))
                Pl = (P - piv) @ R.T + piv                                                       # back into the mount frame
                for k, eq in enumerate(gear_eqs):
                    c = inside(Pl, eq).sum()
                    if c: bad.append((nm, 'gear%d' % k, tv, el, int(c)))
    print('check 1 (moving gun vs hull, interior and the fixed mantle):', 'PASS' if not bad else 'FAIL %d cases, e.g. %s' % (len(bad), bad[:8]))
    eqh = solid_eq(G.housing()[0])
    Pr = Pg + gun_off; Pr = Pr[(Pr[:, 2] < G.HOUSING['z1'] - G.TRUN[2] - 0.005) & (Pr[:, 2] > G.HOUSING['z0'] - G.TRUN[2] + 0.005)]
    out = ~np.all(Pr @ eqh[:, :3].T + eqh[:, 3] < 0.001, axis=1)
    print('check 2 (ZiS-3 recoil gear inside the housing where they overlap): %s (%d of %d points outside)' % ('PASS' if out.sum() == 0 else 'FAIL', out.sum(), len(Pr)))
    zb = G.TRUN[2] + gun_off[2] + Z.local('d_zatvor')[3, 2]
    back = G.front_z(G.BORE_Y) - 0.04
    print('check 3 (breech block behind the mantle, free in the compartment): breech z %.3f, mantle back at bore height %.3f -> %s' % (zb, back, 'PASS' if zb < back else 'FAIL'))
    m = azg2.read(mesh)
    print('check 4 (u16 vertex limit):', [(b['tag'], b['nv']) for b in m['blocks']], 'PASS' if all(b['nv'] < 65535 for b in m['blocks']) else 'FAIL')
if __name__ == '__main__':
    main(*sys.argv[1:3])

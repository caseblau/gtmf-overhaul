"""SU-76M (1943) geometry: every dimension of the new hull, casemate, gun mount and fittings, in the game's vehicle frame
(x right, y up, z forward, metres; ground at y -0.84, road-wheel centres at y -0.558 like the T-70).

Sources: the user's reference model of an SU-76M (Downloads\\su-76m_bin: a ripped game model - reference only, never
shipped; scaled 0.2263 m per unit so its road wheels are the T-70's 0.55 m; dimensions read off its sections and
orthographic views, 1 Nov 2026) and the published figures (length 4.97 m without the gun / 5.00 m with it, width
2.72 m, height 2.10 m, ground clearance 0.30 m; armour: upper front 35 mm at 60 deg, lower front 25 mm, hull sides and
rear 15 mm, casemate front 25 mm at 25 deg, casemate sides 10 mm, open top).

Running gear (ref, game frame): six road wheels per side at z -1.550 -0.937 -0.373 0.258 0.901 1.550 (y -0.558), drive
sprocket front (z 2.157, y -0.246), idler rear (z -2.150, y -0.286), three return rollers (z -1.206 -0.002 1.159,
y -0.144), track centre x +-1.228 (the SU-76M is 0.3 m wider than the T-70; the T-70 has five wheels at x +-1.076).
All solids are (V, F) with outward winding (geom.py).
"""
import numpy as np, geom

# ---------------------------------------------------------------- main dimensions
HW = 1.07                 # hull side plates (outer face), lower and upper hull
Y_BOT = -0.56             # belly
Y_DECK = 0.49             # engine / transmission deck, top of the hull sides
Y_FLOOR = -0.08           # fighting-compartment floor
Z_REAR = -2.12            # rear plate (outer face)
T_PLATE = 0.015           # thin plates (sides, rear, floor, fenders) - drawn as slabs so the open compartment has insides
T_FRONT = 0.025           # casemate front plate
HULL_PROFILE = [(1.80, Y_BOT), (2.15, -0.47), (2.36, -0.10), (1.24, Y_DECK)]       # (z, y): belly front edge .. glacis top
REAR_PROFILE = [(-1.85, Y_BOT), (Z_REAR, -0.15)]                                   # belly rear edge, rear knee
GLACIS = ((2.36, -0.10), (1.24, Y_DECK))
# casemate
CM_BASE = (-0.20, Y_DECK)                                                          # front plate foot (z, y)
CM_TOP = 1.26
CM_FT = (-0.56, CM_TOP)                                                            # front plate top edge (z, y)
CM_KNEE_Z = -2.12                                                                  # side plates full height to the rear
CM_REAR_Y = CM_TOP                                                                 # (reference sections z -1.8 / -2.0)
REAR_WALL_Y = 0.80                                                                 # rear plate top
SIDE_LEAN = 0.30                                                                   # dx / dy of the casemate sides (16.7 deg)

def side_x(y):
    """outer face of a casemate side plate at height y"""
    return HW - (y - Y_DECK) * SIDE_LEAN

_ft = np.array([CM_FT[0] - CM_BASE[0], CM_FT[1] - CM_BASE[1]]); _ft /= np.linalg.norm(_ft)
FRONT_N = np.array([0.0, -_ft[0], _ft[1]])                                       # outward (up and forward): (0, 0.42, 0.91)
FRONT_D = FRONT_N @ np.array([0.0, CM_BASE[1], CM_BASE[0]])                       # outer face: n.p = FRONT_D

def front_z(y):
    """z of the casemate front plate's outer face at height y"""
    return CM_BASE[0] - (y - CM_BASE[1]) * (-_ft[0] / _ft[1])

# gun mount (ZiS-3Sh): traverse axis, cylindrical mantlet, armoured housing over the barrel
GUN_X = -0.23             # gun axis (left of the centre line; reference muzzle brake x -0.324..-0.133)
TRAV_X = -0.245           # vertical traverse axis (mantlet centre, reference x -0.546..0.030)
TRAV_Z = -0.10            # reference frame of the mantle's front profile (MANT['prof'] is measured from here)
PIV_Z = 0.10              # v2: traverse and elevation pivot on the mantle's face (the mantle is fixed to the hull)
MANT_Y = (0.555, 1.21)
NOTCH_X = (-0.685, 0.195) # opening in the front plate = the fixed mantle's outline (TRAV_X +- 0.44, v3 flared sides)
BORE_Y = 0.902            # reference barrel y 0.834..0.970
TRUN = np.array([GUN_X, BORE_Y, PIV_Z])
MUZZLE_Z = 2.545          # muzzle socket; the brake ends 2 cm further, at the reference's 2.567
HOUSING = dict(hw=0.148, xo=0.003, y0=0.627, y1=1.156, z0=0.02, z1=0.86, chamfer=(0.78, 1.10))   # covers the ZiS-3's recoil gear (x -0.095..0.138,
                                                                                             # y -0.145..+0.214 about the bore); small top-front chamfer
PLINTH = dict(x=(-0.60, 0.11), y=(Y_DECK, 0.553), z=(-0.19, 0.14))

# running gear (from the reference model)
TRACK_X = 1.228
ROAD_Z = [1.550, 0.901, 0.258, -0.373, -0.937, -1.550]      # front to rear
ROAD_Y = -0.558
SPROCKET = (2.157, -0.246)
IDLER = (-2.150, -0.286)
ROLLER_Z = [1.159, -0.002, -1.206]                        # front to rear
ROLLER_Y = -0.144
# 3 Nov (user: "su-76 fenders are on top of tracks it looks bad"): at y 0.13 the fenders lay ~10 cm over the upper track run
# (track top y ~0.025 over the return rollers, 0.11 over the sprocket) and the front mudguard, sloping down from z 2.06,
# cut through the track where it wraps the sprocket. Now 0.20 (17 cm over the run, 8 cm over the sprocket) and level to
# z 2.18, then down to the nose (2.46, 0.06) - at least 3 cm clear of the track round the sprocket.
FENDER = dict(x=(HW, 1.43), y=0.20, t=0.012, z=(-2.17, 2.18), nose=(2.46, 0.06))

# ---------------------------------------------------------------- helpers
def _planes_from_poly2d(poly, interior):
    """edges of a convex polygon in (z, y) -> planes n.p <= d with n in the (y, z) plane"""
    out = []; P = np.asarray(poly, float); c = np.asarray(interior, float)
    for i in range(len(P)):
        a, b = P[i], P[(i + 1) % len(P)]; t = b - a
        n2 = np.array([t[1], -t[0]]); n2 /= np.linalg.norm(n2)          # (z, y) normal
        if n2 @ (c - a) > 0: n2 = -n2
        n = np.array([0.0, n2[1], n2[0]]); out.append((n, n @ np.array([0.0, a[1], a[0]])))
    return out

def prism_x(poly, x0, x1, extra=()):
    """convex polygon in (z, y) extruded from x0 to x1"""
    c = np.mean(np.asarray(poly, float), 0)
    planes = _planes_from_poly2d(poly, c) + [(np.array([1.0, 0, 0]), x1), (np.array([-1.0, 0, 0]), -x0)] + list(extra)
    return geom.polytope(planes, [(x0 + x1) / 2, c[1], c[0]])

def slab(points, normal, t, extra=()):
    """a plate: convex polygon (3D points in one plane, any order around) given thickness t inward (against normal)"""
    P = np.asarray(points, float); n = np.asarray(normal, float); n /= np.linalg.norm(n); c = P.mean(0)
    d = n @ P[0]
    # in-plane edge planes from the convex hull of the points projected on the plane
    s = np.cross(n, [0, 1.0, 0] if abs(n[1]) < 0.9 else [1.0, 0, 0]); s /= np.linalg.norm(s); u = np.cross(n, s)
    q = np.c_[(P - c) @ s, (P - c) @ u]; ang = np.arctan2(q[:, 1], q[:, 0]); order = np.argsort(ang); Q = P[order]
    planes = [(n, d), (-n, -(d - t))]
    for i in range(len(Q)):
        a, b = Q[i], Q[(i + 1) % len(Q)]; e = np.cross(b - a, n); e /= np.linalg.norm(e)
        if e @ (c - a) > 0: e = -e
        planes.append((e, e @ a))
    planes += list(extra)
    if extra:                                                            # v3: interior point by Chebyshev centre (clipped slabs)
        from scipy.optimize import linprog
        A = np.array([np.r_[np.asarray(p, float), np.linalg.norm(p)] for p, _ in planes]); bb = np.array([d for _, d in planes])
        r = linprog(np.r_[0, 0, 0, -1.0], A_ub=A, b_ub=bb, bounds=[(None, None)] * 3 + [(0, None)])
        return geom.polytope(planes, r.x[:3])
    return geom.polytope(planes, c - n * t / 2)

def tube(points, r, seg=8):
    """a bent tube through the given points (each straight run its own closed cylinder; joints get a small ball)"""
    parts = []
    for a, b in zip(points[:-1], points[1:]):
        a = np.asarray(a, float); b = np.asarray(b, float); L = np.linalg.norm(b - a)
        parts.append(geom.revolve([(0, r), (L, r)], a, b - a, seg=seg))
    for p in points[1:-1]:
        parts.append(geom.revolve([(-r, 0.001), (-r * 0.7, r * 0.72), (0, r), (r * 0.7, r * 0.72), (r, 0.001)], p, (0, 1.0, 0), seg=seg))
    return geom.merge(*parts)

def cyl(c, axis, r, L, seg=16):
    c = np.asarray(c, float); a = np.asarray(axis, float); a /= np.linalg.norm(a)
    return geom.revolve([(-L / 2, r), (L / 2, r)], c, a, seg=seg)

# ---------------------------------------------------------------- hull
def hull_front():
    """closed front hull: belly, lower front plates, glacis, deck, bulkhead at the casemate front plate foot"""
    poly = [(CM_BASE[0], Y_BOT)] + HULL_PROFILE + [(CM_BASE[0], Y_DECK)]
    return prism_x(poly, -HW, HW)

def hull_rear_low():
    """under the fighting-compartment floor: belly, rear slope, floor on top"""
    poly = [(CM_BASE[0], Y_BOT), (CM_BASE[0], Y_FLOOR), (Z_REAR, Y_FLOOR), (Z_REAR, -0.15), (-1.85, Y_BOT)]
    return prism_x(poly, -HW, HW)

def hull_rear_walls():
    """side walls of the fighting compartment between floor and deck level, and the rear plate up to the wall top"""
    out = []
    for s in (-1, 1):
        x0, x1 = (HW - T_PLATE, HW) if s > 0 else (-HW, -HW + T_PLATE)
        out.append(prism_x([(CM_BASE[0], Y_FLOOR), (CM_BASE[0], Y_DECK), (Z_REAR + T_PLATE, Y_DECK), (Z_REAR + T_PLATE, Y_FLOOR)], x0, x1))
    out.append(prism_x([(Z_REAR + T_PLATE, -0.15), (Z_REAR + T_PLATE, REAR_WALL_Y), (Z_REAR, REAR_WALL_Y), (Z_REAR, -0.15)], -HW, HW))
    return out

SIDE_KNEE = (-1.39, 0.80)    # v2: both side plates' top edges run level to z -1.37, then down to y 0.82 at the rear plate
                             # (reference sections: top y 1.24 at z -1.4, 1.12 at -1.6, 1.00 at -1.8)

def casemate_sides():
    out = []
    for s in (-1, 1):
        n = np.array([s * 1.0, SIDE_LEAN, 0.0]); n /= np.linalg.norm(n)
        pts = []
        top = [(SIDE_KNEE[0], CM_TOP), (Z_REAR, SIDE_KNEE[1])]
        for z, y in [(CM_BASE[0] + 0.02, Y_DECK), (CM_FT[0] + 0.02, CM_TOP)] + top + [(Z_REAR, Y_DECK)]:
            pts.append([s * side_x(y), y, z])
        front_cut = (FRONT_N, FRONT_D)                                     # stop at the front plate's outer face
        out.append(slab(pts, n, 0.012, extra=[front_cut]))
    return out

def casemate_front():
    """front plate (25 mm, 25 deg) between the side planes, with the notch for the mantlet"""
    out = []
    t = T_FRONT
    def piece(x0, x1, y0, y1):
        pts = []
        for y in (y0, y1):
            for x in (x0, x1):
                pts.append([x, y, front_z(y)])
        sides = []
        for s in (-1, 1):
            n = np.array([s * 1.0, SIDE_LEAN, 0.0]); n /= np.linalg.norm(n)
            sides.append((n, n @ np.array([s * HW, Y_DECK, 0.0])))
        return slab(pts, FRONT_N, t, extra=sides)
    xl = -side_x(Y_DECK) - 0.05; xr = side_x(Y_DECK) + 0.05
    out.append(piece(xl, NOTCH_X[0], Y_DECK, CM_TOP))
    out.append(piece(NOTCH_X[1], xr, Y_DECK, CM_TOP))
    out.append(piece(NOTCH_X[0], NOTCH_X[1], Y_DECK, MANT_Y[0]))
    return out

def plinth():
    p = PLINTH; return geom.box([np.mean(p['x']), np.mean(p['y']), np.mean(p['z'])], [p['x'][1] - p['x'][0], p['y'][1] - p['y'][0], p['z'][1] - p['z'][0]])

def deck_hatches():
    """engine hatch (right, in front of the casemate), transmission hatch (front deck), 6 mm proud, with hinge knuckles"""
    out = []
    for x0, x1, z0, z1 in ((0.22, 0.98, -0.12, 0.62), (-0.95, -0.35, 0.30, 1.10), (-0.20, 0.95, 0.70, 1.18)):
        out.append(geom.box([(x0 + x1) / 2, Y_DECK + 0.003, (z0 + z1) / 2], [x1 - x0, 0.012, z1 - z0]))
    # engine access box (raised louvre cover on the right, against the casemate front)
    # v2: the raised box right of the mantle (reference: x 0.07..0.65, z -0.25..0.20, top y 0.75, sloped front)
    poly = [(-0.24, Y_DECK), (-0.24, 0.75), (0.05, 0.75), (0.20, 0.59), (0.20, Y_DECK)]
    out.append(prism_x(poly, 0.20, 0.65))
    return out

def driver_hatch_outline():
    """driver's hatch on the glacis (left of centre): corners in world, hinge on its top edge"""
    (zn, yn), (zt, yt) = GLACIS
    tdir = np.array([0.0, yn - yt, zn - zt]); tdir /= np.linalg.norm(tdir)           # down the glacis
    top = np.array([0.0, yt, zt]) + tdir * 0.10
    return top, tdir

GLACIS_N = np.array([0.0, GLACIS[0][0] - GLACIS[1][0], GLACIS[1][1] - GLACIS[0][1]]); GLACIS_N /= np.linalg.norm(GLACIS_N)   # (0, 0.89, 0.47)

def driver_hatch(local=True):
    """lid 0.52 x 0.46, 2 cm thick, with a vision block; returned in the hinge frame (x along the hinge, -z... see mesh)"""
    top, tdir = driver_hatch_outline()
    x0, x1 = -0.46, 0.06
    L = 0.46
    pts = []
    for x in (x0, x1):
        for s in (0.0, L):
            p = top + tdir * s; pts.append([x, p[1], p[2]])
    pts = np.array(pts) + GLACIS_N * 0.02
    lid = slab(pts, GLACIS_N, 0.02)
    # vision block housing on the lid
    c = top + tdir * 0.12 + GLACIS_N * 0.03; c[0] = -0.20
    vb = geom.box(c, [0.20, 0.05, 0.06])
    knuckles = []
    for x in (x0 + 0.06, x1 - 0.06):
        knuckles.append(cyl([x, top[1] + GLACIS_N[1] * 0.02, top[2] + GLACIS_N[2] * 0.02], (1, 0, 0), 0.022, 0.08, seg=10))
    return [lid, vb] + knuckles, top + GLACIS_N * 0.02

def fenders():
    f = FENDER; out = []
    for s in (-1, 1):
        x0, x1 = (f['x'][0], f['x'][1]) if s > 0 else (-f['x'][1], -f['x'][0])
        out.append(prism_x([(f['z'][0], f['y']), (f['z'][0], f['y'] + f['t']), (f['z'][1], f['y'] + f['t']), (f['z'][1], f['y'])], x0, x1))
        zn, yn = f['nose']                                               # front mudguard sloping down to the nose
        out.append(prism_x([(f['z'][1], f['y']), (f['z'][1], f['y'] + f['t']), (zn, yn + f['t']), (zn, yn)], x0, x1))
        xo = x1 - 0.012 if s > 0 else x0                                 # outer lip
        out.append(prism_x([(f['z'][0], f['y'] - 0.05), (f['z'][0], f['y']), (f['z'][1], f['y']), (f['z'][1], f['y'] - 0.05)], xo, xo + 0.012))
    return out

def fender_boxes():
    out = []
    # left rear stowage box with a sloped outer lid edge
    poly_x = None
    out.append(prism_x([(-0.95, FENDER['y'] + 0.012), (-0.95, 0.42), (-1.98, 0.42), (-1.98, FENDER['y'] + 0.012)], -1.40, -1.10))
    # right rear box (reference height map: z -2.08..-0.62, x 1.08..1.44, top y 0.50; the silencer lies on it)
    out.append(prism_x([(-0.62, FENDER['y'] + 0.012), (-0.62, 0.50), (-2.08, 0.50), (-2.08, FENDER['y'] + 0.012)], 1.08, 1.44))
    out.append(geom.box([1.26, 0.505, -1.35], [0.37, 0.012, 1.47]))
    # right front tool box
    out.append(prism_x([(1.75, FENDER['y'] + 0.012), (1.75, 0.46), (1.25, 0.46), (1.25, FENDER['y'] + 0.012)], 1.10, 1.40))
    # lid seams (thin strips) on both boxes
    out.append(geom.box([-1.25, 0.425, -1.465], [0.31, 0.012, 1.04]))
    out.append(geom.box([1.25, 0.465, 1.50], [0.31, 0.012, 0.51]))
    return out

SILENCER = dict(c=(1.25, 0.59, -1.37), r=0.085, L=0.52)

def exhaust():
    """v2 (reference right-side view): the exhaust pipe climbs out of the engine deck by the casemate front and runs back
    along the right casemate side at y 0.55-0.60 to the silencer (z -1.63..-1.11, x 1.15..1.35); two tail pipes to the rear"""
    c = SILENCER['c']
    pipe = tube([(0.98, 0.50, 0.12), (1.15, 0.62, -0.15), (1.21, 0.57, -0.60), (1.25, 0.59, c[2] + SILENCER['L'] / 2)], 0.032)
    sil = cyl(c, (0, 0, 1.0), SILENCER['r'], SILENCER['L'], seg=14)
    tails = geom.merge(*[tube([(c[0] + dx, c[1], c[2] - SILENCER['L'] / 2), (c[0] + dx, c[1] - 0.01, -2.00)], 0.025) for dx in (-0.08, 0.08)])
    straps = [geom.box([c[0], c[1], z], [0.20, 0.20, 0.03]) for z in (-1.20, -1.54)]
    return [pipe, sil, tails] + straps

def rail_frame():
    """tubular frame on top of the casemate (for the tarpaulin)"""
    y = CM_TOP + 0.03; xs = side_x(CM_TOP) - 0.04
    xr = side_x(0.84) - 0.03                                                   # rear posts down to the rear corners (y 0.84)
    pts_l = [(-xs, y, CM_FT[0] - 0.05), (-xs, y, -1.96), (-xs, y - 0.04, -2.05), (-xr, 0.84, Z_REAR + 0.03)]
    pts_r = [(xs, y, CM_FT[0] - 0.05), (xs, y, -1.96), (xs, y - 0.04, -2.05), (xr, 0.84, Z_REAR + 0.03)]
    return [tube(pts_l, 0.016), tube(pts_r, 0.016), tube([(-xs, y, -1.96), (xs, y, -1.96)], 0.016)]

def rear_fittings():
    out = []
    # rear door (centre of the rear wall) with two hinges and a handle
    out.append(geom.box([0.0, 0.36, Z_REAR - 0.006], [0.62, 0.74, 0.012]))
    for y in (0.12, 0.60): out.append(cyl([-0.33, y, Z_REAR - 0.02], (0, 1.0, 0), 0.02, 0.10, seg=8))
    out.append(tube([(0.18, 0.40, Z_REAR - 0.012), (0.18, 0.40, Z_REAR - 0.06), (0.26, 0.40, Z_REAR - 0.06), (0.26, 0.40, Z_REAR - 0.012)], 0.010))
    # tail lights
    for x in (-0.85, 0.85): out.append(geom.box([x, 0.62, Z_REAR - 0.03], [0.10, 0.08, 0.06]))
    return out

def front_fittings():
    out = []
    # glacis weld seam (plate joint at the nose) and two lifting eyes on the deck
    (zn, yn), (zt, yt) = GLACIS
    out.append(prism_x([(zn - 0.02, yn - 0.01), (zn + 0.005, yn - 0.005), (zn - 0.005, yn + 0.02)], -HW, HW))
    for x in (-0.80, 0.80):
        out.append(tube([(x - 0.05, Y_DECK, 1.10), (x - 0.05, Y_DECK + 0.05, 1.10), (x + 0.05, Y_DECK + 0.05, 1.10), (x + 0.05, Y_DECK, 1.10)], 0.012))
    return out

def interior():
    """the open fighting compartment: fuel tank housing right, ammunition racks, seats, the radio"""
    out = []
    out.append(geom.box([0.80, (Y_FLOOR + 0.40) / 2, -1.70], [0.50, 0.40 - Y_FLOOR, 0.62]))     # fuel tank housing, right rear
    out += rack_frames()                                                                       # v4: open racks (rounds: ammo_rounds())
    for x, z in ((0.47, -1.25), (0.40, -1.80)):                                                  # seats (loader, commander)
        out.append(geom.box([x, 0.30, z], [0.32, 0.05, 0.30]))
        out.append(geom.box([x, 0.10, z], [0.06, 0.36, 0.06]))
    out += radio_set()                                                                          # v4: 12RT set with a sloped front
    return out

def antenna():
    """on the right casemate side plate, z -0.94 (reference): a bracket off the plate, the base, a 2.2 m whip"""
    y0 = 0.86; x0 = side_x(y0) + 0.05
    base = geom.merge(cyl([x0, y0, -0.94], (0, 1.0, 0), 0.03, 0.10, seg=10), geom.box([x0 - 0.03, y0, -0.94], [0.07, 0.05, 0.05]))
    whip = cyl([x0, y0 + 0.05 + 1.10, -0.94], (0, 1.0, 0), 0.006, 2.20, seg=6)
    return base, whip

# ---------------------------------------------------------------- gun mount
MANT_RIDGE = 1.30          # v3: reference front view - the mantle's top rises to a ridge over the gun
MANT = dict(hw=0.29, flare_z=-0.20, flare_hw=0.44, r=0.06, t=0.025, waist=-0.05, back=-0.45, back_hw=0.16,
            # front profile in side view (reference section x -0.27): (y, z ahead of the traverse axis)
            prof=[(0.555, 0.13), (0.65, 0.22), (0.75, 0.25), (0.85, 0.245), (0.95, 0.22), (1.05, 0.17), (1.13, 0.10), (1.21, 0.00)])

def mantlet():
    """the gun's traversing shield (ZiS-3Sh upper mount armour): its front bulges forward in side view (the reference's
    curved face, foremost 0.25 m ahead of the axis at y 0.75), round vertical front edges (r 0.10) in plan, flat top and
    bottom, sides tapering back into the casemate (0.16 m half width at the back) so the swing stays inside the notch;
    in the traverse node's frame (origin on the axis at the bore height)"""
    m = MANT; planes = []
    pr = m['prof']
    for (y0, z0), (y1, z1) in zip(pr[:-1], pr[1:]):                    # front facets (tilted about x)
        t = np.array([0.0, y1 - y0, z1 - z0]); n = np.array([0.0, -t[2], t[1]]); n /= np.linalg.norm(n)
        if n[2] < 0: n = -n
        p = np.array([0.0, y0 - BORE_Y, z0]); planes.append((n, n @ p))
    zf = max(z for _, z in pr)
    for s in (-1, 1):
        planes.append((np.array([s * 1.0, 0, 0]), m['hw']))
        c = np.array([s * (m['hw'] - m['r']), 0, zf - m['r']])
        for k in range(1, 4):
            t = np.radians(22.5 * k); n = np.array([s * np.sin(t), 0.0, np.cos(t)]); planes.append((n, n @ c + m['r']))
        a = np.array([s * m['hw'], 0, m['waist']]); b = np.array([s * m['back_hw'], 0, m['back']])   # taper
        e = b - a; n = np.array([e[2], 0.0, -e[0]]) * s; n /= np.linalg.norm(n)
        if n @ (np.zeros(3) - a) > 0: n = -n
        planes.append((n, n @ a))
    planes += [(np.array([0, 0, -1.0]), -m['back']), (np.array([0, 1.0, 0]), MANT_Y[1] - BORE_Y), (np.array([0, -1.0, 0]), -(MANT_Y[0] - BORE_Y))]
    return geom.polytope(planes, [0.0, 0.0, 0.0])

def mantlet_details():
    """lifting eyes on the mantlet top and the sight port on its left"""
    out = []
    for x in (-0.12, 0.12):
        z = -0.18
        out.append(tube([(x, MANT_Y[1] - BORE_Y, z - 0.04), (x, MANT_Y[1] - BORE_Y + 0.05, z - 0.04), (x, MANT_Y[1] - BORE_Y + 0.05, z + 0.04), (x, MANT_Y[1] - BORE_Y, z + 0.04)], 0.010))
    return out

def housing():
    """armoured housing of the recoil gear over the barrel, in the gun-mask (elevation) frame: origin at the trunnion"""
    h = HOUSING; o = TRUN; xo = h['xo']
    planes = [(np.array([1.0, 0, 0]), h['hw'] + xo), (np.array([-1.0, 0, 0]), h['hw'] - xo),
              (np.array([0, 1.0, 0]), h['y1'] - o[1]), (np.array([0, -1.0, 0]), -(h['y0'] - o[1])),
              (np.array([0, 0, 1.0]), h['z1'] - o[2]), (np.array([0, 0, -1.0]), -(h['z0'] - o[2]))]
    zc, yc = h['chamfer']; a = np.array([0.0, h['y1'] - o[1], zc - o[2]]); b = np.array([0.0, yc - o[1], h['z1'] - o[2]])
    t = b - a; n = np.array([0.0, t[2], -t[1]]); n /= np.linalg.norm(n)
    if n[1] < 0: n = -n
    planes.append((n, n @ a))
    # round bottom (the reference's U section at z 0.5): facets tangent to a half circle of the housing's half width
    c = np.array([xo, h['y0'] - o[1] + h['hw'], 0.0])
    for k in range(1, 8):
        t = np.radians(180.0 * k / 8); n2 = np.array([np.cos(t), -np.sin(t), 0.0]); planes.append((n2, n2 @ c + h['hw']))
    c2 = np.array([xo, h['y1'] - o[1] - h['hw'] * 0.6, 0.0])                # rounded top corners (r 0.6 x half width)
    for k in (1, 2, 3, 5, 6, 7):
        t = np.radians(180.0 * k / 8); n2 = np.array([np.cos(t), np.sin(t), 0.0])
        planes.append((n2, n2 @ c2 + h['hw'] * 0.6 + (h['hw'] * 0.4) * abs(np.cos(t))))
    return geom.polytope(planes, [xo, (h['y0'] + h['y1']) / 2 - o[1], (h['z0'] + h['z1']) / 2 - o[2]])

def housing_bolts():
    out = []; h = HOUSING; o = TRUN
    for z in np.linspace(h['z0'] + 0.25, h['z1'] - 0.25, 4):
        for s in (-1, 1):
            out.append(cyl([h['xo'] + s * (h['hw'] + 0.004), h['y1'] - o[1] - 0.05, z - o[2]], (1, 0, 0), 0.012, 0.01, seg=8))
    return out


# ---------------------------------------------------------------- v2: fixed mantle (user: "the gun mantle is not fixed to the hull,
# the gun breech is stuck to the gun mask"). The reference's mantle is a hollow armoured hood - curved front, flat top, sides -
# open at the back and underneath, standing in the front-plate notch; the gun (housing + barrel) pivots on its face and the
# breech and recoil guard sit free behind it in the fighting compartment.
def _mantle_planes(inset=0.0, open_back=False):
    m = MANT; ox = np.array([TRAV_X, 0.0, TRAV_Z]); planes = []
    pr = m['prof']
    for (y0, z0), (y1, z1) in zip(pr[:-1], pr[1:]):
        t = np.array([0.0, y1 - y0, z1 - z0]); n = np.array([0.0, -t[2], t[1]]); n /= np.linalg.norm(n)
        if n[2] < 0: n = -n
        p = ox + np.array([0.0, y0, z0]); planes.append((n, n @ p - inset))
    zf = max(z for _, z in pr) + TRAV_Z
    for s_ in (-1, 1):
        planes.append((np.array([s_ * 1.0, 0, 0]), s_ * TRAV_X + m['hw'] - inset))
        c = np.array([TRAV_X + s_ * (m['hw'] - m['r']), 0, zf - m['r']])
        for k in range(1, 4):
            t = np.radians(22.5 * k); n = np.array([s_ * np.sin(t), 0.0, np.cos(t)]); planes.append((n, n @ c + m['r'] - inset))
    for s_ in (-1, 1):                                                   # v3: gabled top - ridge 1.30 over the axis, 1.21 at the sides
        t = np.array([s_ * m['hw'], -(MANT_RIDGE - MANT_Y[1]), 0.0]); n = np.array([-t[1], t[0], 0.0]) * s_; n /= np.linalg.norm(n)
        if n[1] < 0: n = -n
        planes.append((n, n @ np.array([TRAV_X, MANT_RIDGE, 0.0]) - inset))
    if open_back:
        planes += [(np.array([0, -1.0, 0]), -(MANT_Y[0] - 1.0)), (np.array([0, 0, -1.0]), 3.0)]
    else:
        planes += [(np.array([0, -1.0, 0]), -MANT_Y[0]), (-FRONT_N, -(FRONT_D - 0.04))]      # back: 4 cm behind the plate's outer face
        planes.append((np.array([0, 0, -1.0]), -m['flare_z']))                                   # v3: the hood ends where the collar flares
    return planes

HOLE = dict(x=(-0.175, 0.175), y=(0.612, 1.170), z=(-0.30, 0.40))   # v3: tight round the housing   # opening in the mantle's face for the housing (about GUN_X + xo)

def _hole_planes():
    h = HOLE; cx = GUN_X + HOUSING['xo']
    return [(np.array([1.0, 0, 0]), cx + h['x'][1]), (np.array([-1.0, 0, 0]), -(cx + h['x'][0])),
            (np.array([0, 1.0, 0]), h['y'][1]), (np.array([0, -1.0, 0]), -h['y'][0]),
            (np.array([0, 0, 1.0]), h['z'][1]), (np.array([0, 0, -1.0]), -h['z'][0])]

def _keep_inside(V, F, planes):
    """drop the parts of a mesh outside a convex region (subtract each outer half-space in turn)"""
    for n, d in planes:
        V, F = geom.subtract_convex(V, F, [(-np.asarray(n, float), -d)])
        if not len(F): break
    return V, F

def _compact(V, F):
    if not len(F): return V[:0], F
    u = np.unique(F); r = np.full(len(V), -1); r[u] = np.arange(len(u)); return V[u], r[F]

def mantle_outer():
    O = _mantle_planes(); return geom.polytope(O, [TRAV_X, BORE_Y, 0.0])

def mantle_shell():
    """the hollow hood (world frame): outer skin minus the inner volume minus the hole, with the inner skin and the hole's
    walls turned inward"""
    O = _mantle_planes(); I = _mantle_planes(MANT['t'], open_back=True); H = _hole_planes()
    Vo, Fo = geom.polytope(O, [TRAV_X, BORE_Y, 0.0])
    Vi, Fi = geom.polytope(I, [TRAV_X, BORE_Y, 0.0]); Fi = Fi[:, [0, 2, 1]]
    Vh, Fh = geom.polytope(H, [GUN_X, BORE_Y, 0.0]); Fh = Fh[:, [0, 2, 1]]
    a = geom.subtract_convex(Vo, Fo, I); a = geom.subtract_convex(*a, H)
    b = _keep_inside(Vi, Fi, O); b = geom.subtract_convex(*b, H)
    c = _keep_inside(Vh, Fh, O); c = geom.subtract_convex(*c, I)
    return [_compact(*x) for x in (a, b, c) if len(x[1])]

def mantle_solids():
    """convex pieces of the fixed hood for the collision audit: (O planes, minus I, minus H)"""
    return _mantle_planes(), _mantle_planes(MANT['t'], open_back=True), _hole_planes()

def gun_cradle():
    """in the gun-mask frame (origin at the pivot TRUN): the cradle trough under the barrel, the trunnion stubs and the
    U-shaped recoil guard reaching back into the compartment (the reference's 'U' behind the breech)"""
    o = TRUN; out = []
    out.append(geom.box([0.0, 0.775 - o[1], -0.11 - o[2]], [0.20, 0.05, 0.28]))                    # trough (short: it drops at +25 deg)
    for s_ in (-1, 1):
        out.append(geom.box([s_ * 0.10, 0.73 - o[1], (-0.45 - 1.30) / 2 - o[2]], [0.03, 0.06, 0.85]))   # guard rails, from under the breech back
        out.append(geom.box([s_ * 0.10, 0.775 - o[1], -0.45 - o[2]], [0.03, 0.15, 0.04]))          # uprights to the breech ring
    out.append(geom.box([0.0, 0.73 - o[1], -1.30 - o[2]], [0.23, 0.06, 0.03]))                      # rear cross bar
    return out

def gunner_seat():
    """v2: the gunner's seat rides on the traversing gun mount (left of the gun), world frame"""
    x, z = GUN_X - 0.39, -0.95
    return [geom.box([x, 0.30, z], [0.30, 0.05, 0.28]), geom.box([x, 0.10, z], [0.06, 0.36, 0.06])]


def mantle_collar():
    """v3 (reference plan sections): behind the hood (which ends at z -0.20) the mantle flares out at 45 deg from (+-0.29,
    z -0.20) to the notch edges (+-0.44, z -0.35), then runs straight back to the front plate; a top plate at y 1.21 covers
    the whole collar and a gable-end plate closes the hood's ridge. Thin slabs (20 mm) clipped at the front plate; world."""
    m = MANT; out = []; back = (-FRONT_N, -(FRONT_D - 0.04)); y0, y1 = MANT_Y[0], MANT_Y[1]
    za, zb = m['flare_z'], m['flare_z'] - (m['flare_hw'] - m['hw'])
    for s_ in (-1, 1):
        x0 = TRAV_X + s_ * m['hw']; x1 = TRAV_X + s_ * m['flare_hw']
        n = np.array([s_ * 0.7071, 0.0, 0.7071])
        out.append(slab([[x0, y0, za], [x0, y1, za], [x1, y0, zb], [x1, y1, zb]], n, 0.02, extra=[back]))
        out.append(slab([[x1, y0, zb], [x1, y1, zb], [x1, y0, -1.2], [x1, y1, -1.2]], np.array([s_ * 1.0, 0, 0]), 0.02, extra=[back]))
    xl, xr = TRAV_X - m['hw'], TRAV_X + m['hw']; xL, xR = TRAV_X - m['flare_hw'], TRAV_X + m['flare_hw']
    out.append(slab([[xl, y1, za], [xr, y1, za], [xR, y1, zb], [xR, y1, -1.2], [xL, y1, -1.2], [xL, y1, zb]], np.array([0, 1.0, 0]), 0.02, extra=[back]))
    out.append(slab([[xl, y1 - 0.02, za], [xr, y1 - 0.02, za], [TRAV_X, MANT_RIDGE - 0.01, za]], np.array([0, 0, -1.0]), 0.02))   # gable end
    return out


# ---------------------------------------------------------------- v4: fighting-compartment detail (user, 1 Nov: "a lot of
# things are missing from the ZiS-3 gun in the SU-76 internal compartment", with a detailed interior picture): the gun's
# elevating and traversing gear with their handwheels, the panoramic sight, the left guard shield, ammunition racks with
# rounds (brass cases, steel projectiles), the radio, the tarpaulin roll strapped on the left side, bolt rows.

ROUND = dict(case_r=0.045, case_L=0.385, rim_r=0.050, shell_r=0.038, shell_L=0.27)     # 76.2 mm round, ~0.66 m

def round_parts(base, axis):
    """one round standing on `base` along `axis`: (case, projectile) solids"""
    a = np.asarray(axis, float); a /= np.linalg.norm(a); r = ROUND
    case = geom.revolve([(0.0, r['rim_r']), (0.012, r['rim_r']), (0.014, r['case_r']), (r['case_L'] - 0.03, r['case_r']),
                         (r['case_L'], r['shell_r'] + 0.002)], base, a, seg=10)
    L = r['case_L']; sL = r['shell_L']
    shell = geom.revolve([(L - 0.01, r['shell_r']), (L + 0.10, r['shell_r']), (L + 0.17, r['shell_r'] * 0.8), (L + 0.23, r['shell_r'] * 0.45),
                          (L + sL, 0.006)], base, a, seg=10)
    return case, shell

AMMO = dict(left=dict(x=(-0.96, -0.80), z=(-1.22, -1.50), n=4),                         # behind the gunner's seat swing
            right=dict(x=(0.80, 0.96), z=(-0.52, -0.98), n=6),
            front=dict(x=(0.80, 0.96), z=(-0.27, -0.47), n=4))                     # right front corner (left is the gunner's)

def ammo_rounds():
    """[(case, shell)]: rounds standing nose-up in the wall racks (left wall 2 x 4, right front 2 x 3, front-left corner 2 x 2)"""
    out = []
    for k, rk in AMMO.items():
        xs = np.linspace(rk['x'][0] + 0.05, rk['x'][1] - 0.05, 2); nz = rk['n'] // 2
        zs = np.linspace(rk['z'][0] - 0.05 * np.sign(rk['z'][0] - rk['z'][1]) * -1, rk['z'][1], nz) if nz > 1 else [np.mean(rk['z'])]
        zs = np.linspace(min(rk['z']) + 0.05, max(rk['z']) - 0.05, nz)
        tilt = 0.10 if k == 'right' else 0.0                                     # right rack: rounds lean back against the wall
        for x in xs:
            for z in zs:
                out.append(round_parts([x, Y_FLOOR + 0.01, z], [tilt, 1.0, 0.0]))
    return out

def rack_frames():
    """open rack frames for the rounds: a floor tray, two clamp bars and corner posts per rack"""
    out = []
    for k, rk in AMMO.items():
        x0, x1 = rk['x']; z0, z1 = min(rk['z']), max(rk['z']); cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
        out.append(geom.box([cx, Y_FLOOR + 0.005, cz], [x1 - x0 + 0.02, 0.012, z1 - z0 + 0.02]))
        for y in (0.20, 0.42):
            out.append(geom.box([cx, y, z0 - 0.005], [x1 - x0 + 0.02, 0.03, 0.012])); out.append(geom.box([cx, y, z1 + 0.005], [x1 - x0 + 0.02, 0.03, 0.012]))
            xo = x0 - 0.005 if cx > 0 else x1 + 0.005
            out.append(geom.box([xo, y, cz], [0.012, 0.03, z1 - z0 + 0.02]))
        for z in (z0, z1):
            xi = x0 if cx > 0 else x1
            out.append(geom.box([xi, (Y_FLOOR + 0.46) / 2, z], [0.02, 0.46 - Y_FLOOR, 0.02]))
    return out

def radio_set():
    body = prism_x([(-1.07, 0.56), (-1.07, 0.84), (-1.33, 0.84), (-1.33, 0.56)], 0.66, 0.92)
    face = prism_x([(-1.07, 0.80), (-1.13, 0.84), (-1.33, 0.84), (-1.33, 0.80)], 0.64, 0.66)
    shelf = geom.box([0.83, 0.54, -1.20], [0.30, 0.03, 0.32])
    knobs = [cyl([0.645, 0.70, z], (1, 0, 0), 0.016, 0.02, seg=8) for z in (-1.13, -1.20, -1.27)]
    return [body, face, shelf] + knobs

def gun_gear():
    """on the traversing mount (s_rotation frame = world minus the pivot later): the pedestal under the cradle, the
    elevating gearbox and handwheel with its crank, the traversing handwheel - all on the gunner's (left) side"""
    gx = GUN_X; out = []
    out.append(geom.box([gx, 0.155, -0.36], [0.18, 0.47, 0.14]))                                      # pedestal post (behind the bulkhead)
    out.append(geom.box([gx, -0.055, -0.38], [0.30, 0.03, 0.16]))                                    # pedestal foot plate on the floor
    out.append(geom.box([gx - 0.235, 0.62, -0.54], [0.07, 0.14, 0.14]))                              # elevating gearbox
    out.append(cyl([gx - 0.26, 0.62, -0.54], (1, 0, 0), 0.025, 0.12, seg=8))                         # handwheel shaft
    out.append(geom.revolve([(0.0, 0.100), (0.016, 0.100), (0.016, 0.084), (0.0, 0.084)], [gx - 0.33, 0.62, -0.54], (1, 0, 0), seg=18, cap_start=False, cap_end=False))
    for a in (0, 120, 240):                                                                          # spokes
        t = np.radians(a); d = np.array([0, np.cos(t), np.sin(t)])
        out.append(tube([np.array([gx - 0.325, 0.62, -0.54]), np.array([gx - 0.325, 0.62, -0.54]) + d * 0.088], 0.008, seg=6))
    out.append(cyl([gx - 0.36, 0.62 + 0.085, -0.54], (1, 0, 0), 0.012, 0.07, seg=8))                 # crank handle
    out.append(geom.box([gx - 0.28, 0.42, -0.40], [0.08, 0.10, 0.12]))                               # traversing gearbox
    out.append(geom.revolve([(0.0, 0.080), (0.014, 0.080), (0.014, 0.066), (0.0, 0.066)], [gx - 0.37, 0.42, -0.46], (1, 0, 0), seg=16, cap_start=False, cap_end=False))
    out.append(cyl([gx - 0.33, 0.42, -0.44], (1, 0, 0), 0.02, 0.10, seg=8))
    out.append(cyl([gx - 0.40, 0.42 + 0.065, -0.46], (1, 0, 0), 0.010, 0.06, seg=8))
    return out

def gun_cradle_detail():
    """on the gun mask (world frame; the mesh subtracts the trunnion): elevating sector on the cradle's left, the
    panoramic sight on its bracket, the left guard shield beside the breech, the breech ring housing"""
    gx = GUN_X; out = []
    # elevating sector: an arc plate below and behind the trunnion, on the cradle's left
    c = TRUN; pts = []
    for t in np.linspace(np.radians(200), np.radians(250), 7):
        pts.append([np.cos(t) * 0.36, np.sin(t) * 0.36])
    for t in np.linspace(np.radians(250), np.radians(200), 7):
        pts.append([np.cos(t) * 0.28, np.sin(t) * 0.28])
    for (a, b), (c2, d2) in zip(pts[:6], pts[1:7]):                                    # segments of the arc as small slabs
        pass
    for t0, t1 in zip(np.linspace(np.radians(208), np.radians(232), 4)[:-1], np.linspace(np.radians(208), np.radians(232), 4)[1:]):
        q = [[gx - 0.17, c[1] + np.sin(t) * r, c[2] + np.cos(t) * r] for t in (t0, t1) for r in (0.18, 0.245)]
        out.append(slab(q, np.array([-1.0, 0, 0]), 0.02))
    # panoramic sight: bracket arm, vertical body, head with window, eyepiece pointing back to the gunner
    out.append(geom.box([gx - 0.17, 1.00, -0.66], [0.03, 0.03, 0.30]))                              # bracket back along the cradle
    out.append(geom.box([gx - 0.22, 1.00, -0.80], [0.10, 0.03, 0.05]))
    out.append(cyl([gx - 0.27, 1.03, -0.80], (0, 1, 0), 0.032, 0.14, seg=10))
    out.append(geom.box([gx - 0.27, 1.12, -0.80], [0.07, 0.06, 0.08]))
    out.append(cyl([gx - 0.27, 1.02, -0.86], (0, 0, 1), 0.016, 0.10, seg=8))
    # guard shield on the left of the breech (protects the gunner from the recoiling breech)
    out.append(geom.box([gx - 0.17, 0.815, -0.63], [0.012, 0.27, 0.24]))
    out.append(geom.box([gx - 0.17, 0.69, -0.63], [0.04, 0.02, 0.24]))
    # cradle side plates and the breech ring housing back to the breech
    for sx in (-1, 1):
        out.append(geom.box([gx + sx * 0.12, 0.84, -0.22], [0.015, 0.16, 0.48]))
    return out

def tarp_roll():
    """the rolled tarpaulin strapped on the outside of the left casemate side (rear half), two straps"""
    y = 0.80; x = -(side_x(y) + 0.11)
    roll = geom.revolve([(-0.50, 0.095), (-0.47, 0.11), (0.47, 0.11), (0.50, 0.095)], [x, y, -1.20], (0, 0, 1.0), seg=16)
    straps = [geom.revolve([(-0.02, 0.116), (0.02, 0.116)], [x, y, z], (0, 0, 1.0), seg=16) for z in (-0.95, -1.45)]
    brackets = [geom.box([-(side_x(y) + 0.02), y + 0.06, z], [0.04, 0.03, 0.04]) for z in (-0.95, -1.45)]
    return [roll] + straps + brackets

def bolt_rows():
    """bolt heads along the casemate side plates' edges (outside) and the front plate's edges"""
    out = []
    for s_ in (-1, 1):
        n = np.array([s_ * 1.0, SIDE_LEAN, 0.0]); n /= np.linalg.norm(n)
        def on_side(y, z, inset=0.04):
            return np.array([s_ * side_x(y), y, z]) + n * 0.001
        pts = []
        for z in np.arange(-0.70, -1.38, -0.13): pts.append(on_side(CM_TOP - 0.04, z))                 # top edge
        for t in np.linspace(0.08, 0.92, 7):                                                         # front edge
            y = Y_DECK + 0.04 + (CM_TOP - Y_DECK - 0.08) * t; pts.append(on_side(y, front_z(y) - 0.05))
        for z in np.arange(-0.40, -2.05, -0.15): pts.append(on_side(Y_DECK + 0.04, z))               # bottom edge
        for t in np.linspace(0.1, 0.9, 5):                                                           # sloped rear edge
            z = SIDE_KNEE[0] + (Z_REAR + 0.05 - SIDE_KNEE[0]) * t; y = CM_TOP + (SIDE_KNEE[1] - CM_TOP) * t - 0.04; pts.append(on_side(y, z))
        for p in pts:
            out.append(geom.revolve([(0.0, 0.013), (0.004, 0.011), (0.007, 0.005), (0.008, 0.001)], p, n, seg=6, cap_end=False))
    return out


# ---------------------------------------------------------------- v6 (4 Nov, user: "there are holes between gun, mask and
# hull in su-76"): the mantle's face opening is larger than the housing (it must clear -3..+25 deg elevation and +-15 deg
# traverse), and through the slits above and beside the housing one looked straight through the open fighting
# compartment to the ground behind. Two hidden baffles close the view without touching the moving gun:
#   * a fixed curtain on the hull: a 1 cm sheet bent round the elevation axis (TRUN) at radius 0.30, from 15 to 80 deg
#     above the horizontal behind the axis - just behind the opening's top edge (the face there is 0.29 m from the axis)
#     and outside everything on the gun mask (housing corners reach 0.28 m at full elevation + traverse);
#   * two cheeks traversing with the gun (s_rotation): half discs r 0.24 behind the axis, 1 cm, 0.19 m either side of
#     the gun, so the side slits look onto armour. Both inside the hood; their outer edges end within its 25 mm walls.
CURTAIN = dict(r=0.30, a=(15.0, 80.0), seg=8, t=0.010, hw=0.26)
CHEEK = dict(r=0.24, dx=0.19, seg=10, t=0.010)

def gun_curtain():
    c = CURTAIN; o = TRUN; out = []
    x0, x1 = TRAV_X - c['hw'], TRAV_X + c['hw']
    ang = np.radians(np.linspace(c['a'][0], c['a'][1], c['seg'] + 1))
    for a0, a1 in zip(ang[:-1], ang[1:]):
        p = lambda a, x: [x, o[1] + c['r'] * np.sin(a), o[2] - c['r'] * np.cos(a)]
        am = (a0 + a1) / 2; n = np.array([0.0, np.sin(am), -np.cos(am)])
        out.append(slab([p(a0, x0), p(a0, x1), p(a1, x0), p(a1, x1)], n, c['t']))
    return out

def gun_cheeks():
    c = CHEEK; o = TRUN; out = []; xc = GUN_X + HOUSING['xo']
    ang = np.radians(np.linspace(-90.0, 90.0, c['seg'] + 1))
    for s_ in (-1, 1):
        x = xc + s_ * c['dx']
        pts = [[x, o[1], o[2]]] + [[x, o[1] + c['r'] * np.sin(a), o[2] - c['r'] * np.cos(a)] for a in ang]
        out.append(slab(pts, np.array([s_ * 1.0, 0, 0]), c['t']))
    return out

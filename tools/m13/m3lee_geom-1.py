"""Shape of the M3 medium tank "Lee" (early M3: short 75 mm M2, M1 cupola) for Mius-Front - v6, built to the user's
reference renders (an orthographic left-side view plus four 3/4 views) with his 4-view drawing as a secondary source.

The left-side render is orthographic: registered on the game's M4A2 running gear (sprocket / idler hubs 757 px apart =
4.873 m -> 155.3 px/m; u = 489.9 - 155.3 z, v = 337 - 155.3 y) it gives every z / y figure below directly (the game
chassis is ~95 % of full size, so all figures are game metres, tied to the chassis, not to Hunnicutt's full-size data).

Frame: the game's vehicle frame (x right, y up, z forward, metres). Ground at y -1.149 (add-ins at (0, 0, 0.15)).

Hull (from the renders):
* roof y 1.00, side plates x +-1.276 from y 0.065 (the sponson floors) up; the fighting compartment's roof ends at
  z -1.03; the side plates are in two pieces with a vertical double rivet row at z -0.41, and behind that row the
  upper corners are chamfered: the side's top edge drops to 0.61 and slopes to 0.39 at the rear, a chamfer plate
  joining it to the roof (x 0.76) and further back to the deck.
* front: ONE transverse upper front plate (driver's plate + the 75 mm sponson's front) leaning 25.6 deg from the
  roof edge z 1.25 down to the bend (y 0.453, z 1.507), then the lower front plate at 51.5 deg down to the sponson
  floor level (0.065, 1.995) and a short ledge to the transmission cover's lip (0.147, 2.14). The left corner is an
  angled cheek plate (one plane, 32 deg in plan, from the side at z 0.48 to the driver's plate at x -0.80), the right
  corner is square: the right side plate runs forward to the front plate (the M3's sponson box). The 75 mm sits in a
  recess of the front plate (x 0.43 .. 1.16, floor y 0.30, back to z 0.33) under the round roof plate r 0.46 centred
  (0.80, 0.62), which just touches the turret ring; the rounded shield is a spheroid about the trunnions (0.80, 0.52,
  0.69), its front at z 1.05, the gun collar to 1.20, the short M2 barrel to the muzzle at 2.48.
* rear: a 45 deg grille plate from the roof edge (1.0, -1.03) down to the engine deck (0.60, -1.35); the deck (x
  +-0.76) to (0.55, -2.35), continuing as the rear roof to (0.55, -2.66); the upper rear plate vertical at z -2.66
  from 0.53 down to 0.28 with 45 deg corners, the overhang bottom at 0.28 back to the lower hull; stowage boxes on
  the chamfers (x 0.90 .. 1.255, z -1.27 .. -2.34, y 0.44 .. 0.86); tail lights in the rear corners.
* side doors hinged at their front edge: left z -0.29 .. 0.34 (hinge 0.38), right -0.29 .. 0.40 (hinge 0.44), both
  y 0.174 .. 0.88, with a pistol port (0.32 x 0.34, centre 0.315 behind the hinge edge, y 0.64), three hinges, a
  latch handle at the rear and a rain strip above; a vision port on the left cheek (projected centre z 1.158, y 0.76)
  and a smaller one on the right side plate's front part (z 1.22, y 0.76).
Turret (cast, r 0.80 about (-0.31, -0.06)): a cylinder to y 1.46, a rounded shoulder to the flat top at 1.68; the
front face leans back below the mantlet (z 0.60 @ 1.03 -> 0.47 @ 1.20) and slopes at 56 deg above it to the top
(z 0.06 @ 1.68); the M24 mount's rotor shield (mantlet) front at z 0.47, y 1.20 .. 1.40; the 37 mm (axis y 1.307): the
recoil jacket r 0.051 to z 0.86, the barrel r 0.03 to the muzzle at 1.89; the coax .30 on its right; the MG cupola
(r 0.32, centre z -0.39, x -0.66) with its rim at 1.89 and the .30 at y 1.71 (muzzle z 0.26).
Rivets: pitch 0.09, heads r 0.02.
"""
import numpy as np
import geom
from geom import polytope, revolve, box, merge

# ---------------------------------------------------------------- hull
HW = 1.276                     # half width over the hull side plates (the game's M4A2)
FLOOR = 0.065                  # bottom edge of the side plates / underside of the sponsons
ROOF = 1.00
REAR_WALL = -1.03              # rear edge of the fighting compartment's roof (the grille plate starts here)
SIDE_SEAM_Z = -0.41            # vertical double rivet row (two side plates); the chamfers start here
GRILLE_BOT = (0.60, -1.35)     # (y, z): foot of the 45 deg grille plate = front of the engine deck
DECK_R = (0.55, -2.35)         # (y, z): rear edge of the engine deck
DECK_HW = 0.76                 # half width of the engine deck / inner edge of the chamfers
REAR_ROOF_Z = -2.66            # the rear roof (y 0.55) ends here; the upper rear plate is vertical at this z
REAR_PLATE_Y = (0.28, 0.53)    # the upper rear plate's bottom / top
REAR_CORNER_X = 1.10           # the rear plate's 45 deg corners start here
LOW_REAR_Z = -2.495            # rear of the game's lower hull (the overhang bottom reaches it)
SIDE_TOP = ((0.61, SIDE_SEAM_Z), (0.39, -2.36))    # the side plates' sloping top edge behind the seam (y, z)
FP_TOP, BEND = (ROOF, 1.25), (0.453, 1.507)        # (y, z): the upper front plate (25.6 deg)
GL_BOT = (FLOOR, 1.995)                            # (y, z): foot of the lower front plate (51.5 deg)
LEDGE = (0.147, 2.14)                              # (y, z): the transmission cover's lip (M4_BOTTOM_FR)
LOW_HW = 0.778                                     # lower hull / transmission cover half width
CHEEK_A, CHEEK_B, CHEEK_C = (-HW, ROOF, 0.48), (-0.80, ROOF, FP_TOP[1]), (-HW, FLOOR, 1.18)   # left cheek plate
RECESS_X = (0.43, 1.16)        # the 75 mm recess in the front plate: its inner / outer walls
RECESS_Y0, RECESS_Z0 = 0.30, 0.62                  # its floor and rear wall
FRONT_STEP = 0.07              # the sponson box's front plates (x > 0.43) stand this far ahead of the driver's plate (side render)

def _plane_through(p, q, r, inside):
    p, q, r = (np.asarray(a, float) for a in (p, q, r)); n = np.cross(q - p, r - p); n /= np.linalg.norm(n)
    d = n @ p
    if n @ np.asarray(inside, float) > d: n, d = -n, -d
    return (n, d)

def _yz_plane(p1, p2, inside):
    """plane containing the x direction through two (y, z) points"""
    (y1, z1), (y2, z2) = p1, p2
    return _plane_through((0, y1, z1), (1, y1, z1), (0, y2, z2), inside)

def _ax(i, v, s=1.0):
    n = np.zeros(3); n[i] = s; return (n, s * v)

def front_plate_plane(): return _yz_plane(FP_TOP, BEND, (0, 0.5, 0))
def lower_plate_plane(): return _yz_plane(BEND, GL_BOT, (0, 0.3, 0))
def cheek_plane(): return _plane_through(CHEEK_A, CHEEK_B, CHEEK_C, (-0.5, 0.5, 0))
def grille_plane(): return _yz_plane((ROOF, REAR_WALL), GRILLE_BOT, (0, 0.3, -1.5))
def deck_plane(): return _yz_plane(GRILLE_BOT, DECK_R, (0, 0.3, -1.8))
def rear_roof_plane(): return _yz_plane(DECK_R, (DECK_R[0], REAR_ROOF_Z), (0, 0.3, -2.5))
def side_top_plane(): return _yz_plane(*SIDE_TOP, (0, 0.3, -1.8))

def deck_y(z):
    """height of the engine deck surface (grille plate / deck / rear roof)"""
    z = np.asarray(z, float)
    g = ROOF + (z - REAR_WALL) * (GRILLE_BOT[0] - ROOF) / (GRILLE_BOT[1] - REAR_WALL)
    d = GRILLE_BOT[0] + (z - GRILLE_BOT[1]) * (DECK_R[0] - GRILLE_BOT[0]) / (DECK_R[1] - GRILLE_BOT[1])
    return np.where(z > GRILLE_BOT[1], g, np.where(z > DECK_R[1], d, DECK_R[0]))
def side_top_y(z):
    (y0, z0), (y1, z1) = SIDE_TOP; return y0 + (np.asarray(z, float) - z0) * (y1 - y0) / (z1 - z0)
def roof_edge_y(z):
    """height of the chamfer's inner edge at x = DECK_HW: the roof to z -1.03, the deck surface behind"""
    z = np.asarray(z, float); return np.where(z > REAR_WALL, ROOF, deck_y(z))
def chamfer_y(x, z):
    ax = np.abs(np.asarray(x, float)); t = np.clip((ax - DECK_HW) / (HW - DECK_HW), 0, 1)
    return roof_edge_y(z) + (side_top_y(z) - roof_edge_y(z)) * t

def on_plane(pl, x=None, y=None, z=None):
    n, d = pl
    if z is None: return np.array([x, y, (d - n[0] * x - n[1] * y) / n[2]])
    if x is None: return np.array([(d - n[1] * y - n[2] * z) / n[0], y, z])
    return np.array([x, (d - n[0] * x - n[2] * z) / n[1], z])
def on_front_plate(x, y): return np.array([x, y, front_z(y, x)])
def on_cheek(y, z): return on_plane(cheek_plane(), y=y, z=z)
def on_deck(x, z): return np.array([x, float(deck_y(z)), z])
def front_z(y, x=0.0):
    """z of the front plates' surface at height y (upper / lower plate; the sponson's part 7 cm ahead)"""
    step = FRONT_STEP if x > RECESS_X[0] else 0.0
    if y >= BEND[0]: return step + FP_TOP[1] + (ROOF - y) * (BEND[1] - FP_TOP[1]) / (ROOF - BEND[0])
    return step + BEND[1] + (BEND[0] - y) * (GL_BOT[1] - BEND[1]) / (BEND[0] - GL_BOT[0])

def hull_pieces():
    """convex pieces of the upper hull (their union is the hull); each (name, V, F)"""
    fp, lp, ch = front_plate_plane(), lower_plate_plane(), cheek_plane()
    gr, dk, rr, st = grille_plane(), deck_plane(), rear_roof_plane(), side_top_plane()
    x0, x1 = RECESS_X
    front = [fp, lp]
    front2 = [(fp[0], fp[1] + FRONT_STEP * fp[0][2]), (lp[0], lp[1] + FRONT_STEP * lp[0][2])]     # the sponson's front, 7 cm ahead
    out = [
        # fighting compartment ahead of the side seam (full roof width): the left part with the cheek, the right part
        # split round the 75 mm recess
        ('fc_l', [_ax(0, x0), _ax(0, -HW, -1), _ax(1, ROOF), _ax(1, FLOOR, -1), _ax(2, SIDE_SEAM_Z, -1), ch] + front, (-0.3, 0.5, 0.3)),
        ('fc_rlow', [_ax(0, x1), _ax(0, x0, -1), _ax(1, RECESS_Y0), _ax(1, FLOOR, -1), _ax(2, SIDE_SEAM_Z, -1)] + front2, (0.8, 0.15, 0.5)),
        ('fc_rback', [_ax(0, x1), _ax(0, x0, -1), _ax(1, ROOF), _ax(1, RECESS_Y0 - 0.003, -1), _ax(2, SIDE_SEAM_Z, -1), _ax(2, RECESS_Z0)], (0.8, 0.6, 0.0)),
        ('fc_rout', [_ax(0, HW), _ax(0, x1, -1), _ax(1, ROOF), _ax(1, FLOOR, -1), _ax(2, SIDE_SEAM_Z, -1)] + front2, (1.2, 0.5, 0.3)),
        # the ledge in front of the lower plate down to the transmission cover's lip
        ('ledge', [_ax(0, LOW_HW), _ax(0, -LOW_HW, -1), _ax(1, LEDGE[0]), _ax(1, FLOOR, -1), _ax(2, LEDGE[1]), (-lp[0], -lp[1])], (0, 0.1, 2.08)),
        # the fighting compartment behind the seam (chamfered corners), the grille plate, the deck, the rear roof
        ('fc_rear', [_ax(0, DECK_HW), _ax(0, -DECK_HW, -1), _ax(1, ROOF), _ax(1, FLOOR, -1), _ax(2, SIDE_SEAM_Z), _ax(2, REAR_WALL, -1)], (0, 0.5, -0.7)),
        ('grille', [_ax(0, DECK_HW), _ax(0, -DECK_HW, -1), gr, _ax(1, FLOOR, -1), _ax(2, REAR_WALL + 0.003), _ax(2, GRILLE_BOT[1], -1)], (0, 0.3, -1.2)),
        ('deck', [_ax(0, DECK_HW), _ax(0, -DECK_HW, -1), dk, _ax(1, FLOOR, -1), _ax(2, GRILLE_BOT[1] + 0.003), _ax(2, DECK_R[1], -1)], (0, 0.3, -1.9)),
        ('rear_roof', [_ax(0, REAR_CORNER_X), _ax(0, -REAR_CORNER_X, -1), rr, _ax(1, REAR_PLATE_Y[0], -1), _ax(2, DECK_R[1] + 0.003), _ax(2, REAR_ROOF_Z, -1)], (0, 0.4, -2.5)),
        ('overhang', [_ax(0, REAR_CORNER_X), _ax(0, -REAR_CORNER_X, -1), _ax(1, REAR_PLATE_Y[0] + 0.003), _ax(1, FLOOR, -1), _ax(2, LOW_REAR_Z - 0.003), _ax(2, REAR_ROOF_Z, -1)], (0, 0.15, -2.6)),
    ]
    for s, nm in ((1, 'r'), (-1, 'l')):
        xo, xi = (_ax(0, HW), _ax(0, DECK_HW - 0.003, -1)) if s > 0 else (_ax(0, -(DECK_HW - 0.003)), _ax(0, -HW, -1))
        # the side shelf under the chamfers from the seam to the rear
        out.append(('shelf_' + nm, [xo, xi, st, _ax(1, FLOOR, -1), _ax(2, SIDE_SEAM_Z), _ax(2, DECK_R[1], -1)], (s * 1.0, 0.2, -1.5)))
        # chamfer plates as twisted quads split along a diagonal: front part (seam .. rear wall), grille part, deck part;
        # each block lies above the side-top plane and below its chamfer triangle's plane
        cx = s * REAR_CORNER_X; corner = _plane_through((cx, 0, REAR_ROOF_Z), (cx, 1, REAR_ROOF_Z), (s * HW, 0, LOW_REAR_Z), (0, 0.3, -2.0))
        above = (-st[0], -st[1])
        for z0, z1, tag in ((SIDE_SEAM_Z, REAR_WALL, 'a'), (REAR_WALL, GRILLE_BOT[1], 'b'), (GRILLE_BOT[1], REAR_ROOF_Z, 'c')):
            A = (s * DECK_HW, float(roof_edge_y(z0)), z0); B = (s * DECK_HW, float(roof_edge_y(z1)), z1)
            D = (s * HW, float(side_top_y(z0)), z0); C = (s * HW, float(side_top_y(z1)), z1)
            inside = (s * 0.9, 0.2, (z0 + z1) / 2)
            split = _plane_through(B, D, (B[0], B[1] - 1, B[2]), A)
            extra = [corner] if tag == 'c' else []
            def mid(tri, pl):      # a point half way between the side-top plane and the chamfer plane under the triangle's centroid
                cx_, cz_ = np.mean([t[0] for t in tri]), np.mean([t[2] for t in tri])
                return (cx_, 0.5 * (on_plane(pl, x=cx_, z=cz_)[1] + on_plane(st, x=cx_, z=cz_)[1]), cz_)
            p1 = _plane_through(A, B, D, inside); p2 = _plane_through(B, C, D, inside)
            out.append(('cham_%s_%s1' % (nm, tag), [xo, xi, p1, above, _ax(2, z0), _ax(2, z1, -1), split] + extra, mid((A, B, D), p1)))
            out.append(('cham_%s_%s2' % (nm, tag), [xo, xi, p2, above, _ax(2, z0), _ax(2, z1, -1), (-split[0], -split[1])] + extra, mid((B, C, D), p2)))
        # the rear plate's 45 deg corner under the chamfer
        out.append(('rcorner_' + nm, [xo if s > 0 else _ax(0, -HW, -1), _ax(0, cx - 0.003, -1) if s > 0 else _ax(0, cx + 0.003), st, _ax(1, FLOOR, -1), _ax(2, DECK_R[1] + 0.003), corner], (s * 1.15, 0.2, -2.42)))
    res = []
    for name, P, c in out:
        try: V, F = polytope(P, c)
        except Exception as e: raise RuntimeError('block %s: %s' % (name, e))
        res.append((name, V, F))
    return res

def _hull(P):
    from scipy.spatial import ConvexHull
    P = np.asarray(P, float); h = ConvexHull(P); F = []
    for sx, eq in zip(h.simplices, h.equations):
        a, b, c = P[sx]
        if np.dot(np.cross(b - a, c - a), eq[:3]) < 0: sx = sx[[0, 2, 1]]
        F.append(sx)
    return P, np.array(F)

def _rrect(cx, cy, hw, hh, r, n=5):
    pts = []
    for sx, sy, a0 in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        for a in np.linspace(a0, a0 + 90, n):
            pts.append((cx + sx * (hw - r) + r * np.cos(np.radians(a)), cy + sy * (hh - r) + r * np.sin(np.radians(a))))
    return pts

def _plate_R(n):
    """frame of a plate with normal n: columns x (horizontal, in the plate), y (up the plate; forward on a deck), n"""
    n = np.asarray(n, float); n = n / np.linalg.norm(n)
    up = np.array([0, 1.0, 0]) if abs(n[1]) < 0.9 else np.array([0, 0, 1.0])
    y = up - n * (up @ n); y /= np.linalg.norm(y); x = np.cross(y, n)
    return np.c_[x, y, n]

def rbox(c, hw, hh, t, R, r=0.02, n=4):
    pts = []
    for u, v in _rrect(0, 0, hw, hh, min(r, hw * 0.9, hh * 0.9), n):
        for s in (0.0, t): pts.append(np.asarray(c, float) + R[:, 0] * u + R[:, 1] * v + R[:, 2] * s)
    return _hull(pts)

def rod(p, q, r=0.009, seg=6):
    p, q = np.asarray(p, float), np.asarray(q, float); d = q - p; L = np.linalg.norm(d)
    return revolve([(0, r), (L, r)], p, d / L, seg=seg)

def torus(c, R, r, axis=(0, 1.0, 0), seg=36, seg2=8):
    c = np.asarray(c, float); a = np.asarray(axis, float); a /= np.linalg.norm(a)
    u = np.cross(a, [0, 0, 1.0] if abs(a[2]) < 0.9 else [1.0, 0, 0]); u /= np.linalg.norm(u); v = np.cross(a, u)
    V = []; F = []
    for i in range(seg):
        t = 2 * np.pi * i / seg; ring = np.cos(t) * u + np.sin(t) * v
        for j in range(seg2):
            p = 2 * np.pi * j / seg2; V.append(c + ring * (R + r * np.cos(p)) + a * (r * np.sin(p)))
    for i in range(seg):
        for j in range(seg2):
            a0 = i * seg2 + j; a1 = i * seg2 + (j + 1) % seg2; b0 = ((i + 1) % seg) * seg2 + j; b1 = ((i + 1) % seg) * seg2 + (j + 1) % seg2
            F += [[a0, b1, b0], [a0, a1, b1]]
    V = np.array(V); F = np.array(F)
    tri = V[F]; n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]); cen = tri.mean(1)
    rad = cen - c - a * ((cen - c) @ a)[:, None]; ring_c = c + rad / np.linalg.norm(rad, axis=1, keepdims=True) * R
    flip = np.einsum('ij,ij->i', n, cen - ring_c) < 0; F[flip] = F[flip][:, [0, 2, 1]]
    return V, F

# ---------------------------------------------------------------- 75 mm gun M2 in mount M1 (right front sponson)
G75_AXIS = np.array([0.80, 0.52, 1.00])      # trunnions = the shield's centre; bore 0.52 above the datum (reference)
G75_TRAV = 15.0
G75_ELEV = (-9.0, 20.0)
G75_MUZZLE_Z = 2.48                          # the short M2 gun (reference): r 0.055 to z 2.40, the thinner muzzle to 2.48
SHIELD_RX, SHIELD_RY = 0.36, 0.75            # the rounded shield: a spheroid about the trunnions (horizontal / vertical radii)
SHIELD_Y = (RECESS_Y0, ROOF - 0.02)          # clipped at the recess floor and under the roof plate
DISC_C, DISC_R = (0.80, 1.00), 0.47          # the round roof plate over the mount (x, z), radius (the drawing's plan)

def shield75(seg=40, rings=14):
    """the traversing shield: a spheroid about the trunnions clipped top and bottom; trunnion frame"""
    y0, y1 = SHIELD_Y[0] - G75_AXIS[1], SHIELD_Y[1] - G75_AXIS[1]
    prof = []
    for y in np.linspace(y0, y1, rings + 1):
        r = SHIELD_RX * np.sqrt(max(1 - (y / SHIELD_RY) ** 2, 0)); prof.append((y, max(r, 0.02)))
    return revolve(prof, (0, 0, 0), (0, 1.0, 0), seg=seg)

def collar75(seg=18):
    """the gun's collar on the shield (elevates with the gun): r 0.10 from inside the shield to 0.15 beyond it; trunnion frame"""
    z0 = SHIELD_RX - 0.06; z1 = SHIELD_RX + 0.15
    return revolve([(z0, 0.0), (z0, 0.10), (z1 - 0.02, 0.10), (z1, 0.085), (z1, 0.0)], (0, 0, 0), (0, 0, 1.0), seg=seg)

def gun75_barrel(seg=22):
    """75 mm M2: r 0.055 to z 2.40 then the thinner muzzle section to 2.48 (reference); trunnion frame"""
    L = G75_MUZZLE_Z - G75_AXIS[2]; z0 = SHIELD_RX
    prof = [(z0, 0.0), (z0, 0.058), (L - 0.10, 0.055), (L - 0.08, 0.040), (L, 0.038), (L, 0.0)]
    return revolve([(t, max(r, 1e-4)) for t, r in prof], (0, 0, 0), (0, 0, 1.0), seg=seg)

def sponson_disc():
    """the round roof plate over the 75 mm mount, 1.5 cm proud of the roof"""
    return revolve([(-0.015, DISC_R), (0.015, DISC_R), (0.015, 0.0)], (DISC_C[0], ROOF, DISC_C[1]), (0, 1.0, 0), seg=60)

def recess_lip():
    """a strip along the recess floor's front edge"""
    x0, x1 = RECESS_X; z = front_z(RECESS_Y0)
    return box(((x0 + x1) / 2, RECESS_Y0 + 0.01, z - 0.03), (x1 - x0, 0.02, 0.06))

# ---------------------------------------------------------------- bow machine guns (two fixed .30 M1919A4, mount M27)
BOW_MG = dict(x=(-0.58, -0.70), y=0.30, port=(0.26, 0.12))
def bow_mg_pivot():
    x = sum(BOW_MG['x']) / 2; n = lower_plate_plane()[0]; return on_front_plate(x, BOW_MG['y']), n
def bow_mg_port():
    c, n = bow_mg_pivot(); R = _plate_R(n); w, h = BOW_MG['port']
    return rbox(c - n * 0.005, w / 2, h / 2, 0.025, R, r=0.015)
def bow_mg_barrels(seg=10):
    c, n = bow_mg_pivot(); parts = []
    for x in BOW_MG['x']:
        o = np.array([x - c[0], 0.0, 0.0])
        parts.append(revolve([(-0.10, 0.0), (-0.10, 0.016), (0.10, 0.016), (0.11, 0.020), (0.19, 0.024), (0.19, 0.0)], o, (0, 0, 1.0), seg=seg))
    return merge(*parts)

# ---------------------------------------------------------------- side doors (hinged at their front edge)
DOORS = {-1: dict(z=(-0.29, 0.34)), 1: dict(z=(-0.29, 0.40))}
DOOR_Y = (0.174, 0.88)
DOOR_PORT = (0.315, 0.64, 0.32, 0.34)   # port centre: this far behind the door's front edge, height; width, height
def door_pivot(s):
    z1 = DOORS[s]['z'][1] + 0.04
    pivot = np.array([s * (HW + 0.02), (DOOR_Y[0] + DOOR_Y[1]) / 2, z1])
    R = np.array([[0, 0, -1.0], [s, 0, 0], [0, -s, 0]], float)           # local x rearward, y outward, z the hinge
    return pivot, R

def side_door(s):
    z0, z1 = DOORS[s]['z']; y0, y1 = DOOR_Y; dz, py, pw, ph = DOOR_PORT; pz = z1 - dz
    n = np.array([s, 0, 0], float); R = _plate_R(n); x = s * HW
    c = np.array([x, (y0 + y1) / 2, (z0 + z1) / 2])
    parts = [rbox(c, (z1 - z0) / 2, (y1 - y0) / 2, 0.02, R, r=0.03)]
    cp = np.array([x + s * 0.02, py, pz])
    parts.append(rbox(cp, pw / 2, ph / 2, 0.035, R, r=0.03))                                # pistol / vision port block
    parts.append(box(cp + n * 0.045 + [0, ph / 2 - 0.04, 0], (pw * 0.75, 0.03, 0.02), R))      # visor hood over the slot
    hz = z0 + 0.10                                                                          # latch handle at the rear, low
    parts.append(rod((x + s * 0.06, 0.42, hz + 0.09), (x + s * 0.06, 0.42, hz - 0.08), 0.01))
    for ddz in (-0.08, 0.09): parts.append(box((x + s * 0.035, 0.42, hz + ddz), (0.03, 0.025, 0.025), R))
    for y in (0.26, 0.50, 0.73):                                                            # hinge straps on the front edge
        parts.append(box(np.array([x + s * 0.02, y, z1 - 0.05]), (0.14, 0.08, 0.035), R))
        parts.append(rod((x + s * 0.04, y - 0.05, z1 + 0.025), (x + s * 0.04, y + 0.05, z1 + 0.025), 0.016, seg=8))
    dark = [box(cp + n * 0.036 + [0, ph / 2 - 0.085, 0], (pw * 0.55, 0.045, 0.004), R)]
    return parts, dark

def door_frame(s):
    """the rain strip above the door"""
    z0, z1 = DOORS[s]['z']; x = s * HW; n = np.array([s, 0, 0], float); R = _plate_R(n)
    return box((x + s * 0.02, DOOR_Y[1] + 0.02, (z0 + z1) / 2 + 0.03), ((z1 - z0) * 0.65, 0.025, 0.04), R)

# ---------------------------------------------------------------- deck fittings
def grille():
    """two mesh panels on the grille plate (dark recesses), x 0.05 .. 0.55 each side, z -1.08 .. -1.31"""
    n, d = grille_plane(); out = []
    for s in (-1, 1):
        pts = [on_plane(grille_plane(), x=x, z=z) + n * dy for x in (s * 0.05, s * 0.55) for z in (-1.08, -1.31) for dy in (-0.012, 0.003)]
        out.append(_hull(pts))
    return merge(*out)

def grille_bars():
    n = grille_plane()[0]; out = []
    for s in (-1, 1):
        for z in np.arange(-1.10, -1.31, -0.035):
            a, b = on_plane(grille_plane(), x=s * 0.06, z=z), on_plane(grille_plane(), x=s * 0.54, z=z)
            out.append(rod(a - n * 0.004, b - n * 0.004, 0.005, seg=4))
        for x in np.arange(s * 0.09, s * 0.54, s * 0.05):
            a, b = on_plane(grille_plane(), x=x, z=-1.09), on_plane(grille_plane(), x=x, z=-1.30)
            out.append(rod(a - n * 0.004, b - n * 0.004, 0.004, seg=4))
    return merge(*out)

def deck_doors():
    """the two engine doors on the deck (x +-0.02 .. 0.72, z -1.40 .. -2.30), 1.5 cm proud, with handles"""
    n = deck_plane()[0]; R = _plate_R(n); out = []
    for s in (-1, 1):
        c = on_deck(s * 0.37, -1.85); out.append(rbox(c, 0.35, 0.45, 0.015, R, r=0.02))
        for z in (-1.50, -2.20):
            h = on_deck(s * 0.37, z) + n * 0.015; out.append(rod(h + [-0.06, 0, 0] + n * 0.03, h + [0.06, 0, 0] + n * 0.03, 0.008))
            for dx in (-0.06, 0.06): out.append(box(h + [dx, 0, 0] + n * 0.015, (0.02, 0.02, 0.03), R))
    return merge(*out)

def cable_coil():
    """the coiled tow cable on the deck's right half (reference), a torus r 0.33"""
    c = on_deck(0.33, -1.88) + [0, 0.04, 0]; n = deck_plane()[0]
    return torus(c, 0.33, 0.024, n, seg=40, seg2=8)

def chamfer_fittings():
    """ventilator domes and tow shackles on the front chamfer plates (both sides)"""
    out = []
    for s in (-1, 1):
        x, z = s * 1.02, -0.85; y = float(chamfer_y(x, z))
        out.append(revolve([(0.0, 0.13), (0.03, 0.13), (0.06, 0.10), (0.085, 0.05), (0.095, 0.0)], (x, y, z), (0, 1.0, 0), seg=20))
        x2, z2 = s * 1.05, -0.58; y2 = float(chamfer_y(x2, z2))
        out.append(box((x2, y2 + 0.04, z2), (0.10, 0.08, 0.06)))
    return merge(*out)

def stowage_boxes():
    """the stowage boxes on the rear chamfers (x 0.90 .. 1.255, z -1.27 .. -2.34, top 0.86), lids with latches"""
    out = []
    for s in (-1, 1):
        x0, x1 = 0.90, HW - 0.021; z0, z1 = -2.34, -1.27; y0, y1 = 0.44, 0.86
        out.append(box(((s * (x0 + x1) / 2), (y0 + y1) / 2, (z0 + z1) / 2), (x1 - x0, y1 - y0, z1 - z0)))
        out.append(box(((s * (x0 + x1) / 2), y1 + 0.008, (z0 + z1) / 2), (x1 - x0 + 0.02, 0.016, z1 - z0 + 0.02)))   # lid
        for z in (z0 + 0.20, (z0 + z1) / 2, z1 - 0.20):                                      # latches on the outer side
            out.append(box((s * (x1 + 0.012), y1 - 0.05, z), (0.024, 0.08, 0.04)))
        for z in (z0 + 0.18, z1 - 0.18):                                                     # lid hinges on the inner side
            out.append(rod((s * (x0 - 0.005), y1 + 0.016, z - 0.04), (s * (x0 - 0.005), y1 + 0.016, z + 0.04), 0.012))
    return merge(*out)

def tail_lights():
    """tail lights in the rear corners (a drum pointing back at y 0.35, z -2.51 .. -2.66) with a bracket"""
    out = []
    for s in (-1, 1):
        c = np.array([s * (REAR_CORNER_X + 0.04), 0.35, -2.51])
        out.append(revolve([(0.0, 0.0), (0.0, 0.065), (0.13, 0.065), (0.15, 0.04), (0.15, 0.0)], c, (0, 0, -1.0), seg=14))
        out.append(box(c + [0, 0, -0.02], (0.04, 0.16, 0.05)))
    return merge(*out)

def exhaust_deflectors():
    out = []
    for s in (-1, 1):
        pts = [(s * 0.62 + dx, y, z) for dx in (-0.075, 0.075) for y in (0.10, 0.24) for z in (LOW_REAR_Z - 0.12, LOW_REAR_Z + 0.01)]
        out.append(_hull(pts))
    return merge(*out)

def fenders():
    """the short mudguards over the track ends (reference: front flat y 0.06 from z 1.96 to 2.62, curling down to
    (2.80, -0.05); rear from -2.45 to -2.72 at y -0.02), 8 mm plates"""
    out = []
    for sx in (-1, 1):
        for prof in (((1.96, 0.065), (2.50, 0.065), (2.64, 0.045), (2.80, -0.05)),
                     ((-2.45, 0.0), (-2.62, 0.0), (-2.72, -0.05), (-2.84, -0.14))):
            for (za, ya), (zb, yb) in zip(prof[:-1], prof[1:]):
                pts = [(sx * x, y + dy, z) for x in (0.875, 1.255) for (z, y) in ((za, ya), (zb, yb)) for dy in (0.0, 0.008)]
                out.append(_hull(np.array(pts)))
        out.append(box((sx * 1.0, 0.03, 2.0), (0.25, 0.06, 0.06)))
    return merge(*out)

HEADLIGHT = dict(x=0.95, y=0.18, z=1.98, r=0.085)
def headlights():
    """headlights low on the front (reference: lamp centre y 0.18, z 1.98) with a stalk and a tall hoop guard; list"""
    out = []
    for sx in (-1, 1):
        c = np.array([sx * HEADLIGHT['x'], HEADLIGHT['y'], HEADLIGHT['z']]); r = HEADLIGHT['r']
        out.append(revolve([(0.0, 0.0), (0.0, r), (0.10, r), (0.12, r * 0.7), (0.12, 0.0)], c - [0, 0, 0.06], (0, 0, 1.0), seg=16))
        out.append(box(c + [0, -0.07, -0.05], (0.04, 0.08, 0.04)))                               # stalk down to the fender
        pts = [c + [0.14 * np.cos(a), 0.14 * np.sin(a) + 0.05, 0.09] for a in np.linspace(0, np.pi, 9)]
        for p, q in zip(pts[:-1], pts[1:]): out.append(rod(p, q, 0.008))
        out.append(rod(pts[0], pts[0] + [0, -0.17, 0], 0.008)); out.append(rod(pts[-1], pts[-1] + [0, -0.17, 0], 0.008))
    return out

def headlight_lenses():
    out = []
    for sx in (-1, 1):
        c = np.array([sx * HEADLIGHT['x'], HEADLIGHT['y'], HEADLIGHT['z']]); r = HEADLIGHT['r']
        out.append(revolve([(0.0, 0.0), (0.0, r * 0.85), (0.006, r * 0.85), (0.006, 0.0)], c + [0, 0, 0.045], (0, 0, 1.0), seg=16))
    return merge(*out)

def siren_horn():
    """the siren beside the right headlight on the lower front plate (x 0.60, y 0.22)"""
    n = lower_plate_plane()[0]; R = _plate_R(n); c = on_front_plate(0.60, 0.22)
    return merge(box(c + n * 0.03, (0.07, 0.09, 0.06), R),
                 revolve([(0.0, 0.001), (0.0, 0.075), (0.09, 0.075), (0.12, 0.05), (0.12, 0.0)], c + n * 0.05, n, seg=14))

def roof_fittings():
    """the ventilator dome on the roof's left front, the 75 mm periscope box on the roof plate, lifting lugs; list"""
    out = [revolve([(0.0, 0.11), (0.03, 0.11), (0.06, 0.085), (0.085, 0.045), (0.095, 0.0)], (-0.95, ROOF, 0.83), (0, 1.0, 0), seg=20)]
    y0 = ROOF + 0.015; x, z = DISC_C[0] - 0.30, DISC_C[1] - 0.17
    out.append(_hull([(x + dx, y0 + h, z + dz) for dx in (-0.10, 0.10) for dz in (-0.065, 0.065) for h in (0.0, 0.11)]))
    return out

def roof_hatch_pivot():
    """the 75 mm crew's hatch in the round roof plate (x 0.78 .. 1.12, z 0.63 .. 0.97): hinged on its front edge"""
    return np.array([0.95, ROOF + 0.015, 0.97])
def roof_hatch():
    p = roof_hatch_pivot(); R = np.array([[1.0, 0, 0], [0, 0, 1.0], [0, 1.0, 0]])
    parts = [rbox(np.array([0.95, ROOF + 0.015, 0.80]), 0.17, 0.17, 0.03, R, r=0.03)]
    parts.append(box((0.95, ROOF + 0.05, 0.70), (0.10, 0.02, 0.02)))
    for dx in (-0.10, 0.10): parts.append(rod(p + [dx - 0.025, 0.02, 0.0], p + [dx + 0.025, 0.02, 0.0], 0.012, seg=8))
    return parts

def drivers_door():
    """driver's vision port on the upper front plate (x -0.42 .. -0.08, y 0.60 .. 0.90): a port block with its visor"""
    n, d = front_plate_plane(); R = _plate_R(n); c = on_front_plate(-0.25, 0.75)
    parts = [rbox(c, 0.17, 0.15, 0.035, R, r=0.03), box(c + n * 0.045 + R[:, 1] * 0.10, (0.26, 0.03, 0.02), R)]
    dark = [box(c + n * 0.036 + R[:, 1] * 0.055, (0.20, 0.045, 0.004), R)]
    return parts, dark

def cheek_ports():
    """vision ports with visors: on the left cheek (projected centre z 1.158, y 0.76; frame 0.36 x 0.38) and on the
    right side plate's front part (z 1.22, y 0.76; 0.24 x 0.31); list of (parts, dark)"""
    out = []
    n, d = cheek_plane(); R = _plate_R(n); c = on_cheek(0.76, 1.158)
    hw, hh = 0.18, 0.19
    parts = [rbox(c, hw, hh, 0.035, R, r=0.03), box(c + n * 0.045 + R[:, 1] * (hh - 0.09), (2 * hw - 0.08, 0.03, 0.02), R)]
    dark = [box(c + n * 0.036 + R[:, 1] * (hh - 0.135), (2 * hw - 0.14, 0.045, 0.004), R)]
    out.append((parts, dark))
    n = np.array([1.0, 0, 0]); R = _plate_R(n); c = np.array([HW, 0.76, 1.22]); hw, hh = 0.12, 0.155
    parts = [rbox(c, hw, hh, 0.035, R, r=0.025), box(c + n * 0.045 + R[:, 1] * (hh - 0.07), (2 * hw - 0.06, 0.025, 0.018), R)]
    dark = [box(c + n * 0.036 + R[:, 1] * (hh - 0.11), (2 * hw - 0.10, 0.04, 0.004), R)]
    out.append((parts, dark))
    return out

# ---------------------------------------------------------------- 37 mm turret (cast, M24 combination mount, MG cupola)
TUR_AXIS = np.array([-0.31, ROOF, -0.06])    # r 0.80 walls: rear at z -0.86 (reference), x 0.49 .. -1.11
TUR_R = 0.80
TUR_PROFILE = [(0.0, 0.83), (0.04, 0.83), (0.055, 0.80), (0.30, 0.80), (0.46, 0.795)] + \
              [(0.46 + 0.22 * np.sin(np.radians(a)), 0.575 + 0.22 * np.cos(np.radians(a))) for a in (20, 40, 60, 80)] + [(0.68, 0.575), (0.68, 0.0)]
TUR_TOP = ROOF + 0.68
TUR_FRONT = [(0.60, 0.0), (0.60, 0.03), (0.47, 0.20), (0.44, 0.40), (0.06, 0.68)]   # (z ahead of the centre, height above the roof)
G37_TRUN = np.array([-0.265, 1.307, 0.25])   # bore x -0.265, height 1.307 (reference)
G37_MUZZLE_Z = 1.89
G37_ELEV = (-7.0, 60.0)
COAX_DX, COAX_DY, COAX_MUZZLE_Z = 0.12, -0.02, 1.45   # the .30 beside the 37 (on its right), muzzle z 1.45
MANTLET = dict(x0=-0.855, x1=0.065, y0=1.20, y1=1.40, r=0.09, front=0.47)   # rotor shield: outline and its front face z
CUP_AXIS = np.array([-0.66, TUR_TOP, -0.39]) # the MG cupola on the turret's left rear
CUP_R, CUP_H = 0.32, 0.21                    # body radius, height of the rim above the turret top
CUP_HATCH_R = 0.25
CUP_MG = np.array([-0.55, 1.71, 0.0])        # the cupola's .30: height (reference 1.71)
CUP_MG_MUZZLE_Z = 0.26

def turret_body(seg=72):
    V, F = revolve(TUR_PROFILE, TUR_AXIS, (0, 1.0, 0), seg=seg, cap_start=True, cap_end=False)
    zs, hs = np.array(TUR_FRONT).T
    h = V[:, 1] - TUR_AXIS[1]; zl = np.interp(h, hs, zs)
    d = V[:, 2] - TUR_AXIS[2]; V = V.copy(); V[:, 2] = TUR_AXIS[2] + np.minimum(d, zl)
    return _hull(np.unique(np.round(V, 5), axis=0))

def turret_front_z(y):
    zs, hs = np.array(TUR_FRONT).T; return TUR_AXIS[2] + np.interp(y - TUR_AXIS[1], hs, zs)

def mantlet37():
    """rotor shield of the M24 mount: a rounded block from inside the turret's front out to z 0.47 (reference), its
    front rounded; trunnion frame"""
    m = MANTLET; a = G37_TRUN
    outline = _rrect((m['x0'] + m['x1']) / 2, (m['y0'] + m['y1']) / 2, (m['x1'] - m['x0']) / 2, (m['y1'] - m['y0']) / 2, m['r'], n=6)
    pts = []
    for x, y in outline:
        pts.append((x - a[0], y - a[1], m['front'] - a[2])); pts.append((x - a[0], y - a[1], 0.10 - a[2]))
    inner = _rrect((m['x0'] + m['x1']) / 2, (m['y0'] + m['y1']) / 2, (m['x1'] - m['x0']) / 2 - 0.04, (m['y1'] - m['y0']) / 2 - 0.04, m['r'], n=6)
    for x, y in inner: pts.append((x - a[0], y - a[1], m['front'] + 0.035 - a[2]))
    return _hull(pts)

def mantlet_bolts():
    m = MANTLET; a = G37_TRUN; out = []
    for x, y in _rrect((m['x0'] + m['x1']) / 2, (m['y0'] + m['y1']) / 2, (m['x1'] - m['x0']) / 2 - 0.03, (m['y1'] - m['y0']) / 2 - 0.03, 0.06, n=3):
        c = np.array([x - a[0], y - a[1], m['front'] + 0.035 - a[2]])
        out.append(revolve([(0.0, 0.012), (0.012, 0.012), (0.012, 0.0)], c + [0, 0, -0.002], (0, 0, 1.0), seg=6))
    return merge(*out)

def gun37_barrel(seg=16):
    """M6 37 mm: the recoil jacket r 0.051 from the shield's face to z 0.86, then the barrel r 0.03 to the muzzle at 1.89"""
    L = G37_MUZZLE_Z - G37_TRUN[2]; z1 = 0.86 - G37_TRUN[2]
    prof = [(0.10, 0.0), (0.10, 0.051), (z1, 0.051), (z1 + 0.012, 0.034), (L - 0.04, 0.030), (L, 0.031), (L, 0.0)]
    return revolve([(t, max(r, 1e-4)) for t, r in prof], (0, 0, 0), (0, 0, 1.0), seg=seg)

def coax_barrel(seg=10):
    L = COAX_MUZZLE_Z - G37_TRUN[2]
    return revolve([(0.15, 0.0), (0.15, 0.03), (L - 0.30, 0.03), (L - 0.29, 0.014), (L, 0.014), (L, 0.0)], (COAX_DX, COAX_DY, 0), (0, 0, 1.0), seg=seg)

def turret_fittings():
    """the pistol / sight ports on both front quarters, the periscope box on the roof's front right, the ventilator
    dome, lifting lugs; world coords; returns (parts, dark)"""
    out = []; dark = []
    for b, w, h, yc in ((50.0, 0.20, 0.22, 1.26), (-50.0, 0.20, 0.22, 1.26)):
        b = np.radians(b); n = np.array([np.sin(b), 0, np.cos(b)]); r = TUR_R
        c = TUR_AXIS + [0, yc - ROOF, 0] + n * (r - 0.01); R = _plate_R(n)
        out.append(rbox(c, w / 2, h / 2, 0.04, R, r=0.02))
        out.append(box(c + n * 0.05 + R[:, 1] * (h / 2 - 0.06), (w - 0.06, 0.03, 0.016), R))
        dark.append(box(c + n * 0.041 + R[:, 1] * (h / 2 - 0.085), (w - 0.1, 0.022, 0.004), R))
    tx, tz = TUR_AXIS[0], TUR_AXIS[2]
    out.append(_hull([(tx + 0.40 + dx, y, tz + 0.12 + dz) for dx in (-0.08, 0.08) for dz in (-0.10, 0.10) for y in (1.50, 1.76)]))   # periscope box
    out.append(revolve([(0.0, 0.11), (0.03, 0.11), (0.05, 0.08), (0.065, 0.04), (0.07, 0.0)], (tx + 0.28, TUR_TOP, tz - 0.38), (0, 1.0, 0), seg=18))
    for x, z in ((tx + 0.52, tz + 0.22), (tx - 0.10, tz + 0.52)):
        out.append(revolve([(0.0, 0.0), (0.0, 0.04), (0.03, 0.04), (0.03, 0.0)], (x, TUR_TOP - 0.02, z), (0, 1.0, 0), seg=10))
    return out, dark

def mantlet_sight_bar():
    """the hood over the gunner's sight on the mantlet's left part"""
    a = G37_TRUN; z = MANTLET['front'] + 0.035 + 0.06
    return revolve([(0.0, 0.0), (0.0, 0.035), (0.19, 0.035), (0.19, 0.0)], (-0.705 - a[0], 1.305 - a[1], z - a[2]), (1.0, 0, 0), seg=12)

def cupola(seg=44):
    return revolve([(-0.22, 0.0), (-0.22, CUP_R), (CUP_H - 0.04, CUP_R), (CUP_H - 0.01, CUP_R - 0.03),
                    (CUP_H, CUP_R - 0.06), (CUP_H, 0.0)], (0, 0, 0), (0, 1.0, 0), seg=seg)

def cupola_slits(seg=5):
    hoods = []; dark = []
    for a in np.radians([60, 120, 180, 240, 300]):
        n = np.array([np.sin(a), 0, np.cos(a)]); R = _plate_R(n); c = n * CUP_R + [0, CUP_H - 0.08, 0]
        hoods.append(box(c + n * 0.008 + [0, 0.03, 0], (0.13, 0.025, 0.016), R))
        dark.append(box(c + n * 0.002, (0.10, 0.022, 0.004), R))
    return hoods, dark

def cupola_hatch_pivot(): return np.array([0.0, CUP_H, -(CUP_HATCH_R - 0.02)])
def cupola_hatch():
    c = np.array([0, 0, CUP_HATCH_R - 0.02])
    V, F = revolve([(0.0, CUP_HATCH_R), (0.025, CUP_HATCH_R), (0.035, CUP_HATCH_R - 0.012), (0.035, 0.0)], c, (0, 1.0, 0), seg=36)
    parts = [(V, F), rod((-0.05, 0.02, 0.0), (0.05, 0.02, 0.0), 0.014, seg=8), rod((-0.13, 0.02, 0.0), (-0.09, 0.02, 0.0), 0.014, seg=8),
             rod((0.09, 0.02, 0.0), (0.13, 0.02, 0.0), 0.014, seg=8), box(c + [0, 0.045, 0.06], (0.10, 0.02, 0.02))]
    return parts

def cupola_mg(seg=10):
    """the cupola's .30 in its mount on the cupola front: the jacket to z 0.17, the barrel to 0.26; MG frame (pivot
    CUP_MG at the cupola's front face); returns (jacket, mount block)"""
    L = CUP_MG_MUZZLE_Z - (CUP_AXIS[2] + CUP_R)
    jacket = revolve([(-0.06, 0.0), (-0.06, 0.035), (L - 0.07, 0.035), (L - 0.06, 0.012), (L, 0.012), (L, 0.0)], (0, 0, 0), (0, 0, 1.0), seg=seg)
    rotor = _hull([(x, y, z) for x in (-0.09, 0.09) for y in (-0.08, 0.08) for z in (-0.12, 0.03)])
    return jacket, rotor

# ---------------------------------------------------------------- tools on the hull
def pick_axe():
    """the pick (head at the front, z -0.60 .. -0.74, y 0.30 .. 0.38; handle to z -1.78) on the left side plate, and the
    axe on the right side plate (head at the front); both on brackets 3 cm off the plate"""
    out = []
    x = -HW - 0.03
    out.append(rod((x, 0.30, -0.68), (x, 0.30, -1.78), 0.016, seg=8))                                  # pick handle
    out.append(_hull([(x + dx, y, z) for dx in (-0.025, 0.025) for y in (0.26, 0.42) for z in (-0.60, -0.76)]))   # pick head (a flat wedge)
    for z in (-0.95, -1.55): out.append(box((x + 0.02, 0.30, z), (0.03, 0.05, 0.03)))                  # straps
    x = HW + 0.03
    out.append(rod((x, 0.30, -0.70), (x, 0.30, -1.65), 0.015, seg=8))                                  # axe handle
    out.append(_hull([(x + dx, y, z) for dx in (-0.02, 0.02) for y in (0.22, 0.40) for z in (-0.58, -0.72)]))     # axe head
    for z in (-0.95, -1.45): out.append(box((x - 0.02, 0.30, z), (0.03, 0.05, 0.03)))
    return merge(*out)

def deck_tools():
    """the shovel inside the cable coil and the crowbar beside it on the deck"""
    n = deck_plane()[0]; out = []
    a, b = on_deck(0.55, -1.78) + n * 0.03, on_deck(0.10, -2.02) + n * 0.03
    out.append(rod(a, b, 0.014, seg=8))                                                                # shovel handle
    d = (a - b); d /= np.linalg.norm(d); w = np.cross(n, d)
    blade = [a + d * t + w * s + n * h for t in (0.0, 0.26) for s in (-0.09, 0.09) for h in (0.0, 0.012)]
    out.append(_hull(blade))
    out.append(rod(on_deck(-0.25, -1.45) + n * 0.03, on_deck(-0.25, -2.25) + n * 0.03, 0.012, seg=6))   # crowbar
    return merge(*out)

# ---------------------------------------------------------------- rivets
RIVET_PITCH = 0.09
def rivet_lines():
    rows = []
    def row(p, q, nrm, pitch=RIVET_PITCH):
        p, q = np.asarray(p, float), np.asarray(q, float); L = np.linalg.norm(q - p); k = max(int(round(L / pitch)), 1)
        t = np.linspace(0.5 / k, 1 - 0.5 / k, k); rows.append((p + (q - p)[None] * t[:, None], np.asarray(nrm, float)))
    def ring(c, r, pitch=RIVET_PITCH, nrm=(0, 1, 0)):
        c = np.asarray(c, float); k = max(int(round(2 * np.pi * r / pitch)), 6); a = np.linspace(0, 2 * np.pi, k, endpoint=False)
        rows.append((c + np.c_[r * np.sin(a), np.zeros(k), r * np.cos(a)], np.asarray(nrm, float)))
    fpn = front_plate_plane()[0]; lpn = lower_plate_plane()[0]; dkn = deck_plane()[0]; grn = grille_plane()[0]; chn = cheek_plane()[0]
    for s in (-1, 1):
        nx = (s, 0, 0); x = s * (HW + 0.003); z0d, z1d = DOORS[s]['z']
        zf = front_z(0.97, HW) if s > 0 else CHEEK_A[2]                  # the side's front corner at the top row
        zfb = front_z(0.12, HW) if s > 0 else (CHEEK_C[2] - 0.03)
        # side plates: top row y 0.97 (seam .. rear wall), bottom row y 0.12, the seam's vertical double row, door frame
        row((x, 0.97, zf - 0.06), (x, 0.97, REAR_WALL + 0.05), nx); row((x, 0.12, zfb - 0.06), (x, 0.12, -2.42), nx)
        for dz in (0.036, -0.04): row((x, 0.17, SIDE_SEAM_Z + dz), (x, 0.92, SIDE_SEAM_Z + dz), nx)
        for zz in (z1d + 0.05, z0d - 0.05): row((x, 0.22, zz), (x, 0.84, zz), nx)
        row((x, DOOR_Y[1] + 0.05, z1d + 0.08), (x, DOOR_Y[1] + 0.05, z0d - 0.08), nx)
        row((x, DOOR_Y[0] - 0.05, z1d + 0.08), (x, DOOR_Y[0] - 0.05, z0d - 0.08), nx)
        # the row under the sloping top edge behind the seam, the chamfer's edge rows
        row((x, side_top_y(SIDE_SEAM_Z - 0.1) - 0.04, SIDE_SEAM_Z - 0.1), (x, side_top_y(-2.33) - 0.04, -2.33), nx)
        row((s * (DECK_HW + 0.04), float(chamfer_y(DECK_HW + 0.04, SIDE_SEAM_Z - 0.08)) + 0.003, SIDE_SEAM_Z - 0.08), (s * (DECK_HW + 0.04), float(chamfer_y(DECK_HW + 0.04, -2.33)) + 0.003, -2.33), (s * 0.5, 0.85, 0))
        if s < 0:
            # left cheek: a row each side of the side seam, of the front seam, along the roof edge
            A, B, C = (np.array(CHEEK_A), np.array(CHEEK_B), np.array(CHEEK_C))
            row(A + [0, -0.05, -0.04], C + [0, 0.07, -0.04], nx)
            e = np.cross(C - A, chn); e /= np.linalg.norm(e); e *= np.sign(e @ np.array([0, 0, 1.0]))
            row(A + e * 0.04 + chn * 0.002 + [0, -0.05, 0], C + e * 0.04 + chn * 0.002 + [0, 0.07, 0], chn)
            top = on_cheek(ROOF - 0.05, front_z(ROOF - 0.05)); bend = on_cheek(BEND[0], front_z(BEND[0])); bot = on_cheek(FLOOR + 0.08, front_z(FLOOR + 0.08))
            for p, q in ((top, bend), (bend, bot)):
                f = np.cross(q - p, chn); f /= np.linalg.norm(f); f *= -np.sign(f @ np.array([1.0, 0, 0]))
                row(p + f * 0.04 + chn * 0.002, q + f * 0.04 + chn * 0.002, chn)
            row(on_front_plate(CHEEK_B[0] + 0.04, ROOF - 0.05) + fpn * 0.002, on_front_plate(CHEEK_B[0] + 0.04, BEND[0] + 0.02) + fpn * 0.002, fpn)
            row(on_front_plate(-0.74, BEND[0] - 0.02) + lpn * 0.002, on_front_plate(-0.74, FLOOR + 0.08) + lpn * 0.002, lpn)
            row(A + [-0.04, 0.003, -0.05], B + [-0.04, 0.003, -0.05], (0, 1, 0))
        else:
            # right side plate's front edge rows (along the front plates' lean)
            row((x, 0.95, front_z(0.95, HW) - 0.05), (x, BEND[0] + 0.02, front_z(BEND[0] + 0.02, HW) - 0.05), nx)
            row((x, BEND[0] - 0.02, front_z(BEND[0] - 0.02, HW) - 0.05), (x, 0.12, front_z(0.12, HW) - 0.05), nx)
            row(on_front_plate(HW - 0.04, 0.95) + fpn * 0.002, on_front_plate(HW - 0.04, BEND[0] + 0.02) + fpn * 0.002, fpn)
            row(on_front_plate(HW - 0.04, BEND[0] - 0.02) + lpn * 0.002, on_front_plate(HW - 0.04, FLOOR + 0.08) + lpn * 0.002, lpn)
    # front plates: top row under the roof edge, rows along the bend (both plates), along the recess's inner edge, the
    # bottom row, the driver's port frame
    row(on_front_plate(CHEEK_B[0] + 0.08, 0.95) + fpn * 0.002, on_front_plate(RECESS_X[0] - 0.05, 0.95) + fpn * 0.002, fpn)
    row(on_front_plate(RECESS_X[1] + 0.05, 0.95) + fpn * 0.002, on_front_plate(HW - 0.08, 0.95) + fpn * 0.002, fpn)
    row(on_front_plate(-0.70, BEND[0] + 0.035) + fpn * 0.002, on_front_plate(HW - 0.08, BEND[0] + 0.035) + fpn * 0.002, fpn)
    row(on_front_plate(-0.70, BEND[0] - 0.035) + lpn * 0.002, on_front_plate(HW - 0.08, BEND[0] - 0.035) + lpn * 0.002, lpn)
    row(on_front_plate(-0.70, 0.12) + lpn * 0.002, on_front_plate(HW - 0.08, 0.12) + lpn * 0.002, lpn)
    row(on_front_plate(RECESS_X[0] - 0.04, 0.90) + fpn * 0.002, on_front_plate(RECESS_X[0] - 0.04, 0.36) + fpn * 0.002, fpn)
    row(on_front_plate(RECESS_X[0] + 0.04, 0.26) + lpn * 0.002, on_front_plate(RECESS_X[0] + 0.04, 0.10) + lpn * 0.002, lpn)
    for y in (0.56, 0.94): row(on_front_plate(-0.46, y), on_front_plate(-0.04, y), fpn, pitch=0.08)
    # roof: the front edge row, the seam's roof row, the rear wall's top row, the side edges, the turret ring, the disc ring
    row((CHEEK_B[0] + 0.05, ROOF + 0.003, FP_TOP[1] - 0.05), (RECESS_X[0] - 0.05, ROOF + 0.003, FP_TOP[1] - 0.05), (0, 1, 0))
    row((RECESS_X[1] + 0.05, ROOF + 0.003, FP_TOP[1] + FRONT_STEP - 0.05), (HW - 0.05, ROOF + 0.003, FP_TOP[1] + FRONT_STEP - 0.05), (0, 1, 0))
    row((HW - 0.05, ROOF + 0.003, SIDE_SEAM_Z + 0.04), (-HW + 0.05, ROOF + 0.003, SIDE_SEAM_Z + 0.04), (0, 1, 0))
    row((DECK_HW - 0.05, ROOF + 0.003, REAR_WALL + 0.05), (-DECK_HW + 0.05, ROOF + 0.003, REAR_WALL + 0.05), (0, 1, 0))
    row((HW - 0.05, ROOF + 0.003, FP_TOP[1] + FRONT_STEP - 0.15), (HW - 0.05, ROOF + 0.003, SIDE_SEAM_Z + 0.1), (0, 1, 0))
    row((-HW + 0.05, ROOF + 0.003, CHEEK_A[2] - 0.05), (-HW + 0.05, ROOF + 0.003, SIDE_SEAM_Z + 0.1), (0, 1, 0))
    ring(TUR_AXIS + [0, 0.003, 0], 0.87)
    ring((DISC_C[0], ROOF + 0.018, DISC_C[1]), DISC_R - 0.03, pitch=0.10)
    # grille plate edges, deck doors, deck rear edge, the rear plate's rows
    row(on_plane(grille_plane(), x=0.70, z=-1.06) + grn * 0.003, on_plane(grille_plane(), x=-0.70, z=-1.06) + grn * 0.003, grn)
    row(on_plane(grille_plane(), x=0.70, z=-1.32) + grn * 0.003, on_plane(grille_plane(), x=-0.70, z=-1.32) + grn * 0.003, grn)
    for x in (0.72, -0.72): row(on_deck(x, -1.38) + [0, 0.003, 0], on_deck(x, -2.32) + [0, 0.003, 0], dkn)
    row(on_deck(0.70, -2.38) + [0, 0.003, 0], on_deck(-0.70, -2.38) + [0, 0.003, 0], dkn)
    row((REAR_CORNER_X - 0.05, DECK_R[0] + 0.003, REAR_ROOF_Z + 0.05), (-REAR_CORNER_X + 0.05, DECK_R[0] + 0.003, REAR_ROOF_Z + 0.05), (0, 1, 0))
    for y in (0.33, 0.49): row((REAR_CORNER_X - 0.05, y, REAR_ROOF_Z - 0.003), (-REAR_CORNER_X + 0.05, y, REAR_ROOF_Z - 0.003), (0, 0, -1))
    return [(p, n) for p, n in rows if len(p)]

def rivet_mesh(pts, nrms, r=0.02, h=0.012):
    V = []; F = []
    for p, n in zip(pts, nrms):
        n = np.asarray(n, float); n = n / np.linalg.norm(n)
        u = np.cross(n, [0, 1.0, 0] if abs(n[1]) < 0.9 else [1.0, 0, 0]); u /= np.linalg.norm(u); v = np.cross(n, u)
        b = len(V)
        for k in range(6):
            a = np.pi / 3 * k; V.append(p - n * 0.002 + r * (np.cos(a) * u + np.sin(a) * v))
        V.append(p + n * h)
        F += [[b + k, b + (k + 1) % 6, b + 6] for k in range(6)]
    if not V: return np.zeros((0, 3)), np.zeros((0, 3), int)
    V = np.array(V); F = np.array(F)
    T = V[F]; nr = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); ref = np.repeat(np.asarray(nrms, float), 6, axis=0)
    flip = np.einsum('ij,ij->i', nr, ref) < 0; F[flip] = F[flip][:, [0, 2, 1]]
    return V, F

def all_rivets():
    P = []; N = []
    for pts, n in rivet_lines():
        P.append(pts); N.append(np.tile(n / np.linalg.norm(n), (len(pts), 1)))
    return rivet_mesh(np.vstack(P), np.vstack(N))

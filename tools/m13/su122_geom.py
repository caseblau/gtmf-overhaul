"""SU-122 (1943, UZTM production) new parts on the Mius-Front T-34 mod. 1942 hull (t34_42_utz).

Hull frame: x right, y up, z forward, metres; T-34 track bottom (ground) at y = -1.14, deck at y = 0.524.
v20 (2026-10-30): casemate, gun mount and roof fittings re-fitted to the user's two scale drawings (A: line drawing with
a 0-3 m bar, B: shaded drawing), each view registered on T-34 parts (road wheels, idler, sprocket, rear hull, engine
deck); where A and B disagree the value between them is used and the factory photos decide.
Sources for the shape: Wikipedia SU-122 (5.95 m hull, 6.95 m with gun, 3.0 m wide, 2.235-2.32 m high, 45 mm front,
gun -3..+26 deg, +-5 deg traverse), T-34 hull planes measured on the game mesh (glacis 60 deg, upper sides 40 deg).
Checked against ru.wikipedia "СУ-122" (2026-10-30): hull 6.95 m long with the gun, 3.0 m wide, 2.235 m high;
casemate front 45 mm / 50 deg, sides 45 / 20, rear 45 / 10, roof 20; production vehicles from spring 1943 have ONE front
plate at 50 deg from the nose to the roof (the early "broken" front had two); the howitzer pedestal sits right of the
centre line; crew: driver, gunner, loader left of the gun, commander and breech operator right of it; one entry hatch
in the roof, an opening for the panoramic-sight hood, a PTK periscope instead of the early cupola and a roof fan;
mirror vision devices with armoured visors on the front, rear and right plates; driver's hatch in the front plate;
four external 90 l fuel tanks along the engine-compartment sides; 45 mm cast mantlet.
"""
import numpy as np
import geom
from geom import polytope, revolve, box, merge

GROUND = -1.14                 # track bottom: wheel centres -0.676, road wheel r 0.415, track 0.05
# roof (v20): drawing A puts it at y 0.745 (side view) / 0.785 (front and rear views), drawing B at 0.84 / 0.898, the
# calibrated factory photos at 0.79-0.89; the documented 2.235 m overall height is the PTK head, 0.24-0.26 m above the
# roof in both drawings -> 0.82 (1.96 m above the ground; v19: 0.92, 10 cm too high for every source but one photo)
ROOF = 0.82
FENDER_Y, FENDER_X = -0.03, 1.29
GLACIS = (np.array([0.0, 0.863, 0.506]), 1.0806)           # n.x <= d keeps the inside
DECK_Y = 0.524
a50 = np.radians(51.2); a20 = np.radians(20); a10 = np.radians(10)
z_glacis_top = (GLACIS[1] - GLACIS[0][1] * DECK_Y) / GLACIS[0][2]
NOSE_Y, NOSE_Z, NOSE_X = -0.413, 2.76, 0.90          # top edge of the T-34 nose beam (lower front plate / glacis junction)
FRONT = (np.array([0, np.sin(a50), np.cos(a50)]), np.sin(a50) * NOSE_Y + np.cos(a50) * NOSE_Z)   # one plate, nose to roof;
# v23: 51.2 deg from the T-34 nose puts the roof edge at z 1.227 (v20-v22: the documented 50 deg, 1.29). Line fits on
# the side views: drawing A 50.0 deg with the roof edge at 1.221 (7 cm behind the T-34 nose at the bottom), drawing B
# 48.5 deg through the nose (roof edge 1.37); the three side factory photos put the roof corner at 1.19-1.20. The plate
# keeps meeting the nose and takes A's and the photos' top edge.
SIDE_D = np.cos(a20) * FENDER_X + np.sin(a20) * FENDER_Y
REAR_Z = -0.11                 # rear plate at roof height: calibrated factory photos -0.09..-0.13; drawing A -0.15, B +0.01

SPONSON_Y = -0.026            # underside of the T-34 sponsons (= top of the track run area), measured on the game mesh
LOWER_X = 0.897               # T-34 lower hull side is at |x| 0.899
REAR_PLANE = (np.array([0, np.sin(a10), -np.cos(a10)]), np.sin(a10) * ROOF - np.cos(a10) * REAR_Z)   # rear plate leans forward 10 deg

def casemate():
    """upper casemate: from the sponson underside up to the roof, full width over the tracks"""
    planes = [FRONT,
              (np.array([np.cos(a20), np.sin(a20), 0]), SIDE_D), (np.array([-np.cos(a20), np.sin(a20), 0]), SIDE_D),
              (np.array([0, 1.0, 0]), ROOF), (np.array([0, -1.0, 0]), -(SPONSON_Y + 0.004)),
              (np.array([1.0, 0, 0]), FENDER_X), (np.array([-1.0, 0, 0]), FENDER_X), REAR_PLANE]
    return polytope(planes, [0, 0.5, 0.2]), planes

def casemate_lower():
    """the front plate below the sponsons runs down to the nose only between the tracks (|x| < 0.897); before v17 the
    casemate went down to the nose at full width, which hung a 0.4 m skirt over the upper track run"""
    planes = [FRONT, (np.array([0, -1.0, 0]), -NOSE_Y), (np.array([0, 1.0, 0]), SPONSON_Y + 0.004),
              (np.array([1.0, 0, 0]), LOWER_X), (np.array([-1.0, 0, 0]), LOWER_X), REAR_PLANE]
    return polytope(planes, [0, -0.2, 1.5]), planes

def inside_any(P, eps=0.0):
    return inside(P, casemate()[1], eps) | inside(P, casemate_lower()[1], eps)

def inside(P, planes, eps=0.0):
    return np.all([P @ n <= d + eps for n, d in planes], axis=0)

# gun: trunnion inside the casemate, mantlet on the front plate right of the centre line
GUN_X = 0.18                   # top-front factory photo: cap, slot, gun box and frame centred 0.17-0.19 m right of the centre line
GUN_Y = 0.22                   # trunnion; bore (+0.052) at y 0.272 (drawings: A side 0.25 / front 0.286, B side 0.27 / front 0.28;
                               # v19 0.247 from one photo)
def front_z(y): return (FRONT[1] - FRONT[0][1] * y) / FRONT[0][2]
GUN_Z_PLATE = front_z(GUN_Y)
PIVOT = np.array([GUN_X, GUN_Y, 1.38])                    # trunnion (d_gunmask); the curved shield plate turns about it (elevated side
                                                           # photos: trunnion at z 1.1-1.6; towed M-30 geometry: 1.59). v26: z 1.38
                                                           # (v19-v25 1.47), so the shield fitted on the photos (radius 0.75, see below)
                                                           # stays just behind the cheek faces at trunnion height
# v30 (user: "the gunmask alone should move when gun moves, the gunmount should stay fixed to the hull"): the cast cap is
# fixed to the hull (d_gunmount under d_hull); only the gun mask (box + shield, d_gunmask) traverses and elevates. The
# traverse axis (s_rotation) is a vertical axis TRAVERSE_DZ in front of the trunnion, near the middle of the shield's
# visible part, so the shield's edges move at most ~6 cm sideways in the slot through the +-10 deg sector: the edge going
# toward a cheek moves back as it goes and slides in under the cheek's surface (hidden inside the casting), the box clears
# the cheek faces and the frame, and the shield's top end, standing above the cheeks when the gun is raised, clears their
# tops (clip check: the traverse axis on the trunnion swept the box 5.5 cm into the cheek faces and the frame)
TRAVERSE_DZ = 0.40
TRAVERSE = PIVOT + np.array([0.0, 0.0, TRAVERSE_DZ])       # s_rotation
TRAVERSE_LIMIT = 10.0                                      # +-deg (techn_base_oprum heads: 20 deg sector, -3..+25 deg)
MUZZLE_Z = 3.93                                           # drawings A 3.79, B 3.90; right-side photo >= 4.0; documented 6.95 m overall
                                                           # from the T-34 hull rear (-2.99) -> 3.96

BORE_DY = 0.052  # M-30 bore axis above its trunnion (m30m38: d_gun 0.467, d_head 0.415)

def _loft(rings, top=None, bottom=None):
    """mesh through rings of equal point count (list of (k,3) arrays); optional centre points closing the ends"""
    k = len(rings[0]); V = np.vstack(rings); F = []
    for r in range(len(rings) - 1):
        for i in range(k):
            a, b = r * k + i, r * k + (i + 1) % k; c, d = a + k, b + k
            F += [[a, c, d], [a, d, b]]
    if top is not None:
        t = len(V); V = np.vstack([V, top]); base = (len(rings) - 1) * k
        F += [[base + i, t, base + (i + 1) % k] for i in range(k)]
    if bottom is not None:
        t = len(V); V = np.vstack([V, bottom])
        F += [[(i + 1) % k, t, i] for i in range(k)]
    return V, np.array(F)


# ---------------------------------------------------------------- gun mount (v19 photos, v20 scale drawings A and B)
# A cast cap with a flat top flush with the roof, a vertical front face and big rounded edges, 0.96-1.0 m wide; a
# vertical slot through it, 0.44 m wide, in which a curved shield and the recoil-gear box move with the gun; below the
# cap a bolted U-shaped frame round the opening in the front plate.
# v20: side views A / B: front face at z 2.08-2.11 / 2.13-2.17, rounded into the top with r ~0.24, top at roof height,
# face meets the front plate at y 0.10 / 0.14; plan views: front 2.10 / 2.18, front corners r ~0.24, the cap ends at the
# roof's front edge; front views: 0.95 / 1.0 m wide centred 0.17-0.19 right, slot 0.44 / 0.43 m (v19 cap: 0.12 m too far
# forward, 0.1 m too high, 0.93 m wide)
# v21 (user: the cap's side shape was still off): both side views traced at 8x. The face is not vertical: it leans back
# ~8.5 deg toward the top (A: z 2.127 at y 0.07 -> 2.062 at 0.49; B: 2.178 at 0.25 -> 2.131 at 0.59) and runs into the
# flat top through a rounding 0.18-0.19 m long and 0.19-0.25 m high (the top starts at z 1.86 in A, 1.95 in B). Front
# views: the outer top edges are rounded only ~0.07 m (v20 rounded them 0.14 m in).
# v33 (user: the cap's upper front in the right-side photo "is much more angled" than built): the cap's silhouette in the
# right-side factory photo a417840d (gun at 0 deg, bright wall behind it) traced and back-projected with the calibrated
# camera, and the attached SU-122 model read at its slot edges - both agree, against the drawings: the face is straight
# only up to y ~0.42; above that it is one big arc (r ~0.6) leaning further and further back, so the flat top starts at
# z 1.81-1.86, not 1.90, and the top edge is a ~0.15 fillet. Photo: z 2.089 at y 0.566, 2.017 at 0.69, 1.924 at 0.79,
# 1.81 at the top; attached model: 2.12 at 0.50, 2.035 at 0.67, 1.935 at 0.80, 1.84 at 0.82 (v21-v32: 2.094 / 2.071 /
# 2.01 / 1.906 - up to 7 cm too far forward). Its plan corners are rounder too: the outer edge 0.28 behind the front at
# |x| 0.51 and 0.087 at 0.40 (r 0.30; the drawings' 0.24 gives 0.24 / 0.053). The shield's top end stays 3 cm behind the
# new top edge at 0 deg (the lip at the band's front edge in the top-front photo) and 1-6 cm inside the cheek fronts.
CAP_HW, CAP_TOP, CAP_BOT, CAP_BACK = 0.49, ROOF + 0.01, 0.0, 1.20
CAP_FACE_Z, CAP_LEAN = 2.135, 0.15       # face at y 0.30; dz/dy of the face (the bottom further forward)
CAP_ARC_Y0, CAP_ARC_R = 0.42, 0.60       # v33: the big arc of the upper face - starts tangent to the leaning face at this
                                         # height, radius (right-side factory photo a417840d + the attached model)
CAP_TOP_R = 0.15                         # v33: fillet of the arc into the flat top (the top starts at z 1.83)
CAP_RS, CAP_RSIDE = 0.30, 0.10           # plan-view front corners (v33: 0.30, attached model; v20-v32 0.24 from the drawings);
                                         # rounding of the outer top edges (front views; v26: 0.10,
                                         # top-front photo: the cap is 8-9 cm narrower at the top than at mid-height; v21-v25 0.07)
def cap_face_z(y): return CAP_FACE_Z - CAP_LEAN * (np.asarray(y, float) - 0.30)
SLOT_HW = 0.235                     # v26: 0.47 m (top-front photo, edges of the dark gaps beside the shield; drawings 0.43-0.46)
# v22 (user: the top of the slot in drawing B and the mount under the raised box in the 3/4 factory photo): the slot runs
# right back to the roof edge, so the cap is two cheeks; the curved shield ("drum") fills it from the box up to the
# cap top (A: a rounded rectangle up to the roof; B: a drum shaded as if rounded in plan, its top a little above the cap;
# top-front photo: shield and boss up to the cap top) and, with the gun raised, shows close behind the frame (3/4 photo)
SLOT_BACK = 1.26                    # the slot is cut back to here (behind the roof edge); v26: closed over the top by the bridge
# v26 (user: "the entirety of the gun mantle is off"): the moving shield is a curved PLATE, not a solid drum. The factory
# photos with the gun raised 13-21 deg (left side 783321f8 and 5c2a9524, front-left 1e9d02f0) show its top end standing
# up above the cheeks as a thin crescent (about 5 cm thick, flat end face); the top-front photo (40807adf, gun at 5 deg)
# shows that top end as a bright lip at the front edge of a band that closes the slot over its top between the cheeks
# (the cap is one casting, see cap_bridge); the 3/4 photo shows only a dark recess under the raised box (v20-v25 bulged
# the drum to radius 0.90 low down to fill it). Fitted on the photos (crescent height above the cheeks, lip and boss
# positions): outer radius 0.75 about the trunnion (moved back to z 1.38), top end 56 deg above the bore at 0 deg - flush
# with the cheek tops (y 0.84), 8 cm above them at +12 deg and 13 cm at +26 deg. (The three photos of the raised gun put
# it 2-4 cm higher still, the top-front photo 1 cm lower: their elevations and cameras are good to about that.)
SHIELD_R, SHIELD_T = 0.75, 0.05     # outer radius about the trunnion axis, plate thickness
SHIELD_HW = 0.215                   # v26: 0.43 m - top-front photo, between the dark gaps: 135 px where the v25 0.39 m projects
                                    # to 120 px (front views of the drawings: 0.38-0.39 m in a 0.43-0.46 m slot)
SHIELD_A0, SHIELD_A1 = -80.0, 56.0  # angular range at 0 deg elevation (from the bore axis, up positive)
SHIELD_PROFILE = [(SHIELD_A0, SHIELD_R), (SHIELD_A1, SHIELD_R)]   # constant radius (v20-v25: 0.90 / 0.665 / 0.60)
SHIELD_SAG, SHIELD_FLAT = 0.0, 0.55 # square corners (v22-v25 rounded the drum's top corners in plan by 4.5 cm)
SHIELD_XS = np.array([-1, -0.5, 0, 0.5, 1]) * SHIELD_HW
# the bridge over the slot (part of the cap): a shell under the shield's inner surface, its top flush with the cheek tops;
# it reaches forward to under the shield's top end at full depression, so the slot never opens behind the shield
BRIDGE_R0, BRIDGE_R1 = 0.60, SHIELD_R - SHIELD_T - 0.005
BRIDGE_A_FRONT = SHIELD_A1 - 3.0
def shield_sag(x):
    u = np.clip((np.abs(np.asarray(x, float)) / SHIELD_HW - SHIELD_FLAT) / (1 - SHIELD_FLAT), 0, 1)
    return SHIELD_SAG * (1 - np.sqrt(1 - u * u))           # quarter-ellipse corner
def shield_r(theta_deg, x=0.0):
    """outer radius of the shield about the trunnion axis at angle theta (deg) and lateral offset x: SHIELD_PROFILE with
    smoothstep blends (no kinks)"""
    t = np.asarray(theta_deg, float); r = np.full(t.shape, SHIELD_PROFILE[0][1])
    for (t0, r0), (t1, r1) in zip(SHIELD_PROFILE[:-1], SHIELD_PROFILE[1:]):
        u = np.clip((t - t0) / (t1 - t0), 0, 1); w = u * u * (3 - 2 * u)
        r = np.where(t >= t0, r0 + (r1 - r0) * w, r)
    return r - shield_sag(x)
def _shield_dims():
    return SHIELD_R, SHIELD_R - SHIELD_T, SHIELD_A0, SHIELD_A1
# frame on the front plate below the cap: front views A / B: 0.95 / 0.88 m wide at the top, 0.68 / 0.69 m at the bottom,
# bottom edge at y -0.21 / -0.16
FRAME_TOP, FRAME_BOT, FRAME_HW_TOP, FRAME_HW_BOT, FRAME_T = 0.10, -0.235, 0.478, 0.30, 0.035   # v23: A front view
OPEN_Y0 = -0.15                     # bottom of the opening in the front plate (inside the frame; B: slot to y -0.07, A: -0.22)
_c0 = CAP_FACE_Z + 0.30 * CAP_LEAN
CAP_MEET_Y = (FRONT[1] - FRONT[0][2] * _c0) / (FRONT[0][1] - FRONT[0][2] * CAP_LEAN)   # the face comes out of the plate (0.084)
CAP_FRONT = float(cap_face_z(CAP_MEET_Y))   # foremost point of the cap (bottom of the face, 2.167)
SLOT_TOP_Y = CAP_MEET_Y + 0.03      # top of the opening in the plate, just inside the cap
# v23: the cap (it traverses with the gun) stops at the top of the fixed opening in the plate, so its cheeks never show
# through the opening when the gun is traversed (v22: with the gun at -8 deg, as in the 3/4 factory photo, the part of the
# right cheek below the plate surface showed in the opening). The cheeks now end 3 cm above where their faces would meet
# the plate, on the ends of the frame bars - the 3/4 photo shows a ledge there. (v30: the cap is fixed; the ledge stays.)
CAP_BOT = SLOT_TOP_Y
ROOF_EDGE_Z = front_z(ROOF)         # front edge of the roof (1.23)
def _cap_arc():
    """centre (y, z) of the big arc, its radius, the fillet centre (y, z) and radius, and the tangent point of the two"""
    L = CAP_LEAN; n = np.array([L, 1.0]) / np.sqrt(1 + L * L)                 # outward normal of the leaning face (y, z)
    T = np.array([CAP_ARC_Y0, float(cap_face_z(CAP_ARC_Y0))]); C = T - CAP_ARC_R * n
    fy = CAP_TOP - CAP_TOP_R; fz = C[1] + np.sqrt((CAP_ARC_R - CAP_TOP_R) ** 2 - (fy - C[0]) ** 2)
    Fc = np.array([fy, fz]); J = C + (Fc - C) * CAP_ARC_R / (CAP_ARC_R - CAP_TOP_R)
    return C, CAP_ARC_R, Fc, CAP_TOP_R, J
_CAP_C, _, _CAP_FC, _, _CAP_J = _cap_arc()
_CAP_YT = CAP_ARC_Y0                # where the face stops being straight (0.42)
CAP_TOP_FRONT = float(_CAP_FC[1])   # front edge of the flat top (1.83; v21-v32: 1.906)

def cap_front_z(y):
    """z of the cap's front profile at height y: the leaning face, then the big arc, then the fillet into the flat top
    (v33; v21-v32: face + an elliptical rounding 0.185 long and 0.235 high)"""
    if y <= _CAP_YT: return float(cap_face_z(y))
    if y <= _CAP_J[0]: return float(_CAP_C[1] + np.sqrt(max(CAP_ARC_R ** 2 - (y - _CAP_C[0]) ** 2, 0.0)))
    return float(_CAP_FC[1] + np.sqrt(max(CAP_TOP_R ** 2 - (min(y, CAP_TOP) - _CAP_FC[0]) ** 2, 0.0)))

def cap_profile(n=9):
    """(z, y) points of the front profile from the face's foot on the plate up to the start of the flat top"""
    pts = [(CAP_FRONT, CAP_MEET_Y), (float(cap_face_z(_CAP_YT)), _CAP_YT)]
    a0 = np.arcsin((_CAP_YT - _CAP_C[0]) / CAP_ARC_R); a1 = np.arcsin((_CAP_J[0] - _CAP_C[0]) / CAP_ARC_R)
    for a in np.linspace(a0, a1, n)[1:]:
        pts.append((float(_CAP_C[1] + CAP_ARC_R * np.cos(a)), float(_CAP_C[0] + CAP_ARC_R * np.sin(a))))
    b0 = np.arcsin((_CAP_J[0] - _CAP_FC[0]) / CAP_TOP_R)
    for b in np.linspace(b0, np.pi / 2, 4)[1:]:
        pts.append((float(_CAP_FC[1] + CAP_TOP_R * np.cos(b)), float(_CAP_FC[0] + CAP_TOP_R * np.sin(b))))
    return pts

def _cap_side_inset(y):
    t = y - (CAP_TOP - CAP_RSIDE)
    return 0.0 if t <= 0 else CAP_RSIDE - np.sqrt(max(CAP_RSIDE ** 2 - t ** 2, 0.0))

def _rrect(x0, x1, z0, z1, r, n=6):
    """plan outline (x, z) of a rectangle with rounded FRONT corners (z1 side), counter-clockwise seen from above"""
    r = max(min(r, (x1 - x0) / 2 - 1e-4, z1 - z0 - 1e-4), 1e-4); pts = [(x0, z0), (x1, z0)]
    for a in np.linspace(0, np.pi / 2, n): pts.append((x1 - r + r * np.cos(a), z1 - r + r * np.sin(a)))
    for a in np.linspace(np.pi / 2, np.pi, n): pts.append((x0 + r + r * np.cos(a), z1 - r + r * np.sin(a)))
    return np.array(pts)

def cap():
    """the cast cap (d_gunmount, fixed to the hull - v19-v29 it traversed with the gun), slot cut out, parts inside the
    casemate removed"""
    ys = [CAP_BOT] + [y for z, y in cap_profile(9)[1:]] + list(CAP_TOP - CAP_RSIDE + CAP_RSIDE * np.sin(np.linspace(0, np.pi / 2, 5))[1:])
    ys = sorted(set(np.round(ys, 5)))
    rings = []
    for y in ys:
        hw = CAP_HW - _cap_side_inset(y); zf = cap_front_z(y)
        o = _rrect(GUN_X - hw, GUN_X + hw, CAP_BACK, zf, max(min(CAP_RS, zf - CAP_BACK - 0.05), 0.03))
        rings.append(np.c_[o[:, 0], np.full(len(o), y), o[:, 1]])
    V, F = _loft(rings, top=[[GUN_X, CAP_TOP, (CAP_BACK + CAP_FRONT) / 2]], bottom=[[GUN_X, CAP_BOT, (CAP_BACK + CAP_FRONT) / 2]])
    n = geom.normals(V, F); c = V[F].mean(1); ctr = np.array([GUN_X, (CAP_BOT + CAP_TOP) / 2, (CAP_BACK + CAP_FRONT) / 2])
    flip = np.sum(n * (c - ctr), 1) < 0; F[flip] = F[flip][:, [0, 2, 1]]
    behind = [(FRONT[0], FRONT[1] - 0.15)]                                   # region deeper than 0.15 m behind the front plate
    A, F = geom.subtract_convex(V, F, behind)
    A, F = geom.subtract_convex(A, F, [(np.array([0, 0, 1.0]), ROOF_EDGE_Z - 0.01)])   # v20: the cap ends at the roof's front edge
    A, F = geom.subtract_convex(A, F, slot_cap_planes())
    used = np.unique(F); remap = np.full(len(A), -1); remap[used] = np.arange(len(used))
    return A[used], remap[F]

def slot_cap_planes():
    return [(np.array([1.0, 0, 0]), GUN_X + SLOT_HW), (np.array([-1.0, 0, 0]), -(GUN_X - SLOT_HW)), (np.array([0, 0, -1.0]), -SLOT_BACK)]

def slot_planes():
    """the opening in the front plate below the cap (inside the frame)"""
    return [(np.array([1.0, 0, 0]), GUN_X + SLOT_HW), (np.array([-1.0, 0, 0]), -(GUN_X - SLOT_HW)),
            (np.array([0, 1.0, 0]), SLOT_TOP_Y), (np.array([0, -1.0, 0]), -OPEN_Y0)]

def _fan(poly, want_n):
    poly = np.asarray(poly, float); b = 0; F = []
    for k in range(1, len(poly) - 1):
        f = [0, k, k + 1]
        if np.cross(poly[k] - poly[0], poly[k + 1] - poly[0]) @ want_n < 0: f = [0, k + 1, k]
        F.append(f)
    return poly, np.array(F)

def cap_slot_walls():
    """inner side walls of the two cap cheeks (part of the cap, fixed since v30; the shield's edges slide in through them
    when the gun traverses): from the plate line up the front profile to the flat top and back to where the plate meets
    the top"""
    parts = []
    z_top = (FRONT[1] - FRONT[0][1] * CAP_TOP) / FRONT[0][2]           # the front plate reaches the cap-top level here
    prof = [(z_top, CAP_TOP), (front_z(CAP_BOT), CAP_BOT), (float(cap_face_z(CAP_BOT)), CAP_BOT)] + cap_profile(9)[1:]
    for sx in (-1, 1):
        x = GUN_X + sx * SLOT_HW
        parts.append(_fan([(x, y, z) for z, y in prof], [-sx, 0, 0]))
    return merge(*parts)

def cap_bridge(n=24):
    """v26: the cap's top over the slot, between the cheeks and flush with their tops (top-front photo: one band across the
    whole cap from the roof edge to the shield's top end). A shell between BRIDGE_R0 and BRIDGE_R1 about the trunnion axis,
    cut flat at the cap top, from BRIDGE_A_FRONT back into the casemate; the shield plate slides over it when the gun is
    raised. Hull coordinates; the parts behind the front plate and the roof edge are cut off like the cap's."""
    yc = CAP_TOP - GUN_Y; th = np.radians(np.linspace(BRIDGE_A_FRONT, 135.0, n))
    ro = np.minimum(BRIDGE_R1, yc / np.sin(th))                        # outer boundary: arc in front, then the flat top
    out = np.c_[ro * np.sin(th), ro * np.cos(th)]; inn = np.c_[BRIDGE_R0 * np.sin(th), BRIDGE_R0 * np.cos(th)]
    V = []
    for x in (GUN_X - SLOT_HW, GUN_X + SLOT_HW):
        for ring in (out, inn):
            V.append(np.c_[np.full(n, x), GUN_Y + ring[:, 0], PIVOT[2] + ring[:, 1]])
    V = np.vstack(V); F = []
    o0, i0, o1, i1 = 0, n, 2 * n, 3 * n                                 # outer / inner rows at x0 and x1
    for k in range(n - 1):
        for a, b in ((o0, o1), (i0, i1), (o0, i0), (o1, i1)):           # outer, inner, side x0, side x1
            F += [[a + k, b + k, b + k + 1], [a + k, b + k + 1, a + k + 1]]
    for k in (0, n - 1):                                                 # front and back ends
        F += [[o0 + k, i0 + k, i1 + k], [o0 + k, i1 + k, o1 + k]]
    V, F = np.array(V), np.array(F)
    n_ = geom.normals(V, F); c = V[F].mean(1)
    for t in range(len(F)):                                              # orient every face outward
        p = c[t] - [GUN_X, GUN_Y, PIVOT[2]]; rad = np.r_[0, p[1:]] / np.hypot(p[1], p[2])
        a = np.arctan2(p[1], p[2]); tang = np.array([0, np.cos(a), -np.sin(a)])   # direction of increasing angle
        if t < 8 * (n - 1):
            kind = (t % 8) // 2                                          # 0 outer, 1 inner, 2 side x0, 3 side x1
            w = [rad, -rad, np.array([-1.0, 0, 0]), np.array([1.0, 0, 0])][kind]
        else:
            w = -tang if t < 8 * (n - 1) + 2 else tang                   # front end (smallest angle), back end
        if n_[t] @ w < 0: F[t] = F[t][[0, 2, 1]]
    A, F = geom.subtract_convex(V, F, [(FRONT[0], FRONT[1] - 0.15)])
    A, F = geom.subtract_convex(A, F, [(np.array([0, 0, 1.0]), ROOF_EDGE_Z - 0.01)])
    used = np.unique(F); remap = np.full(len(A), -1); remap[used] = np.arange(len(used))
    return A[used], remap[F]

def slot_pocket():
    """recess behind the opening in the front plate (fixed, faces point into the opening)"""
    parts = []
    # recess behind the plate opening: side walls, bottom, back (parallel to the plate). v20: 0.60 m deep, so the curved
    # shield (r 0.61 about the trunnion) is always in front of the back wall and shows through the opening when the gun is
    # raised, instead of a black hole
    dep = 0.60; zs = lambda y: front_z(y)
    for sx in (-1, 1):
        x = GUN_X + sx * SLOT_HW
        parts.append(_fan([(x, OPEN_Y0, zs(OPEN_Y0) + 0.01), (x, SLOT_TOP_Y, zs(SLOT_TOP_Y) + 0.01), (x, SLOT_TOP_Y, zs(SLOT_TOP_Y) - dep), (x, OPEN_Y0, zs(OPEN_Y0) - dep)], [-sx, 0, 0]))
    x0, x1 = GUN_X - SLOT_HW, GUN_X + SLOT_HW
    parts.append(_fan([(x0, OPEN_Y0, zs(OPEN_Y0) + 0.01), (x1, OPEN_Y0, zs(OPEN_Y0) + 0.01), (x1, OPEN_Y0, zs(OPEN_Y0) - dep), (x0, OPEN_Y0, zs(OPEN_Y0) - dep)], [0, 1, 0]))
    parts.append(_fan([(x0, OPEN_Y0, zs(OPEN_Y0) - dep), (x1, OPEN_Y0, zs(OPEN_Y0) - dep), (x1, SLOT_TOP_Y, zs(SLOT_TOP_Y) - dep), (x0, SLOT_TOP_Y, zs(SLOT_TOP_Y) - dep)], list(FRONT[0])))
    return merge(*parts)

def shield(coarse=False):
    """the curved shield moving with the gun in the slot (d_gunmask frame, origin on the trunnion axis): a surface of
    revolution about the trunnion axis for every x (so it slides through the slot at any elevation); v26 a plate of
    constant radius SHIELD_R and thickness SHIELD_T (v20-v25 a solid drum). coarse: for the far LOD and the hit mesh"""
    n_th = 13 if coarse else 49
    th = np.unique(np.r_[np.linspace(SHIELD_A0, SHIELD_A1, n_th), [p[0] for p in SHIELD_PROFILE]])
    xs = np.array([-1, -0.85, 0, 0.85, 1]) * SHIELD_HW if coarse else SHIELD_XS
    nt, nx = len(th), len(xs); a = np.radians(th)
    def surf(inner):
        P = []
        for i in range(nt):
            for j in range(nx):
                r = shield_r(th[i], xs[j]) - (SHIELD_T if inner else 0.0)
                P.append((xs[j], r * np.sin(a[i]), r * np.cos(a[i])))
        return np.array(P)
    Vo, Vi = surf(False), surf(True); V = np.vstack([Vo, Vi]); off = len(Vo); F = []
    idx = lambda i, j: i * nx + j
    for i in range(nt - 1):
        for j in range(nx - 1):
            p, q, r_, t_ = idx(i, j), idx(i, j + 1), idx(i + 1, j + 1), idx(i + 1, j)
            F += [[p, t_, r_], [p, r_, q]]                                  # outer
            F += [[off + p, off + q, off + r_], [off + p, off + r_, off + t_]]   # inner
    for i in range(nt - 1):                                                  # side faces x = -hw (j 0) and +hw (j nx-1)
        for j, sgn in ((0, -1), (nx - 1, 1)):
            p, t_ = idx(i, j), idx(i + 1, j)
            F += [[p, off + p, off + t_], [p, off + t_, t_]] if sgn < 0 else [[p, t_, off + t_], [p, off + t_, off + p]]
    for i, sgn in ((0, -1), (nt - 1, 1)):                                    # end faces
        for j in range(nx - 1):
            p, q = idx(i, j), idx(i, j + 1)
            F += [[p, q, off + q], [p, off + q, off + p]] if sgn < 0 else [[p, off + p, off + q], [p, off + q, q]]
    F = np.array(F)
    # orient every face outward: radial for the curved faces, +-x for the sides, tangential for the ends
    n = geom.normals(V, F); c = V[F].mean(1)
    for t in range(len(F)):
        f = F[t]; ins = [v >= off for v in f]
        if all(ins) or not any(ins):                                         # outer / inner surface
            w = np.r_[0, c[t, 1:]] * (-1 if all(ins) else 1)
        else:
            vv = V[f]
            if np.allclose(np.abs(vv[:, 0]), SHIELD_HW, atol=1e-9): w = np.array([np.sign(vv[0, 0]), 0, 0])
            else:
                ang = np.degrees(np.arctan2(c[t, 1], c[t, 2])); mid = (SHIELD_A0 + SHIELD_A1) / 2
                tang = np.array([0, np.cos(np.radians(ang)), -np.sin(np.radians(ang))])   # direction of increasing angle
                w = tang if ang > mid else -tang
        if n[t] @ w < 0: F[t] = F[t][[0, 2, 1]]
    return V, F

def shield_details():
    """round boss on the shield above the gun box (top-front photo), and the weld seam where the gun box joins the shield
    (v24, user: the box and the shield are one assembly joined by a seam), d_gunmask frame. v24: the lifting eyes on the
    shield's top and on the box's top were removed (user). v26: the boss at 37 deg on the new plate and 3.5 cm right of
    the gun axis (top-front photo: its centre 11 px right of the midpoint of the two chamfer bolts)"""
    a = np.radians(BOSS_ANGLE); d = np.array([0, np.sin(a), np.cos(a)]); R = float(shield_r(BOSS_ANGLE, 0.0))
    return [revolve([(-0.01, 0.065), (0.035, 0.065), (0.05, 0.045), (0.055, 0.0)], d * R + [BOSS_DX, 0, 0], d, seg=16),
            box_shield_seam()]
BOSS_ANGLE, BOSS_DX = 37.0, 0.035

def tube(points, r, seg=6, closed=True, normal=None):
    """a round bead of radius r along a polyline (closed loop by default), faces pointing outward. normal: for a polyline
    lying in a plane, that plane's normal - used for the cross-section frame (v29: no frame flips on bent open bars)"""
    P = np.asarray(points, float); n = len(P); V = []; F = []; axis = []
    ctr = P.mean(0)
    for i in range(n):
        t = (P[(i + 1) % n] - P[i - 1]) if closed else (P[min(i + 1, n - 1)] - P[max(i - 1, 0)])
        t /= np.linalg.norm(t) + 1e-12
        if normal is not None:
            a = np.asarray(normal, float) - t * (np.asarray(normal, float) @ t)
        elif closed:    # v25: frame from the loop's centre outward - no flips (the fixed up axis twisted the seam bead
            a = (P[i] - ctr) - t * ((P[i] - ctr) @ t)   # where it ran down the sides of the gun box)
        else:
            a = np.cross(t, [0, 1.0, 0] if abs(t[1]) < 0.9 else [1.0, 0, 0])
        a /= np.linalg.norm(a) + 1e-12; b = np.cross(t, a)
        for k in range(seg):
            ang = 2 * np.pi * k / seg; V.append(P[i] + r * (np.cos(ang) * a + np.sin(ang) * b))
    for i in range(n if closed else n - 1):
        j = (i + 1) % n
        for k in range(seg):
            p0, p1 = i * seg + k, i * seg + (k + 1) % seg; q0, q1 = j * seg + k, j * seg + (k + 1) % seg
            F += [[p0, q0, q1], [p0, q1, p1]]; axis += [(P[i] + P[j]) / 2] * 2
    V = np.array(V); F = np.array(F); axis = np.array(axis)
    if not closed:                                     # end caps
        caps = []
        for i in (0, n - 1):
            c = len(V); V = np.vstack([V, P[i]]); base = i * seg
            for k in range(seg): caps.append([c, base + k, base + (k + 1) % seg]); axis = np.vstack([axis, 2 * P[i] - (P[1] if i == 0 else P[n - 2])])
        F = np.vstack([F, caps])
    nrm = geom.normals(V, F); flip = np.sum(nrm * (V[F].mean(1) - axis), 1) < 0; F[flip] = F[flip][:, [0, 2, 1]]
    return V, F

def box_shield_seam(r=0.011):
    """the weld seam round the gun box where it comes out of the shield: the box body's section outline carried back along
    the box until it meets the shield's outer surface (d_gunmask frame)"""
    pts = []
    sec = _coffin(18, BOX_LIP)
    loop = [(hw, y) for y, hw in sec] + [(-hw, y) for y, hw in sec[::-1]]
    for x, yb in loop:
        y = yb + BORE_Y - PIVOT[1]; z = 0.7
        for _ in range(30):                             # z on the shield: |(y, z)| = shield_r(atan2(y, z), x)
            th = np.degrees(np.arctan2(y, z)); R = float(shield_r(th, x)); z = np.sqrt(max(R * R - y * y, 1e-6))
        pts.append((x, y, z + r * 0.3))
    return tube(pts, r, seg=5, closed=True)

# v21 (user: the shape of the gun-box face was still off): both front views traced at 10x. The box's cross-section is a
# "coffin": a flat narrow top (A 0.15 m, B 0.25 m), sides widening to 0.32 m at the bore, a rounded bottom 0.28 m
# under the bore (half-widths about the gun axis, A / B: +0.20 0.119 / 0.131, +0.10 0.143 / 0.14, 0 0.160 / 0.153,
# -0.10 0.149 / 0.149, -0.15 0.136 / 0.130, -0.20 0.105 / 0.095, -0.24 0.070 / 0.057). v20 was a hexagon widest near
# the top and flat underneath. Side views (unchanged): top 0.29 above the bore, bottom 0.28 below it, long chamfer from
# z 2.91 down to just under the bore at z 3.13, vertical face below; it comes out of the cap face at z 2.08-2.19.
# v25: the sides have a sharp lengthwise edge at the widest point, level with the foot of the chamfer: all three side
# factory photos (left 5c2a9524 and 783321f8, right a417840d) show the box's side split along its length into a light
# upper band (the upper side leans out ~8 deg, facing the sky) and a dark lower band (the lower side turns under), with
# a crisp line between them at the height where the chamfer meets the vertical face. v21-v24 rounded the section through
# that point (one smooth curve, smooth normals), so the box read as a tube. The drawn half-widths are kept to 6 mm.
# v26: the top's corners rounded (top-front photo: the box top ends in a round-cornered arch where it meets the shield;
# v21-v25 had a 1.8 cm 45-degree chamfer). v27: radius 5 cm (3.5), flat top 0.12 m wide (drawing A 0.15)
BOX_COFFIN = [(0.29, 0.061), (0.287, 0.078), (0.278, 0.093), (0.265, 0.104), (0.254, 0.109), (0.20, 0.125), (0.10, 0.1395),
              (-0.04, 0.159), (-0.10, 0.148), (-0.15, 0.133), (-0.20, 0.104), (-0.24, 0.066), (-0.265, 0.035), (-0.2765, 0.015),
              (-0.278, 0.0)]   # (y about the bore, half-width); v27: the bottom closes smoothly on the centre line
BOX_CREASE_I = 7                        # index of the side edge in BOX_COFFIN (straight upper side above, rounded below)
BOX_SMOOTH = 12.0                       # normal smoothing angle for the box: the side edge (15-18 deg) and the top edges stay sharp
BOX_Z_CHAMFER, BOX_Z_FACE = 2.91, 3.13  # world z at 0 deg (BOX_Z_REAR: below, from the shield)
BOX_FACE_TOP = -0.04                    # the chamfer ends just under the bore; vertical face below
# v25 (user, two crops of the v24 gun-limits picture): the box was tapered (0.9 wide, 0.75 high) over its last 0.17 m
# (z 1.95-2.12) - left over from v21, when it went into the closed cap. Since v22 it comes out of the shield at z
# 1.97-2.13, inside that taper, so it narrowed just before the shield and v24's weld seam (drawn on the full section)
# floated up to 6 cm off it, like a handle over the box top. Now a straight prism: full section back to z 1.92, which
# is inside the shield's solid for the whole section (4 cm under its outer surface, 4 cm above its inner one), so the
# box meets the shield along one clean line and the seam sits on that line.
BOX_TOP = BOX_COFFIN[0][0]
BORE_Y = GUN_Y + BORE_DY
# v26: with the thin shield plate the box ends inside the plate: its top-rear edge in the middle of the plate thickness, the
# rest of the rear face behind the plate's inner surface (hidden); so nothing of it reaches the bridge over the slot at
# +26 deg. Its visible part now starts 5-7 cm further forward (top-front photo: the box top meets the shield there)
BOX_Z_REAR = PIVOT[2] + float(np.sqrt((SHIELD_R - SHIELD_T / 2) ** 2 - (BORE_DY + BOX_TOP) ** 2))
# v23 (user: the lower part of the box in the 3/4 factory photo) gave the front of the box a raised rim, 1.2 cm proud and
# 4 cm deep. v27 (user: that part "sticks out too much compared to the gunmask", and "the angle ... should be eased"): no
# rim. The narrow band along the front edge in the photos is a rounded edge - the 3/4 photos show only a thin highlight
# line along it, the side photos a ~4 cm band along the front outline. The front's edges are rounded all round
# (BOX_R_EDGE) and the two angles of its side profile are eased: the top runs into the slope through BOX_R_TOP, the slope
# into the vertical face through BOX_R_FACE (the right-side photo a417840d shows the front as one smooth convex curve).
BOX_LIP, BOX_LIP_D = 0.0, 0.0                       # v23-v26 rim (kept at zero for older callers)
BOX_R_EDGE, BOX_R_TOP, BOX_R_FACE = 0.03, 0.05, 0.12    # BOX_R_EDGE: the front-left and 3/4 photos show a crisp edge with a narrow
                                                         # highlight (1-2 cm), the side photos a ~4 cm band; 4.5 cm read too soft
BOX_BOT = BOX_COFFIN[-1][0]

def _box_side_x(y, body=False):
    """half-width of the box at height y about the bore"""
    ys = [p[0] for p in BOX_COFFIN][::-1]; hs = [p[1] for p in BOX_COFFIN][::-1]
    return float(np.interp(y, ys, hs))

def _chamfer_z(y):
    """the straight part of the slope (before easing)"""
    return BOX_Z_CHAMFER + (BOX_Z_FACE - BOX_Z_CHAMFER) * (BOX_TOP - y) / (BOX_TOP - BOX_FACE_TOP)

def _box_front_z(y):
    return BOX_Z_FACE if y <= BOX_FACE_TOP else _chamfer_z(y)

def _coffin(n=28, inset=0.0):
    """the box section (y about the bore, half-width), top first: monotone cubics through BOX_COFFIN above and below the
    side edge (v25: kept sharp - the point BOX_CREASE_I is in the output exactly once), points spread by arc length so
    the rounded bottom gets enough of them; shrunk by `inset` all round"""
    from scipy.interpolate import PchipInterpolator
    P = np.array(BOX_COFFIN, float)
    def arc(Q): return float(np.sum(np.hypot(np.diff(Q[:, 0]), np.diff(Q[:, 1]))))
    def resample(Q, m):
        t = np.r_[0, np.cumsum(np.hypot(np.diff(Q[:, 0]), np.diff(Q[:, 1])))]; t /= t[-1]
        tt = np.linspace(0, 1, m)
        return np.c_[PchipInterpolator(t, Q[:, 0])(tt), PchipInterpolator(t, Q[:, 1])(tt)]
    up, lo = P[:BOX_CREASE_I + 1], P[BOX_CREASE_I:]
    nu = max(3, int(round(n * arc(up) / (arc(up) + arc(lo))))); nl = max(3, n - nu + 1)
    S = np.vstack([resample(up, nu), resample(lo, nl)[1:]])
    # inset: move the top down / bottom up and the sides in (approximately along the normal)
    Y = np.clip(S[:, 0], P[-1, 0] + inset, P[0, 0] - inset); Hh = np.maximum(S[:, 1] - inset, 0.004)
    return list(zip(Y, Hh))

def box_profile(n_top=8, n_face=12, n_slope=3, n_face_lin=4):
    """v27: the front of the box in the side view: points (z world at 0 deg, y about the bore) with outward unit normals
    (n_z, n_y), from where the top starts to round over, down to the bottom of the face. Sharp outline: top line, the slope
    from (BOX_Z_CHAMFER, BOX_TOP) to (BOX_Z_FACE, BOX_FACE_TOP), vertical face; both angles eased by circular arcs."""
    A = np.array([BOX_Z_CHAMFER, BOX_TOP]); B = np.array([BOX_Z_FACE, BOX_FACE_TOP]); E = np.array([BOX_Z_FACE, BOX_BOT])
    d0 = np.array([1.0, 0.0]); d1 = (B - A) / np.linalg.norm(B - A); d2 = np.array([0.0, -1.0])
    out_n = lambda d: np.array([-d[1], d[0]])            # travelling top -> bottom the solid is on the right
    def arc(P, da, db, r, n):
        t = r * np.tan(np.arccos(np.clip(da @ db, -1, 1)) / 2); c = P - da * t - r * out_n(da)
        a = np.linspace(np.arctan2(out_n(da)[1], out_n(da)[0]), np.arctan2(out_n(db)[1], out_n(db)[0]), n)
        N = np.c_[np.cos(a), np.sin(a)]; return c + r * N, N
    pa, na = arc(A, d0, d1, BOX_R_TOP, n_top); pb, nb = arc(B, d1, d2, BOX_R_FACE, n_face)
    s = np.linspace(0, 1, n_slope + 2)[1:-1][:, None]; ps = pa[-1] + (pb[0] - pa[-1]) * s
    f = np.linspace(0, 1, n_face_lin + 1)[1:][:, None]; pf = pb[-1] + (E - pb[-1]) * f
    P = np.vstack([pa, ps, pb, pf])
    N = np.vstack([na, np.tile(out_n(d1), (len(ps), 1)), nb, np.tile(out_n(d2), (len(pf), 1))])
    return P, N

def box_front_point(y):
    """z (world, 0 deg) and outward normal (x, y, z) of the box's front surface at height y about the bore"""
    P, N = box_profile(60, 90, 30, 30)
    z = float(np.interp(y, P[::-1, 1], P[::-1, 0]))
    n = np.array([0.0, np.interp(y, P[::-1, 1], N[::-1, 1]), np.interp(y, P[::-1, 1], N[::-1, 0])])
    return z, n / np.linalg.norm(n)

def _section_half(n=240):
    """right half of the box section outline: points (x, y about the bore) from the top centre round the side to the bottom
    centre, with outward unit normals (at the side edge the mean of its two faces' normals)"""
    from scipy.interpolate import PchipInterpolator
    C = np.array([(hw, y) for y, hw in BOX_COFFIN])
    def fit(Q, m):                                       # monotone cubic through Q, parametrised by arc length
        t = np.r_[0, np.cumsum(np.hypot(np.diff(Q[:, 0]), np.diff(Q[:, 1])))]; tt = np.linspace(0, t[-1], m)
        return np.c_[PchipInterpolator(t, Q[:, 0])(tt), PchipInterpolator(t, Q[:, 1])(tt)]
    up = C[:BOX_CREASE_I + 1]; lo = C[BOX_CREASE_I:]
    lo2 = np.vstack([lo, (lo * [-1, 1])[::-1][1:]])     # through the bottom to the left side: smooth at the centre line
    nu = max(4, n * len(up) // len(C)); P_up = fit(up, nu); P_lo = fit(lo2, 2 * (n - nu) + 1)[:n - nu + 1]
    P = np.vstack([[(0.0, BOX_TOP)], P_up, P_lo[1:], [(0.0, BOX_BOT)]])
    d = np.diff(P, axis=0); P = P[np.r_[True, np.hypot(d[:, 0], d[:, 1]) > 1e-9]]
    e = np.diff(P, axis=0); e /= np.linalg.norm(e, axis=1, keepdims=True); en = np.c_[-e[:, 1], e[:, 0]]
    M = np.zeros_like(P); M[0] = en[0]; M[-1] = en[-1]; M[1:-1] = en[:-1] + en[1:]
    return P, M / np.linalg.norm(M, axis=1, keepdims=True)

def _slerp(a, b, t):
    w = np.arccos(np.clip(a @ b, -1.0, 1.0))
    if w < 1e-6: return a.copy()
    return (np.sin((1 - t) * w) * a + np.sin(t * w) * b) / np.sin(w)

def mantlet(coarse=False):
    """the recoil-gear box (moves with the gun), in the d_gunmask frame (origin at the trunnion, bore along +z at BORE_DY).
    v27: a prism of the coffin section from inside the shield plate to the front, which follows box_profile; the front's
    edges rounded with BOX_R_EDGE - built as the exact offset of the box shrunk by BOX_R_EDGE: the side surface, a rounded
    strip along the front edge, the front surface (v23-v26: three convex pieces with a proud rim). coarse: far LOD / hit mesh"""
    re = BOX_R_EDGE; b = BORE_Y - PIVOT[1]; pz = PIVOT[2]
    K, J = (1, 2) if coarse else (2, 9)                                  # front rows are straight across; strip steps 10 deg (< BOX_SMOOTH)
    Cp, Cn = box_profile(3, 3, 1, 2) if coarse else box_profile(8, 12, 3, 4)
    Ci = Cp - re * Cn                                                   # profile of the shrunk box, (z, y)
    Pf, Mf = _section_half(240); Qf = Pf - re * Mf                      # section outline, and of the shrunk box
    Qf[:, 1] = np.minimum.accumulate(Qf[:, 1])                          # (removes the mm-size folds at tight spots)
    q_top, q_bot = Qf[0, 1], Qf[-1, 1]
    Ps, Ms = _section_half(14 if coarse else 30); Qs = Ps - re * Ms
    cand = np.sort(np.r_[Ci[:, 1], Qs[:, 1], q_top, q_bot])[::-1]
    rows = []
    for y in cand:                                                      # rows of the front: profile samples and section corners
        if y > q_top + 1e-9 or y < q_bot - 1e-9: continue
        if not rows or rows[-1] - y > 0.002: rows.append(float(y))
    if rows[-1] - q_bot > 1e-6: rows.append(float(q_bot))
    rows = np.array(rows); rows[0] = q_top
    def right_end(y):                                                   # the shrunk outline's point at height y (right side)
        i = int(np.nonzero(Qf[:, 1] >= y - 1e-9)[0][-1])
        if i >= len(Qf) - 1: return Qf[-1], Pf[-1], Mf[-1]
        dy = Qf[i, 1] - Qf[i + 1, 1]; t = 0.0 if dy <= 1e-12 else (Qf[i, 1] - y) / dy
        M = Mf[i] + t * (Mf[i + 1] - Mf[i])
        return Qf[i] + t * (Qf[i + 1] - Qf[i]), Pf[i] + t * (Pf[i + 1] - Pf[i]), M / np.linalg.norm(M)
    yi = Ci[::-1, 1]
    zin = np.interp(rows, yi, Ci[::-1, 0]); cz = np.interp(rows, yi, Cp[::-1, 0]); cy = np.interp(rows, yi, Cp[::-1, 1])
    nu = np.c_[np.interp(rows, yi, Cn[::-1, 0]), np.interp(rows, yi, Cn[::-1, 1])]; nu /= np.linalg.norm(nu, axis=1, keepdims=True)
    R = len(rows); ends = [right_end(y) for y in rows]
    # loop of section samples: top row (left -> right), down the right side, up the left side
    loop = [((x, BOX_TOP), (0.0, 1.0), (x, rows[0]), 0) for x in np.linspace(-ends[0][0][0], ends[0][0][0], K + 1)]
    loop += [((P[0], P[1]), (M[0], M[1]), (Q[0], rows[r]), r) for r, (Q, P, M) in enumerate(ends) if r > 0]
    loop += [((-P[0], P[1]), (-M[0], M[1]), (-Q[0], rows[r]), r) for r, (Q, P, M) in reversed(list(enumerate(ends))) if r > 0]
    V = []; vid = {}
    def add(p):
        V.append((p[0], p[1] + b, p[2] - pz)); return len(V) - 1
    rear, strip = [], []
    for (P2, M2, Q2, r) in loop:
        rear.append(add((P2[0], P2[1], BOX_Z_REAR)))
        E = np.array([Q2[0], Q2[1], zin[r]]); ns = np.array([M2[0], M2[1], 0.0]); nf = np.array([0.0, nu[r, 1], nu[r, 0]])
        strip.append([add(E + re * _slerp(ns, nf, j / J)) for j in range(J + 1)])
    F = []
    L = len(loop)
    for u in range(L):
        w = (u + 1) % L
        F += [[rear[u], rear[w], strip[w][0]], [rear[u], strip[w][0], strip[u][0]]]          # side surface
        for j in range(J):
            F += [[strip[u][j], strip[w][j], strip[w][j + 1]], [strip[u][j], strip[w][j + 1], strip[u][j + 1]]]
    # front surface: rows of K + 1 points; the row ends are the strips' outer ends
    right_u = {loop[u][3]: u for u in range(K + 1, K + R)}
    left_u = {loop[u][3]: u for u in range(K + R, L)}
    grid = [[strip[u][J] for u in range(K + 1)]]
    for r in range(1, R):
        a, c = strip[left_u[r]][J], strip[right_u[r]][J]
        xa, xc = V[a][0], V[c][0]
        grid.append([a] + [add((x, cy[r], cz[r])) for x in np.linspace(xa, xc, K + 1)[1:-1]] + [c])
    for r in range(R - 1):
        for k in range(K):
            F += [[grid[r][k], grid[r][k + 1], grid[r + 1][k + 1]], [grid[r][k], grid[r + 1][k + 1], grid[r + 1][k]]]
    ctr = add((0.0, 0.5 * (BOX_TOP + BOX_BOT), BOX_Z_REAR))               # rear end (inside the shield plate)
    F += [[ctr, rear[(u + 1) % L], rear[u]] for u in range(L)]
    V = np.array(V); F = np.array(F)
    from scipy.spatial import cKDTree                                    # merge coincident / nearly coincident (< 1.5 mm) points
    weld = np.arange(len(V))
    for i, j in sorted(cKDTree(V).query_pairs(0.0015)):
        a, c = weld[i], weld[j]
        while weld[a] != a: a = weld[a]
        while weld[c] != c: c = weld[c]
        if a != c: weld[max(a, c)] = min(a, c)
    for i in range(len(weld)):
        while weld[weld[i]] != weld[i]: weld[i] = weld[weld[i]]
    F = weld[F]
    F = F[(F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 0] != F[:, 2])]                                  # (degenerate strips)
    T = V[F]; area = np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1); F = F[area > 1e-10]
    n = geom.normals(V, F); c = V[F].mean(1); mid = V.mean(0)
    flip = np.sum(n * (c - mid), 1) < 0; F[flip] = F[flip][:, [0, 2, 1]]
    used = np.unique(F); remap = np.full(len(V), -1); remap[used] = np.arange(len(used))
    return V[used], remap[F]

def gun_box_details():
    """bolt heads on the box sides, slope and face, a loop handle on its right side (drawings A / B, factory photos),
    d_gunmask frame. v27: the front bolts sit on the eased front surface (box_front_point)"""
    b = BORE_Y - PIVOT[1]; pz = PIVOT[2]
    out = []                                                             # v24: the lifting eye on the box top removed (user)
    for sx in (-1, 1):
        for z, y in ((2.77, 0.22), (2.94, 0.09), (2.94, -0.16), (2.30, -0.16)):   # A and B agree to 3 cm (v23-v26: 2.90, behind the rim)
            out.append(revolve([(0, 0.026), (0.018, 0.02)], [sx * _box_side_x(y), b + y, z - pz], [sx, 0, 0], seg=6))
    hx = _box_side_x(0.0)                                                # loop handle, right side (drawing B: z 2.61-2.77)
    for y in (0.045, -0.045):
        out.append(box([hx + 0.035, b + y, 2.69 - pz], [0.018, 0.018, 0.15]))
    out.append(box([hx + 0.035, b, 2.765 - pz], [0.018, 0.108, 0.018]))
    for y in (0.045, -0.045):
        out.append(box([hx + 0.015, b + y, 2.62 - pz], [0.04, 0.018, 0.018]))
    z, n = box_front_point(0.25)
    for sx in (-1, 1):                                                   # two bolts high on the slope (front views: A +-0.053, B +-0.065)
        out.append(revolve([(0, 0.022), (0.015, 0.017)], [sx * 0.07, b + 0.25, z - pz], n, seg=6))   # v26: +-0.07 (top-front photo +-0.075)
    z, n = box_front_point(-0.10)
    for sx in (-1, 1):                                                   # two bolts on the face beside the barrel (A +-0.076, B +-0.092)
        out.append(revolve([(-0.002, 0.024), (0.016, 0.018)], [sx * 0.085, b - 0.10, z - pz], n, seg=6))   # v27: y -0.10 (-0.085), below the eased corner
    return out

def frame_outer_hw(y):
    """half-width of the frame's outer edge at plate height y: vertical down to y 0.035, then tapering to the bottom
    (drawing A front view: 0.478 to y 0.06, 0.31-0.32 at y -0.20; B and the 3/4 photo agree to 2 cm)"""
    return float(np.interp(y, [FRAME_BOT, -0.20, 0.035, FRAME_TOP], [0.30, 0.31, FRAME_HW_TOP, FRAME_HW_TOP]))

def cap_shields():
    """the bolted U-shaped frame on the front plate round the opening below the cap. v23: outline of drawing A's front
    view - straight sides under the cheeks, then tapering to a bottom bar with rounded corners (v22 was nearly straight
    down); three convex pieces: two side bars and the bottom bar"""
    n = FRONT[0]; t = FRAME_T
    hole_x0, hole_x1 = GUN_X - SLOT_HW, GUN_X + SLOT_HW
    def slab(poly):
        return _hull_of([on_plate(FRONT, x, y) + n * k for x, y in poly for k in (0.004, t)])
    ys = [FRAME_TOP, 0.035, -0.06, OPEN_Y0]
    out = []
    for sx in (-1, 1):                                                   # side bars: from the opening edge to the outer edge
        inner = GUN_X + sx * SLOT_HW
        out.append(slab([(inner, FRAME_TOP), (inner, OPEN_Y0)] + [(GUN_X + sx * frame_outer_hw(y), y) for y in ys[::-1]]))
    # bottom bar: below the opening, rounded outer corners (r 0.05)
    r = 0.05; yb = FRAME_BOT; hb = frame_outer_hw(yb + r)
    poly = [(GUN_X - frame_outer_hw(OPEN_Y0), OPEN_Y0), (GUN_X + frame_outer_hw(OPEN_Y0), OPEN_Y0)]
    for a in np.linspace(0.0, -np.pi / 2, 5): poly.append((GUN_X + hb - r + r * np.cos(a), yb + r + r * np.sin(a)))
    for a in np.linspace(-np.pi / 2, -np.pi, 5): poly.append((GUN_X - hb + r + r * np.cos(a), yb + r + r * np.sin(a)))
    out.append(slab(poly))
    return out

def frame_bolts():
    """v23: the bolt pattern of drawing A's front view (B agrees): two up each side, one in each bottom corner, one in the
    middle of the bottom bar (v22 had 3 + 3 + 3 with the bottom ones 0.20 apart; drawing 0.26, 3/4 photo 0.29)"""
    out = []; n = FRONT[0]
    # drawn positions are on the frame's face, 3.5 cm proud of the plate: 2.7 cm higher in the front view than on the plate
    pts = [(GUN_X + sx * dx, y) for sx in (-1, 1) for dx, y in ((0.434, 0.042), (0.357, -0.068), (0.257, -0.197))] + [(GUN_X, -0.214)]
    for x, y in pts:
        out.append(revolve([(0, 0.024), (0.016, 0.018)], on_plate(FRONT, x, y) + n * FRAME_T, n, seg=6))
    return out

def cap_details():
    """fittings on the cap (hull coordinates): v23 - a bolt low on each cheek face, at its outer bottom corner
    (drawing A front view: x 0.61 / -0.27, y 0.154; B: y 0.165). (v22: the lifting eye moved to the shield.)"""
    # v28: on the cheek's rounded front corner (plan radius CAP_RS), along its normal - v23-v27 put them on the line of the
    # flat face, 6-9 cm in front of the rounded corner (found by the floating-parts check)
    out = []
    for sx in (-1, 1):
        y = 0.155; zf = cap_front_z(y); hw = CAP_HW - _cap_side_inset(y); r = max(min(CAP_RS, zf - CAP_BACK - 0.05), 0.03)
        xc = GUN_X + sx * (hw - r); zc = zf - r; x = GUN_X + sx * 0.435; dx = x - xc
        z = zc + np.sqrt(max(r * r - dx * dx, 0.0))
        d = np.array([dx / r, -CAP_LEAN * (z - zc) / r, (z - zc) / r]); d /= np.linalg.norm(d)
        out.append(revolve([(-0.005, 0.024), (0.016, 0.018)], [x, y, z], d, seg=6))
    return out

# roof fittings (v20, plan views of drawings A and B, placed relative to the roof edges because B's casemate sits 0.13 m
# further forward than A's on the same hull; v19 had them from the photos, with the hood and the hatch swapped sideways):
#   panorama hood   A: x -0.21, z 0.94, 0.50 x 0.51     B: x -0.23, z 1.07, 0.53 x 0.54   front-left, 0.13-0.15 high
#   entry hatch     A: x +0.22, z 0.22, 0.63 x 0.60     B: x +0.32, z 0.41, 0.67 x 0.60   rear-right, hinged at the front
#   fan dome        A: x -0.36, z 0.15, d 0.45          B: x -0.30, z 0.30, d 0.40        rear-left, 0.10-0.11 high
#   PTK periscope   A: x +0.74, z 1.08                  B: x +0.71, z 1.08                front-right, head 0.22-0.27 high
HATCH_C = np.array([0.27, ROOF - 0.011, 0.33]); HATCH_S = (0.62, 0.016, 0.58) # entry hatch lid (x, thickness, z); v34j: sunk into the roof, its top 5 mm proud (user); v34d: no coaming
COAMING = (0.70, 0.02, 0.66)                                                  # low frame round the hatch opening
PTK_C = np.array([0.70, ROOF, 1.09])                                         # commander's PTK periscope (v29: top-front photo x 0.69, z 1.10)
PTK_WIN_Y = 0.165                                                            # height of its window above the roof (photo)
PANO_C = np.array([-0.185, ROOF, ROOF_EDGE_Z - 0.27])                       # armoured hood over the Hertz panorama; the top-front
# factory photo (camera re-solved on the v20 roof) puts it at x -0.51..+0.15 with its front edge at the roof edge (z 1.28):
# v19's x +0.17 was that photo read mirrored. Base 0.62 x 0.52 m between the photo (0.66) and the drawings (0.50-0.53)
FAN_C = np.array([-0.33, ROOF, 0.22])                                        # fan dome

def _hull_of(P):
    from scipy.spatial import ConvexHull
    P = np.asarray(P, float); h = ConvexHull(P); F = []
    for sx_, eq in zip(h.simplices, h.equations):
        a_, bb, c_ = P[sx_]
        if np.dot(np.cross(bb - a_, c_ - a_), eq[:3]) < 0: sx_ = sx_[[0, 2, 1]]
        F.append(sx_)
    return P, np.array(F)

def _rr_ring(hx, z0, z1, r, y, n=5):
    """rounded rectangle (x +-hx, z z0..z1, corner radius r) at height y, as points"""
    pts = []
    for cx, cz, a0 in ((hx - r, z1 - r, 0), (-hx + r, z1 - r, 90), (-hx + r, z0 + r, 180), (hx - r, z0 + r, 270)):
        for a in np.radians(np.linspace(a0, a0 + 90, n)): pts.append((cx + r * np.cos(a), y, cz + r * np.sin(a)))
    return pts

def roof_parts():
    """(entry hatch, PTK periscope, panorama hood body, fan) in hull coordinates; parts sit 1 cm into the roof. v29: the
    PTK is ptk(), the hood's fittings are pano_details() (small parts, not in the far LOD), dark windows in dark_fittings()"""
    # v34c (grey reference model): a flat lid with a long hinge rod along its RIGHT edge carried by two hinges, and a
    # small knob near its middle (v20-v34b: two hinge blocks on the front edge and a grab handle at the rear)
    # v34d (user): the rod along the FRONT edge - the lid opens to the front - and no coaming round the opening
    # v34i (the user's second kit photo, hatch at 4x): a thin lid with a raised rim, a knob at its rear-left corner and
    # TWO separate hinge units on the front edge, each a rounded pad with a pair of knuckles - no long rod, no bracket
    hz = HATCH_C[2] + HATCH_S[2] / 2; yt = HATCH_C[1] + HATCH_S[1]
    Rt = np.eye(3)[:, [0, 2, 1]]
    parts = [rounded_slab(HATCH_C, HATCH_S[0], HATCH_S[2], HATCH_S[1], 0.04, Rt, bevel=0.003)]
    rw = 0.012
    for sx in (-1, 1): parts.append(rounded_slab(HATCH_C + [sx * (HATCH_S[0] / 2 - rw / 2 - 0.01), HATCH_S[1], 0], rw, HATCH_S[2] - 0.04, 0.004, 0.004, Rt, n_arc=1))
    for sz in (-1, 1): parts.append(rounded_slab(HATCH_C + [0, HATCH_S[1], sz * (HATCH_S[2] / 2 - rw / 2 - 0.01)], HATCH_S[0] - 0.02, rw, 0.004, 0.004, Rt, n_arc=1))
    parts.append(_knob(HATCH_C + [-HATCH_S[0] / 2 + 0.07, HATCH_S[1], -HATCH_S[2] / 2 + 0.07], [0, 1.0, 0], r=0.016))
    for dx in (-0.17, 0.17):
        hc = np.array([HATCH_C[0] + dx, yt, hz])
        parts.append(rounded_slab(hc + [0, 0, 0.0], 0.10, 0.075, 0.006, 0.012, Rt, bevel=0.002))               # pad over the edge
        parts.append(box(hc + [0, -HATCH_S[1] / 2, 0.025], [0.10, HATCH_S[1], 0.025]))                          # its foot on the roof
        for kx in (-0.022, 0.022): parts.append(revolve([(kx - 0.017, 0.014), (kx + 0.017, 0.014)], hc + [0, 0.018, 0.0], [1.0, 0, 0], seg=10))
    hatch = merge(*parts)
    body = _hull_of(_rr_ring(PANO_HX[0], -0.26, 0.26, 0.07, -0.01) + _rr_ring(PANO_HX[1], -0.16, 0.16, 0.05, PANO_H))
    pano = (body[0] + PANO_C, body[1])
    # fan dome: 0.42 m, 0.11 high on a flange ring; v34 (kit photo): the "lugs" of A / B are rectangular NOTCHES - vent
    # openings cut into the skirt at the rim (fan_notches, dark), the dome's rim lipped out over them
    # v34e (grey reference): a smooth dome straight off the roof, one vent opening at its foot facing the front
    fan = revolve([(-0.01, 0.21), (0.012, 0.21), (0.035, 0.203), (0.06, 0.188), (0.082, 0.16), (0.1, 0.12), (0.11, 0.07), (0.114, 0.0)], FAN_C, [0, 1, 0], seg=28)
    return hatch, ptk(), pano, fan

def fan_notches():
    """v34k (user: "it should have 4 vent holes", then "rotate every vent hole so it's correct like in the image"): four
    dark vent openings at the fan dome's foot on the diagonals - front-right, front-left, rear-left, rear-right (both
    kit photos: the opening faces the hatch / the front corner; the drawings' lug angles) - 11 x 3.4 cm"""
    out = []
    for a in np.radians([45, 135, 225, 315]):
        R = np.array([[np.cos(a), 0, np.sin(a)], [0, 1, 0], [-np.sin(a), 0, np.cos(a)]]).T
        out.append(box(FAN_C + [0.198 * np.cos(a), 0.022, 0.198 * np.sin(a)], [0.02, 0.034, 0.11], R))
    return out

# v29 (user: "improve on vision ports, gunners sight, other sights etc"). Commander's PTK: the top-front photo is the only
# photo that shows it (in the factory photos the raised gun box hides it): a head tapering from 0.14 m at the bottom to
# 0.10 m under its rounded top, a round window (4.6 cm) high on its front, on a base flange 0.21 m across; drawing A plan:
# a ring with an inner disc, three lugs, the window towards the front; rear views A and B: a band low on the head.
# Its position x 0.70 (photo 0.69, drawings 0.71-0.74); z 1.09 from the drawings (the photo cannot fix z: it looks down on it).
# v20-v28: a square head with a half-round top and a brow, 0.265 m high; now 0.245 (photo: the head about 1.5 times as
# tall as it is wide; drawings 0.24-0.26).
def ptk(simple=False):
    """commander's PTK periscope (hull coordinates): v34e (grey reference) a plain cylinder 0.14 across on a low round
    flange, its top softly rounded; no band, no lugs (v29: tapered head with a band and three lugs)"""
    seg = 10 if simple else 18
    prof = [(-0.008, 0.10), (0.018, 0.10), (0.022, 0.092), (0.022, 0.072), (0.19, 0.072), (0.212, 0.066), (0.228, 0.052), (0.238, 0.03), (0.242, 0.0)]
    return revolve(prof, PTK_C, [0, 1.0, 0], seg=seg)

def ptk_window():
    """dark round window on the front of the PTK head (hull coordinates), 4.6 cm across"""
    return revolve([(0.0, 0.018), (0.012, 0.018)], PTK_C + [0, PTK_WIN_Y + 0.02, 0.072 - 0.008], [0, 0, 1.0], seg=14)   # v34h: round hole high on the front (kit)

# Gunner's panorama hood: top-front photo (it sees the hood square-on): 0.66 m wide at the roof, 0.46 m at the top (v20-v28:
# 0.62 / 0.50), centred at x -0.18; a raised flap on the front slope (x +0.02..-0.335, from the top edge down to 2 cm
# above the roof) with a round handle at its left end (x -0.29, triangulated from three photos to 3-5 px); along the top's
# front edge a bar with three dark windows (centres 8 cm apart; the 3/4 and front-left photos: light bar, dark windows);
# lifting staples standing on the top's two rear corners (top-front photo: arches with a dark gap under them). Shutter bars along
# the sides and back of the top (plan views) as before.
PANO_HX = (0.32, 0.235)
PANO_H = 0.14
# v34 (user's kit photo, "look at the detail on the top hull hatch, the vent cover and other details"; the top-front factory
# photo re-read at 7x agrees): the "bar with three dark windows" along the flap's top edge was the HINGE - three knuckles
# with dark gaps; the flap is a hinged cover with a domed knob at its left end, and beside it on the hood's left part a
# second, smaller hinged cover (the top-front photo: a smaller raised rectangle right of the big one in the image, i.e.
# on the vehicle's left, less tall, same top level). On the hood's top: a hinged cover plate over the sight's opening on
# the right-rear with the sight head standing beside it, and a small hinged strip in the middle (kit); the plan drawings'
# side bars go, the rear bar stays as the cover plate's hinge side.
def _knuckles(p0, p1, n_out, k=3, r=0.013, length=0.05):
    """k hinge knuckles (cylinders of radius r) evenly spaced along the segment p0-p1, lying just outside the surface"""
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float); d = p1 - p0; L = np.linalg.norm(d); d /= L
    out = []
    for i in range(k):
        c = p0 + d * (L * (i + 0.5) / k) + np.asarray(n_out, float) * r
        out.append(revolve([(-length / 2, r), (length / 2, r)], c, d, seg=8))
    return out
def _knob(c, n, r=0.021):
    return revolve([(-0.002, r), (0.010, r), (0.018, r * 0.67), (0.022, 0.0)], c, n, seg=12)
def port_box(c, R, w, h, d, flap_deg=0.0, knob=True, slim=False):
    """v34c (user's grey reference model): an armoured vision port as a BOX housing standing d out of its plate, a dark
    slot in its front face, a thin hinge rod with small knuckles along the top-front edge and a flap on the rod - closed
    over the slot (flap_deg 0, with a knob) or lifted. Returns (parts, dark slot). c: centre of the housing's base on the
    plate, R columns: along, up, out"""
    xa, up, n = R[:, 0], R[:, 1], R[:, 2]
    parts = [rounded_slab(c, w, h, d, 0.012, R, bevel=0.004)]                                   # housing
    slot = rounded_slab(c + n * (d - 0.001) - up * 0.004, w * 0.62, 0.032, 0.003, 0.005, R, n_arc=1)
    rr, rk, kl = (0.007, 0.014, 0.036) if slim else (0.0065, 0.011, 0.022)                    # slim: the hood's ports (v34g: chunky knuckles as in the grey reference - the user: "too small" twice)
    rod = c + up * (h / 2 - 0.004) + n * (d + rk - 0.003)                                       # hinge rod on the top-front edge
    parts.append(revolve([(-w / 2 + 0.012, rr), (w / 2 - 0.012, rr)], rod, xa, seg=8))
    nk = 6 if w >= 0.3 else 4                                                                   # six knuckles (four on a narrow port)
    for i, x in enumerate(np.linspace(-w / 2 + kl / 2 + 0.01, w / 2 - kl / 2 - 0.01, nk)):
        parts.append(revolve([(-kl / 2, rk), (kl / 2, rk)], rod + xa * x, xa, seg=8))
    a = np.radians(flap_deg); g = -up * np.cos(a) + n * np.sin(a); fn = up * np.sin(a) + n * np.cos(a)
    fw, fh = w - 0.02, h - 0.016
    ft = 0.005 if slim else 0.008
    fc = rod + g * (fh / 2 + 0.004) - fn * (rr if flap_deg < 1 else 0.004)
    parts.append(rounded_slab(fc, fw, fh, ft, 0.008, np.c_[xa, g, fn], bevel=0.002))
    if knob: parts.append(_knob(fc + g * (fh / 2 - 0.025) + fn * ft, fn, r=0.013 if slim else 0.016))
    return parts, slot

def pano_cover(c, R, w, h, nk, knob_sx, t=0.008):
    """v34h (the user's two kit photos, hood at 5x): an armoured cover on a hood face - a bevelled plate w x h, t thick,
    hinged along its top edge by nk chunky BLOCK knuckles (3.5 x 2.4 x 2.4 cm, small gaps) that straddle the cover's edge
    and the hood face, and a domed knob low on the cover at the knob_sx end. c: centre of the cover on the face, R columns:
    along, up, out (hull coordinates)"""
    xa, up, n = R[:, 0], R[:, 1], R[:, 2]
    parts = [rounded_slab(c - n * 0.012, w, h, t + 0.012, 0.015, R, bevel=0.004)]            # v34r: rooted 1.2 cm in, 8 mm proud (sunk from 1.5 - user)
    # v34p (user: the block hinges "look fucked up"): one straight piano-style hinge - six round knuckles (r 1.2 cm,
    # 3 mm gaps) on a common axis just above the cover's top edge; alternate knuckles carry a short flat leaf down onto
    # the cover / up onto the face behind it (three each, "each have 6 hinges")
    rk, gap = 0.012, 0.003; nk = 6; span = w - 0.03; kl = (span - gap * (nk - 1)) / nk
    axis = c + up * (h / 2 + 0.002) + n * (t + rk - 0.004)
    parts.append(revolve([(-span / 2, 0.005), (span / 2, 0.005)], axis, xa, seg=8))            # the pin
    for i in range(nk):
        x = -span / 2 + kl / 2 + i * (kl + gap)
        parts.append(revolve([(-kl / 2, rk), (kl / 2, rk)], axis + xa * x, xa, seg=12))
        # (v34t, user: no leaves on the cover - the knuckles sit straight on its top edge)
    # v34q (user: the hood-side leaves "need to be one piece and hold onto the mount"): one backing strap the full width
    # of the hinge, lying on the face behind the pin (rooted 1 cm into it), carrying the hood's three knuckles
    parts.append(rounded_slab(c + up * (h / 2 + 0.012) - n * 0.010, span + 0.02, 0.03, t + rk - 0.004 + 0.010 - 0.004, 0.004, R, n_arc=1))
    parts.append(_knob(c + xa * knob_sx * (w / 2 - 0.035) - up * (h / 2 - 0.03) + n * t, n, r=0.016))
    return parts

def pano_details():
    """v34h: the hood as the user's kit shows it (two kit photos, grey reference model): on the front slope one cover
    (x +0.02..-0.335, knob at its left end - the knob position the v29 photos triangulated); one cover on each sloped side; chunky block-knuckle hinges along their top edges; nothing else on
    the hood (hull coordinates)"""
    out = []
    for c, R, w, h, nk, ks in _pano_ports(): out += pano_cover(c, R, w, h, nk, ks)
    return out

def _pano_ports():
    """(centre, frame R (along, up, out), width, height, knuckles, knob end) of the hood's covers; they sit on the sloped
    faces (base ring hx 0.32 / z +-0.26 at -0.01, top hx 0.235 / z +-0.16 at PANO_H)"""
    c0 = PANO_C; hb = PANO_H + 0.01; ports = []
    n_f = np.array([0, 0.10, 0.15]) / np.hypot(0.10, 0.15); up_f = np.array([0, 0.15, -0.10]) / np.hypot(0.10, 0.15)
    Rf = np.c_[[1.0, 0, 0], up_f, n_f]
    zf = 0.26 - 0.072 * 0.10 / 0.15                                        # the front slope at 6.2 cm up (v34q: covers lowered)
    ports.append((c0 + [0.028, 0.062, zf], Rf, 0.355, 0.11, 3, -1))                              # big front cover, x +0.02..-0.335
    # (v34n: no small second cover on the front - user: three ports, front / left / right, nothing else)
    dx = PANO_HX[0] - PANO_HX[1]
    for sx in (-1, 1):
        n_s = np.array([sx * hb, dx, 0]) / np.hypot(hb, dx); up_s = np.array([-sx * dx, hb, 0]) / np.hypot(hb, dx)
        ports.append((c0 + [sx * (PANO_HX[0] - 0.072 * dx / hb + 0.012 * hb / np.hypot(hb, dx)), 0.062 + 0.012 * dx / np.hypot(hb, dx), 0.0], np.c_[[0, 0, -sx * 1.0], up_s, n_s], 0.22, 0.11, 4, -1))   # v34m: on the face + 1.2 cm proud
    return ports

def pano_windows():
    """v34h: no dark parts on the hood (the covers are closed)"""
    return []

def side_point(y, z, sx, out=0.0):
    """point on the left (sx=-1) or right (sx=+1) casemate side plate at height y, plus `out` along its normal"""
    n = np.array([sx * np.cos(a20), np.sin(a20), 0.0]); x = (SIDE_D - np.sin(a20) * y) / np.cos(a20)
    return np.array([sx * x, y, z]) + n * out, n

def hull_details():
    """small fittings from the drawings / photos: riders' handrails on both casemate sides, pistol-port plugs (left: drawing
    A, right: drawing B), riders' grab loops and two upright handles low on the sides, frame bolts, lifting eyes at the top
    corners of the front plate, handrail on the rear plate"""
    out = []
    side_R = lambda n: np.c_[n, np.cross([0, 0, 1.0], n), [0, 0, 1.0]]
    for sx in (-1, 1):                                   # handrails: A y 0.35, z -0.14..1.56; B y 0.31, z -0.02..1.64
        p0, n = side_point(0.33, -0.05, sx, 0.065); p1, _ = side_point(0.33, 1.60, sx, 0.065)
        c = (p0 + p1) / 2; Rr = side_R(n)
        out.append(box(c, [0.025, 0.025, p1[2] - p0[2]], Rr))
        for z in (0.0, 0.78, 1.55):
            q, _ = side_point(0.33, z, sx, 0.035); out.append(box(q, [0.07, 0.022, 0.022], Rr))
    # pistol ports (v29): a domed plug in a horseshoe guard (drawings A and B side and rear views; side photos: a domed
    # plug casting a crescent shadow). Left: photos 783321f8 / 5c2a9524 y 0.63 / 0.70, z 1.06 / 1.01, drawing A y 0.69,
    # z 1.10 -> y 0.68, z 1.05; right: photo a417840d y 0.52, z 0.75, drawing B y 0.54, z 0.79 -> y 0.53, z 0.765
    # (v20-v28: left 1.10, right y 0.56, z 0.88 - 12 cm too far forward)
    for sx, y, z in PISTOL_PORTS:
        q, n = side_point(y, z, sx, 0.0)
        out += pistol_port(q, n, np.array([-sx * np.sin(a20), np.cos(a20), 0.0]))
    # riders' grab loops along the bottom of the casemate sides (drawing B: right side, z -0.02..0.97 every 0.25 m; on the
    # left the T-34 tool box rides on the fender from z 0.59)
    for sx, zs in ((1, (-0.02, 0.24, 0.48, 0.72, 0.96)), (-1, (-0.02, 0.24, 0.48))):
        for z in zs:
            q, n = side_point(0.10, z, sx, 0.04); Rr = side_R(n)
            out.append(box(q, [0.02, 0.10, 0.02], Rr))
            q2, _ = side_point(0.10, z, sx, 0.02); out.append(box(q2 + [0, 0.05, 0], [0.04, 0.02, 0.02], Rr))
    for z in (0.87, 1.40):                               # upright handles, right side (drawing B: "I" shapes, y 0.18-0.30)
        q, n = side_point(0.24, z, 1, 0.045); Rr = side_R(n)
        out.append(box(q, [0.02, 0.13, 0.02], Rr))
        for dy in (-0.05, 0.05):
            q2, _ = side_point(0.24 + dy, z, 1, 0.022); out.append(box(q2, [0.045, 0.02, 0.02], Rr))
    out += frame_bolts()
    # lifting eyes at the top corners of the front plate
    for x in (-0.80, 0.80):
        c = on_plate(FRONT, x + GUN_X * 0, ROOF - 0.10) + FRONT[0] * 0.042   # v29: touching the plate (0.05 left a 1.3 cm gap)
        out.append(revolve([(-0.012, 0.045), (0.012, 0.045)], c, [1, 0, 0], seg=10))
        out.append(box(on_plate(FRONT, x, ROOF - 0.10) + FRONT[0] * 0.01, [0.06, 0.04, 0.04]))
    # rear plate: handrail 0.10 m under the roof across the plate on three brackets (rear views A and B)
    rn = np.array([0, np.sin(a10), -np.cos(a10)]); y = ROOF - 0.10; zr = REAR_Z - np.tan(a10) * (ROOF - y)
    out.append(box(np.array([0, y, zr]) + rn * 0.06, [1.70, 0.025, 0.025]))
    for x in (-0.80, 0.0, 0.80):
        out.append(box(np.array([x, y, zr]) + rn * 0.03, [0.025, 0.025, 0.06], plate_frame(rn)))
    out += rear_port()                                   # v29: pistol port in the middle of the rear plate, under the rail
    # v23 (user, drawing A side view): the signal horn on the left, right behind the headlight - side view: a dome at the
    # front (z 1.64-1.72), a body (1.52-1.64) and a flared bell (1.45-1.52), y 0.16-0.27, on a short bracket; plan view:
    # x -1.31. Raised 3 cm here so its bell clears the T-34 fender box (top y 0.17; the drawing's box is lower)
    hc = np.array([-1.31, 0.255, 0.0]); ax = np.array([0, 0, 1.0])
    out.append(revolve([(1.455, 0.0), (1.46, 0.07), (1.47, 0.085), (1.50, 0.075), (1.53, 0.05), (1.56, 0.048), (1.63, 0.048),
                        (1.64, 0.075), (1.67, 0.078), (1.70, 0.065), (1.72, 0.035), (1.725, 0.0)], hc, ax, seg=16))
    out.append(box([-1.31, 0.19, 1.585], [0.02, 0.05, 0.06]))                         # bracket down to the fender box
    out.append(box([-1.31, 0.172, 1.585], [0.08, 0.008, 0.08]))                         # its foot
    # headlight bracket (drawing A front view: a triangular bracket from the lamp down to the hull side): a tapered plate
    # from under the lamp (y 0.21) in to the casemate side plate
    yb = 0.10; xs = (SIDE_D - np.sin(a20) * yb) / np.cos(a20)
    out.append(_hull_of([(x, 0.215, z) for x in (-1.32, -1.24) for z in (1.785, 1.815)] +
                        [(x, yb, z) for x in (-xs - 0.015, -xs + 0.01) for z in (1.79, 1.81)]))
    return out

def rounded_slab(c, w, h, t, r, R, bevel=0.0, n_arc=4):
    """a rounded-rectangle block lying on a plane: c = centre of its base, width w along R[:, 0], height h along R[:, 1],
    thickness t along R[:, 2], corner radius r; the top face shrunk by `bevel` all round (softened top edge). Convex hull."""
    def ring(w_, h_, r_):
        r_ = max(min(r_, w_ / 2 - 1e-4, h_ / 2 - 1e-4), 1e-4); pts = []
        for cx, cy, a0 in ((w_ / 2 - r_, h_ / 2 - r_, 0), (r_ - w_ / 2, h_ / 2 - r_, 90), (r_ - w_ / 2, r_ - h_ / 2, 180), (w_ / 2 - r_, r_ - h_ / 2, 270)):
            for a in np.radians(np.linspace(a0, a0 + 90, n_arc + 1)): pts.append((cx + r_ * np.cos(a), cy + r_ * np.sin(a)))
        return pts
    c = np.asarray(c, float)
    P = [c + R[:, 0] * x + R[:, 1] * y for x, y in ring(w, h, r)] + \
        [c + R[:, 0] * x + R[:, 1] * y + R[:, 2] * t for x, y in ring(w - 2 * bevel, h - 2 * bevel, max(r - bevel, 0.002))]
    return _hull_of(P)

def oval_dome(c, a, b, t, R, n=16, rings=4):
    """a low elliptical boss on a plane: semi-axes a (R[:, 0]) and b (R[:, 1]), height t (R[:, 2]), rounded top"""
    c = np.asarray(c, float); P = []
    for k in range(rings + 1):
        ph = np.pi / 2 * k / rings; s_ = np.cos(ph) if k else 1.0; z = t * np.sin(ph)
        for q in np.linspace(0, 2 * np.pi, n, endpoint=False):
            P.append(c + R[:, 0] * a * s_ * np.cos(q) + R[:, 1] * b * s_ * np.sin(q) + R[:, 2] * z)
    return _hull_of(P)

# v28 (user: "drivers hatch needs improvement" - Blender view of v27: a flat slab with thin outline panels, three teeth and a
# handle). Re-modelled from the top-front factory photo (40807adf), which sees the front plate almost square-on (14 deg
# off its normal; features back-projected onto the plate with the camera re-solved in v26, checked on the frame bolt next
# to the hatch to 3 px), and the front views of drawings A and B (same layout, the hatch drawn 5-9 cm taller):
#   lid           x -0.334..-0.690, y 0.16..0.415 on the plate (0.40 m along it), rounded corners, ~2 cm proud
#                 (v20-v27: x -0.677..-0.337, y 0.196..0.546 - 14 cm too long and 8-13 cm too high)
#   hinge         knuckles along the top edge (small dark gaps in the photo at x -0.37..-0.63)
#   housing       a block on the upper part, x -0.386..-0.585, from 1 to 14 cm below the top edge, 5.5 cm proud (its
#                 shadow on the lid is ~5 cm long), with a lower step beside it towards the outer edge (x -0.585..-0.67,
#                 drawing A; in the housing's shadow in the photo)
#   lower panel   a pressed panel in the lower part, x -0.37..-0.646, 0.20-0.375 below the top edge, with a small oval
#                 boss near its outer bottom corner (drawing A)
#   below the lid a bar on the plate, x -0.33..-0.69, y 0.105..0.145 (photo; drawing A 4 cm lower)
DRV_X, DRV_Y0, DRV_Y1 = -0.512, 0.16, 0.415
DRV_W = 0.356
DRV_HOFF = (0.004, 0.016)                 # hinge axis: up the plate, out of it, from the lid's top edge on the plate
def driver_hatch(simple=False):
    """the SU-122's driver's hatch: (V, F) of the lid with its fittings in the hinge frame (origin on the axis of the hinge
    knuckles, 1.6 cm out of the plate at the lid's top edge; axes as world, the plate's x, up and normal from plate_frame),
    the hinge point (world), None. simple: lid, housing and step only (far LOD, hit mesh)"""
    Rp = plate_frame(FRONT[0]); n = FRONT[0]; up = Rp[:, 1]; xa = Rp[:, 0]
    L = (DRV_Y1 - DRV_Y0) / up[1]
    hoff = up * 0.004 + n * 0.016                                        # v28: the node turns about the knuckles' axis
    hinge = on_plate(FRONT, DRV_X, DRV_Y1) + hoff
    bx = -0.4855 - DRV_X                                                 # housing centre, 2.7 cm towards the gun
    na = 1 if simple else 4
    parts = [rounded_slab(-up * L / 2, DRV_W, L, 0.02, 0.03, Rp, bevel=0.005, n_arc=na),                      # lid, 2 cm
             rounded_slab(xa * bx - up * 0.0725 + n * 0.018, 0.20, 0.129, 0.037, 0.012, Rp, bevel=0.006, n_arc=na)]   # periscope housing, 5.5 cm
    # beside the housing towards the outer edge a lower step (drawing A front view; the top-front photo shows it darker - in
    # the housing's shadow)
    parts.append(rounded_slab(xa * (bx - 0.10 - 0.042) - up * 0.078 + n * 0.018, 0.078, 0.112, 0.022, 0.01, Rp, bevel=0.005, n_arc=na))
    if simple:
        V, F = merge(*parts); return (V - hoff, F), hinge, None
    parts += [rounded_slab(xa * 0.004 - up * 0.2875 + n * 0.018, 0.27, 0.175, 0.010, 0.03, Rp, bevel=0.007),  # pressed lower panel
              revolve([(-0.002, 0.024), (0.010, 0.024), (0.017, 0.016), (0.021, 0.0)], xa * -0.068 - up * 0.335 + n * 0.027, n, seg=12)]  # v34: round knob (kit; v28 a small oval boss)
    # v34 (kit photo): a raised rim round the lid's edge, 1.2 cm wide, 6 mm proud of the lid
    rw, rt = 0.012, 0.006
    for sx in (-1, 1):
        parts.append(rounded_slab(xa * sx * (DRV_W / 2 - rw / 2 - 0.006) - up * L / 2 + n * 0.018, rw, L - 0.04, rt, 0.004, Rp, n_arc=1))
    for ey in (-0.006 - rw / 2, -L + 0.006 + rw / 2):
        parts.append(rounded_slab(up * ey + n * 0.018, DRV_W - 0.012, rw, rt, 0.004, Rp, n_arc=1))
    # hinge along the top edge: five knuckles (top-front photo: four gaps between x -0.37 and -0.65); the outer and middle
    # ones belong to the lid (here), the other two to the hull (hatch_hinge_fixed)
    for xc in (-0.112, 0.0, 0.112):
        parts.append(revolve([(xc - 0.025, 0.016), (xc + 0.025, 0.016)], hoff, xa, seg=10))
    V, F = merge(*parts)
    return (V - hoff, F), hinge, None

HATCH_INSET = 0.03                        # the openings' edges lie this far inside the lids' outlines
def hatch_openings():
    """v32 (user: the opened hatches showed no opening): the holes under the two hatch lids as plane sets for
    geom.subtract_convex - the driver's hatch in the front plate (DRV_X / DRV_W wide, DRV_Y0..DRV_Y1 high, in world y:
    the plate's x is world x and its 'up' has a constant slope, so the hole is a rectangle on the plate) and the entry
    hatch in the roof (HATCH_C / HATCH_S), each HATCH_INSET inside the lid"""
    i = HATCH_INSET; up = plate_frame(FRONT[0])[:, 1]; iy = i * up[1]
    drv = [(np.array([1.0, 0, 0]), DRV_X + DRV_W / 2 - i), (np.array([-1.0, 0, 0]), -(DRV_X - DRV_W / 2 + i)),
           (np.array([0, 1.0, 0]), DRV_Y1 - iy), (np.array([0, -1.0, 0]), -(DRV_Y0 + iy)),
           (np.array([0, 0, -1.0]), -(front_z(DRV_Y0) - 0.5))]                     # only the front plate, not the rear one
    roof = [(np.array([1.0, 0, 0]), HATCH_C[0] + HATCH_S[0] / 2 - i), (np.array([-1.0, 0, 0]), -(HATCH_C[0] - HATCH_S[0] / 2 + i)),
            (np.array([0, 0, 1.0]), HATCH_C[2] + HATCH_S[2] / 2 - i), (np.array([0, 0, -1.0]), -(HATCH_C[2] - HATCH_S[2] / 2 + i)),
            (np.array([0, -1.0, 0]), -(ROOF - 0.05))]
    return drv, roof

def hatch_pockets(depth_front=0.35, depth_roof=0.55):
    """v32: dark recesses behind the hatch openings (hull coordinates): four walls into the hull and a back wall, faces
    pointing into the opening, so an open hatch shows a dark interior instead of the far side of the hull. Returns
    (walls, backs): the back walls get the black texture, the walls the dark olive of the gun-slot recess"""
    i = HATCH_INSET; Rp = plate_frame(FRONT[0]); n = FRONT[0]; up = Rp[:, 1]; iy = i * up[1]
    walls, backs = [], []
    # driver's hatch: corners on the plate (0.5 cm proud, so the walls meet the plate without a gap), back wall parallel to it
    x0, x1 = DRV_X - DRV_W / 2 + i, DRV_X + DRV_W / 2 - i; y0, y1 = DRV_Y0 + iy, DRV_Y1 - iy
    c = {k: on_plate(FRONT, x, y) + n * 0.005 for k, (x, y) in enumerate(((x0, y0), (x1, y0), (x1, y1), (x0, y1)))}
    b = {k: c[k] - n * depth_front for k in c}
    walls.append(_fan([c[0], c[3], b[3], b[0]], [1, 0, 0]))              # left wall (x0), normal towards +x
    walls.append(_fan([c[1], c[2], b[2], b[1]], [-1, 0, 0]))             # right wall
    walls.append(_fan([c[0], c[1], b[1], b[0]], list(up)))               # bottom, normal up the plate
    walls.append(_fan([c[3], c[2], b[2], b[3]], list(-up)))              # top
    backs.append(_fan([b[0], b[1], b[2], b[3]], list(n)))
    # entry hatch: vertical walls down from the roof, floor at depth_roof
    hx, hz = HATCH_S[0] / 2 - i, HATCH_S[2] / 2 - i; y = ROOF + 0.005
    cs = [np.array([HATCH_C[0] + sx * hx, y, HATCH_C[2] + sz * hz]) for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    bs = [q - [0, depth_roof + 0.005, 0] for q in cs]
    for k in range(4):
        a_, d_ = cs[k], cs[(k + 1) % 4]; inward = -np.array([a_[0] + d_[0] - 2 * HATCH_C[0], 0, a_[2] + d_[2] - 2 * HATCH_C[2]])
        walls.append(_fan([a_, d_, bs[(k + 1) % 4], bs[k]], list(inward / (np.linalg.norm(inward) + 1e-9))))
    backs.append(_fan(bs, [0, 1, 0]))
    return merge(*walls), merge(*backs)

def hatch_hinge_fixed():
    """v28: the hull's two knuckles of the driver's hatch hinge, with pads on the plate above the hinge line (hull coordinates)"""
    Rp = plate_frame(FRONT[0]); n = FRONT[0]; up = Rp[:, 1]; xa = Rp[:, 0]
    h = on_plate(FRONT, DRV_X, DRV_Y1); hoff = up * 0.004 + n * 0.016; out = []
    for xc in (-0.056, 0.056):
        out.append(revolve([(xc - 0.024, 0.016), (xc + 0.024, 0.016)], h + hoff, xa, seg=10))
        out.append(rounded_slab(h + xa * xc + up * 0.026, 0.042, 0.036, 0.012, 0.004, Rp))
    return out

def weld_beads(V, F, r=0.017):
    """weld seams along the casemate's plate junctions above the fender line (rounded beads, 6 sides); v34: r 1.7 cm
    (1.2) - the kit photo and the factory photos show heavy beads"""
    from collections import defaultdict
    n = geom.normals(V, F); edges = defaultdict(list)
    for k, f in enumerate(F):
        for i in range(3):
            a, b = sorted((f[i], f[(i + 1) % 3])); edges[(a, b)].append(k)
    out = []
    for (a, b), fs in edges.items():
        if len(fs) != 2 or n[fs[0]] @ n[fs[1]] > 0.98: continue          # flat diagonal of a plate
        p, q = V[a], V[b]
        if min(p[1], q[1]) < FENDER_Y + 0.02 and abs(p[1] - q[1]) < 0.02: continue   # bottom edge on the hull
        lo = p if p[1] < q[1] else q; hi = q if lo is p else p
        if lo[1] < FENDER_Y + 0.02:                                          # trim the part below the fender line
            t = (FENDER_Y + 0.02 - lo[1]) / (hi[1] - lo[1]); lo = lo + t * (hi - lo)
        d = hi - lo; L = np.linalg.norm(d)
        if L < 0.05: continue
        out.append(revolve([(0, r), (L, r)], lo, d / L, seg=6))
    return out

def mark_sockets():
    """unit-marking sockets (mslots): on the casemate side plates, local z = outward plate normal, local y = up the plate,
    local x forward on the left side / rearward on the right (as the T-34 and SU-152 sockets). Numbers above the riders'
    rail behind the pistol port (Patriot-park and Kubinka photos), slogans below the rail, the badge at the right rear."""
    out = {}
    for name, sx, y, z in (('s_mark_01', 1, 0.60, 0.42), ('s_mark_01f', 1, 0.60, 0.18),       # number, right side (v20: behind
                           ('s_mark_02', -1, 0.60, 0.45), ('s_mark_02f', -1, 0.60, 0.75),     #   the right pistol port); left side
                           ('s_mark_03', -1, 0.22, 0.35), ('s_mark_03f', -1, 0.22, 0.75),     # slogan, left side, under the rail
                           ('s_mark_04', 1, 0.55, 1.12)):                                     # badge, right side, in front of the port
        p, n = side_point(y, z, sx, 0.004)
        t = np.array([-sx * np.sin(a20), np.cos(a20), 0.0]); xax = np.array([0, 0, 1.0 if sx < 0 else -1.0])
        M = np.eye(4); M[0, :3] = xax; M[1, :3] = t; M[2, :3] = np.cross(xax, t); M[3, :3] = p
        out[name] = M
    return out

def front_fittings():
    """on the front plate around the driver's hatch (v28, top-front photo and drawing A front view): the box above the hatch
    with a round knob (x -0.342..-0.512, y 0.48..0.66; knob at -0.442, 0.568), rounded corners; the bar under the lid
    (x -0.33..-0.69, y 0.105..0.145). (v20-v27: a sharp box 7 cm higher, knob 9 cm too high, no bar)"""
    Rp = plate_frame(FRONT[0]); n = FRONT[0]; out = []
    out.append(rounded_slab(on_plate(FRONT, -0.427, 0.569), 0.17, 0.26, 0.045, 0.02, Rp, bevel=0.007))
    out.append(revolve([(-0.005, 0.038), (0.008, 0.038), (0.018, 0.031), (0.026, 0.016), (0.029, 0.0)], on_plate(FRONT, -0.442, 0.568) + n * 0.045, n, seg=16))   # knob r 3.8 cm
    out.append(rounded_slab(on_plate(FRONT, DRV_X, 0.125), 0.36, 0.064, 0.018, 0.008, Rp, bevel=0.006))
    xa, up = Rp[:, 0], Rp[:, 1]; c = on_plate(FRONT, -0.427, 0.569)                 # v34: weld bead round the knob box (kit)
    ring = [c + xa * x + up * y for x, y in ((-0.085, -0.13), (0.085, -0.13), (0.085, 0.13), (-0.085, 0.13))]
    out.append(tube([p + n * 0.004 for p in ring], 0.007, seg=5, closed=True, normal=n))
    return out + hatch_hinge_fixed()

def coaming():
    """v34d: no coaming round the entry hatch (user: "the weird edges from the sides"); v20-v34c had four bars"""
    return []

def plate_frame(n):
    """3x3 with columns: x, up-along-plate, normal (for parts lying on a sloped plate)"""
    n = np.asarray(n, float); n /= np.linalg.norm(n)
    x = np.array([1.0, 0, 0]) if abs(n[0]) < 0.9 else np.array([0, 0, 1.0])
    x = x - n * (x @ n); x /= np.linalg.norm(x); t = np.cross(n, x)
    return np.c_[x, t, n]

def on_plate(plane, x, y):
    """point on a plate plane (n.x = d) for given x, y"""
    n, d = plane; z = (d - n[0] * x - n[1] * y) / n[2]; return np.array([x, y, z])

VISOR_C = (-0.637, 0.757)
VISOR_R_Z = 0.74            # right side visor centre (v29: photo a417840d z 0.61-0.84, drawing B 0.64-0.86; v20-v28 0.84)
PISTOL_PORTS = ((-1, 0.68, 1.05), (1, 0.53, 0.765))

def visor_device(c, R, w, h, t):
    """armoured vision device lying on a plate (R columns: along, up, out): a rounded housing with a brow over the slit
    and a lip under it, so the slit reads as a slot (v29; v28: a plain block with a dark strip). Returns (parts, slit)"""
    up, n = R[:, 1], R[:, 2]; ws = w * 0.70; hs = 0.024
    parts = [rounded_slab(c, w, h, t, 0.025, R, bevel=0.006),
             rounded_slab(c + up * (hs / 2 + 0.008) + n * (t - 0.001), ws + 0.03, 0.016, 0.010, 0.006, R, bevel=0.003, n_arc=2),   # brow
             rounded_slab(c - up * (hs / 2 + 0.006) + n * (t - 0.001), ws + 0.02, 0.012, 0.005, 0.005, R, bevel=0.002, n_arc=2)]   # lip
    slit = rounded_slab(c + n * (t - 0.001), ws, hs, 0.003, 0.008, R, n_arc=2)
    return parts, slit

def _visor_frames():
    Rf = plate_frame(FRONT[0])
    side_n = np.array([np.cos(a20), np.sin(a20), 0]); y = ROOF - 0.06; xs = (SIDE_D - np.sin(a20) * y) / np.cos(a20)
    Rs = np.c_[[0, 0, 1.0], np.cross(np.array([0, 0, 1.0]), side_n), side_n]
    return [(on_plate(FRONT, VISOR_C[0], VISOR_C[1]), Rf, 0.245, 0.125, 0.04),     # front plate, top left (top-front photo:
            (np.array([xs, y, VISOR_R_Z]), Rs, 0.225, 0.11, 0.05)]                    # x -0.514..-0.76, y 0.718..0.796)

def vision_port(c, R, w, h, t=0.015):
    """v34o (user: both vision ports "wrong"): the hull vision ports are armoured covers of the same make as the hood's
    (`pano_cover`: bevelled plate, six block knuckles along the top edge, domed knob), closed, on a thin welded base
    plate with a dark slit under the cover's lower edge. Returns (parts, dark slit)"""
    xa, up, n = R[:, 0], R[:, 1], R[:, 2]
    parts = [rounded_slab(c, w + 0.05, h + 0.05, 0.008, 0.02, R, bevel=0.003)]
    parts += pano_cover(c + n * 0.008 + up * 0.006, R, w, h, 6, 1, t)
    ring = [c + xa * x + up * y for x, y in ((-w / 2 - 0.025, -h / 2 - 0.025), (w / 2 + 0.025, -h / 2 - 0.025), (w / 2 + 0.025, h / 2 + 0.025), (-w / 2 - 0.025, h / 2 + 0.025))]
    parts.append(tube([p + n * 0.004 for p in ring], 0.006, seg=5, closed=True, normal=n))
    slit = rounded_slab(c + n * 0.009 - up * (h / 2 - 0.004), w * 0.7, 0.012, 0.003, 0.004, R, n_arc=1)
    return parts, slit

def visors():
    """armoured vision devices: front plate top left (A: x -0.64, y 0.72-0.81; B: x -0.61, 0.78-0.91, both just under the
    roof) - v34: a framed port with its flap lifted (kit photo); right side plate under the roof (v29: z 0.625-0.85). v29:
    the round device in the middle of the rear plate is a pistol port (rear views A and B: a plug in a horseshoe guard) -
    now in hull_details"""
    return [p for c, R, w, h, t in _visor_frames() for p in vision_port(c, R, w, h)[0]]

def roof_edge_port():
    """v34e (grey reference): the right-side vision device is a box standing on the roof's right edge, its slot in the
    outer face, its flap folded open onto the box's top (rod with two knuckles along the outer top edge). Returns
    (parts, dark slot) in hull coordinates"""
    xr = (SIDE_D - np.sin(a20) * ROOF) / np.cos(a20); W, H, D = 0.14, 0.10, 0.20
    c = np.array([xr - W / 2 + 0.01, ROOF - 0.005, VISOR_R_Z])
    parts = [rounded_slab(c, D, W, H + 0.005, 0.012, np.c_[[0, 0, 1.0], [1.0, 0, 0], [0, 1.0, 0]], bevel=0.004)]       # housing
    xo = c[0] + W / 2
    slot = box([xo - 0.002, ROOF + 0.045, VISOR_R_Z], [0.006, 0.03, 0.11])
    rod = np.array([xo - 0.004, ROOF + H + 0.006, VISOR_R_Z])
    parts.append(revolve([(-0.085, 0.005), (0.085, 0.005)], rod, [0, 0, 1.0], seg=8))
    parts += [revolve([(-0.012, 0.009), (0.012, 0.009)], rod + [0, 0, dz], [0, 0, 1.0], seg=8) for dz in (-0.06, 0.06)]
    parts.append(rounded_slab(rod + [-0.065, 0.0, 0], 0.17, 0.12, 0.006, 0.008, np.c_[[0, 0, 1.0], [-1.0, 0, 0], [0, 1.0, 0]], bevel=0.002))   # flap, open on the top
    return parts, slot

def pistol_port(c, n, up):
    """v29: a domed plug in a horseshoe guard open at the bottom (c on the plate, n its outward normal, up along the plate)"""
    n = np.asarray(n, float) / np.linalg.norm(n); up = np.asarray(up, float) / np.linalg.norm(up); side = np.cross(up, n)
    out = [revolve([(-0.003, 0.054), (0.009, 0.054), (0.011, 0.045), (0.026, 0.040), (0.036, 0.024), (0.040, 0.0)], c, n, seg=12)]
    rg, leg = 0.072, 0.04
    pts = [c - side * rg - up * leg] + [c + rg * (np.cos(a) * side + np.sin(a) * up) for a in np.radians(np.linspace(180, 0, 9))] + [c + side * rg - up * leg]
    out.append(tube([p + n * 0.010 for p in pts], 0.011, seg=5, closed=False, normal=n))
    return out

def rear_port():
    rear_n = np.array([0, np.sin(a10), -np.cos(a10)]); y = ROOF - 0.19; zr = REAR_Z - np.tan(a10) * (ROOF - y)
    return pistol_port(np.array([0.0, y, zr]), rear_n, np.array([0, np.cos(a10), np.sin(a10)]))

def dark_fittings():
    """dark openings on the hull: the driver's vision port, the right visor's slit, the fan dome's vent notches (v34)"""
    fr = _visor_frames()
    return [vision_port(c, R, w, h)[1] for c, R, w, h, t in fr] + pano_windows() + fan_notches()

if __name__ == '__main__':
    (V, F), planes = casemate()
    print('casemate verts', len(V), 'z', V[:, 2].min(), V[:, 2].max(), 'x', V[:, 0].min(), V[:, 0].max(), 'roof width at y', ROOF, 2 * (SIDE_D - np.sin(a20) * ROOF) / np.cos(a20))
    print('glacis top z', z_glacis_top, 'gun plate z', GUN_Z_PLATE, 'pivot', PIVOT)

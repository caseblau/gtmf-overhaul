"""SU-76M game mesh from the user's purchased model (Downloads\\wwii-soviet-su76-..., obj.rar and the textures inside fbx.glb), on the
game's T-70M running gear, re-laid at the model's own wheel positions.

  python su76_bought.py <t70 mesh> <obj.obj> <textures dir> <out dir> <zis3 mesh> [game diffuse, for the paint]

Frame: game = (-x, y - 0.868, z), metres (the OBJ is in centimetres).  From the model: hull, open casemate, interior,
fenders, fittings, spare parts, gun, gun housing and mantle.  From the game: road wheels, sprocket, idler, rollers, arms and
track as the T-70M's add-ins (su76_config.py).  su76_mesh.wheel_layout() and caret_layout() read the numbers set below.
"""
import sys, os, glob, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import azg2, geom, bought as B, su122_mesh as SM, su76_geom as G, su76_mesh as OLD

Y_OFF = -0.868
ATLAS = {'SU76_Hull_2': (0.0, 0.0, 0.75, 0.75), 'SU76_Hull_1': (0.0, 0.75, 0.5, 0.25)}
DARK_UV = np.array((0.875, 0.125))
MATERIAL = (b'su76m_dift', b'su76m_norsp')

# the model's own wheel centres (raw y + Y_OFF); the T-70M road wheel has the same 0.50 m diameter
G.TRACK_X = 1.20          # 10 Nov (user: wheels too far out): 6 cm in; the model's single disc stood at 1.256, its hub reaches 0.97
G.ROAD_Y = 0.31 + Y_OFF
G.ROAD_Z = [1.47, 0.87, 0.27, -0.33, -0.93, -1.54]
G.SPROCKET = (2.085, 0.685 + Y_OFF)
G.IDLER = (-2.055, 0.53 + Y_OFF)
G.ROLLER_Y = 0.81 + Y_OFF
G.ROLLER_Z = [1.21, 0.01, -1.23]

def to_game(V): V = V * 0.01; return np.c_[-V[:, 0], V[:, 1] + Y_OFF, V[:, 2]]

def tr(p): M = np.eye(4); M[3, :3] = p; return M

def build(t70_path, obj_path, zis3_path):
    T = SM.Src(t70_path); arm = OLD.arm_points(T)
    O = B.load_obj(obj_path, to_game, ATLAS)
    pieces = B.split(O['SU76_Hull_2']) + B.split(O['SU76_Hull_1'])
    print('pieces', len(pieces), 'tris', sum(len(q) for q in pieces))
    def gear(q):   # wheels, rollers, sprockets, idlers, arms between the fenders and the ground: the game's T-70M parts stand there
        lo, hi = q.lo(), q.hi(); c = q.centre(); s = hi - lo
        if abs(c[0]) > 0.95 and hi[1] < 0.17 and s[2] < 0.80 and s[0] < 0.60: return True
        if abs(c[0]) > 1.0 and hi[1] < 0.05 and s[2] < 0.90: return True            # sprocket teeth, idler bolts
        return abs(c[0]) > 0.75 and c[2] < -1.9 and hi[1] < -0.15 and len(q) <= 60   # idler crank fittings left floating by its removal
    keep = [q for q in pieces if not gear(q)]
    # the driver's hatch on the glacis: the raised trapezoid plate, moved into its own node (below)
    hatch = [q for q in keep if abs(q.centre()[0] + 0.065) < 0.03 and abs(q.centre()[2] - 1.50) < 0.04 and 80 < len(q) < 110]
    # 10 Nov (user: its vision port stayed floating): the vision device and handle on the lid go with it
    hl0, hh0 = hatch[0].lo(), hatch[0].hi()
    hatch += [q for q in keep if len(q) in (64, 40, 14) and hl0[0] < q.centre()[0] < hh0[0] and hl0[2] + 0.05 < q.centre()[2] < hh0[2] and hl0[1] - 0.05 < q.centre()[1] < hh0[1] + 0.03]
    # (user: the shells should lean on the insides): the upright rows along the left wall and right of the gun lean 8 deg toward their wall
    for q in keep:
        s_ = q.hi() - q.lo()
        if len(q) == 56 and abs(s_[1] - 0.911) < 0.02 and s_[0] < 0.1 and q.centre()[2] < -0.9:
            base = np.array([q.centre()[0], q.lo()[1], q.centre()[2]]); a = np.radians(8.0) * (1 if q.centre()[0] < 0 else -1)
            Rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1.0]])   # tilts the top toward -x (left) or +x (right)
            q.P[:] = (q.P - base) @ Rz.T + base; q.N[:] = q.N @ Rz.T
    keep = [q for q in keep if not any(q is h for h in hatch)]; print('driver hatch pieces', [len(h) for h in hatch])
    # the gun: everything on its axis between the mantle and the muzzle (not the fixed mantle, not the travel lock on the deck)
    bar = max((q for q in pieces if q.hi()[2] > 2.2 and abs(q.centre()[0]) < 0.4 and (q.hi() - q.lo())[0] < 0.3), key=lambda q: q.hi()[2])
    GX = bar.centre()[0]; BY = bar.centre()[1]
    def on_gun(q):
        c, lo, hi = q.centre(), q.lo(), q.hi(); s = hi - lo
        return q is not bar and abs(c[0] - GX) < 0.42 and lo[1] > BY - 0.50 and hi[1] < BY + 0.50 and -1.15 < lo[2] and hi[2] < 0.88 and s[0] < 0.72 and s[2] < 1.45
    # the raised travel lock on the deck: the barrel would pass through it when it traverses (it folds down in action)
    def lock(q): c, hi = q.centre(), q.hi(); return abs(c[0] - GX) < 0.26 and 0.85 < c[2] < 1.40 and hi[1] > 0.45 and q is not bar and (q.hi() - q.lo())[0] < 0.45
    locks = [q for q in keep if lock(q)]; keep = [q for q in keep if not any(q is k for k in locks)]; print('travel lock pieces', [len(k) for k in locks])
    moving = [q for q in keep if on_gun(q)]
    mantle = [q for q in moving if (q.hi() - q.lo())[0] > 0.60 and q.hi()[2] < 0.12]   # the curved plate the gun moves behind
    moving = [q for q in moving if not any(q is m for m in mantle)]
    print('gun x %.3f bore y %.3f; moving pieces %d (%d tris), barrel %d tris, fixed mantle %s' % (GX, BY, len(moving), sum(len(q) for q in moving), len(bar), [len(m) for m in mantle]))
    mz_model = -0.27           # the middle of the model's curved mantle plate (raw z -0.57 .. 0.03)
    # 9 Nov (user: the gun's parts stayed put; use the ZiS-3's gun): the model's barrel, breech and cradle go; the ZiS-3's cradle,
    # barrel and breech block come as add-ins (zis3 textures) in the ZiS-3's own relative frames.  The model's armoured sleeve in
    # front of the mantle stays on the elevating part; the gun mount's cheeks and fittings behind it traverse with the gun.
    # the model's own panoramic sight (post at x -0.53, head through the casemate's sight port at y 1.3 - 1.47) stays: the ZiS-3's
    # sight on its carriage stood 9 cm aside and 20 cm under the port (user, 9 Nov: misaligned).  It traverses, it does not elevate.
    def is_sight(q): c = q.centre(); return abs(c[0] + 0.50) < 0.08 and -0.90 < c[2] < -0.55 and 0.80 < c[1] < 1.50 and len(q) < 100
    sight = [q for q in keep if is_sight(q)]; moving = [q for q in moving if not is_sight(q)]
    behind = lambda q: q.centre()[2] < mz_model          # all of the model's gun behind the mantle: the ZiS-3's cradle and upper carriage replace it
    gun_drop = [q for q in moving if behind(q)]; moving = [q for q in moving if not behind(q)]
    moving = [q for q in moving if not (q.centre()[2] > mz_model and q.centre()[1] < BY - 0.25)]   # deck fittings in front of the mantle: fixed
    def mount(q):
        c = q.centre(); return (q is not bar and not any(q is s for s in sight) and not any(q is m for m in moving) and not any(q is m for m in gun_drop) and abs(c[0] - GX) < 0.25
                                and BY - 0.40 < c[1] < BY + 0.05 and -1.45 < c[2] < mz_model - 0.2 and float(np.max(q.hi() - q.lo())) < 1.6 and len(q) < 150)
    mounts = [q for q in keep if mount(q)]
    rails = mounts; trav = sight     # the model's mount clashed with the ZiS-3 cradle (user, 9 Nov): the ZiS-3's upper carriage (d_rama) stands there
    print('model sight pieces kept (traversing)', [len(q) for q in sight])
    print('ZiS-3 gun: model gun parts dropped %d, cradle rails dropped %d, mount parts traversing %d' % (len(gun_drop), len(rails), len(trav)))
    fixed = [q for q in keep if q is not bar and not any(q is m for m in moving) and not any(q is m for m in gun_drop) and not any(q is m for m in mounts) and not any(q is s for s in sight)]
    size = lambda q: float(np.max(q.hi() - q.lo()))
    # the opening under the hatch: a dark plate just under the lid's slope, seen only when it stands open
    # 9 Nov (user: the hatch showed black): the dark plate lay over the lid's own face, and the glacis under the lid is solid.  As on
    # the M3's visor: the opening is cut out of the glacis faces under the lid (picked by rays through it), a dark box behind it.
    H_ = B.join(hatch); c_ = H_.centre(); s_ = H_.hi() - H_.lo(); n0 = H_.N.reshape(-1, 3).mean(0); n0[0] = 0; n0 /= np.linalg.norm(n0)
    v_ = np.cross(n0, (1.0, 0, 0)); ha, hb = s_[0] / 2 - 0.06, float(np.hypot(s_[1], s_[2])) / 2 - 0.06
    cutn = 0; plate_n = []
    for k_, q in enumerate(fixed):
        under = set()
        for du in np.linspace(-ha, ha, 5):
            for dv in np.linspace(-hb, hb, 5):
                under.update(B.ray_faces(q, c_ + du * np.array([1.0, 0, 0]) + dv * v_ + n0 * 0.5, -n0, 0.3, 0.75)[0].tolist())
        if under:
            Pq = q.P[sorted(under)]; nq = np.cross(Pq[:, 1] - Pq[:, 0], Pq[:, 2] - Pq[:, 0]); plate_n.append(nq.sum(0))
            fixed[k_], n_ = B.cut_rect(q, c_, n0, (1.0, 0, 0), ha, hb, only=sorted(under)); cutn += n_
    gn = np.sum(plate_n, 0) if plate_n else n0; gn = gn / np.linalg.norm(gn)
    print('driver hatch opening: glacis faces cut', cutn, 'plate normal', np.round(gn, 3))
    fixed = fixed + [B.dark_box(c_ - gn * 0.02, gn, (1.0, 0, 0), ha, hb, 0.55, DARK_UV)]
    hull_all = B.join(fixed); mid = B.join([q for q in fixed if size(q) > 0.22 or len(q) > 180]); far = B.join([q for q in fixed if size(q) > 0.8])
    shell = B.join([q for q in fixed if size(q) > 1.0 and len(q) > 20])
    V, F = shell.plain(); cen = V[F].mean(1)[:, 1]
    H0 = OLD.hit(V, F[cen < 0.56], arm, OLD.hull_class); H1 = OLD.hit(V, F[cen >= 0.56], arm, 'cm_side')
    nodes = []
    def add(name, kind, parent, M, geo=None): nodes.append(dict(name=name, kind=kind, parent=parent, M=M, geo=geo or {}))
    def lods(p): g = p.gxt(); return {1: g, 2: g, 3: g}
    # 10 Nov (user: the crew sat on the floor): the game seats crew on the collision surface under their socket - the Marder's and the
    # Sd.Kfz. 251's seats are in their hit meshes.  The model's three stools (visible only) get solid blocks in ours, floor to seat top.
    stools = [((-0.56, -0.98), 0.11), ((0.30, -1.02), 0.06), ((-0.56, -1.84), 0.12)]   # gunner, commander, loader's seat on the rack
    HS = [OLD.hit(*geom.box((x, (top - 0.36) / 2, z), (0.27, top + 0.36, 0.27)), arm, OLD.hull_class) for (x, z), top in stools]
    add('d_hull', 4, None, np.eye(4), {0: B.cat([H0, H1] + HS), 1: hull_all.gxt(), 2: mid.gxt(), 3: far.gxt()})
    # ---- running gear holders (T-70 nodes at the model's positions)
    for name, tpl, p, kind in OLD.wheel_layout():
        M = T.local(tpl).copy(); M[3, :3] = p; add(name, 1, 'd_hull', M, {0: T.geo[(tpl, 0)]})
    for name, tpl, p, wheel in OLD.caret_layout():
        M = T.local(tpl).copy(); M[3, :3] = p; add(name, 1, 'd_hull', M, {0: T.geo[(tpl, 0)]})
    PW = {'d_hull': np.zeros(3)}
    def pbox(name, parent, p, size_=(0.35, 0.5, 0.35), cls='side'):
        Vb, Fb = geom.box((0, 0, 0), size_); add(name, 1, parent, tr(np.asarray(p, float) - PW[parent]), {0: OLD.hit(Vb, Fb, arm, cls)})
    def sock(name, parent, p, R=None):
        M = tr(np.asarray(p, float) - PW[parent])
        if R is not None: M[:3, :3] = R
        add(name, 0, parent, M)
    # ---- gun: the ZiS-3's.  Its frames: d_gun sits at GUN_D in the cradle (d_gunmask, the trunnion), the bore at BORE in d_gun, the
    # muzzle 1.43 m ahead of d_gun, the breech block at ZAT.  Laid so the bore runs where the model's did and the muzzle stands
    # where the model's stood; the trunnion then comes 9 cm behind the model's mantle centre.
    mz = mz_model; Zg = SM.Src(zis3_path)
    for nm in ('d_gunmask', 'd_gun', 'd_zatvor'): assert np.allclose(Zg.local(nm)[:3, :3], np.eye(3), atol=1e-3), nm
    GUN_D = Zg.local('d_gun')[3, :3].astype(float); ZAT = Zg.local('d_zatvor')[3, :3].astype(float); BORE = Zg.local('s_gun')[3, :3].astype(float)
    MUZ_L = float(Zg.geo[('d_gun', 1)][0][:, 2].max())
    G_GUN = np.array([GX - BORE[0], BY - BORE[1], bar.hi()[2] - MUZ_L]); G0 = G_GUN - GUN_D
    TRUN = G0; PW['s_rotation'] = PW['d_gunmask'] = PW['d_gun_rot'] = PW['d_gunmask_02'] = G0; PW['d_gun'] = G_GUN
    print('ZiS-3 trunnion', np.round(G0, 3), 'd_gun', np.round(G_GUN, 3), '(model mantle centre z %.2f)' % mz)
    add('s_rotation', 0, 'd_hull', tr(G0))
    if trav:
        tv = B.join(trav).moved(G0); add('d_gun_rot', 4, 's_rotation', np.eye(4), {**lods(tv), 0: OLD.hit(*tv.plain(), arm, 'mask')})
    RAMA_D = -Zg.local('d_gunmask')[3, :3].astype(float)            # the upper carriage in the cradle's frame (ZiS-3: cradle in d_rama)
    Vr, Fr = geom.box((0, 0, -0.2), (0.6, 0.4, 0.5))
    add('d_rama', 1, 's_rotation', tr(RAMA_D), {0: OLD.hit(Vr, Fr, arm, 'mask')})                         # holder of SU76M_RAMA: traverses
    mv = B.join(moving).moved(G0); arm_mv = B.join([q for q in moving if size(q) > 0.35]).moved(G0)
    add('d_gunmask', 1, 's_rotation', np.eye(4), {0: OLD.hit(*B.join([arm_mv]).plain(), arm, 'mask')})       # holder of SU76M_CRADLE
    add('d_gunmask_02', 4, 'd_gunmask', np.eye(4), lods(mv))                                                 # the model's armoured sleeve
    A3, F3 = Zg.geo[('d_gun', 3)] if ('d_gun', 3) in Zg.geo else Zg.geo[('d_gun', 2)]
    add('d_gun', 1, 'd_gunmask', tr(GUN_D), {0: OLD.hit(A3[:, :3], F3, arm, 'mask')})                       # holder of SU76M_BARREL
    Vz, Fz = geom.box((0, 0, 0), (0.14, 0.22, 0.14))
    add('d_zatvor', 1, 'd_gun', tr(ZAT), {0: OLD.hit(Vz, Fz, arm, 'mask')})                                 # holder of SU76M_BREECH
    sock('s_gun', 'd_gun', G_GUN + BORE)
    pbox('p_rothead', 's_rotation', TRUN + [0, -0.05, -0.30], (0.55, 0.60, 0.60), 'mask')
    pbox('p_rotgun', 'd_gunmask', TRUN + [0.0, 0.03, 0.30], (0.28, 0.36, 0.90), 'mask')
    # ---- driver's hatch, hinged on its top edge about local z (hatch axis 2; until 9 Nov axis 1, the vertical, so it spun flat):
    # x down the glacis into the lid, y out of it, z = -x world.  The dark opening is under it on the glacis.
    H = B.join(hatch); hl, hh = H.lo(), H.hi(); hinge = np.array([(hl[0] + hh[0]) / 2, hh[1], hl[2]])
    dn = H.centre() - hinge; dn[0] = 0; dn /= np.linalg.norm(dn); RH = np.array([dn, (0, dn[2], -dn[1]), (-1.0, 0, 0)])
    h_l = H.moved(hinge, RH); MH = tr(hinge); MH[:3, :3] = RH
    add('d_hatch_02', 4, 'd_hull', MH, {**lods(h_l), 0: OLD.hit(*h_l.plain(), arm, 'front')})
    # ---- crew: driver closed in the hull front, the three others in the open casemate
    pbox('p_driver', 'd_hull', (-0.22, 0.02, 1.05)); sock('s_driver', 'd_hull', (-0.22, 0.12, 1.02))
    sock('s_driver_out', 'd_hull', (-0.22, 0.56, 1.25)); sock('s_camera_driver', 'd_hull', ((hl[0] + hh[0]) / 2, hh[1] - 0.04, hl[2] + 0.05));   # 10 Nov: the slot near the top of his hatch (marked by the user)
    sock('s_driver_exit', 'd_hull', (-1.95, -0.30, 1.0))
    pbox('p_gunner', 'd_hull', (-0.56, 0.35, -0.98), (0.35, 0.80, 0.35)); sock('s_gunner', 'd_hull', (-0.56, 0.81, -0.98))   # seated on his stool (top 0.11, + 0.70)
    sock('s_camera_gunner', 's_rotation', (-0.528, 1.44, -0.66))     # the panoramic sight's head in the casemate port: traverses, no elevation
    # 9 Nov (user: the commander stood on the shells): as on the SU-76M, the commander at the front right beside the gun, at the
    # front plate's vision ports; the loader behind him by the upright shell rack (rear right)
    # The fighting compartment's floor is the hull bottom, y -0.36 (mapped with rays); the game's open half-track has its crew sockets
    # 0.88 above its floor, so 0.52 here (they were at 0.86 / 0.88: standing on the shell rack, shoulders over the walls).  Spots
    # chosen clear overhead: the front corner roof plates hang at y 1.26 - 1.29 ahead of z -0.9.
    # 9 Nov, round 2 (user: crew looks off, gunner should sit on his stool, sectors off): the model has three round stools - left at
    # the sight (top y 0.11, x -0.56 z -0.98), right beside the breech (top 0.06, x 0.42 z -1.11), rear left (top 0.12).  The gunner
    # sits on his (seated T-34 gunner: socket 0.14 over the seat), the commander stands on the right one, head over the plates, out
    # of the recoil, the loader stands at the rear between the left-wall rack and the upright rack (floor -0.36: socket 0.52).
    # user (9 Nov): the loader belongs at the stool on the left behind the breech (x -0.56, z -1.84): he works from there, on the
    # floor beside it (y 0.52, the standing loader animation), facing the breech
    # Round 3 (user): seated crew sit, standing crew look out.  The anims table: marder_loader sits when idle (apc_sit_01), loads
    # (gun_load_01), stands to look out (apc_gun_out_01, at the out socket); apc_commander sits idle and stands out; apc_shoter sits
    # leaning on the handwheels.  The seated loader showed right at 0.40 over his stool (in game), so seated sockets: stool + 0.40.
    # 10 Nov (user: the loader clipped through the hull loading): he stands where the towed ZiS-3's loader stands relative to the same gun
    # (ZiS-3: s_loader 0.576 right, 0.148 up, 1.512 behind its cradle), so gun_load_01 reaches the breech; idle he sits on the shell
    # rack behind him (collision block, top 0.38)
    # 10 Nov (user): idle he sits on his stool on the left, loading he loads: one socket serves both, so the stool's spot moved
    # forward-in to where the breech is in reach (the model's stool at -0.56, -1.84 is 1.2 m behind the breech)
    LDR = np.array([-0.56, 0.60, -1.84])   # 10 Nov (user): on the model's rear-left stool (top 0.12 + 0.48); loading plays from there
    pbox('p_loader', 'd_hull', LDR - [0, 0.45, 0], (0.35, 0.80, 0.35)); Rl_ = np.array([[0.966, 0, 0.259], [0, 1.0, 0], [-0.259, 0, 0.966]]); sock('s_loader', 'd_hull', LDR, Rl_.T)   # turned 15 deg toward the breech
    sock('s_loader_out', 'd_hull', (LDR[0], 0.52, LDR[2]))
    sock('s_camera_loader', 'd_hull', (-0.694, 1.40, -0.80))                # 10 Nov: the top-left periscope's head window (was 15 cm low, inside its body)
    sock('s_camera_loader_01', 'd_hull', (-0.93, 1.116, -1.448), np.array([[0, 0, 1.0], [0, 1.0, 0], [-1.0, 0, 0]]))   # left wall vision slit
    # user: the commander sits at the right on his stool and looks through the right front periscope; the loader's port is in the
    # left wall beside his stool
    pbox('p_commander', 'd_hull', (0.30, 0.20, -1.02), (0.35, 0.80, 0.35)); sock('s_commander', 'd_hull', (0.30, 0.76, -1.02))   # seated under his periscope, head at its window (seat block below)
    add('d_hatch_03', 0, 'd_hull', tr((0.30, 1.45, -1.02)))   # the commander's invisible hatch: buttoned / head out   # right stool, top 0.06, + 0.70
    sock('s_commander_out', 'd_hull', (0.32, 0.52, -1.05))                  # unbuttoned: stands at the top (front right) periscope
    sock('s_camera_commander', 'd_hull', (0.304, 1.40, -0.84))              # buttoned: the top-right periscope's head window
    sock('s_camera_commander_01', 'd_hull', (0.78, 1.116, -1.448), np.array([[0, 0, -1.0], [0, 1.0, 0], [1.0, 0, 0]]))   # right wall vision slit
    sock('s_camera_gunner_01', 'd_hull', (-0.775, 1.02, -0.40))            # the round vision port on the casemate's front left (marked)
    sock('s_camera_commander_out', 'd_hull', (0.304, 1.55, -0.95))         # unbuttoned: his head over the top-right periscope
    for nm, p in (('s_gunner_exit', (-1.95, -0.30, -1.2)), ('s_loader_exit', (1.95, -0.30, -1.2)), ('s_commander_exit', (0.4, -0.30, -2.95))): sock(nm, 'd_hull', p)
    # ---- damage boxes: engines on the right of the hull front, transmission in the nose, fuel at the rear, ammunition racks
    pbox('p_engine', 'd_hull', (0.52, 0.05, 0.60), (0.55, 0.60, 0.70)); pbox('p_engine_02', 'd_hull', (0.52, 0.05, -0.02), (0.55, 0.60, 0.55))
    pbox('p_transm', 'd_hull', (0.0, -0.25, 1.85), (1.40, 0.45, 0.50)); pbox('p_accum', 'd_hull', (-0.60, -0.20, 0.55), (0.30, 0.25, 0.25))
    pbox('p_fueltank_01', 'd_hull', (0.80, 0.16, -1.70), (0.48, 0.46, 0.60))
    pbox('p_ammo_01', 'd_hull', (-0.88, 0.15, -1.15), (0.30, 0.46, 0.90)); pbox('p_ammo_02', 'd_hull', (0.86, 0.22, -0.75), (0.34, 0.60, 0.50))
    pbox('p_radio', 'd_hull', (0.78, 0.68, -1.20), (0.32, 0.24, 0.26))
    # ---- headlight on the left fender, sockets
    add('d_light_01', 1, 'd_hull', tr((-1.12, 0.43, 1.06)), {0: T.geo[('d_light_01', 0)]} if ('d_light_01', 0) in T.geo else {})
    add('s_light_01', 0, 'd_light_01', tr((0.0, 0.0, 0.20)))
    sock('s_fire_01', 'd_hull', (0.0, 0.30, -1.30)); sock('s_fire_02', 'd_hull', (-0.25, 0.10, 1.10)); sock('s_fire_03', 'd_hull', (0.52, 0.40, 0.30))
    Rs = T.local('s_smoke_01')[:3, :3]   # 10 Nov (user: smoke the wrong way): the T-70's rear-outward exhaust direction (local z)
    sock('s_smoke_01', 'd_hull', (1.21, 0.60, -1.95), Rs); sock('s_smoke_02', 'd_hull', (1.33, 0.60, -1.95), Rs)
    sock('s_smk_gun', 'd_hull', (0.0, 1.35, -1.30))
    sock('s_trace_01', 'd_hull', (G.TRACK_X, G.ROAD_Y - 0.30, 0.0)); sock('s_trace_02', 'd_hull', (-G.TRACK_X, G.ROAD_Y - 0.30, 0.0))
    sock('s_pricep', 'd_hull', (0.0, -0.30, -2.25)); sock('s_water_line', 'd_hull', (0.0, 0.30, -0.60))
    Rr = T.local('s_mark_01')[:3, :3]; Rl = T.local('s_mark_02')[:3, :3]; ym = 0.92; xm = 1.03
    sock('s_mark_01', 'd_hull', (xm, ym, -1.00), Rr); sock('s_mark_01f', 'd_hull', (xm, ym, -1.20), Rr)
    sock('s_mark_02', 'd_hull', (-xm, ym, -1.20), Rl); sock('s_mark_02f', 'd_hull', (-xm, ym, -1.00), Rl)
    des = [(-0.60, 0.58, 0.90), (0.60, 0.58, 0.95), (-0.45, 0.58, 0.20), (-1.25, 0.24, 0.60), (1.25, 0.24, 0.60), (-1.25, 0.24, 1.40)]
    for k, p in enumerate(des, 1): sock('s_des_%02d' % k, 'd_hull', p)
    for k, p in enumerate([(-1.95, -0.3, 0.4), (1.95, -0.3, 0.4), (-1.95, -0.3, 1.4)], 1): sock('s_des_out_%02d' % k, 'd_hull', p)
    return nodes

def textures(tex, out, ref=None):
    def f(pat): return glob.glob(os.path.join(tex, pat))[0]
    layers = []
    for rect, k in ((ATLAS['SU76_Hull_2'], 'Hull_2'), (ATLAS['SU76_Hull_1'], 'hull_1')):
        orm = f('mat_SU76_%s_AO*' % k)
        layers.append((rect, f('mat_SU76_%s_Diffuse.png' % k), f('mat_SU76_%s_Normal.png' % k), (orm, 0), (orm, 1)))
    dif, nrm = B.build_textures(layers, None, None, ref)
    B.write_textures(dif, nrm, out, 'su76m')

if __name__ == '__main__':
    t70, obj, tex, out, zis3 = sys.argv[1:6]; ref = sys.argv[6] if len(sys.argv) > 6 else None
    nodes = build(t70, obj, zis3)
    data = B.rename_material(SM.assemble(nodes, t70), (b't70m_42_dift', b't70m_42_norsp'), MATERIAL)
    for stem, node, blob in OLD.addin_meshes(zis3, zis3):          # the ZiS-3 cradle, barrel and breech block
        open(os.path.join(out, stem + '.mesh.loc_def.bin'), 'wb').write(blob); print('add-in', stem, 'on', node)
    p = os.path.join(out, 'su76m.mesh.loc_def.bin'); open(p, 'wb').write(data)
    m = azg2.read(p); print('written', p, len(data), 'bytes;', len(m['nodes']), 'nodes;', [(b['tag'], b['nv'], b['ni']) for b in m['blocks']], [mt['name'] for mt in m['materials']])
    textures(tex, out, ref); print('textures written')

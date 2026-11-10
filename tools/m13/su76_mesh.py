"""Build the SU-76M game mesh (AZG2) on the Mius-Front T-70's skeleton, with the ZiS-3's barrel and breech as add-ins.

  python su76_mesh.py <t70 mesh> <zis3 mesh> <out su76m.mesh.loc_def.bin> [preview.obj]

From the T-70 (t70, the game's own file): the running-gear holder nodes (sprocket, road wheels, idler, return rollers,
bogie-arm holders d_caret_*) and their hit shapes - re-laid for the SU-76M's longer, wider chassis: six road wheels a
side instead of five, track centres at x +-1.228 (T-70 +-1.076); the tow hooks, the headlight and horn, the shovel and
crowbar, and the spare road wheel (stood up on the rear plate). The wheels, sprockets, idlers, rollers, bogie arms and
the tracks themselves are the T-70M's add-ins (T70M_WHEEL / STAR / LAZY / ROLLER / LCARET / RCARET, track t70_260) and are
only named by the config. New (su76_geom.py): the hull, the open casemate, the fenders, boxes, exhaust and silencer, the
rail frame, the interior, and the gun mount - v2: the hollow mantle fixed to the hull, the gun traversing on its face (s_rotation, +-15 deg) and
elevating (d_gunmask, -3 .. +25 deg: the armoured housing over the recoil gear, the cradle and the recoil guard). The barrel and breech block are the ZiS-3's own geometry and texture,
attached through the addins table (SU76M_BARREL on d_gun, SU76M_BREECH on d_zatvor), as the SU-122 does with the M-30.
One material - the T-70's (t70m_42_dift); armour-map UVs taken from the T-70's own hit meshes per plate class.
"""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import azg2, geom, uvtools as U, su76_geom as G
import su122_mesh as SM            # vertex codecs, Src, assemble / assemble_addin (shared AZG2 writer)

# ---------------------------------------------------------------- texture areas on t70m_42_dift
# v1: chosen from the T-70 hull's own unwrap without the texture in hand (the user is to extract it): the middle of the
# hull side-plate island (u 0.267..0.939, v 0.285..0.454 on the T-70, ~0.18 uv per metre), away from its ends
PLATE_RECT = (0.0, 0.0, 1.0, 0.875); PLATE_SCALE = 0.18                # v3: the SU-76M's own texture (su76_texture.py)
TEXEL_UV = (0.5, 0.4)
BRASS_UV = (0.1875, 0.96875); STEEL_UV = (0.3125, 0.96875)                # v4 (su76_texture.py strips)
MATERIAL = (b'su76m_dift', b'su76m_norsp')                              # v3: replaces the T-70's t70m_42_dift / _norsp

def rename_material(data):
    out = bytearray(data)
    for old, new in ((b't70m_42_dift', MATERIAL[0]), (b't70m_42_norsp', MATERIAL[1])):
        i = 0
        while True:
            i = out.find(old + b'\0', i)
            if i < 0: break
            out[i:i + len(old)] = new.ljust(len(old), b'\0'); i += len(old)
    return bytes(out)

def plate(V, F):
    Vo, Fo, UV = U.plate_uv(V, F, PLATE_RECT, PLATE_SCALE, jitter=True); return SM.new_gxt(Vo, Fo, UV)

def smooth(V, F, crease=40.0):
    Vo, Fo, UV = U.plate_uv(V, F, PLATE_RECT, PLATE_SCALE, jitter=False)
    return SM.new_gxt(Vo, Fo, UV, U.smooth_flat(Vo, Fo, crease))

def texel(V, F, smooth_deg=60.0, uv=TEXEL_UV):
    Vo = V[F].reshape(-1, 3); Fo = np.arange(len(Vo)).reshape(-1, 3)
    return SM.new_gxt(Vo, Fo, np.tile(uv, (len(Vo), 1)), U.smooth_normals(V, F, Vo, smooth_deg))

def round_part(V, F, origin, axis, crease=50.0):
    Vo, Fo, UV = U.cyl_uv(V, F, origin, axis, PLATE_RECT); return SM.new_gxt(Vo, Fo, UV, U.smooth_normals(V, F, Vo, crease))

def cat(lst):
    As, Fs, o = [], [], 0
    for A, F in lst:
        if A is None or not len(F): continue
        As.append(A); Fs.append(F + o); o += len(A)
    return (np.vstack(As), np.vstack(Fs)) if As else None

# ---------------------------------------------------------------- armour map (arm_t70m_42_dift) UVs from the T-70 hit meshes
def arm_points(T):
    out = {}
    for node, picks in (('d_hull', dict(glacis=((0, 0.5, 0.86), (0, 0.3, 1.8)), side=((1, 0, 0), (0.9, 0.1, 0.0)),
                                         roof=((0, 1, 0), (0.3, 0.53, -0.6)), rear=((0, 0, -1), (0, 0.2, -2.1)),
                                         belly=((0, -1, 0), (0, -0.56, 0.0)))),
                        ('d_head', dict(turret=((0, 0.3, 0.95), (0, 0.8, 0.6))))):
        A, F = T.geo[(node, 0)]; P = A[:, :3]; n = geom.normals(P, F); c = P[F].mean(1); uv = A[F][:, :, 6:8].mean(1)
        W = T.node(node)['world'][3, :3]
        for k, (nrm, at) in picks.items():
            nv = np.asarray(nrm, float); nv /= np.linalg.norm(nv)
            s = n @ nv - 0.15 * np.linalg.norm(c + W - np.asarray(at, float), axis=1)
            out[k] = tuple(uv[int(np.argmax(s))])
    # SU-76M plates mapped onto T-70 plates of (nearly) the same thickness: upper / lower front 35 / 25 mm -> T-70 glacis,
    # hull sides and rear 15 mm -> T-70 side (15), casemate front 25 mm -> T-70 rear plate (25), casemate sides 10 mm ->
    # T-70 roof (10), deck 7 mm -> T-70 roof, belly -> T-70 belly, gun shield and housing -> T-70 turret front
    return dict(front=out['glacis'], side=out['side'], rear=out['side'], cm_front=out['rear'], cm_side=out['roof'],
                roof=out['roof'], belly=out['belly'], mask=out['turret'])

def hit(V, F, arm, cls):
    """PNTl rows: cls = a class name, or a function normal -> class name"""
    n = geom.normals(V, F); Vf = V[F].reshape(-1, 3)
    T = np.array([arm[cls(k) if callable(cls) else cls] for k in n for _ in range(3)])
    return np.c_[Vf, np.repeat(n, 3, axis=0), T], np.arange(len(Vf)).reshape(-1, 3)

def hull_class(n):
    if n[1] < -0.9: return 'belly'
    if n[1] > 0.9: return 'roof'
    if n[2] > 0.3: return 'front'
    if n[2] < -0.5: return 'rear'
    return 'side'

def tr(p): M = np.eye(4); M[3, :3] = p; return M

# ---------------------------------------------------------------- running gear layout
def wheel_layout():
    """[(name, template T-70 node, (x, y, z))] - left side first (01 sprocket, 02-07 road wheels front to rear, 08 idler,
    09-11 return rollers front to rear), then the right side (12 sprocket, 13-18, 19 idler, 20-22), as on the T-70
    (01 sprocket, 02-06, 07 idler, 08-10 rollers | 11 sprocket, 12-16, 17 idler, 18-20 rollers)"""
    out = []
    for s, base, tpl in ((-1, 0, dict(star='d_wheel_01', road='d_wheel_03', lazy='d_wheel_07', roller='d_wheel_08')),
                         (1, 11, dict(star='d_wheel_11', road='d_wheel_13', lazy='d_wheel_17', roller='d_wheel_18'))):
        x = s * G.TRACK_X; k = base + 1
        out.append(('d_wheel_%02d' % k, tpl['star'], (x, G.SPROCKET[1], G.SPROCKET[0]), 'star')); k += 1
        for z in G.ROAD_Z: out.append(('d_wheel_%02d' % k, tpl['road'], (x, G.ROAD_Y, z), 'road')); k += 1
        out.append(('d_wheel_%02d' % k, tpl['lazy'], (x, G.IDLER[1], G.IDLER[0]), 'lazy')); k += 1
        for z in G.ROLLER_Z: out.append(('d_wheel_%02d' % k, tpl['roller'], (x, G.ROLLER_Y, z), 'roller')); k += 1
    return out

CARET_OFF = np.array([0.119, 0.067, 0.292])     # T-70: bogie-arm holder d_caret_01 relative to its wheel d_wheel_02 (left; x mirrored)

def caret_layout():
    out = []; k = 1
    for name, tpl, p, kind in wheel_layout():
        if kind != 'road': continue
        s = np.sign(p[0]); q = np.array(p) + CARET_OFF * [-s, 1, 1]
        out.append(('d_caret_%02d' % k, 'd_caret_01' if s < 0 else 'd_caret_06', q, name)); k += 1
    return out

# ---------------------------------------------------------------- build
def build(t70_path, zis3_path):
    T = SM.Src(t70_path); Z = SM.Src(zis3_path); arm = arm_points(T)
    nodes = []
    def add(name, kind, parent, M, geo=None):
        nodes.append(dict(name=name, kind=kind, parent=parent, M=M, geo=geo or {}))
    # ---- d_hull
    main = [G.hull_front(), G.hull_rear_low()] + G.hull_rear_walls()
    cm_sides = G.casemate_sides(); cm_front = G.casemate_front(); pl = G.plinth()
    H0 = [hit(V, F, arm, hull_class) for V, F in main] + [hit(V, F, arm, 'cm_side') for V, F in cm_sides] \
         + [hit(V, F, arm, 'cm_front') for V, F in cm_front] + [hit(*pl, arm, 'cm_front')]
    L1 = [plate(V, F) for V, F in main + cm_sides + cm_front + [pl]]
    det = [plate(V, F) for V, F in G.deck_hatches() + G.fenders() + G.fender_boxes() + G.rear_fittings() + G.interior()]
    ex = G.exhaust(); det.append(smooth(*ex[0], 40.0)); det.append(round_part(*ex[1], G.SILENCER['c'], (0, 0, 1.0)))
    det += [smooth(*ex[2], 40.0)] + [plate(v, f) for v, f in ex[3:]]
    rails = [smooth(v, f, 50.0) for v, f in G.rail_frame()]
    fine = [smooth(v, f, 50.0) for v, f in G.front_fittings()]
    # v4: ammunition in the racks (brass cases, steel projectiles), the tarpaulin roll, bolt rows
    ammo = []
    for (vc, fc), (vs, fs) in G.ammo_rounds(): ammo += [texel(vc, fc, 50.0, BRASS_UV), texel(vs, fs, 50.0, STEEL_UV)]
    det += ammo + [smooth(v, f, 50.0) for v, f in G.tarp_roll()]
    bolts = [texel(v, f, 70.0) for v, f in G.bolt_rows()]
    base, whip = G.antenna()
    hull = {0: cat(H0), 1: cat(L1 + det + bolts + rails + fine + [smooth(*base, 40.0), texel(*whip)]),
            2: cat(L1 + det + rails + [smooth(*base, 40.0)]),
            3: cat([plate(V, F) for V, F in main + cm_sides + cm_front] + [plate(V, F) for V, F in G.fenders()])}
    add('d_hull', 4, None, np.eye(4), hull)
    # ---- running gear holders (T-70 nodes, re-laid)
    for name, tpl, p, kind in wheel_layout():
        M = T.local(tpl).copy(); M[3, :3] = p
        add(name, 1, 'd_hull', M, {0: T.geo[(tpl, 0)]})
    for name, tpl, p, wheel in caret_layout():
        M = T.local(tpl).copy(); M[3, :3] = p
        add(name, 1, 'd_hull', M, {0: T.geo[(tpl, 0)]})
    # ---- kept T-70 fittings, moved onto the SU-76M
    def keep(name, p, R=None, new_name=None, parent='d_hull'):
        M = T.local(name).copy(); M[3, :3] = p
        if R is not None: M[:3, :3] = R
        g = {L: T.geo[(name, L)] for L in range(4) if (name, L) in T.geo}
        add(new_name or name, T.node(name)['kind'], parent, M, g)
    keep('d_kryuk_01', (-0.62, -0.34, 2.24)); keep('d_kryuk_02', (0.62, -0.34, 2.24)); keep('d_kryuk_03', (0.0, -0.30, -2.17))
    keep('d_light_01', (-0.86, 0.60, 1.16)); keep('d_signal', (-0.62, 0.56, 1.14))
    fy = G.FENDER['y'] + G.FENDER['t']
    keep('d_lopata', (1.25, fy + 0.048, 0.35)); keep('d_breakage', (1.25, fy + 0.049, -0.45))
    # spare road wheel stood up on the rear plate, left (T-70: lying on the engine deck, axis vertical)
    # spare road wheel on the rear plate, left: v3 a holder for the T-70M road-wheel add-in (T70M_WHEEL, its own texture);
    # local x (the add-in's axle) along world z
    Msp = tr((-0.70, 0.20, G.Z_REAR - 0.07)); Msp[:3, :3] = np.array([[0, 0, 1.0], [0, 1.0, 0], [-1.0, 0, 0]])
    add('d_wheel_23', 1, 'd_hull', Msp, {0: T.geo[('d_wheel_03', 0)]})
    # light socket in front of the headlight (child of the light, T-70 offset)
    add('s_light_01', 0, 'd_light_01', tr(T.node('s_light_01')['world'][3, :3] - T.node('d_light_01')['world'][3, :3]))
    # ---- driver's hatch (d_hatch_02): on the glacis left of centre, hinged on its top edge (local x)
    parts, hinge = G.driver_hatch()
    Vw, Fw = geom.merge(*parts); Vl = Vw - hinge
    lod = plate(Vl, Fw); Vp, Fp = parts[0]
    add('d_hatch_02', 4, 'd_hull', tr(hinge), {0: hit(Vp - hinge, Fp, arm, 'front'), 1: lod, 2: lod, 3: plate(Vp - hinge, Fp)})
    # ---- gun mount (v2): the mantle is a hollow hood FIXED to the hull (user: "the gun mantle is not fixed to the hull");
    # s_rotation (traverse) and d_gunmask (elevation: housing, cradle, recoil guard) pivot on its face; the breech and the
    # recoil guard sit free behind it in the fighting compartment (v1 buried them in a solid traversing block)
    old_ax = np.array([G.TRAV_X, G.BORE_Y, G.TRAV_Z])
    shell = [plate(v, f) for v, f in G.mantle_shell()] + [smooth(v + old_ax, f, 50.0) for v, f in G.mantlet_details()]
    shell += [plate(v, f) for v, f in G.mantle_collar()]                    # v3: flared collar to the notch edges
    shell += [plate(v, f) for v, f in G.gun_curtain()]                      # v6: fixed curtain behind the face opening
    Vo, Fo = G.mantle_outer()
    hull[0] = cat([hull[0], hit(Vo, Fo, arm, 'mask')]); hull[1] = cat([hull[1]] + shell); hull[2] = cat([hull[2]] + shell[:3])
    hull[3] = cat([hull[3], plate(Vo, Fo)])
    piv = np.array([G.TRAV_X, G.BORE_Y, G.PIV_Z])
    add('s_rotation', 0, 'd_hull', tr(piv))
    Vh, Fh = G.housing(); hh = plate(Vh, Fh)
    hb = [smooth(v, f, 50.0) for v, f in G.housing_bolts()]
    cr = [plate(v, f) for v, f in G.gun_cradle()]
    cr += [smooth(v - G.TRUN, f, 40.0) for v, f in G.gun_cradle_detail()]   # v4: sector, panoramic sight, guard shield, cradle sides
    seat = cat([plate(v - piv, f) for v, f in G.gunner_seat()] + [smooth(v - piv, f, 40.0) for v, f in G.gun_gear()])   # v4: + pedestal, handwheels
    seat = cat([seat] + [plate(v - piv, f) for v, f in G.gun_cheeks()])     # v6: cheeks beside the opening, traverse with the gun
    add('d_gunseat', 3, 's_rotation', np.eye(4), {1: seat, 2: seat})
    add('d_gunmask', 4, 's_rotation', tr(G.TRUN - piv), {0: hit(Vh, Fh, arm, 'mask'), 1: cat([hh] + hb + cr), 2: cat([hh] + cr), 3: hh})
    # the ZiS-3's barrel: d_gun placed so the muzzle is at z 2.50 (5.00 m overall); its local frame as on the towed gun
    z_sg = Z.local('s_gun')[3, :3]                                   # muzzle socket relative to d_gun
    gun_p = np.array([G.GUN_X, G.BORE_Y, G.MUZZLE_Z]) - z_sg
    def hit_only(name):
        A, F = Z.geo[(name, 0)]; A = A.copy(); A[:, 6:8] = arm['mask']; return {0: (A, F)}
    add('d_gun', 1, 'd_gunmask', tr(gun_p - G.TRUN), hit_only('d_gun'))
    add('d_zatvor', 1, 'd_gun', Z.local('d_zatvor'), hit_only('d_zatvor'))
    add('s_gun', 0, 'd_gun', Z.local('s_gun'))
    PW = {'d_hull': np.zeros(3), 's_rotation': piv, 'd_gunmask': G.TRUN, 'd_gun': gun_p}
    def pbox(name, parent, p, size=(0.35, 0.5, 0.35), cls='side'):
        V, F = geom.box((0, 0, 0), size); add(name, 1, parent, tr(np.asarray(p, float) - PW[parent]), {0: hit(V, F, arm, cls)})
    def sock(name, parent, p, R=None):
        M = tr(np.asarray(p, float) - PW[parent])
        if R is not None: M[:3, :3] = R
        add(name, 0, parent, M)
    pbox('p_rothead', 's_rotation', piv + [0, -0.05, -0.30], (0.55, 0.60, 0.60), 'mask')
    pbox('p_rotgun', 'd_gunmask', G.TRUN + [0.015, 0.03, 0.30], (0.28, 0.36, 0.90), 'mask')
    # ---- crew: driver (front, closed), gunner (left of the gun), loader (right), commander (right rear) - open top
    pbox('p_driver', 'd_hull', (-0.22, 0.02, 1.05)); sock('s_driver', 'd_hull', (-0.22, 0.12, 1.02))
    sock('s_driver_out', 'd_hull', (-0.22, 0.52, 1.25))
    sock('s_camera_driver', 'd_hull', (-0.20, 0.40, 1.36))
    sock('s_driver_exit', 'd_hull', (-1.95, -0.30, 1.0))
    pbox('p_gunner', 's_rotation', (G.GUN_X - 0.42, 0.40, -0.95), (0.35, 0.80, 0.35))
    sock('s_gunner', 's_rotation', (G.GUN_X - 0.42, 0.86, -0.95))
    sock('s_camera_gunner', 'd_gunmask', (G.GUN_X - 0.27, 1.02, -0.92))       # v4: at the panoramic sight's eyepiece
    pbox('p_loader', 'd_hull', (0.32, 0.40, -1.15), (0.35, 0.80, 0.35)); sock('s_loader', 'd_hull', (0.32, 0.86, -1.15))
    pbox('p_commander', 'd_hull', (0.40, 0.40, -1.75), (0.35, 0.80, 0.35)); sock('s_commander', 'd_hull', (0.40, 0.88, -1.75))
    for nm, p in (('s_gunner_exit', (-1.95, -0.30, -1.2)), ('s_loader_exit', (1.95, -0.30, -1.2)),
                  ('s_commander_exit', (0.4, -0.30, -2.95))):
        sock(nm, 'd_hull', p)
    # ---- damage boxes: two GAZ-202 engines on the right, transmission in the nose, fuel at the rear, ammunition racks
    pbox('p_engine', 'd_hull', (0.52, 0.05, 0.60), (0.55, 0.60, 0.70)); pbox('p_engine_02', 'd_hull', (0.52, 0.05, -0.02), (0.55, 0.60, 0.55))
    pbox('p_transm', 'd_hull', (0.0, -0.25, 1.85), (1.40, 0.45, 0.50)); pbox('p_accum', 'd_hull', (-0.60, -0.20, 0.55), (0.30, 0.25, 0.25))
    pbox('p_fueltank_01', 'd_hull', (0.80, 0.16, -1.70), (0.48, 0.46, 0.60))
    pbox('p_ammo_01', 'd_hull', (-0.88, 0.15, -1.15), (0.30, 0.46, 0.90)); pbox('p_ammo_02', 'd_hull', (0.86, 0.22, -0.75), (0.34, 0.60, 0.50))
    pbox('p_radio', 'd_hull', (0.78, 0.68, -1.20), (0.32, 0.24, 0.26))
    # ---- sockets: fire, smoke (silencer tail), tracks, tow, marks, riders, water line
    sock('s_fire_01', 'd_hull', (0.0, 0.30, -1.30)); sock('s_fire_02', 'd_hull', (-0.25, 0.10, 1.10)); sock('s_fire_03', 'd_hull', (0.52, 0.40, 0.30))
    sock('s_smoke_01', 'd_hull', (1.17, 0.58, -2.02)); sock('s_smoke_02', 'd_hull', (1.33, 0.58, -2.02))
    sock('s_smk_gun', 'd_hull', (0.0, 1.35, -1.30))
    sock('s_trace_01', 'd_hull', (G.TRACK_X, -0.864, 0.0)); sock('s_trace_02', 'd_hull', (-G.TRACK_X, -0.864, 0.0))
    sock('s_pricep', 'd_hull', (0.0, -0.30, -2.20)); sock('s_water_line', 'd_hull', (0.0, 0.30, -0.60))
    # tactical numbers on the casemate sides (T-70 socket orientation: local z points outward)
    Rr = T.local('s_mark_01')[:3, :3]; Rl = T.local('s_mark_02')[:3, :3]
    ym = 0.95; xm = G.side_x(ym) + 0.004
    sock('s_mark_01', 'd_hull', (xm, ym, -1.00), Rr); sock('s_mark_01f', 'd_hull', (xm, ym, -1.20), Rr)
    sock('s_mark_02', 'd_hull', (-xm, ym, -1.20), Rl); sock('s_mark_02f', 'd_hull', (-xm, ym, -1.00), Rl)
    des = [(-0.60, G.Y_DECK, 0.90), (0.60, G.Y_DECK + 0.01, 0.95), (-0.45, G.Y_DECK, 0.20), (-1.25, G.FENDER['y'] + 0.02, 0.60),
           (1.25, G.FENDER['y'] + 0.02, 0.60), (-1.25, G.FENDER['y'] + 0.02, 1.40)]
    for k, (x, y, z) in enumerate(des, 1): sock('s_des_%02d' % k, 'd_hull', (x, y + 0.05, z))
    for k, p in enumerate([(-1.95, -0.3, 0.4), (1.95, -0.3, 0.4), (-1.95, -0.3, 1.4)], 1): sock('s_des_out_%02d' % k, 'd_hull', p)
    return nodes

CRADLE_CUT_Z = 0.40     # cradle-local z: 0.40 m ahead of the trunnion, just inside the front of the mantle (su76_bought lays it out)
RAMA_CUT_Z = 0.28       # upper-carriage-local z: the mantle's front

def addin_meshes(zis3_path, template):
    """the ZiS-3's barrel (d_gun) and breech block (d_zatvor) as add-ins (the breech has no far LOD - LOD2 reused)"""
    Z = SM.Src(zis3_path); out = []
    cut = {'d_gunmask': CRADLE_CUT_Z, 'd_rama': RAMA_CUT_Z}   # front ends inside the SU-76M's mantle and sleeve would poke out of them
    for stem, node in (('su76m_rama', 'd_rama'), ('su76m_cradle', 'd_gunmask'), ('su76m_barrel', 'd_gun'), ('su76m_breech', 'd_zatvor')):
        geo = {}
        for L in (1, 2, 3):
            geo[L] = Z.geo[(node, L)] if (node, L) in Z.geo else geo[L - 1]
            if node in cut:
                A, F = geo[L]; F2 = np.asarray(F).reshape(-1, 3); ok_ = A[F2, 2].max(1) <= cut[node]
                if node == 'd_rama':
                    ok_ &= ~((A[F2, 2].max(1) > -0.15) & (np.abs(A[F2, 0]).max(1) > 0.25))   # outer trunnion brackets: through the casemate sides
                    ok_ &= ~((A[F2, 0].max(1) < -0.17) & (A[F2, 1].min(1) > 0.06))           # its panoramic sight: the SU-76M's own stands in the casemate's port
                geo[L] = (A, F2[ok_])   # assemble_addin flattens F
        out.append((stem, node, SM.assemble_addin(node, geo, template)))
    return out

if __name__ == '__main__':
    t70, zis3, out = sys.argv[1:4]
    nodes = build(t70, zis3)
    data = rename_material(SM.assemble(nodes, t70))
    open(out, 'wb').write(data)
    m = azg2.read(out)
    print('written', out, len(data), 'bytes;', len(m['nodes']), 'nodes;', [(b['tag'], b['nv'], b['ni']) for b in m['blocks']], [mt['name'] for mt in m['materials']])
    for stem, node, blob in addin_meshes(zis3, zis3):
        p = os.path.join(os.path.dirname(os.path.abspath(out)), stem + '.mesh.loc_def.bin'); open(p, 'wb').write(blob)
        a = azg2.read(p); print('written', p, len(blob), 'bytes; holder', node, [(b['tag'], b['nv'], b['ni']) for b in a['blocks']], [mt['name'] for mt in a['materials']])
    if len(sys.argv) > 4: azg2.export_obj(m, 1, sys.argv[4])

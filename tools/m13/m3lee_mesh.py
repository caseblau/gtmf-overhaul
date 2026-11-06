"""Build the M3 Lee game mesh (AZG2) on the Mius-Front M4A2 Sherman's skeleton from the user's reference M3 model.

  python m3lee_mesh.py <m4a2_sherman mesh> <M3c.obj (Downloads\\m3c\\M3c - not in the repo)> <out m3lee.mesh.loc_def.bin> [m34a2tur mesh] [preview.obj]
  (m34a2tur = the M4A2's upper hull / turret mesh, the game's own file: its headlights are used; without it the reference's lamps stay)

From the M4A2 (m4a2_sherman, the game's own file): the running-gear nodes (sprockets, road wheels, return rollers,
idlers, bogie holders d_caret_*), the lower-hull holders d_bottom / d_bottom_fr, the trace / smoke / tow sockets, the
internal damage boxes, and every one of their hit shapes; the add-in meshes that hang on those holders (M4A2_BOTTOM,
M4_BOTTOM_FR, M4_CARET) and the wheels / tracks are the game's own and are only named by the config.
From the reference model (m3lee_obj.py, registered on the M4A2's running gear, its own gear / lower hull / nose
dropped): the riveted upper hull with the 75 mm sponson and the round roof plate, the splash guard, stowage boxes,
exhausts, lights, antenna; the 75 mm M2 in mount M1 (the vertical rotor traverses = d_gun_rot, the gun elevates
in it = d_gunmask_02 (a hidden sleeve), the barrel recoils = d_gun_02; head2); the two fixed bow .30s (s_bow_rot /
d_bow_rot; head4); the 37 mm turret with the M24 mount (d_head / d_gunmask / d_gun; head1); the MG cupola with its .30
(d_cupola / d_mgun_body; head3); the hatches: the cupola lid d_hatch_01 (hinged at its rear, axis x), the side doors
d_hatch_02 (left, driver) / d_hatch_03 (right, 75 mm crew) hinged at their front edge (the node's local z is the hinge),
the 75 mm crew's roof hatch d_hatch_04 (the lid right of the turret, hinged at its rear edge; its node is turned 180 deg
about y so the lid lies on its local -z like the earlier front-hinged lid and the config's angle keeps its sense).
Added (m3lee_geom.py): the sponson floors / mudguards over the game's tracks, the gun's sleeve, the rivet rows along the
plate seams and round the roof plate, and the openings under the hatches (the reference's plates are solid there): cut
through the side plates, the roof and the cupola top with dark insides behind them. One material - the M4A2 hull's (m4a2_dift, its olive drab texture); armour map
UVs taken from the M4A2's own hit mesh per plate class; the reference's dark parts (slits, lenses, ring) on the
texture's darkest patch; its two flat shadow polygons (under the turret, over the roof hatch) are left out.
"""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import azg2, geom, uvtools as U, m3lee_geom as G, m3lee_obj as O
import su122_mesh as SM            # vertex codecs, Src, assemble (shared AZG2 writer)

# ---------------------------------------------------------------- texture areas on m4a2_sherman_dift (2048 px)
PLATE_RECT = (0.18, 0.192, 0.66, 0.268); PLATE_SCALE = 0.15   # plain plate of the M4A2 side-plate unwrap (no weld lines)
DARK_UV = (0.690, 0.784)                                     # darkest area (grey-black 30): slits, lenses, the turret ring
TEXEL_UV = (0.42, 0.23)                                      # one plain texel: rivet heads, small round parts

def plate(V, F):
    Vo, Fo, UV = U.plate_uv(V, F, PLATE_RECT, PLATE_SCALE, jitter=False); return SM.new_gxt(Vo, Fo, UV)

def smooth(V, F, crease=40.0):
    Vo, Fo, UV = U.plate_uv(V, F, PLATE_RECT, PLATE_SCALE, jitter=False)
    return SM.new_gxt(Vo, Fo, UV, U.smooth_flat(Vo, Fo, crease))

def flat_uv(V, F, uv, smooth_deg=None):
    Vo = V[F].reshape(-1, 3); Fo = np.arange(len(Vo)).reshape(-1, 3)
    N = U.smooth_normals(V, F, Vo, smooth_deg) if smooth_deg else None
    return SM.new_gxt(Vo, Fo, np.tile(uv, (len(Vo), 1)), N)

def round_part(V, F, origin, axis, crease=50.0):
    Vo, Fo, UV = U.cyl_uv(V, F, origin, axis, PLATE_RECT); return SM.new_gxt(Vo, Fo, UV, U.smooth_normals(V, F, Vo, crease))

def cat(lst):
    As, Fs, o = [], [], 0
    for A, F in lst:
        if A is None or not len(F): continue
        As.append(A); Fs.append(F + o); o += len(A)
    return (np.vstack(As), np.vstack(Fs)) if As else None

# ---------------------------------------------------------------- armour map (arm_m4a2_dift) UVs from the M4A2 hit mesh
def arm_points(T):
    A, F = T.geo[('d_hull', 0)]; P = A[:, :3]; n = geom.normals(P, F); c = P[F].mean(1); uv = A[F][:, :, 6:8].mean(1)
    def pick(nrm, at):
        s = n @ np.asarray(nrm, float) - 0.15 * np.linalg.norm(c - np.asarray(at, float), axis=1)
        return tuple(uv[int(np.argmax(s))])
    return dict(front=pick((0, 0.55, 0.83), (0, 0.3, 1.6)), side=pick((1, 0, 0), (1.25, 0.4, 0)), roof=pick((0, 1, 0), (0, 0.75, 0.3)),
                rear=pick((0, 0.2, -0.98), (0, 0.3, -2.7)))

def arm_class(n):
    if n[1] > 0.9: return 'roof'
    if n[2] > 0.3: return 'front'
    if n[2] < -0.5: return 'rear'
    if n[1] < -0.9: return 'roof'          # sponson floor: thin
    return 'side'

def hit(V, F, arm, cls=None):
    """PNTl rows for a part: one armour UV per face by its plate class (cls forces one)"""
    n = geom.normals(V, F); Vf = V[F].reshape(-1, 3)
    T = np.array([arm[cls or arm_class(k)] for k in n for _ in range(3)])
    return np.c_[Vf, np.repeat(n, 3, axis=0), T], np.arange(len(Vf)).reshape(-1, 3)

# ---------------------------------------------------------------- the M4A2 parts we keep
KEEP_PREFIX = ('d_caret_', 'd_wheel_', 's_trace_', 's_smoke_', 'p_')    # no M4A2 wings (own mudguards in d_hull)
KEEP = {'d_bottom', 'd_bottom_fr', 's_pricep', 's_water_line', 's_fire_04'}
DROP = {'p_driver', 'p_mgunner'}            # crew boxes are placed new below

def tr(p): M = np.eye(4); M[3, :3] = p; return M

def local(V, pivot, R=None):
    """world -> node-local coordinates (row-vector convention; R rows = the local axes in world coordinates)"""
    Vl = np.asarray(V, float) - np.asarray(pivot, float)
    return Vl if R is None else Vl @ np.asarray(R, float).T

# ---------------------------------------------------------------- the reference model's frame points (its parts give the rest)
TUR_AXIS = np.array([-0.335, 1.04, -0.17])   # the 16-facet turret's axis at the hull roof
G37_TRUN_Z = 0.25                            # the M24 mount's trunnions: mid-depth of the mantlet (z 0.13 .. 0.40)
CUP_Y = 1.665                                # the cupola's base = the turret top
DOOR_HINGE = (1.30, 0.42)                    # the side doors' hinge pin: |x| (at the hinge straps' outer face), z (their front end)
HATCH4_HINGE = (1.053, -0.43)                # the roof hatch's hinge pin: y, z (through the hinge blocks behind the lid)
DOOR_HOLE = ((0.28, -0.26), (0.78, 0.33))    # the door openings in the side plates: (y, z) from / to (the doors cover 0.24-0.82, -0.30-0.37)
MG_MUZZLE_Z, MG_BORE_Y = 0.646, 0.028       # hmg_m1919a4_body: muzzle z, bore height in its own frame
CUP_HOLE_R = 0.29                            # the cupola's opening (its lid is r 0.33)
HINGE_KNUCKLE_R = 0.016                      # the cupola lid's hinge knuckle / bracket bosses (radius round the pin)
DISC = ((0.76, 1.05), 0.40, 1.092)           # the round roof plate: centre (x, z), bolt-circle r, top y
DECK = ((0.77, -1.10), (0.54, -2.50), 0.51)  # the engine deck (y, z) from / to, the rear roof behind it

def m4_headlights(m4tur_path, V, P):
    """the M4A2's headlight (m34a2tur node d_light_02, its LOD 1 geometry) at each of the reference's two lamps: post
    foot on the reference lamp's base, lens forward; the lens faces (forward-facing, inside the lamp rim) on DARK_UV"""
    T = SM.Src(m4tur_path); A, F = T.geo[('d_light_02', 1)]; L = A[:, :3].astype(float)
    Q = V[np.unique(P['headlights'])]; out = []
    for s in (-1, 1):
        q = Q[np.sign(Q[:, 0]) == s]; lo, hi = q.min(0), q.max(0)
        org = np.array([(lo[0] + hi[0]) / 2, lo[1] - L[:, 1].min(), (lo[2] + hi[2]) / 2])
        W = L + org; T3 = W[F]; n = np.cross(T3[:, 1] - T3[:, 0], T3[:, 2] - T3[:, 0]); n /= np.maximum(np.linalg.norm(n, axis=1), 1e-12)[:, None]
        c = T3.mean(1) - org; lens = (n[:, 2] > 0.85) & (c[:, 2] > L[:, 2].max() - 0.02) & (np.hypot(c[:, 0], c[:, 1] - 0.0) < 0.07)
        out.append(smooth(W, F[~lens], 50.0)); out.append(flat_uv(W, F[lens], DARK_UV))
    return out

def deck_y(z):
    (y0, z0), (y1, z1), yr = DECK; z = np.asarray(z, float)
    return np.where(z > z0, 1.04, np.where(z > z1, y0 + (z - z0) * (y1 - y0) / (z1 - z0), yr))

def build(m4a2_path, obj_path, m4tur_path=None):
    T = SM.Src(m4a2_path); arm = arm_points(T)
    V, P = O.load(obj_path)
    def part(name): return O.part(V, O.dedupe(V, P[name]))
    def parts(*names): return [part(n) for n in names]
    def bb(name): Q = V[np.unique(P[name])]; return Q.min(0), Q.max(0)
    def axis_xy(name): Q = V[np.unique(P[name])]; return Q[:, 0].mean(), Q[:, 1].mean()
    nodes = []
    def add(name, kind, parent, M, geo=None):
        nodes.append(dict(name=name, kind=kind, parent=parent, M=M, geo=geo or {}))
    # ---- d_hull: the reference's upper hull and fittings, the floors, the rivets
    hull_main, hull_fc, disc = parts('hull_main', 'hull_fc', 'disc'); floors = G.floors()
    Vr, Fr = geom.merge(G.seam_rivets(*geom.merge(hull_main, hull_fc)), G.ring_rivets(DISC[0], DISC[1], DISC[2] + 0.001))   # on the uncut plates
    # the openings under the hatches (the reference's plates are solid there): the side plates behind the doors, the roof
    # under its lid; their dark insides go to the hull's details
    openings = [((s, 0, 0), G.rect3(0, DOOR_HOLE[0], DOOR_HOLE[1], s * 1.267), 0.35) for s in (-1, 1)]
    lo, hi = bb('roof_panel'); openings.append(((0, 1.0, 0), G.rect3(1, (lo[0] + 0.025, lo[2] + 0.03), (hi[0] - 0.025, hi[2] - 0.02), 1.04), 0.35))
    rims = []
    for nrm, hole, depth in openings:
        done = False
        for k, (v, f) in enumerate(((hull_main), (hull_fc))):
            try: cut = G.cut_hole(v, f, nrm, hole)
            except ValueError: continue
            if k == 0: hull_main = cut
            else: hull_fc = cut
            done = True
        if not done: raise RuntimeError('no plate for the opening at %s' % (hole.mean(0),))
        rims.append(flat_uv(*G.hole_rim(nrm, hole, depth), DARK_UV))
    armour = [hull_main, hull_fc, disc, part('box_l'), part('box_r'), floors, G.rear_lower_plate()]   # 4 Nov: + lower rear plate
    big = [plate(v, f) for v, f in armour + [part('splash')]]
    det2 = [plate(v, f) for v, f in parts('mount75', 'shield75', 'shield_frame', 'visor', 'cheek_port', 'roof_panel_base', 'panel_blocks', 'ant_base',
                                           'disc_box', 'roof_rail', 'rear_vent', 'rain_strips', 'exhaust', 'rear_fenders', 'handles')]
    det2.append(smooth(*part('taillights'), 50.0)); det2 += rims
    det1 = list(det2)            # (the reference's dark shadow polygons under the turret and over the roof hatch are not used)
    Vg_, Fg_ = part('hl_guards'); det1.append(flat_uv(Vg_, np.vstack([Fg_, Fg_[:, ::-1]]), TEXEL_UV, 60.0))   # 4 Nov: thin bars, both sides drawn
    # 4 Nov (user: "the m3 lee headlights should be fixed, use something from m4 tank"): the reference's box lamps and
    # front lenses go; the M4A2's own headlight (sealed-beam lamp on its post with the blackout marker on top, the
    # game's m34a2tur d_light_02) stands in each one's place, on the Lee's single plate texture (lens on the dark patch)
    lamps = m4_headlights(m4tur_path, V, P) if m4tur_path else [smooth(*part('headlights'), 50.0)]
    det1 += lamps
    Vl_, Fl_ = part('lenses'); keep = Vl_[Fl_].mean(1)[:, 2] < 0 if m4tur_path else np.ones(len(Fl_), bool)
    det1.append(flat_uv(Vl_, Fl_[keep], DARK_UV)); det1.append(flat_uv(*part('antenna'), TEXEL_UV, 60.0))
    det1.append(flat_uv(Vr, Fr, TEXEL_UV, 80.0))
    far = [plate(v, f) for v, f in armour[:5]]
    add('d_hull', 4, None, np.eye(4), {0: cat([hit(v, f, arm) for v, f in armour]), 1: cat(big + det1), 2: cat(big + det2), 3: cat(far)})
    # ---- kept M4A2 nodes (original local matrices and geometry)
    for n in T.nodes[1:]:
        nm = n['name']
        if nm == 'd_hull' or nm in DROP: continue
        if not (nm in KEEP or nm.startswith(KEEP_PREFIX)): continue
        par = T.nodes[n['parent']]['name'] if n['parent'] < len(T.nodes) else 'd_hull'
        if par in DROP: continue
        g = {L: T.geo[(nm, L)] for L in range(4) if (nm, L) in T.geo}
        add(nm, n['kind'], par if par != 's_root' else None, T.local(nm).copy(), g)
    # ---- crew boxes (p_*) as small hit boxes, sockets (parents with identity rotation only)
    PW = {'d_hull': np.zeros(3)}
    def pbox(name, parent, p, size=(0.35, 0.5, 0.35)):
        Vb, Fb = geom.box((0, 0, 0), size); add(name, 1, parent, tr(np.asarray(p, float) - PW[parent]), {0: hit(Vb, Fb, arm, 'side')})
    def sock(name, parent, p, R=None):
        M = tr(np.asarray(p, float) - PW.get(parent, 0))
        if R is not None: M[:3, :3] = R
        add(name, 0, parent, M)
    def mg_socket(name, parent, Q):
        # 4 Nov (user: "all the mg in m3 look off they should be proper american mg"): the reference's MGs were bare
        # tubes; each is now the game's own Browning M1919A4 (add-in M1919A4_BODY, mesh hmg_m1919a4_body: barrel jacket
        # along +z, muzzle at z 0.646, bore at y 0.028) on a socket placed so its muzzle is the reference barrel's muzzle;
        # the receivers sit behind the plates / inside the cupola
        q = np.asarray(Q, float); lo_, hi_ = q.min(0), q.max(0)
        sock(name, parent, ((lo_[0] + hi_[0]) / 2, (lo_[1] + hi_[1]) / 2 - MG_BORE_Y, hi_[2] - MG_MUZZLE_Z))
    lo, hi = bb('visor'); vis = (lo + hi) / 2
    pbox('p_driver', 'd_hull', (-0.30, 0.40, 1.05)); sock('s_driver', 'd_hull', (-0.30, 0.70, 1.05))
    sock('s_driver_exit', 'd_hull', (-1.95, -0.20, 0.3)); sock('s_camera_driver_01', 'd_hull', (vis[0], vis[1], hi[2] - 0.03))
    sock('s_camera_driver_02', 'd_hull', (-0.60, 1.09, 1.10))
    pbox('p_gunner_02', 'd_hull', (0.45, 0.35, 0.55)); sock('s_gunner_02', 'd_hull', (0.45, 0.66, 0.55))
    pbox('p_loader_02', 'd_hull', (0.85, 0.35, -0.10)); sock('s_loader_02', 'd_hull', (0.85, 0.68, -0.10))
    sock('s_gunner_02_exit', 'd_hull', (1.95, -0.20, 0.3)); sock('s_loader_02_exit', 'd_hull', (1.95, -0.20, -0.4))
    lo, hi = bb('disc_box'); sock('s_camera_gunner_04', 'd_hull', ((lo[0] + hi[0]) / 2, hi[1] + 0.02, (lo[2] + hi[2]) / 2))   # periscope on the roof plate
    pbox('p_radio', 'd_hull', (0.30, 0.65, -0.70), (0.4, 0.3, 0.3))
    # ---- 75 mm gun: the vertical rotor traverses about its axis (d_gun_rot; the shield plate behind it stays with the hull),
    #      the hidden sleeve elevates (d_gunmask_02), the barrel recoils (d_gun_02); the pivots at the bore axis through the rotor's centre
    gx, gy = axis_xy('gun75'); lo, hi = bb('rotor75'); G75 = np.array([gx, gy, (lo[2] + hi[2]) / 2])
    PW['d_gun_rot'] = PW['d_gunmask_02'] = PW['d_gun_02'] = G75
    Vs, Fs = part('rotor75'); Vsl = local(Vs, G75); sh = smooth(Vsl, Fs, 35.0)
    add('d_gun_rot', 4, 'd_hull', tr(G75), {0: hit(Vsl, Fs, arm, 'front'), 1: sh, 2: sh, 3: sh})
    Vc, Fc = G.gun_sleeve(lo[2] - G75[2] + 0.02, hi[2] - G75[2] - 0.02); sl = round_part(Vc, Fc, (0, 0, 0), (0, 0, 1.0))
    add('d_gunmask_02', 4, 'd_gun_rot', np.eye(4), {0: hit(Vc, Fc, arm, 'front'), 1: sl, 2: sl, 3: sl})
    Vb, Fb = part('gun75'); Vbl = local(Vb, G75); barrel = round_part(Vbl, Fb, (0, 0, 0), (0, 0, 1.0))
    muz = bb('gun75')[1][2] - G75[2]; rb = np.hypot(Vb[:, 0] - gx, Vb[:, 1] - gy)[Vb[:, 2] > bb('gun75')[1][2] - 0.01].mean()
    bore = flat_uv(*geom.revolve([(muz + 0.001, rb - 0.012), (muz + 0.002, rb - 0.012)], (0, 0, 0), (0, 0, 1.0), seg=12), DARK_UV)
    add('d_gun_02', 4, 'd_gunmask_02', np.eye(4), {0: hit(Vbl, Fb, arm, 'front'), 1: cat([barrel, bore]), 2: barrel, 3: barrel})
    sock('s_gun_02', 'd_gun_02', G75 + [0, 0, muz]); PW['s_gun_02'] = PW['d_gun_02']
    # ---- the two fixed bow .30s: socket pivot in the lower front plate (head4), the barrels, two muzzle sockets
    lo, hi = bb('bow_mg'); BOW = np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2] + 0.12])
    PW['s_bow_rot'] = PW['d_bow_rot'] = BOW
    sock('s_bow_rot', 'd_hull', BOW)
    Vm, Fm = part('bow_mg'); Vml = local(Vm, BOW)
    add('d_bow_rot', 1, 's_bow_rot', np.eye(4), {0: hit(Vml, Fm, arm, 'front')})     # 4 Nov: drawn by the M1919A4 add-ins
    for nm, s_ in (('s_addin_mg_bow_l', -1), ('s_addin_mg_bow_r', 1)):
        Q = Vm[(Vm[:, 0] < BOW[0]) if s_ < 0 else (Vm[:, 0] >= BOW[0])]; mg_socket(nm, 'd_bow_rot', Q)
    for nm, x in (('s_mgun_01', lo[0] + 0.016), ('s_mgun_04', hi[0] - 0.016)): sock(nm, 'd_bow_rot', (x, BOW[1], hi[2]))
    # ---- the side doors (d_hatch_02 left / driver, d_hatch_03 right / 75 mm crew): hinged on their front edge
    for s, nm, pn in ((-1, 'd_hatch_02', 'door_l'), (1, 'd_hatch_03', 'door_r')):
        lo, hi = bb(pn); pivot = np.array([s * DOOR_HINGE[0], (lo[1] + hi[1]) / 2, DOOR_HINGE[1]])
        R = np.array([[0, 0, -1.0], [s, 0, 0], [0, -s, 0]], float)           # local x rearward, y outward, z the hinge
        Vd, Fd = part(pn); Vl = local(Vd, pivot, R); lod = plate(Vl, Fd)
        M = np.eye(4); M[:3, :3] = R; M[3, :3] = pivot
        add(nm, 4, 'd_hull', M, {0: hit(Vl, Fd, arm, 'side'), 1: lod, 2: lod, 3: lod})
    # ---- the roof hatch right of the turret (d_hatch_04): the lid ahead of its rear hinge; node turned 180 deg about y
    lo, hi = bb('roof_panel'); pv = np.array([(lo[0] + hi[0]) / 2, HATCH4_HINGE[0], HATCH4_HINGE[1]])
    R4 = np.diag([-1.0, 1.0, -1.0]); Vw, Fw = part('roof_panel'); Vl = local(Vw, pv, R4); lod = plate(Vl, Fw)
    M = np.eye(4); M[:3, :3] = R4; M[3, :3] = pv
    add('d_hatch_04', 4, 'd_hull', M, {0: hit(Vl, Fw, arm, 'roof'), 1: lod, 2: lod, 3: lod})
    # ---- turret (head1): the faceted turret with its sight and port, the dark side panels
    PW['d_head'] = TUR_AXIS
    Vt, Ft = part('turret'); Vtl = local(Vt, TUR_AXIS); tur = smooth(Vtl, Ft, 30.0)      # the 22.5 deg facets smooth, the bevels stay
    tdet = [plate(local(v, TUR_AXIS), f) for v, f in parts('tur_sight', 'tur_port_r')]
    tdet += [flat_uv(local(v, TUR_AXIS), f, DARK_UV) for v, f in [part(k) for k in ('dark_0016', 'dark_0017') if k in P]]
    add('d_head', 4, 'd_hull', tr(TUR_AXIS), {0: hit(Vtl, Ft, arm, 'front'), 1: cat([tur] + tdet), 2: cat([tur] + tdet), 3: tur})
    pbox('p_rothead', 'd_head', TUR_AXIS + [0, -0.20, 0], (1.3, 0.25, 1.3))
    tx, tz = TUR_AXIS[0], TUR_AXIS[2]
    pbox('p_gunner', 'd_head', (tx - 0.35, 0.65, tz + 0.25)); sock('s_gunner', 'd_head', (tx - 0.35, 1.05, tz + 0.25))
    pbox('p_loader', 'd_head', (tx + 0.35, 0.62, tz - 0.10)); sock('s_loader', 'd_head', (tx + 0.35, 1.02, tz - 0.10))
    pbox('p_commander', 'd_head', (tx - 0.32, 0.80, tz - 0.25)); sock('s_commander', 'd_head', (tx - 0.32, 1.25, tz - 0.25))
    sock('s_gunner_exit', 'd_head', (-1.9, -0.2, 0.30)); sock('s_loader_exit', 'd_head', (1.9, -0.2, -0.5)); sock('s_commander_exit', 'd_head', (-1.9, -0.2, -0.5))
    lo, hi = bb('tur_sight'); sock('s_camera_gunner_01', 'd_head', ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, hi[2] + 0.02))
    sock('s_camera_loader_01', 'd_head', (tx + 0.40, 1.62, tz + 0.10))
    # the 37 mm M24 mount: the mantlet blocks and the coax elevate with the gun (d_gunmask), the gun recoils (d_gun)
    gx, gy = axis_xy('gun37'); G37 = np.array([gx, gy, G37_TRUN_Z]); PW['d_gunmask'] = PW['d_gun'] = G37
    Vm, Fm = part('mantlet'); Vml = local(Vm, G37); mant = smooth(Vml, Fm, 40.0)
    cx, cy = axis_xy('coax'); Vcx, Fcx = part('coax'); coax = round_part(local(Vcx, G37), Fcx, (cx - gx, cy - gy, 0), (0, 0, 1.0))
    add('d_gunmask', 4, 'd_head', tr(G37 - TUR_AXIS), {0: hit(Vml, Fm, arm, 'front'), 1: mant, 2: mant, 3: mant})   # 4 Nov: coax = add-in
    mg_socket('s_addin_mg_coax', 'd_gunmask', Vcx)
    pbox('p_rotgun', 'd_gunmask', G37, (0.4, 0.3, 0.3))
    Vg, Fg = part('gun37'); Vgl = local(Vg, G37); g37 = round_part(Vgl, Fg, (0, 0, 0), (0, 0, 1.0))
    muz = bb('gun37')[1][2] - G37[2]; rb = np.hypot(Vg[:, 0] - gx, Vg[:, 1] - gy)[Vg[:, 2] > bb('gun37')[1][2] - 0.01].mean()
    bore37 = flat_uv(*geom.revolve([(muz + 0.001, rb - 0.01), (muz + 0.002, rb - 0.01)], (0, 0, 0), (0, 0, 1.0), seg=10), DARK_UV)
    add('d_gun', 4, 'd_gunmask', np.eye(4), {0: hit(Vgl, Fg, arm, 'front'), 1: cat([g37, bore37]), 2: g37, 3: g37})
    sock('s_gun', 'd_gun', G37 + [0, 0, muz]); PW['s_gun'] = PW['d_gun']
    sock('s_mgun_02', 'd_gunmask', (cx, cy, bb('coax')[1][2]))
    # the MG cupola (head3: a small rotating turret with its .30), its lid on top (d_hatch_01, hinged at the rear)
    lo, hi = bb('cup_lid'); CUP = np.array([(lo[0] + hi[0]) / 2, CUP_Y, (lo[2] + hi[2]) / 2]); PW['d_cupola'] = CUP
    # the lid's hinge (4 Nov, user: the lid "hovers when opened"): the pin sat 2 cm inside the lid's rear edge and nothing
    # joined the round lid to the cupola, so the open lid stood on one point of its edge and read as floating.  The pin is
    # now ON the cupola's top rim under the lid's rear edge (the rim's top runs from the r 0.29 opening out to r ~0.34, the
    # lid's rear edge lies on it), so the open lid's edge rests on the rim; two brackets on the rim's rear edge straddle a
    # knuckle on the lid round the pin, with the lid's strap over its top, as on the real cupola.
    cq = V[np.unique(P['cupola'])]; ctop = cq[:, 1].max(); rim_z = cq[cq[:, 1] > ctop - 0.01][:, 2].min()
    hp1 = np.array([CUP[0], ctop, lo[2]])
    RK = HINGE_KNUCKLE_R
    def rod_x(x0, x1, c): return G.rod((c[0] + x0, c[1], c[2]), (c[0] + x1, c[1], c[2]), RK, 8)
    brk = []
    for sx in (-1, 1):
        Vb_, Fb_ = geom.box((hp1[0] + sx * 0.058, ctop + 0.002, (rim_z + hp1[2]) / 2 - 0.004), (0.04, 2 * RK + 0.012, hp1[2] - rim_z + 0.03))
        brk.append(plate(local(Vb_, CUP), Fb_))
        Vb_, Fb_ = rod_x(sx * 0.036, sx * 0.078, hp1); brk.append(round_part(local(Vb_, CUP), Fb_, hp1 - CUP, (1.0, 0, 0)))
    Vq, Fq = part('cupola'); hole = G.circle3((CUP[0], CUP[2]), CUP_HOLE_R, lo[1])      # the opening in the cupola's top under the lid
    Vq, Fq = G.cut_hole(Vq, Fq, (0, 1.0, 0), hole); Vql = local(Vq, CUP); cup = smooth(Vql, Fq, 30.0)
    cupd = cat([cup, flat_uv(*G.hole_rim((0, 1.0, 0), hole - CUP, 0.20), DARK_UV)] + brk)
    add('d_cupola', 4, 'd_head', tr(CUP - TUR_AXIS), {0: hit(Vql, Fq, arm, 'front'), 1: cupd, 2: cupd, 3: cup})
    kx, ky = axis_xy('cup_mg'); klo, khi = bb('cup_mg'); CMG = np.array([kx, ky, klo[2] + 0.02]); PW['d_mgun_body'] = CMG
    Vk, Fk = part('cup_mg'); Vkl = local(Vk, CMG)
    add('d_mgun_body', 1, 'd_cupola', tr(CMG - CUP), {0: hit(Vkl, Fk, arm, 'front')})   # 4 Nov: drawn by the M1919A4 add-in
    mg_socket('s_addin_mg_cup', 'd_mgun_body', Vk)
    sock('s_mgun_03', 'd_mgun_body', (kx, ky, khi[2]))
    sock('s_commander_out', 'd_cupola', CUP + [0, 0.45, 0.0])
    sock('s_camera_commander', 'd_cupola', CUP + [0, 0.17, 0.30])
    Vh, Fh = part('cup_lid'); Vhl = local(Vh, hp1); lid0 = smooth(Vhl, Fh, 40.0)
    Vn, Fn = rod_x(-0.034, 0.034, (0, 0, 0)); knuckle = round_part(Vn, Fn, (0, 0, 0), (1.0, 0, 0))
    Vs_, Fs_ = geom.box((0.0, hi[1] - hp1[1] + 0.004, 0.07), (0.05, 0.008, 0.14)); strap = plate(Vs_, Fs_)
    lid = cat([lid0, knuckle, strap])
    add('d_hatch_01', 4, 'd_cupola', tr(hp1 - CUP), {0: hit(Vhl, Fh, arm, 'roof'), 1: lid, 2: lid, 3: lid0})
    # ---- lights / fires / marks sockets
    for s, nm in ((-1, 's_light_02'), (1, 's_light_03')):
        Q = V[np.unique(P['lenses'])]; Q = Q[(np.sign(Q[:, 0]) == s) & (Q[:, 2] > 0)]; sock(nm, 'd_hull', Q.mean(0) + [0, 0, 0.01])
    sock('s_fire_01', 'd_hull', (-0.20, 0.60, 0.9)); sock('s_fire_02', 'd_hull', (0.60, 0.60, 0.3)); sock('s_fire_03', 'd_head', (tx, 1.45, tz))
    sock('s_fire_05', 'd_head', (tx + 0.2, 1.3, tz - 0.2))
    Rl = np.array([[0, 0, 1.0], [0, 1.0, 0], [-1.0, 0, 0]]); Rr = np.array([[0, 0, -1.0], [0, 1.0, 0], [1.0, 0, 0]])
    for nm, p, R in (('s_mark_04', (tx - 0.80, 1.30, tz - 0.10), Rl), ('s_mark_04f', (tx - 0.80, 1.30, tz + 0.10), Rl),
                     ('s_mark_05', (tx + 0.80, 1.30, tz + 0.10), Rr), ('s_mark_05f', (tx + 0.80, 1.30, tz - 0.10), Rr)):
        M = tr(np.asarray(p) - PW['d_head']); M[:3, :3] = R.T; add(nm, 0, 'd_head', M)
    for nm, p, R in (('s_mark_03', (1.27, 0.40, -0.60), Rr), ('s_mark_03f', (1.27, 0.40, -0.85), Rr),
                     ('s_mark_02', (-1.27, 0.40, -0.85), Rl), ('s_mark_02f', (-1.27, 0.40, -0.60), Rl)):
        M = tr(p); M[:3, :3] = R.T; add(nm, 0, 'd_hull', M)
    # riders on the engine deck / box lids (wp_des_*): sockets 5 cm above the plates
    des = [(-0.40, -1.60), (0.40, -1.60), (-0.40, -2.20), (0.40, -2.20), (0.0, -1.90), (1.0, -1.95), (-1.0, -1.95), (0.0, -2.60)]
    for k, (x, z) in enumerate(des, 1):
        y = (float(deck_y(z)) if abs(x) < 0.77 else bb('box_r')[1][1]) + 0.05
        sock('s_des_%02d' % k, 'd_hull', (x, y, z))
    for k, p in enumerate([(-1.9, -0.2, -2.4), (1.9, -0.2, -2.4), (0.2, -0.2, -3.5)], 1): sock('s_des_out_%02d' % k, 'd_hull', p)
    print('pivots: 75 mm %s bow %s 37 mm %s cupola %s cupola MG %s' % tuple(np.round(p, 3).tolist() for p in (G75, BOW, G37, CUP, CMG)))
    return nodes

if __name__ == '__main__':
    m4a2, obj, out = sys.argv[1:4]
    extra = sys.argv[4:]; m4tur = next((a for a in extra if not a.endswith('.obj')), None)   # 4 Nov: the M4A2's m34a2tur mesh (headlights)
    nodes = build(m4a2, obj, m4tur)
    data = SM.assemble(nodes, m4a2)
    open(out, 'wb').write(data)
    m = azg2.read(out)
    print('written', out, len(data), 'bytes;', len(m['nodes']), 'nodes;', [(b['tag'], b['nv'], b['ni']) for b in m['blocks']], [mt['name'] for mt in m['materials']])
    prev = next((a for a in extra if a.endswith('.obj')), None)
    if prev: azg2.export_obj(m, 1, prev)

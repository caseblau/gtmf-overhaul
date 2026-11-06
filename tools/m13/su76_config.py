"""SU-76M (1943) vehicle config: T-70M automotive tables stretched to six road wheels a side, ZiS-3 gun, open-top crew.

  python su76_config.py <techn_base.bin> <su76m mesh> <out techn_base_oprum delta> [out common_res_mod delta]

Figures (SU-76M, 1943): 10.6 t, crew 4 (driver, commander, gunner, loader), 76.2 mm ZiS-3Sh (the divisional gun ZiS-3 on
an SPG mount; elevation -3 .. +25 deg, 15 deg either side), 60 rounds; two GAZ-202 petrol engines, 2 x 85 hp, 412 l,
45 km/h on roads; armour: upper front 35 mm, lower front 25, hull sides and rear 15, casemate front 25, casemate sides
10, open top. Running gear: the T-70M's (torsion-bar road wheels, front sprocket, rear idler, three return rollers a
side, track t70_260) with a sixth road wheel. Crew: the driver sits closed in the hull front (T-70 driver's station);
gunner, loader and commander stand in the open fighting compartment - work-place rows of the open-topped Sd.Kfz.
251/9 (crew visible, apc_* animations), as the game does for open SPGs. The gun is the ZiS-3's own: its weapons row
(breech block d_zatvor), its shells, its panoramic sight, and its barrel / breech geometry with its texture as
add-ins (SU76M_BARREL, SU76M_BREECH; registered in common_res_mod - second output).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vehcfg, azg2, su76_mesh as SMM

def S(v): return 's:' + v

WHEEL_ID0 = 7601          # wheel ids (the cpillars rows name wheels by these): 7601 .. 7622

def build(tb, mesh):
    T = vehcfg.Vehicle(tb, 't70m'); Z = vehcfg.Vehicle(tb, 'zis3'); H = vehcfg.Vehicle(tb, 'sdkfz251c9')
    have = {n['name'] for n in azg2.read(mesh)['nodes']}
    def ok(row):
        for c in row:
            v = vehcfg.text(c)
            if c.startswith('s:') and v[:2] in ('d_', 's_', 'p_') and v not in have: return False
        return True
    def rows(V, name): return [list(r) for r in V.table(name)['rows']]
    def find(rs, key, col=0): return list(next(r for r in rs if vehcfg.text(r[col]) == key))
    wl = SMM.wheel_layout(); ids = {name: WHEEL_ID0 + i for i, (name, _, _, _) in enumerate(wl)}
    out = []
    for t in T.tables:
        name = t['name']; t = dict(t)
        if name == 'props':
            set_ = {'name': 's:ui_su76m', 'mesh': 's:su76m', 'type': "u:'SPG'", 'vis_factor': 'f:0.9', 'effect': 'f:24',
                    'forw_techn': 'b:0', 'mass': 'f:10600', 'j': 'v:24000;22000;21000', 'engine_pow': 'f:170',
                    'fuel_tank': 'f:412', 'arm': 'v:35;15;15;0', 'armor_thick': 'f:35'}
            rs = []
            for k, c in t['rows']:
                if k in set_:
                    kind = c.split(':')[0]; new = set_[k]
                    if new.split(':')[0] != kind: new = kind + ':' + vehcfg.text(new)
                    c = new
                rs.append([k, c])
            t['rows'] = rs
        elif name == 'wheels':     # T-70M rows by part kind, re-numbered for 22 wheels; the end road wheels keep the T-70's flags
            w = rows(T, 'wheels'); tpl = {'star': find(w, 'd_wheel_01', 1), 'road': find(w, 'd_wheel_03', 1), 'end': find(w, 'd_wheel_02', 1),
                                         'lazy': find(w, 'd_wheel_07', 1), 'roller': find(w, 'd_wheel_08', 1)}
            rs = []; road = [n for n, _, _, k in wl if k == 'road']
            for nm, _, _, kind in wl:
                k = kind
                if kind == 'road' and (road.index(nm) % 6 in (0, 5)): k = 'end'
                r = list(tpl[k]); r[0] = 'u:%d' % ids[nm]; r[1] = S(nm); rs.append(r)
            t['rows'] = rs
        elif name == 'cpillars':   # per side: 11 wheels; first list by kind (sprocket, road wheels, idler, rollers front to rear),
            rs = []                # second in track order (sprocket, road wheels, idler, rollers rear to front) - as on the T-70M
            for side, r in zip((0, 1), rows(T, 'cpillars')):
                names = [n for n, _, _, _ in wl[side * 11:(side + 1) * 11]]
                l1 = [ids[n] for n in names]; l2 = [ids[n] for n in names[:8]] + [ids[n] for n in names[8:][::-1]]
                cells = ['u:%d' % i for i in l1 + l2]; cells += ['u:0'] * (32 - len(cells))
                rs.append(r[:13] + ['u:11', 'u:11'] + cells)
            t['rows'] = rs
        elif name == 'carets':
            t['rows'] = [[S(c), S(w), S('')] for c, _, _, w in SMM.caret_layout()]
        elif name == 'addins':
            t['rows'] = [[S('T70M_LCARET' if p[0] < 0 else 'T70M_RCARET'), S(c)] + ['f:0'] * 6 for c, _, p, _ in SMM.caret_layout()]
            t['rows'] += [[S('SU76M_BARREL'), S('d_gun')] + ['f:0'] * 6, [S('SU76M_BREECH'), S('d_zatvor')] + ['f:0'] * 6]
            t['rows'] += [[S('T70M_WHEEL'), S('d_wheel_23')] + ['f:0'] * 6]          # v3: the spare wheel on the rear plate
        elif name == 'weapons':    # the ZiS-3's own row (loader serves it, breech block d_zatvor), the T-70's smoke grenades
            z = find(rows(Z, 'weapons'), 'ZIS3'); z[5] = S('head1'); z[6] = S('wp_loader')
            g = find(rows(T, 'weapons'), 'GREN_TR'); g[6] = S('wp_commander')
            t['rows'] = [r for r in (z, g) if ok(r)]
        elif name == 'shells':     # 60 rounds; July 1943: mostly HE, AP (BR-350A / B), shrapnel, a few sub-calibre BR-350P
            t['rows'] = [['s:76L42_OF_350', 'u:32'], ['s:76L42_BR_350A', 'u:10'], ['s:76L42_BR_350B', 'u:8'], ['s:76L42_SH_354T', 'u:6'],
                         ['s:76L42_BR_350P', 'u:4'], ['s:RDG', 'u:6']]
        elif name == 'heads':      # T-70 head row; v2: s_rotation traverses (the mantle is fixed), d_gunmask elevates; 15 / 15, +25 / -3
            h = find(rows(T, 'heads'), 'head1'); h[1] = S('s_rotation'); h[3] = 'f:15'; h[4] = 'f:15'; h[5] = 'f:25'; h[6] = 'f:3'; t['rows'] = [h]
        elif name == 'work_places':
            drv = find(rows(T, 'work_places'), 'wp_driver')                                  # closed driver's station (T-70)
            hw = rows(H, 'work_places')
            gun = find(hw, 'wp_gunner'); gun[11] = S(''); gun[16] = S('s_gunner_exit')       # open-top crew (Sd.Kfz. 251/9)
            ldr = find(hw, 'wp_loader'); ldr[11] = S(''); ldr[16] = S('s_loader_exit')
            com = find(hw, 'wp_commander'); com[11] = S(''); com[16] = S('s_commander_exit')
            for r in (gun, ldr, com): r[14] = S('p_' + vehcfg.text(r[0])[3:])                 # crew hit boxes
            des = [r for r in rows(T, 'work_places') if vehcfg.text(r[0]).startswith('wp_des_')]
            dn = ['wp_des_%02d' % k for k in range(1, 7)]; outs = ['s_des_out_01', 's_des_out_02', 's_des_out_01', 's_des_out_01', 's_des_out_02', 's_des_out_03']
            rd = []
            for k, (n_, o_) in enumerate(zip(dn, outs)):
                r = list(des[k % len(des)]); r[0] = S(n_); r[12] = S('s' + n_[2:]); r[16] = S(o_); rd.append(r)
            t['rows'] = [r for r in [drv, gun, ldr, com] + rd if ok(r)]
        elif name == 'sights':
            blank = ['s:'] * 7
            def sg(n, cam, kind, grp): return [S(n), S(cam), S(kind), 'f:0', S(grp)] + blank
            pg = vehcfg.text(find(rows(Z, 'sights'), 'sig_gunner')[2])                        # the ZiS-3's panoramic sight
            t['rows'] = [sg('sig_driver', 's_camera_driver', vehcfg.text(find(rows(T, 'sights'), 'sig_driver')[2]), 'sig_driver'),
                         sg('sig_gunner', 's_camera_gunner', pg, 'sig_gunner')]
        elif name == 'hatchs':     # the driver's lid on the glacis, hinged at its top edge (node local x): opens up
            h = find(rows(T, 'hatchs'), 'driver'); h[3] = 'f:-80'; h[7] = 'u:1'; t['rows'] = [h]
        elif name == 'damages':
            t['rows'] = [r for r in rows(T, 'damages') if ok(r)]
        elif name == 'mslots':
            t['rows'] = [r for r in rows(T, 'mslots') if ok(r)]
        elif name == 'flames':
            t['rows'] = [[S('s_fire_02'), S('driver'), 'u:0'], [S('s_fire_03'), S(''), 'u:1'], [S('s_fire_01'), S('gunner'), 'u:0']]
        elif name == 'detachable':
            d = rows(T, 'detachable'); rs = []
            for r in d:
                n_ = vehcfg.text(r[1])
                if n_ == 'd_wheel_21': r[1] = S('d_wheel_23')
                rs.append(r)
            t['rows'] = [r for r in rs if ok(r)]
        elif name == 'col_pts':    # the T-70's turret points -> the gun shield
            t['rows'] = [r for r in rows(T, name) if ok(r)]
        else:
            t['rows'] = [r for r in rows(T, name) if ok(r)]
        out.append(t)
    return out, T.root_type

ADDINS = (('SU76M_BARREL', 'su76m_barrel'), ('SU76M_BREECH', 'su76m_breech'))

def addin_registry_delta():
    out = ['# SU-76M (1943) gun add-ins - generated by tools\\m13\\su76_config.py: the ZiS-3 barrel and breech block meshes',
           '#   (src\\m13_vehicles\\mfo_gos\\su76m_barrel / su76m_breech) with the ZiS-3 textures, registered as SU122_BARREL is']
    for name, mesh in ADDINS:
        out.append('row+|addins|@end|%s|s:%s|s:%s|s:sh_object_wea|b:0|b:0|f:1|s:zis3_dift|s:zis3_norsp|s:|v:0|v:0|v:0|b:1|s:|f:0|s:|b:0|u:3|s:|u:0|s:' % (name, name, mesh))
    return out

if __name__ == '__main__':
    tables, rt = build(*sys.argv[1:3])
    lines = ['# SU-76M (1943) - generated by tools\\m13\\su76_config.py: T-70M running gear with six road wheels, ZiS-3 gun, open-top crew']
    lines += vehcfg.node_delta('su76m', tables, after='@end', root_type=rt)
    open(sys.argv[3], 'w', encoding='cp1251', newline='\n').write('\n'.join(lines) + '\n')
    print(len(lines), 'lines;', {t['name']: len(t['rows']) for t in tables})
    if len(sys.argv) > 4:
        reg = addin_registry_delta(); open(sys.argv[4], 'w', encoding='cp1251', newline='\n').write('\n'.join(reg) + '\n')
        print(len(reg), 'registry lines ->', sys.argv[4])

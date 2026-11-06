"""M3 Lee (Medium Tank M3) vehicle config: M4A2 Sherman running gear and US fittings, the Lee's own gun / crew layout.

  python m3lee_config.py <techn_base.bin> <techn_base_oprum.bin> <m3lee mesh> <out techn_base_oprum delta>

Figures (TM 9-750, Hunnicutt "Sherman"/"Medium Tank M3"): 27.2 t combat weight, crew 6 (Soviet Lend-Lease vehicles), 75 mm
M3 gun in the right-hand sponson (15 deg left / right, -9 .. +20 deg, 46 rounds), 37 mm M6 gun in the turret (-7 .. +60
deg, 178 rounds), co-axial M1919A4, the cupola M1919A4 (+60 / -8) and the two fixed bow M1919A4 fired by the driver
(9200 rounds of .30 in all), Wright R-975 petrol radial 340 hp, 662 l of fuel; armour 51 mm front, 38 mm sides and
rear, 51 mm turret. Hatches: the cupola lid (commander), the two side doors (driver / 75 mm crew) and the 75 mm roof hatch. The VVSS bogies, tracks, wheels, belly, transmission
cover and wings are the game's own M4A2 parts (add-ins and wheel nodes kept from m4a2_sherman), so the automotive tables
(gears, wheels, cpillars) stay the M4A2's.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vehcfg, azg2

def S(v): return 's:' + v

def build(tb, tbo, mesh):
    M4 = vehcfg.Vehicle(tbo, 'm4a2_sherman'); ST = vehcfg.Vehicle(tb, 'm3a1_stuart')
    have = {n['name'] for n in azg2.read(mesh)['nodes']}
    def ok(row):   # every node / socket a row names must exist in the M3 mesh
        for c in row:
            v = vehcfg.text(c)
            if c.startswith('s:') and v[:2] in ('d_', 's_', 'p_') and v not in have: return False
        return True
    def rows(name): return [list(r) for r in M4.table(name)['rows']]
    def find(rs, key): return list(next(r for r in rs if vehcfg.text(r[0]) == key))
    out = []
    for t in M4.tables:
        name = t['name']; t = dict(t)
        if name == 'props':
            set_ = {'name': 's:ui_m3_lee', 'mesh': 's:m3lee', 'mass': 'f:27200', 'j': 'v:54000;54000;36000',
                    'engine_pow': 'f:340', 'diesel': 'b:0', 'fuel_tank': 'f:662', 'snd_engine': 's:engine_ltank',
                    'arm': 'v:51;38;38;13', 'arm_week': 'v:38;-1;-1;-1', 'armor_thick': 'f:51', 'vis_factor': 'f:1.15',
                    }
            drop = ('mesh2', 'link_chunk1', 'armor_map2', 'armor_thikness2', 'armor_qual2', 'armor_frail2', 'armor_str2')
            rs = []; ty = ''   # one mesh (hull and turret): the M4A2's second-mesh keys go, as on vehicles without mesh2
            for (k, c), tc in zip(t['rows'], t['types']):
                if k in drop: continue
                ty += tc
                if k in set_:
                    kind = c.split(':')[0]; new = set_[k]
                    if new.split(':')[0] != kind: new = kind + ':' + vehcfg.text(new)
                    c = new
                rs.append([k, c])
            t['rows'] = rs; t['types'] = ty; t['cols'] = 1
        elif name == 'weapons':
            w = rows('weapons'); st = [list(r) for r in ST.table('weapons')['rows']]
            m3 = find(w, 'M3'); m3[1] = S('s_gun_02'); m3[4] = S('d_gun_02'); m3[5] = S('head2'); m3[6] = S('wp_gunner_02')
            m6 = find(st, 'M6'); m6[1] = S('s_gun'); m6[4] = S('d_gun'); m6[5] = S('head1'); m6[6] = S('wp_gunner'); m6[2] = 'u:0'
            mgs = [list(r) for r in w if vehcfg.text(r[0]) == 'M1919A4']             # M4A2: [0] the coaxial, [1] the bow gun
            cx = mgs[0]; cx[1] = S('s_mgun_02'); cx[5] = S('head1'); cx[6] = S('wp_gunner')
            aa = [r for r in w if vehcfg.text(r[0]) == 'M2HB'][0]; aa = list(aa)
            aa[0] = S('M1919A4'); aa[1] = S('s_mgun_03'); aa[4] = S(''); aa[5] = S('head3'); aa[6] = S('wp_commander')
            bows = []                                                                  # the two fixed bow guns: the driver's
            for sk in ('s_mgun_01', 's_mgun_04'):
                b = list(mgs[1]); b[1] = S(sk); b[5] = S('head4'); b[6] = S('wp_driver'); bows.append(b)
            t['rows'] = [r for r in [m3, m6, cx, aa] + bows if ok(r)]
        elif name == 'shells':   # 46 x 75 mm (M72 AP, M61 APC, M48 HE, M89 smoke), 178 x 37 mm, 9200 x .30
            t['rows'] = [['s:M3_M72', 'u:12'], ['s:M3_M61', 'u:10'], ['s:M3_M48', 'u:20'], ['s:M3_M89', 'u:4'],
                         ['s:M6_M51B1', 'u:80'], ['s:M6_M74', 'u:40'], ['s:M6_M63', 'u:40'], ['s:M6_CAN_M2', 'u:18'],
                         ['s:P30_06', 'u:9200']]
        elif name == 'heads':
            h = rows('heads')
            h1 = find(h, 'head1'); h1[5] = 'f:60'; h1[6] = 'f:7'                               # 37 mm: -7 .. +60 deg
            h2 = find(h, 'head2'); h2[1] = S('d_gun_rot'); h2[2] = S('d_gunmask_02')          # 75 mm: 15 / 15, -9 .. +20
            h2[3] = 'f:15'; h2[4] = 'f:15'; h2[5] = 'f:20'; h2[6] = 'f:9'
            h3 = find(h, 'head3'); h3[1] = S('d_cupola'); h3[2] = S('d_mgun_body')            # cupola: 360 deg, MG -8 .. +60
            h3[3] = 'f:180'; h3[4] = 'f:180'; h3[5] = 'f:60'; h3[6] = 'f:8'
            h4 = find(h, 'head2'); h4[0] = S('head4')                                          # the fixed bow guns (M4A2 bow-gun
            h4[3] = 'f:2'; h4[4] = 'f:2'; h4[5] = 'f:10'; h4[6] = 'f:5'                          # head: s_bow_rot / d_bow_rot), +10 / -5
            t['rows'] = [h1, h2, h3, h4]
        elif name == 'work_places':
            w = rows('work_places')
            drv = find(w, 'wp_driver'); drv[9] = S('head4'); drv[13] = S('')                   # the driver fires the bow guns
            gun = find(w, 'wp_gunner')                                                       # 37 mm gunner (turret)
            ldr = find(w, 'wp_loader')                                                       # 37 mm loader (turret)
            g2 = find(w, 'wp_gunner'); g2[0] = S('wp_gunner_02'); g2[9] = S('head2'); g2[10] = S('sig_mgunner')
            g2[11] = S('mgunner'); g2[12] = S('s_gunner_02'); g2[14] = S('p_gunner_02'); g2[16] = S('s_gunner_02_exit')
            l2 = find(w, 'wp_loader'); l2[0] = S('wp_loader_02'); l2[10] = S(''); l2[11] = S('mgunner')
            l2[12] = S('s_loader_02'); l2[14] = S('p_loader_02'); l2[16] = S('s_loader_02_exit')
            cmd = find(w, 'wp_commander')
            des = [r for r in w if vehcfg.text(r[0]).startswith('wp_des_')]
            t['rows'] = [r for r in [drv, gun, ldr, g2, l2, cmd] + des if ok(r)]
        elif name == 'sights':
            blank = ['s:'] * 7
            def sg(n, cam, kind, grp): return [S(n), S(cam), S(kind), 'f:0', S(grp)] + blank
            t['rows'] = [sg('sig_driver', 's_camera_driver_01', 'driver_tech_rot', 'sig_driver'),
                         sg('sig_driver_02', 's_camera_driver_02', 'periscope', 'sig_driver'),
                         sg('sig_gunner', 's_camera_gunner_01', 'm40a2', 'sig_gunner'),        # 37 mm: M40 telescope
                         sg('sig_mgunner', 's_camera_gunner_04', 'm4', 'sig_mgunner'),         # 75 mm: M1 periscope
                         sg('sig_loader', 's_camera_loader_01', 'periscope', 'sig_loader'),
                         sg('sig_commander', 's_camera_commander', 'm6', 'sig_commander')]
        elif name == 'hatchs':   # column 7 is the hinge axis in the node's frame (1 = x, 2 = z), column 3 the opening angle
            hr = rows('hatchs'); rs = []
            h = find(hr, 'commander'); h[1] = S('d_hatch_01'); h[3] = 'f:-110'; h[7] = 'u:1'; rs.append(h)   # cupola lid, rear hinge
            h = find(hr, 'driver'); h[1] = S('d_hatch_02'); h[3] = 'f:110'; h[7] = 'u:2'; rs.append(h)        # left door, front hinge
            h = find(hr, 'mgunner'); h[1] = S('d_hatch_03'); h[3] = 'f:110'; h[7] = 'u:2'; rs.append(h)       # right door
            h = find(hr, 'mgunner'); h[1] = S('d_hatch_04'); h[3] = 'f:120'; h[7] = 'u:1'; rs.append(h)       # 75 mm roof hatch
            t['rows'] = [r for r in rs if ok(r)]
        elif name == 'flames':
            t['rows'] = [r for r in rows('flames') if ok(r)]
            for r in t['rows']:
                if vehcfg.text(r[1]) == 'loader': r[1] = S('commander')
        elif name == 'mslots':
            def ms(k, f, n, s, a, d, o): return [S(k), S(f), S(n), 'f:%g' % s, 'f:%g' % a, 'f:%g' % d, 'f:%g' % o]
            t['rows'] = [ms('slog', 's_mark_02f', 's_mark_02', 0.5, 0, 0.003, 0.12), ms('slog', 's_mark_03f', 's_mark_03', 0.5, 0, 0.003, 0.12),
                         ms('num', 's_mark_04f', 's_mark_04', 0.45, 0, 0.006, 0.12), ms('num', 's_mark_05f', 's_mark_05', 0.45, 0, 0.006, 0.12)]
        elif name == 'addins':   # 4 Nov: the four Brownings are the game's own M1919A4 (add-in M1919A4_BODY) on the mesh's sockets
            t['rows'] = [r for r in rows('addins') if ok(r)]
            t['rows'] += [[S('M1919A4_BODY'), S(sk)] + ['f:0'] * 6 for sk in ('s_addin_mg_bow_l', 's_addin_mg_bow_r', 's_addin_mg_coax', 's_addin_mg_cup')]
            t['rows'] = [r for r in t['rows'] if ok(r)]
        elif name == 'lights':
            t['rows'] = [r for r in rows('lights') if vehcfg.text(r[1]) in ('s_light_02', 's_light_03')]
        else:
            t['rows'] = [r for r in rows(name) if ok(r)]
        out.append(t)
    return out, M4.root_type

if __name__ == '__main__':
    tables, rt = build(*sys.argv[1:4])
    lines = ['# M3 Lee (1942) - generated by tools\\m13\\m3lee_config.py: M4A2 running gear and fittings, 75 mm M3 sponson gun, 37 mm M6 turret']
    lines += vehcfg.node_delta('m3lee', tables, after='@end', root_type=rt)
    open(sys.argv[4], 'w', encoding='cp1251', newline='\n').write('\n'.join(lines) + '\n')
    print(len(lines), 'lines;', {t['name']: len(t['rows']) for t in tables})

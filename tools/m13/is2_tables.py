"""IS-2 tables for the optional module m14_is2: the vehicle (a KV-1S clone), the D-25T gun and its AP shell, the wreck, UI rows, unit and squads.

  python is2_tables.py <vanilla dir with tabs\\ and tabs_oprum\\> <is2 mesh> <module dir (src\\m14_is2)>

Figures: IS-2 (1943 production, the D-25T with its muzzle brake): 46 t, crew 4, 122 mm D-25T (-3 .. +20 deg, 28 rounds, about 3 rounds a
minute), three DT, V-2-IS diesel 520 hp, 37 km/h, hull 120 mm front / 90 side / 60 rear, turret 100.  In service from December 1943.

Shells: BR-471 (AP, new) and the game's own OF-471 (HE, group 122L46, the A-19's), the usual 8 AP and 20 HE.  BR-471B came in spring 1945 and is left out.
Penetration, from the engine (basic_physic.codelib 0x180022b30), at a normal hit:
    P (m) = k * d * (0.001 * m * v^2 / d^3) ^ (2/3) * S ^ (-4/3)
k shell col 6, d calibre (m), m col 12, v the speed at the target, S the target's armor_str (2000 KV-1S, 2200 Panther).  Speed falls off as v0 / (1 + c t), that is
v(x) = v0 * exp(-c x / v0), with c col 14 (0x180015230).  Against Soviet plate the Soviet table gives 152 / 142 / 133 / 122 mm at 500 / 1000 / 1500 / 2000 m, so k 0.79 and c 0.09.
Col 10 is the shell's blast, not its penetration: by mass between the game's 100 mm BR-412D and 152 mm BR-540.
Armour: its own map arm_is2_dift (is2_lp.py, armour.py): hull 120 / 90 / 60 / 30 mm, turret and mantlet 100 / 90 / 90 / 30 mm.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import vehcfg, azg2, azcf
from su122_tables import table, find, row

def S(v): return 's:' + v

def vehicle(tbo, mesh):
    K = vehcfg.Vehicle(tbo, 'kv1s'); have = {n['name'] for n in azg2.read(mesh)['nodes']}
    def ok(r):
        for c in r:
            v = vehcfg.text(c)
            if c.startswith('s:') and v[:2] in ('d_', 's_', 'p_') and v not in have: return False
        return True
    def rows(n): return [list(r) for r in K.table(n)['rows']]
    def fnd(rs, key, col=0): return list(next(r for r in rs if vehcfg.text(r[col]) == key))
    out = []
    for t in K.tables:
        n = t['name']; t = dict(t)
        if n == 'props':
            set_ = {'name': 's:ui_is2', 'mesh': 's:is2', 'mass': 'f:46000', 'j': 'v:125000;125000;57000', 'engine_pow': 'f:520', 'fuel_tank': 'f:520',
                    'arm': 'v:120;90;60;30', 'arm_week': 'v:60;60;40;20', 'armor_thick': 'f:120', 'vis_factor': 'f:1.35',
                    'armor_map': 's:arm_is2_dift'}   # 11 Nov: its own map (is2_lp + armour.py), values are 2 x mm; armor_thick is the thickest plate
            set_['boekomplekt'] = 's:is2'   # 10 Nov (user: aims, never fires): it named the KV-1S's loadout - 76 mm rounds the D-25T cannot take
            set_['ostov_type'] = next(c for k, c in t['rows'] if k == 'ostov_type').replace('kv1s_ostov', 'is2_ostov')
            rs = []
            for k, c in t['rows']:
                if k in set_:
                    kind = c.split(':')[0]; new = set_[k]
                    if new.split(':')[0] != kind: new = kind + ':' + vehcfg.text(new)
                    c = new
                rs.append([k, c])
            t['rows'] = rs
        elif n == 'weapons':
            w = [r for r in rows(n) if vehcfg.text(r[1]) != 's_mgun2']; rs = []
            g = fnd(w, 'ZIS5'); g[0] = S('D25T'); rs.append(g)
            for r in w[1:]:
                if vehcfg.text(r[0]) == 'DT' and vehcfg.text(r[1]) == 's_mgun2': r[6] = S('wp_driver')      # the fixed bow gun: the driver's, no radio operator here
                rs.append(r)
            t['rows'] = [r for r in rs if ok(r)]
        elif n == 'shells':
            t['rows'] = [['s:122L46_BR_471', 'u:8'], ['s:122L46_OF_471', 'u:20'], ['s:762_AP', 'u:2331'], ['s:RDG', 'u:12']]
        elif n == 'heads':
            h = rows(n); a = fnd(h, 'head1'); a[5] = 'f:20'; a[6] = 'f:3'
            b = fnd(h, 'head2'); b[3] = 'f:2'; b[4] = 'f:2'; b[5] = 'f:5'; b[6] = 'f:5'
            t['rows'] = [a, fnd(h, 'head3')]
        elif n == 'work_places':
            w = rows(n); rs = []
            for r in w:
                k = vehcfg.text(r[0])
                if k == 'wp_mgunner': continue
                if k == 'wp_driver': r[9] = S('')             # 10 Nov: no bow DT (the model has none; its flash came out by the visor)
                if k == 'wp_commander': r[11] = S('commander')  # his own hatch: the cupola leaves (was the loader's)
                rs.append(r)
            t['rows'] = [r for r in rs if ok(r)]
        elif n == 'sights':
            # 9 Nov: the IS-2's own ports (is2_bought places the cameras): no rear loader periscope; the commander's MK-4 and six
            # cupola slits; the driver's second roof periscope
            rs = [r for r in rows(n) if ok(r) and vehcfg.text(r[4]) != 'sig_mgunner' and vehcfg.text(r[0]) not in ('sig_loader_back', 'sig_gunner_side', 'sig_loader_side')]   # 10 Nov: no side vision ports (pistol ports only)
            for r in rs:
                if vehcfg.text(r[1]).startswith('s_camera_mk4_') and vehcfg.text(r[1]) != 's_camera_mk4_01': r[2] = S('hole'); r[7] = S('')
            tpl = list(next(r for r in rs if vehcfg.text(r[0]) == 'sig_comh_02'))
            for k in (6, 7):
                r = list(tpl); r[0] = S('sig_comh_%02d' % k); r[1] = S('s_camera_mk4_%02d' % k); rs.append(r)
            for r in rs:   # 10 Nov: the periscopes turn (is2_lp: d_sight / d_sight_02 / d_sight_03)
                cam = vehcfg.text(r[1])
                if cam == 's_camera_gunner_02': r[7] = S('')   # 10 Nov (user: the gun scope had no view, the gun never fired): tied to the KV's driver_cap, a lid this model lacks
                if cam == 's_camera_loader_02': r[5] = S('d_sight_02')
                if cam == 's_camera_mk4_01': r[5] = S('d_sight_03'); r[7] = S('')   # 10 Nov: the MK-4 no longer opens the lid (it stood open all the time)
            d2 = list(next(r for r in rs if vehcfg.text(r[0]) == 'sig_driver_1')); d2[0] = S('sig_driver_2'); d2[1] = S('s_camera_driver_03'); rs.append(d2)
            t['rows'] = [r for r in rs if ok(r)]
        elif n == 'hatchs':
            h = rows(n); rs = []
            for r in h:
                k, nd = vehcfg.text(r[0]), vehcfg.text(r[1])
                if k == 'head': r[3] = 'f:110'; r[7] = 'u:2'; rs.append(r)    # axis 2: the node's z is the hinge (is2_bought.hatch)
                elif k in ('driver_cap', 'hull'): rs.append(r)
            c = fnd(h, 'head')
            for nd in ('d_hatch_04', 'd_hatch_05'):   # the commander's own hatch (opened when he goes head out), as the loader's
                r = list(c); r[0] = S('commander'); r[1] = S(nd); r[3] = 'f:110'; r[7] = 'u:2'; rs.append(r)
            t['rows'] = [r for r in rs if ok(r)]
        else:
            t['rows'] = [r for r in rows(n) if ok(r)]
        out.append(t)
    return out, K.root_type

def main(root, mesh, mod):
    tb = os.path.join(root, 'tabs_oprum', 'techn_base_oprum.config.loc_def.bin'); ui = os.path.join(root, 'tabs_oprum', 'ui_params.config.loc_def.bin')
    div = os.path.join(root, 'tabs_oprum', 'div_units_ussr.config.loc_def.bin'); crm = os.path.join(root, 'tabs', 'common_res_mod.config.loc_def.bin')
    tabs = os.path.join(mod, 'mfo_tabs'); ap = os.path.join(mod, 'mfo_tabs_ap')
    os.makedirs(tabs, exist_ok=True); os.makedirs(ap, exist_ok=True); os.makedirs(os.path.join(mod, 'mfo_gos'), exist_ok=True)
    def w(path, lines): open(path, 'w', encoding='cp1251', newline='\n').write('\n'.join(lines) + '\n')
    T, rt = vehicle(tb, mesh)
    w(os.path.join(tabs, 'techn_base_oprum.config.loc_def.14_is2.delta'), ['# IS-2 - generated by tools\\m13\\is2_tables.py: KV-1S running gear and tables, 122 mm D-25T'] + vehcfg.node_delta('is2', T, after='@end', root_type=rt))
    print({t['name']: len(t['rows']) for t in T if t['name'] in ('weapons', 'heads', 'work_places', 'sights', 'hatchs', 'addins', 'wheels', 'damages', 'carets')})
    # gun and shells
    L = ["# 122 mm D-25T and its AP shell (tools\\m13\\is2_tables.py); the HE is the game's own 122L46_OF_471"]
    # 10 Nov (user: aims, no shot): built on the KV-1S's ZiS-5 tank-gun row - the SU-152's ML-20S row carried the field-gun flags
    # (u:8576, absent on every tank gun) and its indirect-fire settings; calibre, shells, reload, recoil and report from the 122 mm guns
    g = find(table(crm, 'weapons'), 'ZIS5'); g[0] = S('D25T'); g[4] = 'a:5;5';   # 11 Nov (user: muzzle fumes don't match the muzzle): column 4 is flash size; gas pattern - 3 plain muzzle (A-19, M-30), 4-5 muzzle brake (PaK 40, KwK 36, ML-20S); the D-25T has a two-baffle brake (a leFH 18M copy, a:5;3 inside the brake, was tried and reverted)
    g[6] = 'f:122'; g[8] = 'f:0.45'; g[13] = 'f:22'; g[15] = 'v:2;1'; g[17] = 'f:1'
    # 11 Nov (user: fires, no recoil or sound): shot_a19 is only used by towed / off-map 122 mm guns; the SU-152's ML-20S sound is one a vehicle plays
    g[18] = S('shot_howit'); g[20] = S('gun_d25t'); g[24] = S('122L46'); g[27] = 'f:1'; g[28] = 'v:35;30;200'   # 11 Nov (user: muzzle fumes wrong): the big guns' smoke strength and scale (ML-20S, KwK 42), not the ZiS-5's
    L.append(row('weapons', g))
    sh = table(crm, 'shells')
    a = find(sh, '152L29_BR_540'); a[0] = S('122L46_BR_471'); a[3] = S('122L46'); a[4] = 'v:800'; a[6] = 'f:0.79'; a[10] = 'v:800;6;700;28'; a[12] = 'f:25'; a[13] = 'f:0.156'; a[14] = 'f:0.09'; a[19] = 'v:2000'; a[21] = S('sh_122l46_br_471'); L.append(row('shells', a))
    w(os.path.join(tabs, 'common_res_mod.config.loc_def.14_is2.delta'), L)
    # the wreck: the KV-1S's rows on its own mesh
    ost = os.path.join(root, 'tabs', 'ostovs.config.loc_def.bin'); b, ns = azcf.read(ost); n = next(x for x in ns if x['name'] == 'kv1s_ostov0'); c = ns[n['index'] + 1]
    O_ = ["# IS-2 wreck (tools\\m13\\is2_tables.py): the KV-1S wreck's rows, its own mesh (tools\\m13\\is2_wreck.py)", 'node+|is2_ostov0|%d|%d|%s|@end' % (n['type'], n['cols'], n['types'])]
    for r_ in range(n['rows']):
        o = n['data'] + r_ * 0x40; k = b[o + 0x20:o + 0x40].split(b'\0')[0].decode('cp1251'); v = vehcfg.cell(b, o)
        O_.append('row+|is2_ostov0|@end|%s|%s|%s' % (k, k, 's:is2_ostov01' if k == 'mesh' else 'f:46000' if k == 'mass' else v))
    O_.append('node+|is2_ostov0/col_bounds|%d|%d|%s|@top' % (c['type'], c['cols'], c['types']))
    for r_ in range(c['rows']):
        cells = [vehcfg.cell(b, c['data'] + r_ * 0x20 * c['cols'] + k * 0x20) for k in range(c['cols'])]; O_.append('row+|is2_ostov0/col_bounds|@end|%s|%s' % (vehcfg.text(cells[0]), '|'.join(cells)))
    w(os.path.join(tabs, 'ostovs.config.loc_def.14_is2.delta'), O_)
    # UI
    U = ['# IS-2 UI rows (tools\\m13\\is2_tables.py): the KV-1S layout']
    t = find(table(ui, 'techns'), 'kv1s_m42')
    t[0] = S('is2'); t[1] = S('ui_is2'); t[2] = 'v:120;90;60;30'; t[3] = 'v:100;90;60;30'; t[4] = 'v:100;100;100;30'
    t[10] = S('is2');   # the model the unit / encyclopedia screens show (was kv1s_mid: the IS-2 showed as a KV-1S there, 9 Nov)
    t[13] = 'f:46'; t[14] = 'a:1943;1945;1943;3395'; t[16] = 'a:6770;3070;2730;420'; t[17] = 'a:4'
    t[19] = S('D25T'); t[20] = 'v:-3;20;-180;180'; t[21] = S('DT'); t[23] = 'a:1;3'; t[24] = 'a:28;2331'; t[29] = 'a:520;240;150;520'; t[30] = 'a:37;16;240;78'
    t[36] = S(''); t[42] = S('is2'); U.append(row('techns', t))
    m_ = find(table(ui, 'managed'), 'kv1s_m42'); m_[0] = S('is2'); U.append(row('managed', m_))
    w(os.path.join(tabs, 'ui_params.config.loc_def.14_is2.delta'), U)
    # unit and squads
    D = ['# IS-2 unit and squads (tools\\m13\\is2_tables.py): 4-man crews, in service from December 1943']
    u = find(table(div, 'units'), 'rkkau_kv1s_m42'); u[0] = S('rkkau_is2'); u[1] = S('ui_is2'); u[4] = S('is2'); u[5] = 'u:4'   # 11 Nov (user: the order line is somewhere else): column 16 (indirect-fire calibre, set only on guns, mortars, SU-152, Matilda CS) made the platoon artillery - its orders drew as a fire mission; the KV-1S leaves it empty
    u = [S('is2') if c == S('kv1s_mid') else c for c in u]   # the unit's display model too (9 Nov)
    D.append(row('units', u))
    sq = table(div, 'squads')
    for src, dst, crew, cost in (('rkka_kv1s_m42', 'rkka_is2', 'rkka_crew_stug3', 'a:900;20;37;17'), ('rkka_kv1s_m42_com', 'rkka_is2_com', 'rkka_crew_pcom4', 'a:950;21;37;17'),
                                 ('rkka_kv1s_m42_ccom', 'rkka_is2_ccom', 'rkka_crew_ccom4', 'a:1000;21;37;17')):
        r = find(sq, src); r[0] = S(dst); r[8] = cost; r[13] = 'u:0x19430701'; r[14] = 'u:0x19451201'; r[18] = S('rkkau_is2'); r[20] = S(crew); D.append(row('squads', r))   # 10 Nov (user): from July 1943 so it can join summer-1943 skirmishes (in service Dec 1943)
    w(os.path.join(ap, 'div_units_ussr.config.loc_def.14_is2.delta'), D)
    # the names live in the one text entry, which module m13 owns: harmless strings when the IS-2 is left out
    import textpack
    tp = os.path.join(os.path.dirname(mod), 'm13_vehicles', 'mfo_text_loc', '00_loc_kit_weaps.text.loc_eng.bin'); loc, items = textpack.read(tp)
    new = [('ui_is2', ['IS-2', 'IS-2']), ('gun_d25t', ['122 mm D-25T']), ('sh_122l46_br_471', ['122 mm BR-471', 'Br-471', 'APHE'])]
    _, van = textpack.read(os.path.join(root, 'text_loc', '00_loc_kit_weaps.text.loc_eng.bin')); new += [x for x in van if x[0] == 'sh_122l46_of_471']      # the game's own name back: an earlier build overwrote it
    print('HE name', [x for x in van if x[0] == 'sh_122l46_of_471'])
    ref = {k: [x for x in items if x[0] == k] for k in ('sh_br_350a', 'sh_122l22_of_462', 'gun_m30')}; print('name rows copied from', ref)
    items = [x for x in items if x[0] not in {k for k, _ in new}] + new; textpack.write(tp, loc, items)
    fl = lambda names: 'i_unflat:unflat()\n{\n' + ''.join('\t%-30s, %-16s, loc_def ;\n' % n for n in names) + '}\n'
    open(os.path.join(tabs, '!flatlist'), 'w', newline='\n').write(fl([('common_res_mod', 'config'), ('ostovs', 'config'), ('techn_base_oprum', 'config'), ('ui_params', 'config')]))
    open(os.path.join(ap, '!flatlist'), 'w', newline='\n').write(fl([('div_units_ussr', 'config')]))
    open(os.path.join(mod, 'mfo_gos', '!flatlist'), 'w', newline='\n').write(fl([('is2', 'mesh'), ('reg_is2_dift', 'texture'), ('bump_is2_norsp', 'texture'), ('is2_ostov01', 'mesh'), ('reg_is2_ostov_dift', 'texture'), ('bump_is2_ostov_norsp', 'texture'), ('arm_is2_dift', 'armor')]))

if __name__ == '__main__':
    main(*sys.argv[1:4])

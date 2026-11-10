r"""T-34-85 tables for the optional module m15_t3485 (tools\m13\t3485.py makes the mesh): the game's T-34 mod. 1942 (t34_utz_m42)
with the 85 mm ZiS-S-53 on the 85 mm rounds the game already has (52K family: BR-365, BR-365K, BR-365P, OF-365), a fifth crewman
(the commander under the cupola, the KV-1S's commander row), no opening turret hatches, the KV-1S's 5-man crews, and its unit /
squads / UI rows cloned from the T-34's.

  python t3485_tables.py <vanilla tables root (users\modwork\_orig\3598)> <t3485 mesh> <module dir (src\m15_t3485)>
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import vehcfg, azg2
from su122_tables import table, find, row

def S(x): return 's:' + x


def vehicle(tb, tbo, mesh):
    K = vehcfg.Vehicle(tb, 't34_utz_m42'); KV = vehcfg.Vehicle(tbo, 'kv1s'); have = {n['name'] for n in azg2.read(mesh)['nodes']}
    def ok(r):
        return all(not (c.startswith('s:') and vehcfg.text(c)[:2] in ('d_', 's_', 'p_') and vehcfg.text(c) not in have) for c in r)
    def rows(n): return [list(r) for r in K.table(n)['rows']]
    def fnd(rs, key, col=0): return list(next(r for r in rs if vehcfg.text(r[col]) == key))
    out = []
    for t in K.tables:
        n = t['name']; t = dict(t)
        if n == 'props':
            set_ = {'name': 's:ui_t3485', 'mesh': 's:t3485', 'mass': 'f:32000', 'j': 'v:72000;72000;48000', 'engine_pow': 'f:500',
                    'vis_factor': 'f:1.45', 'boekomplekt': 's:t3485',
                    # 11 Nov (user: real T-34-85 values): the turret's own armour map (t3485.armour_map: 90 / 75 / 52 / 20 mm turret plates,
                    # the T-34's hull), the thickest plate, and the AI's front / side / rear / top estimate; its own wreck
                    'armor_map': 's:arm_t3485_dift', 'armor_thick': 'f:90', 'arm': 'v:90;60;45;20',
                    'ostov_type': 's:tabs\\\\ostovs.cfgpack, t3485_ostov*'}   # written escaped, as the IS-2's row
            rs = []
            for k, c in t['rows']:
                if k in set_:
                    new = set_[k]; kind = c.split(':')[0]
                    c = new if new.split(':')[0] == kind else kind + ':' + vehcfg.text(new)
                rs.append([k, c])
            t['rows'] = rs
        elif n == 'weapons':
            rs = rows(n); g = fnd(rs, 'F34'); g[0] = S('ZIS_S53'); t['rows'] = [g] + [r for r in rs[1:] if ok(r)]
        elif n == 'shells':   # a 1944 load of 55 rounds; DT 31 drums
            t['rows'] = [['s:52K_OF_365', 'u:36'], ['s:52K_BR_365', 'u:14'], ['s:52K_BR_365K', 'u:0'], ['s:52K_BR_365P', 'u:5'], ['s:762_AP', 'u:1953'], ['s:RDG', 'u:12']]
        elif n == 'work_places':
            rs = []
            for r in rows(n):
                k = vehcfg.text(r[0])
                if k == 'wp_gunner': r[11] = S(''); r[13] = S('')                    # the T-34-85 gunner has no hatch of his own
                if k == 'wp_loader': r[11] = S('loader'); r[13] = S('s_loader_out')  # 11 Nov (user): head out of his own hatch
                rs.append(r)
            c = list(next(r for r in KV.table('work_places')['rows'] if vehcfg.text(r[0]) == 'wp_commander'))
            c[9] = S(''); c[11] = S('commander'); c[13] = S('s_commander_out')        # no weapon of his own; head out of the cupola (11 Nov)
            rs.append(c); t['rows'] = [r for r in rs if ok(r)]
        elif n == 'sights':
            rs = []
            for r in rows(n):
                if vehcfg.text(r[1]) == 's_camera_pt4_7':
                    r[5] = S('d_sight_01'); rs.append(r)                               # the gunner's periscope turns (t3485.py cuts it out)
                    l2 = list(r); l2[0] = S('sig_loader_mk4'); l2[1] = S('s_camera_loader_02'); l2[2] = S('mk4'); l2[4] = S('sig_loader'); l2[5] = S('d_sight_02')
                    rs.append(l2); continue                                            # the loader's own turning MK-4
                rs.append(r)
            kv = [list(r) for r in KV.table('sights')['rows'] if vehcfg.text(r[0]).startswith('sig_comh_')]
            for i, r in enumerate(kv[:1] + kv[1:] + [list(kv[-1])]):
                r[0] = S('sig_comh_%02d' % (i + 1)); r[1] = S('s_camera_mk4_%02d' % (i + 1)); r[7] = S('')
                if i: r[2] = S('hole')                                                  # the cupola's vision slits
                else: r[5] = S('d_sight_03')                                            # the MK-4 in the cupola lid turns
                rs.append(r)
            t['rows'] = [r for r in rs if ok(r)]
        elif n == 'heads':   # ZiS-S-53 elevation -5 / +22 deg
            rs = rows(n); h = fnd(rs, 'head1'); h[5] = 'f:22'; t['rows'] = [h] + [r for r in rs if vehcfg.text(r[0]) != 'head1' and ok(r)]
        elif n == 'hatchs':
            rs = [r for r in rows(n) if vehcfg.text(r[0]) in ('driver', 'drv_cap_01', 'drv_cap_02')]
            ld = fnd(rows(n), 'loader'); ld[1] = S('d_hatch_03'); ld[3] = 'f:100'; ld[7] = 'u:2'; rs.append(ld)   # the loader's hatch, front hinge (t3485.LIDS)
            cm = list(ld); cm[0] = S('commander'); cm[1] = S('d_hatch_04'); rs.append(cm)                    # the cupola lid / its front leaf
            t['rows'] = [r for r in rs if ok(r)]
        else:
            t['rows'] = [r for r in rows(n) if ok(r)]
        out.append(t)
    return out, K.root_type


def main(root, mesh, mod):
    tb = os.path.join(root, 'tabs_oprum', 'techn_base.config.loc_def.bin'); tbo = os.path.join(root, 'tabs_oprum', 'techn_base_oprum.config.loc_def.bin')
    ui = os.path.join(root, 'tabs_oprum', 'ui_params.config.loc_def.bin'); div = os.path.join(root, 'tabs_oprum', 'div_units_ussr.config.loc_def.bin')
    crm = os.path.join(root, 'tabs', 'common_res_mod.config.loc_def.bin')
    tabs = os.path.join(mod, 'mfo_tabs'); ap = os.path.join(mod, 'mfo_tabs_ap'); gos = os.path.join(mod, 'mfo_gos')
    for d in (tabs, ap, gos): os.makedirs(d, exist_ok=True)
    def w(path, lines): open(path, 'w', encoding='cp1251', newline='\n').write('\n'.join(lines) + '\n')
    T, rt = vehicle(tb, tbo, mesh)
    w(os.path.join(tabs, 'techn_base_oprum.config.loc_def.15_t3485.delta'), ['# T-34-85 - generated by tools\\m13\\t3485_tables.py: the T-34 mod. 1942 with the 85 mm turret'] + vehcfg.node_delta('t3485', T, after='@end', root_type=rt))
    print({t['name']: len(t['rows']) for t in T if t['name'] in ('weapons', 'shells', 'heads', 'work_places', 'sights', 'hatchs')})
    # the gun: the T-34's F-34 tank-gun row (no field-gun flags) with the 85 mm calibre, the 52K's rounds and a vehicle shot sound
    g = find(table(crm, 'weapons'), 'F34'); g[0] = S('ZIS_S53'); g[6] = 'f:85'; g[13] = 'f:8.5'; g[15] = 'v:1.7;0.8'; g[17] = 'f:0.9'
    g[18] = S('shot_flak36'); g[20] = S('gun_zis_s53'); g[24] = S('52K'); g[27] = 'f:1'; g[28] = 'v:30;30;200'
    w(os.path.join(tabs, 'common_res_mod.config.loc_def.15_t3485.delta'), ['# 85 mm ZiS-S-53 (tools\\m13\\t3485_tables.py) on the game\'s 85 mm rounds', row('weapons', g)])
    # UI and loadout row (props boekomplekt names it)
    t = find(table(ui, 'techns'), 't34_utz_m42'); t[0] = S('t3485'); t[1] = S('ui_t3485'); t[4] = 'v:90;75;52;20'; t[10] = S('t3485')
    t[13] = 'f:32'; t[14] = 'a:1944;1945;1944;11000'; t[16] = 'a:8150;3000;2720;400'; t[17] = 'a:5'; t[19] = S('ZIS_S53'); t[24] = 'a:55;1953'
    t[25] = S('sight_tmdf7'); t[36] = S(''); t[41] = S('tabs\\\\techn_base_oprum.cfgpack'); t[42] = S('t3485')
    m_ = find(table(ui, 'managed'), 't34_utz_m42'); m_[0] = S('t3485')
    w(os.path.join(tabs, 'ui_params.config.loc_def.15_t3485.delta'), ['# T-34-85 UI rows (tools\\m13\\t3485_tables.py)', row('techns', t), row('managed', m_)])
    # the wreck: the generic T-34 wreck's rows on the T-34-85 wreck mesh (t3485.wreck)
    import azcf
    ost = os.path.join(root, 'tabs', 'ostovs.config.loc_def.bin'); b, ns = azcf.read(ost); nn = next(x for x in ns if x['name'] == 'rtank_ostov0')
    O_ = ["# T-34-85 wreck (tools/m13/t3485_tables.py): the T-34 wreck's rows, its own mesh", 'node+|t3485_ostov0|%d|%d|%s|@end' % (nn['type'], nn['cols'], nn['types'])]
    for r_ in range(nn['rows']):
        o = nn['data'] + r_ * 0x40; k = b[o + 0x20:o + 0x40].split(bytes(1))[0].decode('cp1251'); v = vehcfg.cell(b, o)
        O_.append('row+|t3485_ostov0|@end|%s|%s|%s' % (k, k, 's:t3485_ostov01' if k == 'mesh' else 'f:24000' if k == 'mass' else v))
    kids = [x for x in ns if x['index'] > nn['index'] and x['name'].startswith('rtank_ostov0/')] if 'index' in nn else []
    for c in kids:
        O_.append('node+|t3485_ostov0/%s|%d|%d|%s|@top' % (c['name'].split('/', 1)[1], c['type'], c['cols'], c['types']))
        for r_ in range(c['rows']):
            cells = [vehcfg.cell(b, c['data'] + r_ * 0x20 * c['cols'] + k * 0x20) for k in range(c['cols'])]; O_.append('row+|t3485_ostov0/%s|@end|%s|%s' % (c['name'].split('/', 1)[1], vehcfg.text(cells[0]), '|'.join(cells)))
    w(os.path.join(tabs, 'ostovs.config.loc_def.15_t3485.delta'), O_)
    # unit and squads: the T-34's, with the KV-1S's 5-man crews; 1 July 1943 on, so it can join the summer-1943 skirmishes like the IS-2
    D = ['# T-34-85 unit and squads (tools\\m13\\t3485_tables.py)']
    u = find(table(div, 'units'), 'rkkau_t34_42_uztm'); u[0] = S('rkkau_t3485'); u[1] = S('ui_t3485'); u[3] = S('tabs\\\\techn_base_oprum.cfgpack'); u[4] = S('t3485'); u[5] = 'u:5'
    D.append(row('units', u))   # column 16 stays empty: filled, it makes the platoon artillery (the IS-2's order line, 11 Nov)
    sq = table(div, 'squads')
    for src, dst, crew, cost in (('rkka_t34_42_uztm', 'rkka_t3485', 'rkka_crew_kv1', 'a:700;18;34;17'), ('rkka_t34_42_uztm_com', 'rkka_t3485_com', 'rkka_crew_pcom5', 'a:750;19;34;17'),
                                 ('rkka_t34_42_uztm_ccom', 'rkka_t3485_ccom', 'rkka_crew_ccom5', 'a:800;19;19;17'), ('rkka_t34_42_uztm_bcom', 'rkka_t3485_bcom', 'rkka_crew_ccom5', 'a:900;19;19;17')):
        r = find(sq, src); r[0] = S(dst); r[8] = cost; r[13] = 'u:0x19430701'; r[14] = 'u:0x19451201'; r[18] = S('rkkau_t3485'); r[20] = S(crew); D.append(row('squads', r))
    w(os.path.join(ap, 'div_units_ussr.config.loc_def.15_t3485.delta'), D)
    import textpack
    tp = os.path.join(os.path.dirname(mod), 'm13_vehicles', 'mfo_text_loc', '00_loc_kit_weaps.text.loc_eng.bin'); loc, items = textpack.read(tp)
    new = [('ui_t3485', ['T-34-85', 'T-34-85']), ('gun_zis_s53', ['85 mm ZiS-S-53'])]
    items = [x for x in items if x[0] not in {k for k, _ in new}] + new; textpack.write(tp, loc, items)
    fl = lambda names: 'i_unflat:unflat()\n{\n' + ''.join('\t%-30s, %-16s, loc_def ;\n' % n for n in names) + '}\n'
    open(os.path.join(tabs, '!flatlist'), 'w', newline='\n').write(fl([('common_res_mod', 'config'), ('ostovs', 'config'), ('techn_base_oprum', 'config'), ('ui_params', 'config')]))
    open(os.path.join(ap, '!flatlist'), 'w', newline='\n').write(fl([('div_units_ussr', 'config')]))
    open(os.path.join(gos, '!flatlist'), 'w', newline='\n').write(fl([('t3485', 'mesh'), ('reg_t3485__utz_dift', 'texture'), ('bump_t3485__utz_norsp', 'texture'), ('t3485_ostov01', 'mesh'), ('arm_t3485_dift', 'armor')]))


if __name__ == '__main__':
    main(*sys.argv[1:4])

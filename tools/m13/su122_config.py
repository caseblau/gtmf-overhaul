"""SU-122 vehicle config: T-34 mod. 1942 automotive tables + SU-152 crew / gun layout, M-30S gun.

  python su122_config.py <techn_base.bin> <techn_base_oprum.bin> <su122 mesh> <out techn_base_oprum delta> [out common_res_mod delta]

Sources: Wikipedia SU-122 (30.9 t, 5 crew, M-30S, -3..+25 deg, 20 deg traverse sector, 40 rounds); SU-122 used the T-34's
V-2 engine and running gear. Ammunition for July 1943: OF-462 HE and the BP-460A HEAT round (from May 1943).
v31 (user: "use the M-30 gun as source for the gun"): the gun itself comes from the M-30's own config (m30m38 in
techn_base) - its weapons row (M30 with the swinging breech block d_zatvor, -110 deg, as on the towed gun; the mesh has
the M-30's d_zatvor node under d_gun), its shell types (SU-122 quantities: 40 rounds), its panoramic sight (pg) on the
gunner's panorama camera; and the barrel and breech block are the M-30's geometry with the M-30's own texture, attached
through the addins table (SU122_BARREL on d_gun, SU122_BREECH on d_zatvor - mesh files su122_barrel / su122_breech
written by su122_mesh.py next to the main mesh) and registered in common_res_mod's addins table (second output). The gun's damage rows stay the SU-152's (the mount is inside an
armoured casemate, not an open carriage).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vehcfg, azg2

def build(tb, tbo, mesh):
    T = vehcfg.Vehicle(tb, 't34_utz_m42'); S = vehcfg.Vehicle(tbo, 'su152'); M = vehcfg.Vehicle(tb, 'm30m38')   # v31: the gun
    have = {n['name'] for n in azg2.read(mesh)['nodes']}
    def ok(row):   # every node / socket a row names must exist in the SU-122 mesh
        for c in row:
            v = vehcfg.text(c)
            if c.startswith('s:') and v[:2] in ('d_', 's_', 'p_') and v not in have: return False
        return True
    out = []
    for t in T.tables:
        name = t['name']; t = dict(t)
        if name == 'props':
            set_ = {'name': 's:ui_su122', 'mesh': 's:su122', 'type': "u:'SPG'", 'vis_factor': 'f:1.2', 'effect': 'f:45',
                    'forw_techn': 'b:0', 'mass': 'f:30900', 'j': 'v:72000;72000;48000', 'fuel_tank': 'f:540',
                    'snde_base_freq_k': 'f:1.3', 'pill_rep_time': 'f:15', 'eng_ai_snd_max': 'f:500'}
            rows = []
            for k, c in t['rows']:
                if k in set_:
                    kind = c.split(':')[0]; new = set_[k]
                    if new.split(':')[0] != kind and not (kind == 'u' and new.startswith('u:')):   # keep the vanilla cell kind
                        new = kind + ':' + vehcfg.text(new)
                    c = new
                rows.append([k, c])
            t['rows'] = rows
        elif name in ('heads', 'work_places', 'sights', 'damages', 'mslots', 'crew_fireplaces'):
            t = dict(S.table(name)); t['rows'] = [r for r in t['rows'] if ok(r)]
            if name == 'heads':   # SU-122: 20 deg sector (+-10), -3..+25 deg (ru.wikipedia, Modelist-Konstruktor)
                r = list(t['rows'][0]); r[3] = 'f:10'; r[4] = 'f:10'; r[5] = 'f:25'; r[6] = 'f:3'; t['rows'] = [r]
            if name == 'sights':  # v31: the gunner's panorama (hood on the roof, camera s_camera_gunner_01) is the M-30's
                pg = next(r for r in M.table('sights')['rows'] if vehcfg.text(r[2]) == 'pg')   # panoramic sight 'pg'
                t['rows'] = [[r[0], r[1], pg[2]] + list(r[3:]) if vehcfg.text(r[0]) == 'sig_gunner_01' else r for r in t['rows']]
        elif name == 'weapons':   # v31: the M-30's own weapon row (breech block d_zatvor swings -110 deg), the SU-152's smoke grenades
            t = dict(M.table(name)); rows = [list(r) for r in t['rows'] if ok(r)]
            rows += [list(r) for r in S.table(name)['rows'] if vehcfg.text(r[0]) == 'GREN_TR' and ok(r)]
            t['rows'] = rows
        elif name == 'shells':    # v31: the M-30's shell types in the SU-122's 40 rounds (mostly HE; HEAT from May 1943; a
            t = dict(S.table(name))   # few shrapnel and smoke rounds as on the towed gun), the SU-152's hand grenades
            t['rows'] = [['s:122L22_OF_462', 'u:30'], ['s:122L22_BP_460A', 'u:6'], ['s:122L22_SH_460', 'u:2'], ['s:122L22_D_462A', 'u:2'],
                         ['s:RDG', 'u:12'], ['s:RGD_33', 'u:13']]
        elif name == 'addins':    # v31: the barrel and the breech block are add-in meshes with the M-30's texture, on the
            t['rows'] = [r for r in t['rows'] if ok(r)]   # recoil node and the breech node themselves (Pz III L / M: PZ3_GUN on d_gun)
            t['rows'] += [['s:SU122_BARREL', 's:d_gun'] + ['f:0'] * 6, ['s:SU122_BREECH', 's:d_zatvor'] + ['f:0'] * 6]
        elif name == 'hatchs':
            rows = []
            for r in T.table('hatchs')['rows']:
                who = vehcfg.text(r[0]); r = list(r)
                if who == 'gunner': r[0] = 's:commander'; r[3] = 'f:120'   # v34: the lid on its side rod tips over to the right (user: "tip it to the side")
                if who == 'driver': r[3] = 'f:-25'   # the SU-122 driver's hatch could not open fully (recoil-gear armour in the way)
                rows.append(r)
            t['rows'] = [r for r in rows if ok(r)]
        elif name == 'random':      # the four side fuel tanks are always fitted on the SU-122
            t['rows'] = [r for r in t['rows'] if ok(r) and 'fueltank' not in vehcfg.text(r[0])]
        elif name == 'col_bounds':
            t['rows'] = [r for r in t['rows'] if ok(r)]
        else:
            t['rows'] = [r for r in t['rows'] if ok(r)]
        out.append(t)
    return out, T.root_type

ADDINS = (('SU122_BARREL', 'su122_barrel'), ('SU122_BREECH', 'su122_breech'))

def addin_registry_delta():
    """v31a: rows for the common_res_mod 'addins' registry (tabs.flatdata) - every add-in the addins table of a vehicle
    names must be registered here with its mesh, shader and textures (modelled on PZ3_GUN: sh_object_wea, weathering on,
    3 LODs); the M-30's textures. Without these rows the game draws nothing where the add-in should be."""
    out = ['# SU-122 (1943) gun add-ins - generated by tools\\m13\\su122_config.py: the M-30 barrel and breech block meshes',
           '#   (src\\m13_vehicles\\mfo_gos\\su122_barrel / su122_breech) with the M-30 textures, as PZ3_GUN is registered']
    for name, mesh in ADDINS:
        out.append('row+|addins|@end|%s|s:%s|s:%s|s:sh_object_wea|b:0|b:0|f:1|s:m30m38_dift|s:m30m38_norsp|s:|v:0|v:0|v:0|b:1|s:|f:0|s:|b:0|u:3|s:|u:0|s:' % (name, name, mesh))
    return out

if __name__ == '__main__':
    tables, rt = build(*sys.argv[1:4])
    lines = ['# SU-122 (1943) - generated by tools\\m13\\su122_config.py: T-34 mod. 1942 running gear, SU-152 crew layout, M-30S']
    lines += vehcfg.node_delta('su122', tables, after='@end', root_type=rt)
    open(sys.argv[4], 'w', encoding='cp1251', newline='\n').write('\n'.join(lines) + '\n')
    print(len(lines), 'lines;', {t['name']: len(t['rows']) for t in tables})
    if len(sys.argv) > 5:                                   # v31a: the add-in registry delta (common_res_mod)
        reg = addin_registry_delta(); open(sys.argv[5], 'w', encoding='cp1251', newline='\n').write('\n'.join(reg) + '\n')
        print(len(reg), 'registry lines ->', sys.argv[5])

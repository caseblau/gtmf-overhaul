"""M3 Lee rows for ui_params (techns, managed) and its English name.

  python m3lee_tables.py <ui_params.bin> <repo 00_loc_kit_weaps.text.loc_eng.bin> <outdir> [div_units_ussr.bin]
Writes into <outdir>: ui_params.config.loc_def.13_m3lee.delta and 00_loc_kit_weaps.text.loc_eng.bin (the repo's file +
ui_m3_lee); with the 4th argument also div_units_ussr.config.loc_def.13_m3lee.delta: the unit rkkau_m3lee (crew 6) with
its tank / platoon / company / battalion commander squads on the M4A2's rows (Lend-Lease link, 12.1942 - 12.1943) and
six-man crews (the M4A2's five plus a machine-gunner). Figures: TM 9-750 / Hunnicutt - 27.2 t, 5.64 x 2.72 x 3.12 m, 435 mm clearance, crew 6 (Soviet vehicles),
75 mm M3 (-9 .. +20, 15 deg each side) + 37 mm M6 + 4 x M1919A4 (coaxial, cupola, two fixed bow guns), 46 / 178 / 9200 rounds, 51 / 38 / 38 / 13 mm hull,
51 mm turret, R-975 340 hp, 662 l, 193 km road range, 39 km/h. In service with the Red Army 1942-1943 (Lend-Lease).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import vehcfg, textpack
from su122_tables import table, find, row

def main(ui, weaps_txt, out):
    U = ['# M3 Lee UI rows (tools\\m13\\m3lee_tables.py): M4A2 Sherman layout, the Lee\'s own figures']
    t = find(table(ui, 'techns'), 'm4a2_sherman')
    t[0] = 's:m3lee'; t[1] = 's:ui_m3_lee'
    t[2] = 'v:51;38;38;13'; t[3] = 'v:51;38;38;13'; t[4] = 'v:51;51;51;22'     # upper hull / lower hull / turret (mm)
    t[10] = 's:m3lee'; t[13] = 'f:27.2'; t[14] = 'a:1941;1942;1942;6258'
    t[16] = 'a:5639;2718;3124;435'; t[17] = 'a:6'
    t[19] = 's:M3'; t[20] = 'v:-9;20;-15;15'; t[21] = 's:M6'; t[22] = 's:M1919A4'
    t[23] = 'a:1;1;4'; t[24] = 'a:46;178;9200'
    t[25] = 's:sight_m4'; t[26] = 's:sight_m40a2'
    t[27] = 's:'                                                                 # no R-975 entry in the game's engine list
    t[29] = 'a:340;193;105;662'; t[30] = 'a:39;20;420;96'; t[31] = 'v:30;0.6;1.9;1'
    t[36] = 's:'                                                                 # no encyclopedia page
    t[42] = 's:m3lee'                                            # techn_base_oprum.cfgpack (t[41]) as the M4A2
    U.append(row('techns', t))
    mg = find(table(ui, 'managed'), 'm4a2_sherman'); mg[0] = 's:m3lee'; U.append(row('managed', mg))
    open(os.path.join(out, 'ui_params.config.loc_def.13_m3lee.delta'), 'w', encoding='cp1251', newline='\n').write('\n'.join(U) + '\n')
    loc, items = textpack.read(weaps_txt)
    items = [x for x in items if x[0] != 'ui_m3_lee'] + [('ui_m3_lee', ['M3 "Lee"', 'Lee'])]
    textpack.write(os.path.join(out, '00_loc_kit_weaps.text.loc_eng.bin'), loc, items)
    print('written', out)

def units(div, out):
    U = ['# M3 Lee unit, crews and squads (tools\\m13\\m3lee_tables.py): the M4A2 Sherman rows, crew 6']
    u = find(table(div, 'units'), 'rkkau_m4a2'); u[0] = 's:rkkau_m3lee'; u[1] = 's:ui_m3_lee'; u[4] = 's:m3lee'; u[5] = 'u:6'; U.append(row('units', u))
    sq = table(div, 'squads')
    for suf, crew, com in (('', 'm4', 'com'), ('_com', 'pcom5a', 'pcom'), ('_ccom', 'ccom5a', 'ccom'), ('_bcom', 'bcom5a', 'bcom')):
        c = find(sq, 'rkka_crew_' + crew); c[0] = 's:rkka_crew_m3lee' + suf
        c[18:26] = ['s:rkkau_tank_' + com, 'u:1', 's:rkkau_tank_agun', 'u:1', 's:rkkau_tank_mgun', 'u:1', 's:rkkau_tank_pistol', 'u:3']
        U.append(row('squads', c))
    for suf in ('', '_com', '_ccom', '_bcom'):
        r = find(sq, 'rkka_m4a2' + suf); r[0] = 's:rkka_m3lee' + suf; r[18] = 's:rkkau_m3lee'; r[20] = 's:rkka_crew_m3lee' + suf
        U.append(row('squads', r))
    open(os.path.join(out, 'div_units_ussr.config.loc_def.13_m3lee.delta'), 'w', encoding='cp1251', newline='\n').write('\n'.join(U) + '\n')

if __name__ == '__main__':
    main(*sys.argv[1:4])
    if len(sys.argv) > 4: units(sys.argv[4], sys.argv[3])

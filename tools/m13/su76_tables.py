"""SU-76M rows for div_units_ussr (unit + squads), ui_params (techns, managed) and the English names.

  python su76_tables.py <div_units_ussr.bin> <ui_params.bin> <repo 00_loc_kit_weaps text> <repo m7 01_loc_kit_units text> <outdir>
Writes into <outdir>: div_units_ussr.config.loc_def.13_su76m.delta, ui_params.config.loc_def.13_su76m.delta,
00_loc_kit_weaps.text.loc_eng.bin (the repo's file + ui_su76m), 01_loc_kit_units.text.loc_eng.bin (the repo's m7 file +
the three squad names). Figures: SU-76M, 1943 - 10.6 t, 5.00 x 2.72 x 2.10 m, 300 mm clearance, crew 4, ZiS-3Sh
(-3 .. +25 deg, 15 deg either side, 60 rounds), Hertz panorama, 2 x GAZ-202 170 hp, 412 l, 45 km/h, 320 km on roads;
armour 35 / 25 mm front, 15 mm hull sides and rear, 25 mm casemate front, 10 mm casemate sides, open top. Squads use
the 4-man SPG crew of the captured StuG (rkka_crew_stug3) and the 4-man command crews; in service from June 1943.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import vehcfg, textpack
from su122_tables import table, find, row

def main(div, ui, weaps_txt, units_txt, out):
    L = ['# SU-76M unit and squads (tools\\m13\\su76_tables.py); 4-man SPG crews']
    u = find(table(div, 'units'), 'rkkau_su152')
    u[0] = 's:rkkau_su76m'; u[1] = 's:ui_su76m'; u[4] = 's:su76m'; u[5] = 'u:4'; u[6] = 'u:12'; u[16] = 's:76L42'
    L.append(row('units', u))
    sq = table(div, 'squads')
    for src, dst, crew, cost in (('rkka_su152', 'rkka_su76m', 'rkka_crew_stug3', 'a:600;18;33;9'),
                                 ('rkka_su152_com', 'rkka_su76m_com', 'rkka_crew_pcom4', 'a:650;19;33;9'),
                                 ('rkka_su152_ccom', 'rkka_su76m_ccom', 'rkka_crew_ccom4', 'a:700;19;33;9')):
        r = find(sq, src); r[0] = 's:' + dst; r[5] = 's:' + dst; r[8] = cost
        r[13] = 'u:0x19430601'; r[14] = 'u:0x19451201'          # SU-76M: in service from June 1943
        r[18] = 's:rkkau_su76m'; r[20] = 's:' + crew
        L.append(row('squads', r))
    open(os.path.join(out, 'div_units_ussr.config.loc_def.13_su76m.delta'), 'w', encoding='cp1251', newline='\n').write('\n'.join(L) + '\n')
    U = ['# SU-76M UI rows (tools\\m13\\su76_tables.py): SU-152 SPG layout, T-70 automotive figures where they apply']
    t = find(table(ui, 'techns'), 'su152'); t70 = find(table(ui, 'techns'), 't70m')
    t[0] = 's:su76m'; t[1] = 's:ui_su76m'
    t[2] = 'v:35;15;15;7'; t[3] = 'v:25;15;15;7'; t[4] = 'v:25;10;10;0'     # upper hull / lower hull / casemate: front side rear top (mm)
    t[9] = 's:spg'; t[10] = 's:su76m'; t[13] = 'f:10.6'; t[14] = 'a:1943;1945;1943;14292'
    t[16] = 'a:5000;2715;2100;300'; t[17] = 'a:4'; t[18] = t70[18]
    t[19] = 's:ZIS3'; t[20] = 'v:-3;25;-15;15'; t[21] = 's:'; t[22] = 's:'; t[23] = 'a:1'; t[24] = 'a:60'
    t[25] = 's:sight_hertz'; t[26] = 's:'
    t[27] = t70[27]; t[28] = t70[28]                                           # GAZ engine, gearbox 4 + 1
    t[29] = 'a:170;320;190;412'; t[30] = 'a:45;20;260'; t[31] = 'v:28;0.6;1.6;0.9'
    t[34] = t70[34]; t[35] = 's:'; t[36] = 's:'                                 # T-70 track; no encyclopedia page
    t[42] = 's:su76m'
    U.append(row('techns', t))
    mg = find(table(ui, 'managed'), 'su152'); mg[0] = 's:su76m'; U.append(row('managed', mg))
    open(os.path.join(out, 'ui_params.config.loc_def.13_su76m.delta'), 'w', encoding='cp1251', newline='\n').write('\n'.join(U) + '\n')
    loc, items = textpack.read(weaps_txt)
    items = [x for x in items if x[0] != 'ui_su76m'] + [('ui_su76m', ['SU-76M', 'SU-76M'])]
    textpack.write(os.path.join(out, '00_loc_kit_weaps.text.loc_eng.bin'), loc, items)
    loc, items = textpack.read(units_txt)
    new = [('rkka_su76m', ['Self-propelled gun SU-76M']), ('rkka_su76m_com', ['Self-propelled gun SU-76M (cmd)']),
           ('rkka_su76m_ccom', ['Self-propelled gun SU-76M (coy cmd)'])]
    items = [x for x in items if x[0] not in dict(new)] + new
    textpack.write(os.path.join(out, '01_loc_kit_units.text.loc_eng.bin'), loc, items)
    print('written', out)

if __name__ == '__main__':
    main(*sys.argv[1:6])

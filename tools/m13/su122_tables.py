"""SU-122 rows for div_units_ussr (unit + squads), ui_params (techns, managed) and the English names.

  python su122_tables.py <div_units_ussr.bin> <ui_params.bin> <vanilla 00_loc_kit_weaps text> <m7 01_loc_kit_units text> <outdir>
Writes into <outdir>: div_units_ussr.config.loc_def.13_su122.delta, ui_params.config.loc_def.delta,
00_loc_kit_weaps.text.loc_eng.bin (vanilla + ui_su122), 01_loc_kit_units.text.loc_eng.bin (m7's file + 2 squad names).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import azcf, vehcfg, textpack

def table(path, name):
    b, ns = azcf.read(path); n = next(x for x in ns if x['name'] == name); out = []
    for r in range(n['rows']):
        o = n['data'] + r * 0x20 * n['cols']; out.append([vehcfg.cell(b, o + c * 0x20) for c in range(n['cols'])])
    return out

def find(rows, key): return list(next(r for r in rows if vehcfg.text(r[0]) == key))

def row(path, r): return 'row+|%s|@end|%s|%s' % (path, vehcfg._esc(vehcfg.text(r[0])), '|'.join(r))

def main(div, ui, weaps_txt, units_txt, out):
    L = ['# SU-122 unit and squads (tools\\m13\\su122_tables.py); crew squads of the SU-152 (5 men) reused']
    u = find(table(div, 'units'), 'rkkau_su152')
    u[0] = 's:rkkau_su122'; u[1] = 's:ui_su122'; u[4] = 's:su122'; u[16] = 's:122L22'
    L.append(row('units', u))
    sq = table(div, 'squads')
    for src, dst in (('rkka_su152', 'rkka_su122'), ('rkka_su152_com', 'rkka_su122_com')):
        r = find(sq, src); r[0] = 's:' + dst; r[5] = 's:' + dst
        r[13] = 'u:0x19421201'; r[14] = 'u:0x19430901'          # in service Dec 1942 - summer 1943
        r[18] = 's:rkkau_su122'
        L.append(row('squads', r))
    open(os.path.join(out, 'div_units_ussr.config.loc_def.13_su122.delta'), 'w', encoding='cp1251', newline='\n').write('\n'.join(L) + '\n')
    U = ['# SU-122 UI rows (tools\\m13\\su122_tables.py): SU-152 SPG layout, T-34 automotive figures']
    t = find(table(ui, 'techns'), 'su152'); t34 = find(table(ui, 'techns'), 't34_utz_m42')
    t[0] = 's:su122'; t[1] = 's:ui_su122'
    t[2] = 'v:45;45;40;20'; t[3] = 'v:45;45;45;20'; t[4] = 'v:45;45;40;20'     # front / side / rear / roof (mm)
    t[9] = 's:med_spg' if False else t[9]
    t[10] = 's:su122'; t[13] = 'f:30.9'; t[14] = 'a:1942;1943;1943;638'
    t[16] = 'a:6950;3000;2235;400'; t[19] = 's:M30'; t[20] = 'v:-3;25;-10;10'
    for k in (26, 27, 28, 29, 30, 31, 32, 33, 34): t[k] = t34[k]                  # engine, gears, power / speed / range, tracks
    t[35] = 's:'; t[36] = 's:'                                                  # no encyclopedia page
    t[42] = 's:su122'
    U.append(row('techns', t))
    mg = find(table(ui, 'managed'), 'su152'); mg[0] = 's:su122'; U.append(row('managed', mg))
    open(os.path.join(out, 'ui_params.config.loc_def.delta'), 'w', encoding='cp1251', newline='\n').write('\n'.join(U) + '\n')
    loc, items = textpack.read(weaps_txt)
    items = [x for x in items if x[0] != 'ui_su122'] + [('ui_su122', ['SU-122 mod 1943', 'SU-122'])]
    textpack.write(os.path.join(out, '00_loc_kit_weaps.text.loc_eng.bin'), loc, items)
    loc, items = textpack.read(units_txt)
    items = [x for x in items if x[0] not in ('rkka_su122', 'rkka_su122_com')] + [('rkka_su122', ['Assault howitzer SU-122']), ('rkka_su122_com', ['Assault howitzer SU-122 (cmd)'])]
    textpack.write(os.path.join(out, '01_loc_kit_units.text.loc_eng.bin'), loc, items)
    print('written', out)

if __name__ == '__main__':
    main(*sys.argv[1:6])

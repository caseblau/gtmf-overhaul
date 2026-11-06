"""docs/m11_prokhorovka/layout_1011jul.json = the first 12 turns of layout_10jul.json (10-11 July operation): run after any change
to layout_10jul.json.   python tools\make_layout_1011.py"""
import json, copy, os
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'docs', 'm11_prokhorovka')
d = json.load(open(os.path.join(D, 'layout_10jul.json'), encoding='utf-8')); n = copy.deepcopy(d)
n['_comment'] = ("10-11 July 1943 operation (12 turns from 06:00 10 July) = the first half of the 10-13 July campaign (layout_10jul.json, turns 1-12) "
                 "as a separate operation: same layout, frames 1-12, reinforcements arriving after turn 12 left out. Regenerate it from layout_10jul.json "
                 "after any change there (tools/make_layout_1011.py).")
n['turns'] = 12; n['frames'] = d['frames'][:12]
n['units'] = [u for u in d['units'] if u.get('turn', 1) <= 12]
n['air'] = {k: v for k, v in d['air'].items() if v <= 12}
n['objectives'] = [{'name': nm, 'xy': xy, 'value': v} for nm, xy, v in (   # 10-11 July: II SS-Panzerkorps' tasks of 9 / 10 July (Zamulin ch. 6-7)
    ('svkh. Komsomolets', [8468, 8939], 9), ('height 241.6', [9600, 10288], 8), ('svkh. Oktyabrsky', [11900, 13100], 9), ('height 252.2', [13120, 12768], 9),
    ('height 226.6 (Psel bridgehead)', [6720, 15136], 8), ('Storozhevoye', [11674, 9147], 6), ('Ivanovsky Vyselok', [8640, 8256], 5), ('Vasilyevka', [6236, 13132], 4))]
n['kp_cap'] = 2
n['_comment_objectives'] = ('10-11 July: LSSAH to take svkh. Komsomolets, 241.6, then svkh. Oktyabrsky and 252.2 (Operational Order No. 17, 9 July); Totenkopf the '
                            'Psel bridgehead and 226.6; Das Reich Ivanovsky Vyselok and Storozhevoye; the Soviet rear army belt to hold them')
b = n['briefing']
for k in ('op_name', 'op_name1'): b[k] = b[k].replace('July 10 - 13, 1943', 'July 10 - 11, 1943')
for k in ('op_name_rus', 'op_name1_rus'): b[k] = b[k].replace('10 - 13 июля 1943', '10 - 11 июля 1943')
keep = {f['brief'] for f in n['frames'] if f['brief']}
for k in ('briefs', 'briefs_rus', 'briefs_ger', 'briefs_ger_rus'):
    if k in b: b[k] = {kk: v for kk, v in b[k].items() if kk in keep}
json.dump(n, open(os.path.join(D, 'layout_1011jul.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print(len(n['units']), 'units, briefs', sorted(keep))

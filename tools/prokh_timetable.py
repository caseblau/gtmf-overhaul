r"""Prokhorovka briefings the Warsaw way - 22 Nov 2026 (user: "fix the map briefings to match how other operations use, like
okuniew and radzymin").

The Warsaw operations (tools/op_timetable.py) give every turn a briefing - the hand-written text where there is one, then the
turn's tasks from the historic timetable - fill the history panel's turnNN / _plan / _result keys, and draw a sketch for every
turn in the data style of briefing.from_spec (no front lines, unit symbols with defence arcs / assembly ovals, the turn's
attacks and moves as arrows, all pulled onto the map). The Prokhorovka packs had briefings on 10 of 24 turns and the old
hand-coded sketches (front lines, fixed arrows). This module feeds the same op_timetable functions with the Prokhorovka
timetable (tools/ai_orders.py, squares of the old 7 x 5 frame: block square = frame square + SQ_DX / SQ_DY) and makes the
base sketch of each operation from its layout (one symbol per division / corps / brigade, as briefing.FORMATIONS groups them).
Only the Prokhorovka path of tools/prokh_op.py calls it; the Warsaw tables in op_timetable are swapped back afterwards.
"""
import math
import prokh_gen as G
import op_timetable as OT
import briefing as B

# AI group id (tools/oob_12jul.ps1 $AI) -> (side, English, Russian)
NAMES = {
    'L1': ('GER', '1 SS-Pz.Gren.Rgt. LSSAH', '1-й мп СС «Лейбштандарт»'), 'L2': ('GER', '2 SS-Pz.Gren.Rgt. LSSAH', '2-й мп СС «Лейбштандарт»'),
    'LT': ('GER', 'SS-Pz.Rgt. 1', '1-й тп СС'), 'LS': ('GER', 'LSSAH assault guns', 'штурмовые орудия «Лейбштандарта»'),
    'LA': ('GER', 'LSSAH anti-tank battalion', 'противотанковый дивизион «Лейбштандарта»'), 'LAR': ('GER', 'SS-Pz.Art.Rgt. 1', '1-й ап СС'),
    'DL': ('GER', 'SS-Pz.Gren.Rgt. Deutschland', 'полк СС «Дойчланд»'), 'DF': ('GER', 'SS-Pz.Gren.Rgt. Der Fuehrer', 'полк СС «Дер Фюрер»'),
    'DRT': ('GER', 'SS-Pz.Rgt. 2', '2-й тп СС'), 'ST2': ('GER', 'Das Reich assault guns', 'штурмовые орудия «Дас Райх»'),
    'EIC': ('GER', 'SS-Pz.Gren.Rgt. 6 Eicke', 'полк СС «Эйке»'), 'TUL': ('GER', 'SS-Pz.Gren.Rgt. 5 Thule', 'полк СС «Туле»'),
    'TKT': ('GER', 'SS-Pz.Rgt. 3', '3-й тп СС'), 'ST3': ('GER', 'Totenkopf assault guns', 'штурмовые орудия «Мёртвой головы»'),
    'B99': ('USSR', '99th Tank Bde', '99-я тбр'), 'B26': ('USSR', '26th Tank Bde', '26-я тбр'), 'B169': ('USSR', '169th Tank Bde', '169-я тбр'),
    'M58': ('USSR', '58th Motor Rifle Bde', '58-я мсбр'), 'M11': ('USSR', '11th Motor Rifle Bde', '11-я мсбр'),
    'R15': ('USSR', '15th Gds Heavy Tank Rgt', '15-й гв. ттп'),
    'B110': ('USSR', '110th Tank Bde', '110-я тбр'), 'B170': ('USSR', '170th Tank Bde', '170-я тбр'), 'B181': ('USSR', '181st Tank Bde', '181-я тбр'),
    'M32': ('USSR', '32nd Motor Rifle Bde', '32-я мсбр'), 'R36': ('USSR', '36th Gds Heavy Tank Rgt', '36-й гв. ттп'),
    'B25': ('USSR', '25th Tank Bde', '25-я тбр'), 'B31': ('USSR', '31st Tank Bde', '31-я тбр'), 'B32': ('USSR', '32nd Tank Bde', '32-я тбр'),
    'M53': ('USSR', '53rd Motor Rifle Bde', '53-я мсбр'), 'S146': ('USSR', '1446th SP Artillery Rgt', '1446-й сап'),
    'B4G': ('USSR', '4th Gds Tank Bde', '4-я гв. тбр'), 'B25G': ('USSR', '25th Gds Tank Bde', '25-я гв. тбр'), 'B26G': ('USSR', '26th Gds Tank Bde', '26-я гв. тбр'),
    'M4G': ('USSR', '4th Gds Motor Rifle Bde', '4-я гв. мсбр'), 'R47': ('USSR', '47th Gds Heavy Tank Rgt', '47-й гв. ттп'),
    'B10G': ('USSR', '10th Gds Mech Bde', '10-я гв. мбр'), 'R51': ('USSR', '51st Gds Tank Rgt', '51-й гв. тп'), 'B24G': ('USSR', '24th Gds Tank Bde', '24-я гв. тбр'),
    'S147': ('USSR', '1447th SP Artillery Rgt', '1447-й сап'), 'S152': ('USSR', '1529th Heavy SP Artillery Rgt', '1529-й тсап'),
    'R53': ('USSR', '53rd Gds Tank Rgt', '53-й гв. тп'), 'R148': ('USSR', '148th Gds Tank Rgt', '148-й гв. тп'),
    'R227': ('USSR', '227th Rifle Rgt', '227-й сп'), 'R285': ('USSR', '285th Rifle Rgt', '285-й сп'), 'R295': ('USSR', '295th Rifle Rgt', '295-й сп'),
    'R151': ('USSR', '151st Gds Rifle Rgt', '151-й гв. сп'), 'R153': ('USSR', '153rd Gds Rifle Rgt', '153-й гв. сп'), 'R155': ('USSR', '155th Gds Rifle Rgt', '155-й гв. сп'),
    'R245': ('USSR', '245th Tank Rgt', '245-й отп'),
    'R23': ('USSR', '23rd Gds Airborne Rgt', '23-й гв. вдсп'), 'R26': ('USSR', '26th Gds Airborne Rgt', '26-й гв. вдсп'), 'R28': ('USSR', '28th Gds Airborne Rgt', '28-й гв. вдсп'),
    'R284': ('USSR', '284th Gds Rifle Rgt', '284-й гв. сп'), 'R287': ('USSR', '287th Gds Rifle Rgt', '287-й гв. сп'), 'R290': ('USSR', '290th Gds Rifle Rgt', '290-й гв. сп'),
    'R127': ('USSR', '127th Gds Rifle Rgt', '127-й гв. сп'), 'R132': ('USSR', '132nd Gds Rifle Rgt', '132-й гв. сп'), 'R136': ('USSR', '136th Gds Rifle Rgt', '136-й гв. сп'),
    'D97': ('USSR', '97th Gds Rifle Div', '97-я гв. сд'), 'D93': ('USSR', '93rd Gds Rifle Div', '93-я гв. сд'),
    'R278': ('USSR', '278th Gds Rifle Rgt', '278-й гв. сп'), 'R281': ('USSR', '281st Gds Rifle Rgt', '281-й гв. сп'), 'R28G': ('USSR', '285th Gds Rifle Rgt', '285-й гв. сп'),
}
PARENT = {'R278': 'D93', 'R281': 'D93', 'R28G': 'D93'}
# gazetteer in the timetable's squares (old 7 x 5 frame, x east, y south; tools/ai_orders.py)
PLACES = [((1, 2), 'Kozlovka', 'Козловка'), ((2, 3), 'Vasilyevka', 'Васильевка'), ((4, 2), 'Andreyevka', 'Андреевка'), ((5, 2), 'Mikhailovka', 'Михайловка'),
          ((2, 1), 'height 226.6', 'высота 226,6'), ((6, 2), 'Prelestnoye', 'Прелестное'), ((8, 4), 'svkh. Oktyabrsky', 'свх. Октябрьский'),
          ((8, 3), 'height 252.2', 'высота 252,2'), ((4, 7), 'svkh. Komsomolets', 'свх. Комсомолец'), ((5, 6), 'height 241.6', 'высота 241,6'),
          ((7, 7), 'Storozhevoye', 'Сторожевое'), ((4, 9), 'Ivanovsky Vyselok', 'Ивановский Выселок'), ((2, 9), 'height 258.2', 'высота 258,2'),
          ((1, 9), 'Teterevino', 'Тетеревино'), ((5, 9), 'Yasnaya Polyana', 'Ясная Поляна'), ((11, 2), 'Prokhorovka station', 'ст. Прохоровка'),
          ((5, 12), 'Belenikhino', 'Беленихино'), ((7, 10), 'Vinogradovka', 'Виноградовка'), ((-2, 12), 'Kalinin', 'Калинин'),
          ((-1, 2), 'Krasny Oktyabr', 'Красный Октябрь'), ((-1, -1), 'Veselyi', 'Весёлый'), ((4, 0), 'Polezhayev', 'Полежаев'), ((6, 0), 'Petrovka', 'Петровка')]

H = G.ROWS * G.CELL   # block height, metres


def install():
    """point op_timetable at the Prokhorovka tables (this build process only builds Prokhorovka operations)"""
    OT.NAMES = NAMES; OT.PARENT = PARENT; OT.PLACES = dict(OT.PLACES, Prokh=PLACES)


def setup(TT, layout, fr):
    """the Prokhorovka counterpart of prokh_op's Warsaw timetable step: TT['to'] (op turn -> orders), the brief key of every
    frame (campaign-numbered, as the layouts' hand-written briefs: brief_13 = turn 1 of the 12 July operation)"""
    import ai_orders
    install()
    off = int(layout.get('turn_offset', 0))
    TT['block'] = 'Prokh'; TT['koff'] = off
    TT['to'] = OT.turn_orders(ai_orders.ORDERS, len(fr), off, G.SQ_DX, G.SQ_DY, B.W_SQ, B.H_SQ)
    TT['hand'] = {f.get('brief') for f in fr if f.get('brief')}
    for k, f in enumerate(fr): f['brief'] = f.get('brief') or 'brief_%02d' % (k + 1 + off)
    print('  timetable (Prokhorovka): %d turns, %d scripted orders, briefings on all turns (%d hand-written)' % (len(fr), sum(len(v) for v in TT['to'].values()), len(TT['hand'])))


def _m(c):
    """frame squares (what briefing.N expects without BLOCK) -> block metres (x east, y north)"""
    return [round((c[0] + G.SQ_DX) * 1024.0), round(H - (c[1] + G.SQ_DY) * 1024.0)]


def base_spec(layout):
    """the turn-1 picture of a layout as a briefing.from_spec spec: one symbol per formation at the centre of its manoeuvre
    groups (briefing.FORMATIONS), facing the front, rifle divisions with a defence arc; corps / army names and key heights as labels"""
    front = [B._sq(x, y) for x, y in layout['front']]
    sm = B.smooth(front, 206)
    pos = {}
    for u in layout['units']:
        if u.get('turn', 1) != 1: continue
        pos.setdefault(u['form'][0], []).extend(B._sq(x, y) for x, y in u['pos'])
    syms = []
    for key, kind, members in B.FORMATIONS:
        pts = [p for m in members for p in pos.get(m, [])]
        if not pts: continue
        c = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
        syms.append(dict(key=key, kind=kind, c=c, ger=members[0].startswith('we'), r=B.R_SYM * (0.6 if kind == 'arty' else 1.0)))
    B._declutter(syms, sm)
    units = []
    for a in syms:
        q = B._near(sm, a['c'])[0]
        u = dict(key=a['key'], kind=a['kind'], side='GER' if a['ger'] else 'USSR', xy=_m(a['c']), toward=_m(q))
        if a['kind'] == 'inf': u.update(posture='defend', frontage=1.6)
        units.append(u)
    labels = []
    for key, hq in B.GROUPS:
        if hq in pos: labels.append(dict(key=key, xy=_m(pos[hq][0]), size=1.4))
    for key, c in B.HEIGHTS: labels.append(dict(key=key, xy=_m((c[0] + 0.45, c[1] - 0.25)), size=0.8))
    return dict(units=units, labels=labels, thrusts=[])


def sketches(layout, TO, koff):
    """{brief key: spec} for every turn: the operation's base picture with that turn's attacks (solid) and moves (dashed) from the
    nearest own symbol to the objective - op_timetable.sketches in the Prokhorovka frame"""
    base = base_spec(layout); units = base['units']; out = {}
    for t in sorted(TO):
        thr = []; done = set()
        for k, i, x, y in TO[t]:
            if k == 'recon' or i not in NAMES: continue
            side = NAMES[i][0]; tx, ty = _m((x + 0.5, y + 0.5))
            own = [u for u in units if u['side'] == side]
            if not own: continue
            u = min(own, key=lambda u: (u['xy'][0] - tx) ** 2 + (u['xy'][1] - ty) ** 2); sx, sy = u['xy']
            d = math.hypot(sx - tx, sy - ty)
            if d < 900: continue
            if d > 7000: sx, sy = tx + (sx - tx) * 2500 / d, ty + (sy - ty) * 2500 / d
            kk = (side, round(sx / 500), round(sy / 500), round(tx / 500), round(ty / 500))
            if kk in done: continue
            done.add(kk)
            mx, my = (sx + tx) / 2 + (ty - sy) * 0.08, (sy + ty) / 2 - (tx - sx) * 0.08
            thr.append(dict(side=side, pts=[[sx, sy], [mx, my], [tx, ty]], dash=(k == 'move')))
        out['brief_%02d' % (t + koff)] = dict(units=units, labels=base['labels'], thrusts=thr)
    return out

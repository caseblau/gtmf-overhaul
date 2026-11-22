r"""The historic timetable of a Warsaw operation (M16 Okuniew / M18 Radzymin) applied three ways - 20 Nov 2026 (user: "There were
historic timetables for attacks, and they are absent now, the enemies move and attack freely ... the briefings that are written need
to be added by each turn and on map briefings should be improved further"):

  1. postures   the operation's ai_orders table (the vanilla 'timetable' of AI postures: HOLD | DEF | RET, id;turn;side - Stepanovka
                has HOLD for every group at turn 1, DEF / RET rows for some groups from later turns). Ours had HOLD at turn 1 only, so
                a group that had once been sent to attack by the turn script (tools/okun_ai.py, radz_ai.py) went on attacking on its
                own for the rest of the operation. Now: after every run of scripted turns a DEF row from the next turn - the group
                stops and defends where it got to until its next historic order.
  2. briefings  every turn gets a briefing: the hand-written one where there is one, else one made from the turn's historic orders;
                each closes with the turn's timetable - our formations' tasks and what is known of the enemy's.
  3. sketches   every turn without a drawn sketch gets one: the last drawn sketch's units and labels with this turn's attacks
                (solid arrows) and moves (dashed) from the nearest own unit symbol to the objective.

Orders: ORDERS[campaign turn] = [(kind, ai id, x, y)], x, y op-map squares of the block (1024 m; y south from the north edge).
"""
import os, re, json, math, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------------ AI groups: id -> (side, English, Russian)
NAMES = {
    'WK': ('GER', 'Wiking', '«Викинг»'), 'W9': ('GER', 'SS-Pz.Gren.Rgt. 9 Germania', 'полк СС «Германия»'),
    'W10': ('GER', 'SS-Pz.Gren.Rgt. 10 Westland', 'полк СС «Вестланд»'), 'WT': ('GER', 'SS-Pz.Rgt. 5', '5-й тп СС'),
    'WS': ('GER', 'Wiking assault guns', 'штурмовые орудия «Викинга»'), 'WAR': ('GER', 'SS-Pz.Art.Rgt. 5', '5-й ап СС'),
    'WKG': ('GER', 'Kampfgruppe Muehlenkamp', 'боевая группа Мюленкампа'),
    'TK': ('GER', 'Totenkopf', '«Мёртвая голова»'), 'T5': ('GER', 'SS-Pz.Gren.Rgt. 5 Thule', 'полк СС «Туле»'),
    'T6': ('GER', 'SS-Pz.Gren.Rgt. 6 Eicke', 'полк СС «Эйке»'), 'TT': ('GER', 'SS-Pz.Rgt. 3', '3-й тп СС'),
    'TS': ('GER', 'Totenkopf assault guns', 'штурмовые орудия «Мёртвой головы»'), 'TAR': ('GER', 'SS-Pz.Art.Rgt. 3', '3-й ап СС'),
    'P19': ('GER', '19. Pz.Div.', '19-я тд'), 'P19T': ('GER', 'Pz.Rgt. 27', '27-й тп'), 'P73': ('GER', 'Pz.Gren.Rgt. 73', '73-й мпп'),
    'P4': ('GER', '4. Pz.Div.', '4-я тд'), 'P4T': ('GER', 'Pz.Rgt. 35', '35-й тп'), 'P12': ('GER', 'Pz.Gren.Rgt. 12', '12-й мпп'),
    'P49': ('GER', 'Pz.Jg.Abt. 49', '49-й птд'), 'P4K': ('GER', 'Kampfgruppe of 4. Pz.Div.', 'боевая группа 4-й тд'),
    'HG': ('GER', 'Hermann Goering', '«Герман Геринг»'), 'HGT': ('GER', 'Fs.Pz.Rgt. HG', 'тп «Герман Геринг»'),
    'HG1': ('GER', 'Fs.Pz.Gren.Rgt. 2 HG', '2-й мпп «Герман Геринг»'), 'K39': ('GER', 'XXXIX. Pz.Korps', '39-й тк'),
    'G113': ('GER', 'Gren.Brig. 1131', '1131-я пбр'), 'I73': ('GER', '73. Inf.Div.', '73-я пд'), 'I170': ('GER', 'Gren.Rgt. 170', '170-й пп'),
    'I186': ('GER', 'Gren.Rgt. 186', '186-й пп'), 'I213': ('GER', 'Gren.Rgt. 213', '213-й пп'), 'I173': ('GER', 'Art.Rgt. 173', '173-й ап'),
    'U2TA': ('USSR', '2nd Tank Army', '2-я ТА'), 'T3': ('USSR', 'III Tank Corps', '3-й тк'), 'B51': ('USSR', '51st Tank Brigade', '51 тбр'),
    'B103': ('USSR', '103rd Tank Brigade', '103 тбр'), 'M57': ('USSR', '57th Motor Rifle Brigade', '57 мсбр'),
    'T8G': ('USSR', 'VIII Guards Tank Corps', '8-й гв. тк'), 'B58': ('USSR', '58th Guards Tank Brigade', '58 гв. тбр'),
    'B59': ('USSR', '59th Guards Tank Brigade', '59 гв. тбр'), 'B60': ('USSR', '60th Guards Tank Brigade', '60 гв. тбр'),
    'M28': ('USSR', '28th Guards Motor Rifle Brigade', '28 гв. мсбр'), 'U47': ('USSR', '47th Army', '47-я армия'),
    'C125': ('USSR', '125th Rifle Corps', '125 ск'), 'C129': ('USSR', '129th Rifle Corps', '129 ск'), 'C77': ('USSR', '77th Rifle Corps', '77 ск'),
    'R62G': ('USSR', '62nd Guards Heavy Tank Regiment', '62 гв. ттп'), 'S301': ('USSR', '301st Guards SU Regiment', '301 гв. сап'),
    'S181': ('USSR', '1817th SU Regiment', '1817 сап'), 'S385': ('USSR', 'III TC SU-85 regiment', 'полк СУ-85 3 тк'), 'S376': ('USSR', 'III TC SU-76 regiment', 'полк СУ-76 3 тк'),
    'D76': ('USSR', '76th Rifle Division', '76 сд'), 'R93': ('USSR', '93rd Rifle Regiment', '93 сп'), 'R207': ('USSR', '207th Rifle Regiment', '207 сп'),
    'R216': ('USSR', '216th Rifle Regiment', '216 сп'), 'H80': ('USSR', '80th Artillery Regiment', '80 ап'),
    'D175': ('USSR', '175th Rifle Division', '175 сд'), 'R277': ('USSR', '277th Rifle Regiment', '277 сп'), 'R278': ('USSR', '278th Rifle Regiment', '278 сп'),
    'R282': ('USSR', '282nd Rifle Regiment', '282 сп'), 'H373': ('USSR', '373rd Artillery Regiment', '373 ап'),
    'D143': ('USSR', '143rd Rifle Division', '143 сд'), 'R487': ('USSR', '487th Rifle Regiment', '487 сп'), 'R635': ('USSR', '635th Rifle Regiment', '635 сп'),
    'R800': ('USSR', '800th Rifle Regiment', '800 сп'), 'H287': ('USSR', '287th Artillery Regiment', '287 ап'),
    'D185': ('USSR', '185th Rifle Division', '185 сд'), 'R257': ('USSR', '257th Rifle Regiment', '257 сп'), 'R280': ('USSR', '280th Rifle Regiment', '280 сп'),
    'R131': ('USSR', '1319th Rifle Regiment', '1319 сп'), 'H695': ('USSR', '695th Artillery Regiment', '695 ап'),
    'D328': ('USSR', '328th Rifle Division', '328 сд'), 'R110': ('USSR', '1103rd Rifle Regiment', '1103 сп'), 'R11B': ('USSR', '1105th Rifle Regiment', '1105 сп'),
    'R11C': ('USSR', '1107th Rifle Regiment', '1107 сп'), 'H889': ('USSR', '889th Artillery Regiment', '889 ап'), 'R259': ('USSR', '259th Tank Regiment', '259 тп'),
    'K2G': ('USSR', 'II Guards Cavalry Corps', '2-й гв. кк'), 'K3G': ('USSR', '3rd Guards Cavalry Division', '3 гв. кд'),
    'K9': ('USSR', '9th Guards Cavalry Regiment', '9 гв. кп'), 'K10': ('USSR', '10th Guards Cavalry Regiment', '10 гв. кп'),
    'K12': ('USSR', '12th Guards Cavalry Regiment', '12 гв. кп'), 'H179': ('USSR', '179th Guards Mortar Regiment', '179 гв. минп'),
    'R160': ('USSR', '160th Tank Regiment', '160 тп'), 'U70': ('USSR', '70th Army', '70-я армия'),
    'D38G': ('USSR', '38th Guards Rifle Division', '38 гв. сд'), 'G110': ('USSR', '110th Guards Rifle Regiment', '110 гв. сп'),
    'G13B': ('USSR', '113th Guards Rifle Regiment', '113 гв. сп'), 'G115': ('USSR', '115th Guards Rifle Regiment', '115 гв. сп'),
    'H48G': ('USSR', '48th Guards Artillery Regiment', '48 гв. ап'), 'R129': ('USSR', '1295th Rifle Regiment', '1295 сп'),
    'S182': ('USSR', '1821st SU Regiment', '1821 сап'), 'S298': ('USSR', '298th Guards SU Regiment', '298 гв. сап'), 'S129': ('USSR', '1295th SU Regiment', '1295 сап'),
    'D76G': ('USSR', '76th Guards Rifle Division', '76 гв. сд'), 'G239': ('USSR', '239th Guards Rifle Regiment', '239 гв. сп'),
    'G76B': ('USSR', '76th Gds RD, 2nd regiment', '2-й полк 76 гв. сд'), 'D165': ('USSR', '165th Rifle Division', '165 сд'),
    'R165': ('USSR', '165th RD, 1st regiment', '1-й полк 165 сд'), 'R16B': ('USSR', '165th RD, 2nd regiment', '2-й полк 165 сд'),
    'D260': ('USSR', '260th Rifle Division', '260 сд'), 'R102': ('USSR', '1026th Rifle Regiment', '1026 сп'), 'R10B': ('USSR', '1028th Rifle Regiment', '1028 сп'),
    'R103': ('USSR', '1030th Rifle Regiment', '1030 сп'), 'H783': ('USSR', '783rd Artillery Regiment', '783 ап'),
}
# the division / corps an order to which also covers its regiments' (the regiment ids then repeat the same task: one line)
PARENT = {'R93': 'D76', 'R207': 'D76', 'R216': 'D76', 'R277': 'D175', 'R278': 'D175', 'R282': 'D175', 'R487': 'D143', 'R635': 'D143', 'R800': 'D143',
          'R257': 'D185', 'R280': 'D185', 'R131': 'D185', 'R110': 'D328', 'R11B': 'D328', 'R11C': 'D328', 'G110': 'D38G', 'G13B': 'D38G', 'G115': 'D38G',
          'G239': 'D76G', 'G76B': 'D76G', 'R165': 'D165', 'R16B': 'D165', 'R102': 'D260', 'R10B': 'D260', 'R103': 'D260',
          'K9': 'K3G', 'K10': 'K3G', 'K12': 'K3G'}

# ------------------------------------------------------------------ gazetteer: block squares (x east, y south) -> (English, Russian)
PLACES = {
    'Okun': [((1, 9), 'Okuniew', 'Окунев'), ((2, 6), 'Zabraniec', 'Забранец'), ((5, 6), 'Krubki', 'Крубки'), ((6, 9), 'Michalow', 'Михалув'),
             ((3, 10), 'Budziska', 'Будзиска'), ((3, 12), 'Dluga Koscielna', 'Длуга-Косцельна'), ((4, 14), 'Halinow', 'Халинув'),
             ((6, 14), 'Cisie', 'Цисе'), ((7, 13), 'Desno', 'Десно'), ((11, 9), 'Pustelnik', 'Пустельник'), ((12, 9), 'Gozdziowka', 'Гоздзювка'),
             ((14, 8), 'Zalesie', 'Залесе'), ((17, 7), 'Stanislawow', 'Станиславов'), ((16, 12), 'Ladzyn', 'Ладзынь'), ((17, 10), 'Lubomin', 'Любомин'),
             ((9, 17), 'Debe Wielkie', 'Дембе-Вельке')],
    'Radz': [((10, 10), 'Klembow', 'Клембув'), ((10, 8), 'Sitki', 'Ситки'), ((13, 6), 'Krusze', 'Круше'), ((12, 9), 'Pienki', 'Пенки'),
             ((15, 9), 'Jasienica', 'Ясеница'), ((16, 10), 'Jadwinin', 'Ядвинин'), ((17, 7), 'Tluszcz', 'Тлущ'), ((14, 5), 'Kozly', 'Козлы'),
             ((15, 5), 'Wolka Kozlowska', 'Вулька-Козловска'), ((15, 3), 'Fabianow', 'Фабянув'), ((10, 2), 'Trojany', 'Трояны'),
             ((9, 14), 'Stare Grabie', 'Старе-Грабе'), ((10, 12), 'Krzywica', 'Кшивица'), ((8, 12), 'Dobczyn', 'Добчин'), ((9, 6), 'Marcinowek', 'Марцинувек')],
}
COMPASS = [('east', 'к востоку'), ('north-east', 'к северо-востоку'), ('north', 'к северу'), ('north-west', 'к северо-западу'),
           ('west', 'к западу'), ('south-west', 'к юго-западу'), ('south', 'к югу'), ('south-east', 'к юго-востоку')]
MONTHS = (None, ('January', 'января'), ('February', 'февраля'), ('March', 'марта'), ('April', 'апреля'), ('May', 'мая'), ('June', 'июня'),
          ('July', 'июля'), ('August', 'августа'), ('September', 'сентября'), ('October', 'октября'), ('November', 'ноября'), ('December', 'декабря'))
FOURCC = lambda s: sum(ord(c) << (8 * i) for i, c in enumerate(s[:4]))
SIDE_U32 = {'GER': FOURCC('GER'), 'USSR': FOURCC('USSR')}


def ai_prefixes():
    """id -> formation pool name (p_...) from tools/oob_okun.ps1 ($AI table)"""
    t = open(os.path.join(ROOT, 'oob_okun.ps1'), encoding='utf-8').read()
    m = re.search(r'\$AI = @\{(.*?)\n\}', t, re.S)
    return {v: k for k, v in re.findall(r"(p_\w+) = '(\w+)'", m.group(1))} if m else {}


def turn_orders(ORDERS, turns, off, dx, dy, w, h):
    """{op turn: [(kind, id, x, y)]} - the orders the turn script will carry (block squares; outside the window dropped)"""
    return {t: [(k, i, x, y) for k, i, x, y in ORDERS.get(t + off, []) if 0 <= x + dx < w and 0 <= y + dy < h] for t in range(1, turns + 1)}


def postures(TO, turns):
    """[(kind, id, turn)]: DEF from the turn after each run of scripted turns of a group (none past the operation's end)"""
    act = {}
    for t, os_ in TO.items():
        for _, i, _, _ in os_: act.setdefault(i, set()).add(t)
    rows = []
    for i, ts in sorted(act.items()):
        for t in sorted(ts):
            if t + 1 not in ts and t + 1 <= turns: rows.append(('DEF', i, t + 1))
    return rows


def delta_rows(rows):
    """op_body.delta lines appending the posture rows to ai_orders (a table: the key of a row+ @end is not used)"""
    out = []
    for k, (kind, i, t) in enumerate(rows):
        side = NAMES.get(i, ('USSR',))[0]
        out.append('row+|ai_orders|@end|tt%d|a:%d|a:%d;%d;%d' % (k, FOURCC(kind), FOURCC(i), t, SIDE_U32[side]))
    return out


def _where(x, y, places, ru):
    """the objective square as a phrase: 'Okuniew' / '2 km north-east of Okuniew'"""
    cx, cy = x + 0.5, y + 0.5
    best = min(places, key=lambda p: (p[0][0] + 0.5 - cx) ** 2 + (p[0][1] + 0.5 - cy) ** 2)
    dx, dy = cx - best[0][0] - 0.5, cy - best[0][1] - 0.5; d = math.hypot(dx, dy) * 1.024
    nm = best[2] if ru else best[1]
    if d < 1.2: return nm
    k = int(round(math.degrees(math.atan2(-dy, dx)) / 45.0)) % 8
    return ('%s (%d км %s)' % (nm, round(d), COMPASS[k][1])) if ru else ('%s (%d km %s)' % (nm, round(d), COMPASS[k][0]))


VERB = {False: {'attack': 'attack towards', 'recon': 'reconnoitre and screen towards', 'move': 'move to'},
        True: {'attack': 'атака, направление:', 'recon': 'разведка и прикрытие, направление:', 'move': 'выдвижение в район:'}}


def _lines(os_, side, places, ru, own):
    """the turn's tasks of one side, one line per task (formations with the same task and objective in one line; a regiment
    repeating its division's task is folded into the division)"""
    tasks = {}
    for k, i, x, y in os_:
        if NAMES.get(i, ('?',))[0] != side: continue
        par = PARENT.get(i)
        if par and any(o[1] == par and (o[0], o[2], o[3]) == (k, x, y) for o in os_): continue
        if not own and k == 'recon': continue                       # what is known of the enemy: his attacks and moves
        nm = NAMES[i][2 if ru else 1]; lst = tasks.setdefault((k, _where(x, y, places, ru)), [])
        if nm not in lst: lst.append(nm)
    return ['%s - %s %s' % (', '.join(v), VERB[ru][k], w) for (k, w), v in tasks.items()]


def clock(layout, t):
    """(English, Russian) 'HH:MM, D Month' of the start of op turn t"""
    iv = lambda v: int(v, 0) if isinstance(v, str) else int(v)     # the layouts write '0x19440803' (BCD) as text or as a number
    db = '%x' % iv(layout.get('date_beg', 0x19440801)); tb = '%04x' % iv(layout.get('time_beg', 0x600))
    d0 = datetime.datetime(int(db[:4]), int(db[4:6]), int(db[6:8]), int(tb[:2]), int(tb[2:]))
    d = d0 + datetime.timedelta(hours=int(layout.get('hours_per_turn', 4)) * (t - 1))
    return '%02d:%02d, %d %s' % (d.hour, d.minute, d.day, MONTHS[d.month][0]), '%02d:%02d, %d %s' % (d.hour, d.minute, d.day, MONTHS[d.month][1])


def turn_texts(layout, block, TO, t, ger, ru):
    """{text key: text} of op turn t for the operation's history panel (20 Nov, user: "???" under every TURN line).
    adv_opgame builds the keys turn%02u, turn%02u_plan and turn%02u_result (strings of the module); the op packs had
    none, so the panel printed ???. turnNN: one line - the side's main task; _plan: the side's tasks and what intelligence
    expects; _result: what both sides historically did in that turn (the timetable of tools/okun_ai.py / radz_ai.py)."""
    places = PLACES[block]; own, foe = ('GER', 'USSR') if ger else ('USSR', 'GER')
    os_ = TO.get(t, []); mine = _lines(os_, own, places, ru, True); theirs = _lines(os_, foe, places, ru, False)
    hist = _lines(os_, own, places, ru, True) + _lines(os_, foe, places, ru, True)
    hd = clock(layout, t)[1 if ru else 0]
    if mine: title = mine[0] + ('' if len(mine) == 1 else (' (и ещё %d задачи)' % (len(mine) - 1) if ru else ' (and %d more task%s)' % (len(mine) - 1, '' if len(mine) == 2 else 's')))
    else: title = 'Удерживать рубежи, разведка, пополнение' if ru else 'Hold the line, patrol, resupply'
    plan = [('Задачи наших частей по плану: ' if ru else 'Our tasks by the plan: ') + ('; '.join(mine) + '.' if mine else ('удерживать рубежи.' if ru else 'hold the line.'))]
    if theirs: plan.append(('Разведка доносит: ' if ru else 'Intelligence expects: ') + '; '.join(theirs) + '.')
    if hist: res = ('Исторически (%s): ' % hd if ru else 'Historically (%s): ' % hd) + '; '.join(hist) + '.'
    else: res = ('Исторически (%s): без крупных боёв, стороны удерживали рубежи.' % hd if ru else 'Historically (%s): no major fighting, both sides held their lines.' % hd)
    k = '%02d' % t
    return {'turn' + k: title, 'turn' + k + '_plan': '\n'.join(plan), 'turn' + k + '_result': res}


def brief_text(layout, block, TO, t, ger, ru, hand=None):
    """the briefing of op turn t for the side (ger) and language (ru): the hand-written text (or a heading) + the turn's timetable"""
    places = PLACES[block]; own, foe = ('GER', 'USSR') if ger else ('USSR', 'GER')
    os_ = TO.get(t, []); mine = _lines(os_, own, places, ru, True); theirs = _lines(os_, foe, places, ru, False)
    turns = int(layout.get('turns', 24)); hd = clock(layout, t)[1 if ru else 0]
    head = hand.strip() if hand else ('%s. Ход %d из %d.' % (hd, t, turns) if ru else '%s. Turn %d of %d.' % (hd, t, turns))
    parts = [head]
    if mine: parts.append(('Задачи наших частей по плану: ' if ru else 'Our tasks by the plan: ') + '; '.join(mine) + '.')
    else: parts.append('Активных действий не планируется: удерживать рубежи, вести разведку, пополниться.' if ru
                       else 'No attacks are planned: hold the line, patrol, resupply.')
    if theirs: parts.append(('Разведка доносит: ' if ru else 'Intelligence expects: ') + '; '.join(theirs) + '.')
    return '\n\n'.join(parts)


def raw_layout(G):
    return json.load(open(os.environ.get('MFO_LAYOUT') or G.repo_path(G.BLOCK['layout']), encoding='utf-8'))


def sketches(layout_raw, TO, G, keys_drawn):
    """{brief key: spec} for every turn without a drawn sketch: the last drawn sketch's units and labels, this turn's attacks / moves"""
    sk = layout_raw.get('sketches', {}); H = int(G.BLOCK['rows']) * float(G.BLOCK['cell'])
    def spec_of(k):
        while k in sk and isinstance(sk[k], str): k = sk[k]
        return sk.get(k)
    out = {}; base = None
    for t in sorted(TO):
        key = 'brief_%02d' % t
        if key in sk:
            base = spec_of(key); continue
        if base is None:
            base = next((spec_of(k) for k in sorted(sk) if spec_of(k)), None)
            if base is None: continue
        # 20 Nov: only the units inside the operation's map window (block metres, y north) start arrows / are drawn
        ar = layout_raw.get('area'); C_ = float(G.BLOCK['cell'])
        inw = (lambda p: (ar[0] - 1) * C_ <= p[0] <= ar[2] * C_ and H - ar[3] * C_ <= p[1] <= H - (ar[1] - 1) * C_) if ar else (lambda p: True)
        units = base.get('units', []); thr = []; done = set()   # off-map units are drawn at the map edge (briefing.from_spec)
        for k, i, x, y in TO[t]:
            if k == 'recon' or i not in NAMES: continue
            side = NAMES[i][0]; tx, ty = x * 1024.0 + 512.0, H - (y * 1024.0 + 512.0)
            own = [u for u in units if u.get('side') == side]
            if own:
                u = min(own, key=lambda u: (u['xy'][0] - tx) ** 2 + (u['xy'][1] - ty) ** 2); sx, sy = u['xy']
                if math.hypot(sx - tx, sy - ty) < 900: continue                   # the symbol stands on its objective already
                if math.hypot(sx - tx, sy - ty) > 7000:                           # far: a 2.5 km arrow from that direction
                    d = math.hypot(sx - tx, sy - ty); sx, sy = tx + (sx - tx) * 2500 / d, ty + (sy - ty) * 2500 / d
            else: continue
            kk = (side, round(sx / 500), round(sy / 500), round(tx / 500), round(ty / 500))
            if kk in done: continue
            done.add(kk)
            mx, my = (sx + tx) / 2 + (ty - sy) * 0.08, (sy + ty) / 2 - (tx - sx) * 0.08   # a slight bow, as drawn by hand
            thr.append(dict(side=side, pts=[[sx, sy], [mx, my], [tx, ty]], dash=(k == 'move')))
        out[key] = dict(units=units, labels=base.get('labels', []), thrusts=thr)
    return out

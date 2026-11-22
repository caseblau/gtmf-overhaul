r"""Operation body generator for the Prokhorovka test operation (M11).

The test operation is the 30 July 1943 Stepanovka `.campack2` re-pointed at the Prokh polygon (build_prokh.ps1 step 4).
Its desc still carries the Stepanovka operation body: a movement graph over 14 x 10 operational squares, platoon
positions on that graph and the op-map markers, so battles can only be started in the north-west corner of the new
22 x 24 square area. This script writes a gt3 delta that replaces those three tables (and the sector boundary markers
the tac_limits refer to), plus op text packs with the marker names:

  py -3 tools\prokh_op.py --osm docs\m12_terrain\osm\prokh.osm.json --cells build\prokhorovka\cells
        --opdir build\prokhorovka\op_GER
        [--front 7.5,2.8,13,10.4,14.3,19.1,15,24]   front line as x,y square pairs (x from the west, y from the north edge), west/north
        end first; the Germans hold the side with the south-west corner (Territory).  A layout file's 'front' key overrides it.
  needs <opdir>\mg_nodes.csv, plat_pos.csv and tac_markers.csv exported with gt3.ps1 csv (build_prokh.ps1 does that);
  writes <opdir>\op_body.delta and <opdir>\text.text.loc_eng.bin / loc_rus.bin (markers added; originals kept as *.orig)
  and caches the 64 m block DEM (for the hilltops) in <cells>\..\block_h64.npy.

Table formats (decoded 2026-10-23 from 07_30_Stepanovka_GER, build 3598; coordinates: op squares are 1024 m, x from the
west edge of camp_area, y from its NORTH edge; the cells table rows also run north -> south):
  mg_nodes  type 2, 13 cols a a a v v a a a a a a a a
       c0 a:x;y;nlinks;edge   op square, number of links listed in c5..c12, edge = 1 on the nodes of the border
                             squares (the rear "back line" where reinforcements arrive; border squares have 4 nodes,
                             interior squares 2 - a node with edge = 1 is NOT a movement node)
       c1 a:side;0;0;flags   owner: u32 fourcc 'USSR' (1381192533) or 'GDR' (5391687). flags: low bits describe the
                             square (1 hamlet/farm, 2 height, 16 woods/gully, 32 settlement) and bits 11+ make the node a
                             key point: value << 11 (vanilla: Saur-Mogila 8, height 277.9 9, Marinovka 4, Stepanovka
                             south 4, height 223 3, height 214.0 2, several 1); the label the game shows for a key point
                             is the nearest tac_marker.
       c2 a:uid;-1;-1;-1     occupant: uid of the platoon standing on the node (one unit per node; the engine reads
                             placements from plat_pos AND this column - two units on one node crash the game)
       c3 v:dx;0;dy          node position relative to the square centre, metres (dy > 0 = SOUTH, checked in game 25 Oct), always +-256
       c4 v:0
       c5..c12 a:i;j;k;l     indices into mg_links, -1 padded (max 32 links)
  mg_links  type 2, 2 cols: a:nodeA;nodeB;2[;k] | v:cost   cost = length in km (0.5, 0.707, 1.0); each link once
  plat_pos  type 2, 2 cols: a:uid;x;y;node | a:... (per-platoon flags, kept)   units off map: -1;-1;-1
  tac_markers type 2, 4 cols: v:x;0;y (metres inside the CELL, x from west, y from north) | v:w;0;h (label box) |
       a:cell_col;cell_row;level;1 (cells table coordinates, level 0..5 = label importance) | s:text key (op text pack)
       The bnd_* rows are the sector boundary symbols that tac_limits names.
"""
import sys, os, csv, math, argparse, shutil, json, re
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prokh_gen as G, textpack

SQ = 1024.0
COLS_SQ, ROWS_SQ = G.COLS * 2, G.ROWS * 2   # 18 x 18 squares (9 x 9 cells)
CELL_X0, CELL_Y0 = G.CELL_X0, G.CELL_Y0     # camp_area origin in the cells table (1;1;9;9)
USSR = 1381192533; GDR = 5391687
HQ_STACK = 1   # HQ-type units per border node at turn 1 (layout 'hq_stack')
HQ_MIN_FRONT, HQ_MIN_FRONT_DIV, ART_MIN_FRONT = 3000.0, 5000.0, 2500.0
DIV_HQ_RE = r'^(ra_(\d+g?rd|\d+gabd|\d+g?tc|\d+gmc|\d+g?rc|\d+g?cc|5gta|5ga)|we_(lah|dr|tk|wk|hg|19pd|4pd|73id)|we_2tc_ss)_(hq|spam|cons)\d*$'   # layout 'hq_min_front' / 'art_min_front': metres a command post / a battery keeps behind the front in hq_field mode
HIGHER_HQ_RE = r'^(ra_(\d+g?tc|\d+g?mc|\d+g?rc|\d+g?sk|\d+g?ta|\d+g?a)|we_\d+tc_ss|we_\d+pzk|we_4sspzk)_(hq|spam|cons)\d*$'
# 5 Nov (user: "the higher unit HQ should be placed on the cells on the edges of maps like army, corps - they shouldn't be on
# the battlefield itself but on cells in reserve"): army and corps command posts with their supply / construction elements
# (II SS-PzK, 2 / 2 gds / 18 / 29 TC, 5 gds MC, 33 gds / 48 RC, any army HQ) always go to the own rear map edge, also in
# hq_field mode; divisions, brigades, regiments and below keep their field positions
HQ_FIELD = False   # layout 'hq_field': HQ-type elements (HQs, supply, construction, artillery) stand in the field at their 'hq' position instead of on the map edge
# 14 Nov (user: "the village names are suppost to be in polish instead of russian"): a block with 'names': 'pl' shows the Polish name (ASCII) in both
# text packs unless 'names_rus' is 'cyr'. Read from the block config here, so it does not depend on which prokh_gen.py is beside this file.
PL_RUS_LATIN = bool(G.BLOCK and G.BLOCK.get('names') == 'pl' and G.BLOCK.get('names_rus', 'latin') == 'latin')
REPORT = []    # (platoon name, 'hq' | 'bg', node index, side) of every unit placed at turn 1 -> placement_report.csv
PINS = {}      # layout 'pin': battle-group platoon name -> [X, Y] op-map squares
# 14 Nov (user: "units on operational phase that are part of one unit are far apart from eachother"): layout 'hq_near' (metres;
# block builds default 2500 - the vanilla 07_30 Stepanovka p90 of HQ -> own battle group is 2.6 km; 0 = off, the Prokhorovka
# default): HQ-type elements stand near their own battle groups instead of 3-5 km behind the front line or on any free border node
# of their side (08_01: five Wiking HQs on the west edge 6.2-6.8 km from their battalions), and a reinforcement formation arrives
# on one stretch of edge instead of being split across the map (08_01: 19. Pz.Div. west, its 73rd regiment east)
HQ_NEAR = 0.0
HQ_BEHIND, HQ_BEHIND_DIV, FRONT_FLOOR = 1200.0, 2500.0, 800.0   # metres: vanilla 07_30 HQs stand a median 2.6 km from the nearest enemy node, their battle groups 1.0 km
BG_AT = {}     # formation prefix -> [(mx, my)] of its placed turn-1 battle groups (hq_near)
OLD_COLS, OLD_ROWS = 14, 10                 # Stepanovka square grid
F_HAMLET, F_HEIGHT, F_WOODS, F_VILLAGE = 1, 2, 16, 32
QUARTERS = ((256, 256), (-256, -256), (-256, 256), (256, -256))   # NE, SW (interior); + NW, SE on border squares
H_BLOCK = G.ROWS * G.CELL

def esc(s): return s.replace('\\', '\\\\').replace('|', '\\|')
def fmt(v): return ('%.6g' % v)

def front_x(front, y):
    """x of the front line at square row y (polyline, extended flat beyond its ends) - test deployment without a layout."""
    if y <= front[0][1]: return front[0][0]
    for (x0, y0), (x1, y1) in zip(front, front[1:]):
        if y <= y1: return x0 + (x1 - x0) * (y - y0) / (y1 - y0)
    return front[-1][0]

class Territory:
    """Which side holds a point of the op map at turn 1.  The front is a polyline in square units (x from the west edge,
    y from the NORTH edge) that starts on the west or north map edge and ends on the south or east edge; the Germans hold
    the part containing the south-west corner.  25 Oct: the user drew the German line of the morning of 10 July on the op
    map (Kozlovka - W of Vasilyevka - W of svkh. Komsomolets - E of Teterevino), so the line may run east-west as well as
    north-south and is tested as a polygon, not as x(y)."""
    more = []   # 13 Nov: further German-held patches (layout 'ger_poly2'), e.g. the map edge a relief force enters by
    def __init__(self, front, ger_poly=None):
        self.front = [(float(x), float(y)) for x, y in front]
        if ger_poly:   # M16 (Okuniew): the layout gives the German-held ground itself (squares), e.g. the east of the map
            self.poly = [(float(x), float(y)) for x, y in ger_poly]; return
        poly = list(self.front)
        ex, ey = poly[-1]
        if ex >= COLS_SQ - 1e-6 and ey < ROWS_SQ - 1e-6: poly.append((COLS_SQ, ROWS_SQ))   # ends on the east edge
        poly.append((0.0, ROWS_SQ))                                                           # south-west corner
        sx, sy = poly[0]
        if sy <= 1e-6 and sx > 1e-6: poly.append((0.0, 0.0))                                  # starts on the north edge
        self.poly = poly
    def dist(self, x, y):
        """distance (squares) from a point to the front polyline"""
        best = 1e9
        for (x0, y0), (x1, y1) in zip(self.front, self.front[1:]):
            dx, dy = x1 - x0, y1 - y0; L2 = dx * dx + dy * dy or 1e-9
            t = max(0.0, min(1.0, ((x - x0) * dx + (y - y0) * dy) / L2))
            best = min(best, math.hypot(x - (x0 + t * dx), y - (y0 + t * dy)))
        return best
    def ger(self, x, y):
        """square coordinates (x from the west, y from the north) -> True where the Germans hold the ground"""
        return _inside(self.poly, x, y) or any(_inside(pl, x, y) for pl in self.more)
    def side(self, x, y): return GDR if self.ger(x, y) else USSR

def to_sq(px, py):
    """block metres (x east, y north from the south edge) -> op square (x, y from north) and metres inside the area"""
    mx, my = px, H_BLOCK - py
    return int(mx // SQ), int(my // SQ), mx, my

class Graph:
    def __init__(self, terr):
        self.terr = terr
        self.nodes = []; self.by_sq = {}
        for y in range(ROWS_SQ):
            for x in range(COLS_SQ):
                edge = x == 0 or y == 0 or x == COLS_SQ - 1 or y == ROWS_SQ - 1
                for dx, dy in (QUARTERS if edge else QUARTERS[:2]):
                    self.by_sq.setdefault((x, y), []).append(len(self.nodes))
                    mx, my = x * SQ + 512 + dx, y * SQ + 512 + dy   # the node offset dy is positive SOUTHWARD (seen in game 25 Oct: HQs meant for the outer row of the south edge landed on the inner one)
                    self.nodes.append(dict(x=x, y=y, dx=dx, dy=dy, edge=int(edge), mx=mx, my=my,
                                           side=terr.side(mx / SQ, my / SQ), flags=0, uid=-1, more=[]))
        # links: every pair closer than 1.1 km (512 m orthogonal, 724 m diagonal, 1024 m straight across a square)
        self.links = []; self.nl = [[] for _ in self.nodes]
        for i, a in enumerate(self.nodes):
            for ddx in (-1, 0, 1):
                for ddy in (-1, 0, 1):
                    for j in self.by_sq.get((a['x'] + ddx, a['y'] + ddy), []):
                        if j <= i: continue
                        b = self.nodes[j]; d = math.hypot(a['mx'] - b['mx'], a['my'] - b['my'])
                        if d > 1100 or len(self.nl[i]) >= 32 or len(self.nl[j]) >= 32: continue
                        k = len(self.links); self.links.append((i, j, d / 1000.0)); self.nl[i].append(k); self.nl[j].append(k)
    def nearest(self, mx, my, interior=True, free=False, side=None):
        """nearest node to (mx, my): interior (movement) nodes only, free ones only, own-side ground only"""
        best = None; bd = 1e9
        x, y = int(mx // SQ), int(my // SQ)
        for r in range(0, max(COLS_SQ, ROWS_SQ)):
            for ddx in range(-r, r + 1):
                for ddy in range(-r, r + 1):
                    if max(abs(ddx), abs(ddy)) != r: continue
                    for j in self.by_sq.get((x + ddx, y + ddy), []):
                        n = self.nodes[j]
                        if interior and n['edge']: continue
                        if free and n['uid'] != -1: continue
                        if side is not None and n['side'] != side: continue
                        d = math.hypot(n['mx'] - mx, n['my'] - my)
                        if d < bd: bd, best = d, j
            if best is not None: return best
        return best
    def edge_node(self, mx, my, edge, free=True):
        """nearest border-square node on the given map edge (N/E/S/W) to the point (metres, my from the north)"""
        best = None; bd = 1e18
        for j, n in enumerate(self.nodes):
            if not n['edge']: continue
            if edge == 'N' and n['y'] != 0: continue
            if edge == 'S' and n['y'] != ROWS_SQ - 1: continue
            if edge == 'W' and n['x'] != 0: continue
            if edge == 'E' and n['x'] != COLS_SQ - 1: continue
            if free and n['uid'] != -1: continue
            d = (n['mx'] - mx) ** 2 + (n['my'] - my) ** 2
            if d < bd: bd, best = d, j
        return best
    def rows(self):
        out = []
        for i, n in enumerate(self.nodes):
            ids = self.nl[i] + [-1] * (32 - len(self.nl[i]))
            occ = ([n['uid']] + n.get('more', []) + [-1] * 4)[:4]
            out.append([f"a:{n['x']};{n['y']};{len(self.nl[i])};{n['edge']}", f"a:{n['side']};0;0;{n['flags']}", 'a:' + ';'.join(str(v) for v in occ),
                        f"v:{n['dx']};0;{n['dy']}", 'v:0'] + [f'a:{";".join(str(v) for v in ids[k:k + 4])}' for k in range(0, 32, 4)])
        return out

def read_csv(path):
    return list(csv.reader(open(path, encoding='utf-8-sig')))[1:]

def ints(cell, n=4):
    v = [int(float(t)) for t in cell.split(';')] if cell else []
    return (v + [0] * n)[:n]

def block_dem(cells_dir, cache):
    """64 m DEM of the whole block (row 0 = south) from the PHA6 heightmaps, cached as .npy"""
    if os.path.exists(cache): return np.load(cache)
    from pha6 import decode
    S = 64; n = int(G.CELL) // S
    H = np.zeros((G.ROWS * n, G.COLS * n), np.float32)
    for j in range(G.ROWS):
        for i in range(G.COLS):
            name = G.cell_name(i, j); p = G.hei_path(cells_dir, i, j)
            h, _ = decode(p); h = h * (G.MAXH / 65535.0); k = h.shape[0] // n
            x0, y0 = int(i * G.CELL), int((G.ROWS - 1 - j) * G.CELL)   # block frame
            H[y0 // S:y0 // S + n, x0 // S:x0 // S + n] = h.reshape(n, k, n, k).mean(axis=(1, 3))
            print('  dem', name, flush=True)
    np.save(cache, H); return H

def hilltops(H, S=64, n_max=24):
    """local maxima standing >= 15 m above their 2.6 km surroundings, >= 2.5 km apart, away from the block edge:
    (height, x metres, y metres north)"""
    from PIL import Image, ImageFilter
    im = Image.fromarray(H)
    mx = np.asarray(im.filter(ImageFilter.MaxFilter(25))); mn = np.asarray(im.filter(ImageFilter.MinFilter(41)))
    peaks = np.argwhere((H >= mx) & (H - mn >= 15))
    cand = sorted([(float(H[y, x]), x, y) for y, x in peaks], reverse=True); keep = []
    for h, x, y in cand:
        if min(x, y, H.shape[1] - 1 - x, H.shape[0] - 1 - y) * S < 700: continue
        if all((x - kx) ** 2 + (y - ky) ** 2 >= (2500 / S) ** 2 for _, kx, ky in keep): keep.append((h, x, y))
    return [(h, (x + 0.5) * S, (y + 0.5) * S) for h, x, y in keep[:n_max]]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--osm', required=True); ap.add_argument('--opdir', required=True); ap.add_argument('--cells', required=True)
    ap.add_argument('--front', default='0,2.3,3.8,5.7,4.8,7.7,6.7,10', help='x,y square pairs north to south (block squares; the layout "front" key in old-frame metres overrides)')
    ap.add_argument('--layout', default=None, help='docs/m11_prokhorovka/layout_12jul.json: historical deployment, named heights, strongpoints, minefields')
    a = ap.parse_args()
    layout = json.load(open(a.layout, encoding='utf-8')) if a.layout and os.path.exists(a.layout) else None
    if layout: layout = shift_layout(layout)   # layout files are written in the DEM-lattice frame
    fv = [float(v) for v in a.front.split(',')]; front = list(zip(fv[0::2], fv[1::2]))
    if layout and layout.get('front'):   # old-frame metres, west/north end first -> block squares (x from the west, y from the north edge)
        front = [(x / SQ, (H_BLOCK - y) / SQ) for x, y in layout['front']]
    gp = [(x / SQ, (H_BLOCK - y) / SQ) for x, y in layout['ger_poly']] if layout and layout.get('ger_poly') else None
    terr = Territory(front, gp)
    if layout and layout.get('ger_poly2'): terr.more = [[(x / SQ, (H_BLOCK - y) / SQ) for x, y in pl] for pl in layout['ger_poly2']]
    global HQ_STACK, HQ_FIELD, HQ_MIN_FRONT, HQ_MIN_FRONT_DIV, ART_MIN_FRONT, PINS, HQ_NEAR; HQ_STACK = int(layout.get('hq_stack', 1)) if layout else 1; HQ_FIELD = bool(layout.get('hq_field', False)) if layout else False
    if layout: HQ_MIN_FRONT = float(layout.get('hq_min_front', HQ_MIN_FRONT)); HQ_MIN_FRONT_DIV = float(layout.get('hq_min_front_div', HQ_MIN_FRONT_DIV)); ART_MIN_FRONT = float(layout.get('art_min_front', ART_MIN_FRONT))
    PINS = {k: (v[0] + G.SQ_DX, v[1] + G.SQ_DY) for k, v in (layout.get('pin', {}) if layout else {}).items()}   # pins are authored in the 7 x 5 frame
    HQ_NEAR = float(layout.get('hq_near', 2500.0 if G.BLOCK else 0.0)) if layout else 0.0
    old_nodes = read_csv(os.path.join(a.opdir, 'mg_nodes.csv')); plat = read_csv(os.path.join(a.opdir, 'plat_pos.csv'))
    old_markers = read_csv(os.path.join(a.opdir, 'tac_markers.csv'))
    uid_names = {}; uid_code = {}; uid_bg = {}
    up = os.path.join(a.opdir, 'uids.csv')
    if os.path.exists(up):
        for r in read_csv(up):
            try: uid_names[int(r[1])] = r[0]; uid_code[int(r[1])] = int(r[4]) if len(r) > 4 else -1; uid_bg[int(r[1])] = int(r[3]) if len(r) > 3 else 0
            except ValueError: pass
    g = Graph(terr)
    feats, places = G.load_osm(a.osm)
    feats = [(k, t, [G.to_block(x, y) for x, y in p], c) for (k, t, p, c) in feats]
    places = [(G.to_block(px, py), t, key) for (px, py), t, key in places]

    # --- key points and markers: OSM settlements + hilltops from the DEM
    markers = []; add_e = []; add_r = []; mk_xy = []   # mk_xy: block metres of every marker (key-point label guard below)
    def marker(px, py, level, key, eng, rus, w=None):
        col = CELL_X0 + int(px // G.CELL); row = CELL_Y0 + int((H_BLOCK - py) // G.CELL)
        markers.append([f'v:{px % G.CELL:.1f};0;{(H_BLOCK - py) % G.CELL:.1f}', f'v:{w or 40 + 14 * len(eng)};0;110', f'a:{col};{row};{level};1', 's:' + esc(key)])
        add_e.append((key, [eng])); add_r.append((key, [rus])); mk_xy.append((px, py))
        return len(markers) - 1
    kp = {}   # node -> key-point value (3 Nov: the highest one wins - OR-ing two values gave nonsense such as 8 | 4 = 12)
    # 14 Nov (user: "there is too many objective points"): every named OSM place node in the window became a key point, and
    # Polish OSM names each kolonia, osada and part of a village: 13-55 key points per Okuniew / Radzymin operation (26-51
    # per 100 km2, 9-42 of them OSM places); 24 Graviteam operations have 3-30, median 8.5 per 100 km2.  Options, read from
    # the layout, else from the block config (the Prokh layouts and the Prokh build have neither: unchanged there):
    #   kp_osm false   OSM settlements keep their name marker and terrain bit, but are no key point (only fillers, below)
    #   kp_density d   at most max(kp_min, round(d * km2 of camp_area)) key points: the layout's objectives always, then the
    #                  other key points by value, then (kp_fill, default true) OSM villages / towns nearest the turn-1 front
    #                  at value 1; a place in a border square (the reserve zone) is no key point unless it is an objective
    #   kp_min_dist m  no two key points closer than m metres (objectives exempt)
    def kp_opt(k, d): return (layout or {}).get(k, (G.BLOCK or {}).get(k, d))
    KP_OSM = bool(kp_opt('kp_osm', True)); KP_DEN = float(kp_opt('kp_density', 0) or 0)
    kp_fill = []   # block metres of the OSM villages / towns that are no key point (filler candidates)
    def border(x, y): return x == 0 or y == 0 or x == COLS_SQ - 1 or y == ROWS_SQ - 1
    def keypoint(px, py, low, value, is_kp=True):
        x, y, mx, my = to_sq(px, py)
        for j in g.by_sq.get((x, y), []): g.nodes[j]['flags'] |= low
        if not is_kp or (KP_DEN > 0 and border(x, y)): return
        j = g.nearest(mx, my)
        if j is not None: kp[j] = max(kp.get(j, 0), value)
    # OSM settlement names are modern (Politotdelskiy, Komsomolskiy, Storozhevoye-Pervoye ...): one within 500 m of a 1943
    # layout place is dropped (the layout place carries the 1943 name), the rest renamed by prokh_gen.RENAME_1943
    # (27 Oct check of the release: both the modern and the 1943 names stood on the op map)
    lay_pl = [pl['xy'] for pl in (layout or {}).get('places', [])]
    for (px, py), t, key in places:
        if not (0 <= px < G.COLS * G.CELL and 0 <= py < H_BLOCK): continue
        if any(math.hypot(px - q[0], py - q[1]) < 500 for q in lay_pl): continue
        nm43 = G.RENAME_1943.get(t['name'], t['name'])
        if nm43 is None: continue
        if nm43 != t['name']: key = 'pe_mm_' + ''.join(ch for ch in textpack.translit(nm43).lower() if ch.isalnum())[:24]   # a new text key, so no stale modern name survives in the pack
        t = dict(t, name=nm43)
        # 14 Nov (user: "the village names are suppost to be in polish instead of russian"): a Polish block's OSM place carries
        # its Polish ASCII text in name_en / name_ru (prokh_gen.load_osm); translit() of the Cyrillic form gave "Mikhaluv"
        kind = t.get('place', ''); name = t.get('name_en') or textpack.translit(t['name'])
        if kind == 'town': low, value, level = F_VILLAGE, 8, 3
        elif kind == 'village': low, value, level = F_VILLAGE, 4, 3
        else: low, value, level = F_HAMLET, 2, 1
        keypoint(px, py, low, value, KP_OSM); marker(px, py, level, 'op_tm_' + key[6:], name, t.get('name_ru') or (name if PL_RUS_LATIN else t['name']))
        if not KP_OSM and kind in ('town', 'village') and kp_opt('kp_fill', True): kp_fill.append((px, py))
    n_osm = len(markers)   # markers 0 .. n_osm - 1 name OSM places (the label guard below may drop them, never the layout's)
    pl_mk = []   # (block metres, name, value, marker index) of the layout places (key-point label guard below)
    if layout:   # 1943 spot heights, places, strongpoints and minefields from the layout file (names as on the RKKA sheet)
        for n, hh in enumerate(layout.get('heights', [])):
            px, py = hh['xy']; keypoint(px, py, F_HEIGHT, hh.get('value', 2))
            marker(px, py, 2, 'op_tm_h' + hh['name'].replace('.', '_'), 'h. ' + hh['name'], 'выс. ' + hh['name'], w=130)
        for n, pl in enumerate(layout.get('places', [])):
            px, py = pl['xy']; keypoint(px, py, F_VILLAGE if pl.get('value', 2) >= 4 else F_HAMLET, pl.get('value', 2))
            pl_mk.append((pl['xy'], pl['name'], pl.get('value', 2),
                          marker(px, py, 3 if pl.get('value', 2) >= 4 else 1, 'op_tm_p%d' % n, pl['name'], pl['name'] if PL_RUS_LATIN else pl.get('rus', pl['name']))))
        for n, sp in enumerate(layout.get('strongpoints', [])):
            px, py = sp['xy']; marker(px, py, 1, 'op_tm_sp%d' % n, sp['name'], sp['name'] if PL_RUS_LATIN else sp.get('rus', sp['name']), w=110)
        for n, mf in enumerate(layout.get('minefields', [])):
            px = sum(q[0] for q in mf['pts']) / len(mf['pts']); py = sum(q[1] for q in mf['pts']) / len(mf['pts'])
            marker(px, py, 0, 'op_tm_mf%d' % n, 'mines', mf.get('rus', 'мины'), w=70)
    else:
        H = block_dem(a.cells, os.path.join(a.cells, '..', 'block_h64.npy'))
        for n, (h, px, py) in enumerate(hilltops(H)):
            keypoint(px, py, F_HEIGHT, 4 if n < 6 else 2)
            marker(px, py, 2, 'op_tm_h%d_%d' % (int(h), int(round(h * 10)) % 10), 'h. %.1f' % h, 'выс. %.1f' % h, w=130)
    # 3 Nov (user: "give each operation its own objective"): the layout's 'objectives' are the operation's key points at their
    # own values (vanilla scale, up to 9); every other key point (OSM settlements, spot heights, layout places) is capped
    # at 'kp_cap' so the objectives decide the outcome. Without 'objectives' the old values stand.
    objs = (layout or {}).get('objectives', [])
    if objs:
        cap = int(layout.get('kp_cap', 2))
        for j in list(kp): kp[j] = min(kp[j], cap)
        for o in objs:
            _, _, mx_, my_ = to_sq(*o['xy'])   # 'xy' is already in block metres (shift_layout)
            j = g.nearest(mx_, my_)
            if j is not None: kp[j] = max(kp.get(j, 0) if kp.get(j, 0) > cap else 0, int(o['value']))
        print('  objectives:', ', '.join(f"{o['name']} {o['value']}" for o in objs), f'(other key points capped at {cap})')
    if KP_DEN > 0:
        km2 = G.COLS * G.ROWS * (G.CELL / 1000.0) ** 2
        n_max = max(int(kp_opt('kp_min', 4)), int(round(KP_DEN * km2))); dmin = float(kp_opt('kp_min_dist', 1500.0))
        must = set()
        for o in objs:
            _, _, mx_, my_ = to_sq(*o['xy']); j = g.nearest(mx_, my_)
            if j is not None: must.add(j)
        def front_m(j): return terr.dist(g.nodes[j]['mx'] / SQ, g.nodes[j]['my'] / SQ)
        order = sorted(kp, key=lambda j: (j not in must, -kp[j], front_m(j)))
        fill = []
        for px, py in kp_fill:
            x_, y_, mx_, my_ = to_sq(px, py); j = g.nearest(mx_, my_)
            if j is not None and not border(x_, y_) and j not in kp and j not in fill: fill.append(j)
        keep = {}
        for j in order + sorted(fill, key=front_m):
            n = g.nodes[j]
            if j not in must and (len(keep) >= n_max or any(math.hypot(n['mx'] - g.nodes[k]['mx'], n['my'] - g.nodes[k]['my']) < dmin for k in keep)): continue
            keep[j] = kp.get(j, 1)
        print(f'  key points: {len(keep)} kept of {len(kp)} + {len(fill)} OSM fillers (at most {n_max} for {km2:.0f} km2, {dmin:.0f} m apart)')
        if not keep: print("  WARNING no key point at all: the layout has no 'objectives' / 'places' inside the battlefield and OSM places are no key points (kp_osm false)")
        kp = keep
        # Label guard (14 Nov): the game names a key point after the nearest tac_marker, so an objective or a layout place could
        # show a neighbour's name (08_01 / 08_09: the Krubki objective read 'Gorki', the OSM hamlet 946 m away; Radzymin:
        # Wolka Kozlowska read 'Konary'). Whether the game measures from the node or from the centre of its square (where it
        # draws the key-point sphere) is not known, so the key point's own marker - the layout place of that name, else the
        # layout place nearest it within 1 km, else a new marker - must be the nearest to both: when another marker is nearer
        # to either, the own marker moves halfway between the two, and an OSM-place marker still nearer is dropped.
        def set_marker(i, px, py):
            col = CELL_X0 + int(px // G.CELL); row = CELL_Y0 + int((H_BLOCK - py) // G.CELL)
            markers[i][0] = f'v:{px % G.CELL:.1f};0;{(H_BLOCK - py) % G.CELL:.1f}'
            markers[i][2] = f"a:{col};{row};{markers[i][2].split(';')[2]};1"; mk_xy[i] = (px, py)
        def node_of(xy):
            _, _, mx_, my_ = to_sq(*xy); return g.nearest(mx_, my_)
        own = {}   # key-point node -> index of the marker that must name it
        for (xy, nm, v, i) in sorted(pl_mk, key=lambda q: -q[2]):
            x_, y_, _, _ = to_sq(*xy)
            if border(x_, y_): continue   # a place in the reserve zone made no key point: it has no node to name
            j = node_of(xy)
            if j in kp: own.setdefault(j, i)
        for n_o, o in enumerate(objs):
            j = node_of(o['xy'])
            if j not in kp: continue
            same = [q for q in pl_mk if q[1].strip().lower() == o['name'].strip().lower()]
            near = sorted((math.hypot(q[0][0] - o['xy'][0], q[0][1] - o['xy'][1]), q[3]) for q in (same or pl_mk))
            if near and (same or near[0][0] < 1000): own[j] = near[0][1]
            else: own[j] = marker(o['xy'][0], o['xy'][1], 3, 'op_tm_o%d' % n_o, o['name'], o['name'] if PL_RUS_LATIN else o.get('rus', o['name']))
        alive = [True] * len(mk_xy)
        def refs(j):   # block metres of the key point's node and of the centre of its square
            n = g.nodes[j]; return ((n['mx'], H_BLOCK - n['my']), ((n['x'] + 0.5) * SQ, H_BLOCK - (n['y'] + 0.5) * SQ))
        def rivals(j, i):
            return [k for k in range(len(mk_xy)) if k != i and alive[k]
                    and any(math.hypot(mk_xy[k][0] - rx, mk_xy[k][1] - ry) <= math.hypot(mk_xy[i][0] - rx, mk_xy[i][1] - ry) for rx, ry in refs(j))]
        moved = []; dropped = []
        for j, i in own.items():
            r_ = rivals(j, i)
            if r_:
                (ax_, ay_), (bx_, by_) = refs(j); set_marker(i, (ax_ + bx_) / 2, (ay_ + by_) / 2)
                moved.append(f"{add_e[i][1][0]} (was {', '.join(add_e[k][1][0] for k in r_)})")
            for k in rivals(j, i):
                if k < n_osm: alive[k] = False; dropped.append(add_e[k][1][0])
        if moved: print('  key-point labels moved into their squares:', '; '.join(moved))
        if dropped: print('  OSM place markers dropped next to key points:', ', '.join(dropped))
        bad = [f"{add_e[i][1][0]} -> {', '.join(add_e[k][1][0] for k in rivals(j, i))}" for j, i in own.items() if rivals(j, i)]
        if bad: print('  WARNING key points still named after a neighbour:', '; '.join(bad))
        if not all(alive):
            markers[:] = [m for k, m in enumerate(markers) if alive[k]]; add_e[:] = [e for k, e in enumerate(add_e) if alive[k]]
            add_r[:] = [e for k, e in enumerate(add_r) if alive[k]]; mk_xy[:] = [p for k, p in enumerate(mk_xy) if alive[k]]
    for j, v in kp.items(): g.nodes[j]['flags'] = (g.nodes[j]['flags'] & 0x7ff) | (min(int(v), 15) << 11)
    # woods: squares whose centre lies in an OSM wood get the woods bit (op-map terrain hint only)
    for kind, t, p, closed in feats:
        if kind == 'area' and G.area_cover(t) == G.WOOD and len(p) > 3:
            xs = [q[0] for q in p]; ys = [q[1] for q in p]
            if (max(xs) - min(xs)) * (max(ys) - min(ys)) < 300 * 300: continue
            for y in range(ROWS_SQ):
                for x in range(COLS_SQ):
                    cx, cy = x * SQ + 512, H_BLOCK - (y * SQ + 512)
                    if min(xs) <= cx <= max(xs) and min(ys) <= cy <= max(ys) and _inside(p, cx, cy):
                        for j in g.by_sq[(x, y)]: g.nodes[j]['flags'] |= F_WOODS
    # sector boundary symbols: keep the four Stepanovka ones (tac_limits names them), scaled onto the new area
    for r in old_markers:
        if not r[3].startswith('bnd_'): continue
        p = [float(v) for v in r[0].split(';')]; aa = ints(r[2])
        ox = (aa[0] - 3) * G.CELL + p[0]; oy = (aa[1] - 1) * G.CELL + p[2]
        nx = ox * (G.COLS / 7.0); ny = oy * (G.ROWS / 5.0)
        markers.append([f'v:{nx % G.CELL:.1f};0;{ny % G.CELL:.1f}', 'v:' + r[1], f'a:{CELL_X0 + int(nx // G.CELL)};{CELL_Y0 + int(ny // G.CELL)};{aa[2]};1', 's:' + esc(r[3])])

    # --- deployment
    old_side = {i: ints(r[1])[0] for i, r in enumerate(old_nodes)}
    prows = []; placed = 0; unassigned = []; gone = []   # gone: air squadrons the layout takes out of this operation (14 Nov)
    TT = {}   # 20 Nov: the operation's historic timetable (tools/op_timetable.py), filled where the frames are written
    if layout:
        # historical roles: formation prefix -> list of positions (block metres), HQ first then battle groups in file order
        byform = {}
        for u in layout['units']:
            for f in u['form']: byform[f] = u
        counter = {}
        prefixes = sorted(byform, key=len, reverse=True)
        # --- 25 Oct (user): every HQ-type element (HQ, supply, construction) stands on the map edge in reserve, as in the
        # vanilla operations (Stepanovka: 60 of 84 HQs on border nodes at turn 1), never in the field.  A side uses only
        # the border nodes on its own ground (Territory): with the 10 July line the Germans have the west edge south of
        # the Psel and the south edge west of the Teterevino - Ivanovsky Vyselok road, the Soviets everything else.
        # Order of placement: turn-1 HQs first (they must get edge nodes), then turn-1 battle groups (interior nodes on
        # their own ground, the edge as a last resort), then the reinforcements in turn order, whole formation or nothing
        # (an orphan battle group without its HQ, or a formation cut in half, is worse than one left off the map); what
        # finds no node is listed in op_unassigned.txt.
        def is_hqtype(uid, name): return uid_code.get(uid) == 0 or bool(re.search(r'_(hq|spam|cons)\d*$', name)) or uid_code.get(uid) == 7
        def edge_of(n): return 'N' if n['y'] == 0 else 'S' if n['y'] == ROWS_SQ - 1 else 'W' if n['x'] == 0 else 'E'
        def free_edge(side):   # free border nodes on the side's own ground
            sd = GDR if side == 'GER' else USSR
            return [j for j, n in enumerate(g.nodes) if n['edge'] and n['uid'] == -1 and n['side'] == sd]
        def outer(n):
            """the border-square node on the far side (the map edge itself): HQs go there, arriving battle groups to the inner node"""
            return (n['x'] == 0 and n['dx'] < 0) or (n['x'] == COLS_SQ - 1 and n['dx'] > 0) or (n['y'] == 0 and n['dy'] < 0) or (n['y'] == ROWS_SQ - 1 and n['dy'] > 0)
        def rear_node(side, mx, my, prefer=None, exclude=(), want_outer=True, maxd=None, near=None, row_pen=1e7):
            """free border node on the side's own ground nearest to (mx, my); a free node on the preferred edge first; HQ-type
            units (want_outer) take the outer node of the border square, battle groups the inner one (user, 25 Oct: the
            battle groups up front, the HQ elements as far back as possible)"""
            cands = [(((n['mx'] - mx) ** 2 + (n['my'] - my) ** 2) + (0 if (prefer is None or edge_of(n) == prefer) else 4e8) + (0 if outer(n) == want_outer else row_pen), j)
                     for j in free_edge(side) for n in (g.nodes[j],) if edge_of(n) not in exclude
                     and (maxd is None or min(math.hypot(n['mx'] - x, n['my'] - y) for x, y in near) <= maxd)]   # hq_near: next to the formation's own nodes
            return min(cands)[1] if cands else None
        def own_bgs(f, u, div=False):
            """placed turn-1 battle groups of formation f; else of its layout unit; else of its sub-formations (a division command post:
            its own and all its sub-formations' battle groups)"""
            pts = list(BG_AT.get(f, [])) + ([p for ff, ps in BG_AT.items() if ff and ff.startswith(f + '_') for p in ps] if div else [])
            if not pts: pts = [p for ff in u['form'] for p in BG_AT.get(ff, [])]
            if not pts: pts = [p for ff, ps in BG_AT.items() if ff and ff.startswith(f + '_') for p in ps]
            return pts
        side_xy = {s_: np.array([[n['mx'], n['my']] for n in g.nodes if n['side'] == s_], np.float64).reshape(-1, 2) for s_ in (GDR, USSR)}
        def front_m(sd, mx, my):
            """metres from a point on side sd's ground to the enemy: to the front polyline or to the nearest node the other side
            holds, whichever is nearer - a detached patch (ger_poly2) has no front line of its own, so by the polyline alone
            the Wiking staffs of 08_01 stood '5.8 km behind the front' in a strip 1 km from Soviet nodes"""
            e = side_xy[USSR if sd == GDR else GDR]; d = terr.dist(mx / SQ, my / SQ) * SQ
            return min(d, float(np.hypot(e[:, 0] - mx, e[:, 1] - my).min())) if len(e) else d
        def near_own(sd, own, is_div, edge_only=False, hq_pt=None):
            """hq_near: a free own-side node, or one holding this side's turn-1 HQ elements with stack room, within hq_near (division
            command posts 2 x hq_near) of the nearest own battle group, at least FRONT_FLOOR from the enemy and about
            HQ_BEHIND (division HQ_BEHIND_DIV) farther from him than the battle groups' centre; the layout's own 'hq' point
            (hq_pt, metres from the north-west corner) pulls it that way -> node or None"""
            cx = sum(p[0] for p in own) / len(own); cy = sum(p[1] for p in own) / len(own)
            d0 = front_m(sd, cx, cy)
            R = HQ_NEAR * (2 if is_div else 1); want = HQ_BEHIND_DIV if is_div else HQ_BEHIND
            best = None
            for jj, n in enumerate(g.nodes):
                if n['side'] != sd or (edge_only and not n['edge']): continue
                free = n['uid'] == -1
                if not free and not (HQ_STACK > 1 and n.get('hq') and not n.get('late') and 1 + len(n['more']) < HQ_STACK): continue
                near = min(math.hypot(n['mx'] - x, n['my'] - y) for x, y in own)
                if near > R: continue
                fr = front_m(sd, n['mx'], n['my'])
                if fr < FRONT_FLOOR: continue
                cost = abs(fr - d0 - want) + 0.5 * near + (0.0 if free else 250.0) + (400.0 if (n['edge'] and not edge_only) else 0.0)
                if hq_pt is not None: cost += 0.5 * math.hypot(n['mx'] - hq_pt[0], n['my'] - hq_pt[1])
                if best is None or cost < best[0]: best = (cost, jj)
            return best[1] if best else None
        def bg_node(sd, mx, my):
            """battle group: free movement node on own ground; a border node (reserve) when the nearest movement node is far away
            -> (node, distance) or (None, inf)"""
            j = g.nearest(mx, my, interior=True, free=True, side=sd)
            je = g.nearest(mx, my, interior=False, free=True, side=sd)
            dj = math.hypot(g.nodes[j]['mx'] - mx, g.nodes[j]['my'] - my) if j is not None else float('inf')
            de = math.hypot(g.nodes[je]['mx'] - mx, g.nodes[je]['my'] - my) if je is not None and g.nodes[je]['edge'] else float('inf')
            if je is not None and (j is None or (dj > 2500 and de < dj)): return je, de
            return j, dj
        placement = {}   # uid -> (position string, tag); None = platoon removed
        absent = set(layout.get('air_absent', []))   # 14 Nov (user: "all airpower comes all at once"): squadrons not in this operation
        BG_F = {}        # turn-1 battle group uid -> its formation prefix (hq_near)
        jobs = []        # (order, uid, name, u, formation prefix)
        for r in plat:
            uid, x, y, node = ints(r[0])
            name = uid_names.get(uid, '')
            onmap = name and (uid_code.get(uid) == 0 or uid_bg.get(uid, 0) != 0)
            f = next((pf for pf in prefixes if _is(name, pf)), None)
            u = byform.get(f) if (onmap and f) else None
            if u is not None and u.get('absent'): u = None   # 13 Nov: a formation (or one battle group, by its longer prefix) the sources put elsewhere - left off the map
            if u is None:
                # 20 Nov 2026 (user: "units which don't take part in operation are inside the operation oob"): the pool is the whole
                # campaign's (~3000 platoons) and every operation carried all of it, the formations of the other operations as
                # 'off map'. A ground platoon whose formation the layout does not name (or marks absent) is removed from this
                # operation, as the absent squadrons are. Layout 'keep_offmap': true keeps the old behaviour.
                fu_ = byform.get(f) if f else None
                if (name and not re.search(r'_air_\d+$', name) and not layout.get('keep_offmap')
                        and (fu_ is None or fu_.get('absent'))):
                    gone.append(name); placement[uid] = None; continue
                if onmap and name: unassigned.append(name)
                if name in absent: gone.append(name); placement[uid] = None; continue   # squadron not in this operation: platoon removed (official packs simply lack it)
                turn = layout.get('air', {}).get(name) if layout else None   # air squadrons: turn of availability from the layout
                # 14 Nov: the engine puts an arrived squadron into the first battle fought from its turn on, once; all arrived unused
                # squadrons go into the same battle. A layout with 'air_absent' must name every squadron; turns lie inside the operation.
                assert turn is None or (isinstance(turn, int) and 1 <= turn <= int(layout.get('turns', 24))), ('air turn outside the operation', name, turn)
                assert not ('air_absent' in layout and re.search(r'_air_\d+$', name) and turn is None), ('squadron named in neither air nor air_absent', name)
                placement[uid] = (f'{uid};-1;-1;-1', f'{turn};1' if turn else r[1]); continue   # 'T;1' as in all 372 official air rows
            turn = u.get('turn', 1)
            # reinforcements: tank / mechanised brigades and regiments before the artillery of the same turn (the edge nodes run out at turns 12-13)
            tok_ = f.split('_')[-1].lstrip('0123456789')   # ra_24gtbr -> gtbr, ra_27gabr -> gabr, we_tk_tr -> tr
            prio = 0 if tok_ in ('tbr', 'gtbr', 'mrbr', 'gmbr', 'gtr', 'tr', 'tc', 'gtc', 'mc', 'gmc', 'grd', 'rd', 'gab', 'gabd', 'mir', 'ir', 'stug', 'otp') else 1
            # HQ-type elements: before the battle groups when they go to the edge (they must get edge nodes), after them when the
            # layout puts them in the field ('hq_field' - 2 Nov, user: HQs, supply and artillery at their historical positions)
            order = ((1.5 if (HQ_FIELD or HQ_NEAR > 0) else 0) if (turn == 1 and is_hqtype(uid, name)) else 1 if turn == 1 else 2 + prio, turn, len(jobs))   # combat formations of every turn before the reinforcement artillery
            jobs.append((order, uid, name, u, f))
        jobs.sort(key=lambda j: j[0])
        # 14 Nov (user: "units ... that are part of one unit are far apart from eachother"): a layout unit that lists several
        # formations (a division's regiments) gives them one 'pos' list, and the round-robin counter ran per formation: every
        # regiment's first battle group went for pos[0], the second for pos[1], the later entries were never used, and the
        # regiments interleaved (Stanislawow: 185 RD battle groups 2.3 km off their points, nearest sibling a median 1.5 km
        # away; vanilla 0.7 km). With hq_near each formation of such a unit takes one entry, in pool order, and all its
        # battle groups the free nodes nearest it.
        FORMS_BG = {}   # id(layout unit) -> its formation prefixes with turn-1 battle groups, in pool order
        if HQ_NEAR > 0:
            for (o_, uid_, name_, u_, f_) in jobs:
                if o_[0] == 1 and not is_hqtype(uid_, name_):
                    L_ = FORMS_BG.setdefault(id(u_), [])
                    if f_ not in L_: L_.append(f_)
        # reinforcements grouped per layout unit so a formation is placed whole or not at all
        groups = {}
        for job in jobs:
            order, uid, name, u, f = job
            if order[0] >= 2: groups.setdefault((id(u), f), []).append(job)
        done_groups = set()
        UNIT_NODES = {}   # hq_near: id(layout unit) -> edge nodes its reinforcements took
        FAMILY = {}       # hq_near: edge node -> name family of the reinforcement on it (we_4pd_12mir_1b -> we_4pd_12mir)
        bg_jobs = []   # turn-1 battle groups: (uid, name, side fourcc, mx, my) - placed together, nearest-to-its-position first
        for idx, job in enumerate(jobs):
            order, uid, name, u, f = job
            side = u['side']; sd = GDR if side == 'GER' else USSR
            if order[0] >= 2:   # reinforcement formation
                if (id(u), f) in done_groups: continue
                done_groups.add((id(u), f)); grp = groups[(id(u), f)]
                prefer = u.get('edge', 'E' if side == 'USSR' else 'W')
                excl = () if prefer == 'W' or side == 'GER' else ('W',)   # the west edge north of the Psel is 52 gds RD's back line, not an arrival edge for 5 gds TA
                free = [j for j in free_edge(side) if edge_of(g.nodes[j]) not in excl]
                if os.environ.get('OP_DEBUG'): print(f'    turn {u["turn"]} {f}: {len(grp)} platoons, {len(free)} free nodes')
                if len(free) < len(grp):
                    for (_, uid2, name2, _, _) in grp: unassigned.append(name2); placement[uid2] = (f'{uid2};-1;-1;-1', '1')
                    print(f"  reinforcement {f} (turn {u['turn']}): no room on the {side} edges for {len(grp)} platoons - left off the map")
                    continue
                if HQ_NEAR > 0:
                    # hq_near: the unit's platoons fill its arrival edge outward from its anchor, regiment by regiment (name
                    # family: we_19pd_73mir_hq, _1, _2 -> we_19pd_73mir), each family's HQ first, then its battle groups beside it.
                    # The first platoon of the unit stands within 2 x hq_near of the anchor, a family's next ones within hq_near
                    # of a node the family holds (else of one the unit holds): a contiguous stretch, never a jump across the map.
                    # A family whose staff finds no node that way is left off the map whole (op_unassigned.txt: no battle group comes
                    # without its staff); a battle group that finds none stays off alone (the rest of its regiment still arrives).
                    ax = sum(q[0] for q in u['pos']) / len(u['pos']); ay = H_BLOCK - sum(q[1] for q in u['pos']) / len(u['pos'])
                    used_ = UNIT_NODES.setdefault(id(u), [])
                    fams_ = {}
                    stf_ = sorted({re.sub(r'_(hq|spam|cons)\d*$', '', t_[2]) for t_ in grp if re.search(r'_(hq|spam|cons)\d*$', t_[2])}, key=len, reverse=True)
                    def fam_of(nm_):   # the longest staff prefix of the group the platoon belongs to (we_wk_tr_hq -> we_wk_tr: also we_wk_tr1, we_wk_tr8), else its name less the last part
                        return next((p_ for p_ in stf_ if _is(nm_, p_)), nm_.rsplit('_', 1)[0])
                    for t_ in grp: fams_.setdefault(fam_of(t_[2]), []).append(t_)
                    for fm_ in sorted(fams_, key=lambda q: (not any(is_hqtype(t_[1], t_[2]) for t_ in fams_[q]), q.count('_'), q)):
                        took_ = []; fail_hq_ = False
                        for (_, uid2, name2, _, _) in sorted(fams_[fm_], key=lambda t_: (not is_hqtype(t_[1], t_[2]), t_[2])):
                            mine_ = [q for q in used_ if FAMILY.get(q) == fm_]
                            j = None
                            for ref_, maxd_ in (((mine_, HQ_NEAR), (used_, HQ_NEAR), (used_, 2 * HQ_NEAR)) if used_ else (([], 2 * HQ_NEAR),)):
                                if used_ and not ref_: continue
                                cx_ = sum(g.nodes[q]['mx'] for q in ref_) / len(ref_) if ref_ else ax
                                cy_ = sum(g.nodes[q]['my'] for q in ref_) / len(ref_) if ref_ else ay
                                j = rear_node(side, cx_, cy_, prefer=prefer, exclude=excl, want_outer=is_hqtype(uid2, name2), maxd=maxd_,
                                              near=[(g.nodes[q]['mx'], g.nodes[q]['my']) for q in ref_] or [(ax, ay)], row_pen=(0.3 * HQ_NEAR) ** 2)   # the right row of the border square is worth 750 m, not 3 km: beside its staff first
                                if j is not None: break
                            if j is None: fail_hq_ = is_hqtype(uid2, name2); break
                            used_.append(j); took_.append((j, uid2)); FAMILY[j] = fm_; n = g.nodes[j]; n['uid'] = uid2; n['hq'] = True; n['late'] = True
                        if fail_hq_:   # no node for the staff itself: its battle groups do not come without it
                            for j, _ in took_:
                                used_.remove(j); FAMILY.pop(j, None); n = g.nodes[j]; n['uid'] = -1; n.pop('hq', None); n.pop('late', None)
                            for (_, uid2, name2, _, _) in fams_[fm_]: unassigned.append(name2); placement[uid2] = (f'{uid2};-1;-1;-1', '1')
                            print(f"  reinforcement {fm_} (turn {u['turn']}): no free {side} edge node for its staff within {2 * HQ_NEAR:.0f} m of its formation - its {len(fams_[fm_])} platoons left off the map")
                            continue
                        got_ = {uid2 for _, uid2 in took_}   # the staff is in (or the family has none): the battle groups that fit beside it arrive, the rest stay off the map
                        for (_, uid2, name2, _, _) in fams_[fm_]:
                            if uid2 not in got_:
                                unassigned.append(name2); placement[uid2] = (f'{uid2};-1;-1;-1', '1')
                                print(f"  reinforcement {name2} (turn {u['turn']}): no free {side} edge node within {2 * HQ_NEAR:.0f} m of its formation - left off the map")
                        for j, uid2 in took_:
                            n = g.nodes[j]; placement[uid2] = (f"{uid2};{n['x']};{n['y']};{j}", f"{u['turn']}"); placed += 1
                    continue
                for k2, (_, uid2, name2, _, _) in enumerate(grp):
                    px, py = u['pos'][k2 % len(u['pos'])]
                    j = rear_node(side, px, H_BLOCK - py, prefer=prefer, exclude=excl, want_outer=is_hqtype(uid2, name2))
                    n = g.nodes[j]; n['uid'] = uid2; n['hq'] = True; n['late'] = True
                    placement[uid2] = (f"{uid2};{n['x']};{n['y']};{j}", f"{u['turn']}"); placed += 1
                continue
            # 2 Nov: only battle groups count in the round-robin over 'pos' (HQ-type elements go to the edge anyway; before,
            # each HQ / supply / construction platoon of a formation consumed a 'pos' entry, so the battle groups started
            # one or two entries late and the layout positions did not mean what they said)
            hqtype = is_hqtype(uid, name)
            if not hqtype and len(FORMS_BG.get(id(u), [])) > 1: k = FORMS_BG[id(u)].index(f)
            elif not hqtype: k = counter.get(f, 0); counter[f] = k + 1
            else: k = 0
            px, py = u['pos'][k % len(u['pos'])]
            if hqtype:   # HQ-type: rear edge node nearest to the formation (the layout's hq position, if any, only picks the edge)
                cx_ = sum(q[0] for q in u['pos']) / len(u['pos']); cy_ = sum(q[1] for q in u['pos']) / len(u['pos'])
                hx, hy = u.get('hq', (cx_, cy_))
                if HQ_FIELD and not u.get('hq_edge') and not re.search(r'_(hq|spam|cons)\d*$', name):
                    # artillery batteries and other support elements (HQ-type by code): round-robin over 'pos' like battle groups
                    ka = counter.get(f + '#art', 0); counter[f + '#art'] = ka + 1; hx, hy = u['pos'][ka % len(u['pos'])]
                # 25 Oct (user): the HQ elements bunch up - up to HQ_STACK of them share one border node (the occupant field of
                # mg_nodes has four slots).  A node that already holds HQs of this side within 3 km of the formation is
                # taken before a fresh one; vanilla never stacks, so layout 'hq_stack' 1 restores one unit per node.
                j = None
                higher = bool(re.match(HIGHER_HQ_RE, name))
                div_ = bool(re.match(DIV_HQ_RE, name))
                own = own_bgs(f, u, div_) if (HQ_NEAR > 0 and not higher) else []
                if own:   # hq_near: near the formation's own battle groups ('hq_edge': an edge node within reach of them first)
                    hq_pt_ = (u['hq'][0], H_BLOCK - u['hq'][1]) if u.get('hq') else None
                    if u.get('hq_edge'): j = near_own(sd, own, div_, edge_only=True, hq_pt=hq_pt_)
                    if j is None: j = near_own(sd, own, div_, hq_pt=hq_pt_)
                if j is None and (u.get('hq_interior') or (HQ_FIELD and not u.get('hq_edge'))) and not higher:   # the layout puts this HQ in the field (285 RR in the Storozhevoye wood - user, 25 Oct; every HQ-type element with 'hq_field')
                    # 2 Nov (user): "in the vicinity but not in immediate danger" - a command post / supply / battery stays at least
                    # hq_min_front (artillery: art_min_front) metres behind the front: the free own-side movement node nearest to
                    # the layout position among those far enough back
                    # 2 Nov (user: "HQ elements of some units are close to the frontline"): echelon-dependent distances -
                    # battalion / regiment / brigade command posts hq_min_front (3 km), division and corps command posts
                    # hq_min_front_div (5 km), batteries art_min_front (2.5 km); _hq2 etc. count as command posts too
                    is_cp = bool(re.search(r'_(hq|spam|cons)\d*$', name))
                    is_div = is_cp and bool(re.match(DIV_HQ_RE, name))
                    dmin = (HQ_MIN_FRONT_DIV if is_div else HQ_MIN_FRONT if is_cp else ART_MIN_FRONT) / SQ
                    cands = [(((n['mx'] - hx) ** 2 + (n['my'] - (H_BLOCK - hy)) ** 2), jj) for jj, n in enumerate(g.nodes)
                             if not n['edge'] and n['uid'] == -1 and n['side'] == sd and terr.dist(n['mx'] / SQ, n['my'] / SQ) >= dmin]
                    if cands: j = min(cands)[1]
                    else:
                        # 13 Nov (user: "the HQ elements are back and not on the frontline"): no free node that far behind the front
                        # (a narrow map window, a salient): not the node nearest the layout position - that put command posts
                        # 50-900 m from the front - but the own-side node farthest from the front, edge nodes included, among
                        # those within 8 km of the formation (else anywhere); nodes already holding HQs may be shared (hq_stack)
                        def _far(pool_):
                            best_ = None
                            for jj, n in enumerate(g.nodes):
                                if n['side'] != sd: continue
                                if n['uid'] != -1 and not (HQ_STACK > 1 and n.get('hq') and not n.get('late') and 1 + len(n['more']) < HQ_STACK): continue
                                d2_ = (n['mx'] - hx) ** 2 + (n['my'] - (H_BLOCK - hy)) ** 2
                                if pool_ and d2_ > pool_ ** 2: continue
                                key_ = (terr.dist(n['mx'] / SQ, n['my'] / SQ), -d2_)
                                if best_ is None or key_ > best_[0]: best_ = (key_, jj)
                            return best_[1] if best_ else None
                        j = _far(8000.0)
                        if j is None: j = _far(0)
                    if HQ_FIELD and HQ_STACK > 1:   # a node already holding this side's HQ elements nearer than the free node: stack there (within 1.5 km)
                        cands = [(((n['mx'] - hx) ** 2 + (n['my'] - (H_BLOCK - hy)) ** 2), jj) for jj, n in enumerate(g.nodes)
                                 if not n['edge'] and n['uid'] != -1 and n.get('hq') and not n.get('late') and n['side'] == sd and 1 + len(n['more']) < HQ_STACK and terr.dist(n['mx'] / SQ, n['my'] / SQ) >= dmin]
                        cands = [c for c in cands if c[0] < 1500.0 ** 2]
                        if cands and (j is None or min(cands)[0] < (g.nodes[j]['mx'] - hx) ** 2 + (g.nodes[j]['my'] - (H_BLOCK - hy)) ** 2): j = min(cands)[1]
                if j is None and HQ_STACK > 1:
                    cands = [(((n['mx'] - hx) ** 2 + (n['my'] - (H_BLOCK - hy)) ** 2), jj) for jj, n in enumerate(g.nodes)
                             if n['edge'] and n['uid'] != -1 and n.get('hq') and not n.get('late') and n['side'] == sd and 1 + len(n['more']) < HQ_STACK and outer(n)]
                    cands = [c for c in cands if c[0] < 3000.0 ** 2]
                    if cands: j = min(cands)[1]
                if j is None: j = rear_node(side, hx, H_BLOCK - hy)
                if j is None:
                    unassigned.append(name); placement[uid] = (f'{uid};-1;-1;-1', '1'); print('  no free rear edge node for HQ', name); continue
                n = g.nodes[j]
                if n['uid'] == -1: n['uid'] = uid; n['hq'] = True
                else: n['more'].append(uid)
                placement[uid] = (f"{uid};{n['x']};{n['y']};{j}", '1'); placed += 1; REPORT.append((name, 'hq', j, side)); continue
            mx, my = px, H_BLOCK - py
            if not terr.ger(mx / SQ, my / SQ) == (side == 'GER'):
                print(f'  WARNING {name}: layout position ({px / SQ:.2f}, {my / SQ:.2f}) lies on the enemy side of the front line')
            bg_jobs.append((uid, name, sd, mx, my)); BG_F[uid] = f
            if idx + 1 == len(jobs) or jobs[idx + 1][0][0] > 1:
                # last turn-1 battle group: place them all, the one closest to a free node of its own ground first, so a unit whose
                # position is a node gets that node whatever the pool order (the pool lists Das Reich before the LSSAH)
                # layout 'pin': {battle-group platoon name: [X, Y]} (op-map squares) puts that battle group on the node nearest
                # the point, edge nodes included, before the greedy pass (user, 26 Oct: swap III/3 and I/2, move II/3)
                for i_ in [i for i, b in enumerate(bg_jobs) if b[1] in PINS][::-1]:
                    uid_, name_, sd_, _, _ = bg_jobs.pop(i_); X_, Y_ = PINS[name_]
                    c_ = [((n['mx'] - X_ * SQ) ** 2 + (n['my'] - Y_ * SQ) ** 2, jj) for jj, n in enumerate(g.nodes) if n['uid'] == -1 and n['side'] == sd_]
                    if not c_: print('  pin: no free node for', name_); continue
                    d2, j = min(c_); n = g.nodes[j]; n['uid'] = uid_; n['hq'] = False; BG_AT.setdefault(BG_F.get(uid_), []).append((n['mx'], n['my']))
                    if d2 > 300 ** 2: print(f'  pin {name_}: nearest free own node is {d2 ** 0.5:.0f} m from ({X_}, {Y_})')
                    placement[uid_] = (f"{uid_};{n['x']};{n['y']};{j}", '1'); placed += 1; REPORT.append((name_, 'bg', j, 'GER' if sd_ == GDR else 'RUS'))   # 14 Nov: pinned battle groups in the report too
                while bg_jobs:
                    best = min(((bg_node(sd_, mx_, my_), i) for i, (_, _, sd_, mx_, my_) in enumerate(bg_jobs)), key=lambda t: t[0][1])
                    (j, d), i = best; uid_, name_, sd_, mx_, my_ = bg_jobs.pop(i)
                    if j is None:
                        unassigned.append(name_); placement[uid_] = (f'{uid_};-1;-1;-1', '1'); print('  no free node on own ground for', name_); continue
                    n = g.nodes[j]; n['uid'] = uid_; n['hq'] = False; BG_AT.setdefault(BG_F.get(uid_), []).append((n['mx'], n['my']))
                    placement[uid_] = (f"{uid_};{n['x']};{n['y']};{j}", '1'); placed += 1; REPORT.append((name_, 'bg', j, 'GER' if sd_ == GDR else 'RUS'))   # on the map from turn 1: never keep a vanilla 'turn;0;flags' reserve tag (a BG standing on a node with an arrival turn > 1 crashes the battle placer)
        for r in plat:   # output in the platoon order of the pool
            uid = ints(r[0])[0]
            p_ = placement.get(uid, (f'{uid};-1;-1;-1', r[1]))
            if p_ is not None: prows.append(p_)
        # 13 Nov (user: "the HQ elements are back and not on the frontline"): where every turn-1 unit stands, with its
        # distance to the front line (m) - placement_report.csv in the op folder, for the check of the deployment
        with open(os.path.join(a.opdir, 'placement_report.csv'), 'w', encoding='utf-8') as fr_:
            fr_.write('name,kind,side,edge,front_m,mx,my\n')
            for nm_, kd_, j_, sd2_ in REPORT:
                n_ = g.nodes[j_]; fr_.write('%s,%s,%s,%d,%d,%d,%d\n' % (nm_, kd_, sd2_, 1 if n_['edge'] else 0, round(terr.dist(n_['mx'] / SQ, n_['my'] / SQ) * SQ), n_['mx'], n_['my']))
        # ownership: the front line of the layout decides (every unit stands on its own ground, checked above)
        if unassigned:
            print('  no role for', len(unassigned), 'placed platoons (left off map):', ' '.join(sorted(set(unassigned)))[:300])
            open(os.path.join(a.opdir, 'op_unassigned.txt'), 'w').write('\n'.join(sorted(set(unassigned))) + '\n')
        used = {}
        for n in g.nodes:
            if not n['edge']: continue
            e = edge_of(n) + ('/GER' if n['side'] == GDR else '/USSR')
            used.setdefault(e, [0, 0]); used[e][1] += 1; used[e][0] += int(n['uid'] != -1)
        print('  border nodes used / available:', ' '.join(f'{e} {u}/{t}' for e, (u, t) in sorted(used.items())),
              '| stacked HQs: %d extra on %d nodes' % (sum(len(n['more']) for n in g.nodes), sum(1 for n in g.nodes if n['more'])))
        inner = {}
        for n in g.nodes:
            if n['edge']: continue
            e = 'GER' if n['side'] == GDR else 'USSR'
            inner.setdefault(e, [0, 0]); inner[e][1] += 1; inner[e][0] += int(n['uid'] != -1)
        print('  movement nodes used / available:', ' '.join(f'{e} {u}/{t}' for e, (u, t) in sorted(inner.items())))
    else:   # test deployment: old squares scaled into the new area, each unit on its own free interior node on its own side
        sx, sy = COLS_SQ / OLD_COLS, ROWS_SQ / OLD_ROWS
        for r in plat:
            uid, x, y, node = ints(r[0])
            if x < 0 or y < 0 or node < 0 or node >= len(old_nodes):
                prows.append((r[0], r[1])); continue
            side = old_side[node]
            nx, ny = (x + 0.5) * sx, (y + 0.5) * sy
            fx = front_x(front, ny)
            nx = min(nx, fx - 1.5) if side == GDR else max(nx, fx + 1.5)
            nx = min(max(nx, 1.5), COLS_SQ - 1.5); ny = min(max(ny, 1.5), ROWS_SQ - 1.5)
            j = g.nearest(nx * SQ, ny * SQ, interior=True, free=True)
            n = g.nodes[j]; n['uid'] = uid; n['side'] = side
            prows.append((f"{uid};{n['x']};{n['y']};{j}", '1')); placed += 1

    # --- delta
    lines = ['# Prokh operation body: %d-square movement graph (%d nodes, %d links), %d key points, deployment scaled from the Stepanovka body' % (COLS_SQ * ROWS_SQ, len(g.nodes), len(g.links), sum(1 for n in g.nodes if n['flags'] >> 11))]
    lines.append('shape~|mg_nodes|2|13|aaavvaaaaaaaa')
    for k, cells in enumerate(g.rows()): lines.append(f'row+|mg_nodes|@end|n{k}|' + '|'.join(cells))
    lines.append('shape~|mg_links|2|2|av')
    # 13 Nov (user: a platoon taken from the reserve shows "ON THE WAY (1)"; in the game's 30 July operation it is there at once):
    # the game's own graph types every link between a border node and a battlefield node 1 (158 of 158 in 07_30_Stepanovka) and
    # the border-border and field-field links 2; ours were all 2, so the border (reserve) zone had no entry links
    for k, (i, j, c) in enumerate(g.links): lines.append(f"row+|mg_links|@end|l{k}|a:{i};{j};{1 if bool(g.nodes[i]['edge']) != bool(g.nodes[j]['edge']) else 2}|v:{fmt(c)}")
    lines.append('shape~|plat_pos|2|2|aa')
    for k, (c0, c1) in enumerate(prows): lines.append(f'row+|plat_pos|@end|p{k}|a:{c0}|a:{c1}')
    if layout:   # sector limits of the Stepanovka formations (tac_limits + bnd_* markers) would redistribute the units: drop them
        lines.append('shape~|tac_limits|2|2|sa')
        markers = [m for m in markers if not m[3].startswith('s:bnd_')]
    lines.append('shape~|tac_markers|2|4|vvas')
    for k, cells in enumerate(markers): lines.append(f'row+|tac_markers|@end|m{k}|' + '|'.join(cells))
    if layout:   # operation clock and weather: date_beg / time_beg / turns and one frames row per turn (brief key, weather at the start and end, day index)
        for key, fmt_ in (('date_beg', 'u'), ('time_beg', 'u'), ('turns', 'u'), ('hours_per_turn', 'u')):
            if key in layout: lines.append(f'row~|i_campgen:campgen|{key}|c0={fmt_}:{layout[key]}')
        fr = layout.get('frames')
        # 20 Nov 2026 (user: historic timetables, a briefing every turn): the turn script's historic orders -> AI posture rows
        # (DEF after each scripted run), a brief key on every turn, and (below) the turn's timetable in the briefing text and a
        # sketch for every turn without a drawn one (tools/op_timetable.py)
        if fr and G.BLOCK and G.BLOCK.get('ai_orders'):
            import importlib, op_timetable as OT, briefing as BRF
            _ord = importlib.import_module(G.BLOCK['ai_orders']).ORDERS
            TT['block'] = 'Okun' if 'okun' in G.BLOCK['ai_orders'] else 'Radz'
            TT['to'] = OT.turn_orders(_ord, len(fr), int(layout.get('turn_offset', 0)), G.SQ_DX, G.SQ_DY, BRF.W_SQ, BRF.H_SQ)
            # 20 Nov (08_01 RUS crashed): posture rows only for the computer's side - the player's formations are USER, not AI
            # groups; rows naming groups without a platoon left in this operation are dropped below, after the pruning
            ger_op_ = bool(re.search(r'(^|_)GER(_|$)', os.path.basename(os.path.normpath(a.opdir)).upper()))
            prow_ = [r_ for r_ in OT.postures(TT['to'], len(fr)) if OT.NAMES.get(r_[1], ('USSR',))[0] == ('USSR' if ger_op_ else 'GER')]
            TT['prow'] = prow_
            TT['hand'] = {f.get('brief') for f in fr if f.get('brief')}
            for k, f in enumerate(fr): f['brief'] = f.get('brief') or 'brief_%02d' % (k + 1)
            print('  timetable: %d turns, %d scripted orders, %d DEF posture rows, briefings on all turns (%d hand-written)' % (len(fr), sum(len(v) for v in TT['to'].values()), len(prow_), len(TT['hand'])))
        elif fr and not G.BLOCK:   # 22 Nov (user: briefings as in Okuniew / Radzymin): Prokhorovka - briefing, history texts and sketch on every turn (no posture rows)
            import prokh_timetable as PT
            PT.setup(TT, layout, fr)
        if fr:
            lines.append('shape~|frames|2|7|sssuuuu')
            for k, f in enumerate(fr):
                lines.append(f"row+|frames|@end|f{k}|s:{esc(f.get('brief', ''))}|s:{f.get('w0', '')}|s:{f.get('w1', '')}|u:{f.get('day', 0)}|u:{k}|u:0|u:0")
    for nm in gone: lines.append('node-|act_platoons/' + nm)   # 14 Nov: squadrons not in this operation; 20 Nov: and the formations not in it
    if gone: print('  removed from this operation (not in its layout / absent): %d platoons, e.g. %s' % (len(gone), ' '.join(sorted(gone)[:12])))
    # 20 Nov: and the formations (reserves/p_*) none of whose platoons is left - no platoon's pool / pool2-4 names it and it is not
    # the parent of a formation that stays (needs the pool columns of uids.csv and forms.csv, written by oob_okun.ps1)
    fp_ = os.path.join(a.opdir, 'forms.csv')
    if gone and layout and not layout.get('keep_offmap') and os.path.exists(fp_) and os.path.exists(up):
        U_ = read_csv(up); F_ = read_csv(fp_)
        if U_ and len(U_[0]) >= 9:
            gs_ = set(gone); refd_ = set()
            for r_ in U_:
                if r_[0] not in gs_: refd_.update(x_ for x_ in r_[5:9] if x_)
            par_ = {r_[0]: r_[1] for r_ in F_}; keep_ = set()
            # 20 Nov (08_01 RUS crashed): never remove a top formation (p_ra_rgk, p_we_okh ... - the vanilla div_pool names p_ra_rgk)
            refd_.update(r_[0] for r_ in F_ if not r_[1])
            for f_ in refd_:
                while f_ and f_ not in keep_: keep_.add(f_); f_ = par_.get(f_)
            gone_f_ = [r_[0] for r_ in F_ if r_[0] not in keep_]
            for nm in gone_f_: lines.append('node-|reserves/' + nm)
            print('  formations removed from this operation: %d of %d, e.g. %s' % (len(gone_f_), len(F_), ' '.join(sorted(gone_f_)[:10])))
            TT['live_forms'] = keep_
    if TT.get('prow') is not None:   # the posture rows: the computer's side, groups that still have a formation in this operation
        import op_timetable as OT
        f_of_ = OT.ai_prefixes(); lf_ = TT.get('live_forms')
        pr_ = [r_ for r_ in TT['prow'] if lf_ is None or f_of_.get(r_[1]) is None or f_of_.get(r_[1]) in lf_]   # WKG / P4K: battle-group ids, no formation of their own
        lines += OT.delta_rows(pr_)
        print('  posture rows: %d DEF for the computer\'s side (%d dropped: no formation left in this operation)' % (len(pr_), len(TT['prow']) - len(pr_)))
    out = os.path.join(a.opdir, 'op_body.delta')
    open(out, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines) + '\n')
    # --- text packs
    tp = os.path.join(a.opdir, 'text.text.loc_eng.bin'); packs = []
    for loc, add in (('loc_eng', add_e), ('loc_rus', add_r)):
        p = tp.replace('loc_eng', loc)
        if not os.path.exists(p): continue
        if not os.path.exists(p + '.orig'): shutil.copy(p, p + '.orig')
        locname, entries = textpack.read(p + '.orig'); have = {k for k, _ in entries}
        entries = entries + [(k, v) for k, v in add if k not in have]
        if layout and 'briefing' in layout:   # operation name, chapter and turn briefings instead of the Stepanovka ones
            br = layout['briefing']; sfx = '_rus' if loc == 'loc_rus' else ''
            rep = {k: br.get(k + sfx, br.get(k)) for k in ('op_name', 'op_name1', 'op_chap', 'op_canvas', 'op_canvas1')}
            rep = {k: v for k, v in rep.items() if v is not None}
            if sfx and PL_RUS_LATIN:   # 14 Nov: the operation's place name (first line of op_name / op_name1) in Polish, as in loc_eng
                for k in ('op_name', 'op_name1'):
                    if isinstance(rep.get(k), str) and isinstance(br.get(k), str):
                        rep[k] = br[k].split('\n')[0] + ('\n' + rep[k].split('\n', 1)[1] if '\n' in rep[k] else '')
            # op_GER (Prokhorovka) / op_GER_<op> (Warsaw): the German-side turn briefings. 14 Nov: the test was endswith('GER'), so every
            # German-side Warsaw pack carried the Soviet texts
            ger = bool(re.search(r'(^|_)GER(_|$)', os.path.basename(os.path.normpath(a.opdir)).upper()))
            bk = ('briefs_ger' + sfx) if ger and ('briefs_ger' + sfx) in br else ('briefs' + sfx)
            for k, v in br.get(bk, br.get('briefs', {})).items(): rep[k] = v   # per-turn briefings (frames rows name them)
            if TT.get('to'):   # 20 Nov: a briefing on every turn - the hand-written text (if any) + the turn's historic timetable
                import op_timetable as OT
                for t_ in range(1, len(layout['frames']) + 1):
                    k_ = 'brief_%02d' % (t_ + TT.get('koff', 0)); hand_ = rep.get(k_) if k_ in TT['hand'] else None   # koff: Prokhorovka's campaign-numbered keys
                    if isinstance(hand_, (list, tuple)): hand_ = '\n'.join(hand_)
                    rep[k_] = OT.brief_text(layout, TT['block'], TT['to'], t_, ger, bool(sfx), hand_)
                    rep.update(OT.turn_texts(layout, TT['block'], TT['to'], t_, ger, bool(sfx)))   # the history panel's turnNN / _plan / _result
            entries = [(k, ([rep[k]] if isinstance(rep[k], str) else list(rep[k])) if k in rep else v) for k, v in entries]
            have = {k for k, _ in entries}
            entries += [(k, [v] if isinstance(v, str) else list(v)) for k, v in rep.items() if k not in have and (k.startswith('brief_') or re.match(r'^turn\d\d(_plan|_result)?$', k))]
            # M16: sketch labels of the layout (briefing 'labels' / 'labels_rus': key -> text), e.g. op_sk_3tc
            lab_ = dict(br.get('labels' + sfx, br.get('labels', {})))
            if sfx and PL_RUS_LATIN:   # 14 Nov: the sketch's place labels (op_sk_p<n>) in Polish, as in loc_eng; unit labels stay Russian
                lab_.update({k: v for k, v in br.get('labels', {}).items() if re.match(r'^op_sk_p\d+$', k)})
            for k, v in lab_.items():
                if k not in have: entries.append((k, [v])); have.add(k)
        textpack.write(p, locname, entries); packs.append(loc)
    # --- briefing sketches (the F2 picture): an AZSC script pack in the vanilla style, one drawing per frames brief key (tools/briefing.py)
    if layout and layout.get('frames'):
        import briefing
        sp = os.path.join(a.opdir, 'scripts.script.loc_def.bin')
        if os.path.exists(sp) and not os.path.exists(sp + '.orig30'): shutil.copy(sp, sp + '.orig30')
        if TT.get('to'):   # 20 Nov: a sketch for every turn without a drawn one (the turn's attacks / moves on the last drawn picture)
            import op_timetable as OT
            if TT.get('block') == 'Prokh':   # 22 Nov: every Prokhorovka turn drawn from the layout + timetable (the old hand-coded sketches retired)
                import prokh_timetable as PT
                briefing.EXTRA_SKETCHES = PT.sketches(layout, TT['to'], TT.get('koff', 0))
            else: briefing.EXTRA_SKETCHES = OT.sketches(OT.raw_layout(G), TT['to'], G, None)
            print('  sketches made from the timetable: %d (%d arrows)' % (len(briefing.EXTRA_SKETCHES), sum(len(v['thrusts']) for v in briefing.EXTRA_SKETCHES.values())))
        ni, nf = briefing.write_scripts(sp, [f.get('brief', '') for f in layout['frames']], int(layout.get('turns', 24)), int(layout.get('turn_offset', 0)))
        print(f'  briefing script pack: {nf} functions, {ni} instructions -> {sp}')
    print(f'nodes {len(g.nodes)} links {len(g.links)} key points {sum(1 for n in g.nodes if n["flags"] >> 11)} platoons {len(plat)} ({placed} on map) markers {len(markers)} -> {out}; text packs: {", ".join(packs) or "none found"}')

def _is(name, pf):
    """platoon `name` belongs to the layout prefix `pf`: we_lah_2mir_1b, we_lah_tr1, we_lah_tr_hq, ra_285_2 ..."""
    if not name.startswith(pf): return False
    rest = name[len(pf):]
    return rest == '' or rest.startswith('_') or rest.isdigit()

def shift_layout(obj, key=None):
    """layout coordinates (DEM-lattice metres) -> block metres: 'xy' / 'hq' pairs, 'pts' / 'pos' / 'front' point lists"""
    if isinstance(obj, dict): return {k: shift_layout(v, k) for k, v in obj.items()}
    if isinstance(obj, list):
        if key in ('xy', 'hq', 'toward') and len(obj) == 2 and all(isinstance(v, (int, float)) for v in obj): return list(G.to_block(obj[0], obj[1]))
        if key in ('pts', 'pos', 'front', 'fronts', 'ger_poly', 'ger_poly2') and obj and all(isinstance(q, list) and len(q) == 2 and all(isinstance(v, (int, float)) for v in q) for q in obj): return [list(G.to_block(q[0], q[1])) for q in obj]
        return [shift_layout(v, key) for v in obj]
    return obj

def _inside(poly, x, y):
    c = False; n = len(poly)
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1: c = not c
    return c

if __name__ == '__main__':
    main()

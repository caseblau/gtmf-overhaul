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
import sys, os, csv, math, argparse, shutil, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prokh_gen as G, textpack

SQ = 1024.0
COLS_SQ, ROWS_SQ = G.COLS * 2, G.ROWS * 2   # 14 x 10 squares (7 x 5 cells)
CELL_X0, CELL_Y0 = 3, 1                     # camp_area origin in the cells table (3;1;9;5, as the vanilla Mius block)
USSR = 1381192533; GDR = 5391687
HQ_STACK = 1   # HQ-type units per border node at turn 1 (layout 'hq_stack')
PINS = {}      # layout 'pin': battle-group platoon name -> [X, Y] op-map squares
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
    def __init__(self, front):
        self.front = [(float(x), float(y)) for x, y in front]
        poly = list(self.front)
        ex, ey = poly[-1]
        if ex >= COLS_SQ - 1e-6 and ey < ROWS_SQ - 1e-6: poly.append((COLS_SQ, ROWS_SQ))   # ends on the east edge
        poly.append((0.0, ROWS_SQ))                                                           # south-west corner
        sx, sy = poly[0]
        if sy <= 1e-6 and sx > 1e-6: poly.append((0.0, 0.0))                                  # starts on the north edge
        self.poly = poly
    def ger(self, x, y):
        """square coordinates (x from the west, y from the north) -> True where the Germans hold the ground"""
        return _inside(self.poly, x, y)
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
    terr = Territory(front)
    global HQ_STACK, PINS; HQ_STACK = int(layout.get('hq_stack', 1)) if layout else 1
    PINS = {k: tuple(v) for k, v in (layout.get('pin', {}) if layout else {}).items()}
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
    markers = []; add_e = []; add_r = []
    def marker(px, py, level, key, eng, rus, w=None):
        col = CELL_X0 + int(px // G.CELL); row = CELL_Y0 + int((H_BLOCK - py) // G.CELL)
        markers.append([f'v:{px % G.CELL:.1f};0;{(H_BLOCK - py) % G.CELL:.1f}', f'v:{w or 40 + 14 * len(eng)};0;110', f'a:{col};{row};{level};1', 's:' + esc(key)])
        add_e.append((key, [eng])); add_r.append((key, [rus]))
    def keypoint(px, py, low, value):
        x, y, mx, my = to_sq(px, py)
        for j in g.by_sq.get((x, y), []): g.nodes[j]['flags'] |= low
        j = g.nearest(mx, my)
        if j is not None: g.nodes[j]['flags'] |= (value << 11)
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
        kind = t.get('place', ''); name = textpack.translit(t['name'])
        if kind == 'town': low, value, level = F_VILLAGE, 8, 3
        elif kind == 'village': low, value, level = F_VILLAGE, 4, 3
        else: low, value, level = F_HAMLET, 2, 1
        keypoint(px, py, low, value); marker(px, py, level, 'op_tm_' + key[6:], name, t['name'])
    if layout:   # 1943 spot heights, places, strongpoints and minefields from the layout file (names as on the RKKA sheet)
        for n, hh in enumerate(layout.get('heights', [])):
            px, py = hh['xy']; keypoint(px, py, F_HEIGHT, hh.get('value', 2))
            marker(px, py, 2, 'op_tm_h' + hh['name'].replace('.', '_'), 'h. ' + hh['name'], 'выс. ' + hh['name'], w=130)
        for n, pl in enumerate(layout.get('places', [])):
            px, py = pl['xy']; keypoint(px, py, F_VILLAGE if pl.get('value', 2) >= 4 else F_HAMLET, pl.get('value', 2))
            marker(px, py, 3 if pl.get('value', 2) >= 4 else 1, 'op_tm_p%d' % n, pl['name'], pl.get('rus', pl['name']))
        for n, sp in enumerate(layout.get('strongpoints', [])):
            px, py = sp['xy']; marker(px, py, 1, 'op_tm_sp%d' % n, sp['name'], sp.get('rus', sp['name']), w=110)
        for n, mf in enumerate(layout.get('minefields', [])):
            px = sum(q[0] for q in mf['pts']) / len(mf['pts']); py = sum(q[1] for q in mf['pts']) / len(mf['pts'])
            marker(px, py, 0, 'op_tm_mf%d' % n, 'mines', mf.get('rus', 'мины'), w=70)
    else:
        H = block_dem(a.cells, os.path.join(a.cells, '..', 'block_h64.npy'))
        for n, (h, px, py) in enumerate(hilltops(H)):
            keypoint(px, py, F_HEIGHT, 4 if n < 6 else 2)
            marker(px, py, 2, 'op_tm_h%d_%d' % (int(h), int(round(h * 10)) % 10), 'h. %.1f' % h, 'выс. %.1f' % h, w=130)
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
    prows = []; placed = 0; unassigned = []
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
        def is_hqtype(uid, name): return uid_code.get(uid) == 0 or name.endswith('_hq') or name.endswith('_spam') or name.endswith('_cons') or uid_code.get(uid) == 7
        def edge_of(n): return 'N' if n['y'] == 0 else 'S' if n['y'] == ROWS_SQ - 1 else 'W' if n['x'] == 0 else 'E'
        def free_edge(side):   # free border nodes on the side's own ground
            sd = GDR if side == 'GER' else USSR
            return [j for j, n in enumerate(g.nodes) if n['edge'] and n['uid'] == -1 and n['side'] == sd]
        def outer(n):
            """the border-square node on the far side (the map edge itself): HQs go there, arriving battle groups to the inner node"""
            return (n['x'] == 0 and n['dx'] < 0) or (n['x'] == COLS_SQ - 1 and n['dx'] > 0) or (n['y'] == 0 and n['dy'] < 0) or (n['y'] == ROWS_SQ - 1 and n['dy'] > 0)
        def rear_node(side, mx, my, prefer=None, exclude=(), want_outer=True):
            """free border node on the side's own ground nearest to (mx, my); a free node on the preferred edge first; HQ-type
            units (want_outer) take the outer node of the border square, battle groups the inner one (user, 25 Oct: the
            battle groups up front, the HQ elements as far back as possible)"""
            cands = [(((n['mx'] - mx) ** 2 + (n['my'] - my) ** 2) + (0 if (prefer is None or edge_of(n) == prefer) else 4e8) + (0 if outer(n) == want_outer else 1e7), j)
                     for j in free_edge(side) for n in (g.nodes[j],) if edge_of(n) not in exclude]
            return min(cands)[1] if cands else None
        def bg_node(sd, mx, my):
            """battle group: free movement node on own ground; a border node (reserve) when the nearest movement node is far away
            -> (node, distance) or (None, inf)"""
            j = g.nearest(mx, my, interior=True, free=True, side=sd)
            je = g.nearest(mx, my, interior=False, free=True, side=sd)
            dj = math.hypot(g.nodes[j]['mx'] - mx, g.nodes[j]['my'] - my) if j is not None else float('inf')
            de = math.hypot(g.nodes[je]['mx'] - mx, g.nodes[je]['my'] - my) if je is not None and g.nodes[je]['edge'] else float('inf')
            if je is not None and (j is None or (dj > 2500 and de < dj)): return je, de
            return j, dj
        placement = {}   # uid -> (position string, tag)
        jobs = []        # (order, uid, name, u, formation prefix)
        for r in plat:
            uid, x, y, node = ints(r[0])
            name = uid_names.get(uid, '')
            onmap = name and (uid_code.get(uid) == 0 or uid_bg.get(uid, 0) != 0)
            f = next((pf for pf in prefixes if _is(name, pf)), None)
            u = byform.get(f) if (onmap and f) else None
            if u is None:
                if onmap and name: unassigned.append(name)
                turn = layout.get('air', {}).get(name) if layout else None   # air squadrons: turn of availability from the layout
                placement[uid] = (f'{uid};-1;-1;-1', str(turn) if turn else r[1]); continue
            turn = u.get('turn', 1)
            # reinforcements: tank / mechanised brigades and regiments before the artillery of the same turn (the edge nodes run out at turns 12-13)
            tok_ = f.split('_')[-1].lstrip('0123456789')   # ra_24gtbr -> gtbr, ra_27gabr -> gabr, we_tk_tr -> tr
            prio = 0 if tok_ in ('tbr', 'gtbr', 'mrbr', 'gmbr', 'gtr', 'tr', 'tc', 'gtc', 'mc', 'gmc', 'grd', 'rd', 'gab', 'gabd', 'mir', 'ir', 'stug', 'otp') else 1
            order = (0 if (turn == 1 and is_hqtype(uid, name)) else 1 if turn == 1 else 2 + prio, turn, len(jobs))   # combat formations of every turn before the reinforcement artillery
            jobs.append((order, uid, name, u, f))
        jobs.sort(key=lambda j: j[0])
        # reinforcements grouped per layout unit so a formation is placed whole or not at all
        groups = {}
        for job in jobs:
            order, uid, name, u, f = job
            if order[0] >= 2: groups.setdefault((id(u), f), []).append(job)
        done_groups = set()
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
                for k2, (_, uid2, name2, _, _) in enumerate(grp):
                    px, py = u['pos'][k2 % len(u['pos'])]
                    j = rear_node(side, px, H_BLOCK - py, prefer=prefer, exclude=excl, want_outer=is_hqtype(uid2, name2))
                    n = g.nodes[j]; n['uid'] = uid2; n['hq'] = True; n['late'] = True
                    placement[uid2] = (f"{uid2};{n['x']};{n['y']};{j}", f"{u['turn']}"); placed += 1
                continue
            k = counter.get(f, 0); counter[f] = k + 1
            px, py = u['pos'][k % len(u['pos'])]
            if is_hqtype(uid, name):   # HQ-type: rear edge node nearest to the formation (the layout's hq position, if any, only picks the edge)
                cx_ = sum(q[0] for q in u['pos']) / len(u['pos']); cy_ = sum(q[1] for q in u['pos']) / len(u['pos'])
                hx, hy = u.get('hq', (cx_, cy_))
                # 25 Oct (user): the HQ elements bunch up - up to HQ_STACK of them share one border node (the occupant field of
                # mg_nodes has four slots).  A node that already holds HQs of this side within 3 km of the formation is
                # taken before a fresh one; vanilla never stacks, so layout 'hq_stack' 1 restores one unit per node.
                j = None
                if u.get('hq_interior'):   # the layout puts this HQ in the field (285 RR in the Storozhevoye wood - user, 25 Oct)
                    j = g.nearest(hx, H_BLOCK - hy, interior=True, free=True, side=sd)
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
                placement[uid] = (f"{uid};{n['x']};{n['y']};{j}", '1'); placed += 1; continue
            mx, my = px, H_BLOCK - py
            if not terr.ger(mx / SQ, my / SQ) == (side == 'GER'):
                print(f'  WARNING {name}: layout position ({px / SQ:.2f}, {my / SQ:.2f}) lies on the enemy side of the front line')
            bg_jobs.append((uid, name, sd, mx, my))
            if idx + 1 == len(jobs) or jobs[idx + 1][0][0] >= 2:
                # last turn-1 battle group: place them all, the one closest to a free node of its own ground first, so a unit whose
                # position is a node gets that node whatever the pool order (the pool lists Das Reich before the LSSAH)
                # layout 'pin': {battle-group platoon name: [X, Y]} (op-map squares) puts that battle group on the node nearest
                # the point, edge nodes included, before the greedy pass (user, 26 Oct: swap III/3 and I/2, move II/3)
                for i_ in [i for i, b in enumerate(bg_jobs) if b[1] in PINS][::-1]:
                    uid_, name_, sd_, _, _ = bg_jobs.pop(i_); X_, Y_ = PINS[name_]
                    c_ = [((n['mx'] - X_ * SQ) ** 2 + (n['my'] - Y_ * SQ) ** 2, jj) for jj, n in enumerate(g.nodes) if n['uid'] == -1 and n['side'] == sd_]
                    if not c_: print('  pin: no free node for', name_); continue
                    d2, j = min(c_); n = g.nodes[j]; n['uid'] = uid_; n['hq'] = False
                    if d2 > 300 ** 2: print(f'  pin {name_}: nearest free own node is {d2 ** 0.5:.0f} m from ({X_}, {Y_})')
                    placement[uid_] = (f"{uid_};{n['x']};{n['y']};{j}", '1'); placed += 1
                while bg_jobs:
                    best = min(((bg_node(sd_, mx_, my_), i) for i, (_, _, sd_, mx_, my_) in enumerate(bg_jobs)), key=lambda t: t[0][1])
                    (j, d), i = best; uid_, name_, sd_, mx_, my_ = bg_jobs.pop(i)
                    if j is None:
                        unassigned.append(name_); placement[uid_] = (f'{uid_};-1;-1;-1', '1'); print('  no free node on own ground for', name_); continue
                    n = g.nodes[j]; n['uid'] = uid_; n['hq'] = False
                    placement[uid_] = (f"{uid_};{n['x']};{n['y']};{j}", '1'); placed += 1   # on the map from turn 1: never keep a vanilla 'turn;0;flags' reserve tag (a BG standing on a node with an arrival turn > 1 crashes the battle placer)
        for r in plat:   # output in the platoon order of the pool
            uid = ints(r[0])[0]
            prows.append(placement.get(uid, (f'{uid};-1;-1;-1', r[1])))
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
    for k, (i, j, c) in enumerate(g.links): lines.append(f'row+|mg_links|@end|l{k}|a:{i};{j};2|v:{fmt(c)}')
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
        if fr:
            lines.append('shape~|frames|2|7|sssuuuu')
            for k, f in enumerate(fr):
                lines.append(f"row+|frames|@end|f{k}|s:{esc(f.get('brief', ''))}|s:{f.get('w0', '')}|s:{f.get('w1', '')}|u:{f.get('day', 0)}|u:{k}|u:0|u:0")
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
            ger = os.path.basename(os.path.normpath(a.opdir)).upper().endswith('GER')   # op_GER: the German-side turn briefings
            bk = ('briefs_ger' + sfx) if ger and ('briefs_ger' + sfx) in br else ('briefs' + sfx)
            for k, v in br.get(bk, br.get('briefs', {})).items(): rep[k] = v   # per-turn briefings (frames rows name them)
            entries = [(k, ([rep[k]] if isinstance(rep[k], str) else list(rep[k])) if k in rep else v) for k, v in entries]
            have = {k for k, _ in entries}
            entries += [(k, [v] if isinstance(v, str) else list(v)) for k, v in rep.items() if k not in have and k.startswith('brief_')]
        textpack.write(p, locname, entries); packs.append(loc)
    # --- briefing sketches (the F2 picture): an AZSC script pack in the vanilla style, one drawing per frames brief key (tools/briefing.py)
    if layout and layout.get('frames'):
        import briefing
        sp = os.path.join(a.opdir, 'scripts.script.loc_def.bin')
        if os.path.exists(sp) and not os.path.exists(sp + '.orig30'): shutil.copy(sp, sp + '.orig30')
        ni, nf = briefing.write_scripts(sp, [f.get('brief', '') for f in layout['frames']])
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
        if key in ('xy', 'hq') and len(obj) == 2 and all(isinstance(v, (int, float)) for v in obj): return list(G.to_block(obj[0], obj[1]))
        if key in ('pts', 'pos', 'front') and obj and all(isinstance(q, list) and len(q) == 2 and all(isinstance(v, (int, float)) for v in q) for q in obj): return [list(G.to_block(q[0], q[1])) for q in obj]
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

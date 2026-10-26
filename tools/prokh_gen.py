"""Prokhorovka terrain generator: builds every entry of a Mius-Front terrain cell from the DEM-derived heightmaps and
an OpenStreetMap extract (land cover baseline), in the layout decoded in docs/m12_terrain/findings.md.

  python prokh_gen.py --osm docs/m12_terrain/osm/prokh.osm.json --cells build/prokhorovka/cells
                      --template build/prokhorovka/template --out build/prokhorovka/cellsrc [--only MgL5,MgL6] [--no-ai]

Writes build/prokhorovka/cellsrc/<cell>/ with <entry>.cell.loc_def.bin files and a !flatlist for gt3.ps1 pack.
Coordinates: x east, y north in metres from the block's south-west corner; cell (i, j) with j = 0 the NORTH row covers
x in [i*2048, (i+1)*2048), y in [(rows-1-j)*2048, ...). Inside a cell every raster row 0 is the south edge.
Runs with numpy + Pillow only (no GIS libraries).
"""
import sys, os, json, math, argparse, time, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pha6 import decode as pha6_decode
import atf1, cellfmt as C, pen, textpack
import texsynth as TX, texref as TR, morph as MO
REF = None      # texref.Ref: the Petropolye / Mius reference cells, set by main() from --ref

# ------------------------------------------------------------------ block geometry (docs/m12_terrain/prokh_layout.md)
# The DEM lattice ("old frame", 11 x 12 cells, metres from its west / south edge) stays the coordinate system of the
# OSM data, the layout files, the period mask and the heightmap files in build\prokhorovka\cells.  The polygon built
# from it is the 7 x 5 core block (2026-10-24, user): old columns 2..8 (x 4096..18432) and old rows 4..8
# (y 6144..16384) = Vasilyevka / the Psel bend - Prokhorovka station / Grushki, Belenikhino - Hill 226.6, with the
# vanilla Mius geometry (cells table 11 x 7, cells at cell_x 3..9 / cell_y 1..5, camp_area 3;1;9;5).
LATS, LATN, LONW, LONE = 50.904605, 51.1254, 36.4903, 36.8120   # DEM lattice (2026-10-23: two more rows south)
OLD_COLS, OLD_ROWS, CELL = 11, 12, 2048.0
OLD_LETTERS = [chr(ord('D') + i) for i in range(OLD_COLS)]
COLS, ROWS = 7, 5
BLOCK_I0, BLOCK_J0 = 2, 4                                   # old lattice indices of the block's north-west cell
BLOCK_X0 = BLOCK_I0 * CELL                                  # old-frame metres of the block's west edge
BLOCK_Y0 = (OLD_ROWS - BLOCK_J0 - ROWS) * CELL              # old-frame metres of the block's south edge
LAT_C = 51.0334; M_LAT = 111320.0; M_LON = 111320.0 * math.cos(math.radians(LAT_C))
LETTERS = [chr(ord('D') + i) for i in range(COLS)]
MAXH = 320.0

def cell_name(i, j):
    border = (i == 0 or j == 0 or i == COLS - 1 or j == ROWS - 1)
    return ('Mx' if border else 'Mg') + LETTERS[i] + str(j + 1)

def hei_name(i, j):
    """name of the DEM-lattice heightmap file (build\\prokhorovka\\cells) that holds block cell (i, j)"""
    oi, oj = i + BLOCK_I0, j + BLOCK_J0
    border = (oi == 0 or oj == 0 or oi == OLD_COLS - 1 or oj == OLD_ROWS - 1)
    return ('Mx' if border else 'Mg') + OLD_LETTERS[oi] + str(oj + 1)

def cell_origin(i, j):
    """old-frame metres of the cell's south-west corner"""
    return BLOCK_X0 + i * CELL, BLOCK_Y0 + (ROWS - 1 - j) * CELL

def to_block(x, y):
    """old-frame metres -> block metres (from the block's west / south edge)"""
    return x - BLOCK_X0, y - BLOCK_Y0

def project(lon, lat):
    return (lon - LONW) * M_LON, (lat - LATS) * M_LAT

# ------------------------------------------------------------------ land cover codes
GRASS, FIELD, WOOD, ORCHARD, SCRUB, VILLAGE, WATER, MARSH, RAIL, ROAD, TRACK, BUILDING = range(12)
# soils (mat_map low nibble): GRAS0 MARS1 BLAC2 CLAY3 STON4 SAND5 FIEL6 FIGR7 CONC8 ASPH9 PAVE10 RBAC11 FORG12 LEAV13 TREN14 BUMP15
SOIL_OF = {GRASS: 0, FIELD: 6, WOOD: 12, ORCHARD: 0, SCRUB: 0, VILLAGE: 0, WATER: 1, MARSH: 1, RAIL: 4, ROAD: 11, TRACK: 3, BUILDING: 3}   # Petropolye: main roads road_back (11) 4-6 m wide, field roads clay (3) 3-6 m
CLASS_OF = {GRASS: 0, FIELD: 5, WOOD: 3, ORCHARD: 4, SCRUB: 4, VILLAGE: 7, WATER: 0, MARSH: 0, RAIL: 0, ROAD: 0, TRACK: 0, BUILDING: 7}
# flora table rows (season_ua_summer): pine_sm0 pine_mid1 pine_big2 tree_sm3 tree_mid4 tree_big5 rogoz6 bush7 bush_big8 fir9
# garden10 birch11 water_tree12 corn13 poplar14 cultbush15 verba_bush16 sunfl17 corn_dry18 dry_sm19 dry_mid20 dry_big21 cut22
# Petropolye densities: ripe fields carry NO plants (the crop is the ground texture + grass billboards), sunflower / maize
# plots 1 per 10-22 m2, hedges (soil 13) bushes 1 per 11-15 m2, woods (12) big bushes + trees 1 per 18 m2, open steppe
# 1 bush per 450-1100 m2 (cultbush, garden tree, bush)
FLORA = dict(WOOD=[(3, 2), (4, 5), (5, 3), (7, 2), (8, 3), (11, 1)], SCRUB=[(7, 5), (8, 2), (16, 1)], ORCHARD=[(10, 1)],
             FIELD_GRAIN=[], FIELD_CORN=[], FIELD_SUNFL=[(17, 1)], VILLAGE=[(4, 2), (10, 4), (7, 1), (14, 1), (15, 2)], WATER=[(6, 3), (12, 1), (16, 1)],
             BALKA=[(7, 5), (8, 2), (3, 2), (16, 1)], MARSH=[(6, 2), (16, 2), (12, 1), (3, 1)], STEPPE=[(15, 4), (7, 3), (8, 1), (10, 1)])
DENSITY = dict(WOOD=1 / 30.0, SCRUB=1 / 25.0, ORCHARD=1 / 40.0, FIELD=1 / 22.0, VILLAGE=1 / 600.0, WATER=1 / 25.0, BALKA=1 / 140.0, MARSH=1 / 60.0, STEPPE=1 / 900.0)

# ------------------------------------------------------------------ OSM
def load_osm(path):
    data = json.load(open(path, encoding='utf-8'))
    nodes = {}; ways = {}; rels = []
    for e in data['elements']:
        if e['type'] == 'node': nodes[e['id']] = (e['lon'], e['lat'], e.get('tags', {}))
        elif e['type'] == 'way': ways[e['id']] = (e['nodes'], e.get('tags', {}))
        elif e['type'] == 'relation': rels.append(e)
    feats = []  # (kind, tags, [(x,y),...], closed)
    def pts(nids):
        out = []
        for n in nids:
            if n in nodes: out.append(project(nodes[n][0], nodes[n][1]))
        return out
    used_in_rel = set()
    for r in rels:
        t = r.get('tags', {})
        if t.get('type') != 'multipolygon': continue
        outers = [m['ref'] for m in r.get('members', []) if m['type'] == 'way' and m.get('role', 'outer') == 'outer']
        rings = stitch([ways[w][0] for w in outers if w in ways])
        for ring in rings:
            p = pts(ring)
            if len(p) >= 3: feats.append(('area', t, p, True))
        used_in_rel.update(outers)
    for wid, (nids, t) in ways.items():
        p = pts(nids)
        if len(p) < 2: continue
        closed = nids[0] == nids[-1] and len(p) >= 4
        if 'building' in t: feats.append(('building', t, p, closed))
        elif 'highway' in t or 'railway' in t or 'waterway' in t or 'power' in t or t.get('natural') == 'tree_row' or t.get('man_made') == 'embankment' or t.get('barrier'):
            feats.append(('line', t, p, closed))
        elif closed and wid not in used_in_rel: feats.append(('area', t, p, True))
    places = []; seen = set()
    for (x, y, t) in nodes.values():
        if 'place' in t and 'name' in t:
            key = 'pe_mm_' + ''.join(ch for ch in textpack.translit(t['name']).lower() if ch.isalnum())[:24]
            k2 = key; n = 2
            while k2 in seen: k2 = key[:22] + str(n); n += 1
            seen.add(k2); places.append((project(x, y), t, k2))
    return feats, places

HEIGHTS43 = []       # (x, y, label) spot heights of the 1943 map from the layout, set by places_1943()
RENAME_1943 = {'Комсомольский': 'свх. Комсомолец', 'Политотдельский': 'свх. Октябрьский', 'Сторожевое-Первое': 'Сторожевое',
               'Сторожевое-Второе': 'Сталинское отд.', 'Грушки-Первые': 'Грушки', 'Грушки-Вторые': None, 'Михайловка': 'Михайловка'}
def places_1943(osm_places, layout_path):
    """the op-map names of 1943: the layout's `places` (name / rus / xy) and `heights` replace the OpenStreetMap names; an
    OSM place survives only if no layout place lies within 500 m, under its 1943 name (RENAME_1943; None = dropped)"""
    global HEIGHTS43
    lay = json.load(open(layout_path, encoding='utf-8')) if layout_path and os.path.exists(layout_path) else {}
    out = []; seen = set()
    def key_of(name_lat):
        key = 'pe_mm_' + ''.join(ch for ch in name_lat.lower() if ch.isalnum())[:24]; k2 = key; n = 2
        while k2 in seen: k2 = key[:22] + str(n); n += 1
        seen.add(k2); return k2
    for p in lay.get('places', []):
        x, y = p['xy']; rus = p.get('rus') or p['name']; lat = p['name']
        out.append(((float(x), float(y)), {'name': rus, 'name_en': lat, 'place': 'village'}, key_of(lat)))
    for (xy, t, key) in osm_places:
        if any(math.hypot(xy[0] - q[0][0], xy[1] - q[0][1]) < 500 for q in out): continue
        nm = t.get('name', '')
        if nm in RENAME_1943:
            if RENAME_1943[nm] is None: continue
            nm = RENAME_1943[nm]
        out.append((xy, dict(t, name=nm), key_of(textpack.translit(nm))))
    HEIGHTS43 = [(float(hgt['xy'][0]), float(hgt['xy'][1]), str(hgt['name'])) for hgt in lay.get('heights', [])]
    return out

def stitch(waylists):
    """Join way node lists into closed rings (for multipolygon outers)."""
    segs = [list(w) for w in waylists if w]; rings = []
    while segs:
        ring = segs.pop(0)
        changed = True
        while changed and ring[0] != ring[-1]:
            changed = False
            for k, s in enumerate(segs):
                if s[0] == ring[-1]: ring += s[1:]; segs.pop(k); changed = True; break
                if s[-1] == ring[-1]: ring += s[::-1][1:]; segs.pop(k); changed = True; break
                if s[-1] == ring[0]: ring = s[:-1] + ring; segs.pop(k); changed = True; break
                if s[0] == ring[0]: ring = s[::-1][:-1] + ring; segs.pop(k); changed = True; break
        rings.append(ring)
    return rings

def area_cover(t):
    lu = t.get('landuse', ''); nat = t.get('natural', ''); le = t.get('leisure', '')
    if nat in ('wood',) or lu == 'forest': return WOOD
    if lu == 'orchard' or lu == 'vineyard': return ORCHARD
    if nat in ('scrub', 'heath'): return SCRUB
    if nat == 'water' or lu in ('reservoir', 'basin') or t.get('water'): return WATER
    if nat == 'wetland': return MARSH
    if lu in ('farmland', 'farm'): return FIELD
    if lu in ('residential', 'farmyard', 'industrial', 'commercial', 'retail', 'garages', 'allotments', 'cemetery', 'religious') or t.get('place') in ('village', 'hamlet', 'town'): return VILLAGE
    if lu in ('meadow', 'grass', 'pasture', 'greenfield', 'brownfield') or nat in ('grassland',) or le in ('park',): return GRASS
    return None

def line_style(t):
    """(cover, width m, opmap colour or None, dashed) for linear features."""
    if 'railway' in t and t['railway'] in ('rail', 'narrow_gauge', 'disused', 'abandoned'):
        if t.get('service') in ('spur', 'crossover') or t.get('usage') in ('industrial',): return None   # modern yards and sidings
        return (RAIL, 6.0, 0xff1d0a04, False)
    hw = t.get('highway')
    if hw in ('motorway', 'trunk', 'primary', 'secondary', 'tertiary'): return (ROAD, 6.0, C.COL_ROAD, False)   # 1943: unpaved 'grade' roads; Petropolye main roads 4-6 m of road_back
    if hw in ('unclassified', 'residential', 'service', 'living_street', 'road'): return (ROAD, 5.0, C.COL_ROAD_DARK, False)
    if hw in ('track',): return (TRACK, 3.5, C.COL_TRACK, True)
    if hw in ('path', 'footway', 'bridleway', 'cycleway'): return (TRACK, 1.5, None, True)
    ww = t.get('waterway')
    if ww in ('river',): return (WATER, 16.0, 0xff8a5a2a, False)
    if ww in ('stream', 'canal', 'drain', 'ditch'): return (MARSH, 5.0, 0xff8a5a2a, False)
    if t.get('natural') == 'tree_row': return (WOOD, 8.0, None, False)
    return None

class MplPath:
    """point-in-polygon (even-odd rule), numpy only - the PC that runs the generator has no matplotlib"""
    def __init__(self, pts):
        self.p = np.asarray(pts, np.float64)
    def contains_points(self, q):
        q = np.asarray(q, np.float64).reshape(-1, 2); x, y = q[:, 0][:, None], q[:, 1][:, None]
        a = self.p; b = np.roll(a, -1, 0)
        ax, ay, bx, by = a[:, 0][None], a[:, 1][None], b[:, 0][None], b[:, 1][None]
        cross = ((ay > y) != (by > y)) & (x < (bx - ax) * (y - ay) / np.where(by - ay == 0, 1e-12, by - ay) + ax)
        return (cross.sum(1) % 2) == 1

def drop_modern(feats, layout_path):
    """layout 'exclude_1943' (user, 26 Oct: 'weird street layout which should be absent' - the post-war memorial park at
    the station): OSM features lying mostly inside these polygons are dropped - paths, service roads, buildings, parks,
    orchards, grass, small woods, tree rows. Railways, main roads (primary / secondary / tertiary), farmland and the
    railway snow-protection belts stay."""
    lay = json.load(open(layout_path, encoding='utf-8')) if layout_path and os.path.exists(layout_path) else {}
    polys = [MplPath(e['pts']) for e in lay.get('exclude_1943', [])]
    if not polys: return feats
    out = []; n = 0
    for f in feats:
        kind, t, p, closed = f
        keep = True
        if 'railway' in t or t.get('highway') in ('primary', 'secondary', 'tertiary', 'trunk') or t.get('landuse') in ('farmland',) or 'power' in t:
            keep = True
        elif kind == 'area' and area_cover(t) == WOOD and strip_width(p) < 45.0 and near_rail(p, feats, 120.0) and not any(pl.contains_points(p).mean() > 0.8 for pl in polys):
            keep = True
        elif any(pl.contains_points(p).mean() > 0.5 for pl in polys):
            keep = False
        if keep: out.append(f)
        else: n += 1
    print('exclude_1943: %d modern features dropped' % n, flush=True)
    return out

# ------------------------------------------------------------------ natural river courses
# 26 Oct (user: 'the curvature is rigid and unnatural'): the OSM Psel here has a vertex every 110-160 m, so the river was
# a chain of straight 14 m bands with sharp corners. Every river / stream line is smoothed (Chaikin) and given meanders -
# three incommensurate waves of lateral offset with a slowly varying amplitude (tight bends and calm reaches), phases
# hashed from the way's first point, tapered to zero at both ends so consecutive OSM ways still join - and the river
# band gets a width that varies along its length. Done once on the features, so the water levels and every cell agree.
MEANDER = {'river': (20.0, (420.0, 210.0, 120.0), 16.0, 5.0), 'stream': (4.0, (130.0, 70.0, 37.0), 5.0, 1.2),
           'canal': (0.0, (1.0, 1.0, 1.0), 5.0, 0.0), 'drain': (1.5, (90.0, 50.0, 27.0), 4.0, 0.8), 'ditch': (1.5, (90.0, 50.0, 27.0), 4.0, 0.8)}
RIPARIAN = [None]   # set per cell: (belt mask, distance to the water m, noise) for the bank flora

def _meander(pts, amp, lams, salt=0):
    import works as W
    sm = W._chaikin(pts, 4)
    sm = [p for k, p in enumerate(sm) if k == 0 or math.hypot(p[0] - sm[k - 1][0], p[1] - sm[k - 1][1]) > 1e-6]
    if len(sm) < 2 or amp <= 0: return [tuple(p) for p in sm]
    seg = [(x2 - x1, y2 - y1) for (x1, y1), (x2, y2) in zip(sm, sm[1:])]
    L = sum(math.hypot(dx, dy) for dx, dy in seg)
    ph = [(W._hash(round(pts[0][0]), round(pts[0][1]), 31 + k + salt) % 1000) / 1000.0 * 2 * math.pi for k in range(5)]
    taper = min(90.0, L / 3.0)
    out = []; s = 0.0; i = 0; t = 0.0; step = 3.0
    while True:
        while i < len(seg) and t > math.hypot(*seg[i]): t -= math.hypot(*seg[i]); i += 1
        if i >= len(seg): break
        dx, dy = seg[i]; ln = math.hypot(dx, dy); ux, uy = dx / ln, dy / ln
        x, y = sm[i][0] + ux * t, sm[i][1] + uy * t
        w = min(1.0, s / taper, (L - s) / taper) if taper > 0 else 1.0
        a = amp * (0.65 + 0.35 * math.sin(2 * math.pi * s / 1100.0 + ph[3]))
        off = w * a * (math.sin(2 * math.pi * s / lams[0] + ph[0]) + 0.6 * math.sin(2 * math.pi * s / lams[1] + ph[1]) + 0.2 * math.sin(2 * math.pi * s / lams[2] + ph[2]))
        out.append((x - uy * off, y + ux * off)); s += step; t += step
    out.append(tuple(sm[-1]))
    return out

def meander_water(feats):
    out = []; n = 0
    for (kind, t, p, closed) in feats:
        ww = t.get('waterway') if kind == 'line' else None
        if ww in MEANDER:
            amp, lams, w0, dw = MEANDER[ww]
            q = _meander(p, amp, lams)
            if ww == 'river':   # half-width along the line: w0/2 +- dw/2, a ~400 m wave plus a ~120 m one
                import works as W
                ph = (W._hash(round(p[0][0]), round(p[0][1]), 41) % 1000) / 1000.0 * 2 * math.pi
                hw = [0.5 * (w0 + dw * (0.7 * math.sin(k * 3.0 * 2 * math.pi / 410.0 + ph) + 0.3 * math.sin(k * 3.0 * 2 * math.pi / 117.0 + 2 * ph))) for k in range(len(q))]
                t = dict(t); t['_hw'] = hw
            out.append((kind, t, q, closed)); n += 1
        elif kind == 'area' and area_cover(t) == WATER and len(p) >= 4:
            import works as W
            q = W._chaikin(list(p) + [p[0]] if p[0] != p[-1] else list(p), 3)   # rounded pond / oxbow outlines
            out.append((kind, t, q, closed)); n += 1
        else: out.append((kind, t, p, closed))
    print('water courses smoothed / meandered:', n, flush=True)
    return out

def _band(pp, hw):
    """polygon of a line with a half-width per vertex (cell px)"""
    L, R = [], []
    for k, (x, y) in enumerate(pp):
        (x1, y1) = pp[max(0, k - 1)]; (x2, y2) = pp[min(len(pp) - 1, k + 1)]
        ux, uy = x2 - x1, y2 - y1; ln = math.hypot(ux, uy) or 1.0; nx, ny = -uy / ln, ux / ln
        w = hw[k] if k < len(hw) else hw[-1]
        L.append((x + nx * w, y + ny * w)); R.append((x - nx * w, y - ny * w))
    return L + R[::-1]

# ------------------------------------------------------------------ rasterising one cell
def clip_poly(p, x0, y0, margin=50):
    xs = [q[0] for q in p]; ys = [q[1] for q in p]
    return not (max(xs) < x0 - margin or min(xs) > x0 + CELL + margin or max(ys) < y0 - margin or min(ys) > y0 + CELL + margin)

def to_px(p, x0, y0):
    return [(q[0] - x0, q[1] - y0) for q in p]   # 1 px = 1 m; row = y (south = 0): PIL row 0 is the top, so we flip at the end

FARM_MASK = [None]   # set by rasterise: farmyard / industrial landuse of the current cell
VIL_PAD = [None]     # set by rasterise: village / building cover of the cell with a PAD margin (so the village extent is the same on both sides of a border)
PAD = 96
FARMS = []           # layout 'farms': sovkhoz yards of 1943 (polygons, DEM-lattice metres) drawn as village cover + farm mask
FIELDS43 = []        # layout 'fields_1943': field blocks traced from the Luftwaffe photographs (polygon, crop pattern, strip width / axis)
WOODS43 = []         # layout 'woods_1943': woods drawn over everything (polygons, DEM-lattice metres)
VILLAGES43 = []      # layout 'villages_1943': villages of 1943 that modern OSM no longer has (polygons, DEM-lattice metres; e.g. Teterevino from the RKKA 1:100 000 sheet)
ROADS43 = []         # layout 'roads_1943': lanes / tracks of 1943 missing from OSM ({'pts', 'kind': 'track' | 'road'}), streets for the 1943 villages
PONDS = True         # layout 'ponds_1943': False drops the OSM standing water (the gully reservoirs are post-war; the 1941 sheet has none) - rivers and streams stay
STRIPS = False        # brigade strips 25-45 m (Wheatley Fig. 35) - switched OFF 25 Oct: in the game they read as odd stripes; the vanilla fields are large uniform blocks
STRIP_PATTERNS = [[1, 1, 4, 1, 3, 4, 1, 1, 4, 1], [1, 4, 1, 1, 4, 3, 1, 4], [1, 1, 1, 4, 1, 1, 3, 1, 4, 4], [4, 1, 1, 4, 1, 3, 1, 1], [1, 4, 1, 4, 1, 1, 3, 4, 1, 1, 4]]   # strip crops: 1 ripe, 2 green crop, 3 sunflower, 4 ploughed / fallow
STRIP_PATTERNS_FINE = [[1, 4, 1, 2, 1, 4, 2, 1, 4], [1, 2, 4, 1, 4, 2, 1, 3, 4], [4, 1, 2, 1, 4, 1, 2, 4, 1, 1], [1, 4, 2, 1, 4, 1, 3, 1, 4, 2]]
VIL_NEAR = [None, None]   # set by rasterise (8 m): within ~1.5 km of a village (strip-field share) / within ~1.1 km (kolkhoz blocks on open land)
FIELD_TYPES = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 3, 4, 4]   # 25 Oct (user): far fewer sunflower fields - 1 in 18; green crop (2: beet / maize without plants) instead   # 1 ripe grain (soil 6 with green dashes / blobs, copied from Petropolye), 3 sunflower (7 + plants), 4 ploughed / fallow (15)   # Luftwaffe photos of 16 July 1943 (Wheatley 2019): a patchwork of large fields, ripe grain dominant, a few bright harvested / dark fallow ones   # per field polygon: 1 ripe winter rye / wheat (July), 2 green crop (maize), 3 sunflower, 4 fallow / ploughed
FIELD_KEEP_PCT = 90   # share of the OSM farmland polygons that stay crops; the rest is grassland
WORKS = []      # field works from docs/m11_prokhorovka/layout_12jul.json (tools/works.py), set by main()
PERIOD = None   # (H,W) uint8 mask on the 4 m block grid, row 0 = north; set by main() when docs/m12_terrain/period/builtup_1941.png exists

def period_mask_cell(i, j, margin=0):
    """1 m boolean mask of the 1941 built-up area inside cell (i, j) (+ margin px on every side), row 0 = south; None without a period mask."""
    if PERIOD is None: return None
    x0, y0 = cell_origin(i, j); H, W = PERIOD.shape
    xs = np.clip(((x0 + np.arange(-margin, 2048 + margin) + 0.5) / 4).astype(int), 0, W - 1)
    ys = np.clip(((OLD_ROWS * CELL - (y0 + np.arange(-margin, 2048 + margin) + 0.5)) / 4).astype(int), 0, H - 1)   # the mask covers the DEM lattice
    return PERIOD[ys][:, xs] > 0

def landchar_from_template(tpl_path, cls):
    """landchar = 64 x 64 records of 48 bytes per 32 m square (baked lighting / sky openness: bytes 1..27 in 0..191, then
    colour quads). Copying the Mius cell's file paints its woods and ponds as dark blotches on our terrain, so the layer is
    rebuilt from a neutral open-ground record (90th percentile of the template) and darkened only under our own woods."""
    u8 = np.frombuffer(open(tpl_path, 'rb').read(), np.uint8).reshape(-1, 48)
    rec = np.percentile(u8[:, :28], 90, axis=0); rec = np.concatenate([rec, np.median(u8[:, 28:], axis=0)]).astype(np.float32)
    out = np.tile(rec, (64 * 64, 1))
    shade = np.ones(64 * 64, np.float32); c = cls.ravel()
    shade[c == 3] = 0.84; shade[c == 4] = 0.9; shade[c == 7] = 0.95   # woods, orchards / scrub, villages
    out[:, 1:28] *= shade[:, None]
    return np.clip(np.round(out), 0, 255).astype(np.uint8).tobytes()

def strip_width(p):
    """mean width of a polygon = 2 * area / perimeter (small for the long thin shelterbelt polygons)"""
    a = abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(p, p[1:] + p[:1]))) / 2
    per = sum(math.hypot(x2 - x1, y2 - y1) for (x1, y1), (x2, y2) in zip(p, p[1:] + p[:1]))
    return 2 * a / per if per > 0 else 0.0

SINGLE_TRACK = False   # layout 'single_track': True keeps one of each pair of parallel OSM rail ways. The 1941 RKKA
                       # 1:100 000 sheet draws the Belgorod - Kursk line with the double-track symbol, so both tracks stay.
def dedupe_rails(rails, sep=25.0):
    """OSM maps the line as two parallel ways a few metres apart (passenger_lines 2); with SINGLE_TRACK keep one of each pair"""
    if not SINGLE_TRACK: return list(rails)
    keep = []
    for pp in sorted(rails, key=lambda q: -len(q)):
        pts = pp[::max(1, len(pp) // 12)]
        dup = False
        for kp in keep:
            kq = kp[::max(1, len(kp) // 60)]
            near = sum(1 for (x, y) in pts if any(abs(x - a) < sep and abs(y - b) < sep for (a, b) in kq))
            if near >= 0.6 * len(pts): dup = True; break
        if not dup: keep.append(pp)
    return keep

def near_rail(p, feats, dist=80.0):
    """is the polyline p within `dist` m of an OSM main-line railway?"""
    for (kind, t, q, closed) in feats:
        if kind != 'line' or 'railway' not in t or line_style(t) is None or line_style(t)[0] != RAIL: continue
        for (x, y) in p[::max(1, len(p) // 8)]:
            for (qx, qy) in q[::max(1, len(q) // 40)]:
                if abs(qx - x) < dist and abs(qy - y) < dist: return True
    return False

def rasterise(feats, i, j, rng, steep=None):
    x0, y0 = cell_origin(i, j)
    cov = Image.new('L', (2048, 2048), GRASS); d = ImageDraw.Draw(cov)
    fid = Image.new('I', (2048, 2048), 0); df = ImageDraw.Draw(fid)
    farm = Image.new('L', (2048, 2048), 0); dfarm = ImageDraw.Draw(farm)   # state farm / collective farm yards: barns, no homestead fences
    order = {GRASS: 0, FIELD: 1, VILLAGE: 2, ORCHARD: 3, SCRUB: 4, WOOD: 5, MARSH: 6, WATER: 7}
    areas = []; rail_belts = []
    for k, (kind, t, p, closed) in enumerate(feats):
        if kind != 'area' or not clip_poly(p, x0, y0): continue
        c = area_cover(t)
        if c is None: continue
        if c == WATER and not PONDS and t.get('water') not in ('river', 'stream', 'canal', 'oxbow'): continue   # post-war gully reservoirs
        if c == WOOD and strip_width(p) < 45.0 and not near_rail(p, feats, 120.0): continue
        if c == WOOD and strip_width(p) < 70.0 and near_rail(p, feats, 120.0): rail_belts.append(p)   # drawn again over the 1943 villages / farms below   # modern field shelterbelts (post-1948) go; the railway snow-protection belts stay (user, 25 Oct: the tree line along the railway was missing - they were planted from the 1930s)
        areas.append((order[c], c, p, k))
    areas.sort(key=lambda a: a[0])
    field_polys = []
    for (_, c, p, k) in areas:
        if c == FIELD and (k * 2654435761) % 100 >= FIELD_KEEP_PCT: c = GRASS   # 1943: open steppe / fallow between the crop fields (period sheets show pasture, not the modern wall-to-wall arable)
        d.polygon(to_px(p, x0, y0), fill=c)
        if c == FIELD: field_polys.append((k, to_px(p, x0, y0)))
        if c == VILLAGE and feats[k][1].get('landuse') in ('farmyard', 'industrial'): dfarm.polygon(to_px(p, x0, y0), fill=255)
    farm43 = Image.new('L', (2048, 2048), 0); d43 = ImageDraw.Draw(farm43)
    for fm_ in FARMS:   # 1943 state-farm yards from the layout (svkh. Oktyabrsky, Komsomolets, Stalinskoye otd.): barns round a clay yard, no homesteads
        if clip_poly(fm_, x0, y0):
            d.polygon(to_px(fm_, x0, y0), fill=VILLAGE); dfarm.polygon(to_px(fm_, x0, y0), fill=255); d43.polygon(to_px(fm_, x0, y0), fill=255)
    vil43 = Image.new('L', (2048, 2048), 0); dv43 = ImageDraw.Draw(vil43)
    for vl_ in VILLAGES43:   # 1943 villages missing from OSM (Teterevino): village cover, homesteads along the streets inside (tools/settle.py)
        if clip_poly(vl_, x0, y0):
            d.polygon(to_px(vl_, x0, y0), fill=VILLAGE); dv43.polygon(to_px(vl_, x0, y0), fill=255)
    # the railway snow-protection belts run unbroken past the 1943 villages (user, 26 Oct: the wood along the line
    # vanished at Ivanovsky Vyselok - the village polygon of the layout was painted over it)
    for p in rail_belts:
        if clip_poly(p, x0, y0): d.polygon(to_px(p, x0, y0), fill=WOOD)
    for w_ in WOODS43:
        p = w_['pts']
        if not clip_poly(p, x0, y0): continue
        if w_.get('rail_belt'):   # only the belt along the railway inside the polygon
            pm = Image.new('L', (2048, 2048), 0); ImageDraw.Draw(pm).polygon(to_px(p, x0, y0), fill=255)
            bm = Image.new('L', (2048, 2048), 0); dbm = ImageDraw.Draw(bm)
            for (kind_, t_, q_, c_) in feats:
                if kind_ == 'line' and line_style(t_) is not None and line_style(t_)[0] == RAIL and clip_poly(q_, x0, y0, margin=200):
                    dbm.line(to_px(q_, x0, y0), fill=255, width=int(2 * w_['rail_belt']), joint='curve')
            m_ = Image.fromarray(((np.asarray(pm) > 0) & (np.asarray(bm) > 0)).astype(np.uint8) * 255)
            d.bitmap((0, 0), m_, fill=WOOD)
        else: d.polygon(to_px(p, x0, y0), fill=WOOD)

    lines = []; buildings = []; water_lines = []
    rail_ways = dedupe_rails([to_px(p, x0, y0) for (kind, t, p, closed) in feats if kind == 'line' and line_style(t) is not None and line_style(t)[0] == RAIL and clip_poly(p, x0, y0)])
    for rd_ in ROADS43:   # 1943 lanes missing from OSM: drawn like OSM tracks / minor roads (the village walk needs a street)
        if clip_poly(rd_['pts'], x0, y0):
            c, w, col, dash = (ROAD, 5.0, C.COL_ROAD_DARK, False) if rd_.get('kind') == 'road' else (TRACK, 3.5, C.COL_TRACK, True)
            pp = to_px(rd_['pts'], x0, y0); d.line(pp, fill=c, width=max(1, int(round(w))), joint='curve'); lines.append((pp, col, dash, c))
    for (kind, t, p, closed) in feats:
        if not clip_poly(p, x0, y0): continue
        if kind == 'line':
            st = line_style(t)
            if st is None: continue
            if t.get('natural') == 'tree_row': continue   # 1943: no shelterbelts yet (Stalin plan 1948+); the Luftwaffe photos show bare field edges and a bare railway embankment
            c, w, col, dash = st
            pp = to_px(p, x0, y0)
            if c == RAIL and pp not in rail_ways: continue   # the second way of the OSM double track
            if c in (WATER, MARSH) and t.get('waterway'):
                water_lines.append((pp, c, w, t.get('_hw'))); lines.append((pp, col, dash, c)); continue
            d.line(pp, fill=c, width=max(1, int(round(w))), joint='curve')
            lines.append((pp, col, dash, c))
        elif kind == 'building' and closed:
            pp = to_px(p, x0, y0); d.polygon(pp, fill=BUILDING); buildings.append(pp)
    # rivers and streams last, over the roads and tracks that cross them (26 Oct: a track drawn over the Psel left a
    # raised grass strip across the water - the bed is not carved under non-water pixels)
    for (pp, c, w, hw) in water_lines:
        if hw: d.polygon(_band(pp, hw), fill=c)
        else: d.line(pp, fill=c, width=max(1, int(round(w))), joint='curve')
    for (_, c, p, k) in areas:
        if c == WATER: d.polygon(to_px(p, x0, y0), fill=WATER)
    cov = np.asarray(cov).copy(); fid = np.asarray(fid).copy(); FARM_MASK[0] = np.asarray(farm) > 0
    if WOODS43:   # inside a woods_1943 polygon the 21 m track bed is open grass (the rail itself is drawn on it)
        bed = np.zeros((2048, 2048), bool)
        wi = Image.new('L', (2048, 2048), 0); dwi = ImageDraw.Draw(wi)
        for w_ in WOODS43:
            if clip_poly(w_['pts'], x0, y0): dwi.polygon(to_px(w_['pts'], x0, y0), fill=255)
        if (np.asarray(wi) > 0).any():
            bi = Image.new('L', (2048, 2048), 0); dbi = ImageDraw.Draw(bi)
            for pp in rail_ways: dbi.line(pp, fill=255, width=21, joint='curve')
            bed = (np.asarray(wi) > 0) & (np.asarray(bi) > 0) & (cov == WOOD)
            cov[bed] = GRASS
    # villages (incl. those up to 1.6 km outside the cell) dilated by 1.5 km, at 8 m on a padded canvas: strip-field share near the villages
    M8 = 200; vn = Image.new('L', (256 + 2 * M8, 256 + 2 * M8), 0); dvn = ImageDraw.Draw(vn)
    for (kind, t, p, closed) in feats:
        if kind == 'area' and area_cover(t) == VILLAGE and clip_poly(p, x0, y0, margin=M8 * 8):
            dvn.polygon([((x - x0) / 8 + M8, (y - y0) / 8 + M8) for x, y in p], fill=255)
    for vl_ in VILLAGES43:
        if clip_poly(vl_, x0, y0, margin=M8 * 8): dvn.polygon([((x - x0) / 8 + M8, (y - y0) / 8 + M8) for x, y in vl_], fill=255)
    VIL_NEAR[0] = MO.dilate(np.asarray(vn) > 0, 2 * 188 + 1)[M8:M8 + 256, M8:M8 + 256] if (np.asarray(vn) > 0).any() else None
    VIL_NEAR[1] = MO.dilate(np.asarray(vn) > 0, 2 * 138 + 1)[M8:M8 + 256, M8:M8 + 256] if (np.asarray(vn) > 0).any() else None   # 1.1 km
    # village extent with a margin for tools/settle.py (homestead plots may lie in the neighbouring cell)
    vp = Image.new('L', (2048 + 2 * PAD, 2048 + 2 * PAD), 0); dvp = ImageDraw.Draw(vp)
    for (_, c, p, k) in areas:
        if c == VILLAGE: dvp.polygon([(x + PAD, y + PAD) for x, y in to_px(p, x0, y0)], fill=255)
    for fm_ in FARMS:
        if clip_poly(fm_, x0, y0): dvp.polygon([(x + PAD, y + PAD) for x, y in to_px(fm_, x0, y0)], fill=255)
    for vl_ in VILLAGES43:
        if clip_poly(vl_, x0, y0, margin=PAD): dvp.polygon([(x + PAD, y + PAD) for x, y in to_px(vl_, x0, y0)], fill=255)
    for (kind, t, p, closed) in feats:
        if kind == 'building' and closed and clip_poly(p, x0, y0, margin=PAD + 50): dvp.polygon([(x + PAD, y + PAD) for x, y in to_px(p, x0, y0)], fill=255)
    VIL_PAD[0] = np.asarray(vp) > 0
    # 1943 kolkhoz blocks on the open land round the villages (Wheatley Fig. 35, 14 July: a dense patchwork of brigade strips between the
    # Psel villages and the plateau, where OSM has pasture today): irregular blocks (jittered 400 m lattice in block coordinates, so the
    # cells agree) within 1.1 km of a village, 55 % strip blocks, 25 % single fields, 20 % left as meadow; never on steep ground
    if VIL_NEAR[1] is not None:
        # rectangular blocks (the vanilla fields are large straight-edged blocks): a lattice of 420 x 640 m rectangles
        # turned 14 deg, in block coordinates (seam-free), edges wobbled a little by global noise
        bx0_, by0_ = to_block(x0, y0)
        yy8, xx8 = np.mgrid[0:256, 0:256]; gx = xx8 * 8.0 + bx0_ + 4.0; gy = yy8 * 8.0 + by0_ + 4.0
        th = math.radians(14.0)
        jit = TX.gnoise((256, 256), (bx0_ / 8.0, by0_ / 8.0), 40.0, 90) * 30.0     # +-30 m, 320 m scale
        u = gx * math.cos(th) + gy * math.sin(th) + jit; v = -gx * math.sin(th) + gy * math.cos(th) - jit
        # 25 Oct (user, in-game view from height: a camouflage patchwork): blocks 520 x 800 m, the crop shared by 2 x 2 block
        # groups (one crop per ~1 x 1.6 km rotation field) and 70 % of the blocks under crop, so the fields read as fields
        iu = np.floor(u / 520.0).astype(np.int64); iv = np.floor(v / 800.0).astype(np.int64)
        hv = TR._hash_arr(iv, iu, 77) % 100
        typ_idx = TR._hash_arr(iv // 2, iu // 2, 81) % len(FIELD_TYPES)
        openm = (cov == GRASS)
        if steep is not None: openm &= ~steep
        wet8 = ((cov == WATER) | (cov == MARSH)).reshape(256, 8, 256, 8).max((1, 3)) > 0
        flood8 = MO.dilate(wet8, 2 * 31 + 1)   # the river meadows: 250 m either side of the water stay hay meadow (Wheatley Fig. 35)
        open8 = (openm.reshape(256, 8, 256, 8).mean((1, 3)) > 0.6) & ~flood8
        field8 = (hv < 70) & open8 & VIL_NEAR[1]
        # drop slivers (< 1.5 ha per block inside the cell)
        key = iv * 100003 + iu
        for k in np.unique(key[field8]):
            mk = field8 & (key == k)
            if mk.sum() < 24: field8[mk] = False
        m = np.repeat(np.repeat(field8, 8, 0), 8, 1) & openm
        cov[m] = FIELD
        t8 = np.asarray(FIELD_TYPES, np.uint8)[typ_idx]
        fid[m] = np.repeat(np.repeat(t8, 8, 0), 8, 1)[m]
    # kolkhoz strip fields: every OSM field polygon is cut into strips 250-450 m wide along its long axis, each strip
    # with its own crop (the 16 July 1943 Luftwaffe photographs show exactly this patchwork)
    for (k, pp) in field_polys:
        xs = [q[0] for q in pp]; ys = [q[1] for q in pp]
        bx0, by0, bx1, by1 = max(0, int(min(xs))), max(0, int(min(ys))), min(2048, int(max(xs)) + 1), min(2048, int(max(ys)) + 1)
        if bx1 <= bx0 or by1 <= by0: continue
        m = Image.new('L', (bx1 - bx0, by1 - by0), 0); ImageDraw.Draw(m).polygon([(x - bx0, y - by0) for x, y in pp], fill=1); m = np.asarray(m) > 0
        if not m.any(): continue
        best = max(zip(pp, pp[1:] + pp[:1]), key=lambda e: math.hypot(e[1][0] - e[0][0], e[1][1] - e[0][1]))
        th = math.atan2(best[1][1] - best[0][1], best[1][0] - best[0][0]) + math.pi / 2   # strips run along the long edge
        yy, xx = np.mgrid[by0:by1, bx0:bx1]; yy = yy + int(y0); xx = xx + int(x0)   # DEM-lattice metres: the strip index must not depend on the cell
        # Luftwaffe photographs of 14 / 16 July 1943 (Wheatley 2019, Figs. 2, 35, 40): near the Psel villages the arable land is a dense
        # patchwork of kolkhoz brigade strips 25-50 m wide in blocks of 5-15, bright (cut / ripe) and dark (standing crop, ploughed)
        # alternating; on the plateau at 252.2 large uniform fields with faint boundaries.  Here ~70 % of the polygons within 1.5 km of a
        # village become strip blocks, ~30 % elsewhere; the rest is one large field of one crop.
        # (the state-farm land round 252.2, Komsomolets and Stalinskoye was large mechanised fields - Figs. 4, 5, 9 - so the OSM
        # polygons, which are those fields, stay large; the brigade strips of the villages come from the kolkhoz blocks above)
        if STRIPS and (k * 2654435761) % 100 < 25:
            w = 25.0 + ((k * 7919) % 26); off = (k * 104729) % 1000
            idx = np.floor((xx * math.cos(th) + yy * math.sin(th) + off) / w).astype(np.int64)
            pat = STRIP_PATTERNS[(k * 2246822519) % len(STRIP_PATTERNS)]
            typ = np.asarray(pat, np.uint8)[np.mod(idx + (k % 7), len(pat))]
        else:                             # one large field of one crop
            typ = np.full(xx.shape, FIELD_TYPES[((k * 40503) % 1000003) % len(FIELD_TYPES)], np.uint8)
        sub = fid[by0:by1, bx0:bx1]; sub[m] = typ[m]
    # field blocks traced from the 16 July 1943 Luftwaffe photographs (layout 'fields_1943'): they override the OSM cover
    for f43 in FIELDS43:
        if not clip_poly(f43['pts'], x0, y0): continue
        pp = to_px(f43['pts'], x0, y0)
        m = Image.new('L', (2048, 2048), 0); ImageDraw.Draw(m).polygon(pp, fill=255); m = np.asarray(m) > 0
        if not m.any(): continue
        keep = np.isin(cov, LINEAR) & m
        cov[m & ~keep] = FIELD
        pat = f43.get('pattern', [1])
        if STRIPS and f43.get('strip_width'):   # strips of alternating crops, counted along the axis (bearing in degrees from east)
            th = math.radians(f43.get('axis_deg', 0.0)); yy, xx = np.mgrid[0:2048, 0:2048]
            idx = np.floor(((xx + x0) * math.cos(th) + (yy + y0) * math.sin(th)) / float(f43['strip_width'])).astype(np.int64)
            typ = np.asarray(pat, np.uint8)[np.mod(idx, len(pat))]
            fid[m & ~keep] = typ[m & ~keep]
        else:
            fid[m & ~keep] = pat[0]
    # fields meet at the roads (vanilla: the crops run to the shoulder; OSM farmland stops 10-40 m short of roads and
    # railways, leaving grass slivers that read as bright bands along every road): grass gaps narrower than ~60 m between
    # fields, and grass within 20 m of a road / track / railway next to a field, become field with the neighbour's crop
    from scipy import ndimage as ndi
    fm = cov == FIELD
    if fm.any():
        wetz = MO.dilate(np.isin(cov, (WATER, MARSH)), 61)
        gap = MO.erode(MO.dilate(fm, 61), 61) & (cov == GRASS) & ~wetz
        gap |= (cov == GRASS) & MO.dilate(np.isin(cov, (ROAD, TRACK)), 41) & MO.dilate(fm, 41) & ~wetz   # not the railway: a grass verge keeps the ploughland off the embankment
        if steep is not None: gap &= ~steep
        if gap.any():
            _, (iy, ix) = ndi.distance_transform_edt(~fm, return_indices=True)
            fid[gap] = fid[iy[gap], ix[gap]]; cov[gap] = FIELD
        del wetz, gap
    del fm
    pm = period_mask_cell(i, j)
    if pm is not None:   # trim the modern villages to the 1941 built-up area (dilated ~100 m)
        from PIL import ImageFilter
        pmd = MO.dilate(pm, 51)
        cov[(cov == VILLAGE) & ~pmd] = GRASS
        cov[(cov == BUILDING) & ~pmd] = GRASS
        cov[np.asarray(farm43) > 0] = VILLAGE   # the 1943 state-farm yards are not subject to the trim
        cov[(np.asarray(vil43) > 0) & (cov == GRASS)] = VILLAGE   # nor the 1943 villages (they come from the period sheet itself)
        pmp = MO.dilate(period_mask_cell(i, j, PAD), 51); vpf = np.pad((np.asarray(farm43) > 0) | (np.asarray(vil43) > 0), PAD)
        VIL_PAD[0] &= (pmp | vpf)
        buildings = [pp for pp in buildings if 0 <= pp[0][0] < 2048 and 0 <= pp[0][1] < 2048 and pmd[int(pp[0][1]), int(pp[0][0])]]
    return cov, fid, lines, buildings

# ------------------------------------------------------------------ sampling helpers (style from the Mius template)
def sampler(hist, rng, n):
    h = np.asarray(hist, np.float64); h = h / h.sum() if h.sum() else np.ones(len(h)) / len(h)
    return rng.choice(len(h), size=n, p=h).astype(np.uint8)

def fill_by_soil(soil, style, key, rng, n_vals):
    out = np.zeros(soil.shape, np.uint8)
    for s in np.unique(soil):
        m = soil == s; st = style.get(str(int(s))) or style['0']
        out[m] = sampler(st[key], rng, int(m.sum()))
    return out

# ------------------------------------------------------------------ contours (marching squares on a coarse grid)
def contours(h, step, interval, x0=0.0, y0=0.0):
    """h: (n,n) heights at `step` m spacing, h[0] = south. Returns list of segments ((x,y),(x,y)) in metres."""
    segs = []
    lv = np.arange(math.ceil(h.min() / interval) * interval, h.max(), interval)
    a = h[:-1, :-1]; b = h[:-1, 1:]; c = h[1:, 1:]; dd = h[1:, :-1]   # sw, se, ne, nw corners of each square
    for L in lv:
        sa, sb, sc, sd = a > L, b > L, c > L, dd > L
        ys, xs = np.nonzero((sa != sb) | (sb != sc) | (sc != sd) | (sd != sa))
        for yy, xx in zip(ys, xs):
            va, vb, vc, vd = a[yy, xx], b[yy, xx], c[yy, xx], dd[yy, xx]
            pts = []
            def interp(p0, v0, p1, v1):
                t = (L - v0) / (v1 - v0) if v1 != v0 else 0.5
                return (x0 + (p0[0] + (p1[0] - p0[0]) * t) * step, y0 + (p0[1] + (p1[1] - p0[1]) * t) * step)
            if (va > L) != (vb > L): pts.append(interp((xx, yy), va, (xx + 1, yy), vb))
            if (vb > L) != (vc > L): pts.append(interp((xx + 1, yy), vb, (xx + 1, yy + 1), vc))
            if (vc > L) != (vd > L): pts.append(interp((xx + 1, yy + 1), vc, (xx, yy + 1), vd))
            if (vd > L) != (va > L): pts.append(interp((xx, yy + 1), vd, (xx, yy), va))
            if len(pts) == 2: segs.append((pts[0], pts[1]))
            elif len(pts) == 4: segs.append((pts[0], pts[1])); segs.append((pts[2], pts[3]))
    return segs

# ------------------------------------------------------------------ op map mesh
def opmap_mesh(h8, lines, x0, y0):
    """Vertices/indices for the AZG2 line mesh: 250 m grid, 5 m contours (2.5 m thin in flat parts would need more),
    roads/tracks/railway/rivers from OSM."""
    V = []; Cc = []; I = []
    def seg(p, q, col):
        # clip the segment to the cell square (Liang-Barsky); endpoints outside must not be clamped, that rotates lines
        t0, t1 = 0.0, 1.0; dx, dy = q[0] - p[0], q[1] - p[1]
        for pk, qk in ((-dx, p[0]), (dx, 2048.0 - p[0]), (-dy, p[1]), (dy, 2048.0 - p[1])):
            if pk == 0:
                if qk < 0: return
            else:
                r = qk / pk
                if pk < 0: t0 = max(t0, r)
                else: t1 = min(t1, r)
        if t0 >= t1: return
        p, q = (p[0] + dx * t0, p[1] + dy * t0), (p[0] + dx * t1, p[1] + dy * t1)
        n = len(V); V.append(p); V.append(q); Cc.append(col); Cc.append(col); I.append(n); I.append(n + 1)
    for k in range(9):
        t = k * 256.0; col = C.COL_GRID_BOLD if k in (0, 8) else C.COL_GRID
        seg((t, 0.0), (t, 2048.0), col); seg((0.0, t), (2048.0, t), col)
    hs = smooth(h8, 2)
    for (p, q) in contours(hs, 8.0, 5.0): seg(p, q, C.COL_CONTOUR)
    for (pp, col, dash, cover) in lines:
        if col is None: continue
        for a, b in zip(pp, pp[1:]):
            if dash:
                L = math.hypot(b[0] - a[0], b[1] - a[1]); n = max(1, int(L / 30))
                for k in range(n):
                    t0 = k / n; t1 = (k + 0.6) / n
                    seg((a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0), (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1), col)
            else:
                seg(a, b, col)
                if cover == RAIL:   # cross ticks every 60 m
                    L = math.hypot(b[0] - a[0], b[1] - a[1])
                    if L > 1:
                        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
                        for s in np.arange(30, L, 60):
                            cx, cy = a[0] + ux * s, a[1] + uy * s
                            seg((cx - uy * 12, cy + ux * 12), (cx + uy * 12, cy - ux * 12), col)
    return np.array(V, np.float64).reshape(-1, 2), np.array(Cc, np.uint32), np.array(I, np.uint32)

# ------------------------------------------------------------------ the generator
def smooth(a, r):
    """Box blur (radius r cells) applied twice ~ gaussian; edges clamped."""
    for _ in range(2):
        p = np.pad(a, r, mode='edge'); c = np.cumsum(np.cumsum(p, 0), 1); c = np.pad(c, ((1, 0), (1, 0)))
        n = 2 * r + 1
        a = (c[n:, n:] - c[:-n, n:] - c[n:, :-n] + c[:-n, :-n]) / (n * n)
    return a

def normals(h2):
    gy, gx = np.gradient(h2)          # per metre, rows south->north
    n = np.stack([-gx, -gy, np.ones_like(gx)], -1); n /= np.linalg.norm(n, axis=-1, keepdims=True)
    img = np.empty(h2.shape + (4,), np.uint8); img[..., :3] = np.clip((n + 1) * 127.5, 0, 255); img[..., 3] = 255
    return img

def flip_rows(a):
    """PIL images are drawn with row 0 at the top; the engine wants row 0 = south. Our pixel y = metres north, so a drawn
    image already has row index = y; nothing to flip. Kept as identity for clarity."""
    return a

LINEAR = (RAIL, ROAD, TRACK, WATER, BUILDING, MARSH)

def ragged_edges(cov, fid, origin):
    """OSM polygons give razor-straight cover edges (wood / field / village against grass) that stick out in the game.
    The cover map is resampled through a smooth displacement field (±6 m at a ~90 m wavelength) plus a 1 m dither,
    so edges wobble and dissolve like the hand-painted vanilla cells. Roads, rails, water, buildings keep their exact
    pixels.  The fields are value noise in block coordinates (texsynth.gnoise): identical on both sides of a cell border."""
    n = cov.shape[0]
    # 25 Oct (user: the field / steppe edge is a hard straight line in game): two wavelengths of displacement (±9 m at
    # 90 m, ±3 m at 23 m) plus a 1.5 m dither, so the edge wanders over ~10 m and dissolves into a mixed fringe
    oy = TX.gnoise((n, n), origin, 88.0, 11) * 9.0 + TX.gnoise((n, n), origin, 23.0, 15) * 3.0 + TX.gnoise((n, n), origin, 1, 12) * 1.5
    ox = TX.gnoise((n, n), origin, 88.0, 13) * 9.0 + TX.gnoise((n, n), origin, 23.0, 16) * 3.0 + TX.gnoise((n, n), origin, 1, 14) * 1.5
    yy, xx = np.mgrid[0:n, 0:n]
    sy = np.clip((yy + oy).astype(np.int32), 0, n - 1); sx = np.clip((xx + ox).astype(np.int32), 0, n - 1)
    w = cov[sy, sx]
    keep = np.isin(cov, LINEAR) | np.isin(w, LINEAR)
    out = np.where(keep, cov, w).astype(cov.dtype)
    fid[:] = np.where(keep, fid, fid[sy, sx])
    return out

RELIEF_SMOOTH_M = 12.0   # radius of the box blur (applied twice) that rounds the 30 m DEM facets; 0 = off

def hei_path(hei_dir, i, j):
    """heightmap file of block cell (i, j) in the DEM-lattice directory (either border spelling), or None"""
    nm = hei_name(i, j)
    for n2 in (nm, ('Mg' if nm.startswith('Mx') else 'Mx') + nm[2:]):
        fp = os.path.join(hei_dir, f'{n2}_hei_map.cell.loc_def.bin')
        if os.path.exists(fp): return fp
    return None

def round_relief(h, i, j, hei_dir, radius_m):
    """Seam-safe rounding of the 0.5 m heightmap: the 30 m Copernicus DEM comes in as flat facets with creases every
    30 m, which read as 'rough' gullies in the game. The blur is padded with the real strips of the four neighbouring
    cells (so both sides of a cell border see the same data), edge-clamped only where a neighbour does not exist."""
    if radius_m <= 0: return h
    r = int(round(radius_m / (CELL / h.shape[0])))
    n = h.shape[0]
    big = np.pad(h, r, mode='edge')
    def strip(ii, jj):
        if not (0 <= ii + BLOCK_I0 < OLD_COLS and 0 <= jj + BLOCK_J0 < OLD_ROWS): return None   # neighbours beyond the block still exist in the DEM lattice
        fp = hei_path(hei_dir, ii, jj)
        if fp is None: return None
        hu, _ = pha6_decode(fp); return hu * (MAXH / 65535.0)
    # rows run south -> north: j+1 is the cell to the SOUTH (row 0 of ours borders its last row)
    sN = strip(i, j - 1); sS = strip(i, j + 1); sW = strip(i - 1, j); sE = strip(i + 1, j)
    if sS is not None: big[0:r, r:r + n] = sS[n - r:n, :]
    if sN is not None: big[r + n:, r:r + n] = sN[0:r, :]
    if sW is not None: big[r:r + n, 0:r] = sW[:, n - r:n]
    if sE is not None: big[r:r + n, r + n:] = sE[:, 0:r]
    del sN, sS, sW, sE
    a = big.astype(np.float64)
    for _ in range(2):
        c = np.cumsum(np.cumsum(np.pad(a, r, mode='edge'), 0), 1); c = np.pad(c, ((1, 0), (1, 0))); k = 2 * r + 1
        a = (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)
    return a[r:r + n, r:r + n].astype(np.float32)

def build_water_levels(feats, hei_dir):
    """one monotone water surface for the Psel over the whole block (tools/waterlevel.py)"""
    import waterlevel as WL
    n = int(CELL / WL.G); dem = np.zeros((ROWS * n, COLS * n), np.float32)   # block DEM at 16 m, row 0 = south
    for j in range(ROWS):
        for i in range(COLS):
            fp = hei_path(hei_dir, i, j)
            if fp is None: continue
            hu, _ = pha6_decode(fp); f = hu.shape[0] // n
            r0 = (ROWS - 1 - j) * n
            dem[r0:r0 + n, i * n:(i + 1) * n] = (hu * (MAXH / 65535.0)).reshape(n, f, n, f).mean((1, 3)); del hu
    def heights(x, y):
        c = np.clip(((x - BLOCK_X0) / WL.G).astype(np.int64), 0, dem.shape[1] - 1); r = np.clip(((y - BLOCK_Y0) / WL.G).astype(np.int64), 0, dem.shape[0] - 1)
        return dem[r, c]
    def water_of(kind, t):
        if kind == 'area':
            return area_cover(t) == WATER and (PONDS or t.get('water') in ('river', 'stream', 'canal', 'oxbow'))
        if kind == 'line':
            st = line_style(t); return st[1] if st is not None and st[0] == WATER else 0
        return 0
    nlev = WL.build(feats, water_of, heights, BLOCK_X0, BLOCK_Y0, COLS * CELL, ROWS * CELL)
    print('water levels: one surface for the block,', nlev, 'levels in steps of %.1f m' % WL.STEP, flush=True)

def gen_cell(i, j, feats, places, hei_dir, tpl, out_dir, style, no_ai=False, seed=0):
    name = cell_name(i, j); x0, y0 = cell_origin(i, j)
    rng = np.random.default_rng(seed + i * 100 + j)
    od = os.path.join(out_dir, name); os.makedirs(od, exist_ok=True)
    def path(e): return os.path.join(od, f'{e}.cell.loc_def.bin')
    # heights
    hp = hei_path(hei_dir, i, j)
    if hp is None: raise FileNotFoundError('no heightmap %s_hei_map.cell.loc_def.bin in %s for block cell %s' % (hei_name(i, j), hei_dir, name))
    hu, _ = pha6_decode(hp); h = hu * (MAXH / 65535.0); del hu
    h = round_relief(h, i, j, hei_dir, RELIEF_SMOOTH_M)
    # cover
    T = [time.time()]
    def lap(label): T.append(time.time()); print('    %-10s %5.1fs' % (label, T[-1] - T[-2]), flush=True)
    h2s = h.reshape(2048, 2, 2048, 2).mean((1, 3)); sl2 = np.hypot(*np.gradient(h2s)); steep = np.repeat(np.repeat(sl2 > 0.10, 2, 0), 2, 1)[:2048, :2048]; del h2s, sl2
    cov, fid, lines, buildings = rasterise(feats, i, j, rng, steep); lap('cover')
    cov = ragged_edges(cov, fid, to_block(x0, y0))
    soil = np.zeros_like(cov)
    for c, s in SOIL_OF.items(): soil[cov == c] = s
    soil[(cov == FIELD) & ((fid == 2) | (fid == 3))] = 7   # field_green
    soil[(cov == FIELD) & (fid == 4)] = 15                  # ploughed (the vanilla 'bump' soil is the furrowed field texture, see Petropolye PgD5)
    # tracks and streets the vanilla way (tools/tracks.py): pave strips with a second strip beside them, trampled village streets
    import tracks as TKS
    n_strip, n_second, n_zone = TKS.paint(soil, cov, lines, to_block(x0, y0), dict(ROAD=ROAD, TRACK=TRACK, FIELD=FIELD, WATER=WATER, MARSH=MARSH, RAIL=RAIL, BUILDING=BUILDING, VILLAGE=VILLAGE), vil_mask=MO.dilate(cov == VILLAGE, 21))
    # texture classes for tools/texref.py (copied with their soil pattern from the Petropolye cells); 0 = keep the soil
    tcls = np.zeros_like(cov)
    tcls[(cov == FIELD) & (fid == 1)] = TR.CROP; tcls[(cov == FIELD) & (fid == 4)] = TR.PLOUGH
    # field margins: a broken 4-7 m band of bare dark earth (road_back 11) round every field block, as in Petropolye
    fm = cov == FIELD
    ring = MO.dilate(fm, 5) & ~fm & np.isin(cov, (GRASS, TRACK)) & (soil != 10)   # also on the road corridor side, never over the pave lines   # 2 m and broken (user, 25 Oct: the field blocks were outlined like a drawing)
    soil[ring & (TX.gnoise(cov.shape, to_block(x0, y0), 5.0, 21) > 0.25)] = 11
    del fm, ring
    # railway: ballast strip (soil 8 between road_back shoulders, as in the vanilla Korotich cells) on a ~1.5 m embankment
    rail_lines = [pp for (pp, col, dash, c) in lines if c == RAIL]
    rail_lines = dedupe_rails(rail_lines)   # both OSM ways = the double track of 1943 (SINGLE_TRACK drops one)
    rail_strip = None
    if rail_lines:
        emb = Image.new('L', (2048, 2048), 0); de = ImageDraw.Draw(emb)
        sh = Image.new('L', (2048, 2048), 0); ds = ImageDraw.Draw(sh)
        bal = Image.new('L', (2048, 2048), 0); dbl = ImageDraw.Draw(bal)
        for pp in rail_lines:
            de.line(pp, fill=255, width=9, joint='curve'); ds.line(pp, fill=255, width=11, joint='curve'); dbl.line(pp, fill=255, width=6, joint='curve')
        verge = MO.dilate(np.asarray(sh) > 0, 21) & np.isin(cov, (FIELD, GRASS))   # 10 m grass verge each side: no crops or ploughland on the embankment
        soil[verge] = 0; tcls[verge] = 0; cov[verge & (cov == FIELD)] = GRASS
        soil[np.asarray(sh) > 0] = 11; soil[np.asarray(bal) > 0] = 8
        rail_strip = np.asarray(sh) > 0   # the 11 m track bed: no grass billboards on it (user, 25 Oct: grass growing over the rails)
        e = smooth(np.asarray(emb).astype(np.float32) / 255.0, 4)   # ~9 m crest, ~5 m shoulders
        h += np.repeat(np.repeat(e, 2, 0), 2, 1) * 1.5
        del emb, sh, bal, e
    # water: OSM water polygons / river buffers. Level = local terrain minimum (200 m window) + 0.4 m on the 4 m index
    # grid; the bed under the water is carved 1.2 m below the level with smoothed banks, because the 30 m DEM has no
    # channel at all (the vanilla river cells, e.g. Korotich KgD3, have a flat bed just under the level).
    # The vanilla way (MxD1 Mius, Korotich KgD3): the level index covers a generous zone and the WATER PLANE IS ONLY SEEN
    # WHERE THE TERRAIN LIES BELOW IT - the shoreline is the smooth terrain contour at the level, never the 4 m index grid.
    # So: level per 1 m water pixel (running minimum of the DEM along the water, 100 m, + 0.3), a bed that deepens
    # gently from the shore (1:3 to 1.6 m), banks outside lowered to a 1:4 slope and never left below the level, and the
    # index set 8 m beyond the polygon.  (The first version mixed a 1 m mask with a 4 m level grid: pixels without a
    # level got target height -1.2 m ABSOLUTE and dug 3-7 m craters along every shore - the 'canyons' of 25 Oct.)
    import waterlevel as WL
    wm = (cov == WATER)
    yy_, xx_ = np.mgrid[0:2048, 0:2048]; gx_ = xx_ + x0 + 0.5; gy_ = yy_ + y0 + 0.5   # old-frame metres of every pixel (cover row 0 = south)
    if WL.LEVEL is not None and wm.any():
        dry = WL.sample(WL.DRY, gx_, gy_) & wm
        cov[dry] = MARSH; wm &= ~dry   # branches of the OSM water polygon that climb the gully sides: wet meadow, not water
    has_water = wm.sum() > 2500   # ponds under 0.25 ha are dropped (the 30 m DEM does not resolve their hollows)
    idx = vals = None
    if has_water:
        from scipy import ndimage as ndi
        h2w = h.reshape(2048, 2, 2048, 2).mean((1, 3)).astype(np.float32)
        # the level: the block-wide monotone surface (tools/waterlevel.py), so neighbouring cells agree and the river
        # falls in a few 0.5 m steps instead of the 39 slabs per cell the per-cell running minimum gave (user, 25 Oct)
        lvl_ext = WL.sample(WL.LEVEL, gx_, gy_).astype(np.float32)
        d_out = ndi.distance_transform_edt(~wm)
        d_in = ndi.distance_transform_edt(wm)
        zone = d_out <= 40.0
        # terrain: bed inside, a bank outside whose slope varies along the river (1:5 slip-off banks to 1:1.6 cut banks,
        # seam-free noise) out to 40 m (26 Oct, user: the old 12 m / 1:4 zone met the valley side in a dark vertical wall
        # where the bed had to be cut 4 m down), only lowering; nothing in the shore zone below level + 0.2 (no puddles)
        bed = lvl_ext - np.minimum(1.6, 0.15 + 0.35 * d_in)
        bslope = 0.42 + 0.22 * TX.gnoise(wm.shape, to_block(x0, y0), 140.0, 57) + 0.06 * TX.gnoise(wm.shape, to_block(x0, y0), 31.0, 58)
        bank = lvl_ext + 0.25 + bslope * d_out
        target = np.where(wm, bed, np.where(zone, np.minimum(h2w, bank), h2w))
        target = np.where(zone & ~wm, np.maximum(target, lvl_ext + 0.2), target)
        delta = (target - h2w).astype(np.float32)
        delta = np.clip(delta, -8.0, 1.5)
        delta = smooth(delta, 2).astype(np.float32)
        h += np.repeat(np.repeat(delta, 2, 0), 2, 1)
        # the level index (4 m): the polygon dilated by 8 m, level quantised to 0.25 m (<= 63 levels, else 0.5 m)
        zone4 = (d_out <= 8.0).reshape(512, 4, 512, 4).max((1, 3))
        l4 = lvl_ext[2::4, 2::4]   # the surface is already in 0.5 m steps: sample, do not average (averaging made in-between levels)
        for q in (4.0, 2.0, 1.0):
            lq = np.where(zone4, np.round(l4 * q) / q, 0); vals = np.unique(lq[zone4])
            if len(vals) <= 63: break
        vals = vals[:63]
        idx = np.zeros((512, 512), np.uint8)
        for k, v in enumerate(vals): idx[lq == v] = k + 1
        del h2w, lvl_ext, d_out, d_in, zone, bed, bank, target, delta, zone4, l4, lq
    del yy_, xx_, gx_, gy_
    # natural banks (26 Oct, user: 'the bank should be natural, here it is grass'). Measured on the vanilla Mius river cell
    # MxD1: the ground within ~20 m of the water is a mix of marsh (1) ~20 %, forest ground (12) ~20 %, leaves (13) ~30 %
    # and grass ~20 %, with willow bushes, bushes and reeds thick along the water. A riparian belt 6-24 m wide (seam-free
    # noise) is painted that way; flora for it is scattered below (RIPARIAN).
    RIPARIAN[0] = None
    wmb = (cov == WATER)
    if wmb.sum() > 400:
        from scipy import ndimage as ndi
        d_o = ndi.distance_transform_edt(~wmb)
        org = to_block(x0, y0)
        wr = 6.0 + 18.0 * (0.5 + 0.5 * TX.gnoise(wmb.shape, org, 170.0, 61)) + 4.0 * TX.gnoise(wmb.shape, org, 37.0, 62)
        rz = (d_o > 0) & (d_o <= wr) & np.isin(cov, (GRASS, MARSH, FIELD, SCRUB))
        cov[rz & (cov == FIELD)] = GRASS
        n1 = TX.gnoise(wmb.shape, org, 7.0, 63) + 0.5 * TX.gnoise(wmb.shape, org, 2.0, 64)
        rs = np.where(n1 > 0.45, 13, np.where(n1 > 0.0, 12, np.where(n1 > -0.4, 1, 0))).astype(soil.dtype)
        edge = rz & (d_o <= 1.5 + 1.5 * (TX.gnoise(wmb.shape, org, 5.0, 65) + 1.0))   # the waterline: wet mud and leaves
        rs = np.where(edge, np.where(n1 > 0.2, 13, 1), rs).astype(soil.dtype)
        soil[rz] = rs[rz]; tcls[rz] = 0
        soil[wmb] = np.where(n1[wmb] > 0.3, 13, 1).astype(soil.dtype)   # the bed under the water: dark mud / leaves (vanilla 1 and 13)
        tcls[wmb] = 0
        RIPARIAN[0] = (rz, d_o, n1)
        del d_o, wr, rs, edge
    lap('water')
    # micro-relief (25 Oct, user: the vanilla ground is never flat - bumps of 5-20 cm at 2-30 m everywhere, more in the villages)
    import relief as RL
    mr_std = RL.add(h, cov, soil, to_block(x0, y0), dict(WATER=WATER, MARSH=MARSH, ROAD=ROAD, TRACK=TRACK, RAIL=RAIL, VILLAGE=VILLAGE, BUILDING=BUILDING), buildings)
    print('  micro-relief std %.3f m' % mr_std, flush=True); lap('relief')
    # field works (trenches, anti-tank ditch, strongpoints): carved into the heights and the soil, firing positions listed
    trench_recs = []
    works_changed = np.zeros(soil.shape, bool); works_snap = None; works_obj = np.zeros(soil.shape, bool); works_bld = works_obj
    if WORKS:
        import works as W
        soil_before = soil.copy()
        trench_recs = W.apply_cell(h, soil, x0, y0, WORKS, open_mask=np.isin(cov, (GRASS, FIELD, SCRUB)), origin=to_block(x0, y0))
        tcls[np.isin(soil, (3, 11, 14))] = 0   # dug earth, spoil and trampled ground keep their soil (the field / steppe classes would paint over them)
        # 25 Oct (user): nothing may collide with the works - the dug ground (soil 14: trenches, pits, ditch) keeps its soil
        # whatever settle.py paints later, no object or plant within 4 m of it, no house / shed / fence / barn within 12 m
        works_changed = soil != soil_before; works_snap = soil.copy(); del soil_before
        works_obj = MO.dilate(soil == 14, 9); works_bld = MO.dilate(soil == 14, 25)
    h2 = h.reshape(2048, 2, 2048, 2).mean((1, 3)); h8 = h.reshape(256, 16, 256, 16).mean((1, 3))
    if True:   # heights are always re-encoded (relief rounding)
        from pha6 import encode as pha6_encode
        open(path('hei_map'), 'wb').write(pha6_encode(np.clip(h / (MAXH / 65535.0), 0, 65535).astype(np.float32), hp, candidates=[0, 63, 52, 24, 36, 40, 3, 13]))
        print('  works:', len(trench_recs), 'positions,', len(rail_lines), 'railway lines, heights re-encoded', flush=True); lap('works+hei')
    else:
        shutil.copy(hp, path('hei_map'))
    del h
    # steep balka sides: bumps/clay
    # steep balka sides (26 Oct, user: 'the ravines should look natural'): the uniform ploughed-texture band (soil 15) on every
    # slope over 0.4 read as a pale stripe along each ravine; the sides are now steppe grass with eroded clay / sand
    # scars and dark earth where the slope is steepest, in noise patches
    slope = np.hypot(*np.gradient(h2))
    st_ = (slope > 0.4) & (cov == GRASS) & (soil != 14)
    if st_.any():
        n2 = np.repeat(np.repeat(TX.gnoise(slope.shape, (to_block(x0, y0)[0] / 2, to_block(x0, y0)[1] / 2), 6.0, 71), 2, 0), 2, 1)[:2048, :2048] if slope.shape[0] != 2048 else TX.gnoise(slope.shape, to_block(x0, y0), 12.0, 71)
        s2 = np.repeat(np.repeat(slope, 2, 0), 2, 1)[:2048, :2048] if slope.shape[0] != 2048 else slope
        st2 = np.repeat(np.repeat(st_, 2, 0), 2, 1)[:2048, :2048] if st_.shape[0] != 2048 else st_
        soil[st2 & (n2 > 0.45)] = 3; soil[st2 & (n2 < -0.55)] = 5; soil[st2 & (s2 > 0.8) & (n2 > 0.1) & (n2 <= 0.45)] = 2
    slope2 = np.repeat(np.repeat(slope, 2, 0), 2, 1)[:2048, :2048] if slope.shape[0] != 2048 else slope
    # leaves / forest ground mixed under the trees (both are Petropolye hedge / wood soils)
    wood = (cov == WOOD) & (soil == 12)
    if wood.any(): soil[wood & (TX.gnoise(soil.shape, to_block(x0, y0), 14.0, 31) > 0.0)] = 13
    del wood
    cls = np.zeros((64, 64), np.uint8)
    cv = cov.reshape(64, 32, 64, 32).transpose(0, 2, 1, 3).reshape(64, 64, 1024)
    for c, k in CLASS_OF.items():
        if k: cls[(cv == c).mean(-1) > 0.3] = k
    C.write_grid(path('class_map'), cls); cls_grid = cls
    atf1.write(path('nor_map'), normals(h2), 'DXT1')
    if has_water: C.write_water(od, idx, vals.astype(np.float32), wm1=(cov == WATER))
    # op map background: 512 px = 4 m. Vanilla (Mius MgG3 / Petropolye measured): the paper is a hypsometric grey,
    # grey = 124.4 + 0.407 * height (m) (190 at 160 m, 230 at 260 m) - fields are NOT painted; woods a mottled green,
    # gardens / scrub / village plots an olive beige; roads and water come from the line mesh / the engine.
    cv4 = cov.reshape(512, 4, 512, 4)[:, 0, :, 0]
    h512 = h2.reshape(512, h2.shape[0] // 512, 512, h2.shape[1] // 512).mean((1, 3)) if h2.shape[0] % 512 == 0 else np.repeat(np.repeat(h2, 2, 0), 2, 1)[:2048, :2048].reshape(512, 4, 512, 4).mean((1, 3))
    g = np.clip(124.4 + 0.407 * h512, 150, 240)
    back = np.empty((512, 512, 4), np.uint8); back[..., 0] = g; back[..., 1] = g; back[..., 2] = g; back[..., 3] = 255
    nb = TX.gnoise((512, 512), to_block(x0, y0), 8.0 / 4, 71)   # noise in 4 m pixels
    nb2 = TX.gnoise((512, 512), to_block(x0, y0), 3.0 / 4, 72)
    def tint(mask, cols):
        if not mask.any(): return
        k = np.clip(((nb[mask] + nb2[mask] * 0.5) * 0.7 + 0.5) * len(cols), 0, len(cols) - 1).astype(int)
        back[mask, :3] = np.asarray(cols, np.uint8)[k]
    tint(cv4 == WOOD, [(131, 165, 115), (139, 174, 123), (139, 178, 123), (148, 186, 131)])
    tint((cv4 == ORCHARD) | (cv4 == SCRUB), [(180, 182, 164), (189, 194, 172), (197, 198, 180)])
    tint((cv4 == VILLAGE) | (cv4 == BUILDING), [(197, 198, 180), (201, 204, 180), (205, 209, 186), (205, 210, 189)])
    tint((cv4 == WATER) | (cv4 == MARSH), [(176, 196, 205), (186, 204, 211)])
    atf1.write(path('back'), back, 'DXT1', mipmaps=False)
    # op map line mesh + sprites
    V, Cc, I = opmap_mesh(h8, lines, x0, y0)
    C.write_opmap(path('opmap'), os.path.join(tpl, 'opmap.cell.loc_def.bin'), V, Cc, I)
    sprites = []
    # spot heights: local maxima of the 8 m grid with a 400 m window
    hm = smooth(h8, 1); n = 75   # 600 m window
    from numpy.lib.stride_tricks import sliding_window_view
    pad = np.pad(hm, n // 2, mode='edge'); win = sliding_window_view(pad, (n, n)); mx = win.max((-1, -2)); mean = win.mean((-1, -2))
    ys, xs = np.nonzero((hm >= mx) & (hm > mean + 4))
    picked = []
    for yy, xx in sorted(zip(ys, xs), key=lambda q: -hm[q[0], q[1]]):
        if all(abs(yy - a) > 40 or abs(xx - b) > 40 for a, b in picked): picked.append((yy, xx))
    hts = [(hx - x0, hy - y0, lab) for (hx, hy, lab) in HEIGHTS43 if x0 <= hx < x0 + CELL and y0 <= hy < y0 + CELL]   # the 1943 map's spot heights (layout)
    for (hx, hy, lab) in hts:
        sprites.append(dict(name='map_point', label=lab, col=0x80101010, col2=0x80101010, x=float(hx), y=float(hy), scale=1.0, kind=7, flag=1))
    for yy, xx in picked[:8]:   # DEM maxima elsewhere (none within 600 m of a 1943 height)
        if all(math.hypot(xx * 8.0 - hx, yy * 8.0 - hy) > 600 for (hx, hy, _) in hts):
            sprites.append(dict(name='map_point', label='%d' % round(hm[yy, xx]), col=0x80101010, col2=0x80101010, x=xx * 8.0, y=yy * 8.0, scale=1.0, kind=7, flag=1))
    for (px, py), t, key in places:
        if x0 <= px < x0 + CELL and y0 <= py < y0 + CELL:
            sprites.append(dict(name='map_point', label=key, col=0xC0000000, col2=0xC0000000, x=px - x0, z=1.0, y=py - y0, scale=1.0, kind=0, flag=1))
    for pp in buildings[:400]:
        cx = sum(p[0] for p in pp) / len(pp); cy = sum(p[1] for p in pp) / len(pp)
        if 0 <= cx < 2048 and 0 <= cy < 2048: sprites.append(dict(name='build', col=0xff694320, x=cx, y=cy, scale=0.4, kind=1, flag=0))
    C.write_sprites(path('opmap_tri'), sprites)
    lap('opmap')
    # vegetation
    fx, fy, fr, ft = [], [], [], []
    def scatter(mask, dens, mix):
        n = int(mask.sum() * dens)
        if n <= 0: return
        yy, xx = np.nonzero(mask); pick = rng.integers(0, len(yy), n)
        types = np.asarray([t for t, w in mix]); wts = np.asarray([w for t, w in mix], np.float64); wts /= wts.sum()
        fx.append(xx[pick] + rng.random(n)); fy.append(yy[pick] + rng.random(n)); fr.append(rng.random(n)); ft.append(rng.choice(types, n, p=wts))
    dug = MO.dilate(soil == 14, 25)   # earthworks + 12 m: no trees / scrub on the ditch and trench walls
    scatter((cov == WOOD) & ~dug, DENSITY['WOOD'], FLORA['WOOD']); scatter((cov == SCRUB) & ~dug, DENSITY['SCRUB'], FLORA['SCRUB'])
    scatter(cov == ORCHARD, DENSITY['ORCHARD'], FLORA['ORCHARD'])
    # village trees only in the street zone (yards and gardens, 70 m), none on the open sovkhoz land - the whole village /
    # farm polygon used to be sown at 1 tree per 150 m2 (user, 25 Oct: far too many trees in the settlements)
    street_zone = MO.dilate(np.isin(cov, (ROAD, TRACK)), 141) & ~FARM_MASK[0] if FARM_MASK[0] is not None else MO.dilate(np.isin(cov, (ROAD, TRACK)), 141)
    scatter((cov == VILLAGE) & street_zone, DENSITY['VILLAGE'], FLORA['VILLAGE'])
    scatter((cov == FIELD) & (fid == 3), DENSITY['FIELD'], FLORA['FIELD_SUNFL'])   # ripe grain, green crop and fallow carry no plants (Petropolye)
    # balkas: bushes and small trees on the steep sides and in the bottoms of the ravines; a bush per ~900 m2 on the open steppe
    steep = (slope2 > 0.12) & (cov == GRASS) & ~dug; scatter(steep, DENSITY['BALKA'], FLORA['BALKA'])
    scatter((cov == GRASS) & ~steep & ~dug, DENSITY['STEPPE'], FLORA['STEPPE'])
    scatter(cov == MARSH, DENSITY['MARSH'], FLORA['MARSH'])
    wmask = (cov == WATER)
    if RIPARIAN[0] is not None:
        # the bank vegetation (vanilla MxD1: verba willow bushes 16, bushes 7 / 8, reeds 6, small trees 3 / 4 along the water,
        # in clumps): reed beds 0-2.5 m inside the water edge and on the waterline, willow / bush thickets on the belt
        rz, d_o, n1 = RIPARIAN[0]
        d_i = ndi.distance_transform_edt(wmask) if wmask.any() else None
        clump = TX.gnoise(cov.shape, to_block(x0, y0), 19.0, 66)
        reed = ((wmask & (d_i <= 2.5)) | (rz & (d_o <= 2.5))) & (clump > -0.1) if d_i is not None else rz & (d_o <= 2.5)
        scatter(reed & ~dug, 1 / 7.0, [(6, 1)])
        thick = rz & (d_o > 1.0) & (clump > 0.15) & ~dug
        scatter(thick & (d_o <= 8.0), 1 / 22.0, [(16, 5), (7, 3), (8, 2), (12, 1)])
        scatter(thick & (d_o > 8.0), 1 / 45.0, [(16, 3), (7, 2), (8, 2), (3, 2), (4, 1), (12, 1)])
        scatter(rz & (clump <= 0.15) & ~dug, 1 / 160.0, [(16, 2), (7, 2), (8, 1)])   # single bushes between the thickets
        RIPARIAN[0] = None
    scatter(cov == MARSH, DENSITY['WATER'] / 2, FLORA['WATER'])   # wet meadow: reeds / willows; open water stays open
    # settlements: street villages generated along the OSM streets inside the 1941 built-up extent (tools/settle.py),
    # the OSM footprints kept; yards, garden plots and clay margins are painted into the soil here
    lap('flora')
    import settle as SE
    objs, vtrees = SE.build(cov, soil, lines, buildings, slope2, rng, VILLAGE, WATER, MARSH, ROAD, TRACK, RAIL, BUILDING, FARM_MASK[0], cell_seed=i * 131 + j * 17, origin=(x0, y0), vil_pad=VIL_PAD[0], pad=PAD, works_mask=works_bld)
    gx = [t[0] for t in vtrees]; gy = [t[1] for t in vtrees]; gtyp = np.array([t[2] for t in vtrees], np.uint8)
    SE.kolkhoz(objs, soil, FARM_MASK[0], cov, rng, WATER, MARSH, BUILDING, road_mask=MO.dilate(np.isin(cov, (ROAD, TRACK, RAIL)), 13), origin=to_block(x0, y0), works_mask=works_bld)   # sovkhoz yards: long barns (builds_cap farm0 / farm1) round a clay yard, off the roads
    lap('settle')
    # ground texture layers by example (tools/texref.py): fields, ploughed land and open steppe take their soil pattern,
    # micro tiles, detail, grass and ambient colour from windows of the Petropolye cells; every other soil its micro layers
    if works_snap is not None:   # the works' soil wins over anything painted after them (yards, plots, farm ground)
        soil[works_changed] = works_snap[works_changed]
    # 26 Oct (user: 'light green blob where the village supposedly is'): the open ground inside village / farm / orchard /
    # scrub polygons (soil 0 between the yards and plots) took the plain per-soil grass pool and showed up as flat light-green
    # shapes of the polygons; it is meadow like the steppe round it, so it takes the steppe class too
    tcls[np.isin(cov, (GRASS, VILLAGE, ORCHARD, SCRUB)) & (soil == 0)] = TR.STEPPE
    tcls[soil == 14] = 0; tcls[works_changed] = 0
    t1 = time.time()
    lay = REF.apply(soil, tcls, rng, origin=to_block(x0, y0))
    if rail_strip is not None and rail_strip.any():
        # the track bed the way the vanilla railway cells (Korotich KgC3 / KgD3) paint it - measured 26 Oct after the user's
        # screenshot of green hatching over the sleepers: the Petropolye reference windows had put the GRASS detail layer
        # (det_map R ~40, micro-tile weight 8) on the ballast; vanilla ballast (soil 8) is det (2, 91, 39, 3) with micro
        # weight 0, the shoulders (soil 11) det (7, 60, 99, 11) weight 4, ambient a dry brown (70, 63, 42)
        bal = rail_strip & (soil == 8); shd = rail_strip & (soil != 8)
        lay['hi'][bal] = 0; lay['hi'][shd] = 4
        nz = (TX.gnoise(soil.shape, to_block(x0, y0), 3.0, 77) * 6).astype(np.int16)
        det = lay['det']
        for msk, base in ((bal, (2, 91, 39, 3)), (shd, (7, 60, 99, 11))):
            for c in range(4): det[..., c][msk] = np.clip(base[c] + nz[msk], 0, 255).astype(np.uint8)
        lac = lay['lac']; f = 2048 // lac.shape[0]
        rs = rail_strip.reshape(lac.shape[0], f, lac.shape[1], f).mean((1, 3)) > 0.3
        lac[rs] = (70, 63, 42, 60)
    C.write_grid(path('mat_map'), (soil | (lay['hi'] << 4)).astype(np.uint8))
    no_grass = (cov == WATER) if rail_strip is None else ((cov == WATER) | rail_strip)   # no grass billboards standing in the river (user, 25 Oct) or on the track bed
    rail_strip = no_grass
    if rail_strip is not None:   # bare ballast and shoulders: the Petropolye pools put grass on soil 8 / 11
        g_ = lay['grass']; f_ = g_.shape[0] // 2048 if g_.shape[0] >= 2048 else None
        if f_: g_[np.repeat(np.repeat(rail_strip, f_, 0), f_, 1)[:g_.shape[0], :g_.shape[1]]] = 0
        else: g_[rail_strip.reshape(g_.shape[0], 2048 // g_.shape[0], g_.shape[1], 2048 // g_.shape[1]).max((1, 3))] = 0
    C.write_grid(path('grass_map'), lay['grass']); C.write_grid(path('vars_map'), lay['vars'])
    atf1.write(path('det_map'), lay['det'], 'DXT5'); atf1.write(path('land_ambient_col'), lay['lac'], 'DXT5')
    del lay, tcls; lap('textures')
    if gx:
        g_ = np.array(gx); h_ = np.array(gy); ok = (g_ >= 0) & (g_ < 2048) & (h_ >= 0) & (h_ < 2048)
        fx.append(g_[ok]); fy.append(h_[ok]); fr.append(rng.random(int(ok.sum()))); ft.append(gtyp[ok])
    for pp in rail_lines:   # track sections (tabs\objects rail, 12 m) laid along the line, heading = atan2(dx, dy) as in the vanilla cells
        carry = 0.0
        for (ax, ay), (bx, by) in zip(pp, pp[1:]):
            L = math.hypot(bx - ax, by - ay)
            if L < 1e-6: continue
            ux, uy = (bx - ax) / L, (by - ay) / L; t = carry
            while t < L:
                cx, cy = ax + ux * t, ay + uy * t
                if 0 <= cx < 2048 and 0 <= cy < 2048: objs.append(('tabs\\objects.cfgpack', 'rail', float(cx), float(cy), float(math.atan2(ux, uy))))
                t += 12.0
            carry = t - L
    yy, xx = np.nonzero((cov == FIELD) & ~MO.dilate(np.isin(cov, (ROAD, TRACK, RAIL, WATER, MARSH, BUILDING, VILLAGE)), 17))   # haystacks 8 m clear of roads, tracks, rails and water
    for k in rng.integers(0, max(1, len(yy)), int(len(yy) / 40000)):
        objs.append(('tabs\\objects.cfgpack', ['seno_stog', 'seno_copna', 'seno_cyl'][int(rng.integers(0, 3))], float(xx[k]), float(yy[k]), float(rng.random() * 6.28)))
    if works_obj.any():   # nothing stands on the works: plants and small objects 4 m clear, buildings / fences / barns 12 m
        def _clear(x, y, big):
            xi, yi = int(min(2047, max(0, x))), int(min(2047, max(0, y)))
            return not (works_bld if big else works_obj)[yi, xi]
        n0 = len(objs)
        objs = [o for o in objs if _clear(o[2], o[3], 'build' in o[0] or 'fence' in o[0] or 'posts' in o[0] or 'struct' in o[0])]
        if fx:
            X = np.concatenate(fx); Y = np.concatenate(fy); R = np.concatenate(fr); Tt = np.concatenate(ft)
            ok = ~works_obj[np.clip(Y.astype(int), 0, 2047), np.clip(X.astype(int), 0, 2047)]
            fx, fy, fr, ft = [X[ok]], [Y[ok]], [R[ok]], [Tt[ok]]
        print('  works clearance: %d objects dropped' % (n0 - len(objs)), flush=True)
    if fx:
        C.write_flora(path('flora_quads'), np.concatenate(fx), np.concatenate(fy), np.concatenate(fr), np.concatenate(ft))
    else:
        C.write_flora(path('flora_quads'), np.zeros(0), np.zeros(0), np.zeros(0), np.zeros(0, int))
    C.write_objects(path('obj_quads'), objs); lap('objects')
    # ambient-occlusion / shadow map (<cell>_prokh_ao.aomap, outside the pack; tools/aomap.py): terrain, plants and
    # buildings ray-marched for the 24 light directions of the vanilla header - the trenches, the ditch, the balka sides
    # and the woods get their baked shadows (the build script copies cellsrc\<cell>\ao.aomap next to the pack)
    here_ = os.path.dirname(os.path.abspath(__file__))
    ao_hdr = next((p for p in (os.path.join(here_, '..', 'docs', 'm12_terrain', 'aomap_header.bin'), os.path.join(here_, 'docs', 'm12_terrain', 'aomap_header.bin')) if os.path.exists(p)), None)
    if ao_hdr:
        import aomap as AO
        fl_all = (np.concatenate(fx), np.concatenate(fy), np.concatenate(ft)) if fx else None
        AO.build(h2, fl_all, objs, os.path.join(od, 'ao.aomap'), ao_hdr)
        lap('aomap')
    C.write_trenches(path('trench_pos'), trench_recs); C.write_oppos(path('op_pos'))
    open(path('spr_map_side'), 'wb').write(b'\0\0\0\0'); open(path('ambients'), 'wb').write(b'\0\0\0\0')
    entries = ['cell_desc', 'hei_map', 'vars_map', 'mat_map', 'det_map', 'land_ambient_col', 'nor_map'] + (['water_map', 'water_pal', 'water_levels'] if has_water else []) + ['flora_quads', 'obj_quads',
               'trench_pos', 'op_pos', 'grass_map', 'opmap', 'back', 'opmap_tri', 'spr_map_side']
    if not no_ai:
        pm = pen.load_model(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'prokh_pen_model.json'))
        pnodes = pen.tree(soil, slope)
        for cls in ['tanks', 'hums', 'cars', 'apcs']:
            open(path('pen_' + cls), 'wb').write(pen.build(soil, slope, pm[cls], rng, nodes=pnodes)); entries.append('pen_' + cls)
        del pnodes
        shutil.copy(os.path.join(tpl, 'aiplaces.cell.loc_def.bin'), path('aiplaces')); entries.append('aiplaces')
        open(path('landchar'), 'wb').write(landchar_from_template(os.path.join(tpl, 'landchar.cell.loc_def.bin'), cls_grid)); entries.append('landchar')
    lap('ai')
    entries += ['ambients', 'class_map']
    with open(os.path.join(od, '!flatlist'), 'w') as f:
        f.write('i_unflat:unflat()\n{\n'); [f.write('\t%-30s, %-16s, %s ;\n' % (e, 'cell', 'loc_def')) for e in entries]; f.write('}\n')
    return dict(cell=name, buildings=len(buildings), flora=int(sum(len(a) for a in fx)), objs=len(objs), lines=len(lines))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--osm', required=True); ap.add_argument('--cells', required=True); ap.add_argument('--template', required=True)
    ap.add_argument('--out', required=True); ap.add_argument('--only', default=''); ap.add_argument('--no-ai', action='store_true')
    ap.add_argument('--style', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'prokh_style.json'))
    ap.add_argument('--budget', type=float, default=1e9)
    ap.add_argument('--works', action='store_true', help='(default) carve the trenches painted by the user and the anti-tank ditches of the layout')
    ap.add_argument('--no-works', action='store_true', help='leave the field works out (bare terrain)')
    ap.add_argument('--period', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'docs', 'm12_terrain', 'period', 'builtup_1941.png'))
    ap.add_argument('--layout', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'docs', 'm11_prokhorovka', 'layout_10jul.json'))
    ap.add_argument('--ref', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'build', 'prokhorovka', 'ref'),
                    help='directory with the unpacked reference cells (pgd5, pge4, pgf6 of the Petropolye DLC terrain, see gen_prokh.cmd)')
    a = ap.parse_args()
    global WORKS, REF, FARMS, FIELDS43, VILLAGES43, WOODS43, ROADS43, PONDS, SINGLE_TRACK
    if os.path.exists(a.layout):
        lay_ = json.load(open(a.layout, encoding='utf-8'))
        FARMS = [[tuple(q) for q in f['pts']] for f in lay_.get('farms', [])]
        FIELDS43 = [dict(f, pts=[tuple(q) for q in f['pts']]) for f in lay_.get('fields_1943', [])]
        VILLAGES43 = [[tuple(q) for q in v['pts']] for v in lay_.get('villages_1943', [])]
        WOODS43 = [dict(v, pts=[tuple(q) for q in v['pts']]) for v in lay_.get('woods_1943', [])]
        ROADS43 = [dict(r, pts=[tuple(q) for q in r['pts']]) for r in lay_.get('roads_1943', [])]
        PONDS = bool(lay_.get('ponds_1943', True))
        SINGLE_TRACK = bool(lay_.get('single_track', False))
    refs = [os.path.join(a.ref, d) for d in ('pgd5', 'pge4', 'pgf6', 'pgf2', 'pgg1') if os.path.exists(os.path.join(a.ref, d, 'mat_map.cell.loc_def.bin'))]
    if not refs: sys.exit('no reference cells under %s - gen_prokh.cmd unpacks pgd5/pge4/pgf6 of the Petropolye terrain (Stalingrad-Donets DLC) there' % a.ref)
    REF = TR.Ref(refs, mius_dir=a.template)
    if os.path.exists(a.layout):
        if not a.no_works:
            import works as W; WORKS = W.load(a.layout); print('field works loaded:', len(WORKS), 'trench / ditch pieces')
        else: WORKS = []
    style = json.load(open(a.style)); t0 = time.time()
    global PERIOD
    if os.path.exists(a.period):
        PERIOD = np.asarray(Image.open(a.period).convert('L')); print('period built-up mask loaded:', PERIOD.shape, 'fraction %.3f' % (PERIOD > 0).mean())
    os.makedirs(a.out, exist_ok=True); log = open(os.path.join(a.out, 'gen_prokh_log.txt'), 'a')
    class Tee:
        def write(self, s): sys.__stdout__.write(s); log.write(s)
        def flush(self): sys.__stdout__.flush(); log.flush()
    sys.stdout = Tee(); print('# prokh_gen', time.strftime('%Y-%m-%d %H:%M:%S'), sys.argv[1:])
    feats, places = load_osm(a.osm); print('osm features', len(feats), 'places', len(places), flush=True)
    feats = drop_modern(feats, a.layout)
    feats = meander_water(feats)
    places = places_1943(places, a.layout)
    build_water_levels(feats, a.cells)
    syms = ['0123456789!"#$%^&*()_+|\t=-~`[]{}:;"\'<>,.?/ \u2116ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz']
    eng = [('spec_syms_freq', syms), ('pe_poly_name', ['Prokhorovka']), ('pe_poly_country', ['USSR KURSK REG.'])]
    rus = [('spec_syms_freq', syms), ('pe_poly_name', ['\u041f\u0440\u043e\u0445\u043e\u0440\u043e\u0432\u043a\u0430']), ('pe_poly_country', ['\u0421\u0421\u0421\u0420 \u041a\u0423\u0420\u0421\u041a\u0410\u042f \u041e\u0411\u041b.'])]
    for (_, t, key) in places:
        eng.append((key, [t.get('name_en') or textpack.translit(t['name'])])); rus.append((key, [t['name']]))
    textpack.write(os.path.join(a.out, 'Prokh_text.loc_eng.textpack'), 'loc_eng', eng)
    textpack.write(os.path.join(a.out, 'Prokh_text.loc_rus.textpack'), 'loc_rus', rus)
    print('text packs:', len(eng), 'keys')
    only = set(a.only.split(',')) if a.only else None
    for j in range(ROWS):
        for i in range(COLS):
            name = cell_name(i, j)
            if only and name not in only: continue
            if os.path.exists(os.path.join(a.out, name, '!flatlist')): continue
            if time.time() - t0 > a.budget: print('budget reached'); return
            r = gen_cell(i, j, feats, places, a.cells, a.template, a.out, style, a.no_ai)
            print(r, '%.0fs' % (time.time() - t0), flush=True)
    print('done')

if __name__ == '__main__':
    main()

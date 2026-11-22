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
import atf1, cellfmt as C, pen, textpack, bldfoot as BF
import texsynth as TX, texref as TR, morph as MO
VLIB = [None]   # vstamps.Library, set by main()
REF = None      # texref.Ref: the Petropolye / Mius reference cells, set by main() from --ref

# ------------------------------------------------------------------ block geometry (docs/m12_terrain/prokh_layout.md)
# The DEM lattice ("old frame", 11 x 12 cells, metres from its west / south edge) stays the coordinate system of the
# OSM data, the layout files, the period mask and the heightmap files in build\prokhorovka\cells.  The polygon built
# from it was the 7 x 5 core block (2026-10-24: old columns 2..8, rows 4..8, the vanilla Mius geometry - cells table
# 11 x 7, cells at cell_x 3..9 / cell_y 1..5, camp_area 3;1;9;5).  2026-11-01 (user): enlarge it to 9 x 9 - old columns
# 0..8 (x 0..18432) and old rows 2..10 (y 2048..20480) = two cells west (Kozlovka / the Psel bend / Bogoroditskoye),
# north (Polezhayev / Veselyi / the Kartashevka road) and south (Belenikhino / Yasnaya Polyana / Leski); cells table
# 11 x 11 with an empty ring as the vanilla Kalach table (9 x 10 for 7 x 8 cells, camp_area 1;1;7;8), cells at cell_x
# 1..9 / cell_y 1..9, camp_area 1;1;9;9.  Larger than any vanilla map (Kalach 7 x 8 = 14 x 16 squares); 8 x 8 loads
# (test 1 Nov, placeholder cells); the first 9 x 9 and 8 x 8 crashes were a stale camp_area in the reused descriptor.
# The op-map squares authored for the 7 x 5 frame (ai_orders.py, briefing.py, layout 'pin') are shifted by SQ_DX / SQ_DY.
LATS, LATN, LONW, LONE = 50.904605, 51.1254, 36.4903, 36.8120   # DEM lattice (2026-10-23: two more rows south)
OLD_COLS, OLD_ROWS, CELL = 11, 12, 2048.0
OLD_LETTERS = [chr(ord('D') + i) for i in range(OLD_COLS)]
COLS, ROWS = 9, 9
BLOCK_I0, BLOCK_J0 = 0, 2                                   # old lattice indices of the block's north-west cell
SQ_DX, SQ_DY = 2 * (2 - BLOCK_I0), 2 * (4 - BLOCK_J0)       # op-map squares: 7 x 5-frame coordinates + these = this block's
CELL_X0, CELL_Y0 = 1, 1                                     # cells table coordinates of the block's north-west cell (camp_area origin)
BLOCK_X0 = BLOCK_I0 * CELL                                  # old-frame metres of the block's west edge
BLOCK_Y0 = (OLD_ROWS - BLOCK_J0 - ROWS) * CELL              # old-frame metres of the block's south edge
LAT_C = 51.0334; M_LAT = 111320.0; M_LON = 111320.0 * math.cos(math.radians(LAT_C))
LETTERS = [chr(ord('D') + i) for i in range(COLS)]
MAXH = 320.0
# polygon identity (Prokh unless a block config is given)
POLY = 'Prokh'
POLY_NAME = ('Prokhorovka', 'Прохоровка')
POLY_COUNTRY = ('USSR KURSK REG.', 'СССР КУРСКАЯ ОБЛ.')
BLOCK = None    # the block config (dict) when MFO_BLOCK is set
# 14 Nov 2026 (user: "the village names are suppost to be in polish instead of russian"): block 'names': 'pl' = Polish place
# names in BOTH text packs. The packs are single-byte and the game's bitmap fonts have 256 glyphs (loc_rus fonts cp1251,
# loc_eng fonts Latin-1 except the cp1251 typer_* fonts): no font has l-stroke / ogonek / acute letters, so the name is
# folded to ASCII (textpack.pl_ascii). The text keys stay derived from the Cyrillic form as before, so the map_point labels
# already baked into the cells keep resolving and the cells need no rebuild. 'names_rus': 'cyr' keeps the Russian pack in
# Cyrillic (textpack.pl_rus); Prokh (no block config) is unchanged.
PL_NAMES = False; PL_RUS_LATIN = False; PL_RENAME = {}; PL_DROP = set()
PL_ABBR = {'фл.': 'folw.', 'мельн.': 'mlyn', 'г. дв.': 'dwor', 'пильн.': 'tartak', 'Гмин. упр.': 'Urz. gm.', 'лесн.': 'lesn.',
           'раз.': 'przyst.', 'Б.': 'bud.', 'каз.': 'dr.', 'кирп.': 'ceg.',
           # 19 Nov (Radz build: these sheet words reached the text packs in Cyrillic and stopped the cell texts)
           'оз.': 'jez.', 'сар.': 'szopa', 'кол.': 'stud.', 'ст.': 'st.', 'шк.': 'szk.', 'ц.': 'kosc.', 'кл.': 'cm.', 'мог.': 'cm.',
           'пр.': 'staw', 'бол.': 'bagno', 'дер.': 'wies', 'хут.': 'kol.', 'ветр.': 'wiatr.', 'кладб.': 'cm.', 'церк.': 'cerk.'}   # sheet abbreviations -> WIG / Polish map words
# 10 Nov 2026 (M16 Okuniew): another polygon is built by the same generator from a block config - MFO_BLOCK=<path of a
# block.json> (docs/m16_okuniew/block.json): its lat / lon box is the lattice itself (no outer DEM lattice, to_block is
# the identity, the op-map squares are not shifted), its name, and the default inputs (OSM, period sheets, layout, style)
if os.environ.get('MFO_BLOCK'):
    BLOCK = json.load(open(os.environ['MFO_BLOCK'], encoding='utf-8'))
    LATS, LATN, LONW, LONE = BLOCK['latS'], BLOCK['latN'], BLOCK['lonW'], BLOCK['lonE']
    COLS, ROWS, CELL = int(BLOCK['cols']), int(BLOCK['rows']), float(BLOCK['cell'])
    OLD_COLS, OLD_ROWS = COLS, ROWS
    OLD_LETTERS = [chr(ord('D') + i) for i in range(OLD_COLS)]
    LETTERS = [chr(ord('D') + i) for i in range(COLS)]
    BLOCK_I0 = BLOCK_J0 = 0; SQ_DX = SQ_DY = 0
    BLOCK_X0 = 0.0; BLOCK_Y0 = 0.0
    LAT_C = float(BLOCK['lat_c']); M_LON = 111320.0 * math.cos(math.radians(LAT_C))
    MAXH = float(BLOCK.get('maxh', MAXH))
    POLY = BLOCK['name']
    POLY_NAME = tuple(BLOCK.get('poly_name', [POLY, POLY]))
    POLY_COUNTRY = tuple(BLOCK.get('poly_country', ['', '']))
    PL_NAMES = BLOCK.get('names') == 'pl'
    PL_RUS_LATIN = PL_NAMES and BLOCK.get('names_rus', 'latin') == 'latin'
    if PL_RUS_LATIN: POLY_NAME = (POLY_NAME[0], POLY_NAME[0])
    _n44 = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', BLOCK.get('period_dir', ''), BLOCK.get('names_1944', 'names_1944.json'))
    if PL_NAMES and os.path.exists(_n44):   # OSM name -> 1944 name, and OSM places that are not on the 1941 sheets
        _j44 = json.load(open(_n44, encoding='utf-8')); PL_RENAME = _j44.get('rename', {}); PL_DROP = set(_j44.get('drop', []))
    # 11 Nov (M16, user: "for each operation the size of the operational map should be changed with its objectives"):
    # MFO_AREA=i0;j0;i1;j1 (the operation's camp_area: cells 1-based from the north-west) makes the op tools (prokh_op,
    # briefing) work on that window of the block: block metres and op squares are counted from the window's west / south
    # (north) edge, the heightmaps are still the block's.  Not for the cell generator.
    if os.environ.get('MFO_AREA'):
        _i0, _j0, _i1, _j1 = [int(v) for v in os.environ['MFO_AREA'].split(';')]
        BLOCK_X0 = (_i0 - 1) * CELL; BLOCK_Y0 = (ROWS - _j1) * CELL
        BLOCK_I0, BLOCK_J0 = _i0 - 1, _j0 - 1
        SQ_DX, SQ_DY = -2 * (_i0 - 1), -2 * (_j0 - 1)   # okun_ai squares are block squares -> window squares
        CELL_X0, CELL_Y0 = _i0, _j0
        COLS, ROWS = _i1 - _i0 + 1, _j1 - _j0 + 1
        LETTERS = [chr(ord('D') + _i0 - 1 + i) for i in range(COLS)]

def repo_path(p):
    """a block-config path (relative to the repository root)"""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', p)

def pl_text(pl, rus=None):
    """(loc_eng, loc_rus) text of a Polish place name: ASCII-folded Polish in both packs (PL_RUS_LATIN), or the Cyrillic
    form in the Russian pack ('names_rus': 'cyr')"""
    en = textpack.pl_ascii(pl)
    return en, (en if PL_RUS_LATIN else (rus or textpack.pl_rus(pl)))

def period_places():
    """the block's sheet labels (period_names, e.g. names_1941.json) as (xy block metres, tags, text key), or None.
    The key stays the transliteration of the sheet's Cyrillic label (the cells' map_point sprites carry it); the text is the
    entry's hand-checked Polish 1944 name 'pl' when the block has 'names': 'pl'."""
    if not (BLOCK and BLOCK.get('period_names')): return None
    nj_ = repo_path(os.path.join(BLOCK['period_dir'], BLOCK['period_names']))
    if not os.path.exists(nj_): return None
    seen_ = set(); out = []
    for q in json.load(open(nj_, encoding='utf-8'))['names']:
        lat_ = textpack.translit(q['rus'])
        key = 'pe_mm_' + ''.join(ch for ch in lat_.lower() if ch.isalnum() and ord(ch) < 128)[:24]; k2 = key; n_ = 2
        while k2 in seen_: k2 = key[:22] + str(n_); n_ += 1
        seen_.add(k2)
        en_, ru_ = pl_text(q['pl'], q['rus']) if (PL_NAMES and q.get('pl')) else (lat_, q['rus'])
        out.append(((float(q['x']), float(q['y'])), {'name': q['rus'], 'name_en': en_, 'name_ru': ru_, 'place': q.get('place', 'village')}, k2))
    return out

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
            osm_ = t['name']
            if PL_NAMES:   # Polish OSM names: the key from the Cyrillic form as before, the text the (1944) Polish name in ASCII
                en_, ru_ = pl_text(PL_RENAME.get(osm_, osm_))
                t = dict(t, name=textpack.pl_rus(osm_), name_en=en_, name_ru=ru_)
            key = 'pe_mm_' + ''.join(ch for ch in textpack.translit(t['name']).lower() if ch.isalnum() and ord(ch) < 128)[:24]
            k2 = key; n = 2
            while k2 in seen: k2 = key[:22] + str(n); n += 1
            seen.add(k2)                      # a dropped place still takes its key, so the later duplicates keep theirs
            if PL_NAMES and (osm_ in PL_DROP or "%s|%s" % (osm_, t.get("place", "")) in PL_DROP): continue   # "name" or "name|place"
            places.append((project(x, y), t, k2))
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
        key = 'pe_mm_' + ''.join(ch for ch in name_lat.lower() if ch.isalnum() and ord(ch) < 128)[:24]; k2 = key; n = 2
        while k2 in seen: k2 = key[:22] + str(n); n += 1
        seen.add(k2); return k2
    for p in lay.get('places', []):
        x, y = p['xy']; rus = p.get('rus') or p['name']; lat = p['name']
        out.append(((float(x), float(y)), {'name': rus, 'name_en': lat, 'name_ru': lat if PL_RUS_LATIN else rus, 'place': 'village'}, key_of(lat)))
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

def road_class(t):
    """14 Nov: how a road looks on the ground, by how the sheet draws it - 'paved' (the bold double line / the RKKA main road: a hard
    metalled carriageway with earth shoulders), 'road' (the solid-line dirt roads: two wheel tracks, a verge), 'field' (the dashed
    double line: a narrow cart track; inside a wood it becomes a forest ride) and 'path' (the single dashed line: a footpath)."""
    # 14 Nov (user: "there are 9 road types"): the nine road signs of the WIG legend of 1931 (Komunikacje, B. Drogi):
    #   18 szosa wyborowa (over 9 m)   19 szosa I klasy (5.5 - 9 m)   20 szosa II klasy (3.5 - 5.5 m)      - drogi bite, metalled
    #   21 trakt / droga wzmocniona (over 5 m, partly cobbled)   22 droga wiejska IIIa (from 3 m)
    #   23 droga gospodarcza IIIb (from 2 m)   24 drozyna IIIc (field track)                               - drogi gruntowe
    #   25 droga zimowa (over the marsh, in frost only)   26 sciezka (path)
    # A road carries its sign number as 'wig_no' once it has been read off the WIG sheet (period/roads_1941.json). Until then
    # the number is taken from what the trace does know: how the WIG line was drawn (wig_kind) or the RKKA sheet's class.
    wn = t.get('wig_no')
    if wn: return 'w%d' % int(wn)
    wk = t.get('wig_kind'); hw = t.get('highway'); rk = str(t.get('source', '')).startswith('rkka1941')
    if wk: return {'wig_double_solid_bold': 'w19', 'wig_double_solid': 'w21', 'wig_solid_dashed': 'w22', 'wig_single_solid': 'w23',
                   'wig_double_dashed': 'w24', 'wig_single_dashed': 'w26'}.get(wk, 'w24')
    if hw in ('motorway', 'trunk', 'primary', 'secondary', 'tertiary'): return 'w21'   # the RKKA sheet's main roads: at least a tract; which of them are metalled is on the WIG sheet
    if hw in ('unclassified', 'residential', 'service', 'living_street', 'road'): return 'w22'
    if hw == 'track': return 'w22' if rk else 'w24'
    if hw == 'path' and rk: return 'w24'
    return 'w26'

def line_style(t):
    """(cover, width m, opmap colour or None, dashed) for linear features."""
    if 'railway' in t and t['railway'] in ('rail', 'narrow_gauge', 'disused', 'abandoned'):
        if t.get('service') in ('spur', 'crossover') or t.get('usage') in ('industrial',): return None   # modern yards and sidings
        return (RAIL, 6.0, 0xff1d0a04, False)
    hw = t.get('highway')
    wk = t.get('wig_kind')
    if wk:   # 12 Nov (user: "these are different kind of roads" - "determine road types"): the WIG roads by how WIG draws them
        return {'wig_double_solid_bold': (ROAD, 5.0, C.COL_ROAD_DARK, False),   # paved / improved road (droga bita)
                'wig_double_solid': (TRACK, 4.0, C.COL_TRACK, False),           # good dirt road
                'wig_solid_dashed': (TRACK, 3.5, C.COL_TRACK, False),           # dirt road
                'wig_single_solid': (TRACK, 3.0, C.COL_TRACK, False),           # narrow dirt road
                'wig_double_dashed': (TRACK, 3.0, C.COL_TRACK, True),           # field / forest road (droga polna / lesna)
                'wig_single_dashed': (TRACK, 1.8, C.COL_TRACK, True)}.get(wk, (TRACK, 3.0, C.COL_TRACK, True))   # footpath (sciezka)
    if hw in ('motorway', 'trunk', 'primary', 'secondary', 'tertiary'): return (ROAD, 6.0, C.COL_ROAD, False)   # 1943: unpaved 'grade' roads; Petropolye main roads 4-6 m of road_back
    if hw in ('unclassified', 'residential', 'service', 'living_street', 'road'): return (ROAD, 5.0, C.COL_ROAD_DARK, False)
    if hw in ('track',) and str(t.get('source', '')).startswith('rkka1941'): return (TRACK, 3.5, C.COL_TRACK, False)   # 12 Nov (1:1): the sheet's country road (TM 147) is a solid line; only its field / forest tracks (148, 'path') are dashed
    if hw in ('track',): return (TRACK, 3.5, C.COL_TRACK, True)
    if hw == 'path' and str(t.get('source', '')).startswith('rkka1941'): return (TRACK, 2.5, C.COL_TRACK, True)   # the sheet's dashed field / forest tracks
    if hw in ('path', 'footway', 'bridleway', 'cycleway'): return (TRACK, 1.5, None, True)
    ww = t.get('waterway')
    if t.get('source') == 'rkka1941' and ww in ('river', 'stream'):   # 12 Nov (user: everything of the sheet 1:1): the sheet's streams carry water -
        return (WATER, 4.0 if ww == 'river' else 2.0, 0xff2a5a8a, False)   # 12 Nov (user: streams too wide): both are SINGLE blue lines on the sheet, i.e. under 5 m wide (TM 30-548) - the thick line 4 m, the thin one 2 m; the double-line rivers and ponds come as areas (water_1941.png)
    if ww in ('river',): return (WATER, 16.0, 0xff2a5a8a, False)
    if ww in ('stream', 'canal', 'drain', 'ditch'): return (MARSH, 5.0, 0xff2a5a8a, False)
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

def prune_roads(feats):
    """27 Oct (user: 'some roads lead to nowhere ... keep everything historically accurate'). OSM is today's network:
    farm tracks to modern silos, field-access stubs, footpaths and service lanes. The 1943 network is kept by dropping
      * paths / footways / cycleways / bridleways and service lanes outside the villages (none of them on the 1941 sheet),
      * every minor road or track with an end that leads nowhere: not within 25 m of another road, not inside a village,
        farm yard or 1943 village of the layout, not at the railway (crossing, station) or the river (ford), and not at
        the edge of the block - repeated until no such dead end is left, so chains of stubs go too.
    The graded roads (primary / secondary / tertiary) and the layout's roads_1943 are never dropped."""
    MINOR = ('track', 'unclassified', 'residential', 'service', 'living_street', 'road')
    DROP = ('path', 'footway', 'cycleway', 'bridleway', 'steps', 'pedestrian')
    places = [MplPath(p) for (k, t, p, c) in feats if k == 'area' and area_cover(t) == VILLAGE]
    places += [MplPath(p) for p in FARMS] + [MplPath(p) for p in VILLAGES43]
    anchors = []   # railway and river points
    for (k, t, p, c) in feats:
        if k == 'line' and (('railway' in t and line_style(t) is not None) or t.get('waterway') in ('river', 'stream')):
            anchors += [tuple(q) for q in p]
    from scipy.spatial import cKDTree
    TA = cKDTree(np.array(anchors)) if anchors else None
    bx0, by0, bx1, by1 = BLOCK_X0 + 60, BLOCK_Y0 + 60, BLOCK_X0 + COLS * CELL - 60, BLOCK_Y0 + ROWS * CELL - 60
    def in_place(q): return any(pl.contains_points([q])[0] for pl in places)
    def dense(p, step=10.0):
        out = []
        for (ax, ay), (bx, by) in zip(p, p[1:]):
            n = max(1, int(math.hypot(bx - ax, by - ay) / step))
            out += [(ax + (bx - ax) * k / n, ay + (by - ay) * k / n) for k in range(n)]
        return out + [tuple(p[-1])]
    roads = []; other = []; n_drop = 0
    for f in feats:
        k, t, p, c = f
        hw = t.get('highway') if k == 'line' else None
        if hw in DROP: n_drop += 1; continue
        if hw == 'service' and not in_place(p[len(p) // 2]): n_drop += 1; continue
        if hw is not None: roads.append(f)
        else: other.append(f)
    # combs of parallel field tracks 50-100 m apart (post-war orchard / allotment rows, e.g. W of Ivanovsky Vyselok):
    # a track under 800 m with two or more others of the same direction and length within 250 m goes, with them
    tr = [(n, f) for n, f in enumerate(roads) if f[1].get('highway') == 'track']
    info = {}
    for n, (k, t, p, c) in tr:
        L = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(p, p[1:]))
        if L > 800: continue
        ang = math.atan2(p[-1][1] - p[0][1], p[-1][0] - p[0][0]) % math.pi
        info[n] = (ang, ((p[0][0] + p[-1][0]) / 2, (p[0][1] + p[-1][1]) / 2), L)
    comb = set()
    for n, (a, m, L) in info.items():
        mates = [q for q, (a2, m2, L2) in info.items() if q != n and min(abs(a - a2), math.pi - abs(a - a2)) < math.radians(10)
                 and math.hypot(m[0] - m2[0], m[1] - m2[1]) < 250 and 0.6 < L / L2 < 1.6]
        if len(mates) >= 2: comb.add(n); comb.update(mates)
    roads = [f for n, f in enumerate(roads) if n not in comb]
    fixed = [dense(r['pts']) for r in ROADS43]
    changed = True; n_dead = 0
    while changed:
        changed = False
        pts, own = [], []
        for n, (k, t, p, c) in enumerate(roads):
            d = dense(p); pts += d; own += [n] * len(d)
        for d in fixed: pts += d; own += [-1] * len(d)
        if not pts: break
        T = cKDTree(np.array(pts)); own = np.array(own)
        keep = []
        for n, f in enumerate(roads):
            k, t, p, c = f
            if t.get('highway') not in MINOR: keep.append(f); continue
            dead = False
            for q in (p[0], p[-1]):
                if not (bx0 < q[0] < bx1 and by0 < q[1] < by1): continue
                if any(own[j] != n for j in T.query_ball_point(q, 25.0)): continue
                if TA is not None and TA.query(q)[0] < 40.0: continue
                if in_place(q): continue
                dead = True; break
            if dead: n_dead += 1; changed = True
            else: keep.append(f)
        roads = keep
    print('roads 1943: %d paths / service lanes, %d parallel comb tracks and %d dead-end tracks dropped, %d roads kept' % (n_drop, len(comb), n_dead, len(roads)), flush=True)
    return other + roads

ROADS1941 = None   # the road network traced from the RKKA 1:100 000 sheet of 1941 (docs/m12_terrain/period/roads_1941.json,
                   # tools/roads_1941.py): list of {'highway', 'pts' (DEM-lattice metres), 'source', 'length_m'}. Set by main().

def period_settlement(feats):
    """11 Nov (M16, user: "trace everything from historic maps as accurately as possible"): buildings and farmyards of the
    1930s instead of OpenStreetMap's. Block config 'period_houses' (houses_wig.json from tools/wig_trace.py: every building
    of the WIG 1:25 000 sheets as a rotated rectangle, block metres) and 'period_yards' (farmyards_wig.png, the hatched
    zagroda plots, 4 m mask, row 0 = north). Every OSM building and every modern built-up landuse (residential, industrial,
    commercial, retail, garages, allotments) is dropped; the traced buildings come in as footprints (OSM_BUILDINGS on, so
    they stand as houses / sheds where drawn) and the yards as farmyard areas (village cover around them). Where the WIG
    mosaic has no coverage the RKKA house symbols (houses_1941.json) are used."""
    global OSM_BUILDINGS
    if not (BLOCK and BLOCK.get('period_houses')): return feats
    pd_ = repo_path(BLOCK['period_dir'])
    MOD = ('residential', 'industrial', 'commercial', 'retail', 'garages', 'allotments', 'construction', 'brownfield')
    out = [f for f in feats if f[0] != 'building' and not (f[0] == 'area' and f[1].get('landuse') in MOD)]
    nb_osm = sum(1 for f in feats if f[0] == 'building'); na_osm = sum(1 for f in feats if f[0] == 'area' and f[1].get('landuse') in MOD)
    H = json.load(open(os.path.join(pd_, BLOCK['period_houses']), encoding='utf-8'))['houses']
    import trace_edits as TE_
    E_ = TE_.load(pd_); n_px = int(ROWS * CELL / 2.0); H = TE_.apply_houses(H, E_, n_px)
    extra = BLOCK.get('period_houses_fill')   # houses outside the WIG coverage
    if extra and os.path.exists(os.path.join(pd_, extra)):
        wig = np.asarray(Image.open(os.path.join(pd_, 'wig_block.png')).convert('L').reduce(4)) < 250
        n_ = wig.shape[0]
        for h in json.load(open(os.path.join(pd_, extra), encoding='utf-8'))['houses']:
            r_, c_ = int((ROWS * CELL - h['y']) / 8.0), int(h['x'] / 8.0)
            if 0 <= r_ < n_ and 0 <= c_ < n_ and not wig[r_, c_]: H.append(dict(h, src='rkka'))
    for h in H:
        w, d = max(h['w'], 5.0), max(h['d'], 4.0); a_ = math.radians(h['ang'])
        ca, sa = math.cos(a_), math.sin(a_)
        pts = []
        for ex, ey in ((-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)):
            pts.append((h['x'] + ex * ca - ey * sa, h['y'] - (ex * sa + ey * ca)))   # image angle (y down) -> block metres (y up)
        out.append(('building', {'building': 'house', 'source': h['kind'] if str(h.get('kind', '')).startswith('wig_') and h.get('src') != 'rkka' else h.get('src', 'wig25'),
                                 'role': h.get('role')}, pts + [pts[0]], True))   # 19 Nov: 'wig_bld' stands one to one (settle.wig_pick); 21 Nov: role house / aux of the WIG_operations layer
    ny = 0
    if BLOCK.get('period_yards') and os.path.exists(os.path.join(pd_, BLOCK['period_yards'])):
        import cv2
        Y = TE_.apply_yards(np.asarray(Image.open(os.path.join(pd_, BLOCK['period_yards'])).convert('L')), E_, n_px).astype(np.uint8)
        px_ = (ROWS * CELL) / Y.shape[0]
        cs, _ = cv2.findContours(Y, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in cs:
            if cv2.contourArea(c) < 6: continue
            pts = [(float(q[0][0]) * px_, ROWS * CELL - float(q[0][1]) * px_) for q in c]
            out.append(('area', {'landuse': 'farmyard', 'source': 'wig25'}, pts + [pts[0]], True)); ny += 1
    OSM_BUILDINGS = True
    print('settlement (%s): ' % BLOCK['period_houses'] + '%d OSM buildings and %d modern built-up areas dropped, %d traced buildings and %d farmyards inserted' % (nb_osm, na_osm, len(H), ny), flush=True)
    return out

def period_cover(feats):
    """11 Nov (M16, user: "everything has to be 1 to 1 from the rkka map"): water, streams, marsh, meadow and orchards of the
    RKKA 1:50 000 sheets (tools/rkka_cover.py) instead of OpenStreetMap's; OSM water, waterways, wetlands, meadows,
    orchards, power lines, fences and embankments are dropped (the 1941 sheet has none of the modern ones)."""
    if not (BLOCK and BLOCK.get('period_cover')): return feats
    pd_ = repo_path(BLOCK['period_dir'])
    import cv2
    def drop(f):
        k, t, p, c = f
        if 'waterway' in t or 'power' in t or t.get('barrier') or t.get('man_made') == 'embankment': return True
        if k == 'area' and (t.get('natural') in ('water', 'wetland') or t.get('water') or t.get('landuse') in ('reservoir', 'basin', 'meadow', 'grass', 'orchard', 'vineyard', 'farmland', 'farm')): return True
        return False
    out = [f for f in feats if not drop(f)]; nd = len(feats) - len(out)
    # railways: kept only where the 1941 sheet draws them (black line work within 10 m along >= 60 % of the line)
    from scipy import ndimage as ndi
    rk = np.asarray(Image.open(os.path.join(pd_, 'rkka_block2.png')).convert('L').reduce(2)) < 140   # 4 m
    rk = ndi.binary_dilation(rk, iterations=3); nr = rk.shape[0]; keep = []; nrd = 0
    for f in out:
        k, t, p, c = f
        if k == 'line' and 'railway' in t:
            P = np.array(p, float); L = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
            if L[-1] > 0:
                tt = np.arange(0, L[-1], 8.0); Q = np.c_[np.interp(tt, L, P[:, 0]), np.interp(tt, L, P[:, 1])]
                ix = (Q[:, 0] / 4.0).astype(int); iy = ((ROWS * CELL - Q[:, 1]) / 4.0).astype(int)
                ok = (ix >= 0) & (ix < nr) & (iy >= 0) & (iy < nr)
                if ok.mean() > 0.3 and rk[iy[ok], ix[ok]].mean() < 0.6: nrd += 1; continue
        keep.append(f)
    out = keep; nd += nrd
    S = json.load(open(os.path.join(pd_, 'streams_1941.json'), encoding='utf-8'))['streams']
    for s_ in S:
        t_ = {'waterway': s_['waterway'], 'source': 'rkka1941'}
        if s_.get('isolated'): t_['isolated'] = True
        if s_.get('w_m'): t_['w_m'] = float(s_['w_m'])      # 14 Nov: the width read off the sheet's line weight (tools/streams_fix.py)
        if s_.get('wide'): t_['wide'] = True               # ... and the ribbon rivers (two bank lines: 5 - 15 m on the ground)
        out.append(('line', t_, [tuple(q) for q in s_['pts']], False))
    na = 0
    for name, tags in (('field_1941.png', {'landuse': 'farmland'}), ('marsh_1941.png', {'natural': 'wetland'}),
                       ('water_1941.png', {'natural': 'water', 'water': 'river'})):   # water / marsh are drawn above field by class order; meadow: COVER41 raster   # the field parcels (plough pattern); meadow, marsh, water: COVER41 raster in rasterise
        fp = os.path.join(pd_, name)
        if not os.path.exists(fp): continue
        M = (np.asarray(Image.open(fp).convert('L')) > 0).astype(np.uint8); px_ = (ROWS * CELL) / M.shape[0]
        cs, _ = cv2.findContours(M, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in cs:
            if cv2.contourArea(c) < 4: continue
            pts = [(float(q[0][0]) * px_, ROWS * CELL - float(q[0][1]) * px_) for q in c]
            out.append(('area', dict(tags, source='rkka1941'), pts + [pts[0]], True)); na += 1
    # the ploughed land is the RKKA field areas too (field_1941.png, one parcel per area of tools/rkka_regions.py)
    print('cover 1941 (RKKA): %d OSM water / meadow / orchard / fence / power features dropped, %d streams and %d areas inserted' % (nd, len(S), na), flush=True)
    return out

def period_roads(feats):
    """4 Nov (user: "Just match all the roads from the 1941 map don't take into account the modern"): the roads, cart
    tracks, field paths and village streets come from the 1941 sheet itself, not from OpenStreetMap. Every OSM highway is
    dropped (rivers, streams, woods, railway and the rest of OSM stay); the traced network (tools/roads_1941.py ->
    docs/m12_terrain/period/roads_1941.json) is inserted as OSM-style lines tagged by symbol - 'secondary' (double line:
    improved / main road), 'track' (single solid line: dirt road), 'path' (dashed: field / forest track), 'residential'
    (village street) - so line_style, tools/tracks.py, tools/settle.py and the op map treat them as before. The layout's
    roads_1943 (hand-added lanes) are separate and always drawn."""
    if ROADS1941 is None:
        print('roads 1941: no traced network (docs/m12_terrain/period/roads_1941.json) - the OSM roads are kept', flush=True)
        return feats
    out = []; n_drop = 0; L_drop = 0.0
    for f in feats:
        k, t, p, c = f
        if k == 'line' and 'highway' in t:
            n_drop += 1; L_drop += sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(p, p[1:])); continue
        out.append(f)
    n = {}
    for r in ROADS1941:
        pts = [tuple(q) for q in r['pts']]
        if len(pts) < 2: continue
        if r.get('dup_of') is not None: continue   # traced twice (tools/roads_dups.py): the other trace of this road is drawn
        out.append(('line', {'highway': r['highway'], 'source': 'rkka1941_' + r.get('source', 'sheet'), 'wig_kind': r.get('wig_kind'), 'wig_no': r.get('wig_no')}, pts, False))
        n[r['highway']] = n.get(r['highway'], 0) + 1
    print('roads 1941 (RKKA sheet): %d OSM highways dropped (%.0f km), %s traced roads inserted' % (n_drop, L_drop / 1000.0, ', '.join('%d %s' % (v, k) for k, v in sorted(n.items()))), flush=True)
    return out

# ------------------------------------------------------------------ natural river courses
# 26 Oct (user: 'the curvature is rigid and unnatural'): the OSM Psel here has a vertex every 110-160 m, so the river was
# a chain of straight 14 m bands with sharp corners. Every river / stream line is smoothed (Chaikin) and given meanders -
# three incommensurate waves of lateral offset with a slowly varying amplitude (tight bends and calm reaches), phases
# hashed from the way's first point, tapered to zero at both ends so consecutive OSM ways still join - and the river
# band gets a width that varies along its length. Done once on the features, so the water levels and every cell agree.
MEANDER = {'river': (20.0, (420.0, 210.0, 120.0), 16.0, 5.0), 'stream': (4.0, (130.0, 70.0, 37.0), 5.0, 1.2),
           'canal': (0.0, (1.0, 1.0, 1.0), 5.0, 0.0), 'drain': (1.5, (90.0, 50.0, 27.0), 4.0, 0.8), 'ditch': (1.5, (90.0, 50.0, 27.0), 4.0, 0.8)}
RIPARIAN = [None]   # set per cell: (belt mask, distance to the water m, noise, mud band, wet meadow) for the bank flora
FLOOD = [None]      # set per cell: the low floodplain next to the river (wet meadow)
MUD = [None]        # set per cell: the bare mud band at the waterline (no grass billboards)

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

def join_stream_gaps(feats, reach=60.0):
    """14 Nov (user: waterways "should look real"): the sheet's blue line is broken where a label, a contour number or a road
    casing lies over it, and the trace kept the break - a stream that stops in a field and starts again 40 m on. Two loose ends
    (no other water line within 4 m) that lie within `reach` of each other and point at each other are joined by a short piece."""
    from scipy.spatial import cKDTree
    L = [(k, f) for k, f in enumerate(feats) if f[0] == 'line' and f[1].get('source') == 'rkka1941' and f[1].get('waterway') in ('river', 'stream') and len(f[2]) >= 2]
    if not L: return feats
    V = []; vid = []
    for k, f in L:
        for q in f[2]: V.append((q[0], q[1])); vid.append(k)
    V = np.asarray(V, np.float64); vid = np.asarray(vid); tv = cKDTree(V)
    ends = []   # (x, y, outward dx, dy, feature index)
    for k, f in L:
        pts = f[2]
        for a_, b_ in ((pts[0], pts[1]), (pts[-1], pts[-2])):
            near = tv.query_ball_point((a_[0], a_[1]), 4.0)
            if any(vid[j] != k for j in near): continue
            d = math.hypot(a_[0] - b_[0], a_[1] - b_[1])
            if d < 1e-6: continue
            ends.append((a_[0], a_[1], (a_[0] - b_[0]) / d, (a_[1] - b_[1]) / d, k))
    if len(ends) < 2: return feats
    E = np.asarray([(e[0], e[1]) for e in ends]); te = cKDTree(E); used = set(); add = []
    for i, e in enumerate(ends):
        if i in used: continue
        best = None
        for j in te.query_ball_point((e[0], e[1]), reach):
            if j == i or j in used or ends[j][4] == e[4]: continue
            o = ends[j]; dx, dy = o[0] - e[0], o[1] - e[1]; d = math.hypot(dx, dy)
            if d < 1.0: continue
            if (dx * e[2] + dy * e[3]) / d < 0.6 or (-dx * o[2] - dy * o[3]) / d < 0.6: continue   # both ends must point along the gap
            if best is None or d < best[0]: best = (d, j)
        if best is not None:
            o = ends[best[1]]; used.add(i); used.add(best[1])
            t = dict(feats[e[4]][1]); add.append(('line', t, [(e[0], e[1]), (o[0], o[1])], False))
    print('stream gaps joined: %d (of %d loose ends)' % (len(add), len(ends)), flush=True)
    return list(feats) + add

def meander_water(feats):
    feats = join_stream_gaps(feats)
    out = []; n = 0
    for (kind, t, p, closed) in feats:
        ww = t.get('waterway') if kind == 'line' else None
        if ww in MEANDER:
            amp, lams, w0, dw = MEANDER[ww]
            if t.get('source') == 'rkka1941':   # 12 Nov (1:1): the traced line IS the sheet's course - no invented meanders; widths as on the sheet
                # 14 Nov (user: "the rivers are not uniform, they are tiny and dont go in straight line"): the 1:50 000 trace is a chain of
                # straight pieces of one width. Inside the thickness of the sheet's line (0.1 mm = 5 m) the course wobbles a few metres
                # and the width changes along it: streams 1.2 - 3 m, the thick-line rivers 3 - 5.5 m.
                amp, lams = (4.0, (60.0, 31.0, 17.0)) if ww == 'river' else (1.8, (24.0, 13.0, 7.0))
                w0, dw = (4.2, 1.3) if ww == 'river' else (2.1, 0.9)
                if t.get('w_m'):   # 14 Nov: the sheet thickens a stream from source to mouth - the width follows the line weight, piece by piece
                    w0 = float(t['w_m']); dw = max(0.5, 0.3 * w0)
                    amp, lams = ((2.5, (90.0, 47.0, 23.0)) if t.get('wide') else ((4.0, (60.0, 31.0, 17.0)) if w0 >= 3.8 else ((2.8, (40.0, 21.0, 11.0)) if w0 >= 2.6 else (1.8, (24.0, 13.0, 7.0)))))
            q = _meander(p, amp, lams)
            if ww == 'river' or t.get('source') == 'rkka1941':   # half-width along the line: w0/2 +- dw/2, a ~400 m wave plus a ~120 m one
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

OSM_BUILDINGS = False   # layout 'osm_buildings': True puts the OSM building footprints back as houses / sheds (the old way)
OSM_BUILDINGS_IN = []   # layout 'osm_buildings_1943': polygons (DEM-lattice metres) inside which the OSM footprints are kept
def osm_building_ok(p):
    """4 Nov (user: big villages had houses on a grid with sheds round them and no fences, 'take a look at the Korotich
    layouts'): the OSM footprints are today's houses and outbuildings - every one became a house or a shed with a pale yard,
    and the street homesteads (fences, gates, yards, plots) were kept 20 m away from them, so the villages with many
    footprints (Belenikhino 1100, Prokhorovka 900) had no homesteads at all. By default they are dropped and every village
    is built from the street homesteads like the Psel villages (and like vanilla Korotich: a fenced plot per house along
    every street); the layout can keep them inside given polygons."""
    if OSM_BUILDINGS: return True
    if not OSM_BUILDINGS_IN: return False
    cx = sum(q[0] for q in p) / len(p); cy = sum(q[1] for q in p) / len(p)
    return any(pl.contains_points([(cx, cy)])[0] for pl in OSM_BUILDINGS_IN)

def period_mask_cell(i, j, margin=0, raster=None):
    """1 m boolean mask of the 1941 built-up area inside cell (i, j) (+ margin px on every side), row 0 = south; None without a period mask.
    raster: another 4 m period raster of the lattice (WOODS_P) instead of the built-up mask."""
    R = PERIOD if raster is None else raster
    if R is None: return None
    x0, y0 = cell_origin(i, j); H, W = R.shape
    xs = np.clip(((x0 + np.arange(-margin, 2048 + margin) + 0.5) / 4).astype(int), 0, W - 1)
    ys = np.clip(((OLD_ROWS * CELL - (y0 + np.arange(-margin, 2048 + margin) + 0.5)) / 4).astype(int), 0, H - 1)   # the mask covers the DEM lattice
    return R[ys][:, xs] > 0

COVER41 = [None]; COVER41_ON = [False]
DUNE = [None]       # per cell: (dune area, bare sand, distance inside) for the dune flora
WPOOLS = [False]    # 14 Nov: the summer water model (tools/waterpools.py: the water follows the ground, pools, dry beds) - on for a block whose cover comes from the period sheet
WATPAD = [None]     # per cell, set by rasterise: (water mask, dry-bed mask) drawn with a margin of PADW metres round the cell
PADW = 64
WFEATS = []         # the water features of the block (pool lines, dry-bed lines, water areas), set once in main
WRES = [None]       # per cell: the result of waterpools.cell (final water, dry beds, fords, distances) for the bank and plant code
WDEPTH = [None]     # per cell: the water depth in metres at 1 m (0 = no water) - for the passability trees
RIVMASK = [None]    # per cell, set by rasterise: the rivers the passability trees mark as water (3.8 m and wider, the ribbons), 1 m
RIVER_PEN_W = 3.8
DRYBED = [None]     # per cell: the dry stream beds, for their plants
SAND41 = [None]     # 13 Nov (user: 'plenty of sandy terrain'): the WIG sand stipple (no. 160), period/sand_wig.png (2 m, tools/wig_sand.py)
YOUNG41 = [None]    # 13 Nov (user: 'work on young growth'): WIG 152 young pine / 153 bushes / mixed areas read by eye, period/young_wig.png + young_wig_density.png (signs per ha)
MARSHWOOD41 = [None]  # 13 Nov: swamp with trees (TM 349 / 382, WIG 162): the RKKA marsh dashes inside a wood, period/marsh_dash.png
WETMEADOW41 = [None]  # 13 Nov: swampy meadow (TM 384: marsh dashes with meadow signs), period/wetmeadow_1941.png
RAILGRADE = [None]   # 14 Nov: block config 'rail_grade' (dict of tools/railgrade.py parameters): the railway on an even grade
EARTH41 = [None]     # 13 Nov: dikes, dams, road / railway fills, cuts and dune ridges traced off the RKKA sheet, period/earthworks_1941.json (block metres)
PARCELS = [None]   # 12 Nov: field parcels of the period maps (period/field_parcels.npz, 2 m labels)
PARCEL_TYPES = [1, 1, 1, 1, 1, 2, 2, 2, 4]   # ripe / cut grain 5, green crop (potatoes, beet) 3, ploughed 1 - per parcel
BUSHES41 = [None]   # 12 Nov: the sheet's single-tree signs, period/bushes_1941.json (block metres)
TREES41 = [None]    # 13 Nov: lone tree circles of the RKKA sheet outside the woods, period/trees_1941.json (tools/rkka_trees.py)
LANDMARKS41 = [None]   # 12 Nov (1:1 symbols): the sheet's point symbols, period/landmarks_1941.json (block metres)
RELIEF41 = [None]; SPOTS41 = [None]   # 12 Nov (1:1): the sheet's contour lines (block metres) and spot heights for the op map
TREE_ROWS = [None]  # block config 'tree_rows' (period/tree_rows.json): polylines (block metres) of the trees along the roads
WOODKIND = [None]   # block config 'wood_kind' (period/wood_kind.png, 2 m): 1 pine, 2 broadleaf, 3 mixed, 0 the block's default mix
def woodkind_cell(i, j):
    R = WOODKIND[0]; x0, y0 = cell_origin(i, j); H, W = R.shape
    xs = np.clip(((x0 + np.arange(2048) + 0.5) / 2).astype(int), 0, W - 1)
    ys = np.clip(((OLD_ROWS * CELL - (y0 + np.arange(2048) + 0.5)) / 2).astype(int), 0, H - 1)
    return R[ys][:, xs]
OPMAP_SHEET = [None]   # block config 'opmap_sheet' (11 Nov, user: "check it all 1 to 1"): the op map background is the RKKA sheet itself (rkka_block2.png at 4 m)
def cell41(R, i, j):
    """a 2 m block raster (row 0 = north) sampled onto cell (i, j)'s 1 m grid"""
    x0, y0 = cell_origin(i, j); H, W = R.shape
    xs = np.clip(((x0 + np.arange(2048) + 0.5) / 2).astype(int), 0, W - 1)
    ys = np.clip(((OLD_ROWS * CELL - (y0 + np.arange(2048) + 0.5)) / 2).astype(int), 0, H - 1)
    return R[ys][:, xs]
def cover41_cell(i, j):
    R = COVER41[0]; x0, y0 = cell_origin(i, j); H, W = R.shape
    xs = np.clip(((x0 + np.arange(2048) + 0.5) / 2).astype(int), 0, W - 1)
    ys = np.clip(((OLD_ROWS * CELL - (y0 + np.arange(2048) + 0.5)) / 2).astype(int), 0, H - 1)
    return R[ys][:, xs]
WOODS_P = None          # block config 'period_woods': 4 m wood mask read off the 1941 sheets (tools/period_sheets.py), row 0 = north
PERIOD_VILLAGES = False # block config 'period_villages': the 1941 built-up patches become village cover where OSM has houses within 150 m

# 14 Nov (user: "during deployment mode the infantry is inside each other but after start they are ok ... [vehicles] can
# be placed on houses in deployment mode"): landchar is not lighting - it is the deployment layer, one 48-byte record per
# 32 m square (row = y // 32 from the south edge; decoded on Petropolye PgD5 / PgE4, Mius MgG3 / MxD1 and in the code that
# reads it, adv_game 0x120cae and basic_game 0xa1ef1 / 0xa4420):
#   bytes 0-27  the square's 28 deployment places: place k stands at the square's south-west corner + (x, y) * 4 m with
#               x | y << 3 = the byte's low six bits (x east, y north, 0..7), bit 7 = the place can be used, bit 6 = the
#               first place (the middle of the square, 0xe4). A squad's first man is put on place 0, the others on places
#               s, s + 1 ... from a random s in 3..27 (adv_game 0x1207a0). Vanilla: 27-28 distinct points in every square.
#               Bit 7 of places 1-27 is one flag for the whole square (never mixed in a vanilla cell): clear in every square
#               that holds a piece of a building zone; place 0 also has it clear where the middle itself is blocked
#   bytes 28-39 three words of eight 3-bit fields: how open the square is in the eight compass directions (0 shut .. 7 open;
#               vanilla open ground ~4 / 3 / 3, a square with 32+ plants 0, a house square ~1), read by the cell search
#               of the deployment and by the F-key overlay. Not decoded per direction: every field of a word gets the
#               vanilla median for the square's plant count (12 cells), so a wood reads shut and a field open - the
#               template's byte-by-byte median had scrambled the bit fields into one lop-sided value for every square
#   bytes 40-43 zero
#   byte 44     vegetation density (vanilla median code by the square's plant count, 12 cells / 49k squares)
#   byte 45     bits 0-5 the number of places (28), bit 6 open for infantry, bit 7 open for a squad with a vehicle: vanilla
#               closes the squares full of houses (zone share median 0.36) and the wet ones to vehicles, deep water to all
#   byte 46     1 plain open ground | 2 a road runs through the square | 4 a building zone lies in it
# Ours was one record for every square of every cell - the template's 90th percentile byte by byte, bytes 1-27 then
# "shaded" as if they were lighting: the 28 places fell on 4 sub-cells (a squad's men stood in each other until the battle
# moved them), every square was open to vehicles (781 places inside houses in MxD6), every wood read as bare ground.
LANDCHAR_BINS = ((0, 0x00), (1, 0x01), (4, 0x04), (8, 0x18), (12, 0x2f), (16, 0x3f), (24, 0x5f), (32, 0x7f), (48, 0x8f), (64, 0x9f), (96, 0xff))
LANDCHAR_TREES = (0, 1, 2, 3, 4, 5, 8, 9, 10, 11, 12, 14, 19, 20, 21)   # flora rows with a trunk (trees, big bushes, the water and dry trees): no place within 1.5 m
LANDCHAR_OPEN = ((0, (4, 3, 3)), (1, (3, 3, 2)), (4, (3, 2, 2)), (8, (2, 2, 1)), (16, (1, 1, 1)), (24, (0, 0, 0)))   # plants in the square -> openness of the three words

def landchar_from_template(tpl_path, cls, plants=None, objs=(), water1=None, zone1=None, road1=None, seed=0):
    """the cell's landchar entry (the deployment layer, see above) from its own plants (x, y, type arrays), object records,
    and 1 m masks of the water, the building zones (the pen maps' bld_kind > 0) and the roadways; `cls` is not used any
    more (the old wood shading); `seed` makes the places repeatable."""
    u8 = np.frombuffer(open(tpl_path, 'rb').read(), np.uint8).reshape(-1, 48)
    out = np.tile(np.median(u8, axis=0).astype(np.uint8), (64, 64, 1))
    def share(m): return m.reshape(64, 32, 64, 32).mean((1, 3)) if m is not None else np.zeros((64, 64))
    zs, ws, rs = share(zone1), share(water1), share(road1)
    zl = zone1.reshape(512, 4, 512, 4).mean((1, 3)) >= pen.ZONE_FRAC if zone1 is not None else np.zeros((512, 512), bool)   # the pen maps' 4 m zone leaves
    zq = zl.reshape(64, 8, 64, 8).any((1, 3))                            # squares holding a zone leaf
    n = np.zeros((64, 64), int); solid = np.zeros((2048, 2048), bool)   # 1 m pixels holding a trunk or an object
    if plants is not None and len(plants[0]):
        X_, Y_ = np.clip(np.asarray(plants[0]).astype(int), 0, 2047), np.clip(np.asarray(plants[1]).astype(int), 0, 2047)
        np.add.at(n, (Y_ // 32, X_ // 32), 1)
        tr_ = np.isin(np.asarray(plants[2]).astype(int) & 0xff, LANDCHAR_TREES); solid[Y_[tr_], X_[tr_]] = True
    cen = np.zeros((64, 64), int)
    for o in objs:
        if BF.is_building(o[0]):
            mx_, my_ = BF.centre(o[2], o[3], o[4], o[1]); cen[int(min(2047, max(0, my_))) // 32, int(min(2047, max(0, mx_))) // 32] += 1
        else: solid[int(min(2047, max(0, o[3]))), int(min(2047, max(0, o[2])))] = True   # a fence piece, a well, a haystack ...
    # the points no place may stand on (blk[r * 8 + y, c * 8 + x] = the point x, y of square r, c): within 2 m of a building
    # zone (the box + 5 m: about 7-8 m from the walls, as vanilla), in the water, within 1.5 m of a trunk or an object
    bad = MO.dilate(solid, 3)
    if zone1 is not None: bad |= MO.dilate(zone1, 5)
    if water1 is not None: bad |= water1
    blk = bad[0::4, 0::4] | zl                                          # nor on the corner of a zone leaf
    # the 28 places: the middle of the square first, then 27 other points in random order, the free ones first; not the
    # three points next to the middle on its south-west side, the south and west rows at half weight (vanilla use: 3-23 %
    # and 22-34 % against 45-55 % elsewhere). The flag bit is the square's (vanilla), so a point that is not free is
    # only chosen when the square has fewer than 27 free ones
    sq_off = zq                                                          # a leaf of a building zone in the square (vanilla: 324 of 324 such squares)
    rng_ = np.random.default_rng(seed)
    cand = np.array([(x, y) for y in range(8) for x in range(8) if (x, y) not in ((4, 4), (3, 3), (3, 4), (4, 3))])
    wgt = np.where((cand[:, 0] == 0) | (cand[:, 1] == 0), 0.5, 1.0)
    for r in range(64):
        for c in range(64):
            b = blk[r * 8:r * 8 + 8, c * 8:c * 8 + 8]
            key = rng_.random(len(cand)) ** (1.0 / wgt)                 # weighted random order
            free = ~b[cand[:, 1], cand[:, 0]]
            pick = np.argsort(-(key + free))[:27]                        # free sub-cells before blocked ones
            pick = pick[rng_.permutation(27)]
            out[r, c, 0] = 4 | 4 << 3 | 0x40 | (0 if (b[4, 4] or sq_off[r, c]) else 0x80)
            out[r, c, 1:28] = cand[pick, 0] | cand[pick, 1] << 3 | (0 if sq_off[r, c] else 0x80)
    code = np.zeros((64, 64), np.uint8)
    for lo, v in LANDCHAR_BINS: code[n >= lo] = v
    veh = ~((zs >= 0.25) | (cen >= 2) | (ws >= 0.10))                    # open for a squad with a vehicle
    b45 = np.where(veh, 0xdc, 0x5c).astype(np.uint8); b45[ws >= 0.50] = 0
    op_ = np.zeros((64, 64, 3), np.int64)
    for lo, v in LANDCHAR_OPEN: op_[n >= lo] = v
    op_[zq] = np.minimum(op_[zq], 1)                                     # a square with a building zone
    out[..., 28:40] = (op_ * 0o11111111).astype('<u4').view(np.uint8).reshape(64, 64, 12); out[..., 40:44] = 0   # eight equal 3-bit fields a word
    out[..., 44] = code; out[..., 45] = b45
    out[..., 46] = np.where(~zq & veh, 1, 0) | np.where(rs >= 0.02, 2, 0) | np.where(zq, 4, 0); out[..., 47] = 0
    out[ws >= 0.50] = 0                                                  # deep water: the whole record is zero in vanilla
    return out.tobytes()

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
        # 14 Nov: the sheet's ponds are painted from the cover raster (class 5 = the pond mask at 2 m, below) - an outline polygon
        # fills the dikes and islands inside a pond
        if c == WATER and WPOOLS[0] and COVER41_ON[0] and t.get('source') == 'rkka1941': continue
        if c == WOOD and strip_width(p) < 45.0 and not near_rail(p, feats, 120.0): continue
        if c == WOOD and strip_width(p) < 70.0 and near_rail(p, feats, 120.0): rail_belts.append(p)   # drawn again over the 1943 villages / farms below   # modern field shelterbelts (post-1948) go; the railway snow-protection belts stay (user, 25 Oct: the tree line along the railway was missing - they were planted from the 1930s)
        areas.append((order[c], c, p, k))
    areas.sort(key=lambda a: a[0])
    field_polys = []
    for (_, c, p, k) in areas:
        if c == FIELD and not COVER41_ON[0] and (k * 2654435761) % 100 >= FIELD_KEEP_PCT: c = GRASS   # 1943: open steppe / fallow between the crop fields (period sheets show pasture, not the modern wall-to-wall arable)
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
            if t.get('waterway') == 'drybed':   # 14 Nov: a stream bed without water in August (tools/waterpools.py)
                if WPOOLS[0]: lines.append((to_px(p, x0, y0), 0xff2a5a8a, True, MARSH))
                continue
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
            if c in (ROAD, TRACK):
                import tracks as _TKc; _TKc.CLS[id(pp)] = road_class(t)
        elif kind == 'building' and closed and osm_building_ok(p):
            import settle as _SEf; pp = _SEf.Foot(to_px(p, x0, y0)); pp.src = t.get('source'); pp.role = t.get('role'); d.polygon(pp, fill=BUILDING); buildings.append(pp)
    # rivers and streams last, over the roads and tracks that cross them (26 Oct: a track drawn over the Psel left a
    # raised grass strip across the water - the bed is not carved under non-water pixels)
    for (pp, c, w, hw) in water_lines:
        if hw: d.polygon(_band(pp, hw), fill=c)
        else: d.line(pp, fill=c, width=max(1, int(round(w))), joint='curve')
    for (_, c, p, k) in areas:
        if c == WATER: d.polygon(to_px(p, x0, y0), fill=WATER)
    # 12 Nov (1:1 symbols, period/landmarks_1941.json): a bridge marked on the sheet - the road stays solid across the
    # stream for 14 m (the bed is not carved under non-water pixels): a dry crossing where the sheet has a bridge, a ford
    # everywhere else. The game's bridge model is not placed: its height over a carved bed could not be checked.
    for L_ in (LANDMARKS41[0] or []):
        if L_['type'] != 'bridge': continue
        bx_, by_ = L_['x'] + BLOCK_X0, L_['y'] + BLOCK_Y0
        if not (x0 - 20 <= bx_ < x0 + CELL + 20 and y0 - 20 <= by_ < y0 + CELL + 20): continue
        main_ = L_.get('road') in ('secondary', 'residential'); (qx_, qy_), = to_px([(bx_, by_)], x0, y0)
        # a 6 m disc, not a stretch along the road: on the check crops the traced road nearest a mark was sometimes the
        # wrong one of two, and the sheet's mark (a bar with forked ends ACROSS the road: the pipe / small bridge) sits on the road
        d.ellipse([qx_ - 6, qy_ - 6, qx_ + 6, qy_ + 6], fill=ROAD if main_ else TRACK)
    # 14 Nov (user: the roads collide with "Water or banks"): a stream drawn over a road cut it in two - a strip of water, mud and
    # reeds across the carriageway, the bed carved through it. Where a road CROSSES a stream line (not where it runs along one,
    # and not a pond or a double-line river) the road now stays whole across it: the crossing is a culvert, the ground left
    # uncarved for the road's own width, the stream going on either side. Footpaths and winter roads keep their ford.
    if water_lines:
        import tracks as _TKx
        wl_ = Image.new('L', (2048, 2048), 0); dwl_ = ImageDraw.Draw(wl_)
        for (pp, c, w, hw) in water_lines:
            if hw: dwl_.polygon(_band(pp, hw), fill=255)
            else: dwl_.line(pp, fill=255, width=max(1, int(round(w))), joint='curve')
        wl_ = np.asarray(wl_) > 0; ncross_ = 0
        if wl_.any():
            for (pp, col, dash, c) in lines:
                if c not in (ROAD, TRACK) or len(pp) < 2: continue
                look_ = _TKx.CLS.get(id(pp))
                if look_ in ('w26', 'w25', 'path'): continue
                rad_ = _TKx.LOOK.get(look_, ('', 2.0))[1] + 1.5
                P_ = np.asarray(pp, np.float64); sg_ = np.hypot(*np.diff(P_, axis=0).T); Lc_ = np.r_[0, np.cumsum(sg_)]
                if Lc_[-1] < 2: continue
                t_ = np.arange(0.0, Lc_[-1], 1.0); X_ = np.interp(t_, Lc_, P_[:, 0]); Y_ = np.interp(t_, Lc_, P_[:, 1])
                ins_ = (X_ >= 0) & (X_ < 2048) & (Y_ >= 0) & (Y_ < 2048)
                on_ = np.zeros(len(t_), bool); on_[ins_] = wl_[Y_[ins_].astype(int), X_[ins_].astype(int)]
                k_ = 0
                while k_ < len(on_):
                    if not on_[k_]: k_ += 1; continue
                    e_ = k_
                    while e_ + 1 < len(on_) and on_[e_ + 1]: e_ += 1
                    if e_ - k_ + 1 <= 14:   # a crossing: the road is over the water for no more than 14 m
                        m_ = (k_ + e_) // 2
                        d.line([(X_[max(0, k_ - 3)], Y_[max(0, k_ - 3)]), (X_[m_], Y_[m_]), (X_[min(len(t_) - 1, e_ + 3)], Y_[min(len(t_) - 1, e_ + 3)])], fill=c, width=int(round(2 * rad_)))
                        ncross_ += 1
                    k_ = e_ + 1
        if ncross_: print('  road / stream crossings kept whole: %d' % ncross_, flush=True)
    WATPAD[0] = None
    if WPOOLS[0]:   # 14 Nov: the water and the dry beds once more with a margin of PADW m, so that a cell shapes its banks by the
        # neighbour's water too (the carve used to see its own cell only: steps of up to 8 m along the cell borders)
        Np_ = 2048 + 2 * PADW
        wpi_ = Image.new('L', (Np_, Np_), 0); dwp_ = ImageDraw.Draw(wpi_); dpi_ = Image.new('L', (Np_, Np_), 0); ddp_ = ImageDraw.Draw(dpi_)
        for (kind_, t_, p_, closed_) in WFEATS:
            if not clip_poly(p_, x0, y0, margin=PADW + 30): continue
            pp_ = [(x_ + PADW, y_ + PADW) for x_, y_ in to_px(p_, x0, y0)]
            if kind_ == 'area':
                if len(pp_) >= 3 and not COVER41_ON[0]: dwp_.polygon(pp_, fill=255)
                continue
            dsel_ = ddp_ if t_.get('waterway') == 'drybed' else dwp_; hw_ = t_.get('_hw')
            if hw_: dsel_.polygon(_band(pp_, hw_), fill=255)
            else: dsel_.line(pp_, fill=255, width=2, joint='curve')
        wpa_ = np.asarray(wpi_) > 0
        if COVER41_ON[0]:   # the ponds of the margin from the pond mask too (class 5 of the cover raster, 2 m, row 0 = north)
            R41_ = COVER41[0]; xs_ = np.clip(((x0 - PADW + np.arange(Np_) + 0.5) / 2).astype(int), 0, R41_.shape[1] - 1)
            ys_ = np.clip(((OLD_ROWS * CELL - (y0 - PADW + np.arange(Np_) + 0.5)) / 2).astype(int), 0, R41_.shape[0] - 1)
            wpa_ = wpa_ | (R41_[ys_][:, xs_] == 5)
        WATPAD[0] = (wpa_, np.asarray(dpi_) > 0)
        rvi_ = Image.new('L', (2048, 2048), 0); drv_ = ImageDraw.Draw(rvi_)      # the rivers proper, for the passability trees
        for (kind_, t_, p_, closed_) in WFEATS:
            if kind_ != 'line' or t_.get('waterway') == 'drybed' or not (t_.get('wide') or float(t_.get('w_m') or 0.0) >= RIVER_PEN_W): continue
            if not clip_poly(p_, x0, y0, margin=30): continue
            pp_ = to_px(p_, x0, y0); hw_ = t_.get('_hw')
            if hw_: drv_.polygon(_band(pp_, [h_ + 1.0 for h_ in hw_]), fill=255)
            else: drv_.line(pp_, fill=255, width=6, joint='curve')
        RIVMASK[0] = np.asarray(rvi_) > 0
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
        if kind == 'building' and closed and clip_poly(p, x0, y0, margin=PAD + 50) and osm_building_ok(p): dvp.polygon([(x + PAD, y + PAD) for x, y in to_px(p, x0, y0)], fill=255)
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
            # 12 Nov 2026: the open farmland of a period block is ONE connected area of the sheet, kilometres across - its
            # crop must not hang on the hash of its outline (a marsh added elsewhere turned all of it from grain to green
            # crop). An area wider than 1.5 km is ripe grain / stubble, the August ground; smaller plots keep their own crop.
            if COVER41_ON[0] and (max(xs) - min(xs) > 1500 or max(ys) - min(ys) > 1500): typ[:] = 1
        sub = fid[by0:by1, bx0:bx1]; sub[m] = typ[m]
    # 12 Nov 2026 (user: "start strip fields"): the field parcels of the maps (period/field_parcels.npz, tools/field_parcels.py:
    # the farmland cut along every road, the WIG strip boundaries and the streams) - each parcel its own crop, so the land
    # reads as the strip patchwork of the WIG sheets. August 1944 east of Warsaw: rye and wheat cut or ripe (most), potatoes
    # and beet green, some ploughed stubble; no sunflowers (Mazovia).
    if PARCELS[0] is not None:
        Lp = PARCELS[0]; nP = Lp.shape[0]; bx_, by_ = to_block(x0, y0)
        ci = np.clip(((np.arange(2048) + bx_) / 2.0).astype(int), 0, nP - 1); ri = np.clip((nP - (np.arange(2048) + by_) / 2.0).astype(int), 0, nP - 1)
        lab = Lp[ri[:, None], ci[None, :]].astype(np.int64)
        mP = (lab > 0) & (np.asarray(cov) == FIELD) if not isinstance(cov, np.ndarray) else (lab > 0) & (cov == FIELD)
        if mP.any():
            ptypes = (BLOCK.get('parcel_types') if BLOCK else None) or PARCEL_TYPES   # 13 Nov: the mix of the operation's date (block config)
            pt = np.asarray(ptypes, np.uint8)[((lab * 2654435761) % 1000003) % len(ptypes)]
            fid[mP] = pt[mP]
            # 14 Nov (user: "make sure that all things blend it together nicely"): a parcel that lies among the houses (more than half of
            # it within 30 m of a building or the built-up cover) is a garden plot - potatoes, beet, vegetables - not a block of ripe
            # grain standing between the yards
            covA_ = np.asarray(cov); nearv_ = MO.dilate((covA_ == VILLAGE) | (covA_ == BUILDING), 61)
            if nearv_.any():
                lm_ = lab[mP]; tot_ = np.bincount(lm_); inv_ = np.bincount(lm_, weights=nearv_[mP].astype(np.float64), minlength=len(tot_))
                gard_ = (tot_ > 0) & (inv_ > 0.5 * np.maximum(tot_, 1))
                gsel_ = mP & gard_[np.clip(lab, 0, len(gard_) - 1)] & ((fid == 1) | (fid == 5))
                fid[gsel_] = 2
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
        if BLOCK and BLOCK.get('period_houses'):   # M16: every building is traced from the WIG sheets - its yard and village stay
            pmd = pmd | MO.dilate(cov == BUILDING, 41)
        cov[(cov == VILLAGE) & ~pmd] = GRASS
        cov[(cov == BUILDING) & ~pmd] = GRASS
        cov[np.asarray(farm43) > 0] = VILLAGE   # the 1943 state-farm yards are not subject to the trim
        cov[(np.asarray(vil43) > 0) & (cov == GRASS)] = VILLAGE   # nor the 1943 villages (they come from the period sheet itself)
        # 4 Nov: the OSM farmyard / industrial yards outside the 1941 built-up area are post-war livestock and machine
        # yards - their cover went back to grass above, but the farm mask still put barns, sheds and haystacks on them
        FARM_MASK[0] &= (pmd | (np.asarray(farm43) > 0))
        pmp = MO.dilate(period_mask_cell(i, j, PAD), 51); vpf = np.pad((np.asarray(farm43) > 0) | (np.asarray(vil43) > 0), PAD)
        VIL_PAD[0] &= (pmp | vpf)
        if PERIOD_VILLAGES:   # M16: villages of the 1941 sheet that OSM has no residential area for (only house footprints)
            near = MO.dilate(VIL_PAD[0][PAD:PAD + 2048, PAD:PAD + 2048] | (cov == BUILDING), 301)
            add = pm & near & np.isin(cov, (GRASS, FIELD))
            cov[add] = VILLAGE
            VIL_PAD[0] |= np.pad(add, PAD)
    if WOODS_P is not None:   # M16: the woods of the 1941 sheet replace the modern OSM woods (post-war plantings go, cut woods come back)
        wm = period_mask_cell(i, j, raster=WOODS_P)
        cov[(cov == WOOD) & ~MO.dilate(wm, 31)] = GRASS
        cov[wm & np.isin(cov, (GRASS, FIELD, SCRUB, ORCHARD))] = WOOD
        buildings = [pp for pp in buildings if 0 <= pp[0][0] < 2048 and 0 <= pp[0][1] < 2048 and pmd[int(pp[0][1]), int(pp[0][0])]]
    if COVER41_ON[0]:   # M16: the RKKA cover, pixel for pixel, last (tools/rkka_regions.py cover_1941.png, 2 m): every class
        cv41 = cover41_cell(i, j)
        keepc = np.isin(cov, (VILLAGE, BUILDING, ROAD, TRACK, RAIL, WATER))   # 12 Nov: the sheet's stream channels (WATER lines) are not painted over by the cover raster
        for c41, cg in ((0, FIELD), (1, WOOD), (2, GRASS), (3, MARSH), (4, ORCHARD), (5, WATER), (6, SCRUB)):
            cov[(cv41 == c41) & ~keepc] = cg
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
    if OPMAP_SHEET[0] is not None:   # the sheet carries its own 1941 contours, roads, railways and rivers
        return np.array(V, np.float64).reshape(-1, 2), np.array(Cc, np.uint32), np.array(I, np.uint32)
    RLF = (BLOCK or {}).get('opmap_relief')
    if RELIEF41[0] is not None and not RLF:   # the sheet's own contour lines, as drawn on it
        bx_, by_ = to_block(x0, y0)
        for line in RELIEF41[0]:
            P = [(px_ - bx_, py_ - by_) for px_, py_ in line]
            if all(not (-50 <= a_ <= 2098 and -50 <= b_ <= 2098) for a_, b_ in P): continue
            for a, b in zip(P, P[1:]): seg(a, b, C.COL_CONTOUR)
    else:   # 14 Nov (opmap_relief; user: "you added some small height map from the rkka maps which looks bad"): the traced sheet
        # lines are 13,575 brown fragments (median 28 m) not level with the game terrain - the cell's own contours instead,
        # every 5 m as vanilla (line_freq 0.2)
        hs = smooth(h8, 2)
        for (p, q) in contours(hs, 8.0, float((RLF or {}).get('contour', 5.0))): seg(p, q, C.COL_CONTOUR)
    for (pp, col, dash, cover) in lines:
        if col is None: continue
        for a, b in zip(pp, pp[1:]):
            if dash:
                L = math.hypot(b[0] - a[0], b[1] - a[1]); n = max(1, int(L / 30))
                for k in range(n):
                    t0 = k / n; t1 = (k + 0.6) / n
                    seg((a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0), (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1), col)
            elif cover == ROAD and col == C.COL_ROAD and RELIEF41[0] is not None:
                # 12 Nov (1:1): the sheet draws its main (improved) roads as a double line, the country roads single
                L = math.hypot(b[0] - a[0], b[1] - a[1])
                if L > 1e-6:
                    nx_, ny_ = -(b[1] - a[1]) / L * 9.0, (b[0] - a[0]) / L * 9.0
                    seg((a[0] + nx_, a[1] + ny_), (b[0] + nx_, b[1] + ny_), col); seg((a[0] - nx_, a[1] - ny_), (b[0] - nx_, b[1] - ny_), col)
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
    nlev = WL.build(feats, water_of, heights, BLOCK_X0, BLOCK_Y0, COLS * CELL, ROWS * CELL, CELL)
    print('water levels: one surface for the block,', nlev, 'levels in steps of %.2f m' % WL.STEP, flush=True)

def build_water_pools(feats, hei_dir):
    """14 Nov: the summer water of a block of small streams and ponds (tools/waterpools.py) - the water lines split into pools
    and dry beds on the block's ground at 4 m; the stations and levels stay in the module for the cells."""
    import waterpools as WP
    n = 512; dem = np.zeros((ROWS * n, COLS * n), np.float32)   # block ground at 4 m, row 0 = south
    for j in range(ROWS):
        for i in range(COLS):
            fp = hei_path(hei_dir, i, j)
            if fp is None: continue
            hu, _ = pha6_decode(fp); f = hu.shape[0] // n
            r0 = (ROWS - 1 - j) * n
            dem[r0:r0 + n, i * n:(i + 1) * n] = (hu * (MAXH / 65535.0)).reshape(n, f, n, f).mean((1, 3)); del hu
    def wline(t):
        if t.get('waterway') not in ('river', 'stream'): return False
        st = line_style(t); return st is not None and st[0] == WATER
    def warea(t):
        return area_cover(t) == WATER and (PONDS or t.get('water') in ('river', 'stream', 'canal', 'oxbow'))
    am_ = None
    if COVER41_ON[0]:   # 14 Nov: the water areas as the pond mask has them (dikes and islands are land), not as filled outlines
        c5_ = (COVER41[0] == 5); f_ = c5_.shape[0] // dem.shape[0]
        if f_ >= 1 and c5_.shape[0] == dem.shape[0] * f_: am_ = (c5_.reshape(dem.shape[0], f_, dem.shape[1], f_).mean((1, 3)) >= 0.5)[::-1].copy()
    out = WP.build(feats, wline, warea, dem, BLOCK_X0, BLOCK_Y0, CELL, params=(BLOCK or {}).get('water'), log=lambda s_: print(s_, flush=True), area_mask=am_)
    del WFEATS[:]
    for f_ in out:
        if (f_[0] == 'line' and (f_[1].get('waterway') == 'drybed' or wline(f_[1]))) or (f_[0] == 'area' and warea(f_[1])): WFEATS.append(f_)
    print('water model: pools (%d water features)' % len(WFEATS), flush=True)
    return out

def build_rail_grade(feats, hei_dir):
    """14 Nov: the railway's formation height for the whole block (tools/railgrade.py), from the block's ground at 4 m."""
    import railgrade as RG
    n = 512; dem = np.zeros((ROWS * n, COLS * n), np.float32)
    for j in range(ROWS):
        for i in range(COLS):
            fp = hei_path(hei_dir, i, j)
            if fp is None: continue
            hu, _ = pha6_decode(fp); f = hu.shape[0] // n; r0 = (ROWS - 1 - j) * n
            dem[r0:r0 + n, i * n:(i + 1) * n] = (hu * (MAXH / 65535.0)).reshape(n, f, n, f).mean((1, 3)); del hu
    rails = [p for (kind, t, p, closed) in feats if kind == 'line' and 'railway' in t and line_style(t) is not None and line_style(t)[0] == RAIL]
    pr_ = BLOCK.get('rail_grade') if isinstance(BLOCK.get('rail_grade'), dict) else None
    if RG.build(rails, dem, BLOCK_X0, BLOCK_Y0, CELL / n, params=pr_, log=lambda s_: print(s_, flush=True)): RAILGRADE[0] = True

def church_objs(kind, cx, cy, ang=0.0):
    """14 Nov (user: "the churches etc ... verify this if this is real or not"): the churches of the sheet by what stood there in
    1944 (period/churches_1941.json 'kind', checked place by place): 'brick_tower' the brick hall with its bell tower (the game's
    whole church: church_cap0 + 1 + 2 on one record; alone, church_cap0 is half a hall), 'brick' the hall without the tower,
    'wood' a timber church - the game has none: the big log house with a cross before it; 'chapel' a small timber chapel (the
    log barn and a cross). ang: the long side, counter-clockwise from east; the tower end looks west at 0."""
    T_BC, T_BW, T_O = 'tabs\\builds_cap.cfgpack', 'tabs\\builds_wood.cfgpack', 'tabs\\objects.cfgpack'
    ca, sa = math.cos(ang), math.sin(ang)
    if kind in ('brick_tower', 'brick'):
        nd = 'build_asm_church' if kind == 'brick_tower' else 'build_asm_hall'
        return [(T_BC, nd, cx, cy, BF.heading(nd, ang))]
    import settle as SE_
    if kind == 'wood' and SE_.HOUSE_STYLE[0] == 'mazovia':
        # 17 Nov (M19): the timber church of 1944 Mazovia (Dluga Koscielna: larch, c.1630, shingle roofs, board cladding) and its
        # separate bell tower, 9 m off the west end and 6 m to the side
        nd = 'mz_kosciol1'; r = BF.heading(nd, ang); out = [(T_BW, nd) + tuple(min(2047.0, max(0.0, v)) for v in BF.origin_for(cx, cy, r, nd)) + (r,)]
        bx, by = cx - ca * 17.0 - sa * 8.0, cy - sa * 17.0 + ca * 8.0
        if 0 <= bx < 2048 and 0 <= by < 2048: out.append((T_BW, 'mz_dzwonnica1', bx, by, BF.heading('mz_dzwonnica1', ang)))
        return out
    nd = 'izba1' if kind == 'wood' else 'barn1'; r = BF.heading(nd, ang); half = BF.half(nd, True)
    ox, oy = BF.origin_for(cx, cy, r, nd)
    out = [(T_BW, nd, min(2047.0, max(0.0, ox)), min(2047.0, max(0.0, oy)), r)]
    kx, ky = cx - ca * (half + 5.0), cy - sa * (half + 5.0)      # the cross before the west door
    if 0 <= kx < 2048 and 0 <= ky < 2048: out.append((T_O, 'cross_rec', kx, ky, 1.7))
    return out

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
    import tracks as _TKc; _TKc.CLS.clear()
    cov, fid, lines, buildings = rasterise(feats, i, j, rng, steep); lap('cover')
    cov = ragged_edges(cov, fid, to_block(x0, y0))
    soil = np.zeros_like(cov)
    for c, s in SOIL_OF.items(): soil[cov == c] = s
    soil[(cov == FIELD) & ((fid == 2) | (fid == 3))] = 7   # field_green
    soil[(cov == FIELD) & (fid == 4)] = 15                  # ploughed (the vanilla 'bump' soil is the furrowed field texture, see Petropolye PgD5)
    if SAND41[0] is not None:   # open sand (WIG no. 160): bare sand soil, no crop; a wood on sand stays a wood
        R_ = SAND41[0]; H_, W_ = R_.shape
        xs_ = np.clip(((x0 + np.arange(2048) + 0.5) / 2).astype(int), 0, W_ - 1)
        ys_ = np.clip(((OLD_ROWS * CELL - (y0 + np.arange(2048) + 0.5)) / 2).astype(int), 0, H_ - 1)
        sd_ = R_[ys_][:, xs_] & np.isin(cov, (GRASS, FIELD, SCRUB))
        cov[sd_ & (cov == FIELD)] = GRASS
        # 14 Nov (user: "the dune areas with flora they should look real"): the sand was one flat sheet with a ruled outline. Its edge
        # now breaks up over 2 - 9 m (grass reaching in, sand tongues reaching out), a fifth of the inside is grass islands, and the
        # ground rises in low hummocks (up to about a metre) the way blown sand lies; pines, junipers and broom stand on it in clumps
        from scipy import ndimage as ndi_s
        orgs_ = to_block(x0, y0)
        ds_ = ndi_s.distance_transform_edt(sd_)
        nse_ = TX.gnoise(sd_.shape, orgs_, 9.0, 121); nsi_ = TX.gnoise(sd_.shape, orgs_, 16.0, 122) + 0.5 * TX.gnoise(sd_.shape, orgs_, 4.0, 123)
        sand_ = sd_ & (ds_ > 2.0 + 3.5 * (1.0 + nse_)) & (nsi_ < 0.62)
        sand_ |= sd_ & (ds_ > 1.0) & (ds_ <= 9.0) & (nse_ < -0.55)
        soil[sd_] = 0; soil[sand_] = 5
        DUNE[0] = (sd_, sand_, ds_)
        # the same height on both sides of a cell border: the distance to the sand's edge is taken on the sheet's sand mask with a
        # 30 m margin round the cell as well, and the smaller of the two counts
        pd_ = 15
        xp_ = np.clip(((x0 + np.arange(-2 * pd_, 2048 + 2 * pd_) + 0.5) / 2).astype(int), 0, W_ - 1); yp_ = np.clip(((OLD_ROWS * CELL - (y0 + np.arange(-2 * pd_, 2048 + 2 * pd_) + 0.5)) / 2).astype(int), 0, H_ - 1)
        dg_ = ndi_s.distance_transform_edt(R_[yp_][:, xp_])[2 * pd_:-2 * pd_, 2 * pd_:-2 * pd_]
        dh_ = np.minimum(ds_, dg_)
        hum_ = np.clip(dh_ / 14.0, 0.0, 1.0) * (0.55 * (1.0 + TX.gnoise(sd_.shape, orgs_, 38.0, 124)) + 0.25 * TX.gnoise(sd_.shape, orgs_, 11.0, 125))
        h += np.repeat(np.repeat(np.clip(hum_, 0.0, 1.4).astype(h.dtype), 2, 0), 2, 1)
    wetm_ = None
    if WETMEADOW41[0] is not None:   # swampy meadow: grass with wet patches (about 40 % marsh soil), not a closed bog
        wetm_ = cell41(WETMEADOW41[0], i, j) & (cov == MARSH)
        soil[wetm_ & (TX.gnoise(soil.shape, to_block(x0, y0), 22.0, 71) > -0.25)] = 0
    if MARSHWOOD41[0] is not None:   # a wood the sheet hatches with marsh dashes is a swampy wood: wet ground under the trees
        soil[cell41(MARSHWOOD41[0], i, j) & (cov == WOOD)] = 1
    if YOUNG41[0] is not None:   # young growth / bushes stand on heath and pasture, not on a sown field
        cov[(cell41(YOUNG41[0][0], i, j) > 0) & (cov == FIELD)] = GRASS
    # tracks and streets the vanilla way (tools/tracks.py): pave strips with a second strip beside them, trampled village streets
    import tracks as TKS
    if TKS.LIB is not None:   # 27 Oct: real Petropolye road strips bent along the OSM lines (tools/tracks.py paint_strips)
        TKS.paint_strips(soil, cov, lines, to_block(x0, y0), dict(ROAD=ROAD, TRACK=TRACK, FIELD=FIELD, WATER=WATER, MARSH=MARSH, RAIL=RAIL, BUILDING=BUILDING, VILLAGE=VILLAGE, WOOD=WOOD), vil_mask=MO.dilate((cov == VILLAGE) | (cov == BUILDING), 61))
        if TKS.LOWER is not None: h -= np.repeat(np.repeat(TKS.LOWER, 2, 0), 2, 1)   # the wheel tracks lie 10-15 cm below the verge
    else:
        TKS.paint(soil, cov, lines, to_block(x0, y0), dict(ROAD=ROAD, TRACK=TRACK, FIELD=FIELD, WATER=WATER, MARSH=MARSH, RAIL=RAIL, BUILDING=BUILDING, VILLAGE=VILLAGE), vil_mask=MO.dilate(cov == VILLAGE, 21))
    # texture classes for tools/texref.py (copied with their soil pattern from the Petropolye cells); 0 = keep the soil
    tcls = np.zeros_like(cov)
    tcls[(cov == FIELD) & ((fid == 1) | (fid == 5))] = TR.CROP; tcls[(cov == FIELD) & (fid == 4)] = TR.PLOUGH   # 5 = cut grain (stubble): the crop ground, short grass, stooks
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
        if RAILGRADE[0] is None:   # (with the block's rail grade the formation is laid after the water, below)
            e = smooth(np.asarray(emb).astype(np.float32) / 255.0, 4)   # ~9 m crest, ~5 m shoulders
            h += np.repeat(np.repeat(e, 2, 0), 2, 1) * 1.5
        else: e = None
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
    # ponds under 0.25 ha are dropped (the 30 m DEM does not resolve their hollows) - but not a river reach that only clips
    # the cell: without it the neighbour's water stopped in a wall at the seam
    has_water = wm.sum() > 2500 or (wm.sum() > 0 and (wm[0].any() or wm[-1].any() or wm[:, 0].any() or wm[:, -1].any()))
    idx = vals = None; FLOOD[0] = None
    wrecs = None; WRES[0] = None; WDEPTH[0] = None; DRYBED[0] = None
    if WPOOLS[0]:
        # 14 Nov (user: "check the water and how it behaves in game, remember its summer so the water is evaporating and the rivers
        # might be shallow, the exeption are the ponds"): tools/waterpools.py. The water lies on the ground it runs through (banks a
        # median half a metre above it; the old surface lay up to 24 m under the ground and the bed was cut down to it), a stream is
        # a chain of level pools with a ford where the level changes, half of the thin-line stream is a dry bed, the depths are what
        # the engine makes of them (stream 0.40 m: free for men and every vehicle; pond 2.0 m: closed to everything).
        import waterpools as WP
        has_water = False
        Np_ = 2048 + 2 * PADW
        wet_pad, dry_pad = WATPAD[0] if WATPAD[0] is not None else (np.zeros((Np_, Np_), bool), np.zeros((Np_, Np_), bool))
        wet_pad = wet_pad.copy(); wet_pad[PADW:-PADW, PADW:-PADW] = wm      # inside the cell: the water as the cover has it (roads kept whole across it)
        if (BLOCK or {}).get('smooth_shores', True) and wet_pad.any():   # 14 Nov (user: reservoirs 'not in squares'): the pond shores rounded off
            wet_pad = WP.smooth_shores(wet_pad); core_ = wet_pad[PADW:-PADW, PADW:-PADW]
            core_ &= ~(np.isin(cov, (ROAD, TRACK, RAIL, BUILDING, VILLAGE)) & ~wm)      # (a view: the padded mask is cut too)
            cov[wm & ~core_] = GRASS; cov[core_ & ~wm] = WATER; wm = core_.copy()
        if wet_pad.any() or dry_pad.any():
            h2w = h.reshape(2048, 2, 2048, 2).mean((1, 3)).astype(np.float32)
            bslope_ = (0.42 + 0.22 * TX.gnoise(wm.shape, to_block(x0, y0), 140.0, 57) + 0.06 * TX.gnoise(wm.shape, to_block(x0, y0), 31.0, 58)).astype(np.float32)
            res_ = WP.cell(wet_pad, dry_pad, np.isin(cov, (ROAD, TRACK, RAIL, BUILDING)), h2w, x0, y0, PADW, bslope_, params=(BLOCK or {}).get('water'))
            from scipy import ndimage as ndi_z   # 14 Nov (audit): bilinear, not a 2 x 2 repeat - the repeat made a 1 m kerb at every waterline
            h += ndi_z.zoom((res_['h'] - h2w).astype(np.float32), 2, order=1, mode='nearest')[:h.shape[0], :h.shape[1]].astype(h.dtype)
            cov[wm & ~res_['wet']] = GRASS      # the fords between two pools (and water of the sheet that has no level): ground
            WRES[0] = res_
            # 14 Nov (user: ponds "still look off"): the grain stood to the water's edge. A pond lies in a strip of meadow (6 - 22 m, uneven),
            # a stream in one of 2 - 6 m - the banks nobody ploughs
            nzs_ = TX.gnoise(wm.shape, to_block(x0, y0), 45.0, 133)
            cov[((res_['d_wide'] <= 14.0 + 8.0 * nzs_) | (res_['d_out'] <= 4.0 + 2.0 * nzs_)) & (cov == FIELD)] = GRASS; del nzs_
            if res_['idx'] is not None: has_water = True; idx = res_['idx']; vals = res_['vals']; wrecs = res_['recs']
            WDEPTH[0] = np.where(res_['wet'], np.nan_to_num(res_['lvl']) - res_['h'], 0.0).astype(np.float32)
            print('  water: %.2f ha in pools (%d levels, %d patches), fords %.2f ha, dry beds %.2f ha; ground lowered by more than 1 m on %.2f ha (most %.1f m)'
                  % (res_['wet'].sum() / 1e4, 0 if vals is None else len(vals), 0 if wrecs is None else len(wrecs), res_['dam'].sum() / 1e4, res_['dry'].sum() / 1e4,
                     ((h2w - res_['h']) > 1.0).sum() / 1e4, float((h2w - res_['h']).max())), flush=True)
            del h2w, bslope_
        else: cov[wm] = GRASS
        del wet_pad, dry_pad
    if has_water and not WPOOLS[0]:
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
        # 14 Nov (user: the rivers "are passable practically in all places exept for water reservoirs"): a water body at least 24 m
        # across somewhere is a pond / reservoir and keeps a deep bed (to 2.2 m); every stream and river reach is a ford, its bed
        # never more than 0.6 m under the surface.
        lab_, nl_ = ndi.label(wm)
        if nl_:
            wide_ = ndi.maximum(d_in, lab_, index=np.arange(1, nl_ + 1)) >= 12.0
            pond_ = np.concatenate(([False], wide_))[lab_]
        else: pond_ = np.zeros(wm.shape, bool)
        bed = lvl_ext - np.where(pond_, np.minimum(2.2, 0.15 + 0.35 * d_in), np.minimum(0.6, 0.15 + 0.35 * d_in))
        bslope = 0.42 + 0.22 * TX.gnoise(wm.shape, to_block(x0, y0), 140.0, 57) + 0.06 * TX.gnoise(wm.shape, to_block(x0, y0), 31.0, 58)
        bank = lvl_ext + 0.25 + bslope * d_out
        target = np.where(wm, bed, np.where(zone, np.minimum(h2w, bank), h2w))
        target = np.where(zone & ~wm, np.maximum(target, lvl_ext + 0.2), target)
        delta = (target - h2w).astype(np.float32)
        delta = np.clip(delta, -8.0, 1.5)
        delta = smooth(delta, 2).astype(np.float32)
        # 12 Nov (1:1 with the sheet): the smoothing pulled the banks below the level 2-3 m on each side, so a 3 m stream showed
        # 8-10 m of water. The bank outside the water is held at least 0.15 m above the level again after the smoothing.
        lowb = zone & ~wm & ((h2w + delta) < lvl_ext + 0.4)   # 0.4 m: above the micro-relief added later (std 0.12 m)
        delta[lowb] = (lvl_ext + 0.4 - h2w)[lowb]
        # 13 Nov (user: 'check the rivers they look odd'): the sheet's streams are 2-4 m wide, so the smoothing averaged their
        # bed with the banks held above the level and lifted it out of the water - 3/4 of every stream lay dry, a trench with
        # water in pieces. The bed inside the water is held at least 0.35 m under the level again after the smoothing (the
        # micro-relief added later has a std of 0.12 m).
        lowbed = wm & ((h2w + delta) > lvl_ext - 0.35)
        delta[lowbed] = (lvl_ext - 0.35 - h2w)[lowbed]
        h += np.repeat(np.repeat(delta, 2, 0), 2, 1)
        # the level index (4 m): the polygon dilated by 8 m, level quantised to 0.25 m (<= 63 levels, else 0.5 m)
        zone4 = (d_out <= 8.0).reshape(512, 4, 512, 4).max((1, 3))
        l4 = lvl_ext[2::4, 2::4]   # the surface is already in 0.5 m steps: sample, do not average (averaging made in-between levels)
        # 4 Nov: the levels are already quantised once for the whole block (waterlevel.STEP, <= 63 per cell); re-rounding
        # them per cell could give two neighbouring cells different quanta - a step in the water at the seam
        lq = np.where(zone4, np.round(l4, 3), 0); vals = np.unique(lq[zone4])
        if len(vals) > 63:
            print('  WARNING: %d water levels in the cell, re-quantised to 0.5 m' % len(vals), flush=True)
            lq = np.where(zone4, np.round(l4 * 2.0) / 2.0, 0); vals = np.unique(lq[zone4])
        vals = vals[:63]
        idx = np.zeros((512, 512), np.uint8)
        for k, v in enumerate(vals): idx[lq == v] = k + 1
        # the low floodplain (4 Nov, user: 'a very marshy land because of the river'): ground less than ~0.6-1.4 m above
        # the river level within 150 m of the water (before the bank carve), for the wet meadow painted below
        FLOOD[0] = (d_out > 0) & (d_out <= 150.0) & ((h2w - lvl_ext) < 1.0 + 0.4 * TX.gnoise(wm.shape, to_block(x0, y0), 60.0, 59))
        del h2w, lvl_ext, d_out, d_in, zone, bed, bank, target, delta, zone4, l4, lq
    del yy_, xx_, gx_, gy_
    # natural banks (26 Oct, user: 'the bank should be natural, here it is grass'). Measured on the vanilla Mius river cell
    # MxD1: the ground within ~20 m of the water is a mix of marsh (1) ~20 %, forest ground (12) ~20 %, leaves (13) ~30 %
    # and grass ~20 %, with willow bushes, bushes and reeds thick along the water. A riparian belt 6-24 m wide (seam-free
    # noise) is painted that way; flora for it is scattered below (RIPARIAN).
    RIPARIAN[0] = None; MUD[0] = None
    wmb = (cov == WATER)
    if wmb.sum() > 400 or (WPOOLS[0] and WRES[0] is not None and bool((WRES[0]['d_out'] <= 30.0).any())):
        from scipy import ndimage as ndi
        d_o = WRES[0]['d_out'] if (WPOOLS[0] and WRES[0] is not None) else ndi.distance_transform_edt(~wmb)   # 14 Nov: the distance to the water measured with the neighbour cell's water (the same bank strip on both sides of a border)
        org = to_block(x0, y0)
        wr = 6.0 + 18.0 * (0.5 + 0.5 * TX.gnoise(wmb.shape, org, 170.0, 61)) + 4.0 * TX.gnoise(wmb.shape, org, 37.0, 62)
        bankc = (GRASS, MARSH, SCRUB) if COVER41_ON[0] else (GRASS, MARSH, FIELD, SCRUB)   # 12 Nov (1:1): the sheet's field stays field to the water's edge
        # 14 Nov (user: things "should look real ... especially where it comes to waterways"): the belt above is the bank of a river
        # 15 - 40 m wide. A stream of 2 - 5 m has a bank strip of its own size: 2 - 7 m of rough grass with reeds, willow and alder
        # bushes, and that strip also parts the stream from a crop field (the corn stood to the water's edge; a strip this narrow
        # is under what the 1:25 000 sheet can show).
        widew_ = ndi.binary_opening(wmb, iterations=4)   # water more than ~8 m across: rivers, ponds
        nearw_ = ndi.distance_transform_edt(~widew_) <= 40.0 if widew_.any() else np.zeros_like(wmb)
        if WPOOLS[0] and WRES[0] is not None: nearw_ = WRES[0]['d_wide'] <= 40.0
        wr_s = 2.0 + 5.0 * (0.5 + 0.5 * TX.gnoise(wmb.shape, org, 60.0, 68)) + 1.0 * TX.gnoise(wmb.shape, org, 9.0, 69)
        wr = np.where(nearw_, wr, wr_s)
        rz = (d_o > 0) & (d_o <= wr) & (np.isin(cov, bankc) | (~nearw_ & (cov == FIELD)))
        # 4 Nov (user: 'the Psel has no mud around its edges, it is a very marshy land ... the grass grows right on the edge of
        # the water'; Zamulin's photo of the Psel bend: 'the swampy river basin', Wheatley: 'the riverbank was boggy'): the low
        # floodplain within 150 m becomes wet meadow, the belt is painted over it too
        wet_m = FLOOD[0] & np.isin(cov, bankc) if FLOOD[0] is not None else np.zeros_like(rz)
        wet_m &= ~MO.dilate(np.isin(cov, (ROAD, TRACK, RAIL, VILLAGE, BUILDING)), 9)
        rz |= wet_m
        cov[rz & (cov == FIELD)] = GRASS
        n1 = TX.gnoise(wmb.shape, org, 7.0, 63) + 0.5 * TX.gnoise(wmb.shape, org, 2.0, 64)
        # the wet meadow / bank belt as measured on the vanilla Mius river cell MxD1: marsh ~20 %, forest ground ~20 %,
        # leaves ~30 %, grass ~20 % (here grass a little more on the outer floodplain)
        rs = np.where(n1 > 0.45, 13, np.where(n1 > 0.0, 12, np.where(n1 > -0.4, 1, 0))).astype(soil.dtype)
        outer_fp = wet_m & (d_o > wr)
        rs = np.where(outer_fp & (n1 < -0.15), 0, rs).astype(soil.dtype)
        # the waterline: a 2-5 m band of BARE wet mud (vanilla Korotich KgD3 0-2 m: clay 36 %, marsh 11 %, grass soil 48 % but
        # grass billboards on only 23 %; Petropolye PgG1: sand 99 %, no grass within 5 m) - clay / marsh / black earth / leaves
        # in patches, no grass billboards on it (MUD), the reeds start at its outer edge
        mud_w = 2.0 + 3.0 * (0.5 + 0.5 * TX.gnoise(wmb.shape, org, 29.0, 65)) + 0.7 * TX.gnoise(wmb.shape, org, 4.0, 66)
        mud_w = np.where(nearw_, mud_w, 0.25 * mud_w)   # a stream: a foot or two of wet earth at the waterline, not a mud flat
        mud = rz & (d_o <= mud_w)
        n2 = TX.gnoise(wmb.shape, org, 3.5, 67)
        ms = np.where(n2 > 0.35, 3, np.where(n2 > -0.1, 0, np.where(n2 > -0.45, 1, 13))).astype(soil.dtype)   # 14 Nov (audit): no black earth (soil 2) at the shore - no vanilla cell uses it there
        rs = np.where(mud, ms, rs).astype(soil.dtype)
        soil[rz] = rs[rz]; tcls[rz] = 0
        soil[wmb] = np.where(n1[wmb] > 0.3, 13, 1).astype(soil.dtype)   # the bed under the water: dark mud / leaves (vanilla 1 and 13)
        if WPOOLS[0]: soil[wmb] = np.where(n1[wmb] > 0.3, 3, 5).astype(soil.dtype)   # 14 Nov: the game's own ponds and rivers lie on sand / clay; soil 1 is the soft 'marsh' material, kept for bog
        tcls[wmb] = 0
        RIPARIAN[0] = (rz, d_o, n1, mud, mud_w, wet_m, nearw_)
        MUD[0] = mud | (rz & (d_o <= mud_w + 2.0) & (n2 > 0.0))   # the grass starts thin: the next 2 m half bare
        del wr, rs, ms, n2
    if WPOOLS[0] and WRES[0] is not None:
        # 14 Nov: the dry stream beds (damp earth, clay and grass; the game's own summer beds are marsh soil on two thirds of their
        # length) and the fords between two pools (clay / sand / grass: firm ground, a ford must not be the soft marsh material)
        skip_ = np.isin(cov, (ROAD, TRACK, RAIL, BUILDING, WATER))
        nd_ = TX.gnoise(soil.shape, to_block(x0, y0), 5.0, 131)
        dm_ = WRES[0]['dry'] & ~skip_
        if dm_.any():
            soil[dm_] = np.where(nd_[dm_] > 0.3, 3, np.where(nd_[dm_] > -0.3, 1, 0)).astype(soil.dtype); tcls[dm_] = 0
            cov[dm_ & (cov == FIELD)] = GRASS
            DRYBED[0] = dm_; MUD[0] = dm_ if MUD[0] is None else (MUD[0] | dm_)
        fd_ = WRES[0]['dam'] & ~skip_
        if fd_.any():
            soil[fd_] = np.where(nd_[fd_] > 0.25, 5, np.where(nd_[fd_] > -0.35, 3, 0)).astype(soil.dtype); tcls[fd_] = 0
        del skip_, nd_, dm_, fd_
    rail_ch_ = None
    if RAILGRADE[0] is not None and rail_lines:
        # 14 Nov (user: "Railway should be leveled so it goes straight instead of on heights"): the formation on the block's even grade
        # (tools/railgrade.py) - low fills and cuts instead of the ground's bumps, ramps where a road crosses, the fill over a stream
        import railgrade as RG
        rail_ch_ = RG.apply(h, rail_lines, np.isin(cov, (ROAD, TRACK)), x0, y0)
        if rail_ch_ is not None: print('  rail grade: %d m2 of ground re-laid' % int(rail_ch_.sum()), flush=True)
    if EARTH41[0]:   # the sheet's dikes / fills / ridges: a bank with a 3 m crest and 1:2 sides, h metres high along each line (a cut:
        # the same shape downward); never under the water itself. Before the micro-relief, after the water carve.
        from scipy import ndimage as ndi_
        bx_, by_ = to_block(x0, y0); up_ = np.zeros((2048, 2048), np.float32); dn_ = np.zeros((2048, 2048), np.float32); ne_ = 0
        for e_ in EARTH41[0]:
            P_ = [(q[0] - bx_, q[1] - by_) for q in e_['pts']]
            if all(not (-40 <= a_ < 2088 and -40 <= b_ < 2088) for a_, b_ in P_): continue
            hh_ = float(e_.get('h', 1.5)); li_ = Image.new('L', (2048, 2048), 0); ImageDraw.Draw(li_).line(P_, fill=1, width=1)
            if not np.asarray(li_).any(): continue   # 14 Nov (audit): an empty raster measured its distances from index [0, 0] - a 2 m mound in the cell's SW corner
            dd_ = ndi_.distance_transform_edt(np.asarray(li_) == 0)
            pr_ = (hh_ * np.clip(1.0 - (dd_ - 1.5) / (2.0 * hh_), 0.0, 1.0)).astype(np.float32)
            if e_.get('kind') == 'cut': dn_ = np.maximum(dn_, pr_)
            else: up_ = np.maximum(up_, pr_)
            ne_ += 1
        if ne_:
            dl_ = up_ - dn_; dl_[cov == WATER] = 0.0     # same grid as the cover and the water carve above (row 0 = south, 1 m)
            if rail_ch_ is not None: dl_[MO.dilate(rail_ch_, 9)] = 0.0   # the railway's own fills and cuts are the rail grade's
            if WPOOLS[0] and WRES[0] is not None and WRES[0].get('pond_lvl') is not None:   # 14 Nov: beside a pond the dike IS the pond's embankment -
                pl_ = WRES[0]['pond_lvl']; h1_ = h.reshape(2048, 2, 2048, 2).mean((1, 3))      # its top a metre over the water, not 1.5 m on top of the bank
                dl_ = np.where(np.isfinite(pl_) & (dl_ > 0), np.clip(pl_ + 1.0 - h1_, 0.0, dl_), dl_).astype(np.float32); del pl_, h1_
            h += np.repeat(np.repeat(dl_, 2, 0), 2, 1)
            print('  earthworks of the sheet: %d lines in the cell' % ne_, flush=True)
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
    if WPOOLS[0] and WRES[0] is not None and WRES[0]['dry'].any(): works_bld = works_bld | MO.dilate(WRES[0]['dry'], 5)   # 14 Nov: no house or shed on a dry stream bed
    h2 = h.reshape(2048, 2, 2048, 2).mean((1, 3)); h8 = h.reshape(256, 16, 256, 16).mean((1, 3))
    if True:   # heights are always re-encoded (relief rounding)
        from pha6 import encode as pha6_encode
        open(path('hei_map'), 'wb').write(pha6_encode(np.clip(h / (MAXH / 65535.0), 0, 65535).astype(np.float32), hp, candidates=[0, 63, 52, 24, 36, 40, 3, 13]))
        print('  works:', len(trench_recs), 'positions,', len(rail_lines), 'railway lines, heights re-encoded', flush=True); lap('works+hei')
    else:
        shutil.copy(hp, path('hei_map'))
    hpad_ = h; del h   # (kept for the building pads, after the objects are placed)
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
    if has_water: C.write_water(od, idx, vals.astype(np.float32), wm1=(cov == WATER), recs=wrecs)
    # op map background: 512 px = 4 m. Vanilla (Mius MgG3 / Petropolye measured): the paper is a hypsometric grey,
    # grey = 124.4 + 0.407 * height (m) (190 at 160 m, 230 at 260 m) - fields are NOT painted; woods a mottled green,
    # gardens / scrub / village plots an olive beige; roads and water come from the line mesh / the engine.
    cv4 = cov.reshape(512, 4, 512, 4)[:, 0, :, 0]
    h512 = h2.reshape(512, h2.shape[0] // 512, 512, h2.shape[1] // 512).mean((1, 3)) if h2.shape[0] % 512 == 0 else np.repeat(np.repeat(h2, 2, 0), 2, 1)[:2048, :2048].reshape(512, 4, 512, 4).mean((1, 3))
    g = np.clip(124.4 + 0.407 * h512, 150, 240)
    RLF = (BLOCK or {}).get('opmap_relief')
    if RLF:   # 14 Nov (user: "the height map on operational map just doesnt exist"): the vanilla generator's paper, a linear grey
        # ramp grey = 126 + 127 * (h - h0) / (max_h - h0) (measured: Mius 126.6 + 0.397 h with max_h 320, Petropolye 126.0 +
        # 0.798 h with max_h 160, R2 > 0.99); h0 / max_h are display-only (the terrain keeps max_h 320) - a block on low ground
        # takes a floor h0 so its ~60 m of relief get a vanilla-like contrast
        h0_ = float(RLF.get('h0', 0.0)); g = np.clip(126.0 + 127.0 * (h512 - h0_) / (float(RLF['max_h']) - h0_), 126, 253)
    elif BLOCK and BLOCK.get('opmap_paper'):   # 13 Nov (user: "it doesnt look like graviteam operational map"): the Mius formula gives a dark sheet
        lo_, hi_ = BLOCK['opmap_paper']       # (165 - 190) on low ground; the vanilla paper is 207 - 227 - the block's own height range on 205 - 230
        g = np.clip(205.0 + (h512 - lo_) / (hi_ - lo_) * 25.0, 200, 235)
    back = np.empty((512, 512, 4), np.uint8); back[..., 0] = g; back[..., 1] = g; back[..., 2] = g; back[..., 3] = 255
    nb = TX.gnoise((512, 512), to_block(x0, y0), 8.0 / 4, 71)   # noise in 4 m pixels
    nb2 = TX.gnoise((512, 512), to_block(x0, y0), 3.0 / 4, 72)
    def tint(mask, cols, flat=False, strength=1.0):
        if not mask.any(): return
        k = np.clip(((nb[mask] + nb2[mask] * 0.5) * 0.7 + 0.5) * len(cols), 0, len(cols) - 1).astype(int)
        if RLF and not flat:   # 14 Nov: vanilla multiplies the height paper by a per-class factor (woods x 0.667 / 0.837 / 0.587,
            # scrub x 0.913 / 0.926 / 0.827 on Mius and Petropolye alike), so every pixel keeps its height; the palettes below were
            # sampled from vanilla at paper grey ~208, so colour / 208 is that factor - never above 1 (a palette lighter than
            # 208 is scaled to its own lightest value, or the high ground would clip to white), and `strength` < 1 pulls it
            # towards the bare paper
            c_ = np.asarray(cols, np.float64); f_ = 1.0 + strength * (c_ / max(208.0, float(c_.max())) - 1.0)
            back[mask, :3] = np.clip(g[mask][:, None] * f_[k], 0, 255).astype(np.uint8)
        else:
            back[mask, :3] = np.asarray(cols, np.uint8)[k]
    if BLOCK and BLOCK.get('opmap_fields'):   # 13 Nov (user: "the fields are all the same"): a light tint per crop, by parcel
        fid4 = fid.reshape(512, 4, 512, 4)[:, 0, :, 0]; fl4 = cv4 == FIELD
        # 14 Nov (opmap_relief): the game never tints fields - on this flat ground (13 m of relief in a cell) full crop tints
        # over 44 % of the map left the parcel patchwork, not the height, as what the eye reads (height explained 36 % of the
        # open land's brightness); 'crop_tint' (default 0.25) keeps the crops as a faint tone on the height paper (89 %)
        ct_ = float(RLF.get('crop_tint', 0.25)) if RLF else 1.0
        tint(fl4 & (fid4 == 1), [(233, 226, 188), (236, 229, 193)], strength=ct_)            # standing grain: pale yellow
        tint(fl4 & (fid4 == 5), [(238, 234, 212), (240, 236, 216)], strength=ct_)            # cut grain: paler
        tint(fl4 & ((fid4 == 2) | (fid4 == 3)), [(210, 224, 198), (214, 227, 202)], strength=ct_)   # potatoes, beet, clover: pale green
        tint(fl4 & (fid4 == 4), [(216, 206, 192), (219, 210, 196)], strength=ct_)            # ploughed: pale brown
    tint(cv4 == WOOD, [(131, 165, 115), (139, 174, 123), (139, 178, 123), (148, 186, 131)])
    tint((cv4 == ORCHARD) | (cv4 == SCRUB), [(180, 182, 164), (189, 194, 172), (197, 198, 180)])
    tint((cv4 == VILLAGE) | (cv4 == BUILDING), [(197, 198, 180), (201, 204, 180), (205, 209, 186), (205, 210, 189)])
    if LANDMARKS41[0] is not None:   # 12 Nov (1:1): the sheet draws marsh as blue dashes on open ground, not as water -
        tint(cv4 == WATER, [(176, 196, 205), (186, 204, 211)], flat=True)   # water only; the marsh gets the game's 'swamp' marks below
    else:
        tint((cv4 == WATER) | (cv4 == MARSH), [(176, 196, 205), (186, 204, 211)], flat=True)
    if OPMAP_SHEET[0] is not None:   # the sheet itself, 4 m: rows of the cell run south -> north, the sheet's north -> south
        bx, by = to_block(x0, y0); S4 = OPMAP_SHEET[0]; c0 = int(round(bx / 4.0)); r0 = S4.shape[0] - int(round((by + CELL) / 4.0))
        crop = np.full((512, 512, 3), 230, np.uint8)
        ra, rb = max(0, r0), min(S4.shape[0], r0 + 512); ca, cb = max(0, c0), min(S4.shape[1], c0 + 512)
        if ra < rb and ca < cb: crop[ra - r0:rb - r0, ca - c0:cb - c0] = S4[ra:rb, ca:cb]
        back[..., :3] = crop[::-1]
    atf1.write(path('back'), back, 'DXT1', mipmaps=False)
    # op map line mesh + sprites
    V, Cc, I = opmap_mesh(h8, lines, x0, y0)
    C.write_opmap(path('opmap'), os.path.join(tpl, 'opmap.cell.loc_def.bin'), V, Cc, I)
    sprites = []
    if LANDMARKS41[0] is not None:   # marsh: 'swamp' marks (as the game's own cells carry them) on a 96 m lattice inside it
        for my_ in range(12, 512, 24):
            for mx_ in range(12, 512, 24):
                if (cv4[max(0, my_ - 6):my_ + 6, max(0, mx_ - 6):mx_ + 6] == MARSH).mean() > 0.5:
                    sprites.append(dict(name='swamp', col=0x80101080, x=mx_ * 4.0, y=my_ * 4.0, z=1.0, rot=1.5708, scale=1.0, kind=2, flag=1))
    # spot heights: local maxima of the 8 m grid with a 400 m window
    hm = smooth(h8, 1); n = 75   # 600 m window
    from numpy.lib.stride_tricks import sliding_window_view
    pad = np.pad(hm, n // 2, mode='edge'); win = sliding_window_view(pad, (n, n)); mx = win.max((-1, -2)); mean = win.mean((-1, -2))
    ys, xs = np.nonzero((hm >= mx) & (hm > mean + 4))
    picked = []
    for yy, xx in sorted(zip(ys, xs), key=lambda q: -hm[q[0], q[1]]):
        if all(abs(yy - a) > 40 or abs(xx - b) > 40 for a, b in picked): picked.append((yy, xx))
    hts = [(hx - x0, hy - y0, lab) for (hx, hy, lab) in HEIGHTS43 if x0 <= hx < x0 + CELL and y0 <= hy < y0 + CELL]   # the 1943 map's spot heights (layout)
    if SPOTS41[0] is not None:   # 12 Nov (1:1): the sheet's spot heights, no invented DEM maxima
        bx_, by_ = to_block(x0, y0)
        hts += [(sx - bx_, sy - by_, '%.1f' % sh_) for (sx, sy, sh_) in SPOTS41[0] if 0 <= sx - bx_ < CELL and 0 <= sy - by_ < CELL]
        if not (RLF or {}).get('dem_spots'): picked = []   # opmap_relief 'dem_spots': true adds the DEM maxima > 600 m from them (vanilla ~5 a cell)
    for (hx, hy, lab) in hts:
        sprites.append(dict(name='map_point', label=lab, col=0x80101010, col2=0x80101010, x=float(hx), y=float(hy), scale=1.0, kind=7, flag=1))
    if OPMAP_SHEET[0] is not None: picked = []   # the sheet's own spot heights
    for yy, xx in picked[:8]:   # DEM maxima elsewhere (none within 600 m of a 1943 height)
        if all(math.hypot(xx * 8.0 - hx, yy * 8.0 - hy) > 600 for (hx, hy, _) in hts):
            sprites.append(dict(name='map_point', label='%d' % round(hm[yy, xx]), col=0x80101010, col2=0x80101010, x=xx * 8.0, y=yy * 8.0, scale=1.0, kind=7, flag=1))
    for (px, py), t, key in places:
        if x0 <= px < x0 + CELL and y0 <= py < y0 + CELL:
            sprites.append(dict(name='map_point', label=key, col=0xC0000000, col2=0xC0000000, x=px - x0, z=1.0, y=py - y0, scale=1.0, kind=0, flag=1))
    for pp in (buildings[:400] if OPMAP_SHEET[0] is None else []):
        cx = sum(p[0] for p in pp) / len(pp); cy = sum(p[1] for p in pp) / len(pp)
        if 0 <= cx < 2048 and 0 <= cy < 2048: sprites.append(dict(name='build', col=0xff694320, x=cx, y=cy, scale=0.4, kind=1, flag=0))
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
    if WOODKIND[0] is not None:   # M16 (wood_kind.png, tools/wig_woods.py): pine / broadleaf / mixed woods by the WIG tree symbols
        wk = woodkind_cell(i, j); wd_ = (cov == WOOD) & ~dug
        for kv, key in ((0, 'WOOD'), (1, 'WOOD_PINE'), (2, 'WOOD_BROAD'), (3, 'WOOD_MIXED')):
            scatter(wd_ & (wk == kv), DENSITY['WOOD'], FLORA.get(key, FLORA['WOOD']))
    else:
        scatter((cov == WOOD) & ~dug, DENSITY['WOOD'], FLORA['WOOD'])
    scatter((cov == SCRUB) & ~dug, DENSITY['SCRUB'], FLORA['SCRUB'])
    if YOUNG41[0] is not None:   # WIG 152 / 153: young pine growth and bushes. Each sign on the 1:25 000 sheet stands for a clump;
        # the plants follow the sheet's own sign density (about 15 plants per sign: 3 signs/ha -> 1 plant per 220 m2, 10 -> 1 per 67 m2)
        K_, D_ = [cell41(R_, i, j) for R_ in YOUNG41[0]]
        open_ = np.isin(cov, (GRASS, FIELD, MARSH)) & ~dug
        mixes = {1: [(0, 6), (1, 1), (7, 2)], 2: [(7, 4), (8, 2), (16, 1)], 3: [(0, 3), (7, 3)], 4: [(0, 4), (1, 1), (7, 3), (8, 1)]}
        for kv, mix in mixes.items():
            for lo, hi in ((1, 3), (3, 6), (6, 12), (12, 99)):
                m_ = open_ & (K_ == kv) & (D_ >= lo) & (D_ < hi)
                if m_.any(): scatter(m_, (0.5 * (lo + min(hi, 20))) * 15.0 / 1e4, mix)
    if TREE_ROWS[0]:   # M16 (tree_rows.json, tools/rkka_alleys.py): the sheet's rows of trees along the roads, a tree every 9 m
        bx_, by_ = to_block(x0, y0); rx, ry = [], []
        for row in TREE_ROWS[0]:
            P = np.array(row, float) - [bx_, by_]
            if ((P[:, 0] < -20) | (P[:, 0] > 2068) | (P[:, 1] < -20) | (P[:, 1] > 2068)).all(): continue
            for a_, b_ in zip(P[:-1], P[1:]):
                L_ = float(np.hypot(*(b_ - a_))); k_ = max(1, int(L_ / 9.0))
                for t_ in np.arange(k_) / k_:
                    x_, y_ = a_ + (b_ - a_) * t_ + rng.normal(0, 0.8, 2)
                    if 0 <= x_ < 2048 and 0 <= y_ < 2048 and cov[int(y_), int(x_)] not in (ROAD, TRACK, RAIL, WATER, BUILDING): rx.append(x_); ry.append(y_)
        if rx:
            nn_ = len(rx); fx.append(np.array(rx)); fy.append(np.array(ry)); fr.append(rng.random(nn_)); ft.append(rng.choice([4, 5, 11], nn_, p=[0.4, 0.35, 0.25]))
    if BUSHES41[0]:   # 12 Nov (1:1 symbols): the sheet's ring-with-a-tail sign (a tree standing alone) - one broadleaf tree at each
        bx_, by_ = to_block(x0, y0); P_ = np.array(BUSHES41[0], float) - [bx_, by_]
        P_ = P_[(P_[:, 0] >= 0) & (P_[:, 0] < 2048) & (P_[:, 1] >= 0) & (P_[:, 1] < 2048)]
        P_ = np.array([q for q in P_ if cov[int(q[1]), int(q[0])] not in (ROAD, TRACK, RAIL, WATER, BUILDING)]).reshape(-1, 2)
        if len(P_): fx.append(P_[:, 0]); fy.append(P_[:, 1]); fr.append(rng.random(len(P_))); ft.append(rng.choice([4, 5], len(P_)))
    if TREES41[0]:   # 13 Nov: the sheet's lone tree circles outside the woods (TM 309 / 313 / WIG 156) - one tree at each
        bx_, by_ = to_block(x0, y0); P_ = np.array(TREES41[0], float) - [bx_, by_]
        P_ = P_[(P_[:, 0] >= 0) & (P_[:, 0] < 2048) & (P_[:, 1] >= 0) & (P_[:, 1] < 2048)]
        P_ = np.array([q for q in P_ if cov[int(q[1]), int(q[0])] not in (ROAD, TRACK, RAIL, WATER, BUILDING, WOOD)]).reshape(-1, 2)
        if len(P_): fx.append(P_[:, 0]); fy.append(P_[:, 1]); fr.append(rng.random(len(P_))); ft.append(rng.choice([4, 5, 11], len(P_), p=[0.4, 0.35, 0.25]))
    scatter(cov == ORCHARD, DENSITY['ORCHARD'], FLORA['ORCHARD'])
    # village trees only in the street zone (yards and gardens, 70 m), none on the open sovkhoz land - the whole village /
    # farm polygon used to be sown at 1 tree per 150 m2 (user, 25 Oct: far too many trees in the settlements)
    street_zone = MO.dilate(np.isin(cov, (ROAD, TRACK)), 141) & ~FARM_MASK[0] if FARM_MASK[0] is not None else MO.dilate(np.isin(cov, (ROAD, TRACK)), 141)
    scatter((cov == VILLAGE) & street_zone, DENSITY['VILLAGE'], FLORA['VILLAGE'])
    scatter((cov == FIELD) & (fid == 3), DENSITY['FIELD'], FLORA['FIELD_SUNFL'])   # ripe grain, green crop and fallow carry no plants (Petropolye)
    # balkas: bushes and small trees on the steep sides and in the bottoms of the ravines; a bush per ~900 m2 on the open steppe
    steep = (slope2 > 0.12) & (cov == GRASS) & ~dug; scatter(steep, DENSITY['BALKA'], FLORA['BALKA'])
    scatter((cov == GRASS) & ~steep & ~dug, DENSITY['STEPPE'], FLORA['STEPPE'])
    if wetm_ is not None:   # swampy meadow: a third of the bog's bushes and reeds
        scatter((cov == MARSH) & ~wetm_, DENSITY['MARSH'], FLORA['MARSH']); scatter(wetm_, DENSITY['MARSH'] / 3.0, FLORA['MARSH'])
    else:
        scatter(cov == MARSH, DENSITY['MARSH'], FLORA['MARSH'])
    wmask = (cov == WATER)
    if DUNE[0] is not None:
        sd_, sand_, ds_ = DUNE[0]; DUNE[0] = None
        open_ = sd_ & np.isin(cov, (GRASS, SCRUB)) & ~dug
        cl_ = TX.gnoise(cov.shape, to_block(x0, y0), 26.0, 126)
        scatter(open_ & (cl_ > 0.35), 1 / 55.0, [(0, 4), (1, 3), (2, 1), (7, 2)])          # clumps of young and middle pine with bushes
        scatter(open_ & (cl_ > 0.1) & (cl_ <= 0.35), 1 / 180.0, [(0, 3), (7, 3), (8, 1)])   # their thin fringe
        scatter(open_ & ~sand_, 1 / 260.0, [(7, 3), (0, 1)])                                 # single bushes on the grass islands and the edge
    if RIPARIAN[0] is not None:
        # the bank vegetation (vanilla MxD1: verba willow bushes 16, bushes 7 / 8, reeds 6, small trees 3 / 4 along the water,
        # in clumps; vanilla puts no plants IN the water). 4 Nov: the waterline mud stays bare; reed beds (rogoz 6) stand from
        # the outer edge of the mud band out to ~10 m and in patches over the wet meadow, willows behind them
        rz, d_o, n1, mud, mud_w, wet_m, nearw_r = RIPARIAN[0]
        clump = TX.gnoise(cov.shape, to_block(x0, y0), 19.0, 66)
        reed = rz & ~mud & (d_o <= mud_w + 8.0) & (clump > -0.25)
        # 14 Nov: measured against the game's own maps our streams carried 88 reeds per 100 m, theirs 6 - 33 - the reed beds stay by
        # the wide water (ponds, the double-line reaches), a stream gets a thin fringe
        if WPOOLS[0]: scatter(reed & nearw_r & ~dug, 1 / 6.0, [(6, 1)]); scatter(reed & ~nearw_r & ~dug, 1 / 22.0, [(6, 1)])
        else: scatter(reed & ~dug, 1 / 6.0, [(6, 1)])
        scatter(rz & ~mud & (d_o <= mud_w + 1.5) & (clump <= -0.25) & ~dug, 1 / 25.0, [(6, 1)])   # a thin fringe between the beds
        scatter(wet_m & ~mud & (d_o > mud_w + 8.0) & (clump > 0.3) & ~dug, 1 / 14.0, [(6, 1)])   # reed patches in the wet meadow
        thick = rz & ~mud & (d_o > mud_w + 2.0) & (clump > 0.15) & ~dug
        scatter(thick & (d_o <= 12.0), 1 / 26.0, [(16, 5), (7, 3), (8, 2), (12, 1)])
        scatter(thick & (d_o > 12.0) & ~wet_m, 1 / 45.0, [(16, 3), (7, 2), (8, 2), (3, 2), (4, 1), (12, 1)])
        scatter(thick & (d_o > 12.0) & wet_m, 1 / 90.0, [(16, 4), (12, 1), (7, 1)])   # willow clumps on the wet meadow
        scatter(rz & ~mud & (clump <= 0.15) & ~dug, 1 / 160.0, [(16, 2), (7, 2), (8, 1)])   # single bushes between the thickets
        RIPARIAN[0] = None
    if DRYBED[0] is not None:   # 14 Nov: sedge and reeds, willow and bushes along a dry bed (the game's own dry beds: 6 - 33 reeds, 4 - 34 willows, 7 - 39 bushes per 100 m)
        scatter(MO.dilate(DRYBED[0], 5) & np.isin(cov, (GRASS, SCRUB, MARSH)) & ~dug, 1 / 55.0, [(6, 3), (16, 2), (7, 2), (8, 1)])
        DRYBED[0] = None
    scatter(cov == MARSH, DENSITY['WATER'] / 2, FLORA['WATER'])   # wet meadow: reeds / willows; open water stays open
    # settlements: street villages generated along the OSM streets inside the 1941 built-up extent (tools/settle.py),
    # the OSM footprints kept; yards, garden plots and clay margins are painted into the soil here
    lap('flora')
    import settle as SE
    SE.ONE_PER_SYMBOL[0] = bool(BLOCK and BLOCK.get('period_houses'))
    SE.HOUSE_STYLE[0] = (BLOCK or {}).get('house_style', 'vanilla')   # 17 Nov (M19): 'mazovia' on the 1944 Polish blocks
    SE.BRICK_ZONES[:] = [tuple(z_) for z_ in ((BLOCK or {}).get('brick_zones') or [])]   # 14 Nov: the old town centres (block metres)
    SE.TOWN_ZONES[:] = [tuple(z_) for z_ in ((BLOCK or {}).get('town_zones') or [])]   # 19 Nov: the towns (their WIG quarters are street fronts)
    objs, vtrees = SE.build(cov, soil, lines, buildings, slope2, rng, VILLAGE, WATER, MARSH, ROAD, TRACK, RAIL, BUILDING, FARM_MASK[0], cell_seed=i * 131 + j * 17, origin=(x0, y0), vil_pad=VIL_PAD[0], pad=PAD, works_mask=works_bld)
    gx = [t[0] for t in vtrees]; gy = [t[1] for t in vtrees]; gtyp = np.array([t[2] for t in vtrees], np.uint8)
    SE.kolkhoz(objs, soil, FARM_MASK[0], cov, rng, WATER, MARSH, BUILDING, road_mask=MO.dilate(np.isin(cov, (ROAD, TRACK, RAIL)), 13), origin=to_block(x0, y0), works_mask=works_bld)   # sovkhoz yards: long barns (builds_cap farm0 / farm1) round a clay yard, off the roads
    if SE.BUF.get('mask') is not None and SE.BUF['mask'].any():   # copied homesteads bring their own trees: the scattered ones under them go
        sm = SE.BUF['mask']
        for q in range(len(fx)):
            xi_ = np.clip(fx[q].astype(int), 0, 2047); yi_ = np.clip(fy[q].astype(int), 0, 2047); kp = ~sm[yi_, xi_]
            fx[q], fy[q], fr[q], ft[q] = fx[q][kp], fy[q][kp], fr[q][kp], ft[q][kp]
    # 12 Nov (1:1): the churches of the RKKA sheet (period/churches_1941.json, checked one by one) - the game's church model,
    # the houses / sheds the village walk put on its spot moved out of the way (18 m)
    cj_ = repo_path(os.path.join(BLOCK['period_dir'], 'churches_1941.json')) if BLOCK else None
    if cj_ and os.path.exists(cj_):
        bx_, by_ = to_block(x0, y0)
        for ch in json.load(open(cj_, encoding='utf-8'))['churches']:
            cx_, cy_ = ch['x'] - bx_, ch['y'] - by_
            if 0 <= cx_ < 2048 and 0 <= cy_ < 2048:
                objs = [o for o in objs if not (o[1].startswith(('build', 'saray', 'farm', 'fence', 'fpost', 'gates', 'kalitka')) and math.hypot(BF.pos(o)[0] - cx_, BF.pos(o)[1] - cy_) < 18.0)]
                objs += church_objs(ch.get('kind', 'brick_tower'), float(cx_), float(cy_), float(ch.get('ang', 0.0)))
                sprites.append(dict(name='church', col=0xff000000, x=float(cx_), y=float(cy_), rot=1.5708, scale=2.0, kind=1, flag=0))
    # 12 Nov (user: "every symbol has to have its object ... in exact spot", both maps): the point symbols of the RKKA sheet
    # (period/landmarks_1941.json, read off the sheet tile by tile and checked on crops). Objects and op-map marks as the
    # game's own cells use them (windmill1 + 'windmill', well0 + 'well', a plot of cross_rec / cross_roun + 'cementry').
    #   windmill -> windmill1;  well -> well0;  cross -> cross_rec;  chapel -> cross_roun (the game has no chapel model);
    #   cemetery -> crosses on an 8 m lattice over the plot;  fence -> fence2a along the line;
    #   bridge -> the dry crossing above + 'bridge' mark;  ford -> 'ford' mark;  trig -> 'geo_mark';  mound -> 'kurgan';
    #   label (fl., g. dv., piln., lesn. ...) -> the sheet's abbreviation as map text.
    if LANDMARKS41[0]:
        bx_, by_ = to_block(x0, y0); lrng = np.random.default_rng(abs(hash((round(bx_), round(by_)))) % (2 ** 31))
        blk_ = np.zeros((2048, 2048), bool)
        def _clear(cx_, cy_, r_):
            objs[:] = [o for o in objs if not (o[1].startswith(('build', 'saray', 'farm', 'izba', 'barn', 'mz_', 'mzp_', 'fence', 'fpost', 'gates', 'kalitka', 'seno', 'drova')) and math.hypot(BF.pos(o)[0] - cx_, BF.pos(o)[1] - cy_) < r_)]
        for L_ in LANDMARKS41[0]:
            t_ = L_['type']
            if t_ == 'fence':
                P_ = [(px_ - bx_, py_ - by_) for px_, py_ in L_['pts']]
                if all(not (0 <= a_ < 2048 and 0 <= b_ < 2048) for a_, b_ in P_): continue
                for a_, b_ in zip(P_, P_[1:]): SE._fence(objs, a_, b_, 'fence2a', blk_, posts=True)
                continue
            cx_, cy_ = L_['x'] - bx_, L_['y'] - by_
            if not (0 <= cx_ < 2048 and 0 <= cy_ < 2048): continue
            cx_, cy_ = float(cx_), float(cy_); ang_ = float(L_.get('ang', 0.0))
            if t_ == 'windmill':
                _clear(cx_, cy_, 14.0); objs.append(('tabs\\builds_wood.cfgpack', 'windmill1', cx_, cy_, float(lrng.random() * 6.28)))
                sprites.append(dict(name='windmill', col=0xff000000, x=cx_, y=cy_, rot=1.5708, scale=2.0, kind=1, flag=0))
            elif t_ == 'church':   # a church the first church list (churches_1941.json) did not have
                _clear(cx_, cy_, 18.0); objs += church_objs(L_.get('kind', 'brick_tower'), cx_, cy_, float(L_.get('ang', 0.0)))
                sprites.append(dict(name='church', col=0xff000000, x=cx_, y=cy_, rot=1.5708, scale=2.0, kind=1, flag=0))
            elif t_ == 'watermill':   # the toothed-wheel sign on a stream: the game has no mill, a barn at the water + the sheet's "meln."
                _clear(cx_, cy_, 9.0); objs.append(('tabs\\builds_wood.cfgpack', 'barn1', cx_, cy_, float(lrng.random() * 6.28)))
                if L_.get('key'): sprites.append(dict(name='map_point', label=L_['key'], col=0xC0000000, col2=0xC0000000, x=cx_, z=1.0, y=cy_, scale=0.8, kind=0, flag=1))
            elif t_ == 'well':
                r_ = float(lrng.random() * 6.28); objs.append(SE.mz('tabs\\structs.cfgpack', 'well0', lrng, 0.0, 'well') + (cx_, cy_, r_))   # 17 Nov (M19): the well sweep
                sprites.append(dict(name='well', col=0xff204169, x=cx_, y=cy_, rot=r_, scale=1.2, kind=1, flag=0))
            elif t_ in ('cross', 'chapel'):
                _clear(cx_, cy_, 4.0); objs.append((SE.mz('tabs\\objects.cfgpack', 'cross_rec', lrng, 0.0, 'cross') if t_ == 'cross' else ('tabs\\objects.cfgpack', 'cross_roun')) + (cx_, cy_, 1.7))   # 17 Nov (M19): a wayside shrine for some crosses
                sprites.append(dict(name='cementry', col=0x80101010, x=cx_, y=cy_, z=1.0, rot=1.5708, scale=0.8 if t_ == 'cross' else 1.1, kind=2, flag=1))
            elif t_ == 'cemetery':
                w_, d_ = float(L_.get('w', 40.0)), float(L_.get('d', 40.0)); ca_, sa_ = math.cos(ang_), math.sin(ang_)
                _clear(cx_, cy_, 0.5 * math.hypot(w_, d_)); k_ = 0
                for u_ in np.arange(-w_ / 2 + 4.0, w_ / 2 - 3.9, 8.0):
                    for v_ in np.arange(-d_ / 2 + 4.0, d_ / 2 - 3.9, 8.0):
                        gx_, gy_ = cx_ + u_ * ca_ + v_ * sa_ + float(lrng.normal(0, 0.6)), cy_ - u_ * sa_ + v_ * ca_ + float(lrng.normal(0, 0.6))
                        if 0 <= gx_ < 2048 and 0 <= gy_ < 2048: objs.append(('tabs\\objects.cfgpack', 'cross_rec' if k_ % 5 < 3 else 'cross_roun', gx_, gy_, 1.7)); k_ += 1
                sprites.append(dict(name='cementry', col=0x80101010, x=cx_, y=cy_, z=1.0, rot=1.5708, scale=1.5, kind=2, flag=1))
            elif t_ == 'bridge':
                sprites.append(dict(name='bridge', col=0xC01E1A0C, col2=0xC0101010, x=cx_, y=cy_, z=1.0, rot=ang_, scale=1.5, kind=1, flag=1))
            elif t_ == 'ford':
                sprites.append(dict(name='ford', col=0xC01E1A0C, col2=0xC0101010, x=cx_, y=cy_, z=1.0, rot=ang_, scale=1.5, kind=1, flag=1))
            elif t_ == 'trig':
                sprites.append(dict(name='geo_mark', col=0xff000000, x=cx_, y=cy_, rot=1.5708, scale=1.2, kind=1, flag=0))
            elif t_ == 'mound':
                sprites.append(dict(name='kurgan', label='', col=0xC0101010, col2=0xC0101010, x=cx_, y=cy_, z=1.0, scale=1.0, kind=0, flag=1))
            elif t_ == 'label' and L_.get('key'):
                sprites.append(dict(name='map_point', label=L_['key'], col=0xC0000000, col2=0xC0000000, x=cx_, z=1.0, y=cy_, scale=0.8, kind=0, flag=1))
                # 14 Nov: the sheet's lettered buildings as the game's whole brick buildings (vanilla: every station of the Korotich
                # line is the brick hall 18 - 26 m from the rail): 'st.' / 'raz.' a station hall along the track, 'Gmin. upr.' and
                # 'kirp.' the hall, 'g. dv.' (a manor) the two-storey house. The symbol's own house goes; the yard stays.
                b_ = L_.get('build') or {'раз.': 'hall_rail', 'ст.': 'hall_rail', 'Гмин. упр.': 'hall', 'кирп.': 'hall', 'г. дв.': 'brick2'}.get(L_.get('rus'))
                if b_:
                    a_ = float(L_['ang']) if 'ang' in L_ else None
                    if a_ is None:   # along the railway, else along the nearest road
                        for m_, r_ in ((cov == RAIL, 90), (np.isin(cov, (ROAD, TRACK)), 60)):
                            if b_ != 'hall_rail' and r_ == 90: continue
                            y0_, y1_, x0_, x1_ = int(max(0, cy_ - r_)), int(min(2048, cy_ + r_)), int(max(0, cx_ - r_)), int(min(2048, cx_ + r_))
                            yy_, xx_ = np.nonzero(m_[y0_:y1_, x0_:x1_])
                            if len(yy_) >= 30:
                                u_, v_ = xx_ - xx_.mean(), yy_ - yy_.mean(); a_ = 0.5 * math.atan2(2 * float((u_ * v_).mean()), float((u_ ** 2).mean() - (v_ ** 2).mean()))
                                if b_ == 'hall_rail':   # 22 m off the track's middle, on the side the symbol stands on
                                    nx_, ny_ = -math.sin(a_), math.cos(a_); d_ = (cx_ - x0_ - xx_.mean()) * nx_ + (cy_ - y0_ - yy_.mean()) * ny_
                                    s_ = 1.0 if d_ >= 0 else -1.0; cx_, cy_ = float(x0_ + xx_.mean() + nx_ * s_ * max(22.0, abs(d_))), float(y0_ + yy_.mean() + ny_ * s_ * max(22.0, abs(d_)))
                                    cx_, cy_ = min(2030.0, max(18.0, cx_)), min(2030.0, max(18.0, cy_))
                                break
                    nd_ = 'build_asm_brick2' if b_ == 'brick2' else 'build_asm_hall'
                    _clear(cx_, cy_, 17.0); objs.append(('tabs\\builds_cap.cfgpack', nd_, cx_, cy_, BF.heading(nd_, a_ or 0.0)))
    # op-map house symbols: the OSM footprints are gone (osm_building_ok), so the generated houses carry them
    nb_ = sum(1 for sp in sprites if sp['name'] == 'build') if OPMAP_SHEET[0] is None else 400
    for o in objs:
        if nb_ >= 400: break
        if o[1].startswith('build') and 0 <= o[2] < 2048 and 0 <= o[3] < 2048:
            sprites.append(dict(name='build', col=0xff694320, x=float(o[2]), y=float(o[3]), scale=0.4, kind=1, flag=0)); nb_ += 1
    C.write_sprites(path('opmap_tri'), sprites)
    if BLOCK and BLOCK.get('farm_paths', True):
        # 14 Nov (user: "some buildings should have paths connecting them to roads"): a building standing off the road - the long
        # barns, the halls and the station, a barn, a windmill, a house further than 14 m from a road - gets a beaten earth path (2 - 3 m,
        # clay with trampled edges) straight to the nearest road, track or path already laid, up to 160 m, never through the water.
        # Seen from the farthest first is wrong: the nearest go first, so a farther building joins the path of a nearer one.
        from scipy.spatial import cKDTree as KDp_
        rdm_ = np.isin(cov, (ROAD, TRACK)); ry_, rx_ = np.nonzero(rdm_[::2, ::2]); ry_ = ry_ * 2 + 1; rx_ = rx_ * 2 + 1
        def want_(o):
            return o[1].startswith(('farm', 'build_asm', 'barn', 'windmill', 'izba', 'build', 'church', 'mz_')) and not o[1].startswith('saray')
        cand_ = []
        if len(rx_):
            kr_ = KDp_(np.c_[rx_, ry_].astype(np.float64))
            for o in objs:
                if not want_(o): continue
                cx_, cy_ = BF.centre(o[2], o[3], o[4], o[1])
                if not (0 <= cx_ < 2048 and 0 <= cy_ < 2048): continue
                d_, _ = kr_.query([cx_, cy_])
                if 14.0 < d_ <= 160.0: cand_.append((d_, cx_, cy_, o[1]))
        cand_.sort()
        pim_ = Image.new('L', (2048, 2048), 0); pdr_ = ImageDraw.Draw(pim_); ppts_ = np.zeros((0, 2)); npth_ = 0; done_ = []
        watc2_ = cov == WATER
        for d_, cx_, cy_, nd_ in cand_:
            if any(math.hypot(cx_ - a_, cy_ - b_) < 25.0 for a_, b_ in done_): continue   # one path per farmstead
            dr_, jr_ = kr_.query([cx_, cy_]); tx_, ty_ = float(rx_[jr_]), float(ry_[jr_])
            if len(ppts_):
                dp_, jp_ = KDp_(ppts_).query([cx_, cy_])
                if dp_ + 4.0 < dr_: tx_, ty_ = float(ppts_[jp_][0]), float(ppts_[jp_][1]); dr_ = dp_
            if dr_ <= 14.0 or dr_ > 160.0: continue
            L_ = math.hypot(tx_ - cx_, ty_ - cy_); k_ = max(2, int(L_))
            xs_ = np.linspace(cx_, tx_, k_); ys_ = np.linspace(cy_, ty_, k_)
            if watc2_[np.clip(ys_.astype(int), 0, 2047), np.clip(xs_.astype(int), 0, 2047)].any(): continue
            pdr_.line([(cx_, cy_), (tx_, ty_)], fill=255, width=3)
            ppts_ = np.vstack([ppts_, np.c_[xs_[::2], ys_[::2]]]); done_.append((cx_, cy_)); npth_ += 1
        if npth_:
            pm_ = np.asarray(pim_) > 0
            ed_ = MO.dilate(pm_, 3) & ~pm_ & (TX.gnoise(soil.shape, to_block(x0, y0), 4.0, 141) > 0.0)
            keep_ = np.isin(cov, (ROAD, TRACK, RAIL, WATER, BUILDING))
            soil[pm_ & ~keep_] = 3; soil[ed_ & ~keep_] = 10; tcls[(pm_ | ed_) & ~keep_] = 0
            pmw_ = pm_ | ed_
            for q in range(len(fx)):   # no tree or bush on the path
                xi_ = np.clip(fx[q].astype(int), 0, 2047); yi_ = np.clip(fy[q].astype(int), 0, 2047); kp = ~pmw_[yi_, xi_]
                fx[q], fy[q], fr[q], ft[q] = fx[q][kp], fy[q][kp], fr[q][kp], ft[q][kp]
            print('  paths to the road: %d (%.0f m)' % (npth_, len(ppts_) * 2.0), flush=True)
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
    sbuf = SE.BUF if SE.BUF.get('mask') is not None else None
    rbuf = TKS.BUF if TKS.BUF.get('mask') is not None else None
    if sbuf is not None: tcls[sbuf['mask']] = 0
    if rbuf is not None: tcls[rbuf['mask']] = 0
    t1 = time.time()
    lay = REF.apply(soil, tcls, rng, origin=to_block(x0, y0))
    if BLOCK and BLOCK.get('parcel_types') and lay['grass'].shape == fid.shape:
        # 13 Nov (user: "its july-august why there are no fields with crops that are full"): the grain grass of the Petropolye windows
        # is strength 5 (values 165 / 166 = 5 << 5 | type 5 / 6, the season's corn_01 / corn_02); the game's Mius fields carry 6 and 7
        # (197 / 198, 229 / 230). Standing grain takes the Mius strengths, cut grain a thin strength 3 on a third of its pixels.
        # 13 Nov, later (user: "there is no crop at all"): the Mius strengths 6 / 7 (197 / 198, 229 / 230) do NOT draw on these maps in
        # August - the standing grain vanished. Back to the values that are known to draw here (165 / 166, the Petropolye fields); the
        # crop is made FULLER by filling the bare pixels between the tufts instead (vanilla leaves half of a field's pixels empty).
        gr_ = lay['grass']; nz_ = rng.random(fid.shape); pick_ = np.where(rng.random(fid.shape) < 0.6, 165, 166).astype(np.uint8)
        st_m = (cov == FIELD) & (fid == 1) & ((soil == 6) | (soil == 7) | (soil == 0))   # 14 Nov: the green-ground blobs the reference windows scatter through a grain parcel (a third of it) carry grain too
        fill_ = st_m & (((gr_ & 31) == 5) | ((gr_ & 31) == 6) | (nz_ < float(BLOCK.get('grain_fill', 0.9))))   # 14 Nov (user: "the fields lack crops"): 0.5 still read as bare ground - nine pixels in ten carry grain, whatever grass the reference window had put there
        # 14 Nov: the edge of a standing field. The grain stood to a ruled line against the yard, the meadow and the road verge; in
        # the outer 1 - 5 m (the width varies along the edge) it now thins out and the grass of the neighbouring ground shows through
        from scipy import ndimage as ndi_e
        de_ = ndi_e.distance_transform_edt(st_m)
        ew_ = 2.5 + 2.0 * TX.gnoise(fid.shape, to_block(x0, y0), 18.0, 91)
        fill_ &= (de_ > 1.0) & ((de_ >= ew_) | (rng.random(fid.shape) < np.clip((de_ - 1.0) / np.maximum(ew_ - 1.0, 0.5), 0.0, 1.0)))
        gr_[fill_] = pick_[fill_]
        # 14 Nov (user: "the fields are not ripe at all"): two things kept the grain green. (1) The reference windows bring the green
        # crop ground (soil 7) as blobs through a third of every grain parcel - nine in ten of them become grain ground (soil 6, with
        # the detail of the parcel's own grain pixels); (2) the ambient colour of the Petropolye windows under the grain is a greenish
        # (92, 90, 48) - the game's own Mius summer fields are (117, 100, 64); a field ripe for the harvest at the end of July takes a
        # straw tone (126 - 134, 106 - 112, 58 - 66) by its share of standing grain in each 8 m square, cut grain a paler one.
        rp_ = float(BLOCK.get('ripe', 0.9))
        if rp_ > 0:
            g7_ = st_m & (soil == 7) & (nz_ < rp_); g6_ = st_m & (soil == 6)
            if g7_.any() and g6_.any():
                sy_, sx_ = np.nonzero(g6_); pk2_ = rng.integers(0, len(sy_), int(g7_.sum()))
                soil[g7_] = 6; lay['det'][g7_] = lay['det'][sy_[pk2_], sx_[pk2_]]; lay['hi'][g7_] = lay['hi'][sy_[pk2_], sx_[pk2_]]
            lac_ = lay['lac']; f8_ = 2048 // lac_.shape[0]
            for msk_, col_ in ((st_m, (130, 109, 62)), ((cov == FIELD) & (fid == 5), (138, 118, 76))):
                w_ = ndi_e.gaussian_filter(msk_.reshape(lac_.shape[0], f8_, lac_.shape[1], f8_).mean((1, 3)).astype(np.float32), 0.6) * rp_
                if not (w_ > 0.01).any(): continue
                for c_, ref_ in zip(range(3), (92.0, 90.0, 48.0)):   # shifted by (straw - the windows' mean grain tone): the windows' own texture stays
                    lac_[..., c_] = np.clip(lac_[..., c_] + w_ * (col_[c_] - ref_), 0, 255).astype(np.uint8)
        # 14 Nov (user: "The fields of grain are flat" / "Find another way"): the vars layer (2 m) under the grain came from the Petropolye
        # windows, whose grain lies flat in the game too: vars 5 - 6 on 60 % of the grain pixels. The game's Mius fields, whose grain
        # stands, carry vars 1 - 3 (0 8 %, 1 41 %, 2 24 %, 3 13 %, 4 7 %, 5 3 %, 6 2 %, 7 1 %). The standing grain now takes the Mius
        # distribution, in smooth patches (seam-free noise ranked into those shares)
        if BLOCK.get('grain_vars', True) and lay['vars'].shape[0] * 2 == fid.shape[0]:
            vv_ = lay['vars']; sg_ = st_m[::2, ::2]
            if sg_.any():
                q_ = TX.gnoise(fid.shape, to_block(x0, y0), 9.0, 161)[::2, ::2] + 0.35 * TX.gnoise(fid.shape, to_block(x0, y0), 3.0, 162)[::2, ::2]
                cut_q = np.cumsum([0.08, 0.41, 0.24, 0.13, 0.07, 0.03, 0.02])
                # the noise is about normal (sd 0.455 measured): its shares by fixed thresholds, so both sides of a cell border agree
                from scipy.special import ndtri as nd_
                th_ = nd_(cut_q) * 0.455
                vv_[sg_] = np.searchsorted(th_, q_[sg_]).astype(vv_.dtype)
            # 14 Nov, later (user, in the game: "There are no crops at all, up close or far away"): low vars under level-5 grain draw
            # nothing, as level 6 / 7 under the Petropolye vars 5 - 6 drew nothing on 13 Nov. The vanilla maps pair them: Petropolye
            # level 5 with vars 5 - 6, the Mius standing grain level 6 / 7 with vars 0 - 3. Grain on vars 0 - 3 takes level 6 or 7
            # (58 / 42 as in the Mius window), grain on vars 4 - 7 keeps level 5.
            if BLOCK.get('grain_levels', True):
                v2_ = np.repeat(np.repeat(lay['vars'], 2, 0), 2, 1)
                gl_ = ((gr_ == 165) | (gr_ == 166)) & (v2_ <= 3)
                gr_[gl_] = ((np.where(rng.random(fid.shape) < 0.58, 6, 7).astype(np.uint8) << 5) | (gr_ & 31))[gl_]
        cut_m = (cov == FIELD) & (fid == 5)
        thin_ = cut_m & (soil == 6)
        gr_[thin_] = np.where(nz_[thin_] < float(BLOCK.get('stubble_fill', 0.6)), np.where(pick_[thin_] == 165, 133, 134), 0).astype(np.uint8)
        # 14 Nov (user: "plenty of parcels are just empty while they should be crops"): the green crops (potatoes, beet, clover) filled the
        # same way - the bare pixels of a green parcel take the two grass values the reference windows already use on this soil (167 / 168)
        gm_ = (cov == FIELD) & ((fid == 2) | (fid == 3)) & (soil == 7) & (gr_ == 0) & (nz_ < float(BLOCK.get('green_fill', 0.85)))
        gr_[gm_] = np.where(pick_[gm_] == 165, 168, 167).astype(np.uint8)   # stubble: a thin, weaker cover (133 / 134 occur in the vanilla fields)
        # stooks on the cut fields: hay-cock objects on a 24 m lattice, jittered
        srng = np.random.default_rng(abs(hash((round(x0), round(y0), 5))) % (2 ** 31))
        for sy_ in range(12, 2048, 24):
            for sx_ in range(12, 2048, 24):
                jx_, jy_ = sx_ + float(srng.uniform(-6, 6)), sy_ + float(srng.uniform(-6, 6))
                if cut_m[int(jy_), int(jx_)] and cut_m[max(0, int(jy_) - 5):int(jy_) + 6, max(0, int(jx_) - 5):int(jx_) + 6].all():
                    objs.append((SE.TAB_O, 'seno_copna', jx_, jy_, float(srng.random() * 6.28)))
    if rbuf is not None and rbuf['mask'].any():   # the road strips keep their own micro tiles, detail and grass (homesteads painted later win)
        m_ = rbuf['mask'] & (soil != 14)
        if sbuf is not None: m_ &= ~sbuf['mask']
        lay['hi'][m_] = rbuf['hi'][m_]; lay['det'][m_] = rbuf['det'][m_]; lay['grass'][m_] = rbuf['grass'][m_]
    if sbuf is not None and sbuf['mask'].any():   # the copied homesteads keep the micro tiles, detail and grass they came with
        m_ = sbuf['mask'] & (soil != 14)
        lay['hi'][m_] = sbuf['hi'][m_]; lay['det'][m_] = sbuf['det'][m_]; lay['grass'][m_] = sbuf['grass'][m_]
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
    if MUD[0] is not None: no_grass = no_grass | MUD[0]   # nor on the waterline mud (user, 4 Nov: the grass grew right to the water)
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
    # 27 Oct (user: objects, plants and fences must not stand on the roads): nothing within 1.5 m of a road strip
    # (houses, sheds and barns 4 m); the rail sections, gates in the front fences and telegraph posts are not affected
    if TKS.BUF.get('mask') is not None and TKS.BUF['mask'].any():
        rm = TKS.BUF['mask'] & np.isin(soil, (10, 11, 2, 3))   # the worn ground of the road, not the grass verge copied with it
        rm = MO.dilate(rm, 3) | MO.dilate(TKS.CORE_MASK, 3) if getattr(TKS, 'CORE_MASK', None) is not None else MO.dilate(rm, 3)
        rbig = MO.dilate(rm, 7)
        def _off(o):
            if o[1] in ('rail',) or o[1].startswith(('gates', 'kalitka')): return True
            px_, py_ = BF.pos(o)   # 14 Nov: the stone house and the church by the middle of their box, 9 / 7.6 m off the record
            xi, yi = int(min(2047, max(0, px_))), int(min(2047, max(0, py_)))
            if o[1].startswith(('fence', 'fpost')):   # fences only off the wheel tracks themselves (the front fences line the street)
                return TKS.CORE_MASK is None or not TKS.CORE_MASK[yi, xi]
            return not (rbig if o[1].startswith(('build', 'saray', 'farm')) else rm)[yi, xi]
        # 11 Nov (user: "check it all 1 to 1"): a traced building of the sheet that falls on the clearance band is pushed out of
        # it to the nearest clear spot (<= 8 m) instead of dropped - the sheet draws the houses right at the street
        from scipy import ndimage as _ndi_b
        _d, (_iy, _ix) = _ndi_b.distance_transform_edt(rbig, return_indices=True)
        moved = 0
        for k_, o in enumerate(objs):
            if not o[1].startswith(('build', 'saray', 'farm')): continue
            px_, py_ = BF.pos(o)
            xi, yi = int(min(2047, max(0, px_))), int(min(2047, max(0, py_)))
            if rbig[yi, xi] and _d[yi, xi] <= 8.0:
                objs[k_] = (o[0], o[1], float(_ix[yi, xi]) + (o[2] - px_), float(_iy[yi, xi]) + (o[3] - py_)) + tuple(o[4:]); moved += 1
        n0 = len(objs); objs = [o for o in objs if _off(o)]
        nf0 = 0
        if fx:
            X = np.concatenate(fx); Y = np.concatenate(fy); R = np.concatenate(fr); Tt = np.concatenate(ft)
            ok = ~rm[np.clip(Y.astype(int), 0, 2047), np.clip(X.astype(int), 0, 2047)]
            nf0 = int((~ok).sum()); fx, fy, fr, ft = [X[ok]], [Y[ok]], [R[ok]], [Tt[ok]]
        print('  road clearance: %d objects, %d plants dropped' % (n0 - len(objs), nf0), flush=True)
    if BLOCK and BLOCK.get('period_houses') and buildings:
        # 13 Nov (user: houses 1:1 with the sheet - "Yes, remove them"): the village filling (tools/settle.py, vstamps) put
        # houses along the streets where the sheet draws none; a house stands only on a building of the sheet (its traced
        # rectangle grown by 8 m); so does a barn / shed. Fences and yard objects are not touched.
        hm_ = Image.new('L', (2048, 2048), 0); hd_ = ImageDraw.Draw(hm_)
        for pp in buildings: hd_.polygon([tuple(q) for q in pp], fill=1)
        hm_ = MO.dilate(np.asarray(hm_) > 0, 17)
        n0 = len(objs)
        objs = [o for o in objs if not (o[1].startswith(('build', 'saray')) and 'builds.cfgpack' in o[0] and not hm_[int(min(2047, max(0, o[3]))), int(min(2047, max(0, o[2])))])]
        print('  houses / sheds with no building of the sheet under them: %d dropped' % (n0 - len(objs)), flush=True)
    if BLOCK and BLOCK.get('cleanup', True):
        # 13 Nov (user: "make sure nothing is colliding ... smoothen everything so it doesn't look out of pace, like settlements and
        # villages"): a last pass over everything placed. Measured on the built block (tools/cell_audit.py): houses standing in each
        # other, on the road or in the water, trees through roofs, on roads and in streams, fences and haystacks on the roadway, and -
        # since the houses follow the sheet one to one - fences, benches, wood piles and haystacks of yards whose house is gone.
        from scipy import ndimage as ndi_
        from scipy.spatial import cKDTree as KD_
        roadc_ = np.isin(cov, (ROAD, TRACK, RAIL)); roadm_ = roadc_ | np.isin(soil, (8, 9, 10, 11)); watc_ = cov == WATER
        def at_(m, x, y): return bool(m[int(min(2047, max(0, y))), int(min(2047, max(0, x)))])
        def isb_(o): return o[1].startswith(('build', 'saray', 'barn', 'izba', 'farm', 'church', 'windmill', 'mz_'))
        def rank_(o): return 0 if o[1].startswith(('church', 'windmill', 'mz_kosciol', 'mz_dzwonnica')) else 1 if o[1].startswith('build') else 2
        nb0_, nmv_, nob_, nor_, nfl_ = 0, 0, 0, 0, 0
        # (1) two buildings in each other: the shed / the later one goes. 14 Nov: by their boxes (tools/bldfoot.py; an overlap
        # deeper than a metre) - the test was 'middles under 7 m apart', and two 11 m log houses 10 m apart stood in each other
        def pairs_():
            B_ = [k for k, o in enumerate(objs) if isb_(o)]; drop_ = set()
            if len(B_) > 1:
                P_ = np.array([BF.centre(objs[k][2], objs[k][3], objs[k][4], objs[k][1]) for k in B_], np.float64)
                for i_, j_ in sorted(KD_(P_).query_pairs(22.0)):
                    a_, b_ = B_[i_], B_[j_]
                    if a_ in drop_ or b_ in drop_: continue
                    if math.hypot(P_[i_][0] - P_[j_][0], P_[i_][1] - P_[j_][1]) >= 7.0 and not BF.overlap(objs[a_], objs[b_], -0.5): continue
                    drop_.add(b_ if rank_(objs[b_]) >= rank_(objs[a_]) else a_)
            return drop_
        drop_ = pairs_(); nb0_ = len(drop_); objs = [o for k, o in enumerate(objs) if k not in drop_]
        # (2) a building on the roadway or at the water: to the nearest clear ground within 12 m (4 m off the road, 6 m off the water)
        bad_ = MO.dilate(roadc_, 9) | MO.dilate(watc_, 13)
        if bad_.any():
            d_, (iy_, ix_) = ndi_.distance_transform_edt(bad_, return_indices=True)
            for k, o in enumerate(objs):
                if not isb_(o) or o[1].startswith(('church', 'windmill', 'mz_kosciol', 'mz_dzwonnica')): continue
                px_, py_ = BF.pos(o)
                xi_, yi_ = int(min(2047, max(0, px_))), int(min(2047, max(0, py_)))
                if bad_[yi_, xi_] and d_[yi_, xi_] <= 12.0:
                    objs[k] = (o[0], o[1], float(ix_[yi_, xi_]) + 0.5 + (o[2] - px_), float(iy_[yi_, xi_]) + 0.5 + (o[3] - py_)) + tuple(o[4:]); nmv_ += 1
        # (2b) 14 Nov (user: "the vehicles drive into houses"): step 2 looks at the record's position only, and a house is 10-13 m
        # long (the stone house stands 9 m off its record): 1-13 % of the houses of a cell had a wall on a roadway (Radzymin MgE8
        # 182 of 1795; vanilla and Prokhorovka none). The whole box of the model (tools/bldfoot.py) keeps 2.5 m off every
        # road, track and rail pixel and off the water: pushed straight away from the nearest one, 12 m at most, to the
        # clearest spot found (a house between two lanes 14 m apart never gets 2.5 m off both, and stays if nothing is
        # better); a house that started on a roadway and found no ground off it is dropped (churches and windmills, the
        # sheet's landmarks, stay). The fences, benches and wood piles the moved house now covers go.
        nfp_, nfd_, nfn_ = 0, 0, 0
        rw_ = roadc_ | watc_
        if rw_.any():
            dr_, (jy_, jx_) = ndi_.distance_transform_edt(~rw_, return_indices=True)
            def worst_(x_, y_, r_, nd_):
                return min((float(dr_[int(min(2047, max(0, py_))), int(min(2047, max(0, px_)))]), px_, py_) for px_, py_ in BF.samples(x_, y_, r_, nd_))
            dn_, (ky_, kx_) = ndi_.distance_transform_edt(rw_, return_indices=True)     # on the road / in the water: the nearest clear ground
            def boxin_(x_, y_, o):
                return all(0 <= px_ < 2048 and 0 <= py_ < 2048 for px_, py_ in BF.rect(x_, y_, o[4], o[1]))
            def push_(o, normal_):
                """one push of at most 12 m; normal_: straight away from the road at the worst point of the box, else from that road
                pixel towards the middle of the box -> (clearance reached, capped at 2.5; minus the distance moved; x; y)"""
                x_, y_ = o[2], o[3]; w_ = worst_(x_, y_, o[4], o[1]); tot_ = 0.0; best_ = (w_[0], 0.0, x_, y_); in0_ = boxin_(x_, y_, o)
                for it_ in range(16):
                    yi_, xi_ = int(min(2047, max(0, w_[2]))), int(min(2047, max(0, w_[1])))
                    if not normal_:
                        mx_, my_ = BF.centre(x_, y_, o[4], o[1]); vx_, vy_ = mx_ - float(jx_[yi_, xi_]) - 0.5, my_ - float(jy_[yi_, xi_]) - 0.5
                    elif w_[0] > 0: vx_, vy_ = w_[1] - float(jx_[yi_, xi_]) - 0.5, w_[2] - float(jy_[yi_, xi_]) - 0.5      # straight away from the road
                    else: vx_, vy_ = float(kx_[yi_, xi_]) + 0.5 - w_[1], float(ky_[yi_, xi_]) + 0.5 - w_[2]               # that point is on it: straight off it
                    vl_ = math.hypot(vx_, vy_)
                    if vl_ < 0.5:
                        ax_, az_ = BF.axes(o[4]); (vx_, vy_), vl_ = (az_ if BF.long_x(o[1]) else ax_), 1.0     # across the model's short side
                    st_ = min(3.0, 2.5 - w_[0] + 0.5); x_ += vx_ / vl_ * st_; y_ += vy_ / vl_ * st_; tot_ += st_
                    w_ = worst_(x_, y_, o[4], o[1])
                    if w_[0] > best_[0] and 0 <= x_ < 2048 and 0 <= y_ < 2048 and (boxin_(x_, y_, o) or not in0_):   # a box that stood inside the cell stays inside (the neighbour's roads are not seen from here)
                        best_ = (w_[0], -math.hypot(x_ - o[2], y_ - o[3]), x_, y_)
                    if w_[0] >= 2.5 or tot_ >= 12.0: break
                return (min(best_[0], 2.5),) + best_[1:]
            gone_ = set(); moved_ = set()
            for k, o in enumerate(objs):
                if not isb_(o) or o[1].startswith(('church', 'windmill', 'mz_kosciol', 'mz_dzwonnica')): continue
                if worst_(o[2], o[3], o[4], o[1])[0] >= 2.5: continue
                bw_, _, x_, y_ = max(push_(o, True), push_(o, False))     # the clearer end of the two pushes, of two equally clear the shorter one
                if bw_ < 0.5: gone_.add(k); nfd_ += 1          # it started on the roadway / in the water and found no ground off it
                elif (x_, y_) != (o[2], o[3]): objs[k] = (o[0], o[1], float(x_), float(y_)) + tuple(o[4:]); nfp_ += 1; moved_.add(k)
                if 0.5 <= bw_ < 2.5: nfn_ += 1                 # off the roadway, but nearer than 2.5 m
            if moved_:   # yard things now under a moved house
                mv_ = [objs[k] for k in moved_]
                def under_(o):
                    if isb_(o) or not o[1].startswith(('fence', 'fpost', 'gates', 'kalitka', 'skameyka', 'drova', 'seno_', 'well', 'bochka', 'telega', 'mzp_')): return False
                    return any(abs(o[2] - b_[2]) < 30 and abs(o[3] - b_[3]) < 30 and BF.inside(b_[2], b_[3], b_[4], b_[1], o[2], o[3], 0.5) for b_ in mv_)
                gone_ |= {k for k, o in enumerate(objs) if under_(o)}
            if gone_: objs = [o for k, o in enumerate(objs) if k not in gone_]
            if nfp_:
                drop_ = pairs_(); nb0_ += len(drop_); objs = [o for k, o in enumerate(objs) if k not in drop_]
        # (3) yard things with no house left: fences, gates, benches, wood piles, haystacks further than 32 m from every building
        YARD_ = ('fence', 'fpost', 'gates', 'kalitka', 'skameyka', 'drova', 'seno_stog', 'seno_cyl', 'mzp_')
        Bp_ = np.array([BF.pos(o) for o in objs if isb_(o)], np.float64).reshape(-1, 2)
        kb_ = KD_(Bp_) if len(Bp_) else None
        def orphan_(o):
            if not o[1].startswith(YARD_) or o[1].startswith('seno_copna'): return False
            if kb_ is None: return True
            # 21 Nov: the plot fences of the WIG homesteads run 35 - 60 m back from the street - a fence keeps to 75 m
            # (21 Nov: and the fenced orchard plots of the sheet stand on their own - a fence keeps to 200 m)
            return kb_.query([o[2], o[3]], k=1)[0] > (200.0 if o[1].startswith(('fence', 'fpost', 'gates', 'kalitka', 'mzp_')) else 32.0)
        n0_ = len(objs); objs = [o for o in objs if not orphan_(o)]; nor_ = n0_ - len(objs)
        # (4) anything else on the roadway or in the water (the railway's own rails, gates and bridges stay)
        # 14 Nov (user: "some houses fences collide with roads"): a fence panel / gate is 2.6 m long and was tested at its middle
        # against the road's centre band only; now along its whole length against the worn road as painted (the copied road
        # strips' wheel tracks and verges of bare earth), with half a metre to spare
        wornr_ = roadc_.copy()
        # 21 Nov: the roadway and its wheel-track core only - the trampled verge (soils 2/3/10/11 of the copied strip) is where a
        # village front fence stands (settle._wig_plots keeps the fronts off it where it can; dropped panels left the plots open)
        if getattr(TKS, 'CORE_MASK', None) is not None: wornr_ |= TKS.CORE_MASK
        wornr_ = MO.dilate(wornr_, 3)
        def panel_(o):
            if not o[1].startswith(('fence', 'gates', 'kalitka', 'mzp_')): return at_(wornr_, o[2], o[3])
            a_ = o[4] - math.pi / 2; ux_, uy_ = math.sin(a_), math.cos(a_)
            return any(at_(wornr_, o[2] + ux_ * t_, o[3] + uy_ * t_) for t_ in (-1.3, -0.65, 0.0, 0.65, 1.3))
        def clash_(o):
            if isb_(o) or o[1].startswith(('rail', 'bridge', 'most')): return False
            if at_(watc_, o[2], o[3]): return True
            if o[1].startswith(('fence', 'fpost', 'gates', 'kalitka', 'mzp_')): return panel_(o)   # 21 Nov: the M19 fences and gates (mzp_*) too - the gates were tested against the wide road mask and went
            return at_(roadc_ if o[1].startswith('skameyka') else roadm_, o[2], o[3])
        n0_ = len(objs); objs = [o for o in objs if not clash_(o)]; nob_ = n0_ - len(objs)
        # (5) trees and big bushes on the roadway, in the water (reeds and waterside trees stay) or within 5 m of a building centre
        if fx:
            X = np.concatenate(fx); Y = np.concatenate(fy); R = np.concatenate(fr); Tt = np.concatenate(ft)
            tr_ = np.isin(Tt & 0xff, (0, 1, 2, 3, 4, 5, 8, 9, 10, 11, 14))
            xi_ = np.clip(X.astype(int), 0, 2047); yi_ = np.clip(Y.astype(int), 0, 2047)
            rm_ = tr_ & (roadc_[yi_, xi_] | watc_[yi_, xi_])
            if kb_ is not None and tr_.any():
                dd_, _ = kb_.query(np.c_[X, Y], k=1, distance_upper_bound=5.0); rm_ |= tr_ & np.isfinite(dd_)
            # 20 Nov 2026 (user: "There are often patches of vegetation inside buildings"): the 5 m round a building's centre missed
            # the ends of the long town houses and barns, and grass, reeds and small bushes were never taken off. Now every plant
            # on a building's footprint (+ 0.7 m) goes, and a tree / big bush within 2.5 m of its walls
            fpi_ = Image.new('L', (2048, 2048), 0); fpd_ = ImageDraw.Draw(fpi_); fti_ = Image.new('L', (2048, 2048), 0); ftd_ = ImageDraw.Draw(fti_)
            for o in objs:
                if isb_(o):
                    try: fpd_.polygon(BF.rect(o[2], o[3], o[4], o[1], 0.7), fill=1); ftd_.polygon(BF.rect(o[2], o[3], o[4], o[1], 2.5), fill=1)
                    except Exception: pass
            fpa_ = np.asarray(fpi_) > 0; fta_ = np.asarray(fti_) > 0
            rm_ |= fpa_[yi_, xi_] | (tr_ & fta_[yi_, xi_])
            nfl_ = int(rm_.sum()); ok = ~rm_; fx, fy, fr, ft = [X[ok]], [Y[ok]], [R[ok]], [Tt[ok]]
        print('  cleanup: %d buildings in each other dropped, %d moved off road / water (+ %d by their footprint, %d dropped, %d left nearer than 2.5 m), %d yard objects without a house, %d objects off road / water, %d trees' % (nb0_, nmv_, nfp_, nfd_, nfn_, nor_, nob_, nfl_), flush=True)
    # 14 Nov (audit): the height of every object record. The abs_hei models (tabs\builds_cap: stone houses, the church, the long
    # barns) need the absolute ground height at the record - vanilla: the decoded ground to 1 cm, a farm row 0.2 m lower, one
    # value for all the pieces of a set - and stand on a levelled pad (the ground under the box at that height, eased out over
    # 5 m). Others carry the game's fixed offsets.
    OFFS_ = {'izba1': 0.15, 'barn1': -0.2, 'windmill1': -0.2, 'well0': -0.2, 'bridge0': -0.3}
    npad_ = 0; padm_ = np.zeros(hpad_.shape, bool); padz_ = np.zeros(hpad_.shape, np.float32); padw_ = np.zeros(hpad_.shape, np.float32)
    def _zbox(o):
        R_ = BF.rect(o[2], o[3], o[4], o[1], 1.0); im_ = Image.new('L', (4096, 4096), 0)
        ImageDraw.Draw(im_).polygon([(px * 2.0, py * 2.0) for px, py in R_], fill=1); m_ = np.asarray(im_) > 0
        return m_, (float(np.median(hpad_[m_])) if m_.any() else float(hpad_[int(min(4095, max(0, o[3] * 2))), int(min(4095, max(0, o[2] * 2)))]))
    objs2_ = []
    for o in objs:
        if 'builds_cap' in o[0] and len(o) < 6:
            m_, z_ = _zbox(o)
            if o[1].startswith('farm'): z_ -= 0.2
            if m_.any():
                g_ = ndi_p.distance_transform_edt(~m_) if 'ndi_p' in dir() else None
                padm_ |= m_; padz_[m_] = z_ + (0.2 if o[1].startswith('farm') else 0.0); npad_ += 1
            objs2_.append(tuple(o[:5]) + (z_,))
        elif o[1] in OFFS_ and len(o) < 6: objs2_.append(tuple(o[:5]) + (OFFS_[o[1]],))
        else: objs2_.append(o)
    objs = objs2_
    if padm_.any():
        from scipy import ndimage as ndi_p
        dpad_, (iy_, ix_) = ndi_p.distance_transform_edt(~padm_, return_indices=True)
        w_ = np.clip(1.0 - dpad_ / 10.0, 0.0, 1.0)          # 10 samples = 5 m of easing round the pad
        hpad_ = hpad_ + w_ * (padz_[iy_, ix_] - hpad_)
        from pha6 import encode as pha6_encode
        open(path('hei_map'), 'wb').write(pha6_encode(np.clip(hpad_ / (MAXH / 65535.0), 0, 65535).astype(np.float32), hp, candidates=[0, 63, 52, 24, 36, 40, 3, 13]))
        print('  building pads: %d stone buildings / sets levelled, heights re-encoded' % npad_, flush=True)
    del hpad_
    na_ = sum(1 for o in objs if '_asm' in o[1])
    if na_: objs = SE.expand_assemblies(objs); print('  whole buildings written out from their parts: %d' % na_, flush=True)   # 14 Nov: after the last move
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
        # what stands on the ground (plants, buildings, fences) for the passability trees: vanilla marks those 4 m nodes
        # blocked and keeps the open ground between them free for the infantry to deploy on
        obst = np.zeros(soil.shape, bool)
        if fx:
            X_ = np.clip(np.concatenate(fx).astype(int), 0, 2047); Y_ = np.clip(np.concatenate(fy).astype(int), 0, 2047); obst[Y_, X_] = True
        # 14 Nov (user: "the vehicles drive into houses, they can be placed on houses in deployment mode"): a house was one
        # centre point grown to 11 x 11 m and only flagged, never priced (tools/pen.py). Now each building is the box of its
        # model (tools/bldfoot.py: turned by the record's heading, off-centre for the stone house and the church) plus 4 m -
        # with the 4 m leaves that are a quarter or more inside it that is the vanilla zone, the box + 5 m (a lone windmill
        # 5.9 x 6.0 m: 17 x 17 m; 0.57-0.75 % of a village cell) - with the kind of the building; the heavier kind is
        # drawn last where two zones meet. A zone's margin never lies on a road or within 2 m of one
        # (vanilla: 0.0-0.3 % of the road pixels are in a zone), the box itself + 1 m always stays closed.
        zim_ = Image.new('L', (2048, 2048), 0); cim_ = Image.new('L', (2048, 2048), 0); zd_ = ImageDraw.Draw(zim_); cd_ = ImageDraw.Draw(cim_)
        for o in sorted((o for o in objs if BF.is_building(o[0])), key=lambda o: BF.spec(o[1])[4]):
            zd_.polygon(BF.rect(o[2], o[3], o[4], o[1], 4.0), fill=BF.spec(o[1])[4]); cd_.polygon(BF.rect(o[2], o[3], o[4], o[1], 1.0), fill=1)
        for o in objs:
            if not BF.is_building(o[0]): obst[int(min(2047, max(0, o[3]))), int(min(2047, max(0, o[2])))] = True
        bld_kind = np.array(zim_, np.uint8); road_ = np.isin(cov, (ROAD, TRACK))
        bld_kind[MO.dilate(road_, 5) & ~(np.asarray(cim_) > 0)] = 0
        obst = MO.dilate(obst, 3) | (bld_kind > 0)   # plants / fences ~ 3 m
        # 14 Nov: the water (tools/pen.py): the ponds (1.25 m and deeper) close their leaves, their shallow rim and the rivers of
        # 3.8 m and more are forded at the vanilla price; the small streams stay out of the trees
        deep_ = shal_ = None
        if WPOOLS[0] and WDEPTH[0] is not None:
            wd_ = WDEPTH[0]; wet_ = (wd_ > 0.05) & (cov == WATER)
            deep_ = wet_ & (wd_ >= 1.25)
            rim_ = wet_ & ~deep_ & MO.dilate(deep_, 13)
            shal_ = rim_ | (wet_ & ~deep_ & RIVMASK[0]) if RIVMASK[0] is not None else rim_
            print('  pen water: deep %.2f ha, shallow %.2f ha' % (deep_.sum() / 1e4, shal_.sum() / 1e4), flush=True)
        pnodes = pen.tree(soil, slope, obst=obst, bld_kind=bld_kind, road=road_, deep=deep_, shallow=shal_)
        for cls in ['tanks', 'hums', 'cars', 'apcs']:
            open(path('pen_' + cls), 'wb').write(pen.build(soil, slope, pm[cls], rng, nodes=pnodes, cls=cls)); entries.append('pen_' + cls)
        del pnodes
        shutil.copy(os.path.join(tpl, 'aiplaces.cell.loc_def.bin'), path('aiplaces')); entries.append('aiplaces')
        bx_, by_ = to_block(x0, y0)
        open(path('landchar'), 'wb').write(landchar_from_template(os.path.join(tpl, 'landchar.cell.loc_def.bin'), cls_grid,
                                                                  (np.concatenate(fx), np.concatenate(fy), np.concatenate(ft)) if fx else None, objs, cov == WATER,
                                                                  bld_kind > 0, road_, seed=abs(int(round(bx_)) * 7919 + int(round(by_)) * 104729) % (2 ** 31))); entries.append('landchar')
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
    ap.add_argument('--roads1941', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'docs', 'm12_terrain', 'period', 'roads_1941.json'),
                    help='road network traced from the 1941 sheet (tools/roads_1941.py); replaces every OSM highway')
    ap.add_argument('--layout', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'docs', 'm11_prokhorovka', 'layout_10jul.json'))
    ap.add_argument('--ref', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'build', 'prokhorovka', 'ref'),
                    help='directory with the unpacked reference cells (pgd5, pge4, pgf6 of the Petropolye DLC terrain, see gen_prokh.cmd)')
    if BLOCK:   # block-config defaults (the explicit options still win)
        pdir = repo_path(BLOCK.get('period_dir', ''))
        ap.set_defaults(period=os.path.join(pdir, 'builtup_1941.png'), roads1941=os.path.join(pdir, 'roads_1941.json'),
                        layout=repo_path(BLOCK['layout']), style=repo_path(BLOCK.get('style', 'tools/prokh_style.json')),
                        ref=repo_path(os.path.join(BLOCK['build'], 'ref')))
    a = ap.parse_args()
    global WORKS, REF, FARMS, FIELDS43, VILLAGES43, WOODS43, ROADS43, PONDS, SINGLE_TRACK, OSM_BUILDINGS, OSM_BUILDINGS_IN
    if os.path.exists(a.layout):
        lay_ = json.load(open(a.layout, encoding='utf-8'))
        FARMS = [[tuple(q) for q in f['pts']] for f in lay_.get('farms', [])]
        FIELDS43 = [dict(f, pts=[tuple(q) for q in f['pts']]) for f in lay_.get('fields_1943', [])]
        VILLAGES43 = [[tuple(q) for q in v['pts']] for v in lay_.get('villages_1943', [])]
        WOODS43 = [dict(v, pts=[tuple(q) for q in v['pts']]) for v in lay_.get('woods_1943', [])]
        ROADS43 = [dict(r, pts=[tuple(q) for q in r['pts']]) for r in lay_.get('roads_1943', [])]
        PONDS = bool(lay_.get('ponds_1943', True))
        SINGLE_TRACK = bool(lay_.get('single_track', False))
        OSM_BUILDINGS = bool(lay_.get('osm_buildings', False))
        OSM_BUILDINGS_IN = [MplPath(v['pts']) for v in lay_.get('osm_buildings_1943', [])]
    refs = [os.path.join(a.ref, d) for d in ('pgd5', 'pge4', 'pgf6', 'pgf2', 'pgg1') if os.path.exists(os.path.join(a.ref, d, 'mat_map.cell.loc_def.bin'))]
    if not refs: sys.exit('no reference cells under %s - gen_prokh.cmd unpacks pgd5/pge4/pgf6 of the Petropolye terrain (Stalingrad-Donets DLC) there' % a.ref)
    REF = TR.Ref(refs, mius_dir=a.template)
    # villages and roads by example (tools/vstamps.py): homesteads and road strips cut from the same Petropolye cells
    import vstamps as VS, settle as SE_
    VLIB[0] = VS.Library(refs); VS.trim_wet(VLIB[0]); SE_.LIB = VLIB[0]
    import tracks as TKS_; TKS_.LIB = VLIB[0]
    if os.path.exists(a.layout):
        if not a.no_works:
            import works as W; WORKS = W.load(a.layout); print('field works loaded:', len(WORKS), 'trench / ditch pieces')
        else: WORKS = []
    style = json.load(open(a.style)); t0 = time.time()
    global PERIOD, ROADS1941
    if os.path.exists(a.period):
        PERIOD = np.asarray(Image.open(a.period).convert('L')); print('period built-up mask loaded:', PERIOD.shape, 'fraction %.3f' % (PERIOD > 0).mean())
    global WOODS_P, PERIOD_VILLAGES
    if BLOCK and BLOCK.get('period_woods'):
        WOODS_P = np.asarray(Image.open(repo_path(os.path.join(BLOCK['period_dir'], 'woods_1941.png'))).convert('L')); print('period woods loaded: fraction %.3f' % (WOODS_P > 0).mean())
    PERIOD_VILLAGES = bool(BLOCK and BLOCK.get('period_villages'))
    if BLOCK and BLOCK.get('period_cover') and os.path.exists(repo_path(os.path.join(BLOCK['period_dir'], 'cover_1941.png'))):
        COVER41[0] = np.asarray(Image.open(repo_path(os.path.join(BLOCK['period_dir'], 'cover_1941.png')))); COVER41_ON[0] = True
        sp_ = repo_path(os.path.join(BLOCK['period_dir'], 'sand_wig.png'))
        if os.path.exists(sp_): SAND41[0] = np.asarray(Image.open(sp_)) > 0; print('WIG sand loaded: %.2f%% of the block' % (100 * SAND41[0].mean()))
        ep_ = repo_path(os.path.join(BLOCK['period_dir'], 'earthworks_1941.json'))
        if os.path.exists(ep_): EARTH41[0] = json.load(open(ep_, encoding='utf-8'))['lines']; print('earthworks of the sheet loaded:', len(EARTH41[0]))
        wp_ = repo_path(os.path.join(BLOCK['period_dir'], 'wetmeadow_1941.png'))
        if os.path.exists(wp_): WETMEADOW41[0] = np.asarray(Image.open(wp_)) > 0; print('swampy meadow loaded: %.0f ha' % (WETMEADOW41[0].sum() * 4e-4))
        mp_ = repo_path(os.path.join(BLOCK['period_dir'], 'marsh_dash.png'))
        if os.path.exists(mp_): MARSHWOOD41[0] = (np.asarray(Image.open(mp_)) > 0) & (COVER41[0] == 1); print('swampy woods (marsh dashes in woods): %.0f ha' % (MARSHWOOD41[0].sum() * 4e-4))
        yp_ = repo_path(os.path.join(BLOCK['period_dir'], 'young_wig.png')); yd_ = repo_path(os.path.join(BLOCK['period_dir'], 'young_wig_density.png'))
        if os.path.exists(yp_) and os.path.exists(yd_):
            YOUNG41[0] = (np.asarray(Image.open(yp_)), np.asarray(Image.open(yd_))); print('WIG young growth / bushes loaded: %.2f%% of the block' % (100 * (YOUNG41[0][0] > 0).mean()))
    if BLOCK and os.path.exists(repo_path(os.path.join(BLOCK['period_dir'], 'relief_1941.json'))):
        RJ_ = json.load(open(repo_path(os.path.join(BLOCK['period_dir'], 'relief_1941.json')), encoding='utf-8'))
        RELIEF41[0] = RJ_.get('lines', [c['pts'] for c in RJ_['contours']])
        sj_ = repo_path(os.path.join(BLOCK['period_dir'], 'spots_1941.json'))
        SPOTS41[0] = [(q['x'], q['y'], q['h']) for q in (json.load(open(sj_, encoding='utf-8'))['spots'] if os.path.exists(sj_) else RJ_['spots'])]
    if BLOCK and os.path.exists(repo_path(os.path.join(BLOCK['period_dir'], 'field_parcels.npz'))):
        PARCELS[0] = np.load(repo_path(os.path.join(BLOCK['period_dir'], 'field_parcels.npz')))['lab']; print('field parcels loaded:', int(PARCELS[0].max()))
    if BLOCK and os.path.exists(repo_path(os.path.join(BLOCK['period_dir'], 'landmarks_1941.json'))):
        LANDMARKS41[0] = json.load(open(repo_path(os.path.join(BLOCK['period_dir'], 'landmarks_1941.json')), encoding='utf-8'))['landmarks']
        import collections as _co; print('sheet symbols loaded:', dict(_co.Counter(q['type'] for q in LANDMARKS41[0])))
    if BLOCK and os.path.exists(repo_path(os.path.join(BLOCK['period_dir'], 'bushes_1941.json'))):
        BUSHES41[0] = json.load(open(repo_path(os.path.join(BLOCK['period_dir'], 'bushes_1941.json')), encoding='utf-8'))['bushes']; print('single-tree signs loaded:', len(BUSHES41[0]))
        tp_ = repo_path(os.path.join(BLOCK['period_dir'], 'trees_1941.json'))
        if os.path.exists(tp_): TREES41[0] = json.load(open(tp_, encoding='utf-8'))['trees']; print('lone tree circles loaded:', len(TREES41[0]))
    if BLOCK and BLOCK.get('tree_rows') and os.path.exists(repo_path(os.path.join(BLOCK['period_dir'], BLOCK['tree_rows']))):
        TREE_ROWS[0] = json.load(open(repo_path(os.path.join(BLOCK['period_dir'], BLOCK['tree_rows'])), encoding='utf-8'))['rows']
    if BLOCK and BLOCK.get('wood_kind') and os.path.exists(repo_path(os.path.join(BLOCK['period_dir'], BLOCK['wood_kind']))):
        WOODKIND[0] = np.asarray(Image.open(repo_path(os.path.join(BLOCK['period_dir'], BLOCK['wood_kind']))))
    if BLOCK and BLOCK.get('opmap_sheet') and os.path.exists(repo_path(os.path.join(BLOCK['period_dir'], 'rkka_block2.png'))):
        _im = Image.open(repo_path(os.path.join(BLOCK['period_dir'], 'rkka_block2.png'))).convert('RGB')
        OPMAP_SHEET[0] = np.asarray(_im.resize((_im.size[0] // 2, _im.size[1] // 2), Image.LANCZOS)); del _im
        print('RKKA cover raster loaded:', COVER41[0].shape)
    if BLOCK and BLOCK.get('flora'):   # e.g. the Mazovian pine woods: pine rows of the flora table instead of the steppe oak / ash
        for k_, v_ in BLOCK['flora'].items(): FLORA[k_] = [tuple(x) for x in v_]
        for k_, v_ in BLOCK.get('density', {}).items(): DENSITY[k_] = float(v_)
    if os.path.exists(a.roads1941):
        ROADS1941 = json.load(open(a.roads1941, encoding='utf-8'))['roads']; print('1941 road network loaded:', len(ROADS1941), 'roads')
        if BLOCK:   # M16: hand corrections (tools/trace_edits.py)
            import trace_edits as TE_
            ROADS1941 = TE_.apply_roads(ROADS1941, TE_.load(repo_path(BLOCK['period_dir'])), int(ROWS * CELL / 2.0)); print('  after trace_edits:', len(ROADS1941), 'roads')
    os.makedirs(a.out, exist_ok=True); log = open(os.path.join(a.out, 'gen_prokh_log.txt'), 'a')
    class Tee:
        def write(self, s): sys.__stdout__.write(s); log.write(s)
        def flush(self): sys.__stdout__.flush(); log.flush()
    sys.stdout = Tee(); print('# prokh_gen', time.strftime('%Y-%m-%d %H:%M:%S'), sys.argv[1:])
    feats, places = load_osm(a.osm); print('osm features', len(feats), 'places', len(places), flush=True)
    feats = drop_modern(feats, a.layout)
    feats = period_settlement(feats)
    feats = period_cover(feats)
    feats = period_roads(feats) if ROADS1941 is not None else prune_roads(feats)   # 4 Nov: the roads of the 1941 sheet replace OSM's
    feats = meander_water(feats)
    places = places_1943(places, a.layout)
    pp_ = period_places()   # 12 Nov (1:1): the op-map names are the sheet's own labels, at the sheet's places (14 Nov: in Polish)
    if pp_ is not None:
        places = pp_; print('op-map names from the sheet:', len(places), '(%d with a Polish name)' % sum(1 for _, t, _k in places if t['name_en'] != textpack.translit(t['name'])))
    WPOOLS[0] = bool(BLOCK and BLOCK.get('period_cover') and BLOCK.get('water_model', 'pools') == 'pools')
    if WPOOLS[0]: feats = build_water_pools(feats, a.cells)
    else: build_water_levels(feats, a.cells)
    if BLOCK and BLOCK.get('rail_grade'): build_rail_grade(feats, a.cells)
    syms = ['0123456789!"#$%^&*()_+|\t=-~`[]{}:;"\'<>,.?/ \u2116ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz']
    eng = [('spec_syms_freq', syms), ('pe_poly_name', [POLY_NAME[0]]), ('pe_poly_country', [POLY_COUNTRY[0]])]
    rus = [('spec_syms_freq', syms), ('pe_poly_name', [POLY_NAME[1]]), ('pe_poly_country', [POLY_COUNTRY[1]])]
    for (_, t, key) in places:
        eng.append((key, [t.get('name_en') or textpack.translit(t['name'])])); rus.append((key, [t.get('name_ru') or t['name']]))
    for q_ in (LANDMARKS41[0] or []):   # the sheet's object abbreviations (fl., g. dv., piln. ...) as map text
        if q_['type'] in ('label', 'watermill') and q_.get('key'):
            en_, ru_ = pl_text(PL_ABBR[q_['rus']], q_['rus']) if (PL_NAMES and q_['rus'] in PL_ABBR) else (q_.get('eng') or textpack.translit(q_['rus']), q_['rus'])
            if PL_RUS_LATIN: ru_ = en_      # an abbreviation not in PL_ABBR: its transliteration in both packs (ASCII only)
            eng.append((q_['key'], [en_])); rus.append((q_['key'], [ru_]))
    if PL_NAMES:   # every glyph must exist in both locales' fonts: only ASCII is safe (see PL_NAMES above)
        bad_ = [(k, v) for k, vs in (eng + rus if PL_RUS_LATIN else eng) for v in vs if k not in ('spec_syms_freq', 'pe_poly_country') and any(ord(c) > 126 for c in v)]
        if bad_: sys.exit('non-ASCII place names in the text packs: %r' % bad_[:10])
    if not os.environ.get('MFO_NO_TEXT'):     # 19 Nov: tools/cells_parallel.ps1 - one of the parallel runs writes them
        textpack.write(os.path.join(a.out, POLY + '_text.loc_eng.textpack'), 'loc_eng', eng)
        textpack.write(os.path.join(a.out, POLY + '_text.loc_rus.textpack'), 'loc_rus', rus)
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

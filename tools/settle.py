"""Settlement generator - steppe street villages the way Graviteam builds them.

Reference cells: the Petropolye polygon (Stalingrad-Donets DLC, 1943 summer, Graviteam's newest generator) PgD5 / PgE4 /
PgF6 and the Mius-Front MgG3 (Stepanovka).  Petropolye measurements: homesteads 40-100 m apart along the street (median
65-80 m), house centre 7-25 m from the road edge (median 13), gable to the street; 1-3 sheds per house 16-24 m from it,
in an L round a yard of clay / trampled ground (soils 3 and 10); a CONTINUOUS front fence along the whole village street
with a gate at every house, side fences 40-60 m deep between the plots, almost no back fences; behind every yard a garden
plot as wide as the homestead spacing and 120-200 m deep - sunflowers (soil 7 + flora 17) or maize / potato rows (soil 15
+ flora 13), hedges of bushes along the plot borders (soil 13 band + flora 7/8), fruit trees (10) and fruit bushes (15)
near the houses; haystacks, firewood, benches; the kolkhoz yard apart from the village with long barns (farm0 / farm1).
The Psel hamlets of 1943 (Vasilyevka, Andreyevka, Mikhaylovka, Prelestnoye, Petrovka) were exactly such one-street valley
villages - houses on the landward side of the street, gardens running down to the river.

OpenStreetMap carries almost no footprints for them (Andreyevka: 1), so the homesteads are generated along the OSM streets
inside the residential polygons (trimmed to the 1941 built-up extent by prokh_gen); OSM footprints are kept.
Coordinates: cell pixels (1 px = 1 m), row 0 = south.
"""
import math, os, numpy as np
from PIL import Image, ImageDraw, ImageFilter
import morph as MO
class MplPath:
    """a polygon for point tests (no matplotlib here): contains_point with radius < 0 = at least -radius inside"""
    def __init__(self, pts): self.p = [tuple(q) for q in pts]
    def _in(self, x, y):
        c = False; P = self.p
        for i in range(len(P)):
            (x1, y1), (x2, y2) = P[i], P[i - 1]
            if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1: c = not c
        return c
    def contains_point(self, q, radius=0.0):
        if not self._in(q[0], q[1]): return False
        if radius >= 0: return True
        r = -radius; P = self.p
        for i in range(len(P)):
            (ax, ay), (bx, by) = P[i - 1], P[i]; dx, dy = bx - ax, by - ay; L2 = dx * dx + dy * dy or 1e-9
            t = max(0.0, min(1.0, ((q[0] - ax) * dx + (q[1] - ay) * dy) / L2))
            if math.hypot(q[0] - ax - t * dx, q[1] - ay - t * dy) < r: return False
        return True

import bldfoot as BF   # 14 Nov: a building record's heading is pi - the angle of the model's long side (bldfoot.heading), not the plain angle

TAB_BW = 'tabs\\builds_wood.cfgpack'; TAB_B = 'tabs\\builds.cfgpack'; TAB_BC = 'tabs\\builds_cap.cfgpack'; TAB_O = 'tabs\\objects.cfgpack'; TAB_F = 'tabs\\fences.cfgpack'; TAB_S = 'tabs\\structs.cfgpack'; TAB_P = 'tabs\\posts.cfgpack'
VILLAGE_SOIL = 10; CLAY = 3; FIELD = 6; FIELD_GREEN = 7; SAND = 5; LEAVES = 13; PLOUGH = 15
FL_SUNFL = 17; FL_CORN = 13; FL_BUSH = 7; FL_BUSH2 = 8; FL_GARDEN = 10; FL_CULTBUSH = 15

HOUSE_STYLE = ['vanilla']   # 17 Nov (M19): 'mazovia' (block.json house_style) - the Polish village of 1944 with the M19 models
MZ_HOUSES = (('mz_chata1', 0.36), ('mz_chata2', 0.14), ('mz_dom2', 0.18), ('mz_dom1', 0.16), ('izba1', 0.16))   # sources_houses.md:
                            # old thatched cottages 40-50 %, newer wooden houses 25-35 % (the brick ones stand in the town zones)

def mz(tab, node, hr, L=0.0, role='house'):
    """the M19 model for a vanilla pick, by role: house (a hut or the log house) -> a cottage / house of MZ_HOUSES; farm (a barn
    or a big shed off the road) -> a barn or the livestock building; yard (the outbuilding of a homestead); town -> the log
    town house. Leaves everything else - and every pick outside the mazovia style - as it is."""
    if HOUSE_STYLE[0] != 'mazovia': return tab, node
    if role == 'town' and node == 'build0': return TAB_BW, ('mz_podcien1' if hr.random() < 0.4 else 'mz_miasto1')
    if role == 'town': role = 'house'
    if role == 'house' and (node.startswith('build') and not node.startswith('build_') or node == 'izba1'):
        # now and then a village building instead of a farmhouse: the smithy, the fire station, the school (sources_houses.md:
        # "schools, shops, fire stations (remizy), manors"); the manor only on the largest plots (L = the symbol's length)
        v = hr.random()
        if v < 0.020: return TAB_BW, 'mz_kuznia1'
        if v < 0.032: return TAB_BW, 'mz_remiza1'
        if v < 0.044 and L >= 14.0: return TAB_BW, 'mz_szkola1'
        if v < 0.050 and L >= 20.0: return TAB_BW, 'mz_dwor1'
        u = hr.random(); acc = 0.0
        for nd, w in MZ_HOUSES:
            acc += w
            if u < acc: return TAB_BW, nd
        return TAB_BW, MZ_HOUSES[0][0]
    if role == 'town' and node == 'build0': return TAB_BW, 'mz_miasto1'
    if role == 'farm':
        if node == 'barn1' or (node.startswith('saray') and L >= 14.0): return TAB_BW, ('mz_stodola1' if hr.random() < 0.55 else 'mz_stodola2')
        if node.startswith('saray') and L >= 8.0: return TAB_BW, 'mz_obora1'
    if role == 'yard':
        if node == 'barn1': return TAB_BW, ('mz_stodola1' if hr.random() < 0.55 else 'mz_stodola2')
        if node.startswith('saray'):     # Benko: "second livestock building, pigsty, small granary (spichlerek); mound cellars, hay ricks"
            u = hr.random()
            if u < 0.20: return TAB_BW, 'mz_obora1'
            if u < 0.36: return TAB_BW, 'mz_chlew1'
            if u < 0.46: return TAB_BW, 'mz_spichlerz1'
            if u < 0.52: return TAB_BW, 'mz_piwnica1'
    if role == 'stack' and node.startswith('seno') and hr.random() < 0.4: return TAB_BW, 'mz_brog1'     # the roofed hay rick
    if role == 'well' and hr.random() < 0.7: return TAB_BW, 'mz_zuraw1'                                # the well sweep
    if role == 'cross' and hr.random() < 0.5: return TAB_BW, 'mz_kapliczka1'                           # the wayside shrine
    return tab, node

def mz_fence(node, hr, where='front'):
    """the fence of a yard in the mazovia style: picket (grey / limewashed) or wattle at the street, wattle / pole rails at the
    sides; the vanilla gate and wicket become the plank gate and the picket wicket"""
    if HOUSE_STYLE[0] != 'mazovia': return node
    if node == 'gates1': return 'mzp_brama'
    if node.startswith('kalitka'): return 'mzp_furtka'
    u = hr.random()
    if where == 'front': return 'mzp_szt' if u < 0.45 else ('mzp_sztw' if u < 0.6 else ('mzp_plot' if u < 0.9 else 'fence1a'))
    return 'mzp_plot' if u < 0.45 else ('mzp_zerdz' if u < 0.7 else ('fence1a' if u < 0.9 else 'fence3a'))

class Foot(list):
    """a building footprint (cell px) that knows where it was traced from: src 'wig_bld' = one WIG 1:25 000 building, placed
    one to one (wig_pick); anything else = a symbol of the RKKA sheet (a homestead)"""
    src = None
    role = None   # 21 Nov: 'house' (dwelling) / 'aux' (farm building) - allocated to the printed house count (WIG_operations layer)

# 19 Nov 2026 (M18, user: "further work on it with wig sheets"): the M19 models a WIG building can be, by role, with their box
# (local x = the long side). The sheet draws every building at its size (>= 7.5 m): the model whose box is nearest wins.
WIG_HOUSE = (('mz_chata1', 0.36), ('mz_chata2', 0.14), ('mz_dom2', 0.18), ('mz_dom1', 0.16), ('izba1', 0.16))
WIG_TOWN = (('mz_miasto2', 0.3), ('mz_miasto1', 0.25), ('mz_kamienica2', 0.2), ('mz_dom1', 0.15), ('mz_podcien1', 0.1))
WIG_CENTRE = (('mz_kamienica1', 0.45), ('mz_kamienica2', 0.3), ('mz_podcien1', 0.15), ('mz_miasto2', 0.1))   # by the market
TOWN_ZONES = []   # 19 Nov (block 'town_zones', block metres x0, y0, x1, y1): the built-up towns - their hatched WIG quarters are street fronts
WIG_FARM = (('mz_stodola1', 0.35), ('mz_stodola2', 0.3), ('mz_obora1', 0.25), ('mz_chlew1', 0.1))
WIG_SMALL = (('mz_chlew1', 0.4), ('mz_spichlerz1', 0.3), ('mz_obora1', 0.2), ('mz_piwnica1', 0.1))

def wig_pick(L, D, near, town, hr, dwell=False):
    """(table, node, pieces): the model for a WIG building L x D m; near = by a road, town = in a brick zone. A block longer than
    any model is a row: `pieces` models along its long side (town street fronts, long farm ranges)."""
    # town: 0 village, 1 in a town zone, 2 in a town centre (brick zone) - True / False still read as 1 / 0
    town = int(town)
    if near and not town and L >= 21.0 and D >= 12.5 and hr.random() < 0.5: return TAB_BW, 'mz_dwor1', 1
    if near and not town and 15.5 <= L <= 21.0 and 7.5 <= D <= 11.0 and hr.random() < 0.25: return TAB_BW, ('mz_szkola1' if L >= 17.0 else 'mz_remiza1'), 1
    if L <= 8.5 and D <= 6.5 and not (near and dwell): pool = WIG_SMALL   # (a sign allocated as a dwelling stays a house however small it is drawn)
    elif near: pool = (WIG_CENTRE if town >= 2 else WIG_TOWN) if town else WIG_HOUSE
    else: pool = WIG_FARM
    lmax = max(BF.spec(n)[0] for n, _ in pool)
    k = max(1, int(round(L / (lmax * 0.95)))) if L > lmax * 1.3 else 1
    Lp = L / k
    cost = []
    for n, w in pool:
        sx, sz = BF.spec(n)[:2]
        cost.append((abs(Lp - sx) + 0.7 * abs(D - sz)) / (0.5 + w))
    best = min(cost); ok = [(n, w) for (n, w), c in zip(pool, cost) if c <= best + 2.5]
    u = hr.random() * sum(w for _, w in ok); acc = 0.0
    for n, w in ok:
        acc += w
        if u <= acc: return TAB_BW, n, k
    return TAB_BW, ok[-1][0], k

def _town_level(bx, by):
    """0 village, 1 in a town (TOWN_ZONES), 2 in a town centre (BRICK_ZONES) - block metres"""
    if any(z_[0] <= bx <= z_[2] and z_[1] <= by <= z_[3] for z_ in BRICK_ZONES): return 2
    if any(z_[0] <= bx <= z_[2] and z_[1] <= by <= z_[3] for z_ in TOWN_ZONES): return 1
    return 0

ONE_PER_SYMBOL = [False]   # 13 Nov (M16, user: 'One house per symbol'): a traced building symbol of the sheet gets ONE building (a house by a road, else a barn), not a row every 12 m
LIB = None   # vstamps.Library (set by prokh_gen): homesteads copied from the Petropolye villages
BUF = {}     # per cell: the copied ground layers (mask, hi, det, grass) - prokh_gen writes them over texref's

def _h32(*v):
    h = 0
    for q in v: h = (h * 1000003 ^ (int(q) & 0xffffffff)) & 0xffffffff
    return (h ^ (h >> 15)) & 0x7fffffff

def _resample(pp, step):
    out = []; carry = 0.0
    for (ax, ay), (bx, by) in zip(pp, pp[1:]):
        L = math.hypot(bx - ax, by - ay)
        if L < 1e-6: continue
        ux, uy = (bx - ax) / L, (by - ay) / L; t = carry
        while t < L:
            out.append((ax + ux * t, ay + uy * t, ux, uy)); t += step
        carry = t - L
    return out

def _inside(x, y): return 0 <= x < 2048 and 0 <= y < 2048

_SD = {}
def _street_dir(lines, ROAD_C, TRACK_C, x, y, rmax=60.0):
    """the direction (standard angle) of the street nearest (x, y) within rmax m, or None; samples cached per lines list"""
    k = id(lines)
    if _SD.get('k') != k:
        from scipy.spatial import cKDTree
        P = [(px, py, ux, uy) for pp, col, dash, c in lines if c in (ROAD_C, TRACK_C) for px, py, ux, uy in _resample(pp, 3.0)]
        _SD.clear(); _SD.update(k=k, P=P, T=cKDTree([(p[0], p[1]) for p in P]) if P else None)
    if _SD['T'] is None: return None
    d, i = _SD['T'].query((x, y))
    if d > rmax: return None
    return math.atan2(_SD['P'][i][3], _SD['P'][i][2])

def _rect(cx, cy, ux, uy, half_w, d0, d1):
    """polygon from the street point (cx, cy), street direction (ux, uy): +-half_w along the street, d0..d1 along the normal"""
    nx, ny = -uy, ux
    return [(cx + ux * half_w + nx * d0, cy + uy * half_w + ny * d0), (cx - ux * half_w + nx * d0, cy - uy * half_w + ny * d0),
            (cx - ux * half_w + nx * d1, cy - uy * half_w + ny * d1), (cx + ux * half_w + nx * d1, cy + uy * half_w + ny * d1)]

def _fence(objs, a, b, node, blocked, gates=(), posts=True):
    ax, ay = a; bx, by = b
    L = math.hypot(bx - ax, by - ay)
    if L < 2: return
    ux, uy = (bx - ax) / L, (by - ay) / L; ang = math.atan2(ux, uy) + math.pi / 2   # vanilla fence heading convention
    if posts and _inside(ax, ay) and not blocked[int(ay), int(ax)]: objs.append((TAB_P, 'fpost2', ax, ay, ang))
    t = 1.3
    while t < L:
        x, y = ax + ux * t, ay + uy * t
        g = next((gt for gt in gates if abs(t - gt) < 2.2), None)
        if g is not None:
            if abs(t - g) < 1.3 and _inside(x, y) and not blocked[int(y), int(x)]: objs.append((TAB_F, mz_fence('gates1' if g >= 0 else 'kalitka2', None), x, y, ang))
        elif _inside(x, y) and not blocked[int(y), int(x)]: objs.append((TAB_F, node, x, y, ang))
        t += 2.6

def build(cov, soil, lines, buildings, slope2, rng, VIL, WATER_C, MARSH_C, ROAD_C, TRACK_C, RAIL_C, BUILDING_C, farm_mask=None, cell_seed=0, origin=(0.0, 0.0), vil_pad=None, pad=0, works_mask=None):
    """returns (objs, flora) and paints yards / gardens / hedges into `soil` in place.
    objs: (table, node, x, y, angle); flora: list of (x, y, flora_type)"""
    objs = []; flora = []; BUF.clear()
    vil = cov == VIL; bmask = cov == BUILDING_C
    if vil_pad is not None and pad > 0:   # village cover with a margin: the extent is the same on both sides of a cell border
        ext = MO.dilate(vil_pad, 41)[pad:-pad, pad:-pad] | MO.dilate(bmask, 41)
        plot_ok = MO.dilate(vil_pad, 81)[pad:-pad, pad:-pad]
    else:
        ext = MO.dilate(vil | bmask, 41)   # village extent + 20 m
        plot_ok = MO.dilate(vil, 81)   # plots may run 40 m past the polygon
    if not ext.any(): return objs, flora
    road_img = Image.new('L', (2048, 2048), 0); dr = ImageDraw.Draw(road_img); streets = []
    for (pp, col, dash, c) in lines:
        if c in (ROAD_C, TRACK_C):
            dr.line(pp, fill=255, width=9 if c == ROAD_C else 5, joint='curve')
            if c == ROAD_C or True: streets.append((pp, c))
        elif c == RAIL_C: dr.line(pp, fill=255, width=56, joint='curve')   # 26 Oct (user: a garden plot on the embankment): no yard, plot or hedge within ~33 m of a track
    road = np.asarray(road_img) > 0
    road_y = MO.dilate(road, 5)   # 14 Nov (user: "some houses fences collide with roads"): the worn strip painted along a line is wider than the line drawn here - a yard ends 2 m further back
    near_road = MO.dilate(np.asarray(road_img) > 0, 11)
    sym_road = None
    if ONE_PER_SYMBOL[0]:   # distance (m) to the nearest road / track line (not the railway): a house stands by a road, a barn behind
        from scipy import ndimage as _ndi
        # a main road is drawn on the sheet as a wide double line and a house symbol beside it lies outside the casing:
        # its distance counts 15 m less than to a track / lane (the review of 13 Nov: houses along the main roads were barns)
        ri_ = Image.new('L', (2048, 2048), 0); dri_ = ImageDraw.Draw(ri_); rm_ = Image.new('L', (2048, 2048), 0); drm_ = ImageDraw.Draw(rm_)
        for (pp, col, dash, c) in lines:
            if c == TRACK_C: dri_.line(pp, fill=255, width=3, joint='curve')
            elif c == ROAD_C: drm_.line(pp, fill=255, width=3, joint='curve')
        sym_road = np.minimum(_ndi.distance_transform_edt(np.asarray(ri_) == 0), np.maximum(0.0, _ndi.distance_transform_edt(np.asarray(rm_) == 0) - 15.0))
    wet = (cov == WATER_C) | (cov == MARSH_C)
    wet_near = MO.dilate(wet, 41)
    blocked = near_road | wet_near | (slope2 > 0.12)
    if works_mask is not None: blocked |= works_mask   # no houses, sheds or fences on the trenches / the anti-tank ditch
    blocked |= MO.dilate(bmask, 41)   # 20 m off the OSM buildings
    if farm_mask is not None: blocked |= farm_mask
    taken_img = Image.new('L', (2048, 2048), 0); dtk = ImageDraw.Draw(taken_img)   # homestead footprints already used (drawn, not re-rasterised per house)
    yard = Image.new('L', (2048, 2048), 0); dy = ImageDraw.Draw(yard)          # 1 = clay yard, 2 = trampled village ground
    gard = Image.new('L', (2048, 2048), 0); dg = ImageDraw.Draw(gard)          # garden pattern id
    hedge = Image.new('L', (2048, 2048), 0); dh = ImageDraw.Draw(hedge)        # hedge bands (soil 13 + bushes)
    yard_blk = [None]; hs_list = []; town_rd = [None, None]
    trod_img = Image.new('L', (2048, 2048), 0); dtr = ImageDraw.Draw(trod_img)   # trodden ground of the sheet homesteads: round the house, the way to the gate
    hatch_ = []   # 21 Nov: the hatched orchard / yard plots of the WIG sheet outside the towns (cell px polygons)
    wigp_ = []    # 21 Nov: the WIG buildings placed: (objs index, x, y, angle, door flipped, dwelling)
    # --- 1. OSM footprints (Prokhorovka town, a few hamlets) kept as they are, with a yard
    # the WIG buildings first: the town quarters around them fill in and keep clear of them
    for pp in sorted(buildings, key=lambda b_: 0 if getattr(b_, 'src', None) == 'wig_bld' else 1):
        src_ = getattr(pp, 'src', None); role0_ = getattr(pp, 'role', None)   # (pp[:-1] below is a plain list: read them first)
        if len(pp) > 1 and pp[0] == pp[-1]: pp = pp[:-1]
        if len(pp) < 3: continue
        cx = sum(p[0] for p in pp) / len(pp); cy = sum(p[1] for p in pp) / len(pp)
        if not _inside(cx, cy): continue
        best = max(zip(pp, pp[1:]), key=lambda e: math.hypot(e[1][0] - e[0][0], e[1][1] - e[0][1]))
        ang = math.atan2(best[1][1] - best[0][1], best[1][0] - best[0][0])
        area = abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pp, pp[1:] + pp[:1]))) / 2
        # 11 Nov (user: "check it all 1 to 1"): a traced block longer than one house (the sheet's long fire-resistant blocks, the
        # rows of a town quarter) gets a row of houses along its long side, one every 12 m, so its length on the ground matches
        L_ = math.hypot(best[1][0] - best[0][0], best[1][1] - best[0][1]); D_ = area / max(L_, 1.0)
        if src_ == 'wig_hatch' and ONE_PER_SYMBOL[0] and not _town_level(cx + origin[0], cy + origin[1]):
            # 21 Nov 2026 (WIG keys 1931 #93-94, 1920 #68; the sheet inventory of Downloads\WIG_operations\mapping): outside the
            # towns a diagonally hatched shape beside the black buildings is the farmstead's orchard / yard plot, not a building
            # and not a built-up quarter. It becomes a fenced orchard plot (_wig_plots); only the black shapes are buildings.
            hatch_.append(list(pp)); continue
        if src_ == 'wig_hatch' and ONE_PER_SYMBOL[0] and L_ <= 26.0 and D_ <= 18.0:
            src_ = 'wig_bld'   # 20 Nov 2026: a hatched shape the size of a building is a wooden building of the sheet - one model on it (towns only since 21 Nov)
        if src_ == 'wig_bld' and ONE_PER_SYMBOL[0]:
            # 19 Nov 2026 (M18): a building of the WIG sheet stands where it is drawn, as drawn - the model nearest its size, its
            # long side along the block's, the door side to the nearest road; a row block becomes a row of models. No
            # invented outbuildings: the sheet draws the barns and sheds too.
            hr = np.random.default_rng(_h32(round(cx + origin[0]), round(cy + origin[1]), 1931))
            qs_ = list(pp) + [((a_[0] + b_[0]) / 2.0, (a_[1] + b_[1]) / 2.0) for a_, b_ in zip(pp, pp[1:] + pp[:1])]
            dr_ = min(float(sym_road[int(min(2047, max(0, q_[1]))), int(min(2047, max(0, q_[0])))]) for q_ in qs_) if sym_road is not None else 0.0
            town_ = _town_level(cx + origin[0], cy + origin[1])
            role_ = role0_
            near_ = (role_ == 'house') if role_ in ('house', 'aux') else dr_ <= 14.0   # 21 Nov: the sheet's allocation decides dwelling / farm building where it is given
            if L_ < 1.3 * D_:
                # 21 Nov (user: "some buildings still sit sideways even though they are drawn perfectly"): a sign drawn nearly square
                # has no long side to follow, and the longest traced edge turned the (long, narrow) model either way. The Mazovian
                # farmstead decides it: the house gable-end to the street, a barn / farm building along it, closing the yard.
                sd_ = _street_dir(lines, ROAD_C, TRACK_C, cx, cy)
                if sd_ is not None: ang = sd_ + (math.pi / 2 if near_ else 0.0)
            tab_, node_, k_ = wig_pick(L_, D_, near_, town_, hr, dwell=(role_ == 'house'))
            ux_, uy_ = math.cos(ang), math.sin(ang)
            for q_ in range(k_):
                o_ = (q_ - (k_ - 1) / 2.0) * (L_ / k_)
                px_, py_ = cx + ux_ * o_, cy + uy_ * o_
                if q_ > 0 and k_ > 1 and not town_ and node_ in dict(WIG_HOUSE): tab_, node_, _k = wig_pick(L_ / k_, D_, False, False, hr)   # a house with its barn under one roof line
                r0_ = BF.heading(node_, ang); r1_ = BF.heading(node_, ang + math.pi)
                if sym_road is not None:   # the door (local +z) to the road
                    def _dz(r_):
                        zx_, zy_ = math.sin(r_), math.cos(r_)
                        return float(sym_road[int(min(2047, max(0, py_ + zy_ * 9.0))), int(min(2047, max(0, px_ + zx_ * 9.0)))])
                    rot_ = r0_ if _dz(r0_) <= _dz(r1_) else r1_
                else: rot_ = r0_
                objs.append((tab_, node_) + BF.origin_for(px_, py_, rot_, node_) + (rot_,))
                wigp_.append((len(objs) - 1, px_, py_, ang, rot_ != r0_, near_ and role_ != 'aux'))
                dtr.ellipse([px_ - 5, py_ - 5, px_ + 5, py_ + 5], fill=255)
            if near_: dy.ellipse([cx - 9, cy - 9, cx + 9, cy + 9], fill=2)
            continue
        if src_ == 'wig_hatch' and ONE_PER_SYMBOL[0]:
            # 20 Nov 2026 (user: "it has to be 100% like detailed maps"): a hatched quarter of the WIG sheet (wooden buildings
            # drawn as one shape) is built up along the streets it borders, as the sheet's quarters are drawn: on every side of the
            # quarter with a street outside it a row of houses, the front wall 1 - 2.5 m behind the drawn edge, eaves to the
            # street, the door to it; 0.3 - 1.5 m apart in a town, 2 - 6 m in a village. Sheds in the yards behind, square to the
            # quarter. A quarter with no street at any side: its side nearest a road. (It was cut into 42 x 30 m plots, each built
            # towards its own nearest street - houses every way inside the quarters.) No house where a WIG building stands.
            lvl_ = _town_level(cx + origin[0], cy + origin[1])
            hr = np.random.default_rng(_h32(round(cx + origin[0]), round(cy + origin[1]), 1944))
            if town_rd[0] is None:      # distance (m) from the edge of the nearest road / street
                from scipy import ndimage as _ndi
                town_rd[0] = _ndi.distance_transform_edt(~road); town_rd[1] = None
            RD_ = town_rd[0]
            def _rd(px_, py_): return float(RD_[int(min(2047, max(0, py_))), int(min(2047, max(0, px_)))])
            plot_ = MplPath(list(pp)); ring_ = list(pp)
            sides_ = []
            for a_, b_ in zip(ring_, ring_[1:] + ring_[:1]):
                ex_, ey_ = b_[0] - a_[0], b_[1] - a_[1]; le_ = math.hypot(ex_, ey_)
                if le_ < 8.0: continue
                gx_, gy_ = ex_ / le_, ey_ / le_; fx_, fy_ = gy_, -gx_
                mx_, my_ = (a_[0] + b_[0]) / 2.0, (a_[1] + b_[1]) / 2.0
                if (mx_ - cx) * fx_ + (my_ - cy) * fy_ < 0: fx_, fy_ = -fx_, -fy_          # outward
                ds_ = [_rd(a_[0] + gx_ * t + fx_ * 4.0, a_[1] + gy_ * t + fy_ * 4.0) for t in np.linspace(0.15, 0.85, 6) * le_]
                sides_.append((float(np.mean([d <= 9.0 for d in ds_])), float(np.median(ds_)), a_, (gx_, gy_), (fx_, fy_), le_))
            street_ = [s_ for s_ in sides_ if s_[0] >= 0.5]
            if not street_ and sides_: street_ = [min(sides_, key=lambda s_: s_[1])]
            pool_ = WIG_CENTRE if lvl_ >= 2 else (WIG_TOWN if lvl_ else WIG_HOUSE)
            backs_ = []
            for _, _, a_, (gx_, gy_), (fx_, fy_), le_ in sorted(street_, key=lambda s_: -s_[5]):
                fang_ = math.atan2(gy_, gx_); t_ = hr.uniform(0.3, 1.5)
                while t_ < le_ - 6.0:
                    u_ = hr.random() * sum(w for _, w in pool_); acc_ = 0.0; node_ = pool_[-1][0]
                    for n_, w_ in pool_:
                        acc_ += w_
                        if u_ <= acc_: node_ = n_; break
                    sx_, sz_ = BF.spec(node_)[:2]
                    if t_ + sx_ > le_ + 0.5:      # the last one: the narrower house if the wider will not fit
                        node_ = min((n_ for n_, _ in pool_), key=lambda n_: BF.spec(n_)[0]); sx_, sz_ = BF.spec(node_)[:2]
                        if t_ + sx_ > le_ + 0.5: break
                    back_ = hr.uniform(1.0, 2.5) + sz_ / 2.0
                    px_ = a_[0] + gx_ * (t_ + sx_ / 2.0) - fx_ * back_; py_ = a_[1] + gy_ * (t_ + sx_ / 2.0) - fy_ * back_
                    r0_ = BF.heading(node_, fang_); r1_ = BF.heading(node_, fang_ + math.pi)
                    rot_ = r0_ if (math.sin(r0_) * fx_ + math.cos(r0_) * fy_) > 0 else r1_      # the door side (local +z) to the street
                    rec_ = (TAB_BW, node_) + BF.origin_for(px_, py_, rot_, node_) + (rot_,)
                    cs_ = BF.rect(rec_[2], rec_[3], rot_, node_)
                    ok_ = _inside(px_, py_) and plot_.contains_point((px_, py_), radius=-1.0) and min(_rd(q_[0], q_[1]) for q_ in cs_) >= 0.5
                    if ok_ and not any(BF.is_building(o_[0]) and BF.overlap(rec_, o_, 0.1) for o_ in objs if abs(o_[2] - px_) < 30.0 and abs(o_[3] - py_) < 30.0):
                        objs.append(rec_); dtr.ellipse([px_ - 5, py_ - 5, px_ + 5, py_ + 5], fill=255)
                        backs_.append((px_ - fx_ * (sz_ / 2.0 + 6.0), py_ - fy_ * (sz_ / 2.0 + 6.0), fang_))
                    t_ += sx_ + (hr.uniform(0.3, 1.5) if lvl_ else hr.uniform(2.0, 6.0))
            for bx_, by_, fang_ in backs_:      # the yards behind: a shed or a woodshed behind every other house
                if hr.random() > 0.5: continue
                nd_ = ['mz_obora1', 'mz_chlew1', 'saray1', 'mz_spichlerz1'][int(hr.integers(0, 4))]; tb_ = TAB_B if nd_.startswith('saray') else TAB_BW
                r_ = BF.heading(nd_, fang_ + (math.pi if hr.random() < 0.5 else 0.0))
                if not plot_.contains_point((bx_, by_), radius=-2.0): continue
                rec_ = (tb_, nd_) + BF.origin_for(bx_, by_, r_, nd_) + (r_,)
                if _inside(bx_, by_) and not any(BF.is_building(o_[0]) and BF.overlap(rec_, o_, 0.6) for o_ in objs if abs(o_[2] - bx_) < 30.0 and abs(o_[3] - by_) < 30.0): objs.append(rec_)
            dy.polygon(list(pp), fill=2)
            continue
        k_ = max(1, int(round(L_ / 12.0))) if L_ > 18.0 else 1
        ux_, uy_ = math.cos(ang), math.sin(ang); nx_, ny_ = -uy_, ux_
        rows_ = (-D_ / 4, D_ / 4) if (D_ > 14.0 and L_ > 18.0) else (0.0,)   # a deep block: two rows, back to back
        if ONE_PER_SYMBOL[0]:
            # the sheet draws a building symbol larger than the house (1:50 000): one building at its centre along its long
            # side (user: 'no need for barn'); a house when the symbol stands by a road, else a barn (user: 'if its near any road its house if not its a barn')
            # measured from the symbol's nearest side (its corners and side midpoints): the road on the sheet is drawn wide,
            # so a house symbol beside it has its centre 30-50 m from the road's centre line, its near side within 20 m
            if sym_road is not None:
                qs_ = list(pp) + [((a_[0] + b_[0]) / 2.0, (a_[1] + b_[1]) / 2.0) for a_, b_ in zip(pp, pp[1:] + pp[:1])]
                dr_ = min(sym_road[int(min(2047, max(0, q_[1]))), int(min(2047, max(0, q_[0])))] for q_ in qs_)
            else: dr_ = 0.0
            # 14 Nov (user: "The villages look bare and lifeless, there are multiple buildings that are different shapes and sizes on wig
            # maps, also different types of buildings while in game its all shacks"): the symbol becomes a HOMESTEAD. The main
            # building is chosen by the symbol's size and place from every building the game has (three wooden houses, the big
            # log house, the stone houses, the long farm buildings, the barn, the sheds), the larger symbols get one or two
            # outbuildings at the back, and the yard is fenced with a gate to the road and furnished (wood pile, bench,
            # haystack, a well now and then, garden trees). Seeded by the symbol's place in the block, so both cells of a
            # border agree.
            hr = np.random.default_rng(_h32(round(cx + origin[0]), round(cy + origin[1]), 977))
            ux_, uy_ = math.cos(ang), math.sin(ang); nx_, ny_ = -uy_, ux_
            def _sr(px_, py_): return float(sym_road[int(min(2047, max(0, py_))), int(min(2047, max(0, px_)))]) if sym_road is not None else 0.0
            hw_ = min(max(L_ / 2.0 + 2.0, 9.0), 26.0); hd_ = min(max(D_ / 2.0 + 2.0, 8.0), 22.0)
            # the front: the side of the symbol that looks at the nearest road
            cands_ = [((nx_, ny_), hd_, (ux_, uy_), hw_), ((-nx_, -ny_), hd_, (ux_, uy_), hw_), ((ux_, uy_), hw_, (nx_, ny_), hd_), ((-ux_, -uy_), hw_, (nx_, ny_), hd_)]
            (fx_, fy_), ef_, (gx_, gy_), eg_ = min(cands_, key=lambda c_: _sr(cx + c_[0][0] * c_[1], cy + c_[0][1] * c_[1]))
            def _lim(dx_, dy_, e_):   # the yard ends 2 m short of a road
                t_ = 2.0
                while t_ < e_:
                    if road_y[int(min(2047, max(0, cy + dy_ * t_))), int(min(2047, max(0, cx + dx_ * t_)))]: return max(4.0, t_ - 2.0)
                    t_ += 1.0
                return e_
            ef_ = min(_lim(fx_, fy_, ef_), _lim(-fx_, -fy_, ef_)); eg_ = min(_lim(gx_, gy_, eg_), _lim(-gx_, -gy_, eg_))
            near_ = dr_ <= 20.0; pk_ = hr.random(); tab_ = TAB_B; hb_ = []
            gxb_, gyb_ = cx + origin[0], cy + origin[1]; town_ = any(z_[0] <= gxb_ <= z_[2] and z_[1] <= gyb_ <= z_[3] for z_ in BRICK_ZONES)
            def _clr(px_, py_, r_=6.5): return all(math.hypot(px_ - q_[0], py_ - q_[1]) >= r_ for q_ in hb_)
            if not near_:   # off the road: a farm building
                if L_ >= 46.0: tab_, node_ = TAB_BC, 'farm_asm%d' % min(4, max(2, int(round((L_ - 6.7) / 9.0))))   # the long barn, whole (expand_assemblies)
                elif L_ >= 30.0 and pk_ < 0.5: tab_, node_ = TAB_BW, 'barn1'
                else: node_ = 'saray%d' % hr.integers(0, 4)
            # 14 Nov: brick only where it stood - the blocks of the two old town centres (Okuniew, Stanislawow: market squares with
            # masonry houses); the game's brick buildings are 26 - 28 m long, so the symbol must be that long. Elsewhere the
            # Mazovian village of 1944 is timber.
            elif town_ and L_ >= 24.0 and pk_ < 0.50: tab_, node_ = TAB_BC, ('build_asm_brick2' if pk_ < 0.20 else 'build_asm_hall')
            elif town_ and pk_ < 0.55: node_ = 'build0'   # the plastered house of a small town
            elif pk_ < 0.50 and area >= 700.0: tab_, node_ = TAB_BW, 'izba1'                                  # the big log house
            else: node_ = 'build%d' % hr.integers(0, 4)
            tab_, node_ = mz(tab_, node_, hr, L_, 'farm' if not near_ else ('town' if town_ else 'house'))   # 17 Nov (M19)
            # 14 Nov (user: "the vehicles drive into houses"): the house was written with the plain angle of the symbol, which the
            # game reads mirrored (houses a median 27 deg off their own fences, corners in the street), and the stone house
            # build_cap0, whose body stands 9 m off its record, stood beside its symbol. Now the model's long side lies along
            # the symbol's, the middle of its box on the spot, and its front wall stays 3 m inside the yard's road end.
            rot_ = BF.heading(node_, ang)
            if node_ == 'build_cap0' and not all(0.0 <= v_ < 2048.0 for v_ in BF.origin_for(cx, cy, rot_, node_)): node_ = 'build_cap1'; rot_ = BF.heading(node_, ang)   # its record would fall outside the cell: the centred stone house
            dep_ = BF.half(node_, abs(fx_ * ux_ + fy_ * uy_) > 0.5)   # half the house along the way to the road
            sh_ = max(0.0, min(8.0, ef_ - 9.0, ef_ - dep_ - 3.0)) if near_ else 0.0   # the house stands at the road end of its yard
            hx_, hy_ = cx + fx_ * sh_, cy + fy_ * sh_
            objs.append((tab_, node_) + BF.origin_for(hx_, hy_, rot_, node_) + (rot_,)); hb_.append((hx_, hy_)); dtr.ellipse([hx_ - 6, hy_ - 6, hx_ + 6, hy_ + 6], fill=255)
            # 'blocked' keeps 20 m round every building of the sheet and 5 m off the roads clear - made for the street filling; a yard's
            # own sheds and fences stand exactly there. They keep off the roadway, the water and the field works only.
            if yard_blk[0] is None: yard_blk[0] = road_y | wet | (works_mask if works_mask is not None else False)
            blk_ = yard_blk[0]
            def _free(px_, py_): return _inside(px_, py_) and not blk_[int(py_), int(px_)]
            s1_ = 1.0 if hr.random() < 0.5 else -1.0
            if area >= 500.0 and near_:   # outbuilding in a back corner of the yard
                ox_, oy_ = cx - fx_ * max(4.0, ef_ - 7.0) + gx_ * s1_ * max(0.0, eg_ - 8.0), cy - fy_ * max(4.0, ef_ - 7.0) + gy_ * s1_ * max(0.0, eg_ - 8.0)
                if _free(ox_, oy_) and math.hypot(ox_ - hx_, oy_ - hy_) >= 11.0:
                    hb_.append((ox_, oy_))
                    if area >= 1800.0 and hr.random() < 0.4:
                        tb_, nd_ = mz(TAB_BW, 'barn1', hr, 0.0, 'yard')
                        objs.append((tb_, nd_, ox_, oy_, BF.heading(nd_, ang + (hr.random() - 0.5) * 0.12)))
                    else:
                        tb_, nd_ = mz(TAB_B, 'saray%d' % hr.integers(0, 4), hr, 0.0, 'yard')
                        objs.append((tb_, nd_, ox_, oy_, BF.heading(nd_, ang + (0.0 if hr.random() < 0.5 else math.pi / 2) + (hr.random() - 0.5) * 0.12)))
                    if hr.random() < 0.6: objs.append((TAB_O, 'drova', ox_ + fx_ * 7.0, oy_ + fy_ * 7.0, ang))
            if area >= 1400.0 and near_:   # a second one on the other side
                ox_, oy_ = cx - fx_ * 1.0 - gx_ * s1_ * max(0.0, eg_ - 7.0), cy - fy_ * 1.0 - gy_ * s1_ * max(0.0, eg_ - 7.0)
                if _free(ox_, oy_) and _clr(ox_, oy_, 11.0):
                    nd_ = 'saray%d' % hr.integers(0, 4)
                    hb_.append((ox_, oy_)); objs.append((TAB_B, nd_, ox_, oy_, BF.heading(nd_, ang + math.pi / 2 + (hr.random() - 0.5) * 0.12)))
            if near_:
                # the fence: front with a gate, both sides, the back now and then
                fn_ = mz_fence(['fence2a', 'fence2a', 'fence2a', 'fence4a', 'fence1a', 'fence3a'][int(hr.integers(0, 6))], hr, 'front')
                c00 = (cx + fx_ * ef_ - gx_ * eg_, cy + fy_ * ef_ - gy_ * eg_); c01 = (cx + fx_ * ef_ + gx_ * eg_, cy + fy_ * ef_ + gy_ * eg_)
                c10 = (cx - fx_ * ef_ - gx_ * eg_, cy - fy_ * ef_ - gy_ * eg_); c11 = (cx - fx_ * ef_ + gx_ * eg_, cy - fy_ * ef_ + gy_ * eg_)
                hs_list.append((len(hs_list) + 1, c00, c01, c10, c11, fn_, eg_ + s1_ * min(7.0, max(0.0, eg_ - 4.0)), hr.random() < 0.9, hr.random() < 0.9, hr.random() < 0.35))
                gxm_, gym_ = (c00[0] + c01[0]) / 2 + gx_ * s1_ * min(7.0, max(0.0, eg_ - 4.0)), (c00[1] + c01[1]) / 2 + gy_ * s1_ * min(7.0, max(0.0, eg_ - 4.0))
                dtr.line([(hx_, hy_), (gxm_, gym_)], fill=255, width=4)   # the trodden way from the door to the gate
                if hr.random() < 0.5: objs.append((TAB_O, 'skameyka%d' % (1 + hr.integers(0, 2)), hx_ + fx_ * 5.5 + gx_ * 4.0, hy_ + fy_ * 5.5 + gy_ * 4.0, math.atan2(gy_, gx_)))
                sx_, sy_ = cx - fx_ * (ef_ - 4.0) - gx_ * s1_ * (eg_ - 5.0), cy - fy_ * (ef_ - 4.0) - gy_ * s1_ * (eg_ - 5.0)
                if hr.random() < 0.5 and _clr(sx_, sy_): objs.append(mz(TAB_O, ['seno_stog', 'seno_stog', 'seno_copna'][int(hr.integers(0, 3))], hr, 0.0, 'stack') + (sx_, sy_, float(hr.random() * 6.28)))
                if hr.integers(0, 6) == 0: objs.append(mz(TAB_S, 'well0', hr, 0.0, 'well') + (hx_ - gx_ * s1_ * 8.0 + fx_ * 2.0, hy_ - gy_ * s1_ * 8.0 + fy_ * 2.0, math.atan2(gy_, gx_)))
                for _t in range(int(hr.integers(1, 4))):   # garden trees behind the house
                    tx_, ty_ = cx - fx_ * hr.random() * (ef_ - 2.0) + gx_ * (hr.random() * 2 - 1) * (eg_ - 2.0), cy - fy_ * hr.random() * (ef_ - 2.0) + gy_ * (hr.random() * 2 - 1) * (eg_ - 2.0)
                    if _clr(tx_, ty_, 7.0): flora.append((tx_, ty_, int(hr.choice([FL_GARDEN, FL_GARDEN, FL_CULTBUSH]))))
            elif hr.random() < 0.4: objs.append(mz(TAB_O, 'seno_stog', hr, 0.0, 'stack') + (cx + gx_ * (eg_ - 3.0), cy + gy_ * (eg_ - 3.0), float(hr.random() * 6.28)))
            rows_ = ()
        for r_ in rows_:
            for q_ in range(k_):
                o_ = (q_ - (k_ - 1) / 2.0) * (L_ / k_) if k_ > 1 else 0.0
                node = ('build%d' % rng.integers(0, 4)) if area / (k_ * len(rows_)) > 60 else ('saray%d' % rng.integers(0, 4))
                tb_, node = mz(TAB_B, node, rng, 0.0, 'house')
                objs.append((tb_, node, cx + ux_ * o_ + nx_ * r_, cy + uy_ * o_ + ny_ * r_, BF.heading(node, ang)))
        dy.ellipse([cx - 16, cy - 16, cx + 16, cy + 16], fill=1)
    # 21 Nov: in the dense rows the signs stand 8 - 10 m apart while the cottages are 10 - 13.5 m long, and the cleanup dropped
    # one of every pair that overlapped (14 - 20 a cell). A building that runs into a neighbour first takes the smallest model of
    # its kind on the same spot and heading (the small cottage for a dwelling; the cowshed, pigsty, granary for a farm building);
    # only when even that does not fit is it left to the cleanup.
    if wigp_:
        SMALL_H = ('mz_chata2',); SMALL_A = ('mz_obora1', 'mz_chlew1', 'mz_spichlerz1')
        idx_ = [w[0] for w in wigp_]
        def _hits(k, rec):
            return any(j != k and abs(objs[j][2] - rec[2]) < 30 and abs(objs[j][3] - rec[3]) < 30 and BF.overlap(rec, objs[j], -0.5) for j in idx_)
        nsw_ = 0
        for k, x_, y_, a_, flip_, dw_ in sorted(wigp_, key=lambda w: -BF.spec(objs[w[0]][1])[0]):
            if not _hits(k, objs[k]): continue
            for nd_ in (SMALL_H if dw_ else SMALL_A):
                if BF.spec(nd_)[0] >= BF.spec(objs[k][1])[0]: continue
                r_ = BF.heading(nd_, a_) + (math.pi if flip_ else 0.0)
                rec_ = (TAB_BW, nd_) + BF.origin_for(x_, y_, r_, nd_) + (r_,)
                if not _hits(k, rec_): objs[k] = rec_; nsw_ += 1; break
        if nsw_ and os.environ.get('PLOT_DEBUG'): print('  smaller model where a building ran into its neighbour: %d' % nsw_, flush=True)
    # --- 2. homesteads along the streets inside the village extent.  The walk along a street starts at the way's
    # global start and every decision is seeded by the street and the attempt index, so the cells on both sides of a
    # cell border place the same homesteads (a yard or plot straddling the border is drawn identically by both cells).
    def hash32(*v):
        h = 0
        for q in v: h = (h * 1000003 ^ (int(q) & 0xffffffff)) & 0xffffffff
        return (h ^ (h >> 15)) & 0x7fffffff
    def in_ext(x, y):   # village extent is known inside this cell only; outside it the walk assumes the street is built up
        return (ext[int(y), int(x)] > 0) if _inside(x, y) else True
    if ONE_PER_SYMBOL[0] and hs_list and False:   # 21 Nov: these houses get their plot and fences from _wig_plots with the rest (two fence sets crossed)
        # the fences, once every yard is known: no fence inside another yard (two symbols side by side share the line between
        # them instead of crossing), none through a building
        idm_ = Image.new('I', (2048, 2048), 0); did_ = ImageDraw.Draw(idm_)
        for h_ in hs_list: did_.polygon([h_[1], h_[2], h_[4], h_[3]], fill=h_[0])
        idm_ = np.asarray(idm_)
        bdm_ = Image.new('L', (2048, 2048), 0); dbd_ = ImageDraw.Draw(bdm_)
        for o in objs:
            if o[1].startswith(('build', 'saray', 'izba', 'barn', 'farm', 'church', 'mz_')):
                r_ = 15 if '_asm' in o[1] else (10 if o[1].startswith(('farm', 'barn', 'build_cap', 'izba', 'church', 'mz_')) else 6)
                dbd_.ellipse([o[2] - r_, o[3] - r_, o[2] + r_, o[3] + r_], fill=255)
        bdm_ = np.asarray(bdm_) > 0
        for h_ in hs_list:
            b2_ = yard_blk[0] | bdm_ | ((idm_ != 0) & (idm_ != h_[0]))
            _fence(objs, h_[1], h_[2], h_[5], b2_, gates=(h_[6],))
            if h_[7]: _fence(objs, h_[1], h_[3], h_[5], b2_)
            if h_[8]: _fence(objs, h_[2], h_[4], h_[5], b2_)
            if h_[9]: _fence(objs, h_[3], h_[4], h_[5], b2_, posts=False)
    if LIB is not None and not ONE_PER_SYMBOL[0]:   # 27 Oct: homesteads copied from the Petropolye villages (tools/vstamps.py); 14 Nov: not where the houses follow the sheet - their yards, fences and garden ground lay along the streets without a house
        import vstamps as VS
        n = 2048
        BUF.clear(); BUF.update(mask=np.zeros((n, n), bool), hi=np.zeros((n, n), np.uint8), det=np.zeros((n, n, 4), np.uint8), grass=np.zeros((n, n), np.uint8))
        if vil_pad is not None and pad > 0:
            ext_pad = MO.dilate(vil_pad, 41)
            def in_ext2(x, y):
                X, Y = int(x) + pad, int(y) + pad
                return bool(ext_pad[Y, X]) if 0 <= X < ext_pad.shape[1] and 0 <= Y < ext_pad.shape[0] else True
        else: in_ext2 = in_ext
        def house_ok(x, y): return (not blocked[int(y), int(x)]) if _inside(x, y) else True
        allowed = plot_ok & ~wet & ~road & ~bmask
        import tracks as TK_
        if TK_.BUF.get('mask') is not None: allowed &= ~TK_.BUF['mask']   # the copied yards never paint over a road strip
        if works_mask is not None: allowed &= ~works_mask
        if farm_mask is not None: allowed &= ~farm_mask
        so, sf = [], []; taken = []
        for (pp, c) in sorted(streets, key=lambda q: (q[1] != ROAD_C, -len(q[0]))):   # the main streets first, side lanes fill in
            VS.place_street(LIB, pp, origin, in_ext2, house_ok, allowed, soil, BUF, so, sf, taken=taken, min_front=10.0 if c == ROAD_C else 7.5)
        if os.environ.get('VS_DUMP'):
            import pickle; pickle.dump((so, road), open(os.environ['VS_DUMP'], 'wb'))
        roadw = MO.dilate(road, 3); from scipy import ndimage as _ndi; rd_ = _ndi.distance_transform_edt(~road); road_f = rd_ < 4.0; road_s = rd_ < 9.0   # side / yard fences of the copied homesteads stay 9 m off any street   # front fences of one street stop 4 m short of a crossing street
        for o in so:
            x, y = o[2], o[3]
            if not _inside(x, y): continue
            if o[1].startswith(('build', 'saray')) and blocked[int(y), int(x)]: continue
            if wet[int(y), int(x)] or bmask[int(y), int(x)]: continue
            if roadw[int(y), int(x)] and not o[1].startswith(VS.FENCE): continue
            if o[1].startswith(VS.FENCE) and (road_f if (len(o) > 5 and o[5] == 'front') else road_s)[int(y), int(x)]: continue
            o = o[:5]
            if works_mask is not None and works_mask[int(y), int(x)]: continue
            objs.append(o)
        for f in sf:
            x, y = f[0], f[1]
            if _inside(x, y) and not (wet[int(y), int(x)] or road[int(y), int(x)]) and (works_mask is None or not works_mask[int(y), int(x)]): flora.append(f)
        streets = []   # the rule-based homesteads below are not drawn
    if ONE_PER_SYMBOL[0]: streets = []   # 14 Nov: houses stand on the sheet's symbols only - no street filling of either kind
    for (pp, c) in streets:
        pts = _resample(pp, 2.0)
        inside = [k for k, (x, y, ux, uy) in enumerate(pts) if _inside(x, y) and ext[int(y), int(x)]]
        if len(inside) < (1 if vil_pad is not None else 30): continue   # a street that only clips the cell still gets its homesteads' yards and plots drawn
        sseed = hash32(round(pp[0][0] + origin[0]), round(pp[0][1] + origin[1]), len(pp), cell_seed * 0)
        sr = np.random.default_rng(sseed)
        spacing = 48.0 + sr.random() * 30                       # Petropolye: 40-100 m between homesteads
        density = 0.7 + 0.3 * sr.random()
        depth = 80.0 + sr.random() * 60                         # garden plot depth (vanilla villages: yards ~40 % of the area, plots ~18 %)
        f_front = ['fence2a', 'fence2a', 'fence2a', 'fence4a', 'fence1a'][int(sr.integers(0, 5))]; f_side = ['fence2a', 'fence2a', 'fence2a', 'fence4a'][int(sr.integers(0, 4))]   # vanilla: fence2a ~90 %, no fence3a
        f_front, f_side = mz_fence(f_front, sr, 'front'), mz_fence(f_side, sr, 'side')   # 17 Nov (M19)
        for si, side in enumerate((1.0, -1.0)):
            # front fence runs: the street front is fenced continuously where there are homesteads
            run = []; nh = 0; k = 0; t_next = sr.random() * spacing * 0.6; attempt = 0
            while k < len(pts):
                x, y, ux, uy = pts[k]
                here = _inside(x, y)
                if not in_ext(x, y):
                    if run: _front_run(objs, run, f_front, blocked); run = []
                    k += 1; continue
                nx, ny = -uy * side, ux * side
                if t_next > 0: t_next -= 2.0; k += 1; continue
                hr = np.random.default_rng(hash32(sseed, si, attempt)); attempt += 1
                hx, hy = x + nx * (16.0 + hr.random() * 6), y + ny * (16.0 + hr.random() * 6)   # vanilla street zone ~20 m: the house 16-22 m off the axis
                ok = hr.random() < density
                if ok and _inside(hx, hy): ok = not blocked[int(hy), int(hx)] and not taken_img.getpixel((int(hx), int(hy)))
                if ok:
                    half = spacing / 2 - 1.5
                    dev = max(-0.6, min(0.6, hr.normal(0.0, 0.26)))                      # vanilla: |angle to the street| median 15-25 deg, up to 35
                    ang = math.atan2(ny, nx) + dev + (math.pi / 2 if hr.random() < 0.2 else 0.0)   # a fifth stand with the long side to the street
                    nh += 1
                    tb_, nd_ = mz(TAB_B, 'build%d' % hr.integers(0, 4), hr, 0.0, 'house')
                    if _inside(hx, hy): objs.append((tb_, nd_, hx, hy, BF.heading(nd_, ang)))
                    # yard: clay ~30 x 30 m with trampled ground round the house
                    dy.polygon(_rect(x, y, ux * side, uy * side, half - 1.0, 7.5, 44.0), fill=1)   # the yard fills the street front (vanilla: clay / trampled ground ~40 % of the village)
                    dy.ellipse([hx - 9, hy - 9, hx + 9, hy + 9], fill=2)
                    # the trodden path from the street through the gate to the door (26 Oct, user: the yards must connect to the road)
                    gx_, gy_ = x + nx * 9.5 + ux * (hr.random() - 0.5) * 6, y + ny * 9.5 + uy * (hr.random() - 0.5) * 6
                    dy.line([(x + nx * 3, y + ny * 3), (gx_, gy_), (hx, hy)], fill=3, width=4)
                    dtk.polygon(_rect(x, y, ux * side, uy * side, half + 6, 0.0, 44.0), fill=255)
                    # 1-3 sheds in an L, 16-24 m from the house
                    for q in range(int(hr.integers(2, 5))):
                        sa = ang + [math.pi / 2, math.pi, -math.pi / 2][q % 3] + (hr.random() - 0.5) * 0.5; sd = 16.0 + hr.random() * 8
                        sx, sy = hx + math.cos(sa) * sd, hy + math.sin(sa) * sd
                        node = 'saray%d' % hr.integers(0, 4); rot = ang + (0.0 if hr.random() < 0.5 else math.pi / 2) + (hr.random() - 0.5) * 0.2   # vanilla sheds: 2-5 deg off the house
                        if _inside(sx, sy) and not blocked[int(sy), int(sx)] and not road[int(sy), int(sx)]:
                            objs.append((TAB_B, node, sx, sy, BF.heading(node, rot))); dy.ellipse([sx - 6, sy - 6, sx + 6, sy + 6], fill=2)
                    # front fence segment for this homestead (joined into one continuous run), gate beside the house
                    f0 = (x + nx * 9.5 - ux * half, y + ny * 9.5 - uy * half); f1 = (x + nx * 9.5 + ux * half, y + ny * 9.5 + uy * half)
                    run.append((f0, f1, half + 6.0))
                    pd = 40.0 + hr.random() * 20
                    if hr.random() < 0.95: _fence(objs, f0, (f0[0] + nx * pd, f0[1] + ny * pd), f_side, blocked)
                    if hr.random() < 0.15: _fence(objs, (f0[0] + nx * pd, f0[1] + ny * pd), (f1[0] + nx * pd, f1[1] + ny * pd), f_side, blocked, posts=False)
                    # garden plot behind the yard: pattern 1 sunflower (7), 2 maize / potato rows (15), 4 orchard (13)
                    pdepth = depth * (0.75 + 0.5 * hr.random())
                    pat = int(hr.choice([1, 2, 2, 2, 4, 4, 5, 5]))   # plots: 1 sunflower (1 in 8 - user, 25 Oct: too many), 2 maize / potato rows, 4 orchard, 5 hay meadow (grass)
                    dg.polygon(_rect(x, y, ux * side, uy * side, half - 2.0, 44.0, 44.0 + pdepth), fill=pat)
                    # hedges along the plot sides and the back
                    for s_ in (-1.0, 1.0):
                        if hr.random() < 0.7:
                            hx0, hy0 = x + ux * s_ * half, y + uy * s_ * half
                            dh.line([(hx0 + nx * 34, hy0 + ny * 34), (hx0 + nx * (40 + pdepth), hy0 + ny * (40 + pdepth))], fill=255, width=int(2 + hr.integers(0, 2)))   # Petropolye hedges: 2-3 m bands of leaves soil (measured 25 Oct: half-width 1 m)
                    if hr.random() < 0.5: dh.line([(x - ux * half + nx * (42 + pdepth), y - uy * half + ny * (42 + pdepth)), (x + ux * half + nx * (42 + pdepth), y + uy * half + ny * (42 + pdepth))], fill=255, width=int(2 + hr.integers(0, 2)))
                    # yard furniture and garden trees
                    if hr.random() < 0.6: objs.append((TAB_O, 'drova', hx + math.cos(ang + 2.4) * 9, hy + math.sin(ang + 2.4) * 9, ang))
                    if hr.random() < 0.45: objs.append((TAB_O, 'skameyka%d' % (1 + hr.integers(0, 2)), x + nx * 11.0 + ux * (half - 6), y + ny * 11.0 + uy * (half - 6), math.atan2(uy, ux)))
                    if hr.random() < 0.55: objs.append(mz(TAB_O, ['seno_stog', 'seno_stog', 'seno_copna'][int(hr.integers(0, 3))], hr, 0.0, 'stack') + (x + nx * (33 + hr.random() * 8) - ux * (half - 8), y + ny * (33 + hr.random() * 8) - uy * (half - 8), float(hr.random() * 6.28)))
                    if nh % 7 == 3: objs.append(mz(TAB_S, 'well0', hr, 0.0, 'well') + (x + nx * 11.5 + ux * (half + 2), y + ny * 11.5 + uy * (half + 2), math.atan2(uy, ux)))
                    for _ in range(int(1 + hr.random() * 2)):   # 1-2 garden trees / bushes per homestead (was 2-5; user 25 Oct: too much flora)
                        tx, ty = hx + (hr.random() - 0.5) * 30 + nx * (8 + hr.random() * 14), hy + (hr.random() - 0.5) * 30 + ny * (8 + hr.random() * 14)
                        flora.append((tx, ty, int(hr.choice([FL_GARDEN, FL_GARDEN, FL_CULTBUSH]))))
                    t_next = spacing
                else:
                    t_next = 6.0
                k += 1
            if run: _front_run(objs, run, f_front, blocked)
    objs = [o for o in objs if _inside(o[2], o[3])]; flora = [f for f in flora if _inside(f[0], f[1])]
    # 20 Nov 2026 (user: "the ground near the areas of buildings should have some paths, around entrances and to make it look as if
    # people lived there. There are often patches of vegetation inside buildings"): every building stands on bare trodden earth
    # (the grass under it grew through the floor), a worn apron 1.5 - 3 m round it, a trodden patch at the door, a worn path from
    # the door to the nearest street / road (<= 45 m, not across another building), and from each shed / barn to the nearest house
    # (<= 40 m). Plants on a footprint go (here and in prokh_gen's cleanup).
    fp_img = Image.new('L', (2048, 2048), 0); dfp = ImageDraw.Draw(fp_img)
    path_img = Image.new('L', (2048, 2048), 0); dpt = ImageDraw.Draw(path_img)
    yguard_ = [None]
    if ONE_PER_SYMBOL[0]:
        from scipy import ndimage as _ndi
        from scipy.spatial import cKDTree
        _rdd, (_riy, _rix) = _ndi.distance_transform_edt(~road, return_indices=True)
        SHED_ = ('mz_obora', 'mz_chlew', 'saray', 'mz_spichlerz', 'mz_stodola', 'stodola', 'barn', 'farm', 'mz_szopa', 'mz_podcien')
        bl_ = [o for o in objs if BF.is_building(o[0])]
        for o in bl_:
            dfp.polygon(BF.rect(o[2], o[3], o[4], o[1], 0.3), fill=255)
            ar_ = 1.5 + 1.5 * float(np.random.default_rng(_h32(round(o[2] + origin[0]), round(o[3] + origin[1]), 2011)).random())
            dtr.polygon(BF.rect(o[2], o[3], o[4], o[1], ar_), fill=255)
        fpa_ = np.asarray(fp_img) > 0
        def _crosses(p0, p1, own):
            L_ = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
            for t_ in np.arange(1.0, max(1.0, L_ - 1.0), 1.0):
                qx_, qy_ = p0[0] + (p1[0] - p0[0]) * t_ / L_, p0[1] + (p1[1] - p0[1]) * t_ / L_
                if fpa_[int(min(2047, max(0, qy_))), int(min(2047, max(0, qx_)))] and not own(qx_, qy_): return True
            return False
        def _wavy(p0, p1, hr_, w_):   # a trodden path is not ruled: two bends of up to 1.5 m
            dx_, dy_ = p1[0] - p0[0], p1[1] - p0[1]; L_ = math.hypot(dx_, dy_)
            if L_ < 1.0: return
            nx_, ny_ = -dy_ / L_, dx_ / L_; pts_ = [p0]
            for f_ in (0.33, 0.66):
                o_ = hr_.uniform(-1.5, 1.5) * min(1.0, L_ / 15.0); pts_.append((p0[0] + dx_ * f_ + nx_ * o_, p0[1] + dy_ * f_ + ny_ * o_))
            pts_.append(p1); dpt.line(pts_, fill=255, width=w_, joint='curve')
        houses_ = [o for o in bl_ if not o[1].startswith(SHED_)]
        for o in houses_:
            hr_ = np.random.default_rng(_h32(round(o[2] + origin[0]), round(o[3] + origin[1]), 2012))
            cx_, cy_ = BF.centre(o[2], o[3], o[4], o[1]); sz_ = BF.spec(o[1])[1]
            zx_, zy_ = math.sin(o[4]), math.cos(o[4])                   # the door side: local +z
            door_ = (cx_ + zx_ * (sz_ / 2.0 + 0.8), cy_ + zy_ * (sz_ / 2.0 + 0.8))
            dpt.ellipse([door_[0] - 2.5, door_[1] - 2.0, door_[0] + 2.5, door_[1] + 2.0], fill=255)
            di_, dj_ = int(min(2047, max(0, door_[1]))), int(min(2047, max(0, door_[0])))
            if _rdd[di_, dj_] <= 45.0:
                rp_ = (float(_rix[di_, dj_]), float(_riy[di_, dj_]))
                rh_ = max(BF.spec(o[1])[:2]) / 2.0 + 0.5
                own_ = lambda qx_, qy_: math.hypot(qx_ - cx_, qy_ - cy_) < rh_     # its own footprint
                if not _crosses(door_, rp_, own_): _wavy(door_, rp_, hr_, 2 if _rdd[di_, dj_] > 12 else 3)
        if houses_:
            HC_ = np.array([BF.centre(o[2], o[3], o[4], o[1]) for o in houses_]); THC_ = cKDTree(HC_)
            for o in bl_:
                if not o[1].startswith(SHED_): continue
                sc_ = BF.centre(o[2], o[3], o[4], o[1]); d_, k_ = THC_.query(sc_)
                if d_ <= 40.0:
                    hr_ = np.random.default_rng(_h32(round(o[2] + origin[0]), round(o[3] + origin[1]), 2013))
                    _wavy(sc_, tuple(HC_[k_]), hr_, 2)
        yguard_[0] = _wig_plots(objs, flora, houses_, bl_, lines, ROAD_C, TRACK_C, road, wet, works_mask, fpa_, dg, dh, origin, hatch=hatch_)
    # --- 3. paint the ground
    ym = np.asarray(yard); gm = np.asarray(gard)
    hm = np.asarray(hedge) > 0
    if hm.any():   # ragged hedge edges
        import texsynth as TX
        hf = np.asarray(Image.fromarray(hm.astype(np.uint8) * 255).filter(ImageFilter.GaussianBlur(2))).astype(np.float32) / 255.0
        hm = (hf + 0.2 * (0.6 * TX.gnoise(hm.shape, origin, 1, 41) + 0.8 * TX.gnoise(hm.shape, origin, 3.0, 42))) > 0.4   # global noise: the same ragged edge on both sides of a cell border
    hm &= plot_ok
    free = ~wet & ~near_road & ~bmask & (soil != VILLAGE_SOIL)   # the pave tracks of tools/tracks.py stay
    if works_mask is not None: free &= ~works_mask
    import texsynth as TX
    yn = TX.gnoise(soil.shape, origin, 6.0, 43)
    y1 = (ym == 1) & free; y2 = (ym == 2) & free; y3 = (ym == 3) & ~wet & ~bmask
    if works_mask is not None: y3 &= ~works_mask
    # yards the Petropolye way (26 Oct, user: the brown blotches round the houses): grass with a trodden pale patch by the
    # house (pave 10) and a few dark specks - the old dark-earth / clay mix filled whole yards with brown
    soil[y1] = np.where(yn[y1] > 0.25, 10, np.where(yn[y1] < -0.6, 11, 0)).astype(soil.dtype)
    soil[y2] = np.where(yn[y2] > -0.2, VILLAGE_SOIL, 0).astype(soil.dtype)   # round the house: mostly trodden
    soil[y3] = VILLAGE_SOIL
    if ONE_PER_SYMBOL[0]:
        # 14 Nov (user: "the ground looks out of place"): the sheet's building symbol was a hard rectangle of bare clay 30 x 45 m in the
        # crop. It is grass now, with a few specks of dark earth, and trodden pale ground only round the house and on the way to the gate
        b2 = bmask & ~wet
        soil[b2] = np.where(yn[b2] > 0.8, 11, 0).astype(soil.dtype)
        tf = np.asarray(trod_img.filter(ImageFilter.GaussianBlur(2.5))).astype(np.float32) / 255.0
        tm = ((tf + 0.25 * yn) > 0.42) & ~wet & ~road
        if works_mask is not None: tm &= ~works_mask
        soil[tm] = VILLAGE_SOIL
        # 20 Nov: the paths (lightly blurred - a ragged edge, not lost in the apron's blur) and bare earth under every building
        pf = np.asarray(path_img.filter(ImageFilter.GaussianBlur(0.8))).astype(np.float32) / 255.0
        pm = ((pf + 0.15 * yn) > 0.45) & ~wet & ~road
        if works_mask is not None: pm &= ~works_mask
        soil[pm] = VILLAGE_SOIL
        soil[(np.asarray(fp_img) > 0) & ~wet] = VILLAGE_SOIL
        # plants of this module on a footprint go (garden trees beside a house that a WIG building now covers)
        fpm_ = np.asarray(fp_img.filter(ImageFilter.MaxFilter(5))) > 0
        flora = [f for f in flora if not fpm_[int(min(2047, max(0, f[1]))), int(min(2047, max(0, f[0])))]]
    gmask = (gm > 0) & plot_ok & free & (ym == 0) & ~hm
    if yguard_[0] is not None: gmask &= ~yguard_[0] & ~(np.asarray(fp_img.filter(ImageFilter.MaxFilter(9))) > 0)
    yy, xx = np.nonzero(gmask)
    if len(yy):
        pat = gm[yy, xx]
        val = np.where(pat == 1, FIELD_GREEN, np.where(pat == 2, PLOUGH, np.where(pat == 3, FIELD, soil[yy, xx])))   # orchards (4) and hay meadows (5) keep the grass
        soil[yy, xx] = val.astype(soil.dtype)
        edge = gmask & ~MO.erode(gmask, 3)                                   # vanilla plots: a 1 m dark headland round every plot
        soil[edge] = 11
        # plants on the plots: sunflowers on 7 (dense), maize on the ploughed rows, fruit trees in the orchards
        for pid, ftype, dens in ((1, FL_SUNFL, 1 / 14.0), (2, FL_CORN, 1 / 18.0), (4, FL_GARDEN, 1 / 90.0)):
            sel = np.flatnonzero(pat == pid)
            if len(sel):
                pick = sel[rng.integers(0, len(sel), max(1, int(len(sel) * dens)))]
                flora += [(float(xx[p]) + rng.random(), float(yy[p]) + rng.random(), ftype) for p in pick]
    hm &= free & (ym == 0)
    soil[hm] = LEAVES
    hy_, hx_ = np.nonzero(hm)
    if len(hy_):
        pick = rng.integers(0, len(hy_), max(1, len(hy_) // 30))
        flora += [(float(hx_[p]) + rng.random(), float(hy_[p]) + rng.random(), int(rng.choice([FL_BUSH, FL_BUSH, FL_BUSH2]))) for p in pick]   # hedges: bushes only - fruit trees stay in the orchards and yards (user, 25 Oct: trees growing in the sunflower plots)
    return objs, flora

def _wig_plots(objs, flora, houses, bl, lines, ROAD_C, TRACK_C, road, wet, works_mask, fpa, dg, dh, origin, hatch=()):
    """21 Nov 2026 (user, on a WIG village: "there is nothing, no plots no fences just nothing"): the homestead plots of the
    houses placed from the WIG sheet. Every house within 45 m of a street gets a plot square to that street: as wide as halfway
    to its neighbours on the same side (6 - 22 m each way, 14 m with none), a front fence between the street and the house with a
    gate on the way to the door (none where the house itself stands at the street), side fences back over the yard to 6 m behind
    the furthest building of the plot (35 - 60 m), the right one only where a neighbour shares it; behind the yard a garden plot
    80 - 140 m deep (potato / rye rows, orchard, hay, now and then sunflowers) with bushes along its sides. Seeded by the house's
    place in the block, so the cells on both sides of a border agree."""
    from scipy.spatial import cKDTree
    pts = []
    for pp, col, dash, c in lines:
        if c in (ROAD_C, TRACK_C):
            ln_ = sum(math.hypot(b_[0] - a_[0], b_[1] - a_[1]) for a_, b_ in zip(pp, pp[1:]))   # a short lane up to a house is not its street
            pts += [(x, y, ux, uy, 4.5 if c == ROAD_C else 2.5, ln_) for x, y, ux, uy in _resample(pp, 2.0)]
    yg = Image.new('L', (2048, 2048), 0); dyg = ImageDraw.Draw(yg)   # the yards: no other plot's garden paints over them
    if not pts or not houses: return np.asarray(yg) > 0
    P = np.array(pts); T = cKDTree(P[:, :2])
    # 21 Nov (user: "the fences shouldn't collide, also they should be continuous on the plots with gates"): two neighbours share
    # ONE boundary line (square to the street at the midpoint between them), so their fences meet and never cross; each fence is a
    # run of equal panels from corner to corner (no gap at a corner, the gate in the run); a panel never touches a building, the
    # water or the worn road (prokh_gen's cleanup drops a panel within 1.5 m of it along its length - the front line moves back
    # until the whole run is clear), a side fence ends where another plot's yard begins.
    import tracks as TK_
    worn = road.copy()
    if TK_.BUF.get('mask') is not None and TK_.BUF['mask'].shape == road.shape: worn |= TK_.BUF['mask']
    if getattr(TK_, 'CORE_MASK', None) is not None and TK_.CORE_MASK.shape == road.shape: worn |= TK_.CORE_MASK
    worn = MO.dilate(worn, 5)
    soft = road.copy()                         # the roadway and its wheel-track core only: a front that cannot clear the whole worn strip
    if getattr(TK_, 'CORE_MASK', None) is not None and TK_.CORE_MASK.shape == road.shape: soft |= TK_.CORE_MASK
    soft = MO.dilate(soft, 5)
    hard = MO.dilate(fpa, 3) | wet
    if works_mask is not None: hard |= works_mask
    def _at(m, x, y): return (not _inside(x, y)) or bool(m[int(y), int(x)])
    H = []
    DWELL = ('mz_chata', 'mz_dom', 'izba', 'mz_miasto', 'mz_kamienica', 'mz_podcien', 'mz_dwor', 'mz_szkola', 'mz_remiza', 'mz_kuznia', 'build0', 'build1', 'build2', 'build3', 'build_cap', 'build_asm')
    for o in houses:
        if not o[1].startswith(DWELL): continue        # hay ricks, cellars, wells, shrines: things of a yard, not its owner
        cx, cy = BF.centre(o[2], o[3], o[4], o[1])
        ks_ = T.query_ball_point((cx, cy), 45.0)
        if not ks_: continue
        # the street of the house: the nearest sample, a lane shorter than 150 m counting 20 m further (the track up to a farm)
        k = min(ks_, key=lambda k_: math.hypot(P[k_][0] - cx, P[k_][1] - cy) + (20.0 if P[k_][5] < 150.0 else 0.0))
        rx, ry, ux, uy, hw = P[k][:5]
        nx, ny = -uy, ux
        if (cx - rx) * nx + (cy - ry) * ny < 0: nx, ny = -nx, -ny
        ux, uy = -ny, nx                                  # (u, n) right-handed, n from the street to the house
        sx, sz = BF.spec(o[1])[:2]
        a_ = abs(math.sin(o[4]) * nx + math.cos(o[4]) * ny)   # |cos| between the house's local z and the street normal
        half_n = sz / 2.0 if a_ > 0.7 else (sx / 2.0 if a_ < 0.3 else max(sx, sz) / 2.0)
        dn = (cx - rx) * nx + (cy - ry) * ny
        cu = (cx - rx) * ux + (cy - ry) * uy
        H.append(dict(i=len(H) + 1, o=o, c=(cx, cy), O=(float(rx + ux * cu), float(ry + uy * cu)), u=(float(ux), float(uy)), n=(float(nx), float(ny)), hw=float(hw), dn=dn, hn=half_n,
                      hr=np.random.default_rng(_h32(round(cx + origin[0]), round(cy + origin[1]), 2111))))
    # 21 Nov: the hatched orchard / yard plots of the sheet. Pieces closer than 4 m are one plot; the plot is the rectangle square
    # to its street round the hatching and every building touching it (6 m); a dwelling house in it owns it (it gets no drawn-up
    # plot of its own). Fenced all round, the gate on the street side, fruit trees on a 7 m chessboard over the hatching.
    HP = []; hp_mask = np.zeros((2048, 2048), bool)
    if hatch:
        from scipy import ndimage as _ndi
        him = Image.new('L', (2048, 2048), 0); dhi = ImageDraw.Draw(him)
        for pp in hatch: dhi.polygon([tuple(q) for q in pp], fill=255)
        hm_ = np.asarray(him) > 0
        hm_ = MO.erode(MO.dilate(hm_, 9), 9)
        lab, nl = _ndi.label(hm_)
        bxs_ = [(o, BF.rect(o[2], o[3], o[4], o[1])) for o in bl]
        for k in range(1, nl + 1):
            ys, xs = np.nonzero(lab == k)
            if len(xs) < 120: continue
            cx, cy = float(xs.mean()), float(ys.mean())
            kk = T.query((cx, cy))[1]; tx, ty = float(P[kk][2]), float(P[kk][3])
            nx, ny = -ty, tx
            if (cx - P[kk][0]) * nx + (cy - P[kk][1]) * ny < 0: nx, ny = -nx, -ny
            ux, uy = -ny, nx
            comp = lab == k; near_ = MO.dilate(comp, 13)
            pts = list(zip(xs.tolist(), ys.tolist()))[::7]
            members = []
            for o, rc in bxs_:
                if any(_inside(px, py) and near_[int(py), int(px)] for px, py in rc + [(o[2], o[3])]): members.append(o); pts += rc
            A = [(px - cx) * ux + (py - cy) * uy for px, py in pts]; N_ = [(px - cx) * nx + (py - cy) * ny for px, py in pts]
            a0, a1, n0, n1 = min(A) - 1.5, max(A) + 1.5, min(N_) - 1.5, max(N_) + 1.5
            def Q(a, n, cx=cx, cy=cy, ux=ux, uy=uy, nx=nx, ny=ny): return (cx + ux * a + nx * n, cy + uy * a + ny * n)
            owner = None
            for h in H:
                if h['o'] in members or (a0 - 3 < (h['c'][0] - cx) * ux + (h['c'][1] - cy) * uy < a1 + 3 and n0 - 3 < (h['c'][0] - cx) * nx + (h['c'][1] - cy) * ny < n1 + 3):
                    if owner is None or BF.spec(h['o'][1])[0] > BF.spec(owner['o'][1])[0]: owner = h
            HP.append(dict(Q=Q, a0=a0, a1=a1, n0=n0, n1=n1, comp=comp, owner=owner, c=(cx, cy), u=(ux, uy), n=(nx, ny),
                           hr=np.random.default_rng(_h32(round(cx + origin[0]), round(cy + origin[1]), 2112))))
        own_ = {id(p['owner']) for p in HP if p['owner'] is not None}
        H = [h for h in H if id(h) not in own_]
        for i_, h in enumerate(H): h['i'] = i_ + 1
        for p in HP:
            dhp = Image.new('L', (2048, 2048), 0); ImageDraw.Draw(dhp).polygon([p['Q'](p['a0'], p['n0']), p['Q'](p['a1'], p['n0']), p['Q'](p['a1'], p['n1']), p['Q'](p['a0'], p['n1'])], fill=255)
            hp_mask |= np.asarray(dhp) > 0
    if not H and not HP: return np.asarray(yg) > 0
    # neighbours on the same side of the same street (within 50 m along, 30 m across): they share the boundary between them
    for h in H:
        h['L'] = h['R'] = None
        for g in H:
            if g is h or g['n'][0] * h['n'][0] + g['n'][1] * h['n'][1] < 0.5: continue
            dx, dy = g['c'][0] - h['c'][0], g['c'][1] - h['c'][1]
            along = dx * h['u'][0] + dy * h['u'][1]; across = dx * h['n'][0] + dy * h['n'][1]
            if abs(across) > 30.0 or abs(along) < 4.0 or abs(along) > 50.0: continue
            if along > 0 and (h['R'] is None or along < h['R'][0]): h['R'] = (along, g)
            if along < 0 and (h['L'] is None or -along < h['L'][0]): h['L'] = (-along, g)
    # a house behind another of the same street (the second row of a farmstead) stands in that one's yard - it has no plot of its own
    back_ = set()
    for h in H:
        for g in H:
            if g is h or g['n'][0] * h['n'][0] + g['n'][1] * h['n'][1] < 0.5: continue
            dx, dy = g['c'][0] - h['c'][0], g['c'][1] - h['c'][1]
            if abs(dx * h['u'][0] + dy * h['u'][1]) < 9.0 and g['dn'] < h['dn'] - 6.0: back_.add(h['i']); break
    if back_:
        H = [h for h in H if h['i'] not in back_]
        for h in H: h['L'] = h['R'] = None
        for h in H:
            for g in H:
                if g is h or g['n'][0] * h['n'][0] + g['n'][1] * h['n'][1] < 0.5: continue
                dx, dy = g['c'][0] - h['c'][0], g['c'][1] - h['c'][1]
                along = dx * h['u'][0] + dy * h['u'][1]; across = dx * h['n'][0] + dy * h['n'][1]
                if abs(across) > 30.0 or abs(along) < 4.0 or abs(along) > 50.0: continue
                if along > 0 and (h['R'] is None or along < h['R'][0]): h['R'] = (along, g)
                if along < 0 and (h['L'] is None or -along < h['L'][0]): h['L'] = (-along, g)
    for h in H:   # a side with no shared line: 14 m, or less where a house of the same side stands nearer than 28 m
        h['wL'] = max(5.0, min(14.0, h['L'][0] / 2.0 - 0.5)) if h['L'] else 14.0
        h['wR'] = max(5.0, min(14.0, h['R'][0] / 2.0 - 0.5)) if h['R'] else 14.0
    for h in H:   # only mutual pairs share a line
        if h['R'] is not None and (h['R'][1]['L'] is None or h['R'][1]['L'][1] is not h): h['R'] = None
        if h['L'] is not None and (h['L'][1]['R'] is None or h['L'][1]['R'][1] is not h): h['L'] = None
    # 21 Nov (user: "the buildings are overlapped with fences and other things"): a boundary goes where the ground between the
    # buildings is widest - every line is tried across the gap and the one furthest from every building box wins (ties: nearer
    # the middle); the back of a yard goes 3 m behind the last building box reaching into it, along the clearest line
    from scipy import ndimage as _ndi
    D = np.minimum(_ndi.distance_transform_edt(~(fpa | hp_mask)), _ndi.distance_transform_edt(~soft) + 1.0)   # metres to the nearest building box, hatched plot or roadway (+1)
    Db = np.minimum(_ndi.distance_transform_edt(~fpa), _ndi.distance_transform_edt(~soft) + 1.0)   # building boxes and roadway only (yard things, trees)
    def _db(x, y): return float(Db[int(min(2047, max(0, y))), int(min(2047, max(0, x)))])
    def _d(x, y): return float(D[int(min(2047, max(0, y))), int(min(2047, max(0, x)))])
    def lclear(p, v, s0, s1):   # the least clearance along p + v * s, s0 <= s <= s1
        return min(_d(p[0] + v[0] * s, p[1] + v[1] * s) for s in np.arange(s0, s1 + 0.01, 1.0))
    boxes = [BF.rect(o[2], o[3], o[4], o[1]) for o in bl]
    lines_ = {}
    def bline(h, side):
        """the boundary line on one side: (point on the street, unit normal towards the houses), shared by a mutual pair"""
        nb = h[side]
        if nb is not None:
            key = (min(h['i'], nb[1]['i']), max(h['i'], nb[1]['i']))
            if key not in lines_:
                g = nb[1]; nx, ny = h['n'][0] + g['n'][0], h['n'][1] + g['n'][1]; nl = math.hypot(nx, ny); nx, ny = nx / nl, ny / nl
                ux, uy = -ny, nx
                mx, my = (h['O'][0] + g['O'][0]) / 2.0, (h['O'][1] + g['O'][1]) / 2.0
                ta = (h['O'][0] - mx) * ux + (h['O'][1] - my) * uy; tb = (g['O'][0] - mx) * ux + (g['O'][1] - my) * uy
                lo, hi = min(ta, tb) + 2.5, max(ta, tb) - 2.5
                s0 = min(h['hw'], g['hw']) + 2.0; s1 = max(h['dn'] + h['hn'], g['dn'] + g['hn']) + 25.0
                best = (-1e9, 0.0)
                for t in (np.arange(lo, hi + 0.01, 0.5) if hi > lo else [0.0]):
                    sc = min(4.0, lclear((mx + ux * t, my + uy * t), (nx, ny), s0, s1)) - 0.04 * abs(t)
                    if sc > best[0]: best = (sc, t)
                lines_[key] = ((mx + ux * best[1], my + uy * best[1]), (nx, ny))
            return lines_[key]
        s = 1.0 if side == 'R' else -1.0; best = (-1e9, h['w' + side])
        s0 = h['hw'] + 2.0; s1 = h['dn'] + h['hn'] + 25.0
        for w in np.arange(5.0, h['w' + side] + 4.01, 0.5):
            p = (h['O'][0] + h['u'][0] * s * w, h['O'][1] + h['u'][1] * s * w)
            sc = min(4.0, lclear(p, h['n'], s0, s1)) - 0.04 * abs(w - h['w' + side])
            if sc > best[0]: best = (sc, w)
        w = best[1]
        return ((h['O'][0] + h['u'][0] * s * w, h['O'][1] + h['u'][1] * s * w), h['n'])
    def corner(b, f): return (b[0][0] + b[1][0] * f, b[0][1] + b[1][1] * f)
    def clear(a, b, m):
        L = math.hypot(b[0] - a[0], b[1] - a[1]); n = max(2, int(L))
        return not any(_at(m, a[0] + (b[0] - a[0]) * j / n, a[1] + (b[1] - a[1]) * j / n) for j in range(n + 1))
    posts_ = set()
    def run(a, b, node, gate=None, stop=None, worn=worn):
        """equal panels from a to b; gate = distance from a of the gate's middle; stop(x, y) -> True ends the run there"""
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if L < 1.5: return
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L; ang = math.atan2(ux, uy) + math.pi / 2
        if gate is not None:   # the gate slides along the fence to the nearest spot where it stands clear (else no gate, no hole)
            def gok_(g_): return 2.3 <= g_ <= L - 2.3 and not any(_at(hard, a[0] + ux * (g_ + e), a[1] + uy * (g_ + e)) or _at(worn, a[0] + ux * (g_ + e), a[1] + uy * (g_ + e)) for e in (-1.9, -1.0, 0.0, 1.0, 1.9))
            gate = next((gate + s_ * k_ * 0.5 for k_ in range(0, 25) for s_ in ((1,) if k_ == 0 else (1, -1)) if gok_(gate + s_ * k_ * 0.5)), None)
        # the panels stop 0.3 m short of each corner (the corner post fills it): a panel never pokes through the fence it meets
        n = max(1, int(math.ceil((L - 0.6) / 2.6))); st = (L - 0.6) / n; end = L
        for j in range(n):
            t = 0.3 + (j + 0.5) * st; x, y = a[0] + ux * t, a[1] + uy * t
            if stop is not None and stop(x, y): end = 0.3 + j * st; break
            if gate is not None and abs(t - gate) < 2.0: continue
            if any(_at(hard, x + ux * e, y + uy * e) or _at(worn, x + ux * e, y + uy * e) for e in (-st / 2 + 0.2, 0.0, st / 2 - 0.2)): continue
            objs.append((TAB_F, node, x, y, ang))
        if gate is not None and 1.0 < gate < end - 1.0:
            gx, gy = a[0] + ux * gate, a[1] + uy * gate
            if not _at(hard, gx, gy) and not _at(worn, gx, gy): objs.append((TAB_F, mz_fence('gates1', None), gx, gy, ang))
        for px, py in (a, (a[0] + ux * end, a[1] + uy * end)):
            kp = (round(px * 2), round(py * 2))
            if kp in posts_ or _at(hard, px, py) or _at(worn, px, py): continue
            posts_.add(kp); objs.append((TAB_P, 'fpost2', px, py, ang))
    bc = np.array([BF.centre(o[2], o[3], o[4], o[1]) for o in bl]) if bl else np.zeros((0, 2))
    # 1. every plot: its two boundary lines, the front line (clear of the worn road) and the back of the yard
    for h in H:
        hr = h['hr']; h['bL'] = bline(h, 'L'); h['bR'] = bline(h, 'R')
        (ox, oy), (ux, uy), (nx, ny) = h['O'], h['u'], h['n']
        h['ff'] = None; h['wm'] = worn
        for wm_ in (worn, soft):
            f = h['hw'] + 2.0
            while f <= h['dn']:
                if clear(corner(h['bL'], f), corner(h['bR'], f), wm_): h['ff'] = f; h['wm'] = wm_; break
                f += 0.5
            if h['ff'] is not None: break
        if h['ff'] is None and h['dn'] - h['hn'] - 1.5 >= h['hw'] + 1.0:   # no clear line: just before the house wall (the panels on the roadway are left out)
            h['ff'] = h['dn'] - h['hn'] - 1.5; h['wm'] = soft
        f0 = h['ff'] if h['ff'] is not None else h['dn']
        aL = (h['bL'][0][0] - ox) * ux + (h['bL'][0][1] - oy) * uy; aR = (h['bR'][0][0] - ox) * ux + (h['bR'][0][1] - oy) * uy
        back = h['dn'] + h['hn'] + 15.0
        for bx_ in boxes:                       # every building box reaching into the strip of the plot
            pr = [((px - ox) * ux + (py - oy) * uy, (px - ox) * nx + (py - oy) * ny) for px, py in bx_]
            if max(a for a, _ in pr) > aL + 0.5 and min(a for a, _ in pr) < aR - 0.5 and min(n for _, n in pr) < h['dn'] + 55.0 and max(n for _, n in pr) > f0:
                back = max(back, max(n for _, n in pr) + 3.0)
        back = min(max(back, f0 + 30.0), f0 + 70.0)
        best = (-1e9, back)
        for bk in np.arange(back, back + 10.01, 1.0):   # the clearest back line within 10 m
            a0 = corner(h['bL'], bk); a1 = corner(h['bR'], bk); L_ = max(1.0, math.hypot(a1[0] - a0[0], a1[1] - a0[1]))
            sc = min(4.0, lclear(a0, ((a1[0] - a0[0]) / L_, (a1[1] - a0[1]) / L_), 0.0, L_)) - 0.05 * (bk - back)
            if sc > best[0]: best = (sc, bk)
        h['back'] = best[1]; h['f0'] = f0
    # 2. the yards (an id raster: a side fence stops where another plot's yard begins)
    own = Image.new('I', (2048, 2048), 0); dow = ImageDraw.Draw(own)
    for h in H:
        q = [corner(h['bL'], h['f0']), corner(h['bR'], h['f0']), corner(h['bR'], h['back']), corner(h['bL'], h['back'])]
        dow.polygon(q, fill=h['i']); dyg.polygon(q, fill=255)
    for j_, p in enumerate(HP):       # the sheet's plots: no drawn-up side fence runs into them
        q = [p['Q'](p['a0'], p['n0']), p['Q'](p['a1'], p['n0']), p['Q'](p['a1'], p['n1']), p['Q'](p['a0'], p['n1'])]
        p['i'] = 10000 + j_; dow.polygon(q, fill=p['i']); dyg.polygon(q, fill=255)
    own = np.asarray(own)
    # 3. the fences
    n0_ = len(objs)
    for h in H:
        hr = h['hr']
        fr = mz_fence('fence2a', hr, 'front'); sd = mz_fence('fence2a', hr, 'side')
        if h['ff'] is not None:     # the front with its gate before the door
            a, b = corner(h['bL'], h['ff']), corner(h['bR'], h['ff'])
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            g = ((h['c'][0] - a[0]) * (b[0] - a[0]) + (h['c'][1] - a[1]) * (b[1] - a[1])) / max(L, 1e-6) + hr.uniform(-3.0, 3.0)
            run(a, b, fr, gate=max(2.5, min(L - 2.5, g)), worn=h['wm'])
        for side in ('L', 'R'):
            nb = h[side]
            if nb is not None and nb[1]['i'] < h['i']: continue      # a shared line is fenced once, by the first of the pair
            g = nb[1] if nb is not None else None
            b_ = h['b' + side]
            f0 = min(h['f0'], g['f0']) if g is not None else h['f0']; bk = max(h['back'], g['back']) if g is not None else h['back']
            ok_ = {0, h['i']} | ({g['i']} if g is not None else set())
            run(corner(b_, f0), corner(b_, bk), sd, stop=lambda x, y, ok_=ok_: _inside(x, y) and int(own[int(y), int(x)]) not in ok_)
        run(corner(h['bL'], h['back']), corner(h['bR'], h['back']), sd)   # the back closes the yard
        # the garden behind the yard
        depth = hr.uniform(80.0, 140.0); pat = int(hr.choice([1, 2, 2, 2, 4, 4, 4, 5, 5])); bk = h['back']
        dg.polygon([corner(h['bL'], bk + 1.0), corner(h['bR'], bk + 1.0), corner(h['bR'], bk + depth), corner(h['bL'], bk + depth)], fill=pat)
        if hr.random() < 0.6: dh.line([corner(h['bR'], bk), corner(h['bR'], bk + depth)], fill=255, width=2)
        if h['L'] is None and hr.random() < 0.5: dh.line([corner(h['bL'], bk), corner(h['bL'], bk + depth)], fill=255, width=2)
        (ox, oy), (ux, uy), (nx, ny) = h['O'], h['u'], h['n']
        for _ in range(int(hr.integers(1, 4))):            # fruit trees in the yard behind the house
            a_ = hr.uniform(-8.0, 8.0); n_ = hr.uniform(h['dn'] + h['hn'] + 4.0, max(h['dn'] + h['hn'] + 5.0, bk - 3.0))
            tx, ty = ox + ux * a_ + nx * n_, oy + uy * a_ + ny * n_
            if _inside(tx, ty) and not hard[int(ty), int(tx)] and int(own[int(ty), int(tx)]) in (0, h['i']): flora.append((tx, ty, int(hr.choice([FL_GARDEN, FL_GARDEN, FL_CULTBUSH]))))
    # the sheet's hatched plots: fenced all round (the front pulled back off the worn road), the gate before the owner's door or
    # in the middle of the street side; fruit trees on a 7 m chessboard over the hatching (key 1931 #94)
    for p in HP:
        hr = p['hr']; Q = p['Q']; a0, a1, n0, n1 = p['a0'], p['a1'], p['n0'], p['n1']
        fr = mz_fence('fence2a', hr, 'front'); sd = mz_fence('fence2a', hr, 'side')
        wm_ = worn; nf = n0
        while nf < n0 + 6.0 and not clear(Q(a0, nf), Q(a1, nf), wm_): nf += 0.5
        if not clear(Q(a0, nf), Q(a1, nf), wm_): wm_ = soft; nf = n0
        if p['owner'] is not None:
            oc = p['owner']['c']; g = (oc[0] - p['c'][0]) * p['u'][0] + (oc[1] - p['c'][1]) * p['u'][1] - a0 + hr.uniform(-3.0, 3.0)
        else: g = (a1 - a0) / 2.0
        run(Q(a0, nf), Q(a1, nf), fr, gate=max(2.5, min(a1 - a0 - 2.5, g)), worn=wm_)
        run(Q(a1, nf), Q(a1, n1), sd); run(Q(a0, nf), Q(a0, n1), sd); run(Q(a0, n1), Q(a1, n1), sd)
        ys, xs = np.nonzero(p['comp'])
        if len(xs):
            off = float(hr.uniform(0, 7.0))
            for a in np.arange(a0 + 3.0, a1 - 2.9, 3.5):
                for n in np.arange(nf + 3.0, n1 - 2.9, 7.0):
                    n2 = n + (3.5 if int(round((a - a0) / 3.5)) % 2 else 0.0) + off % 3.5
                    tx, ty = Q(a, n2)
                    if _inside(tx, ty) and p['comp'][int(ty), int(tx)] and _db(tx, ty) >= 3.5: flora.append((tx, ty, FL_GARDEN))
    # 4. the last check: a panel (or gate) that crosses or doubles one already standing goes - in placing order, so the first
    # fence of a line is kept whole
    def seg_(o, half):
        a = o[4] - math.pi / 2; ux, uy = math.sin(a), math.cos(a)
        return (o[2] - ux * half, o[3] - uy * half), (o[2] + ux * half, o[3] + uy * half)
    def cr_(p, q):
        def c_(o, a_, b_): return (a_[0] - o[0]) * (b_[1] - o[1]) - (a_[1] - o[1]) * (b_[0] - o[0])
        (a, b), (c, d) = p, q
        return c_(c, d, a) * c_(c, d, b) < -0.05 and c_(a, b, c) * c_(a, b, d) < -0.05
    new_ = objs[n0_:]; del objs[n0_:]
    kept_ = [o for o in objs if o[0] == TAB_F]
    grid_ = {}
    def cells_(x, y): return [(int(x // 4) + i, int(y // 4) + j) for i in (-1, 0, 1) for j in (-1, 0, 1)]
    for o in kept_: grid_.setdefault((int(o[2] // 4), int(o[3] // 4)), []).append(o)
    for o in new_:
        if o[0] == TAB_F:
            half = 2.0 if o[1] == mz_fence('gates1', None) else 1.3; s = seg_(o, half - 0.15); bad = False
            for c in cells_(o[2], o[3]):
                for q in grid_.get(c, ()):
                    hq = 2.0 if q[1] == mz_fence('gates1', None) else 1.3
                    if abs(math.sin(o[4] - q[4])) < 0.15:
                        if math.hypot(o[2] - q[2], o[3] - q[3]) < 1.2: bad = True; break
                    elif cr_(s, seg_(q, hq - 0.15)): bad = True; break
                if bad: break
            if bad: continue
            grid_.setdefault((int(o[2] // 4), int(o[3] // 4)), []).append(o)
        objs.append(o)
    # yard things and garden trees in or against a building go: benches within 1.5 m of a wall, wood piles / ricks / wells 3.5 m,
    # trees and bushes 3 m (their crowns)
    def _keep(o):
        if not o[1].startswith(('skameyka', 'drova', 'seno_', 'well', 'bochka', 'telega')): return True
        return _db(o[2], o[3]) >= (2.0 if o[1].startswith('skameyka') else 3.5)
    objs[:] = [o for o in objs if _keep(o)]
    flora[:] = [f for f in flora if _db(f[0], f[1]) >= 3.0]
    if os.environ.get('PLOT_DEBUG'):
        Fs =[o for o in objs if o[0] == TAB_F]; nx_ = 0
        for i in range(len(Fs)):
            for j in range(i + 1, len(Fs)):
                if abs(Fs[i][2] - Fs[j][2]) < 2.7 and abs(Fs[i][3] - Fs[j][3]) < 2.7 and abs(math.sin(Fs[i][4] - Fs[j][4])) > 0.3 and cr_(seg_(Fs[i], 0.95), seg_(Fs[j], 0.95)):
                    nx_ += 1
        print('  plots: %d, fence crossings %d' % (len(H), nx_), flush=True)
    return np.asarray(yg) > 0

def _front_run(objs, run, node, blocked):
    """one continuous front fence along the street for a row of homesteads, a gate at each house.  Drawn homestead by
    homestead (f0 -> f1, then across the gap to the next f0) so that it follows a curving street; a gap of more than
    30 m between two homesteads is left open (the first version drew one straight line from the first to the last
    homestead, which cut across the street and the yards wherever the street bent)."""
    for n, (f0, f1, g) in enumerate(run):
        L = math.hypot(f1[0] - f0[0], f1[1] - f0[1])
        if L >= 2: _fence(objs, f0, f1, node, blocked, gates=[g])
        if n + 1 < len(run):
            n0 = run[n + 1][0]
            if math.hypot(n0[0] - f1[0], n0[1] - f1[1]) <= 30.0: _fence(objs, f1, n0, node, blocked, posts=False)

BRICK_ZONES = []     # block rectangles (x0, y0, x1, y1) of the old town centres, where the sheet's larger blocks are brick houses

def expand_assemblies(objs):
    """14 Nov (user: "There are buildings which should be placed in bigger villages, brick houses ... the churches etc"): the stone
    models are PARTS. In all 880 vanilla cells church_cap1 never stands without church_cap0 at the same record (230 of 230; the two
    are the halves of a brick hall 27.8 x 13.2 m, with church_cap2 on the same record a church with its tower), build_cap1 has a
    build_cap0 on the same record turned 0 and 180 deg (the two-storey brick house, 26.2 x 15.4 m), and the barn pieces come as
    farm0, n x farm1 every 9 m, farm0 turned round. Ours stood alone: half a hall for a church, a porch wing for a house, a gable
    for a barn. The village code now places one stand-in (tools/bldfoot.py 'build_asm_*' / 'farm_asm*', its record in the middle
    of the whole box); this writes the set out. Records are kept inside the cell."""
    out = []
    def cl(v): return min(2047.9, max(0.0, v))
    for o in objs:
        nd = o[1]
        if '_asm' not in nd: out.append(o); continue
        x, y, r = o[2], o[3], o[4]; ax, az = BF.axes(r); zz = tuple(o[5:6])   # (the height of the whole set, if given)
        def at(dx, dz=0.0): return (cl(x + ax[0] * dx + az[0] * dz), cl(y + ax[1] * dx + az[1] * dz))
        if nd == 'build_asm_hall':        # box x -15.2 .. 12.59: its middle is 1.3 m on the minus side of the record
            p = at(1.305); out += [(TAB_BC, 'church_cap0') + p + (r,) + zz, (TAB_BC, 'church_cap1') + p + (r,) + zz]
        elif nd == 'build_asm_church':    # box x -15.2 .. 21.4, z -6.6 .. 7.7
            p = at(-3.1, -0.555); out += [(TAB_BC, 'church_cap0') + p + (r,) + zz, (TAB_BC, 'church_cap1') + p + (r,) + zz, (TAB_BC, 'church_cap2') + p + (r,) + zz]
        elif nd == 'build_asm_brick2':
            p = (cl(x), cl(y)); out += [(TAB_BC, 'build_cap1') + p + (r,) + zz, (TAB_BC, 'build_cap0') + p + (r,) + zz, (TAB_BC, 'build_cap0') + p + (r + math.pi,) + zz]
        elif nd.startswith('farm_asm'):
            k = int(nd[-1]); b = -4.5 * (k - 1)
            out.append((TAB_BC, 'farm0') + at(b - 6.0) + (r,) + zz)
            for i in range(k): out.append((TAB_BC, 'farm1') + at(b + 9.0 * i) + (r,) + zz)
            out.append((TAB_BC, 'farm0') + at(b + 9.0 * (k - 1) + 6.0) + (r + math.pi,) + zz)
        else: out.append(o)
    return out

def kolkhoz(objs, soil, farm_mask, cov, rng, WATER_C, MARSH_C, BUILDING_C, road_mask=None, origin=(0.0, 0.0), works_mask=None):
    """sovkhoz / kolkhoz yards (OSM farmyard / industrial): long barns (farm0 / farm1) in rows round a clay yard, haystacks, a fence"""
    if farm_mask is None or not farm_mask.any(): return
    from scipy import ndimage
    if road_mask is not None: farm_mask = farm_mask & ~road_mask   # no barns or haystacks on the roads / tracks through the yard
    if works_mask is not None: farm_mask = farm_mask & ~works_mask
    lab, n = ndimage.label(farm_mask)
    for k in range(1, n + 1):
        m = lab == k; ys, xs = np.nonzero(m)
        if len(ys) < 1500: continue
        cx, cy = float(xs.mean()), float(ys.mean())
        # principal axis of the yard polygon
        cxx, cyy = xs - xs.mean(), ys - ys.mean(); ang = 0.5 * math.atan2(2 * (cxx * cyy).mean(), (cxx ** 2).mean() - (cyy ** 2).mean())
        ux, uy = math.cos(ang), math.sin(ang); nx, ny = -uy, ux
        half_len = math.sqrt(len(ys)) * 0.4
        # the yard: vanilla farm ground (Petropolye PgD5) is a mottled mix - clay 30 / grass 28 / dark earth 13 / pave 10 / leaves 9 / sand 4 %,
        # not a clean clay apron; here by global noise so the neighbouring cell paints the same patches
        import texsynth as TX
        yn = TX.gnoise(soil.shape, origin, 5.0, 44); yn2 = TX.gnoise(soil.shape, origin, 2.0, 45)
        ym = m & (cov != WATER_C) & (cov != MARSH_C) & (soil == 0)
        # 25 Oct (user: the yards were a pale camouflage of sand / pave / clay blotches): mostly trodden grass with dark
        # earth round the buildings, clay only in a few patches, no pale pave or sand
        if ONE_PER_SYMBOL[0]:   # 14 Nov (user: "the ground looks out of place"): a Mazovian farmyard is grass with some trodden earth, not the kolkhoz yard's dung and clay
            soil[ym & (yn > 0.55)] = 11
            continue
        soil[ym & (yn > 0.15)] = 11
        soil[ym & (yn > 0.5) & (yn2 > 0.0)] = CLAY
        soil[ym & (yn > 0.7)] = 2                                    # black earth (dung) - never soil 1, the engine draws it as water
        n_rows = 2 if len(ys) > 6000 else 1
        for r in range(n_rows):
            off = (r - (n_rows - 1) / 2) * 45
            t = -half_len + 20
            while t < half_len - 20:
                bx, by = cx + ux * t + nx * off, cy + uy * t + ny * off
                if 0 <= bx < 2048 and 0 <= by < 2048 and m[int(by), int(bx)] and cov[int(by), int(bx)] != BUILDING_C:
                    nd_ = 'farm%d' % rng.integers(0, 2)
                    objs.append((TAB_BC, nd_, bx, by, BF.heading(nd_, ang + (rng.random() - 0.5) * 0.12)))
                t += 34 + rng.random() * 8
        for _ in range(int(3 + len(ys) / 3000)):   # vanilla farm yard: 6 seno_cyl, 4 copna, 2 stog within 120 m
            p = rng.integers(0, len(ys)); objs.append((TAB_O, ['seno_cyl', 'seno_cyl', 'seno_copna', 'seno_stog'][int(rng.integers(0, 4))], float(xs[p]), float(ys[p]), float(rng.random() * 6.28)))
        for _ in range(int(1 + len(ys) / 6000)):   # sheds and a woodpile by the barns
            p = rng.integers(0, len(ys)); objs.append((TAB_B, 'saray%d' % rng.integers(0, 4), float(xs[p]), float(ys[p]), ang + (rng.random() - 0.5) * 0.3))

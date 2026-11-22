"""Passability quadtrees (`pen_tanks` / `pen_hums` / `pen_cars` / `pen_apcs` cell entries).

Format (decoded 2026-10-22 from Mius MgG3/MxD1; cost and flags re-read 2026-11-14 on 7 vanilla cells): a flat array of
40-byte nodes
  u8  flags0   bit 0x80 = node has stored children; 8 = road leaf; 34 (2 | 32) = building zone; other bits sampled per
               soil from the vanilla cells
  u8  flags1   (0x88 mostly)        u8 level (1 = 1024 m quadrant ... 9 = 4 m)       u8 flags3 (high nibble 0..15)
  u16 cx, u16 cy   centre of the node square in metres (x east, y north)
  u16 mask (a road-direction mask on the vanilla road leaves, 0 elsewhere; written 0)
  u16 cost     movement cost, low byte first: open grass ~60-170 by mover class, rising with slope; 50 on a road leaf for
               wheels and half-tracks; 300-1001 in a building zone; 1001 = closed (the highest value in any vanilla cell)
  u24 parent (0xffffff for the four roots)
  u24 neighbour N, S, W, E (same level, wrapping around the cell edges)
  u24 children NE, NW, SE, SW (0xffffff for leaves)
  u8 0xff
Levels 1..5 are always fully subdivided; deeper nodes are split while their area is not uniform (down to level 8 here,
level 9 round the buildings).

14 Nov 2026 (user: "the vehicles drive into houses, they can be placed on houses in deployment mode"): bytes 10-11 were
read as an 8-bit cost and a separate 0..3 field, and a house was only flagged (b0 |= 34), never priced - a house leaf cost
what its trodden yard cost, 63-128, less than the grass round it, and nothing in a cell was ever closed. The engine plans
vehicle routes, warns a driver of an obstacle ahead and refuses a deployment spot ('closed for the vehicle') from these
maps. Vanilla, 328 buildings in 6 cells: every one stands in a zone closed (1001) for wheeled vehicles and priced 300-1001
for tanks and half-tracks by the kind of building, ~370 for infantry. So now:
  * a building zone is the model's footprint plus 4 m (tools/bldfoot.py, drawn by prokh_gen) in 4 m leaves - with the
    leaves a quarter inside it (ZONE_FRAC) the vanilla footprint plus 5 m - flagged 34 and priced BLD_COST by mover
    class and building kind;
  * the road bit comes from the road raster (vanilla: 94-99 % of the road-line pixels lie in road leaves, only 8-17 % of the
    trodden yard soil away from a road), and a road leaf costs wheels and half-tracks 50 as in every vanilla cell;
  * a parent's cost follows the vanilla rule: the dearest child for tanks; for wheels and half-tracks the cheapest road
    child when it has one (a street keeps the village open at the coarse levels), else the dearest; for infantry the
    dearest, capped at 100 when it has a road child; 127 on the four roots (checked on 8-10 thousand parents per class).
The per-soil terrain costs are unchanged (low byte from the model's base and slope, high byte the soil's mode).

14 Nov 2026, water (user: "check the water and how it behaves in game", "fix everything thats wrong"): the trees knew nothing of
the water - a pond 2 m deep was priced as the soil of its bed, and the engine floods a vehicle that stands 6 - 8 s with its water
line under the surface. Read off 12 vanilla cells (3 with enough water; scratch pen_water_vanilla.py):
  * every leaf that holds any water (over 2 % of it) is cut down to 4 - 8 m, flags0 = 22 (16 | 4 | 2) and flags3 = 15 << 4 while
    the water in it is under ~1.25 m deep: tanks ~486, half-tracks ~460, wheels 1001 (closed, 93 - 98 %), infantry ~180;
  * deeper water: flags0 = 6 (4 | 2, bit 16 clear) with whatever the bed costs - the search leaves such leaves out by the flag;
  * a road through shallow water (a ford): flags0 = 14 (8 | 4 | 2), cost 40.
Here: `deep` (pond water of 1.25 m and more) -> flags0 6 and closed (1001) for every class, so the flag and the price agree;
`shallow` (the rivers of 3.8 m and more, the shallow rim of a pond) -> flags0 22 with the vanilla prices; the streams and
ditches under 3.8 m are left out on purpose - at most 0.5 m of water over firm ground, every vehicle and man crosses them
anywhere (user: the rivers "are passable practically in all places exept for water reservoirs") and the search need not know.
A road keeps its leaf (no water is drawn on a road: the crossing is a ford or a culvert), so every road is a way over.
"""
import json, numpy as np

MAXLEVEL = 8
OBSTLEVEL = 8   # split mixed open / blocked ground down to 8 m (vanilla goes to 4 m in places; 8 m keeps the packs small)
BLDLEVEL = 9    # a building zone's edge down to 4 m (vanilla zones: 40 % of the area in 4 m leaves, 50 % in 8 m)
ROADLEVEL = 8   # a road down to 8 m (vanilla road leaves are 8 m and 4 m)
ROAD_FRAC = 0.15  # share of road pixels that makes an 8 m leaf a road leaf (a 2.5 m field path crossing 4 m of it); vanilla: 94-99 % of the road-line pixels lie in road leaves
ZONE_FRAC = 0.25  # share of building-zone pixels that makes a 4 m leaf part of the zone
CLOSED = 1001
ROOT_COST = 127
#           kind:   1 shed   2 wooden house   3 heavy (stone house, church, barn row, windmill)
BLD_COST = {'tanks': (305, 600, CLOSED), 'apcs': (680, 885, CLOSED), 'cars': (CLOSED, CLOSED, CLOSED), 'hums': (370, 370, 370)}
ROAD_COST = {'cars': 50, 'apcs': 50}
WATERLEVEL = 8      # water edges down to 8 m
WATER_FRAC = 0.02   # share of water that makes a leaf a water leaf (vanilla: any)
SHALLOW_COST = {'tanks': 486, 'apcs': 460, 'cars': CLOSED, 'hums': 180}
FORD_COST = 40

class _Sampler:
    """cached categorical sampler for one histogram {value: count}"""
    def __init__(self, counter):
        keys = list(counter.keys()); w = np.asarray([counter[k] for k in keys], np.float64)
        self.keys = np.asarray([int(k) for k in keys]); self.cum = np.cumsum(w / w.sum())
    def draw(self, rng, n):
        return self.keys[np.minimum(np.searchsorted(self.cum, rng.random(n)), len(self.keys) - 1)]

def tree(soil, slope, maxlevel=MAXLEVEL, obst=None, bld=None, bld_kind=None, road=None, deep=None, shallow=None):
    """the quadtree (shared by the four mover classes): list of dicts level, cx, cy, parent, children, soil, slope, obst,
    bld (share of the node inside a building zone), kind (the building kind most of that share belongs to, 0 = none), road
    (share of road pixels; None without a road raster).
    obst: what stands on the ground (plants, fences, buildings); bld_kind: uint8 raster of the building zones, 0 = none,
    1..3 = BLD_COST kind (bld: the same as a plain mask, kind 2); road: the roadways; deep / shallow: bool rasters of the water
    that closes a leaf / that is forded at a price (see the module text) - the nodes get 'deep' and 'shal' (shares)."""
    H = soil.shape[0]
    onehot = np.stack([(soil == s) for s in range(16)], 0).astype(np.int32)
    sat = np.pad(onehot.cumsum(1).cumsum(2), ((0, 0), (1, 0), (1, 0))); del onehot
    ssat = np.pad(slope.astype(np.float64).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    def hist(x0, y0, s):
        return sat[:, y0 + s, x0 + s] - sat[:, y0, x0 + s] - sat[:, y0 + s, x0] + sat[:, y0, x0]
    def smean(x0, y0, s):
        return (ssat[y0 + s, x0 + s] - ssat[y0, x0 + s] - ssat[y0 + s, x0] + ssat[y0, x0]) / (s * s)
    def _sat(m):
        return None if m is None else np.pad(m.astype(np.int32).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    if bld_kind is not None: bld = bld_kind > 0
    osat, bsat, rsat = _sat(obst), _sat(bld), _sat(road)
    dsat, hsat = _sat(deep), _sat(shallow)
    k2sat, k3sat = (_sat(bld_kind >= 2), _sat(bld_kind >= 3)) if bld_kind is not None else (None, None)
    def cnt(S, x0, y0, s):
        return 0 if S is None else int(S[y0 + s, x0 + s] - S[y0, x0 + s] - S[y0 + s, x0] + S[y0, x0])
    def _slope_var(x0, y0, s):
        blk = slope[y0:y0 + s:4, x0:x0 + s:4]; return float(blk.var())
    nodes = []
    def add(level, cx, cy, parent):
        s = H >> level; x0, y0 = cx - s // 2, cy - s // 2; a = s * s
        hh = hist(x0, y0, s); dom = int(hh.argmax()); uni = hh[dom] / a
        of = cnt(osat, x0, y0, s) / a; nb = cnt(bsat, x0, y0, s); nr = cnt(rsat, x0, y0, s)
        if not nb: kind = 0
        elif bld_kind is None: kind = 2
        else:   # the kind most of the zone pixels in the node have (a shed's leaf at the rim of a stone house's zone stays a shed's)
            n2, n3 = cnt(k2sat, x0, y0, s), cnt(k3sat, x0, y0, s); kind = 3 if n3 >= max(n2 - n3, nb - n2) else (2 if n2 - n3 >= nb - n2 else 1)   # a tie goes to the heavier
        nd_, nh_ = cnt(dsat, x0, y0, s), cnt(hsat, x0, y0, s)
        i = len(nodes); nodes.append(dict(level=level, cx=cx, cy=cy, parent=parent, children=None, soil=dom, slope=smean(x0, y0, s), obst=of, bld=nb / a,
                                          kind=kind, road=(nr / a if rsat is not None else None), deep=nd_ / a, shal=nh_ / a))
        # a wood interior is one cover value whatever stands in it (encode: forest soil = 15): vanilla keeps it in 32-64 m
        # leaves (9f_forestry: 57 % of that area in 64 m leaves), ours was a sheet of 8 m ones, 2-3 times the vanilla node
        # count. Not where a road, a stream or a building runs through it.
        woods = nb == 0 and nr == 0 and nd_ == 0 and nh_ == 0 and int(hh[12] + hh[13]) >= 0.97 * a
        mixed = 0.1 < of < 0.9   # part open, part blocked: split so the open part stays usable
        split = level < 5 \
            or (not woods and level < maxlevel and (uni < (0.8 if level < 7 else 0.6) or (level < 7 and _slope_var(x0, y0, s) > 0.01))) \
            or (not woods and level < OBSTLEVEL and mixed) \
            or (level < ROADLEVEL and 0 < nr < 0.9 * a) \
            or (level < BLDLEVEL and 0 < nb < a) \
            or (level < WATERLEVEL and 0 < nd_ + nh_ < a)   # a shore runs through the node
        if split:
            q = s // 4
            kids = [add(level + 1, cx + q, cy + q, i), add(level + 1, cx - q, cy + q, i), add(level + 1, cx + q, cy - q, i), add(level + 1, cx - q, cy - q, i)]
            nodes[i]['children'] = kids
        return i
    import sys; sys.setrecursionlimit(10000)
    for (cx, cy) in [(1536, 1536), (512, 1536), (1536, 512), (512, 512)]: add(1, cx, cy, 0xffffff)
    # 14 Nov (audit, disassembly of the loader 'Load tactical map' and the point look-up): the engine takes nodes 0-3 of a cell as
    # its four roots and descends from them; vanilla files are breadth-first - the roots NE, NW, SE, SW, then the children of
    # node i at 4i+4..4i+7 while the levels are full, deeper nodes four at a time. Ours were depth-first (roots at 0, 11893,
    # 25474, 39155 in MgF2): the look-up found a node for the NE quarter of every cell only. Renumbered breadth-first here.
    order = [0] + [k for k in range(1, len(nodes)) if nodes[k]['parent'] == 0xffffff]
    q = 0
    while q < len(order):
        kids = nodes[order[q]]['children']
        if kids: order += kids
        q += 1
    assert len(order) == len(nodes) and order[:4] == [k for k in range(len(nodes)) if nodes[k]['parent'] == 0xffffff]
    new = {old: i for i, old in enumerate(order)}
    nodes = [nodes[old] for old in order]
    for nd in nodes:
        if nd['parent'] != 0xffffff: nd['parent'] = new[nd['parent']]
        if nd['children']: nd['children'] = [new[c] for c in nd['children']]
    # neighbours: same level, wrapping; fall back to the deepest existing node containing the point
    index = {(nd['level'], nd['cx'], nd['cy']): i for i, nd in enumerate(nodes)}
    def find(level, x, y):
        x %= H; y %= H
        for L in range(level, 0, -1):
            s = H >> L; k = (L, (x // s) * s + s // 2, (y // s) * s + s // 2)
            if k in index: return index[k]
        return 0
    for nd in nodes:
        L = nd['level']; s = H >> L
        nd['nb'] = (find(L, nd['cx'], nd['cy'] + s), find(L, nd['cx'], nd['cy'] - s), find(L, nd['cx'] - s, nd['cy']), find(L, nd['cx'] + s, nd['cy']))
    return nodes

def encode(nodes, model, rng, cls='tanks'):
    """entry bytes of one mover class ('tanks' | 'hums' | 'cars' | 'apcs') from the shared tree"""
    n = len(nodes)
    out = np.zeros((n, 40), np.uint8)
    soil_of = np.asarray([nd['soil'] for nd in nodes]); lvl = np.asarray([nd['level'] for nd in nodes])
    slope = np.asarray([nd['slope'] for nd in nodes]); has_kids = np.asarray([nd['children'] is not None for nd in nodes])
    cost = np.zeros(n); b0 = np.zeros(n, np.int64); b1 = np.zeros(n, np.int64); b3 = np.zeros(n, np.int64); b11 = np.zeros(n, np.int64)
    obst = np.asarray([nd.get('obst', 0.0) for nd in nodes]); bld = np.asarray([nd.get('bld', 0.0) for nd in nodes])
    kind = np.asarray([nd.get('kind', 0) for nd in nodes], np.int64)
    has_road = any(nd.get('road') is not None for nd in nodes); roadf = np.asarray([nd.get('road') or 0.0 for nd in nodes])
    deepf = np.asarray([nd.get('deep', 0.0) for nd in nodes]); shalf = np.asarray([nd.get('shal', 0.0) for nd in nodes])
    # 27 Oct: the flags used to be drawn at random from the vanilla histograms, which scattered "blocked" nodes (b3
    # high nibble 15) and building / trench flags over open ground at every level of the tree and broke infantry
    # deployment (squads stacked on one spot).  Vanilla MgG3: a parent's flags are the OR of its children and its b3
    # high nibble the max of its children on levels 5..8 (the floored mean on 2..4, zero on 1); leaves with 15 hold the plants / buildings / hedges (38 plants per 1000 m2,
    # 49 objects per ha) while open ground has 0..14.  So: per-soil modes, 15 only where something stands, then
    # propagate up the tree.
    def mode(h, drop=None):
        items = [(int(k), v) for k, v in h.items() if drop is None or not drop(int(k))]
        return max(items, key=lambda kv: kv[1])[0] if items else 0
    for sv in np.unique(soil_of):
        m = model.get(str(int(sv))) or model['0']; sel = soil_of == sv; k = int(sel.sum())
        cost[sel] = m['base'] + max(0.0, min(500.0, m['slope_k'])) * slope[sel] + rng.normal(0, 3, k)
        b0[sel] = mode(m['b0']) & 0x7f; b1[sel] = mode(m['b1']); b11[sel] = mode(m['b11'])
        b3[sel] = (15 << 4) if sv in (12, 13) else (mode(m['b3'], lambda v: (v >> 4) == 15) & 0xf0)
    # the terrain cost as before: low byte from the soil's base and the slope, high byte the soil's mode (water for wheels: + 768)
    c = np.minimum(np.clip(cost, 8, 250).astype(np.int64) + 256 * (b11 & 3), CLOSED)
    c[(b11 & 3) == 3] = CLOSED                  # a soil whose mode is the top range (the river bed for wheels) is closed: vanilla median 1001
    b0[(b0 & 34) == 34] &= ~34                  # the building bits come from the footprints only (the tanks model's rail soil has them as its mode)
    zone = ~has_kids & (bld >= ZONE_FRAC)       # leaves of a building zone
    blocked = (obst > 0.15) | zone              # vanilla MgG3: ~13 % of the leaf area
    b3[blocked] = 15 << 4
    if has_road:
        b0 &= ~8                                # the road bit from the roads, not from the trodden soil of every yard
        rd = ~has_kids & ~zone & (roadf >= ROAD_FRAC)
        b0[rd] |= 8
        if cls in ROAD_COST: c[rd] = ROAD_COST[cls]
    b0[zone] = 34
    c[zone] = np.asarray(BLD_COST[cls], np.int64)[np.clip(kind[zone], 1, 3) - 1]
    # water (see the module text): deep closes the leaf, shallow is forded at the vanilla price, a road leaf in it is a ford
    wl_deep = ~has_kids & ~zone & (deepf >= 0.5)
    wl_shal = ~has_kids & ~zone & ~wl_deep & (deepf + shalf > WATER_FRAC)
    if wl_deep.any() or wl_shal.any():
        ford = wl_shal & ((b0 & 8) > 0)
        b0[wl_deep] = 6; c[wl_deep] = CLOSED; b3[wl_deep] = 15 << 4
        b0[wl_shal & ~ford] = 22; c[wl_shal & ~ford] = SHALLOW_COST[cls]; b3[wl_shal & ~ford] = 15 << 4
        b0[ford] = 14; c[ford] = FORD_COST
    # bottom-up: deepest levels first
    for i in np.argsort(-lvl, kind='stable'):
        kids = nodes[i]['children']
        if kids:
            f = 0; hn = 0
            for k_ in kids: f |= int(b0[k_]) & 0x7f; hn = max(hn, int(b3[k_]) >> 4)
            L_ = int(lvl[i])   # vanilla: levels 5..8 take the max of the children, 2..4 the floored mean, 1 zero
            if L_ <= 1: hn = 0
            elif L_ <= 4: hn = sum(int(b3[k_]) >> 4 for k_ in kids) // 4
            kc = [int(c[k_]) for k_ in kids]; kr = [kc[q] for q, k_ in enumerate(kids) if int(b0[k_]) & 8]
            if L_ <= 1: pc = ROOT_COST
            elif kr and cls in ROAD_COST: pc = min(kr)       # wheels, half-tracks: the cheapest road child
            elif kr and cls == 'hums': pc = min(max(kc), 100)
            else: pc = max(kc)
            b0[i] = f; b3[i] = hn << 4; c[i] = pc
    b0[has_kids] |= 0x80
    root = lvl == 1                             # vanilla roots (176 of 176): b0 0x80, b1 0, b3 0, price 127
    b0[root] = 0x80; b1[root] = 0; b3[root] = 0; c[root] = ROOT_COST
    out[:, 0] = b0; out[:, 1] = b1; out[:, 2] = lvl; out[:, 3] = b3
    cx = np.asarray([nd['cx'] for nd in nodes]); cy = np.asarray([nd['cy'] for nd in nodes])
    out[:, 4] = cx & 255; out[:, 5] = cx >> 8; out[:, 6] = cy & 255; out[:, 7] = cy >> 8
    out[:, 10] = c & 255; out[:, 11] = c >> 8
    def put(col, v):
        v = np.asarray(v, np.int64); out[:, col] = v & 255; out[:, col + 1] = (v >> 8) & 255; out[:, col + 2] = (v >> 16) & 255
    put(12, [nd['parent'] for nd in nodes])
    for q in range(4): put(15 + 3 * q, [nd['nb'][q] for nd in nodes])
    for q in range(4): put(27 + 3 * q, [(nd['children'] or [0xffffff] * 4)[q] for nd in nodes])
    out[:, 39] = 0xff
    return out.tobytes()

def build(soil, slope, model, rng, maxlevel=MAXLEVEL, nodes=None, cls='tanks'):
    """soil: (2048,2048) uint8 low-nibble soil index; slope: (2048,2048) float gradient magnitude; model: one class of
    prokh_pen_model.json; cls: that class' name. Returns the entry bytes.  Pass `nodes` (from tree()) to share the quadtree
    between classes."""
    if nodes is None: nodes = tree(soil, slope, maxlevel)
    return encode(nodes, model, rng, cls)

def load_model(path):
    return json.load(open(path))

def read(path):
    b = np.fromfile(path, np.uint8).reshape(-1, 40)
    lvl = b[:, 2]; cx = b[:, 4].astype(int) | (b[:, 5].astype(int) << 8); cy = b[:, 6].astype(int) | (b[:, 7].astype(int) << 8)
    return b, lvl, cx, cy

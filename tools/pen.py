"""Passability quadtrees (`pen_tanks` / `pen_hums` / `pen_cars` / `pen_apcs` cell entries).

Format (decoded 2026-10-22 from Mius MgG3/MxD1): a flat array of 40-byte nodes
  u8  flags0   bit 0x80 = node has stored children; other bits sampled per soil from the vanilla cells
  u8  flags1   (0x88 mostly)        u8 level (1 = 1024 m quadrant ... 9 = 4 m)       u8 flags3 (high nibble 0..15)
  u16 cx, u16 cy   centre of the node square in metres (x east, y north)
  u16 mask (0 in most leaves; meaning unknown, written 0)   u8 cost (movement cost: asphalt ~40..60, grass ~60, marsh ~100,
                                                              forest ~105, trench ~130; rises with slope)   u8 b11 (0..3)
  u24 parent (0xffffff for the four roots)
  u24 neighbour N, S, W, E (same level, wrapping around the cell edges)
  u24 children NE, NW, SE, SW (0xffffff for leaves)
  u8 0xff
Levels 1..5 are always fully subdivided; deeper nodes are split while their area is not uniform (down to level 8 here).
"""
import json, numpy as np

MAXLEVEL = 8

class _Sampler:
    """cached categorical sampler for one histogram {value: count}"""
    def __init__(self, counter):
        keys = list(counter.keys()); w = np.asarray([counter[k] for k in keys], np.float64)
        self.keys = np.asarray([int(k) for k in keys]); self.cum = np.cumsum(w / w.sum())
    def draw(self, rng, n):
        return self.keys[np.minimum(np.searchsorted(self.cum, rng.random(n)), len(self.keys) - 1)]

def tree(soil, slope, maxlevel=MAXLEVEL):
    """the quadtree (shared by the four mover classes): list of dicts level, cx, cy, parent, children, soil, slope"""
    H = soil.shape[0]
    onehot = np.stack([(soil == s) for s in range(16)], 0).astype(np.int32)
    sat = np.pad(onehot.cumsum(1).cumsum(2), ((0, 0), (1, 0), (1, 0))); del onehot
    ssat = np.pad(slope.astype(np.float64).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    def hist(x0, y0, s):
        return sat[:, y0 + s, x0 + s] - sat[:, y0, x0 + s] - sat[:, y0 + s, x0] + sat[:, y0, x0]
    def smean(x0, y0, s):
        return (ssat[y0 + s, x0 + s] - ssat[y0, x0 + s] - ssat[y0 + s, x0] + ssat[y0, x0]) / (s * s)
    def _slope_var(x0, y0, s):
        blk = slope[y0:y0 + s:4, x0:x0 + s:4]; return float(blk.var())
    nodes = []
    def add(level, cx, cy, parent):
        s = H >> level; x0, y0 = cx - s // 2, cy - s // 2
        hh = hist(x0, y0, s); dom = int(hh.argmax()); uni = hh[dom] / (s * s)
        i = len(nodes); nodes.append(dict(level=level, cx=cx, cy=cy, parent=parent, children=None, soil=dom, slope=smean(x0, y0, s)))
        split = level < 5 or (level < maxlevel and (uni < (0.8 if level < 7 else 0.6) or (level < 7 and _slope_var(x0, y0, s) > 0.01)))
        if split:
            q = s // 4
            kids = [add(level + 1, cx + q, cy + q, i), add(level + 1, cx - q, cy + q, i), add(level + 1, cx + q, cy - q, i), add(level + 1, cx - q, cy - q, i)]
            nodes[i]['children'] = kids
        return i
    import sys; sys.setrecursionlimit(10000)
    for (cx, cy) in [(1536, 1536), (512, 1536), (1536, 512), (512, 512)]: add(1, cx, cy, 0xffffff)
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

def encode(nodes, model, rng):
    """entry bytes of one mover class from the shared tree"""
    n = len(nodes)
    out = np.zeros((n, 40), np.uint8)
    soil_of = np.asarray([nd['soil'] for nd in nodes]); lvl = np.asarray([nd['level'] for nd in nodes])
    slope = np.asarray([nd['slope'] for nd in nodes]); has_kids = np.asarray([nd['children'] is not None for nd in nodes])
    cost = np.zeros(n); b0 = np.zeros(n, np.int64); b1 = np.zeros(n, np.int64); b3 = np.zeros(n, np.int64); b11 = np.zeros(n, np.int64)
    for sv in np.unique(soil_of):
        m = model.get(str(int(sv))) or model['0']; sel = soil_of == sv; k = int(sel.sum())
        cost[sel] = m['base'] + max(0.0, min(500.0, m['slope_k'])) * slope[sel] + rng.normal(0, 3, k)
        b0[sel] = _Sampler(m['b0']).draw(rng, k) & 0x7f; b1[sel] = _Sampler(m['b1']).draw(rng, k)
        b3[sel] = _Sampler(m['b3']).draw(rng, k); b11[sel] = _Sampler(m['b11']).draw(rng, k)
    b0[has_kids] |= 0x80
    out[:, 0] = b0; out[:, 1] = b1; out[:, 2] = lvl; out[:, 3] = b3
    cx = np.asarray([nd['cx'] for nd in nodes]); cy = np.asarray([nd['cy'] for nd in nodes])
    out[:, 4] = cx & 255; out[:, 5] = cx >> 8; out[:, 6] = cy & 255; out[:, 7] = cy >> 8
    out[:, 10] = np.clip(cost, 8, 250).astype(np.uint8); out[:, 11] = b11
    def put(col, v):
        v = np.asarray(v, np.int64); out[:, col] = v & 255; out[:, col + 1] = (v >> 8) & 255; out[:, col + 2] = (v >> 16) & 255
    put(12, [nd['parent'] for nd in nodes])
    for q in range(4): put(15 + 3 * q, [nd['nb'][q] for nd in nodes])
    for q in range(4): put(27 + 3 * q, [(nd['children'] or [0xffffff] * 4)[q] for nd in nodes])
    out[:, 39] = 0xff
    return out.tobytes()

def build(soil, slope, model, rng, maxlevel=MAXLEVEL, nodes=None):
    """soil: (2048,2048) uint8 low-nibble soil index; slope: (2048,2048) float gradient magnitude; model: one class of
    prokh_pen_model.json. Returns the entry bytes.  Pass `nodes` (from tree()) to share the quadtree between classes."""
    if nodes is None: nodes = tree(soil, slope, maxlevel)
    return encode(nodes, model, rng)

def load_model(path):
    return json.load(open(path))

def read(path):
    b = np.fromfile(path, np.uint8).reshape(-1, 40)
    lvl = b[:, 2]; cx = b[:, 4].astype(int) | (b[:, 5].astype(int) << 8); cy = b[:, 6].astype(int) | (b[:, 7].astype(int) << 8)
    return b, lvl, cx, cy

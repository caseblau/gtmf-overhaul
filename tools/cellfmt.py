"""Readers/writers for the Mius-Front terrain cell entries other than hei_map (pha6.py) and ATF1 textures (atf1.py).
Formats decoded 2026-10-22 from the Mius cell MgG3 (see docs/m12_terrain/findings.md).

Coordinates: every layer shares the hei_map convention: array row 0 / y = 0 is the SOUTH edge of the cell, x grows east.
Positions in quads/opmap are metres within the 2048 m cell (opmap: normalised 0..1 * 32767).
"""
import struct, numpy as np

# ---------------------------------------------------------------- raw grids
def read_grid(path, n, dtype=np.uint8):
    return np.fromfile(path, dtype).reshape(n, n)

def write_grid(path, a):
    np.ascontiguousarray(a).tofile(path)

# ---------------------------------------------------------------- flora_quads
# u32 n; n x (f32 x, f32 rnd, f32 y, u32 type); u32 ngroups (= rows of the season flora table, 23 for ua_summer);
# per group: u32 nq; nq x (u32 x0,y0,x1,y1, u32 count, count x u32 record index). Quads of 512 m in Morton order,
# split to 256 m quads when a quad holds more than QUAD_SPLIT records (observed: 2038 unsplit).
QUAD_SPLIT = 10**9   # vanilla quads hold >2000 records unsplit; the split rule is unknown, so never split

def read_flora(path):
    b = open(path, 'rb').read()
    n = struct.unpack_from('<I', b, 0)[0]
    R = np.frombuffer(b, np.uint8, count=n * 16, offset=4).reshape(n, 16)
    x = R[:, 0:4].copy().view('<f4').ravel(); r = R[:, 4:8].copy().view('<f4').ravel()
    y = R[:, 8:12].copy().view('<f4').ravel(); t = R[:, 12:16].copy().view('<u4').ravel()
    return x, y, r, t

def _morton_quads(size, cell=2048):
    """Quads of `size` covering the cell in Morton (Z) order: list of (x0, y0)."""
    out = []
    def rec(x0, y0, s):
        if s == size: out.append((x0, y0)); return
        h = s // 2
        for dy in (0, h):
            for dx in (0, h):
                rec(x0 + dx, y0 + dy, h)
    rec(0, 0, cell)
    return out

def write_flora(path, x, y, rnd, typ, ngroups=23):
    n = len(x)
    rec = np.zeros((n, 4), '<u4')
    rec[:, 0] = np.asarray(x, '<f4').view('<u4'); rec[:, 1] = np.asarray(rnd, '<f4').view('<u4')
    rec[:, 2] = np.asarray(y, '<f4').view('<u4'); rec[:, 3] = np.asarray(typ, '<u4')
    out = [struct.pack('<I', n), rec.tobytes(), struct.pack('<I', ngroups)]
    xi = np.clip(np.floor(np.asarray(x)), 0, 2047).astype(int); yi = np.clip(np.floor(np.asarray(y)), 0, 2047).astype(int)
    typ = np.asarray(typ)
    for g in range(ngroups):
        idx = np.nonzero(typ == g)[0]
        quads = []
        for (qx, qy) in _morton_quads(512):
            m = idx[(xi[idx] >= qx) & (xi[idx] < qx + 512) & (yi[idx] >= qy) & (yi[idx] < qy + 512)]
            if len(m) > QUAD_SPLIT:
                for sy in (0, 256):
                    for sx in (0, 256):
                        mm = m[(xi[m] >= qx + sx) & (xi[m] < qx + sx + 256) & (yi[m] >= qy + sy) & (yi[m] < qy + sy + 256)]
                        quads.append((qx + sx, qy + sy, qx + sx + 256, qy + sy + 256, mm))
            else:
                quads.append((qx, qy, qx + 512, qy + 512, m))
        out.append(struct.pack('<I', len(quads)))
        for (x0, y0, x1, y1, m) in quads:
            out.append(struct.pack('<5I', x0, y0, x1, y1, len(m))); out.append(np.asarray(m, '<u4').tobytes())
    open(path, 'wb').write(b''.join(out))

# ---------------------------------------------------------------- obj_quads
# u32 total; then a stream of [u32 len][name]: a name 'tabs\\<table>.cfgpack' switches the table; any other name is a
# node of that table followed by f32 x, f32 y, f32 rotation (rad), u32, u32; an empty name repeats the previous node.
# Consecutive records of one table are separated by a u32 0 (no separator before a table switch).
def read_objects(path):
    b = open(path, 'rb').read(); o = 4; tab = None; name = None; recs = []
    while o < len(b):
        ln = struct.unpack_from('<I', b, o)[0]; s = b[o + 4:o + 4 + ln]; o += 4 + ln
        if s.startswith(b'tabs\\'): tab = s.decode(); continue
        if ln: name = s.decode('latin1')
        x, y, r, a, c = struct.unpack_from('<3f2I', b, o); o += 20
        recs.append((tab, name, x, y, r, a, c))
        if o < len(b) and struct.unpack_from('<I', b, o)[0] == 0: o += 4
    return recs

def write_objects(path, recs):
    """recs: list of (table, node, x, y, rot) with table like 'tabs\\builds.cfgpack'. Grouped by table, names repeated."""
    out = [struct.pack('<I', len(recs))]
    tables = {}
    for r in recs: tables.setdefault(r[0], []).append(r)
    for tab, rs in tables.items():
        nm = tab.encode()
        out.append(struct.pack('<I', len(nm)) + nm)
        rs = sorted(rs, key=lambda r: r[1]); prev = None
        for k, (_, node, x, y, rot, *rest) in enumerate(rs):
            if k: out.append(b'\0\0\0\0')
            s = b'' if node == prev else node.encode('latin1'); prev = node
            out.append(struct.pack('<I', len(s)) + s + struct.pack('<3f2I', x, y, rot, 0, 0))
    open(path, 'wb').write(b''.join(out))

# ---------------------------------------------------------------- trench_pos / op_pos (written empty for now)
def write_trenches(path, recs=()):
    """recs: (tag, x, y, w) firing positions: tag INF / MG / GUN / MORT / TANK, cell metres, w = dug patch size (~8.3);
    the file repeats x, y (vanilla MgG3: 300 records, point pairs 2 m apart along the trench lines)."""
    out = [struct.pack('<I', len(recs))]
    for r in recs:
        tag, x, y, w = r[:4]; x2, y2 = (r[4], r[5]) if len(r) > 5 else (x, y)   # MG / GUN: second point = facing, 10-15 m away (vanilla)
        out.append(tag.encode('ascii').ljust(4, b'\0')[:4] + struct.pack('<5f', x, y, w, x2, y2))
    open(path, 'wb').write(b''.join(out))

def write_oppos(path): open(path, 'wb').write(struct.pack('<I', 0))

# ---------------------------------------------------------------- opmap_tri (sprites with labels on the op map)
# u32 n; n x ([u32 len][name] [u32 len][label] u32 colour ARGB, u32 colour2, f32 x, f32 z, f32 y, f32 rot, f32 scale, u32 kind, u32 flag)
def read_sprites(path):
    b = open(path, 'rb').read(); n = struct.unpack_from('<I', b, 0)[0]; o = 4; out = []
    for i in range(n):
        ln = struct.unpack_from('<I', b, o)[0]; name = b[o + 4:o + 4 + ln].decode('latin1'); o += 4 + ln
        ln = struct.unpack_from('<I', b, o)[0]; label = b[o + 4:o + 4 + ln].decode('latin1'); o += 4 + ln
        c1, c2, x, z, y, rot, sc, kind, one = struct.unpack_from('<2I5f2I', b, o); o += 36
        out.append(dict(name=name, label=label, col=c1, col2=c2, x=x, z=z, y=y, rot=rot, scale=sc, kind=kind, flag=one))
    return out

def write_sprites(path, sprites):
    out = [struct.pack('<I', len(sprites))]
    for s in sprites:
        nm = s['name'].encode('latin1'); lb = s.get('label', '').encode('latin1')
        out.append(struct.pack('<I', len(nm)) + nm + struct.pack('<I', len(lb)) + lb)
        out.append(struct.pack('<2I5f2I', s.get('col', 0xff204169), s.get('col2', 0), s['x'], s.get('z', 0.0), s['y'], s.get('rot', 0.0), s.get('scale', 1.0), s.get('kind', 1), s.get('flag', 0)))
    open(path, 'wb').write(b''.join(out))

# ---------------------------------------------------------------- opmap (AZG2 line mesh)
# Header copied from a template (0x1000 bytes), geometry 'GXT7': u16 index list (line segments, pairs) at 0x1000, then
# vertices (i16 x, i16 y normalised 0..32767 over the cell, u32 colour ARGB) at a 16-byte aligned offset. Node 'd_map'
# carries the counts at 0x210/0x214, the GXT7 header at 0x430 carries offsets/counts. File padded to 16 KiB.
def read_opmap(path):
    b = open(path, 'rb').read()
    ni, nv = struct.unpack_from('<II', b, 0x214 - 4)[1], struct.unpack_from('<I', b, 0x210)[0]
    io, vo, ni, nv = struct.unpack_from('<4I', b, 0x43c)
    I = np.frombuffer(b, '<u2', count=ni, offset=io)
    raw = np.frombuffer(b, np.uint8, count=nv * 8, offset=vo).reshape(nv, 8)
    xy = raw[:, :4].copy().view('<i2').reshape(nv, 2); col = raw[:, 4:].copy().view('<u4').ravel()
    return xy, col, I

def write_opmap(path, template, xy, col, I):
    """xy: (n,2) float metres in the cell; col: (n,) u32 ARGB; I: (m,) vertex indices, consecutive pairs = line segments."""
    hdr = bytearray(open(template, 'rb').read()[:0x1000])
    nv, ni = len(xy), len(I)
    assert nv < 65536
    v = np.zeros((nv, 2), '<u4')
    p = np.clip(np.rint(np.asarray(xy, np.float64) / 2048.0 * 32767.0), 0, 32767).astype('<i2')
    v[:, 0] = p.view('<u4').ravel(); v[:, 1] = np.asarray(col, '<u4')
    idx = np.asarray(I, '<u2').tobytes()
    io = 0x1000; vo = (io + len(idx) + 15) & ~15
    body = idx + b'\0' * (vo - io - len(idx)) + v.tobytes()
    total = 0x1000 + len(body); total = (total + 0x3fff) & ~0x3fff
    struct.pack_into('<I', hdr, 4, total)
    struct.pack_into('<II', hdr, 0x210, nv, ni)
    struct.pack_into('<4I', hdr, 0x43c, io, vo, ni, nv)
    data = bytes(hdr) + body
    open(path, 'wb').write(data + b'\0' * (total - len(data)))

# ---------------------------------------------------------------- colours used by the vanilla op map
COL_CONTOUR = 0x80767d6d
COL_GRID = 0x30101010
COL_GRID_BOLD = 0x80101010
COL_ROAD = 0xff795310
COL_ROAD_DARK = 0xff63320d
COL_TRACK = 0xff1d0a04

# ---------------------------------------------------------------- water (MxD1): water_levels = 512x512 u8 index (4 m) into
# water_pal = 16 B header (u32 64, 4, 5, 512) + 64 f32 surface heights (entry 0 = descriptor water_h) padded to 516 B;
# water_map = ATF1 DXT5 512x512, RGB ~(228,238,231) alpha ~21 where water, alpha 0 elsewhere.
def write_water(dir_path, levels_idx, pal_levels, water_h=23.0, wm1=None):
    import os, atf1
    # vanilla river cell (Korotich KgD3): water_pal header 64;4;2;512, level bytes = 0x40 | palette index, and the
    # water_map carries the water itself: dark green with alpha ~250 where water is rendered, alpha 0 elsewhere
    pal = np.full(64, 10.0, '<f4'); pal[1:1 + len(pal_levels)] = pal_levels[:63]   # unused entries 10.0 as in the vanilla cell
    # after the palette: the water patches the renderer draws - u32 count, then (x0, y0, x1, y1, level index) in METRES
    # (Korotich KgD3: records x 830-999 / y 742-1003 cover exactly the water_levels zone at 512-grid px 208-249 / 185-250,
    # i.e. px * 4); the vanilla cell splits each level's bounding box into chunks of <= ~90 m. Without this table the
    # engine logs 'Water levels 0' and crashes once the water texture is opaque; with the records at half scale (the
    # first version wrote 2 m units) the water is simply not drawn.
    recs = []
    for k in range(1, min(63, len(pal_levels)) + 1):
        m = levels_idx == k
        if not m.any(): continue
        ys, xs = np.nonzero(m); x0, x1, y0, y1 = int(xs.min()) * 4, int(xs.max()) * 4 + 4, int(ys.min()) * 4, int(ys.max()) * 4 + 4
        nx = max(1, -(-(x1 - x0) // 64)); ny = max(1, -(-(y1 - y0) // 64))
        for i in range(nx):
            for j in range(ny):
                cx0 = x0 + (x1 - x0) * i // nx; cx1 = x0 + (x1 - x0) * (i + 1) // nx; cy0 = y0 + (y1 - y0) * j // ny; cy1 = y0 + (y1 - y0) * (j + 1) // ny
                if m[cy0 // 4:max(cy0 // 4 + 1, -(-cy1 // 4)), cx0 // 4:max(cx0 // 4 + 1, -(-cx1 // 4))].any(): recs.append((cx0, cy0, min(cx1, 2048), min(cy1, 2048), k))
    body = struct.pack('<4I', 64, 4, min(63, len(pal_levels)) + 1, 512) + pal.tobytes() + struct.pack('<I', len(recs)) + b''.join(struct.pack('<5I', *r) for r in recs)
    open(os.path.join(dir_path, 'water_pal.cell.loc_def.bin'), 'wb').write(body)
    lv = levels_idx.astype(np.uint8); lv = np.where(lv > 0, lv | 0x40, 0).astype(np.uint8)
    np.ascontiguousarray(lv).tofile(os.path.join(dir_path, 'water_levels.cell.loc_def.bin'))
    # water_map (vanilla Korotich KgD3 measured): alpha ~250 inside the water, a SOFT edge of 2-3 px (8-12 m) with the
    # whole 0..255 range used, RGB a mottled dark green (84, 105, 74) that lightens towards the shore; a hard 4 m alpha
    # edge is what drew the stair-stepped black river of 25 Oct. wm1 = the 1 m water mask (2048 x 2048) if given.
    from scipy import ndimage as ndi
    # 26 Oct (user's screenshot: bright white slabs on a reach of the Psel): wherever the level zone lets the engine draw the
    # water plane (terrain below the level), the map must be opaque - pixels of the zone outside the 1 m water mask had
    # alpha 0 and the 'empty' colour (255, 255, 255) and were drawn white. Alpha is now full over the whole level zone;
    # the shoreline is the terrain contour at the level, as in the vanilla cells.
    zone = ndi.binary_dilation(levels_idx > 0, iterations=1).astype(np.float32)
    alpha = np.clip(ndi.gaussian_filter(zone, 0.6) * 1.6, 0, 1)
    if wm1 is not None:
        cov = wm1.reshape(512, 4, 512, 4).mean((1, 3)).astype(np.float32)
        tone = np.clip(ndi.gaussian_filter(cov, 0.8) * 1.25, 0, 1)
    else:
        tone = alpha
    rng = np.random.default_rng(7)
    noise = ndi.gaussian_filter(rng.standard_normal((512, 512)).astype(np.float32), 1.2); noise /= max(1e-6, noise.std())
    deep = np.array((84, 105, 74), np.float32); shore = np.array((150, 170, 140), np.float32)
    t = np.clip(0.35 + 0.65 * tone, 0, 1)[..., None]
    rgb = shore + (deep - shore) * t + noise[..., None] * 12.0
    img = np.empty((512, 512, 4), np.uint8); img[..., :3] = np.clip(rgb, 0, 255); img[..., 3] = np.clip(alpha * 250, 0, 250)
    img[alpha <= 0.002] = (255, 255, 255, 0)
    atf1.write(os.path.join(dir_path, 'water_map.cell.loc_def.bin'), img, 'DXT5')

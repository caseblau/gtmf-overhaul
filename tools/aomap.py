"""The per-cell `<cell>_<poly>_ao.aomap` of a Mius-Front polygon (format AZLM v3, decoded 2026-10-25 from mgg3_mius_ao.aomap).

Layout: 'AZLM', u32 3, u16 2048, u16 2048, u16 6148, u16 1, then 24 x float4 light directions (x east, y up, z north/south -
see ZSIGN; azimuths every 15 deg, elevations 3.8-64 deg), then an RLE stream of one u32 per pixel, row-major, row 0 = south
(same orientation as mat_map): bit k set = the ray from the pixel towards direction k is blocked (terrain, trees, buildings);
0 = open sky.  Records: zero or more run bytes (each byte b < 0x80 adds b + 1 zero pixels; 0x7f = 128 and continue), then one
literal byte 0x80 | (n - 1) and n (1..128) literal words.  The vanilla maps are computed with 2 m columns (pairs of equal
words) and ~1 m rows; only 31 % of the pixels have any bit set (trenches 50 % at the low elevations, woods 20-65 %).

The engine darkens the ground with these bits per sun position, so trenches, the anti-tank ditch, balka sides and the
woods get their shadows.  build(h, flora, objs, out, header) computes them for a generated cell: terrain + plant / building
blockers, ray-marched at 1 m to 40 m and coarser to 300 m.
"""
import struct, math
import numpy as np

HEADER_LEN = 400
ZSIGN = 1.0          # +z of the light vectors = north (row index increasing); flipped if the vanilla check says so
# plant heights (m) by flora table row: pine_sm/mid/big, tree_sm/mid/big, rogoz, bush, bush_big, fir, garden, birch,
# water_tree, corn, poplar, cultbush, verba_bush, sunfl, corn_dry, dry_sm/mid/big, cut
PLANT_H = [6, 10, 14, 5, 9, 13, 1.5, 1.5, 2.5, 8, 4, 10, 8, 2.0, 14, 2.0, 3.0, 1.8, 2.0, 4, 7, 10, 0.5]
PLANT_R = [3, 4, 5, 3, 4, 5, 1, 1.5, 2, 4, 2.5, 4, 4, 1, 3, 1.5, 2, 1, 1, 2.5, 3.5, 4, 1]
STEPS = [(1, 1, 12), (14, 2, 40), (44, 4, 64)]   # (first, step, last) metres - the vanilla maps stop short: a 3.8 deg ray is not followed 150 m to the next tree

def read_header(path):
    b = open(path, 'rb').read(HEADER_LEN)
    assert b[:4] == b'AZLM'
    dirs = [struct.unpack_from('<4f', b, 16 + 16 * i)[:3] for i in range(24)]
    return b, dirs

def decode(path):
    """-> (header bytes, dirs, uint32 image (2048, 2048) row 0 = south)"""
    b = open(path, 'rb').read(); n = len(b)
    w, h = struct.unpack_from('<HH', b, 8)
    out = np.zeros(w * h, np.uint32); pos = HEADER_LEN; o = 0
    while pos < n and o < w * h:
        while True:
            c = b[pos]; pos += 1
            if c & 0x80: lit = (c & 0x7f) + 1; break
            o += c + 1
        out[o:o + lit] = np.frombuffer(b[pos:pos + 4 * lit], np.uint32); o += lit; pos += 4 * lit
    hdr, dirs = read_header(path)
    return hdr, dirs, out.reshape(h, w)

def encode(img, header):
    """img: uint32 (rows, cols) -> bytes (header + RLE stream)"""
    flat = np.ascontiguousarray(img, dtype=np.uint32).ravel()
    n = len(flat); out = [bytes(header[:HEADER_LEN])]
    nz = np.flatnonzero(flat)
    if len(nz) == 0:
        nz = np.array([n - 1])            # a run must end in a literal: the last word, even if zero
    # literal blocks: maximal stretches of non-zero words (zeros inside a stretch cost 4 bytes, a run token 1 byte, so a
    # gap of >= 2 zeros becomes a run); split into <= 128 words
    pos = 0; i = 0; m = len(nz)
    while i < m:
        start = nz[i]; j = i
        while j + 1 < m and nz[j + 1] - nz[j] <= 2: j += 1
        end = nz[j] + 1
        gap = int(start - pos)
        while gap > 128: out.append(b'\x7f'); gap -= 128
        if gap > 0: out.append(bytes([gap - 1]))
        k = start
        first = True
        while k < end:
            lit = min(128, end - k)
            if not first: pass   # consecutive literal blocks: no run bytes between them
            out.append(bytes([0x80 | (lit - 1)])); out.append(flat[k:k + lit].tobytes()); k += lit; first = False
        pos = end; i = j + 1
    if pos < n:   # trailing zeros: run + one literal zero word
        gap = int(n - pos) - 1
        while gap > 128: out.append(b'\x7f'); gap -= 128
        if gap > 0: out.append(bytes([gap - 1]))
        out.append(b'\x80'); out.append(struct.pack('<I', 0))
    return b''.join(out)

def blocker_map(h2, flora=None, objs=None):
    """h2: ground (2048, 2048) metres at 1 m; returns the top-of-blocker height map (ground + plants + buildings)"""
    from PIL import Image, ImageDraw
    n = h2.shape[0]
    top = np.zeros((n, n), np.float32)
    if flora is not None:
        x, y, t = flora
        im = {}; dr = {}
        for ti in np.unique(t):
            ti = int(ti); hgt = PLANT_H[ti] if ti < len(PLANT_H) else 2.0; r = PLANT_R[ti] if ti < len(PLANT_R) else 1.5
            key = (hgt, r)
            if key not in im: im[key] = Image.new('F', (n, n), 0.0); dr[key] = ImageDraw.Draw(im[key])
            sel = t == ti
            for xi, yi in zip(x[sel], y[sel]):
                dr[key].ellipse([xi - r, yi - r, xi + r, yi + r], fill=hgt)
        for key, image in im.items(): top = np.maximum(top, np.asarray(image, dtype=np.float32))
    if objs:
        im = Image.new('F', (n, n), 0.0); dr = ImageDraw.Draw(im)
        for o in objs:
            tab, node, x, y = o[0], o[1], o[2], o[3]
            if 'build' in tab or 'saray' in node or 'farm' in node: dr.ellipse([x - 5, y - 5, x + 5, y + 5], fill=5.0)
        top = np.maximum(top, np.asarray(im, dtype=np.float32))
    return h2 + top

def shifted(a, dy, dx, fill):
    """a shifted so that out[y, x] = a[y + dy, x + dx], fill outside"""
    n = a.shape[0]; out = np.full_like(a, fill)
    ys = slice(max(0, dy), min(n, n + dy)); xs = slice(max(0, dx), min(n, n + dx))
    yd = slice(max(0, -dy), min(n, n - dy)); xd = slice(max(0, -dx), min(n, n - dx))
    out[yd, xd] = a[ys, xs]
    return out

def compute_bits(h2, B, dirs, zsign=ZSIGN, eps=0.3, origin_on_top=True):
    """uint32 (n, n): bit k set where the ray from the pixel towards dirs[k] is blocked by B"""
    n = h2.shape[0]
    base = (B if origin_on_top else h2).astype(np.float32)
    bits = np.zeros((n, n), np.uint32)
    for k, (x, y, z) in enumerate(dirs):
        hz = math.hypot(x, z); dx, dz = x / hz, z / hz * zsign; tane = y / hz
        blocked = np.zeros((n, n), bool)
        for (t0, st, t1) in STEPS:
            for t in range(t0, t1 + 1, st):
                ox, oy = int(round(dx * t)), int(round(dz * t))
                if ox == 0 and oy == 0: continue
                hs = shifted(B, oy, ox, -1e9)
                blocked |= hs > base + (tane * t + eps)
        bits |= (blocked.astype(np.uint32) << k)
    return bits

def build(h2, flora, objs, out_path, header_path, zsign=ZSIGN):
    """h2: (2048, 2048) 1 m heights (row 0 = south); flora: (x, y, typ) arrays in cell metres; objs: object records"""
    hdr, dirs = read_header(header_path)
    h2 = np.asarray(h2, np.float32)
    B = blocker_map(h2, flora, objs)
    bits = compute_bits(h2, B, dirs, zsign)
    open(out_path, 'wb').write(encode(bits, hdr))
    return bits

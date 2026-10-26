"""ATF1 texture container (Graviteam) read/write with DXT1/DXT5 codecs in numpy.

Layout (decoded 2026-10-22 from Mius cell packs):
  0x00  'ATF1'            0x04 fourcc 'DXT1'|'DXT5'   0x08 u32 file size   0x0c u32 1
  0x80  u32 mip count     0x84 u32 0
  0x88  mip table, smallest mip first: u16 w, u16 h, u32 offset (relative to 0x2000)
  0x2000 block data (DXT1 8 B / DXT5 16 B per 4x4 block), mips in table order
"""
import struct, numpy as np

HDR = 0x2000

def _rgb565(v):
    r = ((v >> 11) & 31) * 255 // 31; g = ((v >> 5) & 63) * 255 // 63; b = (v & 31) * 255 // 31
    return np.stack([r, g, b], -1).astype(np.int32)

def dxt1_decode(blocks, w, h):
    """blocks: uint8 array (nblocks*8). Returns (h, w, 4) uint8."""
    bw, bh = max(1, w // 4), max(1, h // 4)
    d = np.frombuffer(blocks, '<u2').reshape(bw * bh, 4)
    c0, c1 = d[:, 0].astype(np.int32), d[:, 1].astype(np.int32)
    idx = (d[:, 2].astype(np.uint32) | (d[:, 3].astype(np.uint32) << 16))
    p0, p1 = _rgb565(c0), _rgb565(c1)
    opaque = c0 > c1
    p2 = np.where(opaque[:, None], (2 * p0 + p1) // 3, (p0 + p1) // 2)
    p3 = np.where(opaque[:, None], (p0 + 2 * p1) // 3, 0)
    pal = np.stack([p0, p1, p2, p3], 1)  # n,4,3
    alpha = np.ones((len(d), 4), np.int32) * 255; alpha[:, 3] = np.where(opaque, 255, 0)
    sel = np.stack([(idx >> (2 * k)) & 3 for k in range(16)], 1)  # n,16
    rgb = np.take_along_axis(pal, sel[:, :, None], 1)  # n,16,3
    a = np.take_along_axis(alpha, sel, 1)
    out = np.concatenate([rgb, a[:, :, None]], 2).reshape(bh, bw, 4, 4, 4).transpose(0, 2, 1, 3, 4).reshape(bh * 4, bw * 4, 4)
    return out[:h, :w].astype(np.uint8)

def dxt5_decode(blocks, w, h):
    bw, bh = max(1, w // 4), max(1, h // 4)
    raw = np.frombuffer(blocks, np.uint8).reshape(bw * bh, 16)
    rgba = dxt1_decode(np.ascontiguousarray(raw[:, 8:]).tobytes(), w, h)
    a0, a1 = raw[:, 0].astype(np.int32), raw[:, 1].astype(np.int32)
    bits = np.zeros(len(raw), np.uint64)
    for k in range(6): bits |= raw[:, 2 + k].astype(np.uint64) << np.uint64(8 * k)
    pal = np.zeros((len(raw), 8), np.int32); pal[:, 0] = a0; pal[:, 1] = a1
    gt = a0 > a1
    for k in range(2, 8):
        pal[:, k] = np.where(gt, ((8 - k) * a0 + (k - 1) * a1) // 7, 0)
    for k in range(2, 6):
        pal[:, k] = np.where(gt, pal[:, k], ((6 - k) * a0 + (k - 1) * a1) // 5)
    pal[:, 6] = np.where(gt, pal[:, 6], 0); pal[:, 7] = np.where(gt, pal[:, 7], 255)
    sel = np.stack([((bits >> np.uint64(3 * k)) & np.uint64(7)).astype(np.int64) for k in range(16)], 1)
    a = np.take_along_axis(pal, sel, 1).reshape(bh, bw, 4, 4).transpose(0, 2, 1, 3).reshape(bh * 4, bw * 4)
    rgba[:, :, 3] = a[:h, :w]
    return rgba

def _to565(rgb):
    r, g, b = rgb[..., 0].astype(np.int32), rgb[..., 1].astype(np.int32), rgb[..., 2].astype(np.int32)
    return ((r * 31 + 127) // 255 << 11) | ((g * 63 + 127) // 255 << 5) | ((b * 31 + 127) // 255)

def dxt1_encode(img):
    """img (h,w,3|4) uint8 -> bytes. Opaque 4-colour blocks, endpoints = extremes along the block's principal axis."""
    h, w = img.shape[:2]; bw, bh = w // 4, h // 4
    px = img[:, :, :3].reshape(bh, 4, bw, 4, 3).transpose(0, 2, 1, 3, 4).reshape(bh * bw, 16, 3).astype(np.float32)
    mean = px.mean(1, keepdims=True); d = px - mean
    cov = np.einsum('nki,nkj->nij', d, d)
    # principal axis by a few power iterations
    v = np.ones((len(px), 3), np.float32)
    for _ in range(6):
        v = np.einsum('nij,nj->ni', cov, v); v /= (np.linalg.norm(v, axis=1, keepdims=True) + 1e-6)
    proj = np.einsum('nki,ni->nk', d, v)
    lo = mean[:, 0] + v * proj.min(1, keepdims=True); hi = mean[:, 0] + v * proj.max(1, keepdims=True)
    lo = np.clip(np.rint(lo), 0, 255); hi = np.clip(np.rint(hi), 0, 255)
    c0 = _to565(hi); c1 = _to565(lo)
    swap = c0 < c1; c0s = np.where(swap, c1, c0); c1s = np.where(swap, c0, c1)
    p0 = _rgb565(c0s).astype(np.float32); p1 = _rgb565(c1s).astype(np.float32)
    pal = np.stack([p0, p1, (2 * p0 + p1) / 3, (p0 + 2 * p1) / 3], 1)  # n,4,3
    dist = ((px[:, :, None, :] - pal[:, None, :, :]) ** 2).sum(-1)  # n,16,4
    sel = dist.argmin(-1).astype(np.uint32)
    eq = c0s == c1s; sel[eq] = 0
    idx = np.zeros(len(px), np.uint32)
    for k in range(16): idx |= sel[:, k] << (2 * k)
    out = np.zeros((len(px), 4), '<u2'); out[:, 0] = c0s; out[:, 1] = c1s; out[:, 2] = idx & 0xffff; out[:, 3] = idx >> 16
    return out.tobytes()

def dxt5_encode(img):
    h, w = img.shape[:2]; bw, bh = w // 4, h // 4
    rgb = dxt1_encode(img)
    a = img[:, :, 3].reshape(bh, 4, bw, 4).transpose(0, 2, 1, 3).reshape(bh * bw, 16).astype(np.int32)
    a0 = a.max(1); a1 = a.min(1)
    pal = np.stack([((8 - k) * a0 + (k - 1) * a1) // 7 if k >= 2 else (a0 if k == 0 else a1) for k in range(8)], 1)
    sel = np.abs(a[:, :, None] - pal[:, None, :]).argmin(-1).astype(np.uint64)
    bits = np.zeros(len(a), np.uint64)
    for k in range(16): bits |= sel[:, k] << np.uint64(3 * k)
    out = np.zeros((len(a), 16), np.uint8); out[:, 0] = a0; out[:, 1] = a1
    for k in range(6): out[:, 2 + k] = (bits >> np.uint64(8 * k)) & np.uint64(255)
    out[:, 8:] = np.frombuffer(rgb, np.uint8).reshape(-1, 8)
    return out.tobytes()

def read(path):
    """Returns (fourcc, [(w,h,rgba)] smallest mip first)."""
    b = open(path, 'rb').read()
    assert b[:4] == b'ATF1', path
    fourcc = b[4:8].decode(); n = struct.unpack_from('<I', b, 0x80)[0]
    mips = []
    for k in range(n):
        w, h, off = struct.unpack_from('<HHI', b, 0x88 + 8 * k)
        bw, bh = max(1, w // 4), max(1, h // 4); sz = bw * bh * (8 if fourcc == 'DXT1' else 16)
        blk = b[HDR + off:HDR + off + sz]
        mips.append((w, h, dxt1_decode(blk, max(w, 4), max(h, 4))[:h, :w] if fourcc == 'DXT1' else dxt5_decode(blk, max(w, 4), max(h, 4))[:h, :w]))
    return fourcc, mips

def top(path):
    fourcc, mips = read(path); return mips[-1][2]

def _downsample(img):
    h, w = img.shape[:2]
    if h < 2 or w < 2: return img
    return ((img[0::2, 0::2].astype(np.uint16) + img[1::2, 0::2] + img[0::2, 1::2] + img[1::2, 1::2] + 2) // 4).astype(np.uint8)

def write(path, img, fourcc='DXT1', mipmaps=True):
    """img (h,w,4) uint8, h,w powers of two. Builds the mip chain down to 1x1 (smallest first in file)."""
    img = np.ascontiguousarray(img)
    if img.shape[2] == 3: img = np.concatenate([img, np.full(img.shape[:2] + (1,), 255, np.uint8)], 2)
    chain = [img]
    stop = 2 if fourcc == 'DXT1' else 1   # vanilla DXT1 chains end at 2x2, DXT5 at 1x1
    while mipmaps and min(chain[-1].shape[:2]) > stop: chain.append(_downsample(chain[-1]))
    chain = chain[::-1]
    enc = dxt1_encode if fourcc == 'DXT1' else dxt5_encode
    data = b''; table = []
    for m in chain:
        h, w = m.shape[:2]
        pad = m if min(h, w) >= 4 else np.pad(m, ((0, 4 - h), (0, 4 - w), (0, 0)), mode='edge')
        table.append((w, h, len(data))); data += enc(pad)
    hdr = bytearray(HDR)
    hdr[0:4] = b'ATF1'; hdr[4:8] = fourcc.encode()
    struct.pack_into('<II', hdr, 8, HDR + len(data), 1)
    struct.pack_into('<II', hdr, 0x80, len(table), 0)
    for k, (w, h, off) in enumerate(table): struct.pack_into('<HHI', hdr, 0x88 + 8 * k, w, h, off)
    open(path, 'wb').write(bytes(hdr) + data)

if __name__ == '__main__':
    import sys
    from PIL import Image
    fourcc, mips = read(sys.argv[1]); w, h, img = mips[-1]
    print(sys.argv[1], fourcc, len(mips), 'mips, top', w, 'x', h)
    Image.fromarray(img).save(sys.argv[2])

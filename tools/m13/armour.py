r"""Armour maps (arm_*_dift.armor, 11 Nov): ATF1 'ART8', 256 x 256 texels in 4 x 4 blocks of 4 bytes - two 8-bit values and a
16-bit mask choosing one of them per texel.  The values are 2 x the plate thickness in mm (the T-34-76 turret's 52 mm reads
105, roofs of 20 mm read 40).  Hit faces (PNTl columns 6:8) point into the map, so a vehicle gets new plates by writing
uniform blocks into free spots of a copy of its template's map and pointing its hit faces there.

  plates(src_map, template_mesh, {class: mm})  -> ({class: uv}, blocks) for write()
  write(src_map, out_path, blocks)
"""
import numpy as np
import atf1


def decode(path):
    b = open(path, 'rb').read(); raw = np.frombuffer(b[atf1.HDR:atf1.HDR + 16384], np.uint8).reshape(64, 64, 4)
    bits = raw[..., 2].astype(np.int32) | (raw[..., 3].astype(np.int32) << 8)
    k = np.arange(16); sel = (bits[..., None] >> k) & 1
    v = np.where(sel == 1, raw[..., 1:2], raw[..., 0:1])                     # (64, 64, 16)
    return v.reshape(64, 64, 4, 4).transpose(0, 2, 1, 3).reshape(256, 256)


def free_blocks(path, used_uvs, n):
    """n all-zero blocks away from every uv the template's hit meshes use"""
    from scipy.ndimage import binary_dilation
    A = decode(path); blk = A.reshape(64, 4, 64, 4).transpose(0, 2, 1, 3).reshape(64, 64, 16)
    used = np.zeros((64, 64), bool)
    for uv in used_uvs:
        used[np.clip((uv[:, 1] * 64).astype(int), 0, 63), np.clip((uv[:, 0] * 64).astype(int), 0, 63)] = True
    free = (blk.max(2) == 0) & ~binary_dilation(used, iterations=2)
    ys, xs = np.nonzero(free)
    if len(ys) < n: raise ValueError('only %d free blocks' % len(ys))
    return list(zip(ys[:n].tolist(), xs[:n].tolist()))


def plates(path, template, mm):
    """mm: {class: thickness}; classes with the same thickness share a block"""
    used = [a[:, 6:8] for (nm, L), (a, f) in template.geo.items() if L == 0]
    vals = sorted(set(int(round(2 * t)) for t in mm.values())); spots = free_blocks(path, used, len(vals))
    at = dict(zip(vals, spots)); blocks = [(by, bx, v) for v, (by, bx) in at.items()]
    uv = {k: ((at[int(round(2 * t))][1] * 4 + 2) / 256.0, (at[int(round(2 * t))][0] * 4 + 2) / 256.0) for k, t in mm.items()}
    return uv, blocks


def write(src, out, blocks):
    b = bytearray(open(src, 'rb').read())
    for by, bx, v in blocks:
        o = atf1.HDR + (by * 64 + bx) * 4; assert b[o:o + 4] == bytes(4), (by, bx); b[o:o + 4] = bytes((min(255, v), min(255, v), 0, 0))
    open(out, 'wb').write(bytes(b))

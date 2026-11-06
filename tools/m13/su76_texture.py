"""SU-76M's own texture pair (no game data): a clean, lightly weathered 4BO olive plate texture and a matching flat
normal / gloss map, written in the game's ATF1 container (as the vanilla reg_*_dift / bump_*_norsp textures).

  python su76_texture.py <outdir>   -> reg_su76m_dift.texture.loc_def.bin, bump_su76m_norsp.texture.loc_def.bin, previews

Why: v1/v2 mapped the new plates onto a T-70 texture area chosen blind; in game it showed mud blotches and the T-70's
baked suspension holes on the glacis. The mesh's material is now su76m_dift / su76m_norsp (the engine adds reg_ / bump_).
Layout (u, v in 0..1, v down): PLATE area u 0..1, v 0..0.875 (plain plate, used by every new part through
uvtools.plate_uv); DARK area u 0..0.125, v 0.9375..1 (slits, bores, deep shadow); v4: BRASS u 0.125..0.25 and STEEL
u 0.25..0.375 in the same strip (ammunition); the rest a slightly darker olive.
Values follow the game's own plate areas (T-50 texture: plain plate mean RGB 64 69 41, std ~9; normal map R/G ~128,
B ~10, alpha 140-200).
ATF1: 'ATF1', fourcc, u32 file size, u32 1; u32 mip count at 0x80; mip table at 0x88 (u16 w, u16 h, u32 offset),
smallest mip first; data from 0x2000.
"""
import sys, os, io, struct, numpy as np
from PIL import Image

N = 2048
PLATE_RECT = (0.0, 0.0, 1.0, 0.875)
DARK_RECT = (0.0, 0.9375, 0.125, 1.0)
DARK_UV = (0.0625, 0.96875)
BRASS_RECT = (0.125, 0.9375, 0.25, 1.0); BRASS_UV = (0.1875, 0.96875)     # v4: cartridge cases
STEEL_RECT = (0.25, 0.9375, 0.375, 1.0); STEEL_UV = (0.3125, 0.96875)     # v4: projectiles, bright metal

def _noise(n, scale, rng, octaves=4):
    out = np.zeros((n, n))
    for o in range(octaves):
        s = max(2, int(n / scale * 2 ** o)); g = rng.standard_normal((s + 1, s + 1))
        img = np.asarray(Image.fromarray(g.astype(np.float32), 'F').resize((n, n), Image.BICUBIC))
        out += img / 2 ** o
    return out / np.abs(out).max()

def diffuse(rng):
    # 3 Nov (user: "su-76 color looks odd"): v4's plate (mean 65 71 39, std ~9) was a clean, saturated yellow-green next to
    # the game's own vehicles - the T-50 / KhT-26 plate areas (same period paint) sit at median 65 63 44 with std 24-30
    # (worn, greyer, grimy) and the T-70 running gear it stands on is just as weathered. Now: a greyer 4BO base, stronger
    # tonal variation, grime and brown dust patches.
    base = np.array([61.0, 63.0, 42.0])
    low = _noise(N, 512, rng, 3); mid = _noise(N, 96, rng, 3); fine = rng.standard_normal((N, N))
    # 4 Nov (user: "su-76 texture looks off with stripes"): the v5 rain-streak layer was one random value per texel COLUMN
    # (a 16 x N field stretched only in v), i.e. 1-texel vertical lines that read as wood grain on every plate; the per-texel
    # 'fine' noise added to it. Both gone: only soft blotches (low / mid) and a 6-texel speckle remain.
    soft = _noise(N, 6, rng, 1)
    lum = 1.0 + 0.30 * low + 0.20 * mid + 0.05 * soft
    grime = 1.0 - 0.45 * np.clip(_noise(N, 160, rng, 3), 0, 1) ** 1.2                        # darker worn / oily patches
    dust = np.clip(_noise(N, 256, rng, 2), 0, 1)[..., None] * np.array([16.0, 11.0, 6.0])    # brown dust
    img = base * (lum * grime)[..., None] + dust
    v = np.arange(N) / N
    img[v >= 0.875] *= 0.82                                                                 # spare strip: darker olive
    y0, y1 = int(DARK_RECT[1] * N), N; x1 = int(DARK_RECT[2] * N)
    img[y0:y1, :x1] = np.array([17.0, 18.0, 15.0]) * (1 + 0.05 * fine[y0:y1, :x1, None])
    xb0, xb1 = int(BRASS_RECT[0] * N), int(BRASS_RECT[2] * N); img[y0:y1, xb0:xb1] = np.array([168.0, 132.0, 58.0]) * (1 + 0.04 * fine[y0:y1, xb0:xb1, None])
    xs0, xs1 = int(STEEL_RECT[0] * N), int(STEEL_RECT[2] * N); img[y0:y1, xs0:xs1] = np.array([74.0, 78.0, 66.0]) * (1 + 0.04 * fine[y0:y1, xs0:xs1, None])
    return np.clip(img, 0, 255).astype(np.uint8)

def normal_gloss(rng):
    h = 0.6 * _noise(N, 64, rng, 3) + 0.4 * rng.standard_normal((N, N)) * 0.3              # slight rolled-plate unevenness
    gy, gx = np.gradient(h)
    r = 128 + np.clip(gx * 900, -6, 6); g = 128 + np.clip(gy * 900, -6, 6)
    b = np.full((N, N), 10.0)
    a = 140 + 25 * _noise(N, 128, rng, 3)                                                       # 3 Nov: less glossy (was 165)
    img = np.stack([r, g, b, a], -1)
    y0 = int(DARK_RECT[1] * N); x1 = int(DARK_RECT[2] * N); img[y0:, :x1, 3] = 60
    img[y0:, int(BRASS_RECT[0] * N):int(STEEL_RECT[2] * N), 3] = 230                         # v4: shiny brass / steel
    return np.clip(img, 0, 255).astype(np.uint8)

def _dxt(img, fc):
    h, w = img.shape[:2]
    if h < 4 or w < 4:                                       # DXT works on 4x4 blocks: pad the smallest mips
        img = np.asarray(Image.fromarray(img).resize((4, 4), Image.NEAREST))
    mode = 'RGB' if fc == 'DXT1' else 'RGBA'
    b = io.BytesIO(); Image.fromarray(img).convert(mode).save(b, 'DDS', pixel_format=fc); return b.getvalue()[128:]

def atf(img, fc):
    mips = []; cur = Image.fromarray(img)
    size = img.shape[0]
    while size >= 1:
        mips.append(np.asarray(cur.resize((size, size), Image.LANCZOS) if size != img.shape[0] else cur)); size //= 2
    mips = mips[::-1]                                         # smallest first
    data = b''; table = []
    for m in mips:
        d = _dxt(m, fc); table.append((m.shape[1], m.shape[0], len(data))); data += d
    head = bytearray(0x2000); head[0:4] = b'ATF1'; head[4:8] = fc.encode()
    struct.pack_into('<II', head, 8, 0x2000 + len(data), 1); struct.pack_into('<I', head, 0x80, len(mips))
    for i, (w, h, o) in enumerate(table): struct.pack_into('<HHI', head, 0x88 + 8 * i, w, h, o)
    return bytes(head) + data

if __name__ == '__main__':
    out = sys.argv[1]; rng = np.random.default_rng(76)
    dif = diffuse(rng); nrm = normal_gloss(rng)
    open(os.path.join(out, 'reg_su76m_dift.texture.loc_def.bin'), 'wb').write(atf(np.dstack([dif, np.full(dif.shape[:2], 255, np.uint8)])[..., :3], 'DXT1'))
    open(os.path.join(out, 'bump_su76m_norsp.texture.loc_def.bin'), 'wb').write(atf(nrm, 'DXT5'))
    Image.fromarray(dif).resize((512, 512)).save(os.path.join(out, 'su76m_dift_preview.png'))
    print('written', out)

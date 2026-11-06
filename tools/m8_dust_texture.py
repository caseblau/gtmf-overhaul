"""MF Overhaul: our own wheel / track dust sprite sheet (trans_mfo_dust_dift), generated - no game or third-party pixels.

Why: since patch 3598/2 the dust shader draws the vanilla sprite (sfx_01_dift, cell v 0.5 = mid-grey puffs, ~90/255)
much darker; with any birth colour the cloud behind a moving vehicle came out charcoal grey (user, 0.5.31 / 0.5.32).
This sheet has light, near-neutral puffs (~220/255) in all 16 cells, so the row colour (parts_desc dust_wh c11 / c12,
a dry-chernozem tan) sets the tone. Same 4 x 4 cell layout as sfx_01_dift, so the row's UV cell (c7) is unchanged.

  python m8_dust_texture.py <out_dir>      -> <out_dir>/trans_mfo_dust_dift.texture.loc_def.bin (+ preview png)
"""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import atf1
from scipy.ndimage import gaussian_filter

N, CELL = 1024, 256

def fbm(rng, n, scales=(48, 24, 12, 6, 3), amps=(1, 0.6, 0.4, 0.25, 0.15)):
    f = np.zeros((n, n))
    for s, a in zip(scales, amps):
        g = gaussian_filter(rng.standard_normal((n, n)), s, mode='wrap'); f += a * g / (g.std() + 1e-9)
    return (f - f.mean()) / f.std()

def puff(rng):
    y, x = (np.mgrid[0:CELL, 0:CELL] + 0.5 - CELL / 2) / (CELL / 2)
    ang = np.arctan2(y, x); r = np.hypot(x, y)
    # irregular outline: radius wobbles with angle
    wob = sum(rng.uniform(0.03, 0.07) * np.cos(k * ang + rng.uniform(0, 6.3)) for k in (2, 3, 4))
    edge = 0.78 + wob
    n = fbm(rng, CELL)
    body = np.clip(1 - (r / edge) ** 2, 0, 1) ** 1.3          # soft round body, zero before the cell border
    dens = np.clip(body * (0.7 + 0.35 * n), 0, None)
    dens *= np.clip((0.92 - r) / 0.12, 0, 1)                     # hard zero ring inside the cell (no bleed)
    a = np.clip(dens * 320, 0, 235)
    lum = np.clip(222 + 16 * fbm(rng, CELL, (16, 8, 4), (1, 0.6, 0.3)), 190, 248)
    rgb = np.stack([lum + 3, lum, lum - 7], -1)                 # near neutral, a touch warm
    return np.concatenate([np.clip(rgb, 0, 255), a[..., None]], -1)

def build(seed=1943):
    rng = np.random.default_rng(seed)
    img = np.zeros((N, N, 4))
    for j in range(4):
        for i in range(4):
            img[j * CELL:(j + 1) * CELL, i * CELL:(i + 1) * CELL] = puff(rng)
    # fully transparent texels keep the puff colour (no dark fringe in the filtered mips)
    img[..., :3] = np.where(img[..., 3:4] > 0, img[..., :3], 220)
    return np.clip(img + 0.5, 0, 255).astype(np.uint8)

if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else '.'
    img = build()
    atf1.write(os.path.join(out, 'trans_mfo_dust_dift.texture.loc_def.bin'), img, 'DXT5')
    try:
        from PIL import Image
        im = Image.fromarray(img); bg = Image.new('RGBA', im.size, (60, 70, 40, 255)); bg.alpha_composite(im)
        bg.convert('RGB').resize((512, 512)).save(os.path.join(out, 'mfo_dust_preview.png'))
    except ImportError:
        pass
    print('alpha mean per cell', round(img[..., 3].mean(), 1))

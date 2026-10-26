"""Texture layers with the spatial statistics of the vanilla Mius-Front summer cells (measured on MgG3, Mius 1943):

  * the first generator sampled every pixel of mat_map (micro-tile nibble), det_map, land_ambient_col independently
    from the vanilla histograms -> white noise, "all tiles mixed onto every square metre". Vanilla is not like that:
    mat_map hi-nibble: neighbour-equality 0.78 at 1 px, 0.47 at 4 px, floor 0.27; steeper slopes use higher tiles
    det_map (detail blend RGBA): autocorrelation 0.95 / 0.65 / 0.44 / 0.27 / 0.18 at 1 / 4 / 16 / 64 / 128 px; the G and
        B channels are one signal (r = 0.95), anti-correlated with R (-0.63), alpha weakly anti-correlated with R (-0.36)
    land_ambient_col (8 m): autocorrelation 0.65 / 0.39 / 0.15 at 1 / 4 / 16 px
    grass_map: per-pixel white noise in vanilla too (equality 0.40 -> 0.35 floor) - left as it was
    soils: the open steppe is not plain 'grass' - ~10 % marsh (1) in low, flat places, ~10 % clay (3) on slopes and
        along roads, ~5 % sand (5) speckles, ~4 % bump (15) on steep ground, leaves (13) under trees, a bare-earth
        margin around every field; mottles are 2-6 px specks clustered in 50-100 m patches
All fields are sums of box-blurred white noise (two passes, radius r) with weights fitted to those statistics.
"""
import numpy as np

def _blur(a, r, times=2):
    for _ in range(times):
        c = np.cumsum(np.cumsum(np.pad(a, r, mode='reflect'), 0), 1); c = np.pad(c, ((1, 0), (1, 0))); k = 2 * r + 1
        a = (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)
    return a

def noise(shape, rng, weights):
    """unit-variance field = sum of blurred white noise, weights {radius_px: weight} (radius 0 = white)"""
    F = np.zeros(shape, np.float64)
    for r, w in weights.items():
        n = rng.standard_normal(shape); f = n if r == 0 else _blur(n, r)
        F += w * f / f.std()
    return (F / F.std()).astype(np.float32)

W_DET_R = {1: 0.555, 2: 0.164, 4: 0.426, 16: 0.36, 32: 0.279, 128: 0.526}
W_DET_G = {0: 0.307, 1: 0.55, 4: 0.337, 8: 0.086, 16: 0.379, 32: 0.114, 64: 0.207, 128: 0.531}
W_DET_A = {0: 0.168, 1: 0.568, 2: 0.07, 4: 0.423, 16: 0.375, 32: 0.15, 64: 0.281, 128: 0.472}
W_LAC = {0: 0.569, 1: 0.529, 4: 0.32, 8: 0.39, 16: 0.377}
W_LAC_A = {0: 0.721, 1: 0.514, 4: 0.321, 16: 0.338}
W_HI = {2: 0.5, 5: 1.0, 16: 0.4, 64: 0.5, 128: 0.8}
W_MOTTLE = {1: 0.7, 6: 0.5, 30: 0.6}

FALLBACK = {'8': '11', '2': '3', '4': '3'}   # soils without a vanilla sample in the style: ballast -> road_back, black earth / stone -> clay

def _st(style, s):
    k = str(int(s)); return style.get(k) or style.get(FALLBACK.get(k, '0')) or style['0']

def quantile_map(F, mask, hist):
    """categorical values with histogram `hist` laid over the ordering of the field F inside mask"""
    h = np.asarray(hist, np.float64); h = h / h.sum() if h.sum() else np.ones(len(h)) / len(h)
    idx = np.flatnonzero(mask.ravel()); order = idx[np.argsort(F.ravel()[idx], kind='stable')]
    out = np.zeros(F.size, np.uint8); cum = np.r_[0, np.cumsum(h)]; n = len(order)
    for k in range(len(h)):
        a, b = int(round(cum[k] * n)), int(round(cum[k + 1] * n))
        if b > a: out[order[a:b]] = k
    return out.reshape(F.shape)

def hi_nibble(soil, slope, style, rng):
    """micro-tile index per pixel: coherent 2-10 m clumps with the vanilla per-soil tile mix, steeper -> higher tiles"""
    F = noise(soil.shape, rng, W_HI)
    sl = slope if slope.shape == soil.shape else np.repeat(np.repeat(slope, 2, 0), 2, 1)[:soil.shape[0], :soil.shape[1]]
    z = (sl - sl.mean()) / (sl.std() + 1e-6); F = F + 0.6 * np.clip(z, -2, 3).astype(np.float32)
    out = np.zeros(soil.shape, np.uint8)
    for s in np.unique(soil):
        m = soil == s; out[m] = quantile_map(F, m, _st(style, s)['hi'])[m]
    return out

def det_map(soil, style, rng):
    """detail blend texture: per-soil mean colour, vanilla-like multi-scale noise with the vanilla channel correlations"""
    f1 = noise(soil.shape, rng, W_DET_R); f2 = noise(soil.shape, rng, W_DET_G); f3 = noise(soil.shape, rng, W_DET_A); f4 = noise(soil.shape, rng, {1: 1.0})
    g = -0.63 * f1 + 0.777 * f2
    fields = [f1, g, 0.9 * g + 0.436 * f4, -0.36 * f1 + 0.933 * f3]
    det = np.zeros(soil.shape + (4,), np.float32)
    for s in np.unique(soil):
        st = _st(style, s); m = soil == s; mean = np.asarray(st['det_mean'], np.float32); std = np.asarray(st['det_std'], np.float32)
        for c in range(4): det[..., c][m] = mean[c] + std[c] * fields[c][m]
    return np.clip(det, 0, 255).astype(np.uint8)

def ambient_col(soil8, style, rng):
    """land_ambient_col at 8 m: per-soil colour + smooth noise (vanilla autocorrelation)"""
    f = [noise(soil8.shape, rng, W_LAC) for _ in range(3)] + [noise(soil8.shape, rng, W_LAC_A)]
    f[1] = 0.8 * f[0] + 0.6 * f[1]; f[2] = 0.7 * f[0] + 0.714 * f[2]   # colour channels move together (shading / moisture), as in the vanilla map
    lac = np.zeros(soil8.shape + (4,), np.float32)
    for s in np.unique(soil8):
        st = _st(style, s); m = soil8 == s
        mean = np.asarray(st.get('lac_mean', style['0']['lac_mean']), np.float32); std = np.asarray(st.get('lac_std', style['0']['lac_std']), np.float32)
        for c in range(4): lac[..., c][m] = mean[c] + std[c] * f[c][m]
    return np.clip(lac, 0, 255).astype(np.uint8)

def mottle(soil, open_mask, wood_mask, field_mask, h2, slope, rng, fr_marsh=0.04, fr_clay=0.05, fr_sand=0.02, fr_bump=0.02):   # about half the vanilla Mius mottling: the 16 July 1943 photographs show a near-uniform steppe
    """vanilla-style soil variety on the open steppe (in place). open_mask: plain grass pixels that may change.
    marsh in relatively low, flat ground; clay on slopes; sand specks; bump on the steepest ground; leaves under trees;
    a 4 m bare-earth margin around the fields."""
    H, W = soil.shape
    rel = h2 - _blur(h2, 50, 1)                                  # relative elevation over ~100 m
    sl = slope if slope.shape == soil.shape else np.repeat(np.repeat(slope, 2, 0), 2, 1)[:H, :W]
    zr = (rel - rel.mean()) / (rel.std() + 1e-6); zs = (sl - sl.mean()) / (sl.std() + 1e-6)
    def pick(score, frac, avail):
        n = int(frac * open_mask.sum())
        if n <= 0 or not avail.any(): return np.zeros_like(avail)
        v = score[avail]; thr = np.partition(v, max(0, v.size - n))[max(0, v.size - n)] if n < v.size else v.min() - 1
        return avail & (score >= thr)
    avail = open_mask.copy()
    bump = pick(noise(soil.shape, rng, W_MOTTLE) + 1.6 * np.clip(zs, -1, 4), fr_bump, avail); soil[bump] = 15; avail &= ~bump
    clay = pick(noise(soil.shape, rng, W_MOTTLE) + 0.9 * np.clip(zs, -1, 4), fr_clay, avail); soil[clay] = 3; avail &= ~clay
    marsh = pick(noise(soil.shape, rng, W_MOTTLE) - 1.1 * np.clip(zr, -4, 1) - 0.4 * np.clip(zs, -1, 3), fr_marsh, avail); soil[marsh] = 1; avail &= ~marsh
    sand = pick(noise(soil.shape, rng, {0: 0.6, 1: 0.6, 30: 0.8}), fr_sand, avail); soil[sand] = 5; avail &= ~sand
    if wood_mask is not None and wood_mask.any():                # leaves / forest ground mixed under the trees
        f = noise(soil.shape, rng, {4: 1.0, 20: 0.6}); soil[wood_mask & (f > 0.0)] = 13
    if field_mask is not None and field_mask.any():
        from PIL import Image, ImageFilter
        dil = np.asarray(Image.fromarray((field_mask * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9))) > 0
        soil[dil & ~field_mask & open_mask] = 3                  # bare margin (headland) round the crop fields
        # ripe grain the Petropolye way: soil 6 with green (7) bands ~12 m apart along the field axis (15 %) and grass (0) patches (25 %)
        H, W = soil.shape; yy, xx = np.mgrid[0:H, 0:W]
        ph = ((xx * 0.42 + yy * 0.91) / 12.0 + noise(soil.shape, rng, {6: 1.0}) * 0.25) % 1.0
        ripe = field_mask & (soil == 6)
        soil[ripe & (ph < 0.15)] = 7
        g = noise(soil.shape, rng, {3: 1.0, 12: 0.8}); soil[ripe & (ph >= 0.15) & (g > 0.65)] = 0
    return soil


def _hash_arr(a, b, c):
    a = a.astype(np.int64); b = b.astype(np.int64)
    h = ((a * 73856093) ^ (b * 19349663) ^ (int(c) * 83492791)) & 0xffffffff
    h = ((h ^ (h >> 13)) * 1274126177) & 0xffffffff
    return (h ^ (h >> 16)) & 0xffffffff

def gnoise(shape, origin, scale, salt=0):
    """deterministic value noise in GLOBAL coordinates (block metres): bilinear interpolation of hashed lattice values
    `scale` metres apart, in [-1, 1].  The same at a given point whichever cell asks, so cover edges, field margins
    and the leaves / forest-ground mix do not jump at the cell borders.  scale <= 1 gives per-pixel white noise."""
    H, W = shape; oy, ox = float(origin[1]), float(origin[0])
    yy, xx = np.mgrid[0:H, 0:W]
    gy = (yy + oy) / scale; gx = (xx + ox) / scale
    if scale <= 1: return (_hash_arr(np.floor(gy), np.floor(gx), salt) / 2 ** 32 * 2 - 1).astype(np.float32)
    y0 = np.floor(gy); x0 = np.floor(gx); ty = (gy - y0).astype(np.float32); tx = (gx - x0).astype(np.float32)
    v00 = _hash_arr(y0, x0, salt); v01 = _hash_arr(y0, x0 + 1, salt); v10 = _hash_arr(y0 + 1, x0, salt); v11 = _hash_arr(y0 + 1, x0 + 1, salt)
    f = lambda v: (v / 2 ** 32 * 2 - 1).astype(np.float32)
    ty = ty * ty * (3 - 2 * ty); tx = tx * tx * (3 - 2 * tx)   # smoothstep
    return (f(v00) * (1 - ty) * (1 - tx) + f(v01) * (1 - ty) * tx + f(v10) * ty * (1 - tx) + f(v11) * ty * tx).astype(np.float32)

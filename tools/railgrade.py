"""Railway grade (M16, user 14 Nov: "Railway should be leveled so it goes straight instead of on heights").

The track used to lie 1.5 m over the ground it crossed, so it rose and fell with every bump of the height data (and with
the tree canopy the surface model still carries). A railway is built on an even grade: low fills over the hollows, cuts
through the rises, the gradient a few per mille.

  build()  once per block: the rail lines are drawn on the block's ground at 4 m and the ground under them is averaged
           ALONG THE LINES (a Gaussian of `sigma` metres over the rail pixels only), so the profile does not depend on the
           cell or on how the lines are split; the formation sits `lift` metres over that average, never below the ground
           by more than `max_cut` and never more than `max_fill` over it (a long fill over a valley stays a fill).
  apply()  per cell: the formation height is read off the block profile at every pixel near the line; the crest
           (`crest` m each side of the line) lies at it, the sides fall / rise to the ground at 1:`side` - at 1:`ramp`
           on a road or track, so a level crossing is a ramp, not a wall. Water under the fill is covered (a culvert).
"""
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

P = dict(sigma=350.0, lift=1.0, max_cut=2.5, max_fill=4.0, crest=5.5, side=1.6, ramp=14.0)
Z = [None]        # (profile at 4 m, row 0 = south; x0, y0 of the raster in block metres; step)

def build(lines, dem, x0, y0, step=4.0, params=None, log=print):
    """lines: polylines in block metres; dem: block ground (row 0 = south) at `step` m, pixel (r, c) centred on
    (x0 + (c + 0.5) * step, y0 + (r + 0.5) * step)."""
    P.update(params or {})
    H, W = dem.shape
    im = Image.new('L', (W, H), 0); d = ImageDraw.Draw(im)
    for pp in lines:
        q = [((x - x0) / step - 0.5, (y - y0) / step - 0.5) for x, y in pp]
        if len(q) > 1: d.line(q, fill=1, width=3)
    m = np.asarray(im).astype(np.float32)
    if not m.any(): Z[0] = None; log('rail grade: no railway in the block'); return 0
    s = P['sigma'] / step
    num = ndi.gaussian_filter(dem * m, s, mode='nearest'); den = ndi.gaussian_filter(m, s, mode='nearest')
    avg = num / np.maximum(den, 1e-6)
    # the ground near the line (not just on it): a cut or fill is judged against the ground the formation crosses
    g = ndi.gaussian_filter(dem * m, 2.0) / np.maximum(ndi.gaussian_filter(m, 2.0), 1e-6)
    f = avg + P['lift']
    f = np.clip(f, g - P['max_cut'], g + P['max_fill'])
    f = ndi.gaussian_filter(f * m, 6.0) / np.maximum(ndi.gaussian_filter(m, 6.0), 1e-6)   # (the clip leaves kinks: eased over ~25 m)
    f[den < 1e-4] = np.nan
    Z[0] = (f.astype(np.float32), float(x0), float(y0), float(step))
    on = m > 0; dz = (f - dem)[on]
    log('rail grade: %d px of line, formation over ground median %.2f m, p5 %.2f, p95 %.2f, cut > 1 m %.1f %%, fill > 2 m %.1f %%'
        % (on.sum(), np.median(dz), np.percentile(dz, 5), np.percentile(dz, 95), 100 * (dz < -1).mean(), 100 * (dz > 2).mean()))
    return int(on.sum())

def sample(gx, gy):
    """formation height at block metres (arrays); NaN where no railway is near"""
    f, x0, y0, st = Z[0]
    c = (gx - x0) / st - 0.5; r = (gy - y0) / st - 0.5
    ff = np.where(np.isfinite(f), f, 0.0); ok = np.isfinite(f).astype(np.float32)
    v = ndi.map_coordinates(ff, [r.ravel(), c.ravel()], order=1, mode='nearest').reshape(gx.shape)
    w = ndi.map_coordinates(ok, [r.ravel(), c.ravel()], order=1, mode='nearest').reshape(gx.shape)
    return np.where(w > 0.5, v / np.maximum(w, 1e-6), np.nan)

def apply(h, rail_px, road_mask, ox, oy, pad=64):
    """h: the cell's ground at 0.5 m (4096^2, row 0 = south), changed in place; rail_px: polylines in cell metres (1 m
    pixels, row 0 = south, may run past the cell); road_mask: roads / tracks at 1 m; ox, oy: block metres of the cell's
    corner. -> mask (1 m) of the pixels changed."""
    if Z[0] is None or not rail_px: return None
    n = 2048; N = n + 2 * pad
    im = Image.new('L', (N, N), 0); d = ImageDraw.Draw(im)
    for pp in rail_px: d.line([(x + pad, y + pad) for x, y in pp], fill=1, width=1)
    li = np.asarray(im) > 0
    if not li.any(): return None
    dist = ndi.distance_transform_edt(~li)[pad:-pad, pad:-pad].astype(np.float32)
    reach = P['crest'] + P['ramp'] * (P['max_fill'] + 1.0)
    sel = dist <= reach
    if not sel.any(): return None
    yy, xx = np.nonzero(sel)
    z = sample(ox + xx + 0.5, oy + yy + 0.5)
    ok = np.isfinite(z); yy, xx, z = yy[ok], xx[ok], z[ok]
    # the side slope: 1:side off the roads, 1:ramp on them (blended over ~6 m so the ramp has no edge)
    rw = ndi.gaussian_filter(road_mask.astype(np.float32), 3.0)
    k = P['side'] + (P['ramp'] - P['side']) * np.clip(rw[yy, xx] * 2.0, 0.0, 1.0)
    dd = np.maximum(dist[yy, xx] - P['crest'], 0.0) / k
    h2 = h.reshape(n, 2, n, 2).mean((1, 3))
    g = h2[yy, xx]
    new = np.where(z >= g, np.maximum(g, z - dd), np.minimum(g, z + dd))   # fill: down to the ground; cut: up to it
    dl = np.zeros((n, n), np.float32); dl[yy, xx] = new - g
    ch = np.abs(dl) > 1e-3
    if not ch.any(): return None
    dl = ndi.gaussian_filter(dl, 0.7)                                         # (the 1 m steps at 0.5 m)
    h += np.repeat(np.repeat(dl, 2, 0), 2, 1).astype(h.dtype)
    return ch

"""Ground texture layers by example from Graviteam's own cells (texture quilting).

The first two generators sampled or synthesised mat_map / det_map / grass_map / land_ambient_col pixel by pixel and
never looked like the game's maps. Petropolye (Stalingrad-Donets DLC, same season table tabs\\season_ua_summer as
Mius-Front) is the reference the user pointed at: its fields are soil 6 with horizontal rows of soil-7 dashes every
4 m and 10-30 m green blobs, its ploughed land soil 15 with a 4/8/10 micro-tile pattern, its steppe soil 0 with
natural marsh/clay/sand patches, and the detail / ambient layers belong to those pixels. So instead of imitating the
statistics we copy the real thing: the target cell is cut into irregular Voronoi regions (~80 m), and every region
takes all its layers from a random window of a reference cell that carries the same surface class, pixel for pixel.

Classes copied with their soil pattern (the target soil is overwritten inside the class mask):
  crop   ripe grain          (6 with 7 dashes / blobs, a few 0 specks)
  green  green field crop    (7 with 6 / 0 patches)
  plough ploughed / fallow   (15)
  steppe open grass          (0 with 1 / 3 / 5 / 13 patches)
Everything else keeps the target soil and gets micro tile, det, grass and ambient colour from the per-soil pools
(pixels of other soils inside the source window are filled from the nearest valid pixel).  Reference cells: the three
Petropolye village cells (pgd5, pge4, pgf6) and the Mius template cell for the soils Petropolye has not got (8, 9, 14).
"""
import os
import numpy as np
from scipy import ndimage as ndi
import atf1

WIN = 160           # source window side (px = m); a region reaches at most (0.5 + JIT) * STEP * sqrt(2) ~ 77 px from its seed
STEP = 64           # Voronoi seed spacing
JIT = 0.35          # seed jitter (fraction of STEP)
SOILS = 16

CROP, PLOUGH, STEPPE = 1, 3, 4
# class -> (soils allowed inside the window, {soil: min fraction}, {soil: max fraction}).  Petropolye has no large
# green (7) fields - soil 7 is the blobs inside the ripe fields and the garden plots - so a green field is plain soil 7
# from the per-soil pool with its own plants.
CLASS_SPEC = {
    CROP:   ({0, 6, 7},               {6: 0.55}, {11: 0.02, 3: 0.02, 10: 0.02, 15: 0.02, 13: 0.02, 1: 0.02, 5: 0.02}),
    PLOUGH: ({0, 1, 3, 5, 13, 15},    {15: 0.6}, {11: 0.03, 10: 0.03, 6: 0.03, 7: 0.03}),
    STEPPE: ({0, 1, 3, 5, 13, 15},    {0: 0.55}, {6: 0.01, 7: 0.01, 10: 0.01, 11: 0.01, 12: 0.01}),
}
CLASS_SOIL = {CROP: 6, PLOUGH: 15, STEPPE: 0}   # what a copied pixel falls back to when the source pixel is of a soil outside the class


def _grid(path, n=2048):
    return np.fromfile(path, np.uint8).reshape(n, n)


def _window_fractions(soil, stride):
    """fraction of every soil inside each WIN x WIN window with its top-left corner on the stride grid"""
    n = soil.shape[0]; k = (n - WIN) // stride + 1
    out = np.zeros((SOILS, k, k), np.float32)
    for s in range(SOILS):
        m = (soil == s).astype(np.int32)
        c = np.pad(np.cumsum(np.cumsum(m, 0), 1), ((1, 0), (1, 0)))
        ys = np.arange(k) * stride; xs = np.arange(k) * stride
        a = c[np.ix_(ys + WIN, xs + WIN)] - c[np.ix_(ys, xs + WIN)] - c[np.ix_(ys + WIN, xs)] + c[np.ix_(ys, xs)]
        out[s] = a / float(WIN * WIN)
    return out


class Ref:
    def __init__(self, dirs, mius_dir=None, stride=16, verbose=True):
        self.cells = []
        for d in list(dirs) + ([mius_dir] if mius_dir else []):
            if not os.path.exists(os.path.join(d, 'mat_map.cell.loc_def.bin')): continue
            mat = _grid(os.path.join(d, 'mat_map.cell.loc_def.bin'))
            self.cells.append(dict(name=os.path.basename(d.rstrip('/\\')), soil=mat & 15, hi=mat >> 4,
                                   grass=_grid(os.path.join(d, 'grass_map.cell.loc_def.bin')),
                                   det=atf1.top(os.path.join(d, 'det_map.cell.loc_def.bin')),
                                   lac=atf1.top(os.path.join(d, 'land_ambient_col.cell.loc_def.bin')),
                                   vars=_grid(os.path.join(d, 'vars_map.cell.loc_def.bin'), 1024),
                                   mius=(d == mius_dir)))
        if not self.cells: raise RuntimeError('no reference cells found in ' + ', '.join(dirs))
        self.stride = stride
        fr = [_window_fractions(c['soil'], stride) for c in self.cells]
        # class windows
        self.cand = {}
        for cls, (allowed, need, forbid) in CLASS_SPEC.items():
            self.cand[cls] = self._select(fr, allowed, need, forbid, classes_only=True)
        # per-soil pools
        self.pool = {}
        for s in range(SOILS):
            lst = []
            for thr in (0.8, 0.6, 0.45, 0.3, 0.15, 0.05):
                lst = self._select(fr, None, {s: thr}, {}, classes_only=False, prefer_petro=True)
                if len(lst) >= 40: break
            self.pool[s] = lst
        if verbose:
            print('  texref: %d reference cells; windows per class: %s; per soil: %s' % (
                len(self.cells), {k: len(v) for k, v in self.cand.items()}, {s: len(v) for s, v in self.pool.items() if v}), flush=True)

    def _select(self, fr, allowed, need, forbid, classes_only, prefer_petro=False):
        out = []
        for ci, (c, f) in enumerate(zip(self.cells, fr)):
            if classes_only and c['mius']: continue
            ok = np.ones(f.shape[1:], bool)
            if allowed is not None:
                other = sum(f[s] for s in range(SOILS) if s not in allowed); ok &= other <= 0.03
            for s, v in need.items(): ok &= f[s] >= v
            for s, v in forbid.items(): ok &= f[s] <= v
            ys, xs = np.nonzero(ok)
            out += [(ci, int(y) * self.stride, int(x) * self.stride) for y, x in zip(ys, xs)]
        if prefer_petro and len(out) >= 40:
            petro = [o for o in out if not self.cells[o[0]]['mius']]
            if len(petro) >= 40: out = petro
        return out

    # ------------------------------------------------------------------ application
    def apply(self, soil, cls, rng, origin=(0, 0), seed_step=STEP):
        """soil: (n,n) uint8 target soils (modified in place for the copied classes); cls: (n,n) uint8 class map
        (0 = keep soil, use the per-soil pools); origin: (x, y) metres of the cell in the block, so that the region
        seeds, the source windows and the pixel mapping are the same on both sides of a cell border (no seams).
        Returns dict(hi, det, grass, lac, vars)."""
        n = soil.shape[0]; ox0, oy0 = int(origin[0]), int(origin[1])
        lab, seeds = self._voronoi(n, ox0, oy0, seed_step)
        hi = np.zeros((n, n), np.uint8); grass = np.zeros((n, n), np.uint8); det = np.zeros((n, n, 4), np.uint8)
        lac = np.zeros((n // 8, n // 8, 4), np.uint8); vrs = np.zeros((n // 2, n // 2), np.uint8)
        lac_done = np.zeros((n // 8, n // 8), bool); vrs_done = np.zeros((n // 2, n // 2), bool)
        objs = ndi.find_objects(lab, max_label=len(seeds))
        half = WIN // 2
        for r, sl in enumerate(objs, start=1):
            if sl is None: continue
            gy, gx, spy, spx = seeds[r - 1]          # global seed grid index and seed position (cell pixels)
            ys, xs = sl; y0, x0 = ys.start, xs.start
            reg = lab[sl] == r
            c_reg = cls[sl]; s_reg = soil[sl]
            counts = {}
            for v in np.unique(c_reg[reg]):
                if v == 0:
                    for sv in np.unique(s_reg[reg & (c_reg == 0)]): counts[('s', int(sv))] = int(((c_reg == 0) & (s_reg == sv) & reg).sum())
                else: counts[('c', int(v))] = int(((c_reg == v) & reg).sum())
            if not counts: continue
            dom = max(counts, key=counts.get)
            for key in counts:
                kind, v = key
                src = self._pick(kind, v, gy, gx)
                if src is None: continue
                ci, sy, sx = src; cell = self.cells[ci]
                m = reg & ((c_reg == v) if kind == 'c' else ((c_reg == 0) & (s_reg == v)))
                ry, rx = np.nonzero(m); py = y0 + ry; px = x0 + rx
                # source pixel = window centre + offset from the region seed (identical in the neighbouring cell)
                qy = np.clip(np.rint(sy + half + (py - spy)), sy, sy + WIN - 1).astype(np.int64); qx = np.clip(np.rint(sx + half + (px - spx)), sx, sx + WIN - 1).astype(np.int64)
                if kind == 'c':
                    allowed, _, _ = CLASS_SPEC[v]
                    ss = cell['soil'][qy, qx]
                    bad = ~np.isin(ss, list(allowed))
                    if bad.any(): ss = ss.copy(); ss[bad] = CLASS_SOIL[v]
                    soil[py, px] = ss
                    hi[py, px] = cell['hi'][qy, qx]; grass[py, px] = cell['grass'][qy, qx]; det[py, px] = cell['det'][qy, qx]
                else:
                    win = cell['soil'][sy:sy + WIN, sx:sx + WIN] == v
                    if win.all():
                        hi[py, px] = cell['hi'][qy, qx]; grass[py, px] = cell['grass'][qy, qx]; det[py, px] = cell['det'][qy, qx]
                    else:   # nearest valid pixel of the wanted soil inside the window
                        _, idx = ndi.distance_transform_edt(~win, return_indices=True)
                        ly, lx = qy - sy, qx - sx
                        vy = sy + idx[0][ly, lx]; vx = sx + idx[1][ly, lx]
                        hi[py, px] = cell['hi'][vy, vx]; grass[py, px] = cell['grass'][vy, vx]; det[py, px] = cell['det'][vy, vx]
                if key == dom:   # coarse layers from the same place: ambient colour (8 m) and vars (2 m), block centres mapped like the pixels
                    l_sl = (slice(y0 // 8, (ys.stop + 7) // 8), slice(x0 // 8, (xs.stop + 7) // 8))
                    ly, lx = np.nonzero(~lac_done[l_sl])
                    if len(ly):
                        cy_ = (l_sl[0].start + ly) * 8 + 4; cx_ = (l_sl[1].start + lx) * 8 + 4
                        gqy = (np.clip(np.rint(sy + half + (cy_ - spy)), sy, sy + WIN - 1) // 8).astype(np.int64); gqx = (np.clip(np.rint(sx + half + (cx_ - spx)), sx, sx + WIN - 1) // 8).astype(np.int64)
                        lac[l_sl][ly, lx] = cell['lac'][gqy, gqx]; lac_done[l_sl][ly, lx] = True
                    v_sl = (slice(y0 // 2, (ys.stop + 1) // 2), slice(x0 // 2, (xs.stop + 1) // 2))
                    vy_, vx_ = np.nonzero(~vrs_done[v_sl])
                    if len(vy_):
                        cy_ = (v_sl[0].start + vy_) * 2 + 1; cx_ = (v_sl[1].start + vx_) * 2 + 1
                        gqy = (np.clip(np.rint(sy + half + (cy_ - spy)), sy, sy + WIN - 1) // 2).astype(np.int64); gqx = (np.clip(np.rint(sx + half + (cx_ - spx)), sx, sx + WIN - 1) // 2).astype(np.int64)
                        vrs[v_sl][vy_, vx_] = cell['vars'][gqy, gqx]; vrs_done[v_sl][vy_, vx_] = True
        if not lac_done.all():
            _, idx = ndi.distance_transform_edt(~lac_done, return_indices=True); lac = lac[idx[0], idx[1]]
        if not vrs_done.all():
            _, idx = ndi.distance_transform_edt(~vrs_done, return_indices=True); vrs = vrs[idx[0], idx[1]]
        return dict(hi=hi, det=det, grass=grass, lac=lac, vars=vrs)

    def _pick(self, kind, v, gy, gx):
        """source window for (class / soil) in the region of global seed (gy, gx): deterministic in the seed"""
        lst = self.cand[v] if kind == 'c' else self.pool.get(v, [])
        if not lst:
            if kind == 'c': return None
            for alt in FALLBACK.get(v, []):
                if self.pool.get(alt): lst = self.pool[alt]; break
            if not lst: return None
        return lst[_hash(gy, gx, (v + 1) * (7 if kind == 'c' else 13)) % len(lst)]

    @staticmethod
    def _voronoi(n, ox0, oy0, step):
        """irregular regions from a jittered global seed grid (block coordinates): every pixel takes the nearest of the
        seeds in its 3 x 3 grid neighbourhood.  Returns (labels 1.., [(gy, gx, seed_y, seed_x) per label])."""
        gy0 = oy0 // step - 1; gx0 = ox0 // step - 1             # global grid index of the first local seed row / column
        k = n // step + 3
        gy, gx = np.mgrid[0:k, 0:k]; GY = gy + gy0; GX = gx + gx0
        jy = (_hash_arr(GY, GX, 1) / 2 ** 32 - 0.5) * 2 * JIT * step; jx = (_hash_arr(GY, GX, 2) / 2 ** 32 - 0.5) * 2 * JIT * step
        sy = GY * step + step / 2 + jy - oy0; sx = GX * step + step / 2 + jx - ox0   # seed positions in cell pixels
        yy, xx = np.mgrid[0:n, 0:n]
        by = np.clip((yy + oy0) // step - gy0, 1, k - 2); bx = np.clip((xx + ox0) // step - gx0, 1, k - 2)
        best = None; blab = None
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                cy = by + dy; cx = bx + dx
                d = (yy - sy[cy, cx]) ** 2 + (xx - sx[cy, cx]) ** 2
                l = cy * k + cx
                if best is None: best, blab = d, l
                else:
                    m = d < best; best = np.where(m, d, best); blab = np.where(m, l, blab)
        u, inv = np.unique(blab, return_inverse=True)
        seeds = [(int(GY.ravel()[i]), int(GX.ravel()[i]), float(sy.ravel()[i]), float(sx.ravel()[i])) for i in u]
        return (inv.reshape(n, n) + 1).astype(np.int32), seeds


def _hash(a, b, c):
    h = (int(a) * 73856093) ^ (int(b) * 19349663) ^ (int(c) * 83492791)
    h = (h ^ (h >> 13)) * 1274126177 & 0xffffffff
    return (h ^ (h >> 16)) & 0x7fffffff

def _hash_arr(a, b, c):
    a = a.astype(np.int64); b = b.astype(np.int64)
    h = ((a * 73856093) ^ (b * 19349663) ^ (c * 83492791)) & 0xffffffff
    h = ((h ^ (h >> 13)) * 1274126177) & 0xffffffff
    return (h ^ (h >> 16)) & 0xffffffff

FALLBACK = {8: [11, 3], 9: [11, 3], 14: [3, 11], 2: [3], 4: [3, 5], 12: [13], 13: [12]}

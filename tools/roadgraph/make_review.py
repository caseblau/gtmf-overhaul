#!/usr/bin/env python3
r"""C2 gate material (roadgraph N1 v2): per 1 km tile review sheets for a separate reviewer.

  python3 make_review.py <roads.json> <outdir> [--region x0 y0 x1 y1] [--ref-dir DIR] [--tiles T0512,T0513,...]

For every 1 km tile (1024 m square of the block, Trrcc, row 0 at the north edge) that overlaps the region it writes
<outdir>/tiles/Trrcc.png: left the sheet crop at 2x (2 image px per 4 m sheet px), right the same
crop with ink_clean in grey, the traced lines in colour (red secondary, blue track, green path, magenta residential) and
every UNCOVERED ink_skel piece >= 60 m (skeleton farther than 12 m from any traced line, split at its junctions).  Pieces are split by a
road-likeness filter: ROAD-LIKE (yellow, numbered, to be judged) = length >= 120 m, low mean curvature (length-weighted chord / arc of its
edges >= 0.9, >= 0.8 for pieces >= 300 m, >= 0.95 if the line is dashed - supplementary contours are dashed arcs),
less than half of it within 10 m of contour line work (contours.png), less than half on brownish line work (warm.png:
half-contours, ravine teeth), less than half inside lettering boxes (lettering.png); all others are drawn in light cyan as an info layer (listed with the reason, no verdict needed).
<outdir>/uncovered.json lists the pieces: {id, tile, length_m, x, y, bbox_m, road_like, reason, verdict: null}; the
reviewer sets verdict to "road" (must be traced) or "not-road" for every road_like piece.  C2 passes when no piece is
"road".  <outdir>/index.md lists the tiles with their piece counts.  Deterministic.
"""
import sys, os, json, math, argparse
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
Image.MAX_IMAGE_PIXELS = None
BLOCK = (0.0, 2048.0, 18432.0, 20480.0); TILE = 1024.0; NT = 18; TOL = 12.0; MIN_PIECE = 60.0
SHEET = '/mnt/user-data/uploads/gtmf-overhaul/docs/m12_terrain/period/rkka100k_block.png'
COL = {'secondary': (230, 0, 0), 'track': (0, 70, 255), 'path': (0, 160, 0), 'residential': (220, 0, 220)}

def m_to_px(x, y): return x / 4.0, (24576.0 - y) / 4.0
def px_to_m(px, py): return 4.0 * px, 24576.0 - 4.0 * py

def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument('roads'); ap.add_argument('outdir')
    ap.add_argument('--region', nargs=4, type=float, default=None); ap.add_argument('--ref-dir', default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument('--sheet', default=SHEET); ap.add_argument('--tiles', default=None)
    a = ap.parse_args(argv); RD = a.ref_dir
    reg = tuple(a.region) if a.region else BLOCK
    os.makedirs(os.path.join(a.outdir, 'tiles'), exist_ok=True)
    ink = np.asarray(Image.open(os.path.join(RD, 'ink_clean.png'))) > 0
    skel = np.asarray(Image.open(os.path.join(RD, 'ink_skel.png'))) > 0
    void = np.asarray(Image.open(os.path.join(RD, 'void.png'))) > 0
    cont = ndi.binary_dilation(np.asarray(Image.open(os.path.join(RD, 'contours.png'))) > 0, iterations=3)
    lett = np.asarray(Image.open(os.path.join(RD, 'lettering.png'))) > 0
    inkd = ndi.binary_dilation(np.asarray(Image.open(os.path.join(RD, 'ink_clean.png'))) > 0, iterations=1)
    warm = ndi.binary_dilation(np.asarray(Image.open(os.path.join(RD, 'warm.png'))) > 0, iterations=1)
    sheet = np.asarray(Image.open(a.sheet).convert('RGB'))
    J = json.load(open(a.roads, encoding='utf-8'))
    roads = [(r.get('highway', ''), np.asarray(r['pts'], float)) for r in J['roads'] if len(r['pts']) >= 2]
    pts = []
    for _, p in roads:
        for A, B in zip(p[:-1], p[1:]):
            n = max(1, int(math.ceil(math.hypot(*(B - A)) / 2.0))); pts += [A + (B - A) * k / n for k in range(n + 1)]
    T = cKDTree(np.array(pts)) if pts else None
    # uncovered skeleton pieces (8-connected), >= 60 m long, outside void
    ry, rx = np.nonzero(skel); X, Y = px_to_m(rx, ry)
    d = T.query(np.c_[X, Y])[0] if T is not None else np.full(len(rx), np.inf)
    unc = np.zeros_like(skel); m = (d > TOL) & ~void[ry, rx]; unc[ry[m], rx[m]] = True
    # judge every edge on its own: split the uncovered skeleton at its junction pixels
    nbu = ndi.convolve(unc.astype(np.uint8), np.ones((3, 3), np.uint8), mode='constant') - unc
    unc &= ~(unc & (nbu >= 3))
    lab, n = ndi.label(unc, structure=np.ones((3, 3)))
    pieces = []; piece_px = {}
    if n:
        sl = ndi.find_objects(lab); cnt = ndi.sum(unc, lab, range(1, n + 1))
        for k, q in enumerate(sl):
            yy, xx = np.nonzero(lab[q] == k + 1); yy = yy + q[0].start; xx = xx + q[1].start
            # length: 4 m per orthogonal step, 5.66 m per diagonal step (8-connected skeleton, half per neighbour)
            sub = lab[q] == k + 1
            K4 = ndi.convolve(sub.astype(np.uint8), np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]], np.uint8), mode='constant')[sub]
            KD = ndi.convolve(sub.astype(np.uint8), np.array([[1, 0, 1], [0, 0, 0], [1, 0, 1]], np.uint8), mode='constant')[sub]
            L = float((4.0 * K4 + 5.657 * KD).sum() / 2.0)
            span = 4.0 * math.hypot(xx.max() - xx.min(), yy.max() - yy.min())
            if max(L, span) < MIN_PIECE or span < MIN_PIECE * 0.5: continue
            cx, cy = px_to_m(xx.mean(), yy.mean())
            # mean curvature: length-weighted chord / arc of the piece's edges between junctions (>= 32 m)
            nbk = ndi.convolve(sub.astype(np.uint8), np.ones((3, 3), np.uint8), mode='constant') - sub
            ed = sub & ~ndi.binary_dilation(sub & (nbk >= 3), structure=np.ones((3, 3)))
            el_, en_ = ndi.label(ed, structure=np.ones((3, 3))); ch = 0.0; ar = 0.0
            for qq in ndi.find_objects(el_):
                if qq is None: continue
                e_ = el_[qq] > 0; ny, nx = np.nonzero(e_)
                if len(ny) < 8: continue
                # chord = distance between the two farthest-apart end pixels (ends: 1 neighbour)
                ne = ndi.convolve(e_.astype(np.uint8), np.ones((3, 3), np.uint8), mode='constant')[e_] - 1
                ends = np.c_[nx, ny][ne <= 1]
                if len(ends) < 2: continue
                dd_ = np.hypot(*(ends[:, None, :] - ends[None, :, :]).transpose(2, 0, 1)); ch += dd_.max(); ar += len(ny)
            if ar >= 0.5 * len(yy): straight = ch / ar
            else:                                  # mostly junction knots / short edges: major-axis extent / length
                ev, evec = np.linalg.eigh(np.cov(np.stack([xx, yy]).astype(float))); u = evec[:, 1]
                pr = xx * u[0] + yy * u[1]; straight = min(1.0, 4.0 * (pr.max() - pr.min()) / max(L, 1e-6))
            fc = float(cont[yy, xx].mean()); fl = float(lett[yy, xx].mean()); fw = float(warm[yy, xx].mean()); fi = float(inkd[yy, xx].mean())
            curved = straight < (0.8 if L >= 300 else 0.9) or (fi < 0.8 and straight < 0.95)
            why = [w for w, bad in (('short (< 120 m)', L < 120), ('curved (chord / arc %.2f%s)' % (straight, ', dashed' if fi < 0.8 else ''), curved),
                                     ('brownish line work (%.0f %%)' % (100 * fw), fw >= 0.5),
                                     ('hugs contour line work (%.0f %%)' % (100 * fc), fc >= 0.5), ('in lettering (%.0f %%)' % (100 * fl), fl >= 0.5)) if bad]
            if not (reg[0] <= cx < reg[2] and reg[1] <= cy < reg[3]): continue
            r_ = int((BLOCK[3] - cy) // TILE); c_ = int((cx - BLOCK[0]) // TILE)
            x0, y1_ = px_to_m(xx.min(), yy.min()); x1, y0_ = px_to_m(xx.max(), yy.max())
            pieces.append(dict(tile='T%02d%02d' % (r_, c_), length_m=round(L), x=round(cx, 1), y=round(cy, 1),
                               bbox_m=[round(x0), round(y0_), round(x1), round(y1_)], road_like=not why, reason='; '.join(why) or 'road-like',
                               verdict=None, _k=k + 1))
    pieces.sort(key=lambda p: (not p['road_like'], p['tile'], -p['y'], p['x']))
    nr = 0; ni = 0
    for p in pieces:
        if p['road_like']: nr += 1; p['id'] = 'U%04d' % nr
        else: ni += 1; p['id'] = 'I%04d' % ni; p.pop('verdict')
        piece_px[p['_k']] = p['id']
    keepk = np.zeros(n + 1, bool); keepk[[p['_k'] for p in pieces if p['road_like']]] = True
    infok = np.zeros(n + 1, bool); infok[[p['_k'] for p in pieces if not p['road_like']]] = True
    upiece = keepk[lab]; ipiece = infok[lab]
    want = set(a.tiles.split(',')) if a.tiles else None
    index = ['# C2 review sheets', '', 'roads: `%s`' % a.roads, '', 'Yellow (numbered U....) = road-like ink skeleton piece >= 120 m farther than 12 m from every traced line: set its verdict '
             'in uncovered.json to "road" or "not-road". Light cyan (I....) = other uncovered pieces, info only.', '', '| tile | road-like pieces | sheet |', '|---|---|---|']
    S2 = 2
    for r_ in range(NT):
        for c_ in range(NT):
            name = 'T%02d%02d' % (r_, c_)
            bx = (c_ * TILE, BLOCK[3] - (r_ + 1) * TILE, (c_ + 1) * TILE, BLOCK[3] - r_ * TILE)
            if bx[2] <= reg[0] or bx[0] >= reg[2] or bx[3] <= reg[1] or bx[1] >= reg[3]: continue
            if want and name not in want: continue
            px0, py0 = int(c_ * 256), int(1024 + r_ * 256); sl_ = np.s_[py0:py0 + 256, px0:px0 + 256]
            raw = sheet[sl_]
            o = np.full((256, 256, 3), 255, np.uint8); o[ink[sl_]] = (175, 175, 175)
            v = void[sl_]; o[v] = (o[v] * 0.7 + np.array((255, 240, 200)) * 0.3).astype(np.uint8)
            o[ndi.binary_dilation(ipiece[sl_])] = (150, 225, 240)
            up = ndi.binary_dilation(upiece[sl_]); o[up] = (255, 210, 0)
            L = Image.fromarray(raw).resize((512, 512), Image.LANCZOS); Rr = Image.fromarray(o).resize((512, 512), Image.NEAREST)
            dr = ImageDraw.Draw(Rr)
            for cls, p in roads:
                q = [((u / 4.0 - px0) * S2, ((24576.0 - w) / 4.0 - py0) * S2) for u, w in p]
                xs = [t[0] for t in q]; ys = [t[1] for t in q]
                if max(xs) < 0 or min(xs) > 512 or max(ys) < 0 or min(ys) > 512: continue
                dr.line(q, fill=COL.get(cls, (0, 0, 0)), width=2)
            tp = [p for p in pieces if p['tile'] == name and p['road_like']]
            for p in pieces:
                if not p['road_like']: continue
                ux, uy = m_to_px(p['x'], p['y']); ux = (ux - px0) * S2; uy = (uy - py0) * S2
                if 0 <= ux < 512 and 0 <= uy < 512:
                    dr.rectangle([ux + 3, uy - 6, ux + 40, uy + 6], fill=(255, 255, 255)); dr.text((ux + 4, uy - 6), p['id'], fill=(120, 80, 0))
            im = Image.new('RGB', (1030, 530), 'white'); im.paste(L, (0, 18)); im.paste(Rr, (518, 18))
            ImageDraw.Draw(im).text((2, 2), '%s  x %d-%d  y %d-%d   uncovered pieces: %d' % (name, bx[0], bx[2], bx[1], bx[3], len(tp)), fill=(0, 0, 0))
            im.save(os.path.join(a.outdir, 'tiles', name + '.png'), optimize=True)
            index.append('| %s | %d | tiles/%s.png |' % (name, len(tp), name))
    for p in pieces: p.pop('_k')
    json.dump(dict(meta=dict(roads=os.path.abspath(a.roads), region=list(reg), tolerance_m=TOL, min_piece_m=MIN_PIECE,
                             rule='C2 passes when no road_like piece has verdict "road"', road_like=sum(p['road_like'] for p in pieces), info=sum(not p['road_like'] for p in pieces)), pieces=pieces), open(os.path.join(a.outdir, 'uncovered.json'), 'w'), indent=1)
    open(os.path.join(a.outdir, 'index.md'), 'w').write('\n'.join(index) + '\n')
    R_ = [p for p in pieces if p['road_like']]; I_ = [p for p in pieces if not p['road_like']]
    print('uncovered pieces >= %.0f m: %d (%.1f km); road-like (to review) %d (%.1f km); info layer %d (%.1f km) -> %s' % (
        MIN_PIECE, len(pieces), sum(p['length_m'] for p in pieces) / 1000, len(R_), sum(p['length_m'] for p in R_) / 1000,
        len(I_), sum(p['length_m'] for p in I_) / 1000, a.outdir))

if __name__ == '__main__':
    main()

"""Settlement generator - steppe street villages the way Graviteam builds them.

Reference cells: the Petropolye polygon (Stalingrad-Donets DLC, 1943 summer, Graviteam's newest generator) PgD5 / PgE4 /
PgF6 and the Mius-Front MgG3 (Stepanovka).  Petropolye measurements: homesteads 40-100 m apart along the street (median
65-80 m), house centre 7-25 m from the road edge (median 13), gable to the street; 1-3 sheds per house 16-24 m from it,
in an L round a yard of clay / trampled ground (soils 3 and 10); a CONTINUOUS front fence along the whole village street
with a gate at every house, side fences 40-60 m deep between the plots, almost no back fences; behind every yard a garden
plot as wide as the homestead spacing and 120-200 m deep - sunflowers (soil 7 + flora 17) or maize / potato rows (soil 15
+ flora 13), hedges of bushes along the plot borders (soil 13 band + flora 7/8), fruit trees (10) and fruit bushes (15)
near the houses; haystacks, firewood, benches; the kolkhoz yard apart from the village with long barns (farm0 / farm1).
The Psel hamlets of 1943 (Vasilyevka, Andreyevka, Mikhaylovka, Prelestnoye, Petrovka) were exactly such one-street valley
villages - houses on the landward side of the street, gardens running down to the river.

OpenStreetMap carries almost no footprints for them (Andreyevka: 1), so the homesteads are generated along the OSM streets
inside the residential polygons (trimmed to the 1941 built-up extent by prokh_gen); OSM footprints are kept.
Coordinates: cell pixels (1 px = 1 m), row 0 = south.
"""
import math, numpy as np
from PIL import Image, ImageDraw, ImageFilter
import morph as MO

TAB_B = 'tabs\\builds.cfgpack'; TAB_BC = 'tabs\\builds_cap.cfgpack'; TAB_O = 'tabs\\objects.cfgpack'; TAB_F = 'tabs\\fences.cfgpack'; TAB_S = 'tabs\\structs.cfgpack'; TAB_P = 'tabs\\posts.cfgpack'
VILLAGE_SOIL = 10; CLAY = 3; FIELD = 6; FIELD_GREEN = 7; SAND = 5; LEAVES = 13; PLOUGH = 15
FL_SUNFL = 17; FL_CORN = 13; FL_BUSH = 7; FL_BUSH2 = 8; FL_GARDEN = 10; FL_CULTBUSH = 15

def _resample(pp, step):
    out = []; carry = 0.0
    for (ax, ay), (bx, by) in zip(pp, pp[1:]):
        L = math.hypot(bx - ax, by - ay)
        if L < 1e-6: continue
        ux, uy = (bx - ax) / L, (by - ay) / L; t = carry
        while t < L:
            out.append((ax + ux * t, ay + uy * t, ux, uy)); t += step
        carry = t - L
    return out

def _inside(x, y): return 0 <= x < 2048 and 0 <= y < 2048

def _rect(cx, cy, ux, uy, half_w, d0, d1):
    """polygon from the street point (cx, cy), street direction (ux, uy): +-half_w along the street, d0..d1 along the normal"""
    nx, ny = -uy, ux
    return [(cx + ux * half_w + nx * d0, cy + uy * half_w + ny * d0), (cx - ux * half_w + nx * d0, cy - uy * half_w + ny * d0),
            (cx - ux * half_w + nx * d1, cy - uy * half_w + ny * d1), (cx + ux * half_w + nx * d1, cy + uy * half_w + ny * d1)]

def _fence(objs, a, b, node, blocked, gates=(), posts=True):
    ax, ay = a; bx, by = b
    L = math.hypot(bx - ax, by - ay)
    if L < 2: return
    ux, uy = (bx - ax) / L, (by - ay) / L; ang = math.atan2(ux, uy) + math.pi / 2   # vanilla fence heading convention
    if posts and _inside(ax, ay) and not blocked[int(ay), int(ax)]: objs.append((TAB_P, 'fpost2', ax, ay, ang))
    t = 1.3
    while t < L:
        x, y = ax + ux * t, ay + uy * t
        g = next((gt for gt in gates if abs(t - gt) < 2.2), None)
        if g is not None:
            if abs(t - g) < 1.3 and _inside(x, y) and not blocked[int(y), int(x)]: objs.append((TAB_F, 'gates1' if g >= 0 else 'kalitka2', x, y, ang))
        elif _inside(x, y) and not blocked[int(y), int(x)]: objs.append((TAB_F, node, x, y, ang))
        t += 2.6

def build(cov, soil, lines, buildings, slope2, rng, VIL, WATER_C, MARSH_C, ROAD_C, TRACK_C, RAIL_C, BUILDING_C, farm_mask=None, cell_seed=0, origin=(0.0, 0.0), vil_pad=None, pad=0, works_mask=None):
    """returns (objs, flora) and paints yards / gardens / hedges into `soil` in place.
    objs: (table, node, x, y, angle); flora: list of (x, y, flora_type)"""
    objs = []; flora = []
    vil = cov == VIL; bmask = cov == BUILDING_C
    if vil_pad is not None and pad > 0:   # village cover with a margin: the extent is the same on both sides of a cell border
        ext = MO.dilate(vil_pad, 41)[pad:-pad, pad:-pad] | MO.dilate(bmask, 41)
        plot_ok = MO.dilate(vil_pad, 81)[pad:-pad, pad:-pad]
    else:
        ext = MO.dilate(vil | bmask, 41)   # village extent + 20 m
        plot_ok = MO.dilate(vil, 81)   # plots may run 40 m past the polygon
    if not ext.any(): return objs, flora
    road_img = Image.new('L', (2048, 2048), 0); dr = ImageDraw.Draw(road_img); streets = []
    for (pp, col, dash, c) in lines:
        if c in (ROAD_C, TRACK_C):
            dr.line(pp, fill=255, width=9 if c == ROAD_C else 5, joint='curve')
            if c == ROAD_C or True: streets.append((pp, c))
        elif c == RAIL_C: dr.line(pp, fill=255, width=30, joint='curve')
    road = np.asarray(road_img) > 0
    near_road = MO.dilate(np.asarray(road_img) > 0, 11)
    wet = (cov == WATER_C) | (cov == MARSH_C)
    wet_near = MO.dilate(wet, 41)
    blocked = near_road | wet_near | (slope2 > 0.12)
    if works_mask is not None: blocked |= works_mask   # no houses, sheds or fences on the trenches / the anti-tank ditch
    blocked |= MO.dilate(bmask, 41)   # 20 m off the OSM buildings
    if farm_mask is not None: blocked |= farm_mask
    taken_img = Image.new('L', (2048, 2048), 0); dtk = ImageDraw.Draw(taken_img)   # homestead footprints already used (drawn, not re-rasterised per house)
    yard = Image.new('L', (2048, 2048), 0); dy = ImageDraw.Draw(yard)          # 1 = clay yard, 2 = trampled village ground
    gard = Image.new('L', (2048, 2048), 0); dg = ImageDraw.Draw(gard)          # garden pattern id
    hedge = Image.new('L', (2048, 2048), 0); dh = ImageDraw.Draw(hedge)        # hedge bands (soil 13 + bushes)
    # --- 1. OSM footprints (Prokhorovka town, a few hamlets) kept as they are, with a yard
    for pp in buildings:
        if len(pp) > 1 and pp[0] == pp[-1]: pp = pp[:-1]
        if len(pp) < 3: continue
        cx = sum(p[0] for p in pp) / len(pp); cy = sum(p[1] for p in pp) / len(pp)
        if not _inside(cx, cy): continue
        best = max(zip(pp, pp[1:]), key=lambda e: math.hypot(e[1][0] - e[0][0], e[1][1] - e[0][1]))
        ang = math.atan2(best[1][1] - best[0][1], best[1][0] - best[0][0])
        area = abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pp, pp[1:] + pp[:1]))) / 2
        node = ('build%d' % rng.integers(0, 4)) if area > 60 else ('saray%d' % rng.integers(0, 4))
        objs.append((TAB_B, node, cx, cy, ang))
        dy.ellipse([cx - 16, cy - 16, cx + 16, cy + 16], fill=1)
    # --- 2. homesteads along the streets inside the village extent.  The walk along a street starts at the way's
    # global start and every decision is seeded by the street and the attempt index, so the cells on both sides of a
    # cell border place the same homesteads (a yard or plot straddling the border is drawn identically by both cells).
    def hash32(*v):
        h = 0
        for q in v: h = (h * 1000003 ^ (int(q) & 0xffffffff)) & 0xffffffff
        return (h ^ (h >> 15)) & 0x7fffffff
    def in_ext(x, y):   # village extent is known inside this cell only; outside it the walk assumes the street is built up
        return (ext[int(y), int(x)] > 0) if _inside(x, y) else True
    for (pp, c) in streets:
        pts = _resample(pp, 2.0)
        inside = [k for k, (x, y, ux, uy) in enumerate(pts) if _inside(x, y) and ext[int(y), int(x)]]
        if len(inside) < (1 if vil_pad is not None else 30): continue   # a street that only clips the cell still gets its homesteads' yards and plots drawn
        sseed = hash32(round(pp[0][0] + origin[0]), round(pp[0][1] + origin[1]), len(pp), cell_seed * 0)
        sr = np.random.default_rng(sseed)
        spacing = 48.0 + sr.random() * 30                       # Petropolye: 40-100 m between homesteads
        density = 0.7 + 0.3 * sr.random()
        depth = 80.0 + sr.random() * 60                         # garden plot depth (vanilla villages: yards ~40 % of the area, plots ~18 %)
        f_front = ['fence2a', 'fence2a', 'fence2a', 'fence4a', 'fence1a'][int(sr.integers(0, 5))]; f_side = ['fence2a', 'fence2a', 'fence2a', 'fence4a'][int(sr.integers(0, 4))]   # vanilla: fence2a ~90 %, no fence3a
        for si, side in enumerate((1.0, -1.0)):
            # front fence runs: the street front is fenced continuously where there are homesteads
            run = []; nh = 0; k = 0; t_next = sr.random() * spacing * 0.6; attempt = 0
            while k < len(pts):
                x, y, ux, uy = pts[k]
                here = _inside(x, y)
                if not in_ext(x, y):
                    if run: _front_run(objs, run, f_front, blocked); run = []
                    k += 1; continue
                nx, ny = -uy * side, ux * side
                if t_next > 0: t_next -= 2.0; k += 1; continue
                hr = np.random.default_rng(hash32(sseed, si, attempt)); attempt += 1
                hx, hy = x + nx * (16.0 + hr.random() * 6), y + ny * (16.0 + hr.random() * 6)   # vanilla street zone ~20 m: the house 16-22 m off the axis
                ok = hr.random() < density
                if ok and _inside(hx, hy): ok = not blocked[int(hy), int(hx)] and not taken_img.getpixel((int(hx), int(hy)))
                if ok:
                    half = spacing / 2 - 1.5
                    dev = max(-0.6, min(0.6, hr.normal(0.0, 0.26)))                      # vanilla: |angle to the street| median 15-25 deg, up to 35
                    ang = math.atan2(ny, nx) + dev + (math.pi / 2 if hr.random() < 0.2 else 0.0)   # a fifth stand with the long side to the street
                    nh += 1
                    if _inside(hx, hy): objs.append((TAB_B, 'build%d' % hr.integers(0, 4), hx, hy, ang))
                    else: hr.integers(0, 4)
                    # yard: clay ~30 x 30 m with trampled ground round the house
                    dy.polygon(_rect(x, y, ux * side, uy * side, half - 1.0, 7.5, 44.0), fill=1)   # the yard fills the street front (vanilla: clay / trampled ground ~40 % of the village)
                    dy.ellipse([hx - 9, hy - 9, hx + 9, hy + 9], fill=2)
                    dtk.polygon(_rect(x, y, ux * side, uy * side, half + 6, 0.0, 44.0), fill=255)
                    # 1-3 sheds in an L, 16-24 m from the house
                    for q in range(int(hr.integers(2, 5))):
                        sa = ang + [math.pi / 2, math.pi, -math.pi / 2][q % 3] + (hr.random() - 0.5) * 0.5; sd = 16.0 + hr.random() * 8
                        sx, sy = hx + math.cos(sa) * sd, hy + math.sin(sa) * sd
                        node = 'saray%d' % hr.integers(0, 4); rot = ang + (0.0 if hr.random() < 0.5 else math.pi / 2) + (hr.random() - 0.5) * 0.2   # vanilla sheds: 2-5 deg off the house
                        if _inside(sx, sy) and not blocked[int(sy), int(sx)] and not road[int(sy), int(sx)]:
                            objs.append((TAB_B, node, sx, sy, rot)); dy.ellipse([sx - 6, sy - 6, sx + 6, sy + 6], fill=2)
                    # front fence segment for this homestead (joined into one continuous run), gate beside the house
                    f0 = (x + nx * 9.5 - ux * half, y + ny * 9.5 - uy * half); f1 = (x + nx * 9.5 + ux * half, y + ny * 9.5 + uy * half)
                    run.append((f0, f1, half + 6.0))
                    pd = 40.0 + hr.random() * 20
                    if hr.random() < 0.8: _fence(objs, f0, (f0[0] + nx * pd, f0[1] + ny * pd), f_side, blocked)
                    if hr.random() < 0.15: _fence(objs, (f0[0] + nx * pd, f0[1] + ny * pd), (f1[0] + nx * pd, f1[1] + ny * pd), f_side, blocked, posts=False)
                    # garden plot behind the yard: pattern 1 sunflower (7), 2 maize / potato rows (15), 4 orchard (13)
                    pdepth = depth * (0.75 + 0.5 * hr.random())
                    pat = int(hr.choice([1, 2, 2, 2, 4, 4, 5, 5]))   # plots: 1 sunflower (1 in 8 - user, 25 Oct: too many), 2 maize / potato rows, 4 orchard, 5 hay meadow (grass)
                    dg.polygon(_rect(x, y, ux * side, uy * side, half - 2.0, 44.0, 44.0 + pdepth), fill=pat)
                    # hedges along the plot sides and the back
                    for s_ in (-1.0, 1.0):
                        if hr.random() < 0.7:
                            hx0, hy0 = x + ux * s_ * half, y + uy * s_ * half
                            dh.line([(hx0 + nx * 34, hy0 + ny * 34), (hx0 + nx * (40 + pdepth), hy0 + ny * (40 + pdepth))], fill=255, width=int(2 + hr.integers(0, 2)))   # Petropolye hedges: 2-3 m bands of leaves soil (measured 25 Oct: half-width 1 m)
                    if hr.random() < 0.5: dh.line([(x - ux * half + nx * (42 + pdepth), y - uy * half + ny * (42 + pdepth)), (x + ux * half + nx * (42 + pdepth), y + uy * half + ny * (42 + pdepth))], fill=255, width=int(2 + hr.integers(0, 2)))
                    # yard furniture and garden trees
                    if hr.random() < 0.6: objs.append((TAB_O, 'drova', hx + math.cos(ang + 2.4) * 9, hy + math.sin(ang + 2.4) * 9, ang))
                    if hr.random() < 0.45: objs.append((TAB_O, 'skameyka%d' % (1 + hr.integers(0, 2)), x + nx * 11.0 + ux * (half - 6), y + ny * 11.0 + uy * (half - 6), math.atan2(uy, ux)))
                    if hr.random() < 0.55: objs.append((TAB_O, ['seno_stog', 'seno_stog', 'seno_copna'][int(hr.integers(0, 3))], x + nx * (33 + hr.random() * 8) - ux * (half - 8), y + ny * (33 + hr.random() * 8) - uy * (half - 8), float(hr.random() * 6.28)))
                    if nh % 7 == 3: objs.append((TAB_S, 'well0', x + nx * 11.5 + ux * (half + 2), y + ny * 11.5 + uy * (half + 2), math.atan2(uy, ux)))
                    for _ in range(int(1 + hr.random() * 2)):   # 1-2 garden trees / bushes per homestead (was 2-5; user 25 Oct: too much flora)
                        tx, ty = hx + (hr.random() - 0.5) * 30 + nx * (8 + hr.random() * 14), hy + (hr.random() - 0.5) * 30 + ny * (8 + hr.random() * 14)
                        flora.append((tx, ty, int(hr.choice([FL_GARDEN, FL_GARDEN, FL_CULTBUSH]))))
                    t_next = spacing
                else:
                    t_next = 6.0
                k += 1
            if run: _front_run(objs, run, f_front, blocked)
    objs = [o for o in objs if _inside(o[2], o[3])]; flora = [f for f in flora if _inside(f[0], f[1])]
    # --- 3. paint the ground
    ym = np.asarray(yard); gm = np.asarray(gard)
    hm = np.asarray(hedge) > 0
    if hm.any():   # ragged hedge edges
        import texsynth as TX
        hf = np.asarray(Image.fromarray(hm.astype(np.uint8) * 255).filter(ImageFilter.GaussianBlur(2))).astype(np.float32) / 255.0
        hm = (hf + 0.2 * (0.6 * TX.gnoise(hm.shape, origin, 1, 41) + 0.8 * TX.gnoise(hm.shape, origin, 3.0, 42))) > 0.4   # global noise: the same ragged edge on both sides of a cell border
    hm &= plot_ok
    free = ~wet & ~near_road & ~bmask & (soil != VILLAGE_SOIL)   # the pave tracks of tools/tracks.py stay
    if works_mask is not None: free &= ~works_mask
    import texsynth as TX
    yn = TX.gnoise(soil.shape, origin, 6.0, 43)
    y1 = (ym == 1) & free; y2 = (ym == 2) & free
    soil[y1] = np.where(yn[y1] > 0.45, 11, np.where(yn[y1] < -0.5, VILLAGE_SOIL, CLAY)).astype(soil.dtype)   # yard: clay with patches of dark earth and packed ground
    soil[y2] = np.where(yn[y2] > 0.3, 11, VILLAGE_SOIL).astype(soil.dtype)
    gmask = (gm > 0) & plot_ok & free & (ym == 0) & ~hm
    yy, xx = np.nonzero(gmask)
    if len(yy):
        pat = gm[yy, xx]
        val = np.where(pat == 1, FIELD_GREEN, np.where(pat == 2, PLOUGH, np.where(pat == 3, FIELD, soil[yy, xx])))   # orchards (4) and hay meadows (5) keep the grass
        soil[yy, xx] = val.astype(soil.dtype)
        edge = gmask & ~MO.erode(gmask, 3)                                   # vanilla plots: a 1 m dark headland round every plot
        soil[edge] = 11
        # plants on the plots: sunflowers on 7 (dense), maize on the ploughed rows, fruit trees in the orchards
        for pid, ftype, dens in ((1, FL_SUNFL, 1 / 14.0), (2, FL_CORN, 1 / 18.0), (4, FL_GARDEN, 1 / 90.0)):
            sel = np.flatnonzero(pat == pid)
            if len(sel):
                pick = sel[rng.integers(0, len(sel), max(1, int(len(sel) * dens)))]
                flora += [(float(xx[p]) + rng.random(), float(yy[p]) + rng.random(), ftype) for p in pick]
    hm &= free & (ym == 0)
    soil[hm] = LEAVES
    hy_, hx_ = np.nonzero(hm)
    if len(hy_):
        pick = rng.integers(0, len(hy_), max(1, len(hy_) // 30))
        flora += [(float(hx_[p]) + rng.random(), float(hy_[p]) + rng.random(), int(rng.choice([FL_BUSH, FL_BUSH, FL_BUSH2]))) for p in pick]   # hedges: bushes only - fruit trees stay in the orchards and yards (user, 25 Oct: trees growing in the sunflower plots)
    return objs, flora

def _front_run(objs, run, node, blocked):
    """one continuous front fence along the street for a row of homesteads, a gate at each house.  Drawn homestead by
    homestead (f0 -> f1, then across the gap to the next f0) so that it follows a curving street; a gap of more than
    30 m between two homesteads is left open (the first version drew one straight line from the first to the last
    homestead, which cut across the street and the yards wherever the street bent)."""
    for n, (f0, f1, g) in enumerate(run):
        L = math.hypot(f1[0] - f0[0], f1[1] - f0[1])
        if L >= 2: _fence(objs, f0, f1, node, blocked, gates=[g])
        if n + 1 < len(run):
            n0 = run[n + 1][0]
            if math.hypot(n0[0] - f1[0], n0[1] - f1[1]) <= 30.0: _fence(objs, f1, n0, node, blocked, posts=False)

def kolkhoz(objs, soil, farm_mask, cov, rng, WATER_C, MARSH_C, BUILDING_C, road_mask=None, origin=(0.0, 0.0), works_mask=None):
    """sovkhoz / kolkhoz yards (OSM farmyard / industrial): long barns (farm0 / farm1) in rows round a clay yard, haystacks, a fence"""
    if farm_mask is None or not farm_mask.any(): return
    from scipy import ndimage
    if road_mask is not None: farm_mask = farm_mask & ~road_mask   # no barns or haystacks on the roads / tracks through the yard
    if works_mask is not None: farm_mask = farm_mask & ~works_mask
    lab, n = ndimage.label(farm_mask)
    for k in range(1, n + 1):
        m = lab == k; ys, xs = np.nonzero(m)
        if len(ys) < 1500: continue
        cx, cy = float(xs.mean()), float(ys.mean())
        # principal axis of the yard polygon
        cxx, cyy = xs - xs.mean(), ys - ys.mean(); ang = 0.5 * math.atan2(2 * (cxx * cyy).mean(), (cxx ** 2).mean() - (cyy ** 2).mean())
        ux, uy = math.cos(ang), math.sin(ang); nx, ny = -uy, ux
        half_len = math.sqrt(len(ys)) * 0.4
        # the yard: vanilla farm ground (Petropolye PgD5) is a mottled mix - clay 30 / grass 28 / dark earth 13 / pave 10 / leaves 9 / sand 4 %,
        # not a clean clay apron; here by global noise so the neighbouring cell paints the same patches
        import texsynth as TX
        yn = TX.gnoise(soil.shape, origin, 5.0, 44); yn2 = TX.gnoise(soil.shape, origin, 2.0, 45)
        ym = m & (cov != WATER_C) & (cov != MARSH_C) & (soil == 0)
        soil[ym & (yn > -0.15)] = CLAY
        soil[ym & (yn > 0.55)] = 2                                   # black earth (dung / dark soil) patches - never soil 1, the engine draws it as water
        soil[ym & (yn < -0.15) & (yn2 > 0.4)] = VILLAGE_SOIL          # packed pave patches on the grass
        soil[ym & (yn2 < -0.8)] = SAND
        n_rows = 2 if len(ys) > 6000 else 1
        for r in range(n_rows):
            off = (r - (n_rows - 1) / 2) * 45
            t = -half_len + 20
            while t < half_len - 20:
                bx, by = cx + ux * t + nx * off, cy + uy * t + ny * off
                if 0 <= bx < 2048 and 0 <= by < 2048 and m[int(by), int(bx)] and cov[int(by), int(bx)] != BUILDING_C:
                    objs.append((TAB_BC, 'farm%d' % rng.integers(0, 2), bx, by, ang + (rng.random() - 0.5) * 0.12))
                t += 34 + rng.random() * 8
        for _ in range(int(3 + len(ys) / 3000)):   # vanilla farm yard: 6 seno_cyl, 4 copna, 2 stog within 120 m
            p = rng.integers(0, len(ys)); objs.append((TAB_O, ['seno_cyl', 'seno_cyl', 'seno_copna', 'seno_stog'][int(rng.integers(0, 4))], float(xs[p]), float(ys[p]), float(rng.random() * 6.28)))
        for _ in range(int(1 + len(ys) / 6000)):   # sheds and a woodpile by the barns
            p = rng.integers(0, len(ys)); objs.append((TAB_B, 'saray%d' % rng.integers(0, 4), float(xs[p]), float(ys[p]), ang + (rng.random() - 0.5) * 0.3))

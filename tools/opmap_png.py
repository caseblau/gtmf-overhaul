#!/usr/bin/env python3
"""Stitch the Prokhorovka operation map into one PNG from each cell's own op-map layers.

  opmap_png.py <cellsrc dir> <out.png> [--px 800]

back = the background picture, opmap = the road / contour line mesh, opmap_tri = place names and spot heights.  The labels
are drawn with Pillow's font, so the picture matches the game's map in content, not in lettering.  Squares are 1024 m.
"""
import argparse, os, re
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import atf1
import cellfmt as C


NAMES = {}


def load_names(path):
    """key -> English text from the polygon's text pack"""
    import textpack
    if os.path.exists(path):
        for k, v in textpack.read(path)[1]:
            if v: NAMES[k] = NAMES[k.lower()] = v[0]


def name(i, j):
    return ('Mx' if i in (0, 8) or j in (0, 8) else 'Mg') + chr(68 + i) + str(j + 1)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('cells'); ap.add_argument('out'); ap.add_argument('--px', type=int, default=800)
    a = ap.parse_args(); S = a.px; img = Image.new('RGB', (9 * S, 9 * S), (225, 220, 200)); dr = ImageDraw.Draw(img, 'RGBA')
    try: big, small = ImageFont.truetype('arialbd.ttf', S // 26), ImageFont.truetype('arial.ttf', S // 44)
    except OSError: big = small = ImageFont.load_default()
    labels = []; seen = {}
    load_names(os.path.join(a.cells, 'Prokh_text.loc_eng.textpack'))
    for j in range(9):
        for i in range(9):
            d = os.path.join(a.cells, name(i, j)); ox, oy = i * S, j * S
            try:
                b = np.asarray(atf1.top(os.path.join(d, 'back.cell.loc_def.bin')))[..., :3].astype(np.uint8)
                img.paste(Image.fromarray(b[::-1]).resize((S, S), Image.BILINEAR), (ox, oy))   # row 0 = south, as the other layers
            except Exception as e: print(name(i, j), 'back', e)
            try:
                xy, col, I = C.read_opmap(os.path.join(d, 'opmap.cell.loc_def.bin'))[:3]
                xy = np.asarray(xy, np.float64); sc = 2048.0 if xy.max() <= 2048.5 else 32767.0
                X = ox + xy[:, 0] / sc * S; Y = oy + (1 - xy[:, 1] / sc) * S
                for p, q in zip(I[0::2], I[1::2]):
                    c = int(col[p]); dr.line((X[p], Y[p], X[q], Y[q]), fill=((c >> 16) & 255, (c >> 8) & 255, c & 255, (c >> 24) & 255), width=2 if (c >> 24) == 255 else 1)
            except Exception as e: print(name(i, j), 'lines', e)
            try:
                for s in C.read_sprites(os.path.join(d, 'opmap_tri.cell.loc_def.bin')):
                    labels.append((ox + s['x'] / 2048 * S, oy + (1 - s['y'] / 2048) * S, s['label'], s['kind']))
            except Exception as e: print(name(i, j), 'labels', e)
    for k in range(1, 9):   # the 1024 m operation squares (the cells' own mesh draws the 256 m grid and the 2048 m lines)
        for v in (k * S, k * S - S // 2):
            dr.line((v, 0, v, 9 * S), fill=(40, 40, 40, 90), width=1); dr.line((0, v, 9 * S, v), fill=(40, 40, 40, 90), width=1)
    for x, y, t, kind in labels:
        if t.isdigit() or re.fullmatch(r'[\d.]+', t):
            dr.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(120, 60, 0)); dr.text((x + 5, y - 7), t, fill=(120, 60, 0), font=small)
        else:
            k = NAMES.get(t) or NAMES.get(t.lower()) or re.sub(r'^(pe_mm_|pe_|mm_)', '', t.lower()).replace('_', ' ').title()
            if seen.get(k): continue
            seen[k] = 1
            dr.text((x, y), k, fill=(20, 20, 20), font=big, anchor='mm', stroke_width=3, stroke_fill=(245, 240, 225))
    img.save(a.out, optimize=True); print('saved', a.out, img.size, len(labels), 'labels')


if __name__ == '__main__':
    main()

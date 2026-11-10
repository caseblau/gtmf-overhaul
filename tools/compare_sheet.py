#!/usr/bin/env python3
"""Lay the generated Prokhorovka ground over the RKKA 1:100 000 sheet, so every disagreement can be seen.

  compare_sheet.py <cellsrc dir> <block png> <out dir> [--blocks 3]

Writes one picture per group of cells: the sheet with generated cover tinted on top, with the sheet's ink still legible.
Tints: green wood, blue water / marsh, orange village, red road, magenta rail, yellow crops, nothing for meadow.
Sheet scale: 1 px = 4 m, a cell is 512 px. The block spans px x 0..4608 (columns D..L), py 1024..5632 (rows 1..9).
"""
import os, sys, argparse
import numpy as np
from PIL import Image, ImageDraw
Image.MAX_IMAGE_PIXELS = None

TINT = {12: (0, 150, 40), 1: (0, 90, 255), 4: (255, 0, 255), 11: (230, 30, 30), 6: (240, 200, 0)}
VILLAGE_CLASS = 7


def cell_layers(d):
    """soil and class at 2 m -> reduced to 4 m (sheet pixels); rows run south to north in the files, flipped here"""
    mat = np.fromfile(os.path.join(d, 'mat_map.cell.loc_def.bin'), np.uint8).reshape(2048, 2048)
    soil = (mat & 15)[::-1]
    out = {}
    for s in TINT:
        out[s] = (soil == s).reshape(512, 4, 512, 4).mean((1, 3))
    cp = os.path.join(d, 'class_map.cell.loc_def.bin')
    if os.path.exists(cp):
        n = int(round(os.path.getsize(cp) ** 0.5))
        if n * n == os.path.getsize(cp):
            c = np.fromfile(cp, np.uint8).reshape(n, n)[::-1]
            out['v'] = np.kron(c == VILLAGE_CLASS, np.ones((512 // n, 512 // n)))
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('cells'); ap.add_argument('sheet'); ap.add_argument('out'); ap.add_argument('--blocks', type=int, default=3)
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    sheet = np.asarray(Image.open(a.sheet).convert('RGB'), np.float32)
    done = 0
    for bj in range(0, 9, a.blocks):
        for bi in range(0, 9, a.blocks):
            img = sheet[1024 + bj * 512:1024 + (bj + a.blocks) * 512, bi * 512:(bi + a.blocks) * 512].copy()
            have = 0
            for j in range(bj, bj + a.blocks):
                for i in range(bi, bi + a.blocks):
                    n = ('Mx' if i in (0, 8) or j in (0, 8) else 'Mg') + chr(68 + i) + str(j + 1)
                    d = os.path.join(a.cells, n)
                    if not os.path.exists(os.path.join(d, '!flatlist')): continue
                    have += 1
                    L = cell_layers(d); y = (j - bj) * 512; x = (i - bi) * 512
                    for s, m in L.items():
                        col = np.array((255, 140, 0) if s == 'v' else TINT[s], np.float32)
                        al = (m * (0.8 if s in (11, 4) else 0.22 if s == 6 else 0.38))[..., None]
                        img[y:y + 512, x:x + 512] = img[y:y + 512, x:x + 512] * (1 - al) + col * al
            if not have: continue
            im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)); dr = ImageDraw.Draw(im)
            for k in range(a.blocks):
                for l in range(a.blocks):
                    n = chr(68 + bi + k) + str(bj + l + 1)
                    dr.rectangle([k * 512, l * 512, k * 512 + 511, l * 512 + 511], outline=(0, 0, 0)); dr.text((k * 512 + 4, l * 512 + 4), n, fill=(255, 0, 0))
            im.save(os.path.join(a.out, f'cmp_{bi}_{bj}.png')); done += 1
    print('pictures', done)


if __name__ == '__main__':
    main()

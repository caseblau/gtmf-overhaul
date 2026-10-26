"""Micro-relief for the generated cells: the small bumps and hollows the vanilla ground has everywhere.

Measured 2026-10-25 (band-pass std of the 1 m heightmap, h - uniform_filter(h, k), in metres):
                        k = 3 m   5 m    11 m   21 m   41 m
  Mius MgG3    field    0.044    0.052  0.066  0.084  0.104      village 0.034 0.048 0.079 0.113 0.145
  Petropolye   field    0.110    0.147  0.142  0.155  0.177      village 0.082 0.110 0.171 0.259 0.421
  Korotich     grass    0.067    0.085  0.142  0.222  0.294      village 0.088 0.125 0.206 0.310 0.425
  ours (DEM)   field    0.005    0.005  0.015  0.049  0.166      village 0.013 0.026 0.061 0.103 0.290
The DEM-derived surface is 5-20 x smoother than any vanilla cell below ~20 m.  add() puts value noise of five lattice
spacings on the 0.5 m heightmap, fitted to a target a little above Mius (3 m 0.045, 5 m 0.07, 11 m 0.09, 21 m 0.10,
41 m 0.11 - the long waves of the DEM are already there), x 1.3 for the coarser octaves inside the villages (the vanilla
villages are the roughest ground: yards, pits, dung heaps, ditches), x 0.5 on roads and tracks, x 0.6 under the house
footprints, nothing on the water.  Seam-free: texsynth.gnoise in block coordinates.
"""
import numpy as np
from scipy import ndimage as ndi
import texsynth as TX

OCTAVES = ((2.0, 0.214), (4.0, 0.027), (8.0, 0.057), (16.0, 0.145), (32.0, 0.099))   # (lattice m, amplitude m), fitted
VILLAGE_GAIN = 1.3      # for the 8-32 m octaves inside the village cover / yards
ROAD_GAIN = 0.5
BUILDING_GAIN = 0.6


def add(h, cov, soil, origin, codes, buildings=()):
    """h: (4096, 4096) heights in metres (0.5 m, row 0 = south), modified in place.  cov / soil: (2048, 2048) 1 m.
    codes: dict with WATER, MARSH, ROAD, TRACK, RAIL, VILLAGE, BUILDING cover codes.  buildings: list of footprint polygons (cell m)."""
    ox, oy = origin
    fine = np.zeros((2048, 2048), np.float32); coarse = np.zeros((2048, 2048), np.float32)
    for s, a in OCTAVES:
        n = a * TX.gnoise((2048, 2048), (ox, oy), s, salt=int(900 + s))
        if s <= 4.0: fine += n
        else: coarse += n
    # weights on the 1 m grid
    vil = (cov == codes['VILLAGE']) | np.isin(soil, (3, 10, 11, 15))
    vil = ndi.binary_dilation(vil, iterations=8)
    w_c = np.where(vil, VILLAGE_GAIN, 1.0).astype(np.float32)
    w = np.ones((2048, 2048), np.float32)
    road = np.isin(cov, (codes['ROAD'], codes['TRACK'], codes['RAIL']))
    w[ndi.binary_dilation(road, iterations=2)] = ROAD_GAIN
    if buildings:
        from PIL import Image, ImageDraw
        bi = Image.new('L', (2048, 2048), 0); d = ImageDraw.Draw(bi)
        for pp in buildings:
            if len(pp) >= 3: d.polygon([(float(x), float(y)) for x, y in pp], fill=255)
        w[ndi.binary_dilation(np.asarray(bi) > 0, iterations=3)] = BUILDING_GAIN
    w[cov == codes['BUILDING']] = BUILDING_GAIN
    wet = (cov == codes['WATER']) | (cov == codes['MARSH'])
    w[ndi.binary_dilation(wet, iterations=6)] = 0.0
    w = ndi.uniform_filter(w, 5)
    n1 = (fine + coarse * w_c) * w
    # to the 0.5 m grid (bilinear) plus a 1 m-lattice octave for the finest grain (vanilla 0.5 m-grid std 0.04-0.1)
    n05 = np.repeat(np.repeat(n1, 2, 0), 2, 1)
    n05 = ndi.uniform_filter(n05, 3)
    n05 += 0.05 * TX.gnoise((4096, 4096), (2 * ox, 2 * oy), 2.0, salt=899) * np.repeat(np.repeat(w, 2, 0), 2, 1)
    h += n05.astype(np.float32)
    return float(n1.std())

import sys, os, json, math, time, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from pha6 import encode
mos=np.load('dem/mosaic.npy'); lat_top=52.0; lon_left=36.0; dx=1/2400; dy=1/3600
latS,latN,lonW,lonE=50.904605,51.1254,36.4903,36.8120   # 2 rows added south 2026-10-23
cols,rows=11,12; CELL=2048.0; N=4096; MAXH=320.0
lat_c=51.0334; m_lat=111320.0; m_lon=111320.0*math.cos(math.radians(lat_c))   # lat_c fixed: the x scale of the first 110 cells
template='cells/MgG3/hei_map.cell.loc_def.bin'
out='out/prokh_cells'; os.makedirs(out, exist_ok=True)
letters=[chr(ord('D')+i) for i in range(cols)]
layout={'name':'Prokh','cols':cols,'rows':rows,'latS':latS,'latN':latN,'lonW':lonW,'lonE':lonE,'cell_m':CELL,'cells':[]}
def sample(lat, lon):
    # bilinear sample of the mosaic at arrays of lat/lon
    fx=(lon-lon_left)/dx; fy=(lat_top-lat)/dy
    x0=np.floor(fx).astype(np.int64); y0=np.floor(fy).astype(np.int64); tx=(fx-x0).astype(np.float32); ty=(fy-y0).astype(np.float32)
    x1=np.minimum(x0+1,mos.shape[1]-1); y1=np.minimum(y0+1,mos.shape[0]-1)
    return (mos[y0,x0]*(1-tx)*(1-ty)+mos[y0,x1]*tx*(1-ty)+mos[y1,x0]*(1-tx)*ty+mos[y1,x1]*tx*ty)
t0=time.time(); budget=float(os.environ.get('BUDGET','540'))
rows_only=[int(v) for v in os.environ.get('ROWS_ONLY','').split(',') if v]
for j in range(rows):
    if rows_only and j not in rows_only: continue
    for i in range(cols):
        border = (i==0 or j==0 or i==cols-1 or j==rows-1)
        cell=('Mx' if border else 'Mg')+letters[i]+str(j+1)
        fn=f'{out}/{cell}_hei_map.cell.loc_def.bin'
        if os.path.exists(fn) and os.path.getsize(fn)>0: continue
        if time.time()-t0>budget: print('budget reached', flush=True); sys.exit(0)
        # sample grid: x east from the block's W edge, y NORTH from the cell's S edge (rows run south->north); sample centres at (k+0.5)*0.5 m
        xs=(i*CELL+(np.arange(N)+0.5)*(CELL/N)); ys=((rows-1-j)*CELL+(np.arange(N)+0.5)*(CELL/N))
        lon=lonW+xs/m_lon; lat=latS+ys/m_lat   # engine: sample row 0 = SOUTH edge of the cell (in-game seam test 2026-10-22; see docs/m12_terrain/findings.md)
        LAT,LON=np.meshgrid(lat.astype(np.float64),lon.astype(np.float64),indexing='ij')
        h=sample(LAT,LON).astype(np.float32)
        units=np.clip(h*65535.0/MAXH,0,65535).astype(np.float32)
        open(fn,'wb').write(encode(units, template, candidates=[0,63,52,24,36,40,3,13]))
        layout['cells'].append({'cell':cell,'col':i,'row':j,'hmin':float(h.min()),'hmax':float(h.max())})
        print(f'{cell} {h.min():.1f}..{h.max():.1f} m  {time.time()-t0:.0f}s', flush=True)
print('all cells done')

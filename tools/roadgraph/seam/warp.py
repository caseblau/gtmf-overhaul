"""Realign the 1941 sheet mosaic: each piece between the scan seams (block rows 607, 2431) gets a quadratic
pixel->grid fit from its own 2 km grid lines; every piece is mapped into the grid frame of the reference piece."""
import numpy as np, json, sys
from scipy import ndimage as ndi
f=json.load(open('fit.json'))
SEAMS=[607,2431]; REF=int(sys.argv[1]) if len(sys.argv)>1 else 1
def F(P,x,y):
  A=np.stack([np.ones_like(x),x,y,x*x/1e4,x*y/1e4,y*y/1e4],-1)
  return A@np.array(f[str(P)]['u']), A@np.array(f[str(P)]['v'])
def J(P,x,y):
  cu=np.array(f[str(P)]['u']); cv=np.array(f[str(P)]['v'])
  dux=cu[1]+2*cu[3]*x/1e4+cu[4]*y/1e4; duy=cu[2]+cu[4]*x/1e4+2*cu[5]*y/1e4
  dvx=cv[1]+2*cv[3]*x/1e4+cv[4]*y/1e4; dvy=cv[2]+cv[4]*x/1e4+2*cv[5]*y/1e4
  return dux,duy,dvx,dvy
def inv(P,u,v,x0,y0):
  x,y=x0.copy(),y0.copy()
  for _ in range(6):
    uu,vv=F(P,x,y); a,b,c,d=J(P,x,y); det=a*d-b*c
    du,dv=u-uu,v-vv; x+= ( d*du-b*dv)/det; y+=(-c*du+a*dv)/det
  return x,y
def src_map(shape):
  """for every output pixel: source (x,y) in the old block raster, and the piece id (-1 = gap)"""
  H,W=shape; oy,ox=np.mgrid[0:H,0:W].astype(np.float64)
  u,v=F(REF,ox,oy)
  bounds=[-1e9]+SEAMS+[1e9]
  sx=np.full(shape,np.nan); sy=np.full(shape,np.nan); pid=np.full(shape,-1,np.int8)
  for P in (2,1,0):          # later pieces first; an earlier piece wins in an overlap
    x,y=inv(P,u,v,ox,oy)
    m=(y>=bounds[P])&(y<bounds[P+1])
    sx[m]=x[m]; sy[m]=y[m]; pid[m]=P
  return sx,sy,pid
def fwd(P,x,y):
  """old block px of piece P -> new block px"""
  u,v=F(P,x,y); return inv(REF,u,v,np.asarray(x,float),np.asarray(y,float))
if __name__=='__main__':
  sx,sy,pid=src_map((4608,4608))
  np.savez_compressed('map_ref%d.npz'%REF,sx=sx.astype(np.float32),sy=sy.astype(np.float32),pid=pid)
  for P in range(3):
    m=pid==P; print('piece',P,'px',m.sum(),'max shift %.1f'%np.nanmax(np.hypot(sx[m]-np.mgrid[0:4608,0:4608][1][m],sy[m]-np.mgrid[0:4608,0:4608][0][m])))
  print('gap px',(pid<0).sum())

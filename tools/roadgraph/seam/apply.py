import numpy as np, sys
from PIL import Image
from scipy import ndimage as ndi
import warp
Image.MAX_IMAGE_PIXELS=None
src=np.asarray(Image.open('/mnt/user-data/uploads/gtmf-overhaul/docs/m12_terrain/period/rkka100k_block.png').convert('RGB'))
H,W=src.shape[:2]                       # 6144 x 5632, block rows = sheet rows - 1024
out=np.empty_like(src); PID=np.full((H,W),-1,np.int8)
for r0 in range(0,H,512):
  oy,ox=np.mgrid[r0:min(H,r0+512),0:W].astype(np.float64); by=oy-1024
  u,v=warp.F(warp.REF,ox,by)
  sx=np.full(ox.shape,np.nan); sy=np.full(ox.shape,np.nan); pid=np.full(ox.shape,-1,np.int8)
  b=[-1e9]+warp.SEAMS+[1e9]
  for P in (2,1,0):
    x,y=warp.inv(P,u,v,ox,by); m=(y>=b[P])&(y<b[P+1]); sx[m]=x[m]; sy[m]=y[m]; pid[m]=P
  ok=pid>=0
  for c in range(3):
    ch=ndi.map_coordinates(src[...,c].astype(np.float32),[np.where(ok,sy+1024,0),np.where(ok,sx,0)],order=1,mode='nearest')
    out[r0:r0+512,:,c]=np.where(ok,np.clip(ch+0.5,0,255),(222,217,196)[c]).astype(np.uint8)
  PID[r0:r0+512]=pid
# keep the blank-patch sentinel exact (rgb == 230 where the source was blank): nearest sampling there
Image.fromarray(out).save('rkka100k_block_aligned.png',optimize=True)
np.save('pid_sheet.npy',PID)
print('gap px in block', (PID[1024:5632,:4608]<0).sum())

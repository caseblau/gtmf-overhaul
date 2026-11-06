import numpy as np, math, json
d=np.load('gridpx.npz'); vm,hm=d['vm'],d['hm']
SEAMS=[607,2431]
def piece(py): return np.searchsorted(SEAMS,py)
t=math.tan(math.radians(2.1))
vy,vx=np.nonzero(vm); hy,hx=np.nonzero(hm)
u0=(vx-438-(vy-576)*t)/502.0
v0=(hy-571+(hx-144)*t)/501.0
res={}
for P in range(3):
  sv=(piece(vy)==P)&(np.abs(vy-np.array([0]+SEAMS+[9999])[np.minimum(piece(vy),2)])>0)
  # stay 12 px away from seams
  far=lambda y: np.min(np.abs(np.array(SEAMS)[None,:]-y[:,None]),1)>12
  mv=(piece(vy)==P)&far(vy); mh=(piece(hy)==P)&far(hy)
  out={}
  for name,X,Y,g0,m in (('u',vx,vy,u0,mv),('v',hx,hy,v0,mh)):
    X_,Y_=X[m].astype(float),Y[m].astype(float); g=g0[m]
    for it in range(4):
      k=np.round(g); A=np.c_[np.ones_like(X_),X_,Y_,X_*X_/1e4,X_*Y_/1e4,Y_*Y_/1e4]
      c,*_=np.linalg.lstsq(A,k,rcond=None); r=A@c-k
      ok=np.abs(r)<0.03
      c,*_=np.linalg.lstsq(A[ok],k[ok],rcond=None); g=A@c
    r=(A@c-np.round(A@c))
    out[name]=c.tolist(); print(P,name,'n',m.sum(),'inl',ok.mean().round(3),'rms px %.2f'%(np.sqrt(np.mean((r[np.abs(r)<0.03]*500)**2))), 'k range',np.round(g).min(),np.round(g).max())
  res[P]=out
json.dump(res,open('fit.json','w'))

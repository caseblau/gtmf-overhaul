"""z-buffered flat-shaded preview of an OBJ, 3 views side by side: python preview.py in.obj out.png"""
import sys, numpy as np
from PIL import Image
def load(p):
    V=[];F=[]
    for l in open(p):
        if l.startswith('v '): V.append([float(x) for x in l.split()[1:4]])
        elif l.startswith('f '): F.append([int(t.split('/')[0])-1 for t in l.split()[1:4]])
    return np.array(V),np.array(F)
def rot(yaw,pitch):
    a,b=np.radians(yaw),np.radians(pitch)
    Ry=np.array([[np.cos(a),0,np.sin(a)],[0,1,0],[-np.sin(a),0,np.cos(a)]]); Rx=np.array([[1,0,0],[0,np.cos(b),-np.sin(b)],[0,np.sin(b),np.cos(b)]])
    return Rx@Ry
def render(V,F,R,size=600,s=None,c=None):
    P=V@R.T
    if c is None: c=(P.max(0)+P.min(0))/2
    P=P-c
    if s is None: s=0.9*size/max(np.ptp(P[:,0]),np.ptp(P[:,1]))
    X=size/2+P[:,0]*s; Y=size/2-P[:,1]*s; Z=P[:,2]
    tri=P[F]; n=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]); n/=np.linalg.norm(n,axis=1,keepdims=True)+1e-12
    L=np.array([0.35,0.75,0.55]); L/=np.linalg.norm(L); sh=np.abs(n@L)*0.7+0.3
    zb=np.full((size,size),-1e9); img=np.full((size,size,3),[235,235,228],float)
    for k,(a,b_,c_) in enumerate(F):
        xs=np.array([X[a],X[b_],X[c_]]); ys=np.array([Y[a],Y[b_],Y[c_]]); zs=np.array([Z[a],Z[b_],Z[c_]])
        x0,x1=int(max(0,np.floor(xs.min()))),int(min(size-1,np.ceil(xs.max()))); y0,y1=int(max(0,np.floor(ys.min()))),int(min(size-1,np.ceil(ys.max())))
        if x1<x0 or y1<y0: continue
        gx,gy=np.meshgrid(np.arange(x0,x1+1)+0.5,np.arange(y0,y1+1)+0.5)
        d=(ys[1]-ys[2])*(xs[0]-xs[2])+(xs[2]-xs[1])*(ys[0]-ys[2])
        if abs(d)<1e-12: continue
        w0=((ys[1]-ys[2])*(gx-xs[2])+(xs[2]-xs[1])*(gy-ys[2]))/d; w1=((ys[2]-ys[0])*(gx-xs[2])+(xs[0]-xs[2])*(gy-ys[2]))/d; w2=1-w0-w1
        m=(w0>=-1e-6)&(w1>=-1e-6)&(w2>=-1e-6)
        if not m.any(): continue
        z=w0*zs[0]+w1*zs[1]+w2*zs[2]
        sub=zb[y0:y1+1,x0:x1+1]; upd=m&(z>sub)
        sub[upd]=z[upd]; g=200*sh[k]; img[y0:y1+1,x0:x1+1][upd]=[g,g-8,g-25]
    return Image.fromarray(np.clip(img,0,255).astype(np.uint8))
if __name__=='__main__':
    V,F=load(sys.argv[1])
    views=[(90,0),(35,25),(0,0),(-140,20)]
    ims=[render(V,F,rot(*a),size=500) for a in views]
    out=Image.new('RGB',(1000,1000)); [out.paste(im,((i%2)*500,(i//2)*500)) for i,im in enumerate(ims)]; out.save(sys.argv[2])

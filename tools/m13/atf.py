"""ATF1 texture container (Graviteam): 'ATF1' fourcc(DXT1/DXT5) u32 total u32 1, zeros to 0x80; u32 mip count at 0x80;
mip table at 0x88: per mip (u16 w, u16 h, u32 offset), smallest first; data at 0x2000 (offsets relative to it)."""
import struct, numpy as np
def read(d):
    fc=d[4:8].decode(); n=struct.unpack_from('<I',d,0x80)[0]; mips=[]
    for i in range(n):
        w,h,o=struct.unpack_from('<HHI',d,0x88+8*i); mips.append((w,h,o))
    return fc,mips
def _c565(c):
    r=((c>>11)&31)*255//31; g=((c>>5)&63)*255//63; b=(c&31)*255//31; return np.stack([r,g,b],-1).astype(np.float32)
def decode(d,level=-1):
    fc,mips=read(d); w,h,o=mips[level]; bs=8 if fc=='DXT1' else 16
    bw,bh=max(1,(w+3)//4),max(1,(h+3)//4); raw=np.frombuffer(d,np.uint8,bw*bh*bs,0x2000+o).reshape(bh*bw,bs)
    out=np.zeros((bh*4,bw*4,4),np.float32)
    col=raw[:,-8:]
    c0=col[:,0].astype(np.uint16)|col[:,1].astype(np.uint16)<<8; c1=col[:,2].astype(np.uint16)|col[:,3].astype(np.uint16)<<8
    p0=_c565(c0); p1=_c565(c1); four=(c0>c1)|(fc!='DXT1')
    pal=np.stack([p0,p1,np.where(four[:,None],(2*p0+p1)/3,(p0+p1)/2),np.where(four[:,None],(p0+2*p1)/3,0)],1)
    idx=np.unpackbits(col[:,4:8],axis=1,bitorder='little').reshape(-1,16,2); idx=idx[:,:,0]+2*idx[:,:,1]
    rgb=np.take_along_axis(pal,idx[:,:,None].repeat(3,2),1)
    a=np.full((len(raw),16),255.0)
    if fc=='DXT5':
        a0=raw[:,0].astype(np.float32); a1=raw[:,1].astype(np.float32)
        ap=[a0,a1]+[np.where(a0>a1,((6-k)*a0+(k+1)*a1)/7,np.where(k<4,((4-k)*a0+(k+1)*a1)/5,0 if k==4 else 255)) for k in range(6)]
        ap=np.stack(ap,1); bits=np.unpackbits(raw[:,2:8],axis=1,bitorder='little').reshape(-1,16,3)
        ai=bits[:,:,0]+2*bits[:,:,1]+4*bits[:,:,2]; a=np.take_along_axis(ap,ai,1)
    blk=np.concatenate([rgb,a[:,:,None]],2).reshape(bh,bw,4,4,4).transpose(0,2,1,3,4).reshape(bh*4,bw*4,4)
    return blk[:h,:w]

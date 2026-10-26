import tifffile, numpy as np, zlib
def read_cog_float32(path):
    t=tifffile.TiffFile(path); p=t.pages[0]
    H,W=p.shape; th,tw=p.tilelength,p.tilewidth
    assert p.compression==8 or p.compression.name.upper().endswith('DEFLATE'), p.compression
    out=np.zeros((H,W),np.float32)
    ntx=(W+tw-1)//tw
    for i,(off,cnt) in enumerate(zip(p.dataoffsets,p.databytecounts)):
        t.filehandle.seek(off); raw=zlib.decompress(t.filehandle.read(cnt))
        b=np.frombuffer(raw,np.uint8).reshape(th,tw*4)
        b=np.cumsum(b,axis=1,dtype=np.uint8)             # undo horizontal differencing (byte-wise, wraps)
        # predictor 3: row stored as 4 byte-planes, big-endian order (msb plane first)
        planes=b.reshape(th,4,tw)
        le=np.stack([planes[:,3,:],planes[:,2,:],planes[:,1,:],planes[:,0,:]],axis=2)  # little-endian bytes
        tile=le.reshape(th,tw*4).view('<f4')
        ty,tx=divmod(i,ntx); y0,x0=ty*th,tx*tw
        hh,ww=min(th,H-y0),min(tw,W-x0)
        out[y0:y0+hh,x0:x0+ww]=tile[:hh,:ww]
    scale=p.tags['ModelPixelScaleTag'].value; tie=p.tags['ModelTiepointTag'].value
    return out,(tie[3],tie[4],scale[0],scale[1])

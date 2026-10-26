import struct, sys, numpy as np
def decode(path):
    b=open(path,'rb').read()
    magic, v, fcc, _, w, h, bits, _, hsz = struct.unpack_from('<4sI4sIIIIII', b, 0)
    assert magic==b'AZHP' and fcc==b'PHA6', (magic, fcc)
    fixed = np.array(struct.unpack_from('<4f', b, 0x30), np.float32)
    pal = np.array(struct.unpack_from('<252f', b, 0x40), np.float32).reshape(63,4)
    pal = np.vstack([pal, fixed[None,:]])            # index 63 = the fixed quartet? (to verify)
    data = np.frombuffer(b, dtype='<u8', offset=0x40+1008)
    bw, bh = w//4, h//4
    assert data.size == bw*bh, (data.size, bw*bh)
    A = (data & 0xFFFF).astype(np.float32)
    B = ((data >> 16) & 0xFFFF).astype(np.int64)
    C = (data >> 32).astype(np.uint64)
    palidx = (B >> 10).astype(np.int64); rng = (B & 0x3FF).astype(np.float32)
    # 16 x 2-bit indices: row y (0..3) in byte y, sample x in bits 2x..2x+1
    out = np.empty((h, w), np.float32)
    A2 = A.reshape(bh, bw); R2 = rng.reshape(bh, bw); P2 = palidx.reshape(bh, bw)
    levels = pal[P2]            # (bh,bw,4)
    for y in range(4):
        for x in range(4):
            idx = ((C >> np.uint64(8*y + 2*x)) & np.uint64(3)).astype(np.int64).reshape(bh, bw)
            lv = np.take_along_axis(levels, idx[...,None], axis=2)[...,0]
            out[y::4, x::4] = A2 + R2 * lv
    return out, dict(w=w,h=h,bits=bits,hsz=hsz,fixed=fixed,palidx_max=int(palidx.max()),rng_max=float(rng.max()))
if __name__=='__main__':
    arr, info = decode(sys.argv[1])
    print(info)
    print('min/max', arr.min(), arr.max(), 'metres if 65535=320m:', arr.min()*320/65535, arr.max()*320/65535)
    # seam check: mean abs diff within blocks vs across block boundaries
    dx = np.abs(np.diff(arr, axis=1)); 
    inner = dx[:, [i for i in range(dx.shape[1]) if i%4!=3]].mean(); border = dx[:, 3::4].mean()
    print('mean |dh| horizontal inside blocks %.2f, across block borders %.2f'%(inner, border))
    dy = np.abs(np.diff(arr, axis=0)); inner = dy[[i for i in range(dy.shape[0]) if i%4!=3], :].mean(); border = dy[3::4, :].mean()
    print('mean |dh| vertical inside blocks %.2f, across block borders %.2f'%(inner, border))
    from PIL import Image
    small = arr.reshape(1024,4,1024,4).mean(axis=(1,3))
    img = ((small-small.min())/(small.max()-small.min())*255).astype(np.uint8)
    Image.fromarray(img).save(sys.argv[2]); print('wrote', sys.argv[2])
    np.save(sys.argv[2]+'.npy', small)

def encode(arr, template_path, candidates=None):
    """arr: (h,w) float32 heights in the file's u16 units. Returns bytes with the template's header and palettes."""
    b=open(template_path,'rb').read()
    hdr = b[:0x40+1008]
    fixed = np.array(struct.unpack_from('<4f', b, 0x30), np.float32)
    pal = np.vstack([np.array(struct.unpack_from('<252f', b, 0x40), np.float32).reshape(63,4), fixed[None,:]])  # (64,4)
    h, w = arr.shape; bh, bw = h//4, w//4
    blk = arr.reshape(bh,4,bw,4).transpose(0,2,1,3).reshape(bh*bw,16)     # (N,16) row-major y then x
    base = np.floor(blk.min(axis=1)); base = np.clip(base, 0, 65535)
    rng = np.ceil(blk.max(axis=1) - base); rng = np.clip(rng, 0, 1023)
    rel = (blk - base[:,None]) / np.where(rng>0, rng, 1)[:,None]            # (N,16) in [0,1]
    # best palette: for each palette, nearest level per sample, sum squared error
    best_err = None; best_p = None; best_idx = None
    for p in (range(64) if candidates is None else candidates):
        lv = pal[p]                                                     # (4,)
        d = np.abs(rel[:,:,None] - lv[None,None,:])                      # (N,16,4)
        idx = d.argmin(axis=2)                                           # (N,16)
        err = ((rel - lv[idx])**2).sum(axis=1)                            # (N,)
        if best_err is None: best_err, best_p, best_idx = err, np.full(len(err), p), idx
        else:
            m = err < best_err
            best_err = np.where(m, err, best_err); best_p = np.where(m, p, best_p); best_idx = np.where(m[:,None], idx, best_idx)
    B = (best_p.astype(np.uint64) << np.uint64(10)) | rng.astype(np.uint64)
    C = np.zeros(bh*bw, np.uint64)
    for k in range(16):
        y, x = divmod(k, 4)
        C |= best_idx[:,k].astype(np.uint64) << np.uint64(8*y + 2*x)
    data = base.astype(np.uint64) | (B << np.uint64(16)) | (C << np.uint64(32))
    return hdr + data.astype('<u8').tobytes()

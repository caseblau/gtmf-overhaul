"""AZG2 mesh reader (Graviteam Tactics: Mius-Front / Operation Star) - work in progress, M13.

  m = read(path)  -> dict(nodes=[...], blocks=[...], materials=[...], matrices=np.array (n,4,4))
  export_obj(m, lod, out)  -> OBJ of one geometry block (0 = PNTl simplified mesh, 1..3 = GXT2 LODs)
See docs/m13_vehicles/azg2_format.md.
"""
import struct, numpy as np, collections

def _s(b, o, n=0x20): return b[o:o + n].split(b'\0')[0].decode('cp1251', 'replace')

def read(path):
    d = open(path, 'rb').read(); assert d[:4] == b'AZG2'
    p = struct.unpack_from('<16I', d, 8)
    pairs = [(p[2 * i], p[2 * i + 1]) for i in range(8)]
    (no, nn), (mo, nm), (xo, nx) = pairs[0], pairs[1], pairs[2]
    go, ng = pairs[4]
    nodes = []
    for i in range(nn):
        o = no + i * 0x140; f = struct.unpack_from('<8I', d, o + 0x20)
        slots = []
        for s in range(4):
            so = o + 0x40 + s * 0x40
            nv, ni = struct.unpack_from('<2I', d, so); bb = struct.unpack_from('<8f', d, so + 0x20)
            slots.append(dict(nv=nv, ni=ni, bbox=bb))
        nodes.append(dict(index=i, name=_s(d, o), sibling=f[0], kind=f[1], parent=f[2], child=f[3], nchild=f[4], slots=slots))
    mats = [dict(name=_s(d, mo + i * 0x68), tex=[_s(d, mo + i * 0x68 + 0x60 - 0x40 + 0x60 + k * 0x20) for k in range(0)]) for i in range(nm)]
    M = np.frombuffer(d, np.float32, nx * 16, xo).reshape(nx, 4, 4) if nx else np.zeros((0, 4, 4), np.float32)
    blocks = []
    for k in range(ng):
        o = go + k * 0xC0
        tag = d[o:o + 4].decode('latin1'); ver, lod, io, vo, ni, nv, li = struct.unpack_from('<6Ii', d, o + 4)
        decl = []; e = o + 64
        while True:
            st, off, ty, me, us, ui = struct.unpack_from('<HHBBBB', d, e)
            if st == 0xff: break
            decl.append((off, ty, us, ui)); e += 8
        stride = 48 if tag == 'PNTl' else 32
        isz = 4 if tag == 'PNTl' else 2
        idx = np.frombuffer(d, np.uint32 if isz == 4 else np.uint16, ni, io).astype(np.int64)
        raw = np.frombuffer(d, np.uint8, nv * stride, vo).reshape(nv, stride)
        pos = raw[:, :12].copy().view(np.float32)
        b = dict(tag=tag, ni=ni, nv=nv, idx=idx, pos=pos, raw=raw, decl=decl)
        if tag == 'GXT2':
            b['uv'] = raw[:, 12:16].copy().view(np.int16).reshape(-1, 2) / 32767.0
            b['bone'] = raw[:, 16].astype(int)
            b['nrm'] = raw[:, 20:23].astype(np.float32) / 127.5 - 1
        blocks.append(b)
    m = dict(nodes=nodes, matrices=M, blocks=blocks, materials=mats, data=d)
    for n in nodes:   # header field 0 = matrix index (bit 31 a flag), -1 for s_root / d_hull (identity)
        n['matrix'] = -1 if n['sibling'] == 0xffffffff else n['sibling'] & 0x7fffffff
    _world(m)
    return m

def _world(m, compose=True):
    """world matrix per node: local (row vectors, translation in row 3) times the parent's world"""
    N = m['nodes']; W = {}
    def get(i):
        if i in W: return W[i]
        n = N[i]; L = m['matrices'][n['matrix']].astype(np.float64) if 0 <= n['matrix'] < len(m['matrices']) else np.eye(4)
        P = get(n['parent']) if (compose and n['parent'] != 0xffffffff and n['parent'] < len(N)) else np.eye(4)
        W[i] = L @ P; return W[i]
    for n in N: n['world'] = get(n['index'])

def lod_nodes(m, lod):
    """bone k of a GXT2 block = the k-th node (table order) that has geometry in that block"""
    return [n for n in m['nodes'] if n['slots'][lod]['nv'] > 0]

def _map_bones(m):
    """bone index (GXT2 BLENDINDICES) -> node, matched by the per-LOD vertex counts of each node"""
    geo = [n for n in m['nodes'] if any(s['nv'] for s in n['slots'][1:])]
    lods = [b for b in m['blocks'] if b['tag'] == 'GXT2']
    nb = len(m['matrices'])
    sig = {}
    for k in range(nb):
        sig[k] = tuple(int((b['bone'] == k).sum()) for b in lods)
    want = {n['index']: tuple(s['nv'] for s in n['slots'][1:1 + len(lods)]) for n in geo}
    used = set(); bone2node = {}
    order = [n['index'] for n in geo]
    # first the ordinal guess, then fix by count signature
    for k in range(nb):
        cand = [i for i in order if i not in used and want[i] == sig[k]]
        if cand: bone2node[k] = cand[0]; used.add(cand[0])
    m['bone2node'] = bone2node

def export_obj(m, lod, out):
    b = m['blocks'][lod]
    pos = b['pos'].astype(np.float64)
    if 'bone' in b:
        Wb = np.array([n['world'] for n in lod_nodes(m, lod)])
        p4 = np.c_[pos, np.ones(len(pos))]
        pos = np.einsum('ni,nij->nj', p4, Wb[np.clip(b['bone'], 0, len(Wb) - 1)])[:, :3]
    with open(out, 'w') as f:
        for x, y, z in pos: f.write('v %.5f %.5f %.5f\n' % (x, y, -z))
        if 'uv' in b:
            for u, v in b['uv']: f.write('vt %.5f %.5f\n' % (u, 1 - v))
        t = b['idx'][:len(b['idx']) // 3 * 3].reshape(-1, 3) + 1
        uvs = 'uv' in b
        for a, c, e in t:
            f.write(('f %d/%d %d/%d %d/%d\n' % (a, a, e, e, c, c)) if uvs else ('f %d %d %d\n' % (a, e, c)))
    return pos

if __name__ == '__main__':
    import sys
    m = read(sys.argv[1]); lod = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    export_obj(m, lod, sys.argv[2])
    print(len(m['nodes']), 'nodes', [(b['tag'], b['nv'], b['ni']) for b in m['blocks']], len(m['matrices']), 'matrices')

# ---------------------------------------------------------------- structured parse + writer (round trip)
def _hash(name, N):
    h = 0; a = 0x7e9f; M = 2 ** 32
    for ch in name.encode('cp1251'):
        c = ch - 256 if ch >= 128 else ch
        t = ((a * h) % M) + c
        if t < 0: t += M
        h = (t % M) % N; a = ((a * 0x6a2f) % M) % (N - 1)
    return h

def _buckets(n):
    p = 1
    while p < 3 * n: p *= 2
    return p

def parse(path_or_bytes):
    """everything needed to rebuild the file: raw node records, materials, matrices, ITABS lists, geometry blocks"""
    d = path_or_bytes if isinstance(path_or_bytes, bytes) else open(path_or_bytes, 'rb').read()
    p = struct.unpack_from('<16I', d, 8); P = [(p[2 * i], p[2 * i + 1]) for i in range(8)]
    (no, nn), (mo, nm), (xo, nx), _, (go, ng), (lo, nl), _, (ho, nh) = P
    nodes = [bytearray(d[no + i * 0x140: no + (i + 1) * 0x140]) for i in range(nn)]
    mats = [bytes(d[mo + i * 0x60: mo + (i + 1) * 0x60]) for i in range(nm)]
    mtx = bytes(d[xo: xo + nx * 64]) if nx else b''
    itabs = []
    for i in range(nl):
        off, cnt, a, b_ = struct.unpack_from('<4I', d, lo + 32 * i)
        itabs.append(dict(items=list(struct.unpack_from('<%dI' % cnt, d, off)), a=a, b=b_, rest=bytes(d[lo + 32 * i + 16: lo + 32 * i + 32])))
    blocks = []
    for k in range(ng):
        o = go + k * 0xC0
        tag = bytes(d[o:o + 4]); ver, lod, io, vo, ni, nv, li = struct.unpack_from('<6Ii', d, o + 4)
        isz = 4 if tag == b'PNTl' else 2
        stride = 48 if tag == b'PNTl' else 32
        blocks.append(dict(tag=tag, ver=ver, lod=lod, li=li, head=bytes(d[o + 32:o + 0xC0]), isz=isz,
                           idx=bytes(d[io: io + ni * isz]), ni=ni, vtx=bytes(d[vo: vo + nv * stride]), nv=nv))
    first_io = struct.unpack_from('<I', d, go + 12)[0] if ng else 0
    packed = ng > 0 and first_io == go + 0xC0 * ng      # newer Mius-Front files: no 64 KB alignment, no tail padding
    return dict(nodes=nodes, mats=mats, mtx=mtx, nx=nx, itabs=itabs, blocks=blocks, hash_n=nh, packed=packed)

def write(s):
    a16 = lambda x: (x + 15) & ~15
    a64k = (lambda x: (x + 15) & ~15) if s.get('packed') else (lambda x: (x + 0xFFFF) & ~0xFFFF)
    out = bytearray(0x80); out += b'[CHUNKS]'.ljust(16, b'\0')
    no = len(out); nn = len(s['nodes'])
    for n in s['nodes']: out += n
    out += bytes(a16(len(out)) - len(out)); out += b'[MATERIALS]'.ljust(16, b'\0')
    mo = len(out); [out.__iadd__(m) for m in s['mats']]
    xo = 0
    if s['nx']:
        out += bytes(a16(len(out)) - len(out)); out += b'[MATRICES]'.ljust(16, b'\0'); xo = len(out); out += s['mtx']
    out += bytes(a16(len(out)) - len(out)); out += b'[CHUNKS_HASH]'.ljust(16, b'\0')
    names = [bytes(n[:0x20]).split(b'\0')[0].decode('cp1251') for n in s['nodes']]
    nh = s.get('hash_n') or _buckets(nn); slots = [0] * (2 * nh)
    for i, nm_ in enumerate(names):
        h = _hash(nm_, nh); k = h
        for _ in range(nh):
            if not slots[2 * k] & 0x80000000: break
            k = (k + 1) % nh
        slots[2 * k] = 0x80000000 | h; slots[2 * k + 1] = i
    ho = len(out); out += struct.pack('<%dI' % (2 * nh), *slots)
    out += bytes(a16(len(out)) - len(out)); out += b'[ITABS]'.ljust(16, b'\0')
    lo = len(out); nl = len(s['itabs']); out += bytes(32 * nl + 32)
    for i, t in enumerate(s['itabs']):
        off = len(out); out += struct.pack('<%dI' % len(t['items']), *t['items'])
        struct.pack_into('<4I', out, lo + 32 * i, off, len(t['items']), t['a'], t['b']); out[lo + 32 * i + 16: lo + 32 * i + 32] = t['rest']
    out += bytes(a16(len(out)) - len(out)); out += b'[GEOMETRY]'.ljust(16, b'\0')
    go = len(out); ng = len(s['blocks']); out += bytes(0xC0 * ng)
    for k, b in enumerate(s['blocks']):
        out += bytes(a64k(len(out)) - len(out)); io = len(out); out += b['idx']
        out += bytes(a16(len(out)) - len(out)); vo = len(out); out += b['vtx']
        o = go + k * 0xC0
        out[o:o + 4] = b['tag']; struct.pack_into('<6Ii', out, o + 4, b['ver'], b['lod'], io, vo, b['ni'], b['nv'], b['li'])
        out[o + 32:o + 0xC0] = b['head']
    if not s.get('packed'): out += bytes(a64k(len(out)) - len(out))
    hdr = [len(out), no, nn, mo, len(s['mats']), xo, s['nx'], 0, 0, go, ng, lo, nl, 0, 0, ho, nh]
    out[0:4] = b'AZG2'; struct.pack_into('<17I', out, 4, *hdr)
    return bytes(out)

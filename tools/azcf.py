"""Reader for the AZCF config containers (operation desc, div_pool ...) - Python port of the gt3.ps1 reader.

  nodes = read(path)              -> list of dict(index, name, type, cols, rows, types, rows_data)
  table(path, 'markers_01')       -> (type string, [[cell, ...], ...]) with cells decoded as gt3.ps1 csv does
"""
import struct

def _cstr(b, off):
    e = b.index(b'\0', off); return b[off:e].decode('cp1251', 'replace')

def _fourcc(v):
    if v < 0x10000:
        lo, hi = v & 0xff, (v >> 8) & 0xff
        return chr(lo) + chr(hi) if 0x41 <= lo <= 0x5a and 0x41 <= hi <= 0x5a else None
    s = ''
    for i in range(4):
        c = (v >> (8 * i)) & 0xff
        if c == 0:
            if i < 3: return None
            break
        if c < 0x21 or c > 0x7e: return None
        s += chr(c)
    return s

def _fmt(x):
    s = '%.6g' % x
    return s

def decode(b, off):
    kind = struct.unpack_from('<I', b, off + 16)[0]
    s = struct.unpack_from('<4I', b, off)
    if kind == 2: return _cstr(b, s[1]) if s[1] else ''
    if kind == 4:
        fc = _fourcc(s[0])
        if fc: return fc
        if 0x19 <= (s[0] >> 24) <= 0x20 and ((s[0] >> 16) & 0xff) <= 0x99: return '0x%08x' % s[0]
        return str(s[0])
    if kind == 6:
        n = 3
        while n > 0 and s[n] == 0: n -= 1
        return ';'.join(str(v) for v in struct.unpack_from('<4i', b, off)[:n + 1])
    if kind == 1:
        n = 3
        while n > 0 and s[n] == 0: n -= 1
        return ';'.join(_fmt(v) for v in struct.unpack_from('<4f', b, off)[:n + 1])
    if kind == 0: return _fmt(struct.unpack_from('<f', b, off)[0])
    if kind == 5: return '1' if s[0] else '0'
    return 'kind%d:%08x;%08x;%08x;%08x' % (kind, *s)

def read(path):
    b = open(path, 'rb').read()
    assert b[:4] == b'AZCF'
    count, tab = struct.unpack_from('<II', b, 4)
    nodes = []
    for i in range(count):
        o = tab + i * 0x80
        f = struct.unpack_from('<10I', b, o + 0x20)
        name = b[o:o + 0x20].split(b'\0')[0].decode('cp1251', 'replace')
        nodes.append(dict(index=i, name=name, type=f[0], cols=f[1], rows=f[2], types=_cstr(b, f[3]) if f[3] else '', data=f[4]))
    return b, nodes

def table(path, name, index=None):
    b, nodes = read(path)
    n = next(nd for nd in nodes if (nd['index'] == index if index is not None else nd['name'] == name))
    out = []
    if n['type'] == 1:
        for r in range(n['rows']):
            o = n['data'] + r * 0x40
            out.append([b[o + 0x20:o + 0x40].split(b'\0')[0].decode('cp1251', 'replace'), decode(b, o)])
    else:
        for r in range(n['rows']):
            o = n['data'] + r * 0x20 * n['cols']
            out.append([decode(b, o + c * 0x20) for c in range(n['cols'])])
    return n['types'], out

if __name__ == '__main__':
    import sys
    b, nodes = read(sys.argv[1])
    if len(sys.argv) == 2:
        for nd in nodes:
            if nd['type'] in (1, 2) and not nd['name'].startswith(('we_', 'ra_', 'p_', 'pool', 'slots', 'wer_')): print(nd['index'], nd['name'], nd['type'], nd['cols'], nd['rows'], nd['types'])
    else:
        t, rows = table(sys.argv[1], sys.argv[2]); print(t)
        for r in rows: print(' | '.join(r))

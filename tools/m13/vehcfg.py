"""Read vehicle config nodes (techn_base / techn_base_oprum) as typed cells and write gt3.ps1 row deltas.

Cell text forms are those of gt3.ps1 Cell-Encode: s: string, f: float, v: float vector, u: u32 (hex for dates, 'FOURCC'),
a: int vector, b: bool.
"""
import struct, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import azcf

def _fmt_single(x):
    import numpy as np
    x = float(np.float32(x))
    if x == 0: return '0'
    for p in (7, 9):
        t = ('%.' + str(p) + 'G') % x
        if 'E' in t:
            m, e = t.split('E'); e = int(e); t = m + 'E' + ('+' if e >= 0 else '-') + '%02d' % abs(e)
        if float(np.float32(float(t))) == x or p == 9: return t

def _esc(s): return s.replace('\\', '\\\\').replace('|', '\\|').replace('\n', '\\n').replace('\r', '\\r')

def cell(b, off):
    kind = struct.unpack_from('<I', b, off + 16)[0]
    v = struct.unpack_from('<4I', b, off)
    if kind == 2: return 's:' + _esc(azcf._cstr(b, v[1]) if v[1] else '')
    if kind == 4:
        x = v[0]
        if 0x19 <= (x >> 24) <= 0x20 and ((x >> 16) & 0xff) <= 0x99: return 'u:0x%08x' % x
        fc = azcf._fourcc(x)
        return ("u:'%s'" % fc) if fc else 'u:%d' % x
    if kind == 6:
        n = 3
        while n > 0 and v[n] == 0: n -= 1
        return 'a:' + ';'.join(str(i) for i in struct.unpack_from('<4i', b, off)[:n + 1])
    if kind == 1:
        n = 3
        while n > 0 and v[n] == 0: n -= 1
        return 'v:' + ';'.join(_fmt_single(f) for f in struct.unpack_from('<4f', b, off)[:n + 1])
    if kind == 0: return 'f:' + _fmt_single(struct.unpack_from('<f', b, off)[0])
    if kind == 5: return 'b:' + ('1' if v[0] else '0')
    return 'k%d:%08x;%08x;%08x;%08x' % (kind, *v)

def text(c):
    """display text of an encoded cell (what Resolve-RowIndex keys on)"""
    k, _, val = c.partition(':')
    if k == 'u' and val.startswith("'"): return val.strip("'")
    return val

class Vehicle:
    def __init__(self, path, name):
        b, nodes = azcf.read(path); self.b = b
        i = next(n['index'] for n in nodes if n['name'] == name)
        j = i + 1; self.tables = []
        while j < len(nodes) and not (nodes[j]['name'] != 'props' and j + 1 < len(nodes) and nodes[j + 1]['name'] == 'props'):
            n = nodes[j]; rows = []
            if n['type'] == 1:
                for r in range(n['rows']):
                    o = n['data'] + r * 0x40
                    rows.append([b[o + 0x20:o + 0x40].split(b'\0')[0].decode('cp1251'), cell(b, o)])
            else:
                for r in range(n['rows']):
                    o = n['data'] + r * 0x20 * n['cols']
                    rows.append([cell(b, o + c * 0x20) for c in range(n['cols'])])
            self.tables.append(dict(name=n['name'], type=n['type'], cols=n['cols'], types=n['types'], rows=rows))
            j += 1
        self.root_type = nodes[i]['type']
    def table(self, name): return next(t for t in self.tables if t['name'] == name)

def node_delta(vname, tables, after='@end', root_type=1):
    out = ['node+|%s|%d|0||%s' % (vname, root_type, after)]
    prev = '@top'
    for t in tables:
        path = vname + '/' + t['name']
        out.append('node+|%s|%d|%d|%s|%s' % (path, t['type'], t['cols'], t['types'], prev))
        prev = path
        last = '@end'
        for r in t['rows']:
            if t['type'] == 1:
                out.append('row+|%s|@end|%s|%s|%s' % (path, _esc(r[0]), _esc(r[0]), r[1]))
            else:
                out.append('row+|%s|@end|%s|%s' % (path, _esc(text(r[0])), '|'.join(r)))
    return out

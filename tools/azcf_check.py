"""Structural comparison of two AZCF files, independent of gt3.ps1 (python -I tools\azcf_check.py a.bin b.bin).

Compares everything the engine reads, ignoring only where things sit in the file: node names, types, column and
row counts, type strings, every cell (kind, numeric slots, string text), the kid lists, and the hash tables
(bucket count, home slot and kid index of every occupied bucket). Exit code 0 = identical, 1 = differences.
"""
import struct, sys

def cstr(b, off):
    return b[off:b.index(b'\0', off)]

def load(path):
    b = open(path, 'rb').read()
    assert b[:4] == b'AZCF', path
    count, table, rhsz, rhoff = struct.unpack_from('<4I', b, 4)
    nodes = []
    for i in range(count):
        o = table + i * 0x80
        f = struct.unpack_from('<11I', b, o + 0x20)
        n = dict(name=cstr(b, o) if b[o] else b'', type=f[0], cols=f[1], rows=f[2], types=cstr(b, f[3]), nkids=f[6], hsz=f[9], fhsz=f[7])
        kids = struct.unpack_from('<%dI' % f[6], b, f[5]) if f[6] else ()
        n['kids'] = [(b[table + k * 0x80:table + k * 0x80 + 0x20].split(b'\0')[0]) for k in kids]
        n['kididx'] = list(kids)
        hashes = []
        for s in range(f[9]):
            a, c = struct.unpack_from('<2I', b, f[10] + s * 8)
            if a & 0x80000000:
                hashes.append((s, a & 0x7fffffff, c))
        n['hash'] = hashes
        fh = []   # field-name hash table of a struct (node fields 7/8)
        for s in range(f[7]):
            a, c = struct.unpack_from('<2I', b, f[8] + s * 8)
            if a & 0x80000000:
                fh.append((s, a & 0x7fffffff, c))
        n['fhash'] = fh
        cells = []
        if n['type'] == 1:
            for r in range(n['rows']):
                co = f[4] + r * 0x40
                cells.append((b[co + 0x20:co + 0x40].split(b'\0')[0], cell(b, co)))
        elif n['type'] == 2:
            for r in range(n['rows']):
                row = []
                for c in range(n['cols']):
                    row.append(cell(b, f[4] + (r * n['cols'] + c) * 0x20))
                cells.append(tuple(row))
        n['cells'] = cells
        nodes.append(n)
    return dict(name=cstr(b, 0x20), rhsz=rhsz, nodes=nodes, size=len(b))

def cell(b, co):
    s = struct.unpack_from('<8I', b, co)
    if s[4] == 2:
        return ('s', cstr(b, s[1]) if s[1] else b'', s[0], s[2], s[3], s[5], s[6], s[7])
    return s

def compare(A, B):
    out = []
    if A['name'] != B['name']:
        out.append('header name %r vs %r' % (A['name'], B['name']))
    if A['rhsz'] != B['rhsz']:
        out.append('root hash size %d vs %d' % (A['rhsz'], B['rhsz']))
    if len(A['nodes']) != len(B['nodes']):
        out.append('node count %d vs %d' % (len(A['nodes']), len(B['nodes'])))
    for i, (a, b) in enumerate(zip(A['nodes'], B['nodes'])):
        for k in ('name', 'type', 'cols', 'rows', 'types', 'nkids', 'hsz', 'kids', 'kididx', 'hash', 'fhsz', 'fhash'):
            if a[k] != b[k]:
                out.append('node %d %s: %s differs: %r vs %r' % (i, a['name'], k, str(a[k])[:80], str(b[k])[:80]))
        if a['cells'] != b['cells']:
            for r, (ra, rb) in enumerate(zip(a['cells'], b['cells'])):
                if ra != rb:
                    out.append('node %d %s row %d differs: %r vs %r' % (i, a['name'], r, str(ra)[:100], str(rb)[:100]))
                    break
    return out

if __name__ == '__main__':
    A = load(sys.argv[1]); B = load(sys.argv[2])
    d = compare(A, B)
    for line in d[:30]:
        print(line)
    print('%s: %d nodes, %d vs %d bytes, %d differences' % ('IDENTICAL' if not d else 'DIFFERENT', len(A['nodes']), A['size'], B['size'], len(d)))
    sys.exit(1 if d else 0)

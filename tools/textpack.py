"""AZTX text pack writer (polygon place names etc.), layout verified against 6m_mius_text.loc_eng.textpack:
  0x00 'AZTX', u32 1, u32 0x20, u32 0, u32 0x20, zeros; 0x20 loc name (char[0x20], e.g. 'loc_eng')
  0x40 u32 key count, u32 key records offset, u32 bucket count, u32 bucket table offset (0x50)
  0x50 bucket table: count x {u32 0x80000000|hash, u32 key record offset}, linear probing; hash = AZP3 string hash of the key
  key records 0x30: char[0x20] key, u32 item count, u32 items offset, u32 hash, u32 0
  items 0x10: u32 length, u32 string offset, u64 0; strings NUL-terminated cp1251, packed in order.
"""
import struct

def azhash(s, N):
    h = 0; M = 1 << 32; a = 0x7e9f
    for ch in s.encode('cp1251'):
        c = ch - 256 if ch >= 128 else ch
        t = (a * h) % M + c
        if t < 0: t += M
        h = (t % M) % N; a = ((a * 0x6a2f) % M) % (N - 1)
    return h

def write(path, loc, entries):
    """entries: list of (key, [strings]) in file order."""
    n = len(entries); nb = 16
    while nb < 3 * n: nb *= 2
    bt = 0x50; kr = bt + nb * 8; ip = kr + n * 0x30
    nitems = sum(len(v) for _, v in entries); sp = ip + nitems * 0x10
    strings = b''; items = b''; recs = b''; so = sp
    for key, vals in entries:
        recs += key.encode('cp1251').ljust(0x20, b'\0')[:0x20] + struct.pack('<4I', len(vals), ip + len(items), azhash(key, nb), 0)
        for v in vals:
            enc = v.encode('cp1251')
            items += struct.pack('<IIQ', len(enc), so, 0); strings += enc + b'\0'; so += len(enc) + 1
    buckets = [None] * nb
    for i, (key, _) in enumerate(entries):
        h = azhash(key, nb); k = h
        while buckets[k] is not None: k = (k + 1) % nb
        buckets[k] = (0x80000000 | h, kr + i * 0x30)
    btab = b''.join(struct.pack('<II', *b) if b else b'\0' * 8 for b in buckets)
    hdr = bytearray(0x40); hdr[0:4] = b'AZTX'; struct.pack_into('<4I', hdr, 4, 1, 0x20, 0, 0x20)
    hdr[0x20:0x20 + len(loc)] = loc.encode()
    hdr2 = struct.pack('<4I', n, kr, nb, bt)
    open(path, 'wb').write(bytes(hdr[:0x40]) + hdr2 + btab + recs + items + strings)

def read(path):
    b = open(path, 'rb').read(); n, kr, nb, bt = struct.unpack_from('<4I', b, 0x40); out = []
    for i in range(n):
        o = kr + i * 0x30; k = b[o:o + 0x20].split(b'\0')[0].decode('cp1251'); cnt, ip, h, _ = struct.unpack_from('<4I', b, o + 0x20)
        vals = []
        for j in range(cnt):
            ln, so, _ = struct.unpack_from('<IIQ', b, ip + j * 0x10); vals.append(b[so:so + ln].decode('cp1251'))
        out.append((k, vals))
    return b[0x20:0x40].split(b'\0')[0].decode(), out

TRANSLIT = {'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo', 'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l',
            'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh',
            'щ': 'shch', 'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'}

def translit(s):
    out = []
    for i, ch in enumerate(s):
        lo = ch.lower(); t = TRANSLIT.get(lo, ch)
        if lo == 'е' and (i == 0 or s[i - 1].lower() in 'аеёиоуыэюяьъ '): t = 'ye'
        out.append(t.capitalize() if ch.isupper() else t)
    return ''.join(out)

if __name__ == '__main__':
    import sys
    loc, e = read(sys.argv[1]); print(loc); [print(k, v) for k, v in e]

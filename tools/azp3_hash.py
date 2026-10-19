"""Probe the AZP3 (.flatdata) name hash table.

usage: python -I azp3_hash.py <archive.flatdata> [...]
Dumps bucket count, the (home_slot, entry_index) pairs, and tests candidate hash functions
against the recorded home slots so the packer can write a table the engine accepts.
"""
import struct
import sys
import zlib

MASK = 0xFFFFFFFF


def read(path):
    b = open(path, 'rb').read()
    assert b[:4] == b'AZP3', path
    count = struct.unpack_from('<I', b, 4)[0]
    buckets = struct.unpack_from('<I', b, 8)[0]
    slots = {}
    for i in range(buckets):
        s, idx = struct.unpack_from('<II', b, 0x40 + i * 8)
        if s:
            slots[i] = (s & 0x7FFFFFFF, idx)
    entries = []
    base = 0x40 + buckets * 8
    for i in range(count):
        o = base + i * 0x80
        name = b[o + 0x20:o + 0x40].split(b'\0')[0].decode('latin1')
        kind = b[o + 0x40:o + 0x60].split(b'\0')[0].decode('latin1')
        loc = b[o + 0x60:o + 0x80].split(b'\0')[0].decode('latin1')
        entries.append((name, kind, loc))
    return count, buckets, slots, entries


def fnv1(s, h=0x811C9DC5):
    for c in s:
        h = (h * 0x01000193) & MASK
        h ^= c
    return h


def fnv1a(s, h=0x811C9DC5):
    for c in s:
        h ^= c
        h = (h * 0x01000193) & MASK
    return h


def djb2(s, h=5381):
    for c in s:
        h = (h * 33 + c) & MASK
    return h


def djb2x(s, h=5381):
    for c in s:
        h = ((h * 33) ^ c) & MASK
    return h


def sdbm(s):
    h = 0
    for c in s:
        h = (c + (h << 6) + (h << 16) - h) & MASK
    return h


def java(s):
    h = 0
    for c in s:
        h = (h * 31 + c) & MASK
    return h


def elf(s):
    h = 0
    for c in s:
        h = ((h << 4) + c) & MASK
        g = h & 0xF0000000
        if g:
            h ^= g >> 24
        h &= ~g & MASK
    return h


def crc(s):
    return zlib.crc32(s) & MASK


def jenkins_oaat(s):
    h = 0
    for c in s:
        h = (h + c) & MASK
        h = (h + (h << 10)) & MASK
        h ^= h >> 6
    h = (h + (h << 3)) & MASK
    h ^= h >> 11
    h = (h + (h << 15)) & MASK
    return h


def mul_hash(s, m=65599):
    h = 0
    for c in s:
        h = (h * m + c) & MASK
    return h


def rot_hash(s):
    h = 0
    for c in s:
        h = (((h << 5) | (h >> 27)) & MASK) ^ c
    return h


HASHES = {
    'fnv1': fnv1, 'fnv1a': fnv1a, 'djb2': djb2, 'djb2x': djb2x, 'sdbm': sdbm, 'java31': java,
    'elf': elf, 'crc32': crc, 'oaat': jenkins_oaat, 'mul65599': mul_hash, 'rot5': rot_hash,
}


def keys(name, kind, loc):
    yield 'name', name.encode()
    yield 'name_lower', name.lower().encode()
    yield 'name0', name.encode() + b'\0'
    yield 'name+kind', (name + kind).encode()
    yield 'name+kind+loc', (name + kind + loc).encode()
    yield 'name.kind', (name + '.' + kind).encode()
    yield 'name.kind.loc', (name + '.' + kind + '.' + loc).encode()
    yield 'name32', name.encode().ljust(0x20, b'\0')
    yield 'name32+kind32+loc32', name.encode().ljust(0x20, b'\0') + kind.encode().ljust(0x20, b'\0') + loc.encode().ljust(0x20, b'\0')
    yield 'kind+name', (kind + name).encode()


def probe(path):
    count, buckets, slots, entries = read(path)
    print(f'{path}\n  count={count} buckets={buckets} used_slots={len(slots)}')
    if not buckets:
        return
    home = {}
    for i, (h, idx) in slots.items():
        home[idx] = h
    # sanity: show a few
    for idx in list(home)[:4]:
        print(f'    entry {idx} {entries[idx]} home_slot={home[idx]}')
    mask = buckets - 1
    results = []
    for hname, fn in HASHES.items():
        for kname in [k for k, _ in keys('a', 'b', 'c')]:
            ok = 0
            for idx, h in home.items():
                name, kind, loc = entries[idx]
                kb = dict(keys(name, kind, loc))[kname]
                v = fn(kb)
                if (v & mask) == h or (v % buckets) == h or ((v >> 16) & mask) == h or ((v ^ (v >> 16)) & mask) == h:
                    ok += 1
            results.append((ok, hname, kname))
    results.sort(reverse=True)
    print('  best candidates (matches / entries):')
    for ok, hname, kname in results[:6]:
        print(f'    {ok:4d}/{len(home)}  {hname:10s} over {kname}')


if __name__ == '__main__':
    for p in sys.argv[1:]:
        probe(p)

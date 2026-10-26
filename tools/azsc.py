r"""AZSC operation script pack (scripts.script.loc_def.bin) - decoded 2026-10-25 from 07_30_Stepanovka / 07_12_Prokhorovka.

Layout (all little-endian):
  0x00 'AZSC'  u32 n_arg_strings  u32 n_arg_strings + n_funcs  u32 n_builtins (18)  u32 func_table_off (0x30)  u32 n_funcs
  0x18 u32 instr_off  u32 n_instr  u32 tags_off  u32 n_args  u32 strtab_off  u32 n_strings            (12 words, 0x30 bytes)
  func table: n_funcs x u32 = first instruction index of each function; the string table holds first the strings used
              as arguments (in order of first use), then the function names (sorted: at_end, at_start, brief_*, draw_brief_*,
              settings, turn_*), then the 18 builtin names (sorted) - so string[n_arg_strings + k] names function k
  instructions: n_instr x (u16 opcode, u16 n_args, u32 first_arg)   opcode = index into the builtin names (sorted):
              break brush call commit_lines commit_text dump font line line_scale line_style log order pen polygon ret
              text text_color text_scale
  tags: n_args bytes: 0 float, 2 string (index into the string table), 3 int, 4 u32 (colour 0xAARRGGBB / flags)
  values: n_args x 4 bytes (float / u32)
  string table: n_strings x (u16 off, u16 len) relative to strtab_off, then the NUL-terminated cp1251 strings

Drawing calls (coordinates are fractions 0..1 of the op-map area, x east, y south):
  pen(colour, flags, width)  line_style(style, dash, style2, dash2)  line(x0, y0, x1, y1[, ...])  brush(colour)
  polygon(x0, y0, ..., xn, yn)  text_color(colour)  text(string, x, y, w, h, angle, flags, align)
  font / line_scale / text_scale (settings), commit_lines / commit_text (end of a drawing batch), call(func), ret, break,
  log(string), order(...) (AI orders of the turn functions), dump
"""
import struct

BUILTINS = 'break brush call commit_lines commit_text dump font line line_scale line_style log order pen polygon ret text text_color text_scale'.split()
OP = {n: i for i, n in enumerate(BUILTINS)}


def read(path):
    b = open(path, 'rb').read()
    assert b[:4] == b'AZSC'
    h = struct.unpack_from('<12I', b, 0)
    nb, ftab, nf, ioff, ni, toff, na, soff, ns = h[3], h[4], h[5], h[6], h[7], h[8], h[9], h[10], h[11]
    funcs = list(struct.unpack_from('<%dI' % nf, b, ftab))
    strs = []
    for i in range(ns):
        o, l = struct.unpack_from('<HH', b, soff + 4 * i); strs.append(b[soff + o:soff + o + l].decode('cp1251', 'replace'))
    tags = b[toff:toff + na]; voff = toff + na
    instrs = []
    for i in range(ni):
        op, n, a0 = struct.unpack_from('<HHI', b, ioff + 8 * i)
        args = []
        for k in range(n):
            t = tags[a0 + k]; raw = b[voff + 4 * (a0 + k):voff + 4 * (a0 + k) + 4]
            if t == 0: v = struct.unpack('<f', raw)[0]
            elif t == 2: v = strs[struct.unpack('<I', raw)[0]]
            elif t == 3: v = struct.unpack('<i', raw)[0]
            else: v = struct.unpack('<I', raw)[0]
            args.append((t, v))
        instrs.append((op, args))
    return dict(header=h, funcs=funcs, strs=strs, instrs=instrs, a=h[1], b=h[2], names=strs[h[1]:h[2]])


def func_names(d):
    """the function names: string-table entries n_arg_strings .. n_arg_strings + n_funcs, same order as the func table"""
    return d['names']


def disasm(d, start, end=None):
    out = []
    end = end if end is not None else len(d['instrs'])
    for i in range(start, end):
        op, args = d['instrs'][i]
        def f(t, v):
            if t == 0: return '%.4g' % v
            if t == 2: return repr(v)
            if t == 4: return '0x%08x' % v
            return str(v)
        out.append('%5d %-12s %s' % (i, BUILTINS[op], ', '.join(f(t, v) for t, v in args)))
    return '\n'.join(out)


def write(path, funcs, strs, instrs, a, b):
    """funcs: first-instruction index per function (in the order of their names in strs[a:b]); instrs: (op, [(tag, value), ...]);
    a = number of argument strings (they come first in strs), b = a + number of functions."""
    sidx = {}
    for i, s in enumerate(strs): sidx.setdefault(s, i)
    tags = bytearray(); vals = bytearray(); irec = bytearray()
    for op, args in instrs:
        irec += struct.pack('<HHI', op, len(args), len(tags))
        for tg, v in args:
            tags.append(tg)
            if tg == 0: vals += struct.pack('<f', float(v))
            elif tg == 2: vals += struct.pack('<I', sidx[v])
            elif tg == 3: vals += struct.pack('<i', int(v))
            else: vals += struct.pack('<I', int(v) & 0xffffffff)
    ftab = struct.pack('<%dI' % len(funcs), *funcs)
    ioff = 0x30 + len(ftab); toff = ioff + len(irec); soff = toff + len(tags) + len(vals)
    enc = [s.encode('cp1251') for s in strs]
    sdata = bytearray(); sindex = bytearray(); base = 4 * len(strs)
    for e in enc:
        sindex += struct.pack('<HH', base + len(sdata), len(e)); sdata += e + b'\0'
    hdr = struct.pack('<4sIIIIIIIIIII', b'AZSC', a, b, len(BUILTINS), 0x30, len(funcs), ioff, len(instrs), toff, len(tags), soff, len(strs))
    return open(path, 'wb').write(hdr + ftab + irec + bytes(tags) + bytes(vals) + bytes(sindex) + bytes(sdata))


if __name__ == '__main__':
    import sys
    d = read(sys.argv[1])
    names = func_names(d)
    print('header', [hex(v) for v in d['header']]); print('functions:', list(zip(names, d['funcs'])))
    if len(sys.argv) > 2:
        k = names.index(sys.argv[2]); s = d['funcs'][k]
        e = min([f for f in d['funcs'] if f > s] + [len(d['instrs'])])
        print(disasm(d, s, e))

"""Measure or scale Graviteam AAF2 sound entries (<name>.sound.loc_def.bin).

Format (verified on build 3598): 'AAF2', u32 total length, 4 bytes 0, WAVEFORMATEX (16 bytes:
tag 1 = PCM, channels, sample rate, byte rate, block align, bits), zero padding to 0x40, then raw PCM.

usage:
  python -I sound_gain.py stats <file> [<file> ...]
  python -I sound_gain.py apply <in> <out> <gain_db>
"""
import array
import math
import struct
import sys

HDR = 0x40


def read(path):
    with open(path, 'rb') as f:
        b = f.read()
    if b[:4] != b'AAF2':
        raise SystemExit(f'{path}: not AAF2')
    total, tag, ch, rate, brate, align, bits = struct.unpack_from('<I4xHHIIHH', b, 4)
    if tag != 1 or bits != 16:
        raise SystemExit(f'{path}: unsupported format tag={tag} bits={bits}')
    pcm = array.array('h')
    pcm.frombytes(b[HDR:HDR + ((len(b) - HDR) // 2) * 2])
    return b, pcm, ch, rate, total


def db(x):
    return -999.0 if x <= 0 else 20 * math.log10(x)


def stats(path):
    b, pcm, ch, rate, total = read(path)
    n = len(pcm)
    peak = max(abs(s) for s in pcm) if n else 0
    rms = math.sqrt(sum(s * s for s in pcm) / n) if n else 0
    # loudest 1-second window (RMS), to compare a sustained hiss with a short bang fairly
    win = rate * ch
    best = 0.0
    if n >= win:
        acc = sum(s * s for s in pcm[:win])
        best = acc
        for i in range(win, n):
            acc += pcm[i] * pcm[i] - pcm[i - win] * pcm[i - win]
            if acc > best:
                best = acc
        best = math.sqrt(best / win)
    secs = n / (rate * ch) if rate else 0
    print(f'{path}\n  len={len(b)} hdr_total={total} ch={ch} rate={rate} dur={secs:.1f}s '
          f'peak={db(peak / 32768):.1f} dBFS rms={db(rms / 32768):.1f} dBFS loudest1s={db(best / 32768):.1f} dBFS')


def apply(src, dst, gain_db):
    b, pcm, ch, rate, total = read(src)
    g = 10 ** (gain_db / 20)
    out = array.array('h', (max(-32768, min(32767, int(round(s * g)))) for s in pcm))
    with open(dst, 'wb') as f:
        f.write(b[:HDR])
        f.write(out.tobytes())
        f.write(b[HDR + len(out) * 2:])  # keep any odd trailing byte
    print(f'wrote {dst}: gain {gain_db:+.1f} dB (x{g:.3f}), {len(out)} samples, header untouched')


if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == 'stats':
        for p in sys.argv[2:]:
            stats(p)
    elif len(sys.argv) == 5 and sys.argv[1] == 'apply':
        apply(sys.argv[2], sys.argv[3], float(sys.argv[4]))
    else:
        print(__doc__)
        sys.exit(2)

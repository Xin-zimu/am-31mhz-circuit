import zlib, bz2, lzma, struct, sys
from pathlib import Path

def try_all(tag, data, off):
    for wbits in (31, 15, -15):
        try:
            d = zlib.decompressobj(wbits)
            out = d.decompress(data[off:])
            if len(out) > 200:
                print('  %s @%d zlib wbits=%d -> %d bytes: %r' % (tag, off, wbits, len(out), out[:160]))
                return True
        except Exception:
            pass
    return False

for f in sys.argv[1:]:
    b = Path(f).read_bytes()
    print('==== %s  size=%d' % (Path(f).name, len(b)))
    print('  magic: %r' % b[:40])
    # gzip markers
    poss = []
    i = 0
    while True:
        i = b.find(b'\x1f\x8b\x08', i)
        if i < 0: break
        poss.append(i); i += 1
    print('  gzip-like markers at:', poss[:20])
    for p in poss[:6]:
        print('   context before %d: %r' % (p, b[max(0,p-24):p]))
        if try_all('gz', b, p):
            break
    # try decompressing right after the 45-byte-ish header
    for off in (36, 32, 40, 44, 48, 56):
        if off < len(b):
            try_all('hdr', b, off)

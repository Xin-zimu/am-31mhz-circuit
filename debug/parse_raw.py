import struct, sys, math
from pathlib import Path

def parse_raw(p):
    b = Path(p).read_bytes()
    i = b.find(b'Binary:\n')
    if i < 0:
        raise SystemExit('no binary marker')
    head = b[:i].decode('latin-1')
    data = b[i+len('Binary:\n'):]
    nvars = int([l for l in head.splitlines() if l.startswith('No. Variables')][0].split(':')[1])
    npts  = int([l for l in head.splitlines() if l.startswith('No. Points')][0].split(':')[1])
    names = []
    inb = False
    for l in head.splitlines():
        if l.startswith('Variables:'):
            inb = True; continue
        if inb:
            parts = l.split()
            if len(parts) >= 4:
                names.append(parts[-1])
    need = nvars*npts*8
    n = min(len(data), need)
    vals = struct.unpack('<%dd' % (n//8), data[:n - n % 8])
    cols = [vals[k::nvars] for k in range(nvars)]
    return head, names, cols, npts

if __name__ == '__main__':
    head, names, cols, npts = parse_raw(sys.argv[1])
    print(head.strip()[:400])
    print('names:', names)
    t = cols[0]
    print('points parsed: %d, t0=%.12g  t1=%.12g  span=%.6g s' % (len(t), t[0], t[-1], t[-1]-t[0]))
    d = [t[k+1]-t[k] for k in range(min(len(t)-1, 200000))]
    import statistics
    print('dt: min=%.6g max=%.6g mean=%.6g median=%.6g' % (min(d), max(d), statistics.mean(d), statistics.median(d)))
    for k, nm in enumerate(names):
        c = cols[k]
        print('  %-10s min=%+.6g max=%+.6g' % (nm, min(c), max(c)))

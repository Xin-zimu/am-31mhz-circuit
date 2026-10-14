import struct, sys, statistics
from pathlib import Path

def parse_raw(p):
    b = Path(p).read_bytes()
    i = b.find(b'Binary:\n')
    head = b[:i].decode('latin-1')
    data = b[i+len('Binary:\n'):]
    nvars = int([l for l in head.splitlines() if 'No. Variables' in l][0].split(':')[1])
    npts  = int([l for l in head.splitlines() if 'No. Points' in l][0].split(':')[1])
    names=[]; inb=False
    for l in head.splitlines():
        if l.startswith('Variables:'): inb=True; continue
        if inb:
            parts=l.split()
            if len(parts)>=3: names.append(parts[-1])
    n = min(len(data), nvars*npts*8); n -= n % 8
    vals = struct.unpack('<%dd'%(n//8), data[:n])
    cols = [vals[k::nvars] for k in range(nvars)]
    return head, names, cols

head, names, cols = parse_raw(sys.argv[1])
print(head.strip()[:300])
d = {n: c for n, c in zip(names, cols)}
t = d['time']
print('points=%d  t=[%g, %g]  span=%.6g' % (len(t), t[0], t[-1], t[-1]-t[0]))
dt = [t[i+1]-t[i] for i in range(len(t)-1)]
print('dt min=%.4g max=%.4g median=%.6g' % (min(dt), max(dt), statistics.median(dt)))
for n in names:
    if n == 'time': continue
    c = d[n]
    print('  %-16s min=%+.6g max=%+.6g' % (n, min(c), max(c)))

# AM envelope check: peak of $tp3 within each 22.727us input high/low window
for key in ('$tp3', '$tp6', '$v2'):
    if key not in d: continue
    c = d[key]
    seg = 22.727272727e-6
    print('\n%s peak per %.3f us window:' % (key, seg*1e6))
    k = 0
    for j in range(1, 9):
        t0, t1 = (j-1)*seg, j*seg
        idx = [i for i in range(len(t)) if t0 <= t[i] < t1]
        if len(idx) < 10: continue
        pk = max(c[i] for i in idx); mn = min(c[i] for i in idx)
        tv1 = statistics.mean(d['$v1'][i] for i in idx)
        print('   win%d t=[%7.3f,%7.3f]us  meanV(v1)=%.3f  %s peak=%+.4f  min=%+.4f'
              % (j, t0*1e6, t1*1e6, tv1, key, pk, mn))

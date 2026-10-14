import sys, statistics
from pathlib import Path

def parse_ascii_raw(p):
    txt = Path(p).read_text(errors='replace')
    head, body = txt.split('Values:', 1)
    names = []
    inb = False
    for l in head.splitlines():
        if l.startswith('Variables:'): inb = True; continue
        if inb:
            parts = l.split()
            if len(parts) >= 3: names.append(parts[-1])
    cols = [[] for _ in names]
    cur = None
    for l in body.splitlines():
        l = l.rstrip('\r\n')
        if not l.strip(): continue
        segs = [s for s in l.split('\t') if s.strip() != '']
        if len(segs) == 2 and segs[0].strip().isdigit():
            # new point: "<idx>\t<value0>"
            cur = 0
            cols[0].append(float(segs[1]))
            cur = 1
            continue
        if len(segs) >= 1 and cur is not None and cur < len(cols):
            v = segs[-1].strip()
            if ',' in v: v = v.split(',')[0]
            cols[cur].append(float(v))
            cur += 1
    n = min(len(c) for c in cols)
    return head, names, [c[:n] for c in cols]

path = sys.argv[1]
head, names, cols = parse_ascii_raw(path)
d = {n: c for n, c in zip(names, cols)}
print('points=%d vars=%d' % (len(cols[0]), len(names)))
wanted = [w for w in sys.argv[2:]] or ['time', 'V(tp3)', 'V(tp6)', 'V(v1)', 'V(v2)']
print('names:', names)
t = d.get('time', cols[0])
print('t=[%g, %g] span=%.6g s' % (t[0], t[-1], t[-1]-t[0]))
dt = [t[i+1]-t[i] for i in range(len(t)-1)]
print('dt min=%.4g max=%.4g median=%.6g  npts=%d' % (min(dt), max(dt), statistics.median(dt), len(t)))

seg = 22.727272727e-6
v1 = d.get('V(v1)')
import bisect
for key in ('V(tp2)', 'V(tp3)', 'V(tp6)', 'V(v2)'):
    if key not in d: continue
    c = d[key]
    print('\n%s : min=%+.5f max=%+.5f' % (key, min(c), max(c)))
    for j in range(1, 13):
        t0, t1 = (j-1)*seg, j*seg
        a = bisect.bisect_left(t, t0); b = bisect.bisect_left(t, t1)
        if b - a < 20: continue
        pk = max(c[a:b]); mn = min(c[a:b])
        mv1 = statistics.mean(v1[a:b]) if v1 else float('nan')
        print('   win%2d t=[%7.2f,%7.2f]us meanV(v1)=%.3f  peak=%+.4f min=%+.4f pk-pk=%.4f'
              % (j, t0*1e6, t1*1e6, mv1, pk, mn, pk-mn))

import sys, struct
from pathlib import Path

ROOT = Path(r'D:\multimism\Circuit Design Suite 14.3')
NEEDLES = ['Internal simulation error', '内部仿真', '仿真错误', 'number of points', 'Maximum number of points',
           'Too many points', 'too many points', 'Timestep too small', 'timestep too small', 'singular matrix',
           'no convergence', 'No convergence']

def strings(data, minlen=4):
    out = []
    cur = bytearray()
    for byte in data:
        if 32 <= byte < 127:
            cur.append(byte)
        else:
            if len(cur) >= minlen:
                out.append(bytes(cur))
            cur = bytearray()
    if len(cur) >= minlen:
        out.append(bytes(cur))
    return out

hits = {}
files = list(ROOT.glob('*.dll')) + list(ROOT.glob('*.exe'))
for f in files:
    try:
        data = f.read_bytes()
    except Exception:
        continue
    # ASCII
    for n in NEEDLES:
        b = n.encode('ascii', 'ignore')
        if b and b in data:
            hits.setdefault(n, []).append(str(f.name))
    # UTF-16LE
    for n in NEEDLES:
        b = n.encode('utf-16le')
        if b in data:
            hits.setdefault(n + ' [utf16]', []).append(str(f.name))

for k, v in hits.items():
    print('%-40s -> %s' % (k, ', '.join(sorted(set(v))[:8])))
print('--- scanned %d files ---' % len(files))

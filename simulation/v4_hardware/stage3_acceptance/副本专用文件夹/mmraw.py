"""Minimal Multisim XSPICE ASCII .raw reader (read-only)."""
import numpy as np
from pathlib import Path

def read_raw(path):
    text = Path(path).read_text(encoding='ascii', errors='replace')
    lines = text.split('\n')
    nvars = None
    vnames = []
    for i, l in enumerate(lines):
        if l.startswith('No. Variables:'):
            nvars = int(l.split(':')[1])
        if l.startswith('No. Points:'):
            npoints = int(l.split(':')[1])
        if l.strip() == 'Variables:':
            for j in range(i + 1, i + 1 + nvars):
                parts = lines[j].split('\t')
                vnames.append(parts[-1].strip() if parts[-1].strip() else parts[1].strip())
        if l.strip() == 'Values:':
            start = i + 1
            break
    body = '\n'.join(lines[start:])
    toks = body.split()
    per = nvars + 1  # index + values
    n = len(toks) // per
    assert n == npoints, (n, npoints)
    arr = np.array(toks[:n * per], dtype=object)
    # build numeric matrix
    num = np.array(toks[:n * per], dtype=object)
    vals = np.empty((n, nvars), dtype=float)
    for k in range(n):
        base = k * per
        vals[k, :] = [float(x) for x in toks[base + 1:base + per]]
    return vnames, vals

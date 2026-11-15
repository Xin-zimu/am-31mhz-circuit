"""Check the antenna-current envelope properly before trusting m = 99.6%.

final_driver.py reported m = 99.6%, which cannot be right for a chain whose
modulation index is 24%. The likely cause is the envelope extraction: taking
max/min over every carrier cycle in a long window will pick up any single glitch,
and using peak |i| per cycle double-counts negative half-cycles.

Correct method: for each AM plateau, take the peak of the *signed* carrier, and
compute m from the two plateau levels. This script prints the per-cycle envelope so
the shape can be inspected instead of only its min and max.
"""
import re
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def read_raw(p):
    b = p.read_bytes()
    off = b.index(b"Binary:\n")
    h = b[:off].decode("latin1")
    nv = int(re.search(r"No\. Variables:\s+(\d+)", h)[1])
    n = int(re.search(r"No\. Points:\s+(\d+)", h)[1])
    names = re.findall(r"^\s*\d+\s+(\S+)\s+\S+\s*$", h.rsplit("Variables:", 1)[1], re.M)
    a = np.frombuffer(b, dtype=np.float64, count=nv * n, offset=off + 8).reshape(n, nv)
    return dict(zip(names, a.T))


d = read_raw(ROOT / "results" / "det_c_nom.raw")
t = d["time"]
i = d["i(ltune)"]
v1 = d["v(v1)"]

sel = t > 1.5e-3
t, i, v1 = t[sel], i[sel], v1[sel]

thr = (np.quantile(v1, .05) + np.quantile(v1, .95)) / 2
high = v1 > thr

# carrier cycle peaks of the signed current
zc = np.flatnonzero((i[:-1] < 0) & (i[1:] >= 0))
cyc_t = t[zc[:-1]]
cyc_peak = np.array([np.max(i[a:b]) for a, b in zip(zc[:-1], zc[1:])])
cyc_trough = np.array([np.min(i[a:b]) for a, b in zip(zc[:-1], zc[1:])])

print(f"steady window: {t[0]*1e3:.3f} - {t[-1]*1e3:.3f} ms, "
      f"{len(cyc_peak)} carrier cycles")
print()
print(f"{'cycle':>6} {'t/us':>9} {'peak/mA':>9} {'trough/mA':>10} {'plateau':>8}")
for k in range(0, len(cyc_peak), max(1, len(cyc_peak) // 30)):
    print(f"{k:6d} {cyc_t[k]*1e6:9.2f} {cyc_peak[k]*1e3:9.3f} "
          f"{cyc_trough[k]*1e3:10.3f} {'H' if high[zc[k]] else 'L':>8}")

print()
hi_pl = [cyc_peak[k] for k in range(len(cyc_peak)) if high[zc[k]]]
lo_pl = [cyc_peak[k] for k in range(len(cyc_peak)) if not high[zc[k]]]
if hi_pl and lo_pl:
    h, l = float(np.mean(hi_pl)), float(np.mean(lo_pl))
    print(f"plateau-averaged peak current: high {h*1e3:.3f} mA, low {l*1e3:.3f} mA")
    print(f"-> modulation index m = {(h-l)/(h+l)*100:.2f}%")
print()
print(f"global max peak {cyc_peak.max()*1e3:.3f} mA, global min peak "
      f"{cyc_peak.min()*1e3:.3f} mA")
print("note: the global min/max pair includes the AM transition region, which is")
print("      why a naive max/min ratio over the whole window overstates m.")

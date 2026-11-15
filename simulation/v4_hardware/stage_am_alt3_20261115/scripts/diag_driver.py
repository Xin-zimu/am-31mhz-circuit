"""Diagnose why the driver variant draws 81 mA and delivers no antenna current."""
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


for name in ("drv3_a", "drv2_ef_only"):
    p = ROOT / "results" / f"{name}.raw"
    if not p.exists():
        print(name, "missing")
        continue
    d = read_raw(p)
    t = d["time"]
    print("=" * 70)
    print(name, "  points:", len(t), "  t_end:", f"{t[-1]*1e3:.3f} ms")
    print("  variables:", [k for k in d if k != "time"])
    print()
    for k in d:
        if k == "time":
            continue
        y = d[k]
        print(f"  {k:12} mean {np.mean(y):9.4f}  min {np.min(y):9.4f} "
              f"max {np.max(y):9.4f}  ptp {np.ptp(y):9.4f}")
    print()
    print("  last 200 us:")
    sel = t > t[-1] - 200e-6
    for k in d:
        if k == "time":
            continue
        y = d[k][sel]
        print(f"  {k:12} mean {np.mean(y):9.4f}  min {np.min(y):9.4f} "
              f"max {np.max(y):9.4f}  ptp {np.ptp(y):9.4f}")

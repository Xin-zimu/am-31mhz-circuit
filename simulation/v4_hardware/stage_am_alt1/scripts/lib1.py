# -*- coding: utf-8 -*-
"""Shared utilities for stage AM-ALT.1 (ngspice flow)."""
import os, sys, subprocess, json, numpy as np
NG = r"D:\ms_xsp\s04_crosscheck_20261017\Spice64\bin\ngspice_con.exe"
ST = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from ngraw import load_ngraw

def run_ng(net_path, out_raw, cwd, timeout=2400, extra=""):
    """Wrap a circuit in a .control block and run ngspice."""
    body = open(net_path, encoding="latin-1").read() if isinstance(net_path, str) else net_path
    p = os.path.join(cwd, os.path.basename(out_raw).replace(".raw", ".cir"))
    with open(p, "w", encoding="latin-1") as f:
        f.write(body)
        f.write("\n.control\nset filetype=ascii\n" + extra +
                "write %s all\nquit\n.endc\n.end\n" % out_raw)
    r = subprocess.run([NG, "-b", os.path.basename(p)], capture_output=True,
                       text=True, encoding="utf-8", errors="replace",
                       timeout=timeout, cwd=cwd)
    rp = os.path.join(cwd, out_raw)
    ok = os.path.exists(rp) and os.path.getsize(rp) > 200
    return (load_ngraw(rp) if ok else None), r, ok

def carrier_vpp(t, v, f0=31e6, ncyc=200):
    T = ncyc / f0
    m = t >= t[-1] - T
    return float(v[m].max() - v[m].min())

def envelope(t, v, fc=31e6, ncyc=32):
    """Per-window peak/trough envelope."""
    T = ncyc / fc; n = int((t[-1] - t[0]) / T)
    hi = np.empty(n); lo = np.empty(n); tc = np.empty(n); k = 0
    for i in range(n):
        a = t[0] + i*T; b = a + T
        m = (t >= a) & (t < b)
        if m.sum() < 3: continue
        hi[k] = v[m].max(); lo[k] = v[m].min(); tc[k] = 0.5*(a+b); k += 1
    return tc[:k], hi[:k], lo[:k]

def am_metrics(t, v, fc=31e6):
    """VH/VL as carrier Vpp on the high/low envelope plateaus + modulation index."""
    tc, hi, lo = envelope(t, v, fc)
    amp = (hi - lo)
    VH = float(np.percentile(amp, 97)); VL = float(np.percentile(amp, 3))
    m = (VH - VL) / (VH + VL) * 100.0 if (VH + VL) > 0 else float('nan')
    return dict(VH=VH, VL=VL, m=m, tc=tc, amp=amp)

def spec(t, v, n=1<<17, fc=31e6):
    tt = t - t[0]; fs = n/(tt[-1]); tu = np.arange(n)/fs
    vu = np.interp(tu, tt, v); w = np.hanning(n)
    S = np.abs(np.fft.rfft(vu*w))*2/np.sum(w)
    return np.fft.rfftfreq(n, 1/fs), S

def pk(f, S, f0, span):
    m = (f > f0-span) & (f < f0+span)
    return float(S[m].max()) if m.any() else 0.0

def carrier_thd(f, S, fc=31e6):
    fund = pk(f, S, fc, 2e5)
    hs = [pk(f, S, k*fc, 2e5) for k in (2, 3, 4, 5)]
    return (float(np.sqrt(sum(h*h for h in hs))/fund*100) if fund > 0 else float('nan')), fund, hs

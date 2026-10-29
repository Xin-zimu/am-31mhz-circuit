# -*- coding: utf-8 -*-
"""C3 step 6: minimal independent-solver check with LTspice.

Scope deliberately reduced.  The question LTspice can answer cheaply is:
  (a) does an independent solver oscillate on this netlist at all, and
  (b) does it land near the ngspice trap answer once it does?

What is NOT asked of LTspice: the frequency.  A .meas crossing count over
100k+ cycles is unreliable, and the raw format in this build does not parse.
Frequency is settled by the analytic RLC reference instead.

Recorded finding: LTspice 26.0.0 with UIC and no injected disturbance does
NOT start this oscillator - v(out) stays at 6e-10 V for the full 4 ms, while
ngspice-trap from the same element list does start.  That is why a kick is
injected here.
"""
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c3lib as L

LT = r"D:\tlspice\LTspice.exe"
LTDIR = os.path.join(L.WORK, "lt")
os.makedirs(LTDIR, exist_ok=True)

KICK = "IKICK 0 xl PULSE(0 200m 10n 1n 1n 500u 1m)"


def build(name, method, tmax="0.25n", tstop="3m", t_from="2.5m", kick=True):
    L_ = ["* C3 LTspice cross-check: " + name,
          "* element list identical to c2_two_load.cir",
          L.ELEMENTS.rstrip(), "RLOADG out 0 2k", "CLOADG out 0 10p",
          L.MODEL.rstrip()]
    if kick:
        L_.append(KICK)
    L_.append(".options method=" + method + " maxord=2 reltol=1e-4 trtol=7 plotwinsize=0")
    L_.append(".tran 0 " + tstop + " 0 " + tmax + " uic")
    L_.append(".meas tran vo_pp PP v(out) FROM=" + t_from + " TO=" + tstop)
    L_.append(".meas tran ve_pp PP v(e) FROM=" + t_from + " TO=" + tstop)
    L_.append(".four 30.99meg 20 v(out)")
    L_.append(".end")
    p = os.path.join(LTDIR, name + ".cir")
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L_) + "\n")
    return p


def run(name, timeout=3600):
    cir = os.path.join(LTDIR, name + ".cir")
    log = os.path.join(LTDIR, name + ".log")
    raw = os.path.join(LTDIR, name + ".raw")
    for f in (log, raw):
        if os.path.exists(f):
            os.remove(f)
    t0 = time.monotonic()
    subprocess.run([LT, "-b", "-ascii", cir], cwd=LTDIR, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, timeout=timeout)
    dt = time.monotonic() - t0
    txt = ""
    if os.path.exists(log):
        b = open(log, "rb").read()
        for enc in ("utf-16-le", "latin-1"):
            try:
                c = b.decode(enc).replace("\x00", "").replace("\r", "")
            except Exception:
                continue
            if "vo_pp" in c or "Total elapsed" in c:
                txt = c
                break
    if os.path.exists(raw):
        os.remove(raw)
    return dt, txt


def parse(txt):
    out = {}
    for m in re.finditer(r"^\s*(\w+)\s*:\s*\w+\([^)]*\)\s*=\s*([-+0-9.eE]+)", txt, re.M):
        out.setdefault(m.group(1), float(m.group(2)))
    h = {}
    for m in re.finditer(r"^\s*(\d+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)",
                         txt, re.M):
        h[int(m.group(1))] = dict(freq=float(m.group(2)), mag=float(m.group(3)),
                                  norm=float(m.group(4)))
    return out, h


if __name__ == "__main__":
    res = []
    for nm, m, kick in (("lt3_trap_kick", "trap", True),
                        ("lt3_gear_kick", "gear", True),
                        ("lt3_trap_nokick", "trap", False)):
        build(nm, m, kick=kick)
        dt, txt = run(nm)
        meas, harm = parse(txt)
        rec = dict(name=nm, method=m, kick=kick, seconds=round(dt, 1), meas=meas, four=harm)
        res.append(rec)
        print("%-18s %6.0fs  vo_pp=%s  ve_pp=%s  h2=%.2f%%" % (
            nm, dt, meas.get("vo_pp"), meas.get("ve_pp"),
            100 * harm[2]["norm"] if 2 in harm else float("nan")), flush=True)
        if "vo_pp" not in meas:
            print(txt[-800:], flush=True)
        L.json_dump(os.path.join(L.RESDIR, "lt.json"), res)

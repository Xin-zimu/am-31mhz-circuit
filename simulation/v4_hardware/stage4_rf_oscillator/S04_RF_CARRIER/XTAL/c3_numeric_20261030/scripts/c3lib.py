# -*- coding: utf-8 -*-
"""C3 shared library: netlist builder, ngspice driver, raw reader, measurements.

C3 = 31 MHz crystal oscillator numerical consistency.
Circuit is byte-for-byte the C2 cascade; ONLY numerical options may differ
between runs (method / maxord / reltol / tmax / tstep / tstart / .ic / kick).
"""
import hashlib
import json
import os
import re
import subprocess
import time

import numpy as np

NG = r"D:\ms_xsp\s04_crosscheck_20261017\Spice64\bin\ngspice_con.exe"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = r"D:\实验报告文件夹\电路2\tmp\c3"
NETDIR = os.path.join(ROOT, "netlists")
RESDIR = os.path.join(ROOT, "results")
for _d in (WORK, NETDIR, RESDIR):
    os.makedirs(_d, exist_ok=True)

ELEMENTS = r"""VSUP vcc 0 PWL(0 0 1u 5)
* --- crystal Colpitts (unchanged from C1) ---
R1 vcc b 10k
R2 b 0 10k
Q1 vcc b e 2N3904
R3 e 0 4.7k
C1 b e 33p
C2 e 0 33p
C3 vcc 0 100n
C4 vcc 0 10u
CSTRAY b 0 1p
CX0 b 0 3.0p
VXM b xr 0
RM xr xl 30
LM xl xc 0.002637081993366925
CM xc 0 10.0f
* --- emitter follower buffer (unchanged from C1) ---
CIN e bf 1n
RBT vcc bf 10k
RBB bf 0 10k
QB vcc bf ef 2N3904
REB ef 0 330
COUTB ef bo 1n
* --- common-emitter gain stage (unchanged from C1) ---
CG bo bg 10n
RG1 vcc bg 22k
RG2 bg 0 4.7k
QG cg bg eg 2N3904
RCG vcc cg 1k
REG eg 0 56
COUTG cg out 10n
"""

MODEL = r""".model 2N3904   NPN(Is=6.734f Xti=3 Eg=1.11 Vaf=74.03 Bf=416.4 Ne=1.259
+               Ise=6.734f Ikf=66.78m Xtb=1.5 Br=.7371 Nc=2 Isc=0 Ikr=0 Rc=1
+               Cjc=3.638p Mjc=.3085 Vjc=.75 Fc=.5 Cje=4.493p Mje=.2593 Vje=.75
+               Tr=239.5n Tf=301.2p Itf=.4 Vtf=4 Xtf=2 Rb=10)
"""


def build_cascade(name, method="trap", maxord=2, reltol="1e-4", trtol=7,
                  tmax="0.25n", tstep=None, tstop="8m", tstart="0",
                  rload="2k", ic="", kick="", extra_options="", raw=None,
                  save="v(out) v(e) v(b)"):
    tstep = tstep or tmax
    raw = raw or (name + ".raw")
    L = []
    L.append("* C3 numerical-consistency run: " + name)
    L.append("* Circuit identical to c2_two_load.cir; numerical options only.")
    L.append("*   method=" + method + " maxord=" + str(maxord) + " reltol=" + reltol +
             " trtol=" + str(trtol) + " tmax=" + tmax + " tstep=" + tstep +
             " tstop=" + tstop + " tstart=" + tstart + " rload=" + rload)
    if ic:
        L.append("*   ic: " + ic.replace("\n", " / "))
    if kick:
        L.append("*   kick: " + kick.replace("\n", " / "))
    L.append(ELEMENTS.rstrip())
    L.append("RLOADG out 0 " + rload)
    L.append("CLOADG out 0 10p")
    L.append(MODEL.rstrip())
    if kick:
        L.append(kick.rstrip())
    if ic:
        L.append(ic.rstrip())
    opt = (".options method=" + method + " maxord=" + str(maxord) + " reltol=" + reltol +
           " trtol=" + str(trtol) + " temp=27 tnom=27")
    if extra_options:
        opt += " " + extra_options
    L.append(opt)
    L.append(".control")
    L.append("set filetype=binary")
    L.append("set num_threads=1")
    L.append("save " + save)
    L.append("tran " + tstep + " " + tstop + " " + tstart + " " + tmax + " uic")
    L.append("write " + raw)
    L.append("quit")
    L.append(".endc")
    L.append(".end")
    return "\n".join(L) + "\n"


def write_netlist(name, text):
    p = os.path.join(NETDIR, name + ".cir")
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return p


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1048576), b""):
            h.update(blk)
    return h.hexdigest()


class RunError(RuntimeError):
    pass


def run_ngspice(cir_path, raw_name, timeout=7200):
    raw_path = os.path.join(WORK, raw_name)
    if os.path.exists(raw_path):
        os.remove(raw_path)
    log_path = os.path.join(WORK, raw_name.replace(".raw", ".log"))
    t0 = time.monotonic()
    with open(log_path, "w", encoding="utf-8", errors="replace") as logf:
        proc = subprocess.run([NG, "-b", cir_path], cwd=WORK,
                              stdout=logf, stderr=subprocess.STDOUT, timeout=timeout)
    dt = time.monotonic() - t0
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        log = f.read().replace("\r", "")
    info = dict(cir=cir_path, log=log_path, seconds=round(dt, 1),
                exit_code=proc.returncode,
                raw=raw_path if os.path.exists(raw_path) else None)
    if proc.returncode != 0 or info["raw"] is None:
        raise RunError("ngspice failed rc=" + str(proc.returncode) + " " + cir_path + "\n" + log[-3000:])
    info["raw_bytes"] = os.path.getsize(info["raw"])
    return info

def read_raw(path):
    """Read a ngspice binary/ascii raw file into a dict of numpy arrays."""
    with open(path, "rb") as f:
        blob = f.read()
    head_end = blob.find(b"Binary:\n")
    ascii_mode = False
    if head_end < 0:
        head_end = blob.find(b"Values:\n")
        ascii_mode = True
        if head_end < 0:
            raise ValueError("unsupported raw header")
        body_start = head_end + len(b"Values:\n")
    else:
        body_start = head_end + len(b"Binary:\n")
    head = blob[:head_end].decode("latin-1").replace("\r", "")
    nvar = int(re.search(r"No\. Variables:\s+(\d+)", head).group(1))
    npt = int(re.search(r"No\. Points:\s+(\d+)", head).group(1))
    flags = re.search(r"Flags:\s*(.*)", head).group(1).lower()
    complex_mode = "complex" in flags
    names = re.findall(r"(?m)^\s*\d+\s+(\S+)\s+(?:voltage|current|time)\s*$", head)
    if len(names) != nvar:
        raise ValueError("variable count mismatch: " + str(len(names)) + " vs " + str(nvar))
    if ascii_mode:
        vals = np.array(blob[body_start:].split(), dtype=float)
        if complex_mode:
            vals = vals[0::2] + 1j * vals[1::2]
        arr = vals.reshape(npt, nvar)
        if complex_mode:
            arr = np.real(arr)
    else:
        dtype = np.complex128 if complex_mode else np.float64
        need = npt * nvar * (16 if complex_mode else 8)
        arr = np.frombuffer(blob[body_start:body_start + need], dtype=dtype)
        arr = arr.reshape(npt, nvar)
        if complex_mode:
            arr = np.real(arr)
    out = {}
    for i, nm in enumerate(names):
        out[nm] = np.ascontiguousarray(arr[:, i])
    return out


def crossings(t, v, level):
    """Linearly interpolated rising-edge crossings of level."""
    d = v - level
    idx = np.nonzero((d[:-1] < 0) & (d[1:] >= 0))[0]
    if idx.size == 0:
        return np.array([])
    t0, t1 = t[idx], t[idx + 1]
    v0, v1 = v[idx], v[idx + 1]
    return t0 + (level - v0) * (t1 - t0) / (v1 - v0)


def fit_frequency(tc):
    """Least-squares frequency (Hz) and max residual (s) from crossing times."""
    if tc.size < 3:
        return float("nan"), float("nan")
    k = np.arange(tc.size, dtype=float)
    A = np.vstack([k, np.ones_like(k)]).T
    sol, *_ = np.linalg.lstsq(A, tc, rcond=None)
    T, t_off = sol[0], sol[1]
    f = 1.0 / T
    resid = tc - (T * k + t_off)
    return f, float(np.max(np.abs(resid)))


def cycle_envelope(t, v):
    """Per-cycle Vpp and period, using mid-level rising crossings."""
    hi = np.percentile(v, 99.5)
    lo = np.percentile(v, 0.5)
    level = 0.5 * (hi + lo)
    tc = crossings(t, v, level)
    if tc.size < 4:
        return None
    idx = np.searchsorted(t, tc)
    tcs, amps, pers = [], [], []
    for i in range(tc.size - 1):
        a, b = int(idx[i]), int(idx[i + 1]) + 1
        if b - a < 8:
            continue
        seg = v[a:b]
        tcs.append(0.5 * (tc[i] + tc[i + 1]))
        amps.append(float(seg.max() - seg.min()))
        pers.append(float(tc[i + 1] - tc[i]))
    if len(amps) < 4:
        return None
    return np.array(tcs), np.array(amps), np.array(pers), tc


def settle_time(tc_env, amp_env, tol=1e-3, hold=40):
    """First cycle after which the envelope stays within tol of the final level."""
    n = amp_env.size
    if n < hold + 5:
        return float("nan"), float("nan"), float("nan")
    a_ref = float(np.median(amp_env[-max(5, n // 10):]))
    idx = n - hold
    for i in range(n - hold):
        seg = amp_env[i:i + hold]
        if np.max(np.abs(seg - a_ref)) <= tol * a_ref:
            idx = i
            break
    return float(tc_env[idx]), a_ref, float(np.max(np.abs(amp_env[idx:] - a_ref)) / a_ref)


def harmonics(t, v, f, ncyc=None):
    """Least-squares fit of harmonics 1..6 over the last whole cycles."""
    if not np.isfinite(f) or f <= 0:
        return None
    T = 1.0 / f
    t1 = float(t[-1])
    if ncyc is None:
        ncyc = max(2, int(np.floor((t1 - float(t[0])) * f)))
    t0 = t1 - ncyc * T
    m = (t >= t0) & (t <= t1)
    tt, vv = t[m], v[m]
    cols = [np.ones_like(tt)]
    for k in range(1, 7):
        cols.append(np.cos(2 * np.pi * k * f * tt))
        cols.append(np.sin(2 * np.pi * k * f * tt))
    A = np.vstack(cols).T
    coef, *_ = np.linalg.lstsq(A, vv, rcond=None)
    amps = [float(np.hypot(coef[2 * k - 1], coef[2 * k])) for k in range(1, 7)]
    resid = vv - A @ coef
    return dict(dc=float(coef[0]), amp=amps, vpp_fit=float(2 * amps[0]),
                rms_resid=float(np.sqrt(np.mean(resid ** 2))),
                window=[float(t0), float(t1)], ncyc=int(ncyc))


def measure(t, v, settle_tol=1e-3):
    """Standard measurement bundle for one node."""
    env = cycle_envelope(t, v)
    if env is None:
        return dict(ok=False, reason="no oscillation")
    tc_env, amp_env, per_env, tc_all = env
    t_set, a_ref, dev = settle_time(tc_env, amp_env, tol=settle_tol)
    t_ref = t_set if np.isfinite(t_set) else float(t[0])
    tc_use = tc_all[tc_all >= t_ref]
    if tc_use.size < 4:
        tc_use = tc_all[-min(40, tc_all.size):]
    f, maxres = fit_frequency(tc_use)
    m = t >= t_ref
    vpp = float(np.max(v[m]) - np.min(v[m]))
    h = harmonics(t, v, f)
    return dict(ok=True, f_hz=f, f_mhz=f / 1e6, vpp=vpp, vpp_cycle=a_ref,
                settle_s=t_set, env_dev_after=dev, n_cycles=int(amp_env.size),
                maxres_s=maxres, harm=h,
                t_first=float(tc_all[0]), t_last=float(tc_all[-1]),
                period_s=float(np.median(per_env)))


def amplitude_series(t, v, nbins=160):
    """Coarse envelope for growth-curve comparison."""
    edges = np.linspace(t[0], t[-1], nbins + 1)
    idx = np.searchsorted(t, edges)
    xs, ys = [], []
    for i in range(nbins):
        a, b = idx[i], max(idx[i] + 1, idx[i + 1])
        if b - a < 4:
            continue
        seg = v[a:b]
        xs.append(0.5 * (edges[i] + edges[i + 1]))
        ys.append(float(seg.max() - seg.min()))
    return np.array(xs), np.array(ys)


def growth_rate(xs, ys, lo=0.15, hi=0.75):
    """Exponential growth rate (1/s) fitted between lo and hi of the rise."""
    if xs is None or xs.size < 8:
        return float("nan")
    top = float(np.max(ys))
    m = (ys > lo * top) & (ys < hi * top)
    if m.sum() < 5:
        return float("nan")
    p = np.polyfit(xs[m], np.log(ys[m]), 1)
    return float(p[0])


def json_dump(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, default=float)


def json_load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def read_ltspice_raw(path):
    """Read an LTspice .raw (real, binary, interleaved by point).

    LTspice writes its header as UTF-16LE, so the usual ASCII search for
    "Binary:" fails.  The point count in the header is also unreliable here,
    so it is recomputed from the file size.
    """
    with open(path, "rb") as f:
        blob = f.read()
    marker = b"Binary:\n"
    marker16 = "Binary:\n".encode("utf-16-le")
    pos = blob.find(marker16)
    if pos >= 0:
        body_start = pos + len(marker16)
        head = blob[:pos].decode("utf-16-le", errors="replace").replace("\r", "")
    else:
        pos = blob.find(marker)
        if pos < 0:
            raise ValueError("only binary LTspice raw supported")
        body_start = pos + len(marker)
        head = blob[:pos].decode("latin-1").replace("\r", "")
    nvar = int(re.search(r"No\. Variables:\s+(\d+)", head).group(1))
    names = re.findall(r"(?m)^\s*(\d+)\s+(\S+)\s+(\S+)\s*$", head)
    names = [nm for i, nm, tp in names]
    if len(names) != nvar:
        raise ValueError("LTspice variable mismatch %d vs %d" % (len(names), nvar))
    npt = (len(blob) - body_start) // (nvar * 8)
    arr = np.frombuffer(blob[body_start:body_start + npt * nvar * 8], dtype=np.float64)
    arr = arr.reshape(npt, nvar)
    out = {}
    for i, nm in enumerate(names):
        key = nm.lower()
        if key == "time":
            out["time"] = np.ascontiguousarray(arr[:, i])
        elif key.startswith("v("):
            out["v(" + key[2:-1] + ")"] = np.ascontiguousarray(arr[:, i])
        else:
            out[key] = np.ascontiguousarray(arr[:, i])
    return out

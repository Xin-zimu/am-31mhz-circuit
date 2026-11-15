# -*- coding: utf-8 -*-
"""LTspice .raw reader: real (tran/dc) and complex (ac); honours the Offset: header."""
import numpy as np, re, os, subprocess
LT = r"D:\tlspice\LTspice.exe"

def load_raw(path):
    raw = open(path, "rb").read()
    enc = "utf-16-le" if (len(raw) > 1 and raw[1:2] == b"\x00") else "latin-1"
    ib = raw.find("Binary:".encode(enc)); iv = raw.find("Values:".encode(enc))
    if ib != -1 and (iv == -1 or ib < iv):
        binary = True;  start = ib + len("Binary:".encode(enc))
    elif iv != -1:
        binary = False; start = iv + len("Values:".encode(enc))
    else:
        raise ValueError("no Values:/Binary: marker")
    nl = "\n".encode(enc)
    while raw[start:start+len(nl)] == nl: start += len(nl)
    body = raw[start:]
    txt = raw[:start].decode(enc, "replace").lstrip("\ufeff")
    nvars = int(re.search(r"No\. Variables:\s*(\d+)", txt).group(1))
    npts  = int(re.search(r"No\. Points:\s*(\d+)", txt).group(1))
    moff  = re.search(r"Offset:\s*([-+0-9.eE]+)", txt)
    offset = float(moff.group(1)) if moff else 0.0
    flags = txt.split("Flags:")[1].split("\n")[0].lower() if "Flags:" in txt else ""
    complex_ = "complex" in flags
    names = []
    for ln in txt.split("Variables:", 1)[1].splitlines():
        ln = ln.strip()
        if not ln or ln.startswith(("Values:", "Binary:")): continue
        p = ln.split()
        if len(p) >= 2 and re.fullmatch(r"-?\d+", p[0]): names.append(p[1])
    assert len(names) == nvars, (len(names), nvars)
    if binary:
        need = nvars * npts * (16 if complex_ else 8)
        if complex_:
            a = np.frombuffer(body[:need], dtype="<f8").reshape(npts, nvars, 2)
            d = {nm: (a[:, i, 0] + 1j*a[:, i, 1]).copy() for i, nm in enumerate(names)}
        else:
            a = np.frombuffer(body[:need], dtype="<f8").reshape(npts, nvars).T.copy()
            d = {nm: a[i].copy() for i, nm in enumerate(names)}
    else:
        rows, cur = [], []
        def conv(s):
            if "," in s:
                x, y = s.split(","); return complex(float(x), float(y))
            return complex(float(s), 0.0) if complex_ else float(s)
        for ln in body.decode(enc, "replace").replace("\r", "").splitlines():
            if not ln.strip(): continue
            if ln.startswith("\t"):
                cur.append(conv(ln.strip()))
                if len(cur) == nvars: rows.append(cur); cur = []
            else:
                p = ln.split(); cur = [conv(v) for v in p[1:] if v.strip()]
                if len(cur) == nvars: rows.append(cur); cur = []
        assert len(rows) == npts, (len(rows), npts)
        a = np.array(rows)
        d = {nm: a[:, i].copy() for i, nm in enumerate(names)}
    # LTspice writes the time axis RELATIVE to Offset: in ASCII files
    tk = None
    for k in d:
        if k.lower() == "time": tk = k
    if tk is not None and offset:
        d[tk] = d[tk] + offset
    d["_offset"] = offset
    return d

def get(r, *cands):
    for c in cands:
        for k in r:
            if k.lower() == c.lower(): return r[k]
    raise KeyError(cands)

def run(netpath, ascii=False, timeout=3600):
    args = [LT, "-b"] + (["-ascii"] if ascii else []) + [netpath]
    return subprocess.run(args, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)

def log(netpath):
    p = os.path.splitext(netpath)[0] + ".log"
    return open(p, encoding="utf-8", errors="replace").read() if os.path.exists(p) else ""

def run_and_load(netpath, ascii=False, timeout=3600, expect_ok=True):
    r = run(netpath, ascii=ascii, timeout=timeout)
    rawp = os.path.splitext(netpath)[0] + ".raw"
    lg = log(netpath)
    ok = (r.returncode == 0) and os.path.exists(rawp) and os.path.getsize(rawp) > 0
    if expect_ok and not ok:
        raise RuntimeError("LTspice failed rc=%s\n%s\n%s" % (r.returncode, r.stderr[-1500:], lg[-1500:]))
    return (load_raw(rawp) if ok else None), lg, r.returncode

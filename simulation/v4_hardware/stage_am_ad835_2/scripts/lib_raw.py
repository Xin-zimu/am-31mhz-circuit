# -*- coding: utf-8 -*-
"""LTspice .raw reader (ASCII and binary) + helpers."""
import numpy as np, struct, os, re

def load_raw(path):
    with open(path, "rb") as f:
        head = b""
        while True:
            line = f.readline()
            if not line: raise ValueError("no header end")
            head += line
            if line.strip() == b"Binary:" or line.strip() == b"Values:":
                break
        txt = head.decode("latin-1")
        binary = txt.rstrip().endswith("Binary:")
        blocks = {}
        cur = None
        for ln in txt.splitlines():
            if ln.startswith("Plotname:"):
                cur = ln.split(":",1)[1].strip(); blocks[cur] = {"vars":[], "data":None, "binary":None, "npoints":0}
            elif ln.startswith("No. Variables:"):
                blocks[cur]["nvars"] = int(ln.split(":")[1])
            elif ln.startswith("No. Points:"):
                blocks[cur]["npoints"] = int(ln.split(":")[1])
            elif ln.startswith("Flags:"):
                blocks[cur]["flags"] = ln.split(":",1)[1].strip()
            elif ln.startswith("\t") and blocks:
                p = ln.strip().split("\t")
                if len(p) >= 2 and re.fullmatch(r"-?\d+", p[0] or ""):
                    blocks[cur]["vars"].append(p[1])
        if binary:
            body = f.read()
            for name, b in blocks.items():
                nv, npnt = b["nvars"], b["npoints"]
                vals = np.frombuffer(body[:nv*npnt*8], dtype="<f8").reshape(npnt, nv).T.copy()
                b["data"] = {v: vals[i] for i, v in enumerate(b["vars"])}
                body = body[nv*npnt*8:]
            return list(blocks.values())[-1]["data"] if len(blocks)==1 else {k:v["data"] for k,v in blocks.items()}
        else:
            nums = np.array(f.read().decode("latin-1").replace("\r","").split(), dtype=float)
            for name, b in blocks.items():
                nv, npnt = b["nvars"], b["npoints"]
                vals = nums[:nv*npnt].reshape(npnt, nv).T.copy()
                b["data"] = {v: vals[i] for i, v in enumerate(b["vars"])}
                nums = nums[nv*npnt:]
            return list(blocks.values())[-1]["data"] if len(blocks)==1 else {k:v["data"] for k,v in blocks.items()}

def run_ltspice(netpath, ascii=True, timeout=1200):
    import subprocess
    args = [r"D:\tlspice\LTspice.exe", "-b"]
    if ascii: args.append("-ascii")
    args.append(netpath)
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    return r

def log_text(netpath):
    base = os.path.splitext(netpath)[0]
    for ext in (".log",):
        p = base + ext
        if os.path.exists(p): return open(p, encoding="utf-8", errors="replace").read()
    return ""

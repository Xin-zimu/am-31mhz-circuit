# -*- coding: utf-8 -*-
"""Mechanical translator: Multisim-exported .cir -> LTspice-runnable .net.
ONLY these edits, nothing else:
  1. drop '.model vresXXX r( )' placeholder lines (Multisim pot models)
  2. strip trailing ' vresXXX' token from R lines
  3. drop '+ distof1 0 0' / '+ distof2 0 0' continuation lines
Everything else is preserved byte-for-byte.
"""
import re, hashlib, os, sys

def translate(src_text):
    out = []
    removed = {"vres_model":0, "vres_token":0, "disto":0}
    for ln in src_text.splitlines():
        s = ln.rstrip()
        if re.match(r"^\s*\.model\s+vres\w+\s+r\s*\(\s*\)\s*$", s, re.I):
            removed["vres_model"] += 1; continue
        if re.match(r"^\s*\+\s*distof[12]\s+0\s+0\s*$", s, re.I):
            removed["disto"] += 1; continue
        m = re.match(r"^(\s*r\S+\s+\S+\s+\S+\s+\S+)\s+vres\w+\s*$", s, re.I)
        if m:
            out.append(m.group(1)); removed["vres_token"] += 1; continue
        out.append(ln)
    return "\n".join(out), removed

if __name__ == "__main__":
    src = r"D:\实验报告文件夹\电路2\simulation\v4_hardware\repair_20261011\final_actual.cir"
    dst = r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2\netlists\frozen_poly.net"
    t = open(src, encoding="utf-8", errors="replace").read()
    new, rem = translate(t)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w", encoding="ascii", errors="replace") as f:
        f.write(new + "\n")
    print("source sha256:", hashlib.sha256(t.encode("utf-8", "replace")).hexdigest())
    print("edits:", rem)
    print("lines in/out:", len(t.splitlines()), len(new.splitlines()))

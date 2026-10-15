#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S04-01 接口参数提取器（只读）

用途：从 S03 冻结的实际网表中，自动提取 S04 第一级（31 MHz 振荡器 + 缓冲级）
      必须满足的接口参数，避免手抄进文档时引入错误。

纪律：
  - 只读，不修改任何文件。
  - 提取结果须与 S04_01_接口要求规格书.md 人工核对；本脚本不替代工程判断。
  - POLY(3) 系数**只报告位次与数值，不断言物理含义**（映射见规格书 §2.1 与待办 V-1）。

用法：
  python extract_interface.py
"""
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
NETLIST = os.path.normpath(os.path.join(
    HERE, "..", "repair_20261011", "final_actual.cir"))
EXPECTED_SHA256 = "D9ABA8EFF74E679F709BC6A680BF569E6DAB87A00303B6FF138F19D4964CCAAF"


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def main():
    if not os.path.exists(NETLIST):
        print("ERROR: netlist not found: %s" % NETLIST)
        return 1

    actual = sha256_of(NETLIST)
    print("netlist      : %s" % NETLIST)
    print("sha256       : %s" % actual)
    print("sha256 match : %s" % ("OK" if actual == EXPECTED_SHA256 else "*** MISMATCH ***"))
    print()

    with open(NETLIST, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()
    lines = raw.splitlines()

    # ---- extract the transmit-path elements of interest ------------------
    wanted = re.compile(
        r"^(vVCARRIER|rRFIX|rRVRF|xEAM_-EAM|eEPA|eECHANNEL|eERX|rRRF|"
        r"vVCC|vV5|vVREF|rRLOAD)\s", re.IGNORECASE)

    found = {}
    for i, ln in enumerate(lines, 1):
        s = ln.strip()
        if not s or s.startswith("*"):
            # keep continuation lines attached (they start with '+')
            pass
        if wanted.match(s):
            found[s.split()[0].lower()] = (i, s)

    print("=== transmit-path elements ===")
    for k in sorted(found):
        i, s = found[k]
        print("L%-5d %s" % (i, s))

    # ---- VCARRIER sine parameters ---------------------------------------
    print()
    print("=== VCARRIER sine() parameters ===")
    vc_line_no = None
    for i, ln in enumerate(lines, 1):
        if re.match(r"^vVCARRIER\s", ln.strip(), re.IGNORECASE):
            vc_line_no = i
            break
    sine = None
    if vc_line_no is not None:
        # sine may be on a continuation line ('+ ...')
        block = []
        for j in range(vc_line_no - 1, min(vc_line_no + 6, len(lines))):
            block.append(lines[j])
            if "sin(" in lines[j].lower():
                break
        joined = " ".join(block)
        m = re.search(r"sin\(([^)]*)\)", joined, re.IGNORECASE)
        if m:
            # Multisim writes sine() args space-separated; other writers use commas.
            inner = m.group(1).replace(",", " ")
            parts = [p.strip() for p in inner.split() if p.strip()]
            sine = parts
            labels = ["VOFF (dc offset, V)", "VAMPL (peak amplitude, V)",
                      "FREQ (Hz)", "TD (delay, s)", "THETA (damping, 1/s)",
                      "PHASE (deg)"]
            for idx, val in enumerate(parts):
                lab = labels[idx] if idx < len(labels) else "extra[%d]" % idx
                print("  %-28s = %s" % (lab, val))
        else:
            print("  *** sine() spec not found on/after line %d ***" % vc_line_no)

    # ---- POLY(3) coefficient positions (position only) -------------------
    print()
    print("=== EAM POLY(3) coefficients (position reported, meaning NOT asserted) ===")
    for i, ln in enumerate(lines, 1):
        if ln.strip().upper().startswith("E1 ") and "POLY(3)" in ln.upper():
            toks = ln.split()
            pi = [t.upper() for t in toks].index("POLY(3)")
            # after "POLY(3)" come exactly 3 node-pair tokens "(n1,n2)" "(n3,n4)" "(n5,n6)"
            n_pairs = 3
            coefs = toks[pi + 1 + n_pairs:]
            print("  line %d: %s" % (i, ln.strip()))
            print("  coefficient count = %d" % len(coefs))
            for n, c in enumerate(coefs, 1):
                if c.strip() not in ("0", "0.0"):
                    print("    position %-3d value %s   <== NON-ZERO" % (n, c))
            break

    # ---- TP2 loading (what the oscillator must drive) --------------------
    print()
    print("=== TP2 load seen by the new oscillator ===")
    in_poly = False
    for i, ln in enumerate(lines, 1):
        s = ln.strip()
        if s.upper().startswith(".SUBCKT POLYSOURCE"):
            in_poly = True
            print("  %s" % s)
            continue
        if in_poly and s.upper().startswith(".ENDS"):
            break
        if in_poly and s:
            print("  %s" % s)

    # ---- supplies -------------------------------------------------------
    print()
    print("=== supply rails present ===")
    for i, ln in enumerate(lines, 1):
        s = ln.strip()
        if re.match(r"^v(VCC|V5|VREF)\s", s, re.IGNORECASE):
            print("  L%-5d %s" % (i, s))

    print()
    print("NOTE: this script reports netlist facts only.")
    print("      S04 requirements derived from them live in S04_01_接口要求规格书.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

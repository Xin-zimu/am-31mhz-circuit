# -*- coding: utf-8 -*-
"""Build AD835_Behav.sub : .subckt wrapper of AD835_Behav_Model.asc.
Equations are copied VERBATIM from LTspice's own netlist of the .asc.
Port order is forced to the datasheet / ad835.asy order so one symbol fits both models:
   1 X1  2 X2  3 Y1  4 Y2  5 VN  6 Z  7 W  8 VP
The .asc itself is never modified.
"""
import re, os, sys
sys.stdout.reconfigure(encoding="utf-8")
STAGE = r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
SRC   = os.path.join(STAGE, "ltspice_netlist", "AD835_Behav_Model.net")
OUT   = os.path.join(STAGE, "adapted", "AD835_Behav.sub")

raw = open(SRC, encoding="latin-1").read().splitlines()
body, params, models, libs = [], [], [], []
for ln in raw:
    s = ln.strip()
    if not s or s.startswith("*"): continue
    if s.startswith("."):
        low = s.lower()
        if low.startswith(".param"): params.append(s)
        elif low.startswith(".model"): models.append(s)
        elif low.startswith(".lib"):   libs.append(s)
        continue
    body.append(s)

DROP = {"V1","V2","V3","V4","V5"}          # .asc testbench sources -> ports
kept = [s for s in body if s.split()[0] not in DROP]

PORTS = ["X1","X2","Y1","Y2","Z","W","VPOS","VNEG"]
INTERNAL = set()
for s in kept:
    t = s.split()
    if len(t) >= 3:
        for n in t[1:3]:
            if n != "0" and n not in PORTS: INTERNAL.add(n)

def ren(n): return n if (n == "0" or n in PORTS) else "i" + n

SUBORDER = ["X1","X2","Y1","Y2","VNEG","Z","W","VPOS"]   # datasheet 1..8

out = [
"* AD835 behavioral model -- ADAPTER (.subckt wrapper of a SCHEMATIC)",
"* Original schematic (unmodified): AD835_Behav_Model.asc",
"*   GLuisF/LTspice  examples/LtSpicePlus/Multiplicadores/ad835",
"*   author marker in the .asc: 'Oct-05/G.Mi'",
"*",
"* The device equations below are copied VERBATIM from LTspice's own netlist",
"* of that .asc; only the .asc's own 5 test-bench sources were removed and",
"* the internal node names prefixed so they stay local to this subcircuit.",
"*",
"* Port order = AD835 datasheet pin order 1..8, identical to ad835.asy SpiceOrder:",
"*   1 X1  2 X2  3 Y1  4 Y2  5 VN(=VNEG)  6 Z  7 W  8 VP(=VPOS)",
"*",
"* THIS IS NOT AN ANALOG DEVICES MODEL and carries no ADI warranty.",
".SUBCKT AD835_BEHAV X1 X2 Y1 Y2 VNEG Z W VPOS",
]
out += params
out.append("* ---------- device equations (verbatim) ----------")
for s in kept:
    t = s.split()
    t = [t[0], ren(t[1]), ren(t[2])] + t[3:]
    line = " ".join(t)
    for a, b in (("V(dcx)","V(idcx)"),("V(dcy)","V(idcy)"),("V(z)","V(Z)"),
                 ("V(w)","V(W)"),("V(11)","V(i11)"),("V(10)","V(i10)")):
        line = line.replace(a, b)
    out.append(line)
out += models
out += libs
out.append(".ENDS AD835_BEHAV")

os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w", encoding="ascii").write("\n".join(out) + "\n")
print("wrote", OUT, len(out), "lines")
print("internal nodes:", sorted(INTERNAL))

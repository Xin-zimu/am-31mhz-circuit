# -*- coding: utf-8 -*-
import os, sys, subprocess, shutil
sys.stdout.reconfigure(encoding="utf-8")
STAGE = r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
NG = r"D:\ms_xsp\s04_crosscheck_20261017\Spice64\bin\ngspice_con.exe"
for d in ("netlists","results","adapted","scripts"):
    os.makedirs(os.path.join(STAGE,d), exist_ok=True)

net = r"""* Model A (ad835.sub) DC transfer: W vs X, Y=1V, Z=0
.include ../models/third_party_GLuisF/ad835.sub
VX  x1 0 dc 0
VX2 x2 0 dc 0
VY  y1 0 dc 1
VY2 y2 0 dc 0
VZ  z  0 dc 0
VN  vn 0 dc -5
VP  vp 0 dc 5
XU  x1 x2 y1 y2 vn z w vp AD835
RL  w  0 150
.control
dc VX -1.5 1.5 0.01
wrdata ../results/A_dc_x.txt v(w) v(x1) i(VX)
.endc
.end
"""
p = os.path.join(STAGE,"netlists","A_dc_x.cir")
open(p,"w",encoding="ascii").write(net)
r = subprocess.run([NG,"-b",p], capture_output=True, text=True, encoding="utf-8", errors="replace")
print("rc",r.returncode)
print(r.stdout[-2500:])
print("ERR:", r.stderr[-2000:])

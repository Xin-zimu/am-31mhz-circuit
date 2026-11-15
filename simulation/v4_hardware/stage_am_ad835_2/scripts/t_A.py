# -*- coding: utf-8 -*-
import os, sys, subprocess
sys.stdout.reconfigure(encoding="utf-8")
STAGE = r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
LT = r"D:\tlspice\LTspice.exe"
d = os.path.join(STAGE,"bench"); os.makedirs(d, exist_ok=True)

net = r"""* Model A DC transfer
.include ../models/third_party_GLuisF/ad835.sub
VX1 x1 0 0
VX2 x2 0 0
VY1 y1 0 1
VY2 y2 0 0
VZ  z  0 0
VNN vn 0 -5
VPP vp 0 5
XU  x1 x2 y1 y2 vn z w vp AD835
RL  w  0 150
.dc VX1 -1.5 1.5 0.01
.options plotwinsize=0
.end
"""
p=os.path.join(d,"A_dc.asc.net")
open(p,"w",encoding="ascii").write(net)
r=subprocess.run([LT,"-b","-ascii",p],capture_output=True,text=True,encoding="utf-8",errors="replace")
print("rc",r.returncode)
print(r.stdout[-3000:])
print("ERR",r.stderr[-2000:])
for f in os.listdir(d):
    print(f, os.path.getsize(os.path.join(d,f)))

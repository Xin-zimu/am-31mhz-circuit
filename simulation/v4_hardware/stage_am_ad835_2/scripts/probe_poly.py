# -*- coding: utf-8 -*-
import os, sys, subprocess, time
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
LT=r"D:\tlspice\LTspice.exe"
d=os.path.join(STAGE,"bench"); os.makedirs(d,exist_ok=True)

net = r"""* Minimal POLY(3) reproduction of frozen TP3 = Vc*(0.6+0.1*Vm)
* Vc on node TP2 (frozen: sin(0 1 31e6)), Vm on node V1
VCAR TP2 0 sin(0 1 31meg)
VM   V1  0 pulse(0.0748175 4.0748175 1u 1n 1n 4.997u 50u)
XAM  TP2 0 V1 0 NO5 NO6 TP3 0 POLYSRC
.SUBCKT POLYSRC 1 2 3 4 5 6 7 8
E1 7 8 POLY(3) (1,2) (3,4) (5,6) 0 0.6 0 0 0 0.1 0 0 0 0 0 0 0 0 0
R0 1 2 1e15
R1 3 4 1e15
R2 5 6 1e15
R3 5 0 1e15
R4 3 0 1e15
R5 1 0 1e15
.ENDS
.options plotwinsize=0
.tran 0 200u 190u 20n
.end
"""
p=os.path.join(d,"poly_probe.net")
open(p,"w",encoding="ascii").write(net)
t0=time.time()
r=subprocess.run([LT,"-b","-ascii",p],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=600)
print("rc",r.returncode,"%.1fs"%(time.time()-t0))
print("ERR",r.stderr[-1500:])
lg=os.path.join(d,"poly_probe.log")
if os.path.exists(lg): print(open(lg,encoding="utf-8",errors="replace").read()[-1200:])
print("raw size", os.path.getsize(os.path.join(d,"poly_probe.raw")) if os.path.exists(os.path.join(d,"poly_probe.raw")) else "none")

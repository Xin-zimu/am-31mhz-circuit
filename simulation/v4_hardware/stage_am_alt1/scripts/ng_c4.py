# -*- coding: utf-8 -*-
"""Run the frozen C4 oscillator in ngspice (the solver the project validated)."""
import os, sys, subprocess, time, numpy as np
sys.stdout.reconfigure(encoding="utf-8")
ST=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NG=r"D:\ms_xsp\s04_crosscheck_20261017\Spice64\bin\ngspice_con.exe"
print("ngspice:", os.path.exists(NG))
B=os.path.join(ST,"bench","ng"); os.makedirs(B,exist_ok=True)
body=open(os.path.join(ST,"sources","C4_original.cir"),encoding="utf-8",errors="replace").read().split(".control")[0]
net=body+"""
.control
set filetype=ascii
tran 0.25n 2m 1.9m 0.125n uic
write c4.raw v(out) v(e) v(cg)
quit
.endc
.end
"""
p=os.path.join(B,"c4.cir")
open(p,"w",encoding="ascii",errors="replace").write(net)
t0=time.time()
r=subprocess.run([NG,"-b",p],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=1800,cwd=B)
print("rc",r.returncode,"%.0fs"%(time.time()-t0))
print(r.stdout[-1500:])
print("ERR", r.stderr[-800:])
for f in os.listdir(B):
    print(" ",f,os.path.getsize(os.path.join(B,f)))

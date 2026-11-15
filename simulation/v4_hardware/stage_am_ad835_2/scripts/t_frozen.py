# -*- coding: utf-8 -*-
import os, sys, subprocess
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
SRC=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\repair_20261011\final_actual.cir"
d=os.path.join(STAGE,"bench"); os.makedirs(d,exist_ok=True)
txt=open(SRC,encoding="utf-8",errors="replace").read()
net=os.path.join(d,"frozen_orig.net")
open(net,"w",encoding="ascii",errors="replace").write(txt+"\n.tran 0 200u 190u 20n uic\n.options plotwinsize=0\n.end\n")
r=subprocess.run([r"D:\tlspice\LTspice.exe","-b",net],capture_output=True,text=True,encoding="utf-8",errors="replace")
print("rc",r.returncode); print(r.stdout[-2500:]); print("ERR",r.stderr[-2000:])
print(open(net.replace(".net",".log"),encoding="utf-8",errors="replace").read()[-2500:])

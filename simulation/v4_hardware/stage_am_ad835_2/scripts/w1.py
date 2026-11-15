# -*- coding: utf-8 -*-
import os, sys, time, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from ltraw import run, log
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
B=os.path.join(STAGE,"bench","mod6")
base=open(os.path.join(B,"adB_U105.net"),encoding="utf-8").read()
body=base.split(".options plotwinsize=0")[0]
for name,an in {"w1":".tran 0 400u 300u 2n uic"}.items():
    p=os.path.join(B,name+".net")
    open(p,"w",encoding="utf-8").write(body+".options plotwinsize=0\n"+an+"\n.end\n")
    t0=time.time(); r=run(p,ascii=False,timeout=300); dt=time.time()-t0
    print("%-6s rc=%d %.1fs  raw=%s"%(name,r.returncode,dt,
        os.path.getsize(os.path.join(B,name+".raw")) if os.path.exists(os.path.join(B,name+".raw")) else "none"))
    if r.returncode: print(log(p)[-600:])

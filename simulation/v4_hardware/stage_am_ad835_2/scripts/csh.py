# -*- coding: utf-8 -*-
import os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from ltraw import run, log
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
B=os.path.join(STAGE,"bench","mod6")
base=open(os.path.join(B,"adB_U105.net"),encoding="utf-8").read()
body=base.split(".options plotwinsize=0")[0]
tests={
 "c1":".options cshunt=1p\n.tran 0 120u 70u 2n uic",
 "c2":".options cshunt=10p\n.tran 0 120u 70u 2n uic",
 "c3":".options cshunt=100p\n.tran 0 120u 70u 2n uic",
 "c4":".options cshunt=1p reltol=1e-3\n.tran 0 120u 70u 2n uic",
}
for name,an in tests.items():
    p=os.path.join(B,name+".net")
    open(p,"w",encoding="utf-8").write(body+".options plotwinsize=0\n"+an+"\n.end\n")
    t0=time.time(); r=run(p,ascii=False,timeout=110); dt=time.time()-t0
    sz=os.path.getsize(os.path.join(B,name+".raw")) if os.path.exists(os.path.join(B,name+".raw")) else 0
    print("%-4s rc=%d %5.1fs raw=%d"%(name,r.returncode,dt,sz))

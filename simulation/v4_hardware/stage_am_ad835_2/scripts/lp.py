# -*- coding: utf-8 -*-
"""L50p10 with a window covering >=1 modulation period (50 us)."""
import os, sys, json, time, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from ltraw import run, log, load_raw
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
B=os.path.join(STAGE,"bench","mod14b")
base=open(os.path.join(B,"L50p10.net"),encoding="utf-8").read()
body=base.split(".options plotwinsize=0")[0]
for tag,tran,opts in (("LP_a",".tran 0 70u 60u 0.1n uic",""),
                      ("LP_b",".tran 0 70u 60u 0.2n uic",".options method=gear")):
    p=os.path.join(B,tag+".net")
    open(p,"w",encoding="utf-8").write(body+".options plotwinsize=0\n"+opts+"\n"
        ".save V(tp3) V(v1) I(RLOAD)\n"+tran+"\n.end\n")
    t0=time.time()
    try: r=run(p,ascii=True,timeout=1200)
    except Exception:
        print("%-5s TIMEOUT"%tag,flush=True); continue
    sz=os.path.getsize(os.path.join(B,tag+".raw")) if os.path.exists(os.path.join(B,tag+".raw")) else 0
    print("%-5s rc=%d %5.0fs raw=%d"%(tag,r.returncode,time.time()-t0,sz),flush=True)

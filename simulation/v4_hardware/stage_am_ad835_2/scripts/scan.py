# -*- coding: utf-8 -*-
import os, sys, re, time
sys.path.insert(0, os.path.dirname(__file__))
from ltraw import run, log
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
NET=os.path.join(STAGE,"netlists","frozen_poly.net")
B=os.path.join(STAGE,"bench","scan"); os.makedirs(B,exist_ok=True)
RAW=open(NET,encoding="latin-1").read()
RAW=re.sub(r"^\.tran.*$","",RAW,flags=re.M)
RAW=re.sub(r"^\.options plotwinsize.*$","",RAW,flags=re.M)
RAW=re.sub(r"^\.end\s*$","",RAW,flags=re.M)
for tag,tran in {"s2n":" .tran 0 400u 300u 2n uic",
                 "s4n":".tran 0 300u 200u 4n uic",
                 "s1n":".tran 0 200u 150u 1n uic",
                 "s10n":".tran 0 300u 200u 10n uic"}.items():
    p=os.path.join(B,tag+".net")
    open(p,"w",encoding="utf-8").write(RAW+"\n.options plotwinsize=0\n"+tran+"\n.end\n")
    t0=time.time()
    try: r=run(p,ascii=True,timeout=240)
    except Exception:
        print("%-6s TIMEOUT"%tag,flush=True); continue
    sz=os.path.getsize(os.path.join(B,tag+".raw")) if os.path.exists(os.path.join(B,tag+".raw")) else 0
    print("%-6s rc=%d %5.0fs size=%d"%(tag,r.returncode,time.time()-t0,sz),flush=True)

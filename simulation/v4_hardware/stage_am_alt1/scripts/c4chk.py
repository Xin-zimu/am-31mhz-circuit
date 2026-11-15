# -*- coding: utf-8 -*-
"""Does the frozen C4 oscillator start in LTspice at all? Try several tmax/tstop."""
import os, sys, time, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from ltraw import run, log, load_raw
sys.stdout.reconfigure(encoding="utf-8")
ST=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
body=open(os.path.join(ST,"sources","C4_original.cir"),encoding="utf-8",errors="replace").read().split(".control")[0]
B=os.path.join(ST,"bench","c4chk"); os.makedirs(B,exist_ok=True)
def go(name,tran,to=600):
    p=os.path.join(B,name+".net")
    open(p,"w",encoding="utf-8").write(body+"\n.options plotwinsize=0\n.save V(out) V(e) V(cg)\n"+tran+"\n.end\n")
    t0=time.time()
    try: r=run(p,ascii=True,timeout=to)
    except Exception: print("%-10s TIMEOUT"%name,flush=True); return
    rp=os.path.join(B,name+".raw"); sz=os.path.getsize(rp) if os.path.exists(rp) else 0
    if r.returncode!=0 or sz==0:
        print("%-10s FAIL %.0fs"%(name,time.time()-t0),flush=True); return
    R=load_raw(rp); t=R["time"]; v=R["V(out)"]
    T=200/31e6; m=t>=t[-1]-T
    print("%-10s %.0fs  span=%.0f-%.0fus  TP2pp=%.4f  V(e)dc=%.3f"%(
        name,time.time()-t0,t[0]*1e6,t[-1]*1e6,v[m].max()-v[m].min(),R["V(e)"].mean()),flush=True)
go("orig","..tran 0.25n 5m 3m 0.125n uic".replace("..","."))
go("t1n"," .tran 0 5m 3m 1n uic")
go("t2n"," .tran 0 5m 3m 2n uic")

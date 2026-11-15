# -*- coding: utf-8 -*-
"""ALT-1 step 1: characterise the real 31 MHz carrier source at TP2 ('out')."""
import os, sys, json, time, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from ltraw import run, log, load_raw
sys.stdout.reconfigure(encoding="utf-8")
ST=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC=os.path.join(ST,"sources","C4_original.cir")
B=os.path.join(ST,"bench","c4src"); os.makedirs(B,exist_ok=True)
body=open(SRC,encoding="utf-8",errors="replace").read().split(".control")[0]
body=body.replace("RLOADG out 0 2k","RLOADG out 0 __RL__").replace("CLOADG out 0 10p","CLOADG out 0 __CL__p")
def build(name, rl, clp):
    t=body.replace("__RL__","%g"%rl).replace("__CL__","%g"%clp)
    p=os.path.join(B,name+".net")
    open(p,"w",encoding="utf-8").write(t+"\n.options plotwinsize=0\n.save V(out) V(e) V(cg)\n"
        ".tran 0 2m 1.9m 0.25n uic\n.end\n")
    return p
def meas(R):
    t=R["time"]; v=R["V(out)"]; T=200/31e6
    m=t>=t[-1]-T
    return float(v[m].max()-v[m].min()), float(v[m].min()), float(v[m].max())
if __name__=="__main__":
    rows=[]
    for rl,clp in [(500,4),(1000,4),(2000,4),(2000,10),(3300,4),(10000,4),(37500,4),(100000,4)]:
        nm="L_%d_%g"%(rl,clp); p=build(nm,rl,clp); t0=time.time()
        try: r=run(p,ascii=True,timeout=1500)
        except Exception:
            print("RL=%7g CL=%4.1fp TIMEOUT"%(rl,clp),flush=True); continue
        rp=os.path.join(B,nm+".raw")
        sz=os.path.getsize(rp) if os.path.exists(rp) else 0
        if r.returncode!=0 or sz==0:
            print("RL=%7g CL=%4.1fp FAIL"%(rl,clp),flush=True); continue
        R=load_raw(rp); vpp,vmin,vmax=meas(R)
        rows.append(dict(rl=rl,clp=clp,vpp=vpp,vmin=vmin,vmax=vmax))
        print("RL=%7g CL=%4.1fp  TP2 = %.4f Vpp  (%.4f..%.4f)  %.0fs"%(rl,clp,vpp,vmin,vmax,time.time()-t0),flush=True)
    json.dump(rows,open(os.path.join(ST,"results","c4_load_sweep.json"),"w"),indent=1)
    print("saved",flush=True)

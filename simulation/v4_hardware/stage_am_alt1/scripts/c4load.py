# -*- coding: utf-8 -*-
"""ALT-1 step 3: C4 carrier load sweep (real oscillator, ngspice)."""
import os, sys, json, time, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib1 import run_ng, ST
sys.stdout.reconfigure(encoding="utf-8")
B=os.path.join(ST,"bench","c4load"); os.makedirs(B,exist_ok=True)
body=open(os.path.join(ST,"sources","C4_original.cir"),encoding="utf-8",errors="replace").read().split(".control")[0]
body=body.replace("RLOADG out 0 2k","RLOADG out 0 __RL__").replace("CLOADG out 0 10p","CLOADG out 0 __CL__p")
rows=[]
for rl,clp in [(2000,10),(1000,4),(2000,4),(3300,4),(5100,4),(10000,4)]:
    nm="L%g_%gp"%(rl,clp)
    net=body.replace("__RL__","%g"%rl).replace("__CL__","%g"%clp)
    p=os.path.join(B,nm+".cir"); open(p,"w",encoding="latin-1").write(net)
    t0=time.time()
    try:
        R,r,ok=run_ng(p,nm+".raw",B,timeout=900,extra="tran 0.25n 2m 1.9m 0.125n uic\n")
    except Exception as e:
        print(nm,"TIMEOUT",flush=True); continue
    if not ok: print(nm,"FAIL",flush=True); continue
    t=R["time"]; v=R["v(out)"]; T=200/31e6; m=t>=t[-1]-T
    vpp=float(v[m].max()-v[m].min())
    rows.append(dict(rl=rl,clp=clp,vpp=vpp,vmin=float(v[m].min()),vmax=float(v[m].max())))
    print("%-10s RL=%6g CL=%3gp  TP2=%.4f Vpp  (%.4f..%.4f)  %.0fs"%(nm,rl,clp,vpp,v[m].min(),v[m].max(),time.time()-t0),flush=True)
json.dump(rows,open(os.path.join(ST,"results","c4_load_sweep.json"),"w"),indent=1)
print("DONE",flush=True)

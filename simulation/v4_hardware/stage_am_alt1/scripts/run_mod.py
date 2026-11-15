# -*- coding: utf-8 -*-
"""ALT-1 step 5: run one modulator candidate and characterise it."""
import os, sys, json, time, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib1 import run_ng, am_metrics, spec, pk, carrier_thd, ST
sys.stdout.reconfigure(encoding="utf-8")

def go(name, tstop="1.2m", tstart="0.9m", tmax="0.5n", to=2400):
    B=os.path.join(ST,"bench",name); os.makedirs(B,exist_ok=True)
    src=os.path.join(ST,"netlists",name+".cir")
    net=open(src,encoding="latin-1").read()
    p=os.path.join(B,name+".cir"); open(p,"w",encoding="latin-1").write(net)
    t0=time.time()
    R,r,ok=run_ng(p,name+".raw",B,timeout=to,
                  extra="tran %s %s %s %s uic\n"%(tmax,tstop,tstart,tmax))
    print("%-14s %s %.0fs"%(name,"ok" if ok else "FAIL",time.time()-t0),flush=True)
    if not ok:
        print(r.stdout[-800:],flush=True); print(r.stderr[-500:],flush=True)
        return None
    t=R["time"]; v=R["v(amout)"]
    m=am_metrics(t,v)
    f,S=spec(t,v); thd,fund,hs=carrier_thd(f,S)
    res=dict(name=name,VH=m["VH"],VL=m["VL"],m=m["m"],carrier=fund,thd=thd,
             t0=float(t[0]),t1=float(t[-1]),n=int(len(t)))
    print("   VH=%.4f VL=%.4f Vpp  m=%.2f%%  carrier=%.4f Vpp  THD=%.2f%%"%(
        m["VH"],m["VL"],m["m"],fund,thd),flush=True)
    # node health
    for k in ("v(m9col)","v(m9emit)","v(m9base)","v(m9e)","v(m9b)"):
        if k in R:
            res[k]=dict(mean=float(R[k].mean()),min=float(R[k].min()),max=float(R[k].max()))
    return res

if __name__=="__main__":
    import sys as s
    names=s.argv[1:] or ["mod_C_collector"]
    out={}
    for n in names:
        res=go(n)
        if res: out[n]=res
    prev={}
    fp=os.path.join(ST,"results","modulators.json")
    if os.path.exists(fp):
        try: prev=json.load(open(fp))
        except Exception: prev={}
    prev.update(out)
    json.dump(prev,open(fp,"w"),indent=1)
    print("saved",flush=True)

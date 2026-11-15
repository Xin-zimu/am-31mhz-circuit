# -*- coding: utf-8 -*-
"""Module 14 (final): output load + power, short windows for stiff cases."""
import os, sys, re, json, time, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from ltraw import run, log, load_raw
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
NET=os.path.join(STAGE,"netlists","frozen_poly.net")
B=os.path.join(STAGE,"bench","mod14"); RES=os.path.join(STAGE,"results")
RAW=open(NET,encoding="latin-1").read()
BASE=re.sub(r"^\.tran.*$","",RAW,flags=re.M)
BASE=re.sub(r"^\.options plotwinsize.*$","",BASE,flags=re.M)
BASE=re.sub(r"^\.end\s*$","",BASE,flags=re.M)
BASE=re.sub(r"^xEAM_-EAM.*$","* [POLY removed]",BASE,flags=re.M)
BASE=re.sub(r"^\.SUBCKT POLYSourceEAM_-EAM.*?^\.ENDS","",BASE,flags=re.M|re.S)
from scipy.optimize import fsolve
def xnet(u=1.05):
    a=0.1*u; b=0.4*u; R1=100e3
    def eqs(p):
        R2,R3=p; G=1/R1+1/R2+1/R3
        return [1/R1-a*G, (-5/R2)+b*G]
    R2,R3=fsolve(eqs,[125e3,13e3])
    return "RXA V1 XA %.6g\nRXB XA VN5 %.6g\nRXC XA 0 %.6g\nVXBIAS VN5 0 -5\n"%(R1,R2,R3)
SUP="VADP ADP 0 5\nVADN ADN 0 -5\n"
AD="XAD835 XA 0 A 0 ADN A TP3 ADP AD835\n.include ../../models/third_party_GLuisF/ad835.sub\n"
def go(name, load, tran, to=1500):
    p=os.path.join(B,name+".net")
    open(p,"w",encoding="utf-8").write(BASE+SUP+"RS TP2 A 510\nRP A 0 680\n"+xnet(1.05)+AD+load+
        "\n.options plotwinsize=0\n.save V(tp3) V(v1) V(a) I(VADP) I(VADN) I(RLOAD)\n"+tran+"\n.end\n")
    t0=time.time()
    try: r=run(p,ascii=True,timeout=to)
    except Exception: return None,"TIMEOUT %.0fs"%(time.time()-t0)
    sz=os.path.getsize(os.path.join(B,name+".raw")) if os.path.exists(os.path.join(B,name+".raw")) else 0
    if r.returncode!=0 or sz==0: return None,"FAIL %.0fs"%(time.time()-t0)
    return load_raw(os.path.join(B,name+".raw")),"ok %.0fs"%(time.time()-t0)

cases=[("noLoad","RLOAD TP3 0 1e6\n",".tran 0 400u 300u 2n uic"),
       ("L50_only","RLOAD TP3 0 50\n",".tran 0 400u 300u 2n uic"),
       ("L50p10","RLOAD TP3 0 50\nCLOAD TP3 0 10p\n",".tran 0 12u 10u 0.02n uic"),
       ("L25","RLOAD TP3 0 25\n",".tran 0 400u 300u 2n uic")]
out={}
for name,load,tran in cases:
    R,msg=go(name,load,tran); print("%-9s %s"%(name,msg),flush=True)
    if R is None: out[name]=None; continue
    t=R["time"]; v=R["V(tp3)"]
    T=16/31e6; n=int((t[-1]-t[0])/T); amp=[]
    for i in range(n):
        m=(t>=t[0]+i*T)&(t<t[0]+(i+1)*T)
        if m.sum()>3: amp.append((v[m].max()-v[m].min())/2)
    amp=np.array(amp); VH=2*np.percentile(amp,99); VL=2*np.percentile(amp,1)
    ip=float((-R["I(VADP)"]).mean()); iN=float((-R["I(VADN)"]).mean())
    pr=float((R["V(tp3)"]*R["I(RLOAD)"]).mean()) if "I(RLOAD)" in R else float('nan')
    out[name]=dict(VH=float(VH),VL=float(VL),m=float((VH-VL)/(VH+VL)*100),
                   Ip=ip,In=iN,P=5*ip+5*iN,Prload=pr,t0=float(t[0]),t1=float(t[-1]))
    print("   VH=%.4f VL=%.4f m=%.2f%%  I+=%.3f mA I-=%.3f mA  Psupply=%.2f mW  Pload=%.3f mW"%(
        VH,VL,(VH-VL)/(VH+VL)*100,ip*1e3,iN*1e3,(5*ip+5*iN)*1e3,pr*1e3))
json.dump(out,open(os.path.join(RES,"M14_load_power.json"),"w"),indent=1)
print("saved M14")

# -*- coding: utf-8 -*-
"""Background: model B full-project runs (stiff; long)."""
import os, sys, re, time, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from ltraw import run, log
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
NET=os.path.join(STAGE,"netlists","frozen_poly.net")
B=os.path.join(STAGE,"bench","mod6"); os.makedirs(B,exist_ok=True)
BASE=open(NET,encoding="latin-1").read()
BASE=re.sub(r"^\.tran.*$","",BASE,flags=re.M)
BASE=re.sub(r"^\.options plotwinsize.*$","",BASE,flags=re.M)
BASE=re.sub(r"^\.end\s*$","",BASE,flags=re.M)
BASE=re.sub(r"^xEAM_-EAM.*$","* [POLY removed]",BASE,flags=re.M)
BASE=re.sub(r"^\.SUBCKT POLYSourceEAM_-EAM.*?^\.ENDS","",BASE,flags=re.M|re.S)

SUP="VADP ADP 0 5\nVADN ADN 0 -5\n"
def xnet(u):
    a=0.1*u; b=0.4*u; R1=100e3
    from scipy.optimize import fsolve
    def eqs(p):
        R2,R3=p; G=1/R1+1/R2+1/R3
        return [1/R1-a*G, (-5/R2)+b*G]
    R2,R3=fsolve(eqs,[125e3,13e3])
    return ("RXA V1 XA %.6g\nRXB XA VN5 %.6g\nRXC XA 0 %.6g\nVXBIAS VN5 0 -5\n"%(R1,R2,R3))

jobs=[("adB_U100_buf", 1.00, True), ("adB_U105_buf", 1.05, True)]
for name,u,buffered in jobs:
    if buffered:
        xdrv = xnet(u) + "XBUF XA XB 0 1\nVXSRC XB 0 0\n"  # placeholder, replaced below
        body = BASE + xnet(u) + """
* ideal unity buffer between the X divider and the AD835 X1 pin
EBUF XB 0 XA 0 1
""" + SUP + "XAD835 XB 0 TP2 0 ADN TP2 TP3 ADP AD835_BEHAV\n"
    p=os.path.join(B,name+".net")
    open(p,"w",encoding="utf-8").write(body+".include ../../adapted/AD835_Behav.sub\n.options plotwinsize=0\n.tran 0 400u 300u 4n uic\n.end\n")
    t0=time.time(); r=run(p,ascii=True,timeout=3000)
    sz=os.path.getsize(os.path.join(B,name+".raw")) if os.path.exists(os.path.join(B,name+".raw")) else 0
    print("%-14s rc=%d %6.1fs raw=%d"%(name,r.returncode,time.time()-t0,sz), flush=True)
    if r.returncode: print(log(p)[-400:], flush=True)

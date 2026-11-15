# -*- coding: utf-8 -*-
"""Fix power sign convention and measure HFA1100 on its own."""
import os, sys, json, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from ltraw import run_and_load
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
B=os.path.join(STAGE,"bench","mod15"); os.makedirs(B,exist_ok=True)
def go(name, body, an=".op\n"):
    p=os.path.join(B,name+".net")
    open(p,"w",encoding="utf-8").write("* pwr\n.include ../../models/third_party_GLuisF/ad835.sub\n"
        ".include ../../models/third_party_GLuisF/hfa1100.sub\n"
        "VP VP 0 5\nVN VN 0 -5\n"+body+an+"\n.options plotwinsize=0\n.end\n")
    R,lg,rc=run_and_load(p,ascii=True)
    return R
def g(R,n):
    for k in R:
        if k.lower()==n.lower(): return float(np.atleast_1d(R[k])[0])
    return float('nan')
def pwr(R,tag):
    ip=g(R,"I(VP)"); iN=g(R,"I(VN)")
    # I(V) is positive when current flows INTO the source's + node (i.e. rail current drawn)
    Ppos=5.0*ip; Pneg=5.0*(-iN)
    print("  %-22s I(VP)=%+8.3f mA  I(VN)=%+9.3f mA  P+ =%7.2f mW  P- =%7.2f mW  Ptot=%7.2f mW"%(
        tag,ip*1e3,iN*1e3,Ppos*1e3,Pneg*1e3,(Ppos+Pneg)*1e3))
    return dict(Ip=ip,In=iN,Ppos=Ppos,Pneg=Pneg,P=(Ppos+Pneg))

print("=== quiescent power ===")
R=go("ad_only","VX1 X1 0 0\nVX2 X2 0 0\nVY1 Y1 0 0\nVY2 Y2 0 0\nVZ Z 0 0\n"
     "XU X1 X2 Y1 Y2 VN Z W VP AD835\nRL W 0 150\n")
a=pwr(R,"AD835 alone (models A)")
R=go("hfa_only","VIN IN 0 0.5\nXU3 IN FB VP VN OUT hfa1100\nRF OUT FB 470\nRG FB 0 470\nRL OUT 0 150\n")
b=pwr(R,"HFA1100 alone (gain 2)")
print()
print("Model A quiescent: 5V*16.667mA + 5V*16.756mA = %.1f mW  (datasheet 16 mA/rail typ -> 160 mW)"%((5*16.667+5*16.756)))
print("Model B quiescent: 5V*16.000mA + 5V*16.100mA = %.1f mW"%(5*16.0+5*16.1))
json.dump({"ad835":a,"hfa1100":b},open(os.path.join(STAGE,"results","M15_power.json"),"w"),indent=1)

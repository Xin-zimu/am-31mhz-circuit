# -*- coding: utf-8 -*-
"""Module 15: HFA1100 buffer separation - AD835 alone vs buffered.
Reproduces ad835_test1.asc's output stage (470+470, HFA1100 gain of 2 with
75 ohm to ground) so the 'buffered' number is not attributed to the AD835.
"""
import os, sys, json, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from ltraw import run_and_load
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
B=os.path.join(STAGE,"bench","mod15"); os.makedirs(B,exist_ok=True); RES=os.path.join(STAGE,"results")
SUP="VP VP 0 5\nVN VN 0 -5\n"
INC=".include ../../models/third_party_GLuisF/ad835.sub\n.include ../../models/third_party_GLuisF/hfa1100.sub\n"

# DC transfer of the AD835 alone vs the test1 arrangement
def go(name, body, an=".dc VX1 -1.2 1.2 0.005"):
    p=os.path.join(B,name+".net")
    open(p,"w",encoding="utf-8").write("* hfa1100 separation\n"+INC+SUP+body+an+"\n.options plotwinsize=0\n.end\n")
    R,lg,rc=run_and_load(p,ascii=True)
    return R

# (1) AD835 alone, W loaded only by 150 ohm
R1=go("alone","""
VX1 X1 0 0
VX2 X2 0 0
VY1 Y1 0 1
VY2 Y2 0 0
VZ Z 0 0
XU X1 X2 Y1 Y2 VN Z W VP AD835
RL W 0 150
""")
# (2) test1 topology: W -> 470 -> node -> 470 -> opamp+, 75 to gnd at opamp out
R2=go("buffered","""
VX1 X1 0 0
VX2 X2 0 0
VY1 Y1 0 1
VY2 Y2 0 0
VZ Z 0 0
XU X1 X2 Y1 Y2 VN Z W VP AD835
R4 W N1 470
R5 N1 XY 470
XU3 N1 XY VP VN OUT hfa1100
R6 OUT 0 75
""")
x=R1["V(x1)"]; wa=R1["V(w)"]; wb=R2["V(out)"]
print("DC transfer, Y=1 V, X swept")
print("  X      AD835 W      buffered OUT   ratio OUT/W")
for xv in (-1.0,-0.5,0.0,0.5,1.0):
    a=float(np.interp(xv,x,wa)); b=float(np.interp(xv,x,wb))
    print("  %+5.2f   %+9.4f   %+9.4f   %8.4f"%(xv,a,b,(b/a) if abs(a)>1e-6 else float('nan')))
# supply current of the buffer alone
R3=go("bufonly","""
VX1 X1 0 0
VX2 X2 0 0
VY1 Y1 0 1
VY2 Y2 0 0
VZ Z 0 0
XU X1 X2 Y1 Y2 VN Z W VP AD835
R4 W N1 470
R5 N1 XY 470
XU3 N1 XY VP VN OUT hfa1100
R6 OUT 0 75
IBUF VP 0 0
""", ".op\n")
def g(R,n):
    for k in R:
        if k.lower()==n.lower(): return float(np.atleast_1d(R[k])[0])
    return float('nan')
print("\nSupply currents at X=0:")
for nm,R in (("AD835 only",R1),("AD835+HFA1100",R3)):
    ip=g(R,"I(VP)"); iN=g(R,"I(VN)")
    print("  %-14s I(VP)=%+8.3f mA  I(VN)=%+8.3f mA  Ptot=%.2f mW"%(nm,-ip*1e3,-iN*1e3,5*(-ip)+5*(-iN)))
json.dump({"vx":x.tolist(),"w_alone":wa.tolist(),"out_buf":wb.tolist()},
          open(os.path.join(RES,"M15_hfa1100.json"),"w"))
print("\nsaved M15")

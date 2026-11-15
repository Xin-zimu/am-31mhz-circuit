# -*- coding: utf-8 -*-
"""DC design v4: follower emitter needs a DC return to ground."""
import os, sys, subprocess, numpy as np
sys.stdout.reconfigure(encoding="utf-8")
NG=r"D:\ms_xsp\s04_crosscheck_20261017\Spice64\bin\ngspice_con.exe"
ST=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = """
.model 2N3904 NPN(Is=6.734f Xti=3 Eg=1.11 Vaf=74.03 Bf=416.4 Ne=1.259
+ Ise=6.734f Ikf=66.78m Xtb=1.5 Br=.7371 Nc=2 Isc=0 Ikr=0 Rc=1
+ Cjc=3.638p Mjc=.3085 Vjc=.75 Fc=.5 Cje=4.493p Mje=.2593 Vje=.75
+ Tr=239.5n Tf=301.2p Itf=.4 Vtf=4 Xtf=2 Rb=10)
"""
B=os.path.join(ST,"bench","op"); os.makedirs(B,exist_ok=True)
def op(circuit, probes):
    p=os.path.join(B,"op.cir")
    open(p,"w",encoding="latin-1").write("* op\n"+circuit+MODEL+"\n.control\nop\n"+
        "".join("print %s\n"%n for n in probes)+"quit\n.endc\n.end\n")
    r=subprocess.run([NG,"-b","op.cir"],capture_output=True,text=True,
                     encoding="utf-8",errors="replace",timeout=120,cwd=B)
    out={}
    for ln in r.stdout.splitlines():
        s=ln.strip()
        if "=" in s and (s.startswith("v(") or s.startswith("@") or s.startswith("i(")):
            k,v=s.split("=",1); k=k.strip(); v=v.strip()
            try: out[k]=float(v)
            except: pass
    return out, r.stdout
if __name__=="__main__":
    print("=== emitter modulation: follower now has RE2 to ground ===")
    for vb1,re1 in ((1.05,100),(1.25,100),(1.25,220),(1.45,220)):
        rt,rr=(10e3*vb1/(5-vb1)),10e3
        for vxx,re2 in ((1.2,470),(1.6,470),(1.2,220)):
            r1,r2=0,0
            # follower base must be vxx+0.65 plus its own base current drop
            vfb=vxx+0.68
            idd=2e-3
            r2=vfb/idd; r1=(5-vfb)/idd
            c="""VCC vcc 0 5
RB1 vcc xb %g
RB2 xb 0 %g
Q1 vcc xc xe 2N3904
RC vcc xc 470
RE xe xx %g
R1 vcc fb %g
R2 fb 0 %g
Q2 vcc fb xx 2N3904
RE2 xx 0 %g
"""%(rt,rr,re1,r1,r2,re2)
            o,_=op(c,["v(xb)","v(xx)","v(xe)","v(xc)","@q1[ic]"])
            ic=o.get("@q1[ic]",0)*1e3
            ie1=(o.get("v(xb)",0)-0.65-o.get("v(xx)",0))/re1*1e3
            vce=o.get("v(xc)",0)-o.get("v(xe)",0)
            ok="OK " if (0.8<ic<6 and vce>1.2 and o.get("v(xx)",0)>0.4) else "   "
            print("%sVb1=%.2f Re1=%3g Vxx=%3.2f Re2=%3g -> V(xx)=%.3f V(xe)=%.3f Ic=%.2f mA Vce=%.2f Ie1p=%.2f"%(
                ok,vb1,re1,vxx,re2,o.get("v(xx)",0),o.get("v(xe)",0),ic,vce,ie1))

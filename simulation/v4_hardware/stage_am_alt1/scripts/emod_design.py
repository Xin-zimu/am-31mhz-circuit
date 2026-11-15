# -*- coding: utf-8 -*-
"""Emitter-modulation DC design, using explicit print probes."""
import os, sys, subprocess
sys.stdout.reconfigure(encoding="utf-8")
NG=r"D:\ms_xsp\s04_crosscheck_20261017\Spice64\bin\ngspice_con.exe"
ST=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B=os.path.join(ST,"bench","op"); os.makedirs(B,exist_ok=True)
MODEL="""
.model 2N3904 NPN(Is=6.734f Xti=3 Eg=1.11 Vaf=74.03 Bf=416.4 Ne=1.259
+ Ise=6.734f Ikf=66.78m Xtb=1.5 Br=.7371 Nc=2 Isc=0 Ikr=0 Rc=1
+ Cjc=3.638p Mjc=.3085 Vjc=.75 Fc=.5 Cje=4.493p Mje=.2593 Vje=.75
+ Tr=239.5n Tf=301.2p Itf=.4 Vtf=4 Xtf=2 Rb=10)
"""
NODES=["v(fb)","v(x)","v(xb)","v(xe)","v(xc)","@q1[ic]","@q2[ic]","i(vcc)"]
def probe(circuit):
    p=os.path.join(B,"d.cir")
    open(p,"w",encoding="latin-1").write("* op\n"+circuit+MODEL+"\n.control\nop\n"+
        "".join("print %s\n"%n for n in NODES)+"quit\n.endc\n.end\n")
    r=subprocess.run([NG,"-b","d.cir"],capture_output=True,text=True,
                     encoding="utf-8",errors="replace",timeout=120,cwd=B)
    out={}
    for ln in r.stdout.splitlines():
        s=ln.strip()
        if "=" in s and (s[0] in "vi@" or s.startswith("@")):
            k,v=s.split("=",1)
            try: out[k.strip()]=float(v.strip())
            except: pass
    return out

def emod(vm, r1, r2, r3, re2, re, rc, rb1=22e3, rb2=4.7e3):
    return """VCC vcc 0 5
VM vm 0 %g
RA1 vcc fb %g
RA2 vm fb %g
RA3 fb 0 %g
Q2 vcc fb x 2N3904
RE2 x 0 %g
RB1 vcc xb %g
RB2 xb 0 %g
Q1 vcc xc xe 2N3904
RC vcc xc %g
RE xe x %g
"""%(vm,r1,r2,r3,re2,rb1,rb2,rc,re)

if __name__=="__main__":
    a,b=1.00,0.060; rb=4.7e3
    k=1.0-a/5.0-b; G=1.0/(rb*k); R1=5.0/(a*G); R2=1.0/(b*G)
    print("divider R1=%.0f R2=%.0f R3=%.0f  -> V(fb)=%.3f+%.4f*Vm"%(R1,R2,rb,a,b))
    for vm in (0.0748,2.0,4.0748):
        o=probe(emod(vm,R1,R2,rb,50,100,470))
        print("Vm=%6.4f V(fb)=%.3f V(x)=%.3f V(xe)=%.3f V(xc)=%.3f Ic1=%7.3f mA  P=%.1f mW"%(
            vm,o.get("v(fb)",0),o.get("v(x)",0),o.get("v(xe)",0),o.get("v(xc)",0),
            o.get("@q1[ic]",0)*1e3, 5*abs(o.get("i(vcc)",0))*1e3))

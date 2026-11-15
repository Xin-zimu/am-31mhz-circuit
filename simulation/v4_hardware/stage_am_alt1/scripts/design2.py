# -*- coding: utf-8 -*-
"""ALT-1 definitive design: collector modulation with a rail that actually
regulates, verified by DC operating point first (1 s), then transient.

Interface facts recovered from the frozen netlist:
  TP2  is driven ONLY by vVCARRIER (ideal source) -> the oscillator is unloaded
  TP3  drives ONLY eEPA (a VCVS) -> input impedance is infinite
  => the acceptance quantity is a TP3 *voltage*, not 50 ohm power.
"""
import os, sys, subprocess, json, numpy as np
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
def op(circuit):
    p=os.path.join(B,"d.cir")
    open(p,"w",encoding="latin-1").write("* op\n"+circuit+MODEL+
        "\n.control\nop\nshow all\nquit\n.endc\n.end\n")
    r=subprocess.run([NG,"-b","d.cir"],capture_output=True,text=True,
                     encoding="utf-8",errors="replace",timeout=120,cwd=B)
    t=r.stdout
    return t

def circ(vrail_vm_lo, vrail_vm_hi, vxbase=1.05, rc=470, re=100, rel=2200):
    """Rail follower: base divider gives V(fb) = vrail+0.65 at Vm=lo and hi.
       R1 vcc, R2 gnd, Rm from Vm."""
    a = vrail_vm_lo+0.65; b=(vrail_vm_hi-vrail_vm_lo)/4.0
    # V(fb) = (5/R1 + Vm/Rm)/(1/R1+1/Rm+1/R2)
    rb=10e3
    k=1.0-a/5.0-b
    G=1.0/(rb*k); R1=5.0/(a*G); Rm=1.0/(b*G)
    return """VCC vcc 0 5
VM vm 0 0
R1M vcc fb %g
RmM vm fb %g
R2M fb 0 %g
Q9D vcc fb rail 2N3904
R9E rail 0 %g
RB1 vcc xb 22k
RB2 xb 0 0
RB2 xb 0 %g
Q9M rail xc xe 2N3904
RC rail xc %g
RE xe 0 %g
"""%(R1,Rm,rb,rel,rb*0+1, re*0+470, rc, re), (R1,Rm,rb)

if __name__=="__main__":
    for vr_lo,vr_hi in ((1.9,3.1),(2.2,3.4)):
        c,info=circ(vr_lo,vr_hi)
        t=op(c)
        print("=== rail %.2f..%.2f  R1=%.0f Rm=%.0f Rb=%.0f ==="%(vr_lo,vr_hi,*info))
        for ln in t.splitlines():
            s=ln.strip()
            if s.startswith("v(") or s.startswith("@q"):
                print("   ",s)

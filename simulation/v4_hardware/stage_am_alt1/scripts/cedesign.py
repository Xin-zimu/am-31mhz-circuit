# -*- coding: utf-8 -*-
"""ALT-1: corrected emitter-modulation design, DC-verified first.

Mechanism check (this is the design equation):
  CE gain = Rc/(re+Re), re = Vt/Ic.  Modulating the emitter changes Ic, hence re.
  For a 1.658 gain ratio with Re present:
      (re_lo+Re)/(re_hi+Re) = 1.658  ->  Re must be small vs re, i.e. Re ~ 0..20 ohm.
  So the emitter node is AC-grounded at BOTH 20 kHz and 31 MHz (via the audio
  source and its coupling cap), and the audio sets the DC operating point.
"""
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
def probe(c, names):
    p=os.path.join(B,"d.cir")
    open(p,"w",encoding="latin-1").write("* op\n"+c+MODEL+"\n.control\nop\n"+
        "".join("print %s\n"%n for n in names)+"quit\n.endc\n.end\n")
    r=subprocess.run([NG,"-b","d.cir"],capture_output=True,text=True,
                     encoding="utf-8",errors="replace",timeout=120,cwd=B)
    out={}
    for ln in r.stdout.splitlines():
        s=ln.strip()
        if "=" in s and s and s[0] in "vi@":
            k,v=s.split("=",1)
            try: out[k.strip()]=float(v.strip())
            except: pass
    return out

def ce(vm, rc=220, re1=10, rm=6800, rbx=470, rb1t=22e3, rb1b=4.7e3):
    """CE stage: C=xcn B=xbn E=va ; audio Thevenin into vae through RE1."""
    return """VCC vcc 0 5
VM mod 0 %g
RB01 vcc xbn %g
RB02 xbn 0 %g
QM1 xcn xbn va 2N3904
RC1 vcc xcn %g
RE1 va vae %g
RM1 mod vae %g
RBX1 vae 0 %g
"""%(vm,rb1t,rb1b,rc,re1,rm,rbx)

if __name__=="__main__":
    for vm in (0.0748, 2.0, 4.0748):
        o=probe(ce(vm),["v(xbn)","v(va)","v(vae)","v(xcn)","@qm1[ic]"])
        ic=o.get("@qm1[ic]",float('nan'))
        vce=o.get("v(xcn)",0)-o.get("v(va)",0)
        print("Vm=%6.4f V(xbn)=%.3f V(va)=%.3f V(vae)=%.3f V(xcn)=%.3f Ic=%6.3f mA Vce=%.2f re=%.1f ohm"%(
            vm,o.get("v(xbn)",0),o.get("v(va)",0),o.get("v(vae)",0),o.get("v(xcn)",0),
            ic*1e3,vce, 26.0/ (ic*1e3) if ic>0 else float('nan')))

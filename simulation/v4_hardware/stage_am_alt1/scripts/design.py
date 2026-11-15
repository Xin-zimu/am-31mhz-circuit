# -*- coding: utf-8 -*-
"""Parameterised modulator builder + batch sweep harness for ALT-1.

Collector modulation design equations (Class-A RF stage, collector load
returned to a modulated rail):
    Ic = (Vrail - Vknee)/Rc ,  Vknee = Vce_min + Ve
    envelope ratio m_target -> Vrail_hi/Vrail_lo = (1+m)/(1-m)
    Vrail(Vm) = a + b*Vm ; follower base = Vrail + Vbe
"""
import os, sys, json
sys.stdout.reconfigure(encoding="utf-8")
ST=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OSC=open(os.path.join(ST,"sources","C4_original.cir"),encoding="utf-8",errors="replace").read().split(".control")[0]
MODEL = """
.model 2N3904 NPN(Is=6.734f Xti=3 Eg=1.11 Vaf=74.03 Bf=416.4 Ne=1.259
+ Ise=6.734f Ikf=66.78m Xtb=1.5 Br=.7371 Nc=2 Isc=0 Ikr=0 Rc=1
+ Cjc=3.638p Mjc=.3085 Vjc=.75 Fc=.5 Cje=4.493p Mje=.2593 Vje=.75
+ Tr=239.5n Tf=301.2p Itf=.4 Vtf=4 Xtf=2 Rb=10)
"""

def divider_for(v_lo, v_hi, vm_lo=0.0748175, vm_hi=4.0748175, rbot=20e3):
    """3-resistor network vcc/Vm/gnd giving  V1 = v_lo + (v_hi-v_lo)*(Vm-vm_lo)/(vm_hi-vm_lo)."""
    dv = vm_hi - vm_lo
    b = (v_hi - v_lo)/dv
    a = v_lo - b*vm_lo                 # V1 = a + b*Vm
    # V1 = (5/Rt + Vm/Rm)/G ,  G=1/Rt+1/Rm+1/Rb
    # 5/(Rt*G) = a  ;  1/(Rm*G) = b
    # => Rt*G = 5/a ; Rm*G = 1/b
    RtG = 5.0/a; RmG = 1.0/b
    G = (1.0/RtG + 1.0/RmG + 1.0/rbot)
    return dict(Rt=RtG/G, Rm=RmG/G, Rb=rbot, G=G, a=a, b=b)

def build_collector(tag, rc=470, re2=100, rload=50, cload=10e-12,
                    vknee=0.60, m_target=0.2477, vrail_lo=None, extra=""):
    e = (1+m_target)/(1-m_target)      # Vrail_hi/Vrail_lo
    if vrail_lo is None:
        vrail_lo = vknee*e/(e-1) + 0.55   # leave >=0.55 V of Vce headroom
    vrail_hi = vrail_lo*e
    d = divider_for(vrail_lo+0.70, vrail_hi+0.70)
    stage = """* --- collector modulation (m_target=%.4f, Vrail %.3f..%.3f V) ---
R9T vcc m9b %.4f
R9M m9src m9b %.4f
R9B m9b 0 %.4f
Q9D vcc m9b m9rail 2N3904
R9E m9rail 0 470
C9IN out m9base 1n
R9C vcc m9base 22k
R9F m9base 0 4.7k
Q9M m9rail m9col m9emit 2N3904
R9G m9rail m9col %g
R9H m9emit 0 %g
C9OUT m9col amout 10n
R9L amout 0 %g
C9L amout 0 %gp
%s""" % (m_target, vrail_lo, vrail_hi, d["Rt"], d["Rm"], d["Rb"], rc, re2, rload, cload*1e12, extra)
    return stage, dict(vrail_lo=vrail_lo, vrail_hi=vrail_hi, ratio=e, **{k:v for k,v in d.items() if k in("Rt","Rm","Rb")})

def build_emitter(tag, rc=470, re2=100, rload=50, cload=10e-12, m_target=0.2477, extra=""):
    # gain ~ 1/(re+Re2); modulate the emitter node downward with Vm
    d = divider_for(0.0, 0.0)  # placeholder, replaced by caller
    return None, None

def net(tag, stage, vmlo=0.0748175, vmhi=4.0748175, duty="4.98u"):
    return (OSC + "\n* ===== %s =====\n" % tag +
            "V9SRC m9src 0 PULSE(%g %g 200u 20n 20n %s 50u)\n" % (vmlo, vmhi, duty) +
            stage + MODEL +
            ".options method=trap maxord=2 reltol=1e-4 trtol=7 temp=27 tnom=27\n")

if __name__=="__main__":
    st,info=build_collector("C")
    print(json.dumps(info,indent=1))

# -*- coding: utf-8 -*-
"""ALT-1 step 6: properly biased modulator candidates.

Design target (matches POLY exactly): envelope(Vm) = Vc*(0.6 + 0.1*Vm)/1.0075
  -> VH/VL = 1.0075/0.6075 = 1.658, m = 24.77% at Vm = 0.0748 .. 4.0748 V

Collector modulation: RF gain ~ Ic, so need Ic_hi/Ic_lo = 1.658.
  Ic = (Vrail - Vknee)/Rc  =>  Vrail(Vm) = a + b*Vm
  solved:  a = 1.171, b = 0.1451  (Rc = 470, Ic_mean = 2 mA)
  follower base = Vrail + 0.7  =>  Vbase = 1.871 + 0.1451*Vm
  3-resistor network into the base: Rtop=26.7k (vcc), Rmod=68.9k (Vm), Rbot=20.8k (gnd)
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
def mk(tag, vmlo, vmhi, stage, duty="4.98u", period="50u"):
    return (OSC + "\n* ===== %s =====\n" % tag +
            "V9SRC m9src 0 PULSE(%g %g 200u 20n 20n %s %s)\n" % (vmlo, vmhi, duty, period) +
            stage + MODEL +
            ".options method=trap maxord=2 reltol=1e-4 trtol=7 temp=27 tnom=27\n")

def c_stage(rtop=26.7e3, rmod=68.9e3, rbot=20.8e3, rc=470, re2=100, rload=50, cload=10e-12):
    return """* --- collector modulation: modulated rail drives the RF collector load ---
R9T vcc m9b %g
R9M m9src m9b %g
R9B m9b 0 %g
Q9D vcc m9b m9rail 2N3904
R9E m9rail 0 1k
C9IN out m9base 1n
R9C vcc m9base 22k
R9F m9base 0 4.7k
Q9M m9rail m9col m9emit 2N3904
R9G m9rail m9col %g
R9H m9emit 0 %g
C9OUT m9col amout 10n
R9L amout 0 %g
C9L amout 0 %gp
""" % (rtop, rmod, rbot, rc, re2, rload, cload*1e12)

def e_stage(rtop=26.7e3, rmod=68.9e3, rbot=20.8e3, rc=470, re2=100, rload=50, cload=10e-12):
    return """* --- emitter modulation: modulated emitter node degenerates the RF stage ---
R9T vcc m9b %g
R9M m9src m9b %g
R9B m9b 0 %g
Q9D vcc m9b m9rail 2N3904
R9E m9rail 0 1k
C9IN out m9base 1n
R9C vcc m9base 22k
R9F m9base 0 4.7k
Q9M vcc m9col m9emit 2N3904
R9G vcc m9col %g
R9H m9emit m9rail %g
C9OUT m9col amout 10n
R9L amout 0 %g
C9L amout 0 %gp
""" % (rtop, rmod, rbot, rc, re2, rload, cload*1e12)

def b_stage(rtop=26.7e3, rmod=68.9e3, rbot=20.8e3, rc=470, re2=100, rload=50, cload=10e-12):
    return """* --- base modulation: 20 kHz summed into the RF stage base bias ---
R9T vcc m9b %g
R9M m9src m9b %g
R9B m9b 0 %g
C9IN out m9base 1n
R9C vcc m9base 22k
R9F m9base m9b 22k
Q9M vcc m9col m9emit 2N3904
R9G vcc m9col %g
R9H m9emit 0 %g
C9OUT m9col amout 10n
R9L amout 0 %g
C9L amout 0 %gp
""" % (rtop, rmod, rbot, rc, re2, rload, cload*1e12)

if __name__=="__main__":
    d=os.path.join(ST,"netlists"); os.makedirs(d,exist_ok=True)
    jobs=[("mod_C_collector", c_stage()), ("mod_E_emitter", e_stage()), ("mod_B_base", b_stage())]
    for nm,st in jobs:
        open(os.path.join(d,nm+".cir"),"w",encoding="latin-1").write(mk(nm,0.0748175,4.0748175,st))
    print("built:", [j[0] for j in jobs])

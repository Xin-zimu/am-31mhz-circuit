# -*- coding: utf-8 -*-
"""Full operating-point dump for a given circuit (fast)."""
import os, sys, subprocess
sys.stdout.reconfigure(encoding="utf-8")
NG=r"D:\ms_xsp\s04_crosscheck_20261017\Spice64\bin\ngspice_con.exe"
ST=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL="""
.model 2N3904 NPN(Is=6.734f Xti=3 Eg=1.11 Vaf=74.03 Bf=416.4 Ne=1.259
+ Ise=6.734f Ikf=66.78m Xtb=1.5 Br=.7371 Nc=2 Isc=0 Ikr=0 Rc=1
+ Cjc=3.638p Mjc=.3085 Vjc=.75 Fc=.5 Cje=4.493p Mje=.2593 Vje=.75
+ Tr=239.5p Tf=301.2p Itf=.4 Vtf=4 Xtf=2 Rb=10)
"""
B=os.path.join(ST,"bench","op"); os.makedirs(B,exist_ok=True)
def dump(circuit):
    p=os.path.join(B,"d.cir")
    open(p,"w",encoding="latin-1").write("* dump\n"+circuit+MODEL+
        "\n.options savecurrents\n.control\nop\nshow all\nquit\n.endc\n.end\n")
    r=subprocess.run([NG,"-b","d.cir"],capture_output=True,text=True,
                     encoding="utf-8",errors="replace",timeout=120,cwd=B)
    return r.stdout
if __name__=="__main__":
    c="""VCC vcc 0 5
RB1 vcc xb 4084.51
RB2 xb 0 10000
Q1 vcc xc xe 2N3904
RC vcc xc 470
RE xe xx 100
R1 vcc fb 1560
R2 fb 0 940
Q2 vcc fb xx 2N3904
RE2 xx 0 470
"""
    t=dump(c)
    print(t[-3500:])

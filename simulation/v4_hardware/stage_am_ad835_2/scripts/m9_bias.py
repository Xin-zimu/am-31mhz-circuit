# -*- coding: utf-8 -*-
"""Module 9: bias-current sensitivity of the project interface (both models).
Sweeps the AD835 input bias current via explicit current sources at the
X1 and Y1/Z pins and records the resulting DC operating point and envelope.
"""
import os, sys, re, json, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from ltraw import run_and_load, log
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
NET=os.path.join(STAGE,"netlists","frozen_poly.net")
B=os.path.join(STAGE,"bench","mod9"); os.makedirs(B,exist_ok=True)
RES=os.path.join(STAGE,"results")
BASE=open(NET,encoding="latin-1").read()
BASE=re.sub(r"^\.tran.*$","",BASE,flags=re.M)
BASE=re.sub(r"^\.options plotwinsize.*$","",BASE,flags=re.M)
BASE=re.sub(r"^\.end\s*$","",BASE,flags=re.M)

# Y/Z network from stage AM-AD835.1 recommendation: 510/680 attenuator + 680 shunt
def ynet(rs, rp):
    return ("* Y/Z attenuator: TP2 -Rs- nodeA -Rp- gnd ; Y1=Z=nodeA\n"
            "RS TP2 A %.6g\nRP A 0 %.6g\n"%(rs,rp))

def build(name, ibx, iby, ibz, rs=510.0, rp=680.0, use_ib=True):
    body=BASE
    extra = ynet(rs,rp)
    # AD835 model A instance: X1=nodeX, X2=0, Y1=A, Y2=0, VN, Z=A, W=TP3, VP
    extra += "VADP ADP 0 5\nVADN ADN 0 -5\n"
    extra += "XAD835 XA 0 A 0 ADN A TP3 ADP AD835\n"
    if use_ib:
        # inject extra bias current at the pins (sign: into the pin = negative I source from pin to gnd)
        extra += "IBX XA 0 %.6g\nIBY A 0 %.6g\nIBZ A 0 %.6g\n"%(ibx,iby,ibz)
    extra += ".include ../../models/third_party_GLuisF/ad835.sub\n"
    p=os.path.join(B,name+".net")
    open(p,"w",encoding="utf-8").write(body+"\n"+extra+
        "\n.options plotwinsize=0\n.tran 0 300u 200u 4n uic\n.end\n")
    return p

def xnet(u=1.05):
    a=0.1*u; b=0.4*u; R1=100e3
    from scipy.optimize import fsolve
    def eqs(p):
        R2,R3=p; G=1/R1+1/R2+1/R3
        return [1/R1-a*G, (-5/R2)+b*G]
    R2,R3=fsolve(eqs,[125e3,13e3])
    return "RXA V1 XA %.6g\nRXB XA VN5 %.6g\nRXC XA 0 %.6g\nVXBIAS VN5 0 -5\n"%(R1,R2,R3)

print("=== Y/Z attenuator 510/680, X network U=1.05, AD835 model A ===")
rows=[]
for iby_uA, ibz_uA in [(0,0),(10,50),(27,100),(-27,-100),(27,-100),(-27,100)]:
    name="sens_y%+d_z%+d"%(iby_uA,ibz_uA)
    body=BASE
    p=os.path.join(B,name+".net")
    extra = ynet(510,680) + xnet(1.05) + "VADP ADP 0 5\nVADN ADN 0 -5\n" + \
            "XAD835 XA 0 A 0 ADN A TP3 ADP AD835\n"
    if iby_uA or ibz_uA:
        extra += "IBY A 0 %.6g\nIBZ A 0 %.6g\n"%(iby_uA*1e-6, ibz_uA*1e-6)
    extra += ".include ../../models/third_party_GLuisF/ad835.sub\n"
    open(p,"w",encoding="utf-8").write(body+"\n"+extra+
        "\n.options plotwinsize=0\n.tran 0 300u 200u 4n uic\n.end\n")
    R,lg,rc=run_and_load(p,ascii=True,expect_ok=False)
    if R is None:
        print("  %-18s FAIL"%name); continue
    t=R["time"]; a=R["V(a)"]; tp3=R["V(tp3)"]; xe=R["V(xa)"]
    m=t>t[-1]*0.9
    # carrier envelope on A
    T=32.3e-9*64; n=int((t[-1]-t[m][0])/T); hi=[];lo=[]
    tt=t[m]; aa=a[m]
    for i in range(n):
        s=(tt>=tt[0]+i*T)&(tt<tt[0]+(i+1)*T)
        if s.sum()>3: hi.append(aa[s].max()); lo.append(aa[s].min())
    print("  IY=%+4d uA IZ=%+5d uA : V(A)dc=%+8.4f V  |A|peak=%6.4f V  TP3 vpp(mean)=%7.4f  Xdc=%+7.4f"%(
        iby_uA, ibz_uA, a[m].mean(), max(abs(min(lo)),abs(max(hi))),
        2*np.mean(np.array(hi)-np.array(lo))/2*2, xe[m].mean()))
    rows.append({"iby_uA":iby_uA,"ibz_uA":ibz_uA,"VAdc":float(a[m].mean()),
                 "Apeak":float(max(abs(min(lo)),abs(max(hi)))),"Xdc":float(xe[m].mean())})
json.dump(rows,open(os.path.join(RES,"M9_bias.json"),"w"),indent=1)
print("\nsaved M9_bias.json")

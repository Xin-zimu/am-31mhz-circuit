
# -*- coding: utf-8 -*-
"""v2: trimmer ACROSS the tank (does NOT touch the Colpitts divider ratio)."""
from pathlib import Path
import json, subprocess, math, time
import numpy as np
EXE=Path('D:/ms_xsp/s04_crosscheck_20261017/Spice64/bin/ngspice_con.exe')
ROOT=Path(r'D:\实验报告文件夹\电路2\tmp\lcdev'); (ROOT/'cir').mkdir(parents=True,exist_ok=True)
WORK=ROOT/'work'; WORK.mkdir(parents=True,exist_ok=True)
MDL=Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage4_rf_oscillator\advance_20261029\2N3904_UNCG.lib').read_text(encoding='ascii').strip()
F0=31e6; LC=1.0/(2*math.pi*F0)**2
def readraw(p):
    with open(p,'rb') as f:
        names=[];inside=False
        while True:
            s=f.readline().decode('ascii').strip()
            if s=='Binary:':break
            if s=='Variables:':inside=True;continue
            if inside and s:names.append(s.split()[1].lower())
        a=np.fromfile(f,dtype='<f8').reshape(-1,len(names))
    return dict(zip(names,a.T))
def f_of(t,e):
    dc=float(np.trapezoid(e,t)/(t[-1]-t[0])); v=e-dc
    idx=np.where((v[:-1]<=0)&(v[1:]>0))[0]
    if len(idx)<10: return None,dc
    cr=t[idx]-v[idx]*(t[idx+1]-t[idx])/(v[idx+1]-v[idx])
    return float((len(cr)-1)/(cr[-1]-cr[0])),dc
def net(name,LnH,Cp,CTp,Q,SRF,temp,vs,stop_us=400,save_us=90,load=True):
    L=LnH*1e-9; Rs=2*math.pi*F0*L/Q; CPAR=1.0/((2*math.pi*SRF*1e6)**2*L)
    ld="RLOAD out 0 2000\nCLOAD out 0 10p\n" if load else "RLOAD out 0 1e15\n"
    return f'''* LC Colpitts | L={LnH}nH Q={Q} SRF={SRF}MHz | trimmer(across tank)={CTp}pF | C1=C2={Cp}pF
VSUP vcc 0 PWL(0 0 1u {vs})
R1 vcc b 10k
R2 b 0 10k
Q1 vcc b e 2N3904
R3 e 0 4.7k
C1 b e {Cp}p
C2 e 0 {Cp}p
CBLK b nL 1000p
LR nL n1 {Rs:.6f}
L1 n1 0 {LnH}n
CP n1 0 {CPAR*1e12:.6f}p
CT n1 0 {CTp}p
C3 vcc 0 100n
C4 vcc 0 10u
CIN e bf 1n
RBT vcc bf 10k
RBB bf 0 10k
QB vcc bf ef 2N3904
REB ef 0 330
COUT ef out 1n
{ld}{MDL}
.options method=trap maxord=2 reltol=1e-3 trtol=7 temp={temp} tnom=27
.control
set filetype=binary
set num_threads=1
save v(vcc) v(b) v(e) v(out) i(vsup)
tran 0.125n {stop_us}u {save_us}u 0.125n uic
write {name}.raw
quit
.endc
.end
'''
def run(name,**kw):
    src=net(name,**kw)
    (ROOT/'cir'/(name+'.cir')).write_text(src,encoding='ascii')
    (WORK/(name+'.cir')).write_text(src,encoding='ascii')
    raw=WORK/(name+'.raw')
    if raw.exists(): raw.unlink()
    t0=time.monotonic()
    subprocess.run([str(EXE),'-b','-n','-o',str(WORK/(name+'.log')),str(WORK/(name+'.cir'))],
                   cwd=WORK,capture_output=True,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
    if not raw.exists(): return None
    d=readraw(raw); t=d['time']; e=d['v(out)']
    f,dc=f_of(t,e); mm=t>=(kw.get('save_us',90)*1e-6)
    return dict(name=name,freq_hz=f,err_ppm=(f/F0-1)*1e6 if f else None,vpp=float(np.ptp(e[mm])),
                dc=dc,supply_mw=float(-np.trapezoid(d['v(vcc)']*d['i(vsup)'],t)/(t[-1]-t[0])*1e3),
                seconds=round(time.monotonic()-t0,1),**kw)

E24=[10,11,12,13,15,16,18,20,22,24,27,30,33,36,39,43,47,51,56,62,68,75,82,91]
def Leff(LnH,SRF):
    L=LnH*1e-9; return L/(1-(F0/(SRF*1e6))**2)

print("=== 1) restore oscillation: trimmer across tank, C1=C2=33p ===")
for CT in [0.5,5.5,9.0]:
    r=run("tr_%s"%str(CT).replace('.','p'),LnH=1200,Cp=33,CTp=CT,Q=60,SRF=200,temp=27,vs=5)
    if r: print("  CT=%4.1f pF -> f=%9.3f kHz  Vpp=%7.4f  P=%5.2f mW (%.0fs)"%(
        CT,(r['freq_hz'] or 0)/1e3,r['vpp'],r['supply_mw'],r['seconds']))

print("\n=== 2) design table: which (L, E24 C, trimmer) land on 31 MHz? ===")
print("L(nH)  SRF   C1=C2  Ctank_req  CT_needed   trimmer 2-10pF")
rows=[]
for LnH,SRF in [(330,500),(470,400),(560,350),(680,300),(820,250),(1200,200),(1500,150)]:
    Le=Leff(LnH,SRF); Ctank=LC/Le*1e12
    best=None
    for C in E24:
        CT=Ctank-C/2.0
        ok = 2.0<=CT<=10.0
        if ok and (best is None or abs(CT-6.0)<abs(best[1]-6.0)):
            best=(C,CT)
    if best:
        print("%5d  %4dMHz  %4.0fpF  %8.2fpF  %8.2fpF   OK"%(LnH,SRF,best[0],Ctank,best[1]))
        rows.append((LnH,SRF,best[0],best[1],Ctank))
    else:
        print("%5d  %4dMHz    --   %8.2fpF   %8.2fpF   no E24 fit"%(LnH,SRF,Ctank,Ctank-16.5))
(ROOT/'design_table.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')

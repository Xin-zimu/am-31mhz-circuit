
# -*- coding: utf-8 -*-
"""(a) Q threshold for the existing topology  (b) common-base Colpitts with real Q."""
from pathlib import Path
import json, subprocess, math
import numpy as np
EXE=Path('D:/ms_xsp/s04_crosscheck_20261017/Spice64/bin/ngspice_con.exe')
ROOT=Path(r'D:\实验报告文件夹\电路2\tmp\lcdev'); WORK=ROOT/'work'
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
    if len(idx)<10: return None
    cr=t[idx]-v[idx]*(t[idx+1]-t[idx])/(v[idx+1]-v[idx])
    return float((len(cr)-1)/(cr[-1]-cr[0]))
def go(name,src):
    (ROOT/'cir'/(name+'.cir')).write_text(src,encoding='ascii')
    (WORK/(name+'.cir')).write_text(src,encoding='ascii')
    raw=WORK/(name+'.raw')
    if raw.exists(): raw.unlink()
    subprocess.run([str(EXE),'-b','-n','-o',str(WORK/(name+'.log')),str(WORK/(name+'.cir'))],
                   cwd=WORK,capture_output=True,timeout=900,creationflags=subprocess.CREATE_NO_WINDOW)
    if not raw.exists(): return None
    d=readraw(raw); t=d['time']; e=d['v(out)']
    m=t>=t[-1]-100e-6
    f=f_of(t[m],e[m])
    return dict(freq_hz=f,err_ppm=(f/F0-1)*1e6 if f else None,vpp=float(np.ptp(e[m])),
                supply_mw=float(-np.trapezoid(d['v(vcc)']*d['i(vsup)'],t)/(t[-1]-t[0])*1e3))

def cur(NAME,Rs,LnH=1280.07,Cp=33,CTp=0.5,CPp=0.0,stop=400):
    return f'''* (a) existing CE-Colpitts, series R sweep
VSUP vcc 0 PWL(0 0 1u 5)
R1 vcc b 10k
R2 b 0 10k
Q1 vcc b e 2N3904
R3 e 0 4.7k
C1 b e {Cp}p
C2 e 0 {Cp}p
CT e 0 {CTp}p
CBLK b nL 1000p
LR nL n1 {Rs}
L1 n1 0 {LnH}n
CP n1 0 {CPp}p
C3 vcc 0 100n
C4 vcc 0 10u
CIN e bf 1n
RBT vcc bf 10k
RBB bf 0 10k
QB vcc bf ef 2N3904
REB ef 0 330
COUT ef out 1n
RLOAD out 0 2000
CLOAD out 0 10p
{MDL}
.options method=trap maxord=2 reltol=1e-3 trtol=7 temp=27 tnom=27
.control
set filetype=binary
set num_threads=1
save v(vcc) v(out) i(vsup)
tran 0.125n {stop}u {stop-100}u 0.125n uic
write {NAME}.raw
quit
.endc
.end
'''

def cb(NAME,LnH,Rs,CPp,C1p=39,C2p=39,CTp=0.5,stop=400):
    return f'''* (b) common-base Colpitts, L in collector, real Q
VSUP vcc 0 PWL(0 0 1u 5)
RFC1 vcc c 1m
R1 vcc b 10k
R2 b 0 3.3k
CBYP b 0 100n
Q1 c b e 2N3904
RE e 0 1k
C1 c e {C1p}p
C2 e 0 {C2p}p
LR c n1 {Rs}
L1 n1 0 {LnH}n
CP n1 0 {CPp}p
CT n1 0 {CTp}p
C3 vcc 0 100n
C4 vcc 0 10u
COUT c out 1n
RLOAD out 0 2000
CLOAD out 0 10p
{MDL}
.options method=trap maxord=2 reltol=1e-3 trtol=7 temp=27 tnom=27
.control
set filetype=binary
set num_threads=1
save v(vcc) v(out) v(c) v(e) i(vsup)
tran 0.125n {stop}u {stop-100}u 0.125n uic
write {NAME}.raw
quit
.endc
.end
'''
print("=== (a) existing topology: how low must the inductor loss be? ===")
print("  Rs(ohm)   Q@31MHz   Vout(Vpp)    f(kHz)")
for Rs in [0,0.001,0.01,0.05,0.1,0.23,0.5,1.0,3.9]:
    Q=2*math.pi*F0*1280.07e-9/Rs if Rs>0 else float('inf')
    nm="rs_%s"%str(Rs).replace(".","p"); r=go(nm, cur(nm,Rs))
    if r is None: print("  %7.3f  FAILED"%Rs); continue
    print("  %7.3f  %8s  %10.4f  %9.2f"%(Rs,("%.0f"%Q) if Q!=float('inf') else "inf",r['vpp'],(r['freq_hz'] or 0)/1e3))

print("\n=== (b) common-base Colpitts, Q=60 (Rs=3.9 ohm), L=1.2uH, C1=C2=39p ===")
L=1200e-9
for Q,SRF in [(1000,500),(200,400),(60,300),(30,250)]:
    Rs=2*math.pi*F0*L/Q; CP=1.0/((2*math.pi*SRF*1e6)**2*L)
    nm="cb_%d"%Q; r=go(nm, cb(nm,L*1e9,Rs,CP*1e12))
    if r is None: print("  Q=%4d FAILED"%Q); continue
    print("  Q=%4d SRF=%3dMHz  Vout=%8.4f Vpp  f=%10.2f kHz  err=%+8.0f ppm  P=%5.2f mW"%(
        Q,SRF,r['vpp'],(r['freq_hz'] or 0)/1e3,r['err_ppm'] or 0,r['supply_mw']))
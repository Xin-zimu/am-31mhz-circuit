
# -*- coding: utf-8 -*-
"""Last check: smaller L with bigger C (Ki=7.5) on a REAL inductor, and the base-collector LC variant."""
from pathlib import Path
import json, subprocess, math
import numpy as np
EXE=Path('D:/ms_xsp/s04_crosscheck_20261017/Spice64/bin/ngspice_con.exe')
ROOT=Path(r'D:\实验报告文件夹\电路2\tmp\lcdev'); WORK=ROOT/'work'
MDL=Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage4_rf_oscillator\advance_20261029\2N3904_UNCG.lib').read_text(encoding='ascii').strip()
F0=31e6
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
def go(nm,src):
    (ROOT/'cir'/(nm+'.cir')).write_text(src,encoding='ascii')
    (WORK/(nm+'.cir')).write_text(src,encoding='ascii')
    raw=WORK/(nm+'.raw')
    if raw.exists(): raw.unlink()
    subprocess.run([str(EXE),'-b','-n','-o',str(WORK/(nm+'.log')),str(WORK/(nm+'.cir'))],
                   cwd=WORK,capture_output=True,timeout=900,creationflags=subprocess.CREATE_NO_WINDOW)
    if not raw.exists(): return None
    d=readraw(raw); t=d['time']; e=d['v(out)']; m=t>=t[-1]-100e-6
    f=f_of(t[m],e[m])
    return dict(freq_hz=f,err_ppm=(f/F0-1)*1e6 if f else None,vpp=float(np.ptp(e[m])),
                supply_mw=float(-np.trapezoid(d['v(vcc)']*d['i(vsup)'],t)/(t[-1]-t[0])*1e3))

def ce(NAME,LnH,Cp,CTp,Rs,CPp,RE="4.7k",stop=400):
    return f'''* CE Colpitts, real L
VSUP vcc 0 PWL(0 0 1u 5)
R1 vcc b 10k
R2 b 0 10k
Q1 vcc b e 2N3904
R3 e 0 {RE}
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
# base-collector LC feedback (very standard HF oscillator: L from base to collector)
def bc(NAME,LnH,C1p,C2p,Rs,CPp,RE="1k",stop=400):
    return f'''* Base-collector LC oscillator (Vackar-like), real L
VSUP vcc 0 PWL(0 0 1u 5)
R1 vcc b 22k
R2 b 0 10k
Q1 c b e 2N3904
R3 e 0 {RE}
C2 e 0 {C2p}p
CB b 0 100n
LR b n1 {Rs}
L1 n1 c {LnH}n
CP n1 c {CPp}p
C1 n1 c {C1p}p
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
save v(vcc) v(out) v(b) v(c) v(e) i(vsup)
tran 0.125n {stop}u {stop-100}u 0.125n uic
write {NAME}.raw
quit
.endc
.end
'''
print("=== CE Colpitts, small L / large C, real Q=60 ===")
for LnH,Q,SRF,Cp,CTp in [(330,60,500,92,10),(470,60,400,77,10),(560,60,350,72,10),(680,60,300,66,10)]:
    Rs=2*math.pi*F0*LnH*1e-9/Q; CP=1.0/((2*math.pi*SRF*1e6)**2*LnH*1e-9)
    nm="ce_%dnH"%LnH
    r=go(nm, ce(nm,LnH,Cp,CTp,Rs,CP*1e12))
    if r is None: print(" %4dnH FAILED"%LnH); continue
    print("  L=%4dnH Q=%d  C1=C2=%2dpF CT=%4.1f pF  Vout=%8.4f Vpp  f=%9.2f kHz  P=%5.2f mW"%(
        LnH,Q,Cp,CTp,r['vpp'],(r['freq_hz'] or 0)/1e3,r['supply_mw']))

print("\n=== base-collector LC, real Q sweep (L=1.2uH) ===")
L=1200e-9
for Q,SRF in [(1000,500),(200,400),(60,300),(30,250)]:
    Rs=2*math.pi*F0*L/Q; CP=1.0/((2*math.pi*SRF*1e6)**2*L)
    nm="bc_%d"%Q
    r=go(nm, bc(nm,L*1e9,470,470,Rs,CP*1e12))
    if r is None: print("  Q=%4d FAILED"%Q); continue
    print("  Q=%4d SRF=%3dMHz  Vout=%8.4f Vpp  f=%9.2f kHz  P=%5.2f mW"%(
        Q,SRF,r['vpp'],(r['freq_hz'] or 0)/1e3,r['supply_mw']))
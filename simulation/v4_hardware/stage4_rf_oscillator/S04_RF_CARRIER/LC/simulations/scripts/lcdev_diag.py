
# -*- coding: utf-8 -*-
"""Diagnose: is it slow startup or genuinely below oscillation threshold?"""
from pathlib import Path
import json, subprocess, math, time
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
def build(name,LnH,Cp,CTp,Q,SRF,stop_us):
    L=LnH*1e-9; Rs=2*math.pi*F0*L/Q; CPAR=1.0/((2*math.pi*SRF*1e6)**2*L)
    return f'''* diag
VSUP vcc 0 PWL(0 0 1u 5)
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
RLOAD out 0 2000
CLOAD out 0 10p
{MDL}
.options method=trap maxord=2 reltol=1e-3 trtol=7 temp=27 tnom=27
.control
set filetype=binary
set num_threads=1
save v(vcc) v(b) v(e) v(out) i(vsup)
tran 0.125n {stop_us}u 0 0.125n uic
write {name}.raw
quit
.endc
.end
'''
def run(name,**kw):
    src=build(name,**kw)
    (ROOT/'cir'/(name+'.cir')).write_text(src,encoding='ascii')
    (WORK/(name+'.cir')).write_text(src,encoding='ascii')
    raw=WORK/(name+'.raw')
    if raw.exists(): raw.unlink()
    subprocess.run([str(EXE),'-b','-n','-o',str(WORK/(name+'.log')),str(WORK/(name+'.cir'))],
                   cwd=WORK,capture_output=True,timeout=900,creationflags=subprocess.CREATE_NO_WINDOW)
    return readraw(raw) if raw.exists() else None

for tag,(Q,SRF) in [("highQ",(1000,2000)),("realQ60",(60,200))]:
    d=run("env_"+tag,LnH=1200,Cp=33,CTp=5.5,Q=Q,SRF=SRF,stop_us=600)
    if d is None: print(tag,"FAILED"); continue
    t=d['time']; e=d['v(e)']
    print("\n%s  (Q=%d, SRF=%d MHz)  Rs=%.2f ohm"%(tag,Q,SRF,2*math.pi*F0*1200e-9/Q))
    for a,b in [(0,100),(100,200),(200,300),(300,400),(400,500),(500,600)]:
        m=(t>=a*1e-6)&(t<b*1e-6)
        if m.sum()<100: continue
        print("   %3d-%3d us : Vpp=%10.6f V"%(a,b,np.ptp(e[m])))


# -*- coding: utf-8 -*-
"""Harness now validated by positive controls. Re-test LC with LONG window (3 ms) and
   the same criteria that let the crystal pass. Also try strong feedback ratios."""
from pathlib import Path
import subprocess, math, json
import numpy as np
EXE=Path('D:/ms_xsp/s04_crosscheck_20261017/Spice64/bin/ngspice_con.exe')
ROOT=Path(r'D:\实验报告文件夹\电路2\tmp\lc02'); WORK=ROOT/'work'
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
    return {n:a[:,i] for i,n in enumerate(names)}
def go(nm,src):
    (ROOT/'cir'/(nm+'.cir')).write_text(src,encoding='ascii')
    (WORK/(nm+'.cir')).write_text(src,encoding='ascii')
    raw=WORK/(nm+'.raw')
    if raw.exists(): raw.unlink()
    subprocess.run([str(EXE),'-b','-n','-o',str(WORK/(nm+'.log')),str(WORK/(nm+'.cir'))],
                   cwd=WORK,capture_output=True,timeout=900,creationflags=subprocess.CREATE_NO_WINDOW)
    if not raw.exists(): return None
    d=readraw(raw); t=d['time']; e=d['v(e)']; stop=t[-1]
    wins=[float(np.ptp(e[(t>=a*stop)&(t<(a+0.05)*stop)])) for a in
          [0.02,0.1,0.2,0.35,0.5,0.65,0.8,0.9,0.97]]
    return wins,d
def build(nm,R1,R2,RE,C1,C2,LnH,Q,SRF,CTp=0.5,load=True):
    L=LnH*1e-9; Rs=2*math.pi*F0*L/Q; CP=1.0/((2*math.pi*SRF*1e6)**2*L)
    ld="RLOAD e 0 2000\nCLOAD e 0 10p" if load else ""
    return f'''* LC-02 long window | div {R1}/{R2} RE={RE} C1={C1} C2={C2} L={LnH} Q={Q}
VSUP vcc 0 PWL(0 0 1u 5)
R1 vcc b {R1}
R2 b 0 {R2}
Q1 vcc b e 2N3904
R3 e 0 {RE}
C1 b e {C1}p
C2 e 0 {C2}p
CT e 0 {CTp}p
CBLK b nL 1000p
LR nL n1 {Rs:.6f}
L1 n1 0 {LnH}n
CP n1 0 {CP:.9f}
C3 vcc 0 100n
C4 vcc 0 10u
{ld}
{MDL}
.options method=trap maxord=2 reltol=1e-3 trtol=7 temp=27 tnom=27
.control
set filetype=binary
set num_threads=1
save v(vcc) v(b) v(e) i(vsup)
tran 0.25n 3000u 0 0.25n uic
write {nm}.raw
quit
.endc
.end
'''
print("=== LC, 3000 us window, same criteria the crystal passed ===")
print("%-30s %7s %7s %7s %7s %7s %7s %7s %7s %7s"%("config","2%","10%","20%","35%","50%","65%","80%","90%","97%"))
cfgs=[
 ("orig 10k/10k RE4.7k C33/33","10000","10000","4.7k",33,33),
 ("RE220 10k/10k C33/33","10000","10000","220",33,33),
 ("RE220 10k/10k C220/33","10000","10000","220",220,33),
 ("RE220 10k/10k C470/33","10000","10000","220",470,33),
 ("RE470 22k/10k C100/100","22000","10000","470",100,100),
]
for tag,R1,R2,RE,C1,C2 in cfgs:
    nm="L3_"+str(abs(hash(tag))%99999)
    r=go(nm,build(nm,R1,R2,RE,C1,C2,1280.07,60,200))
    if r is None: print("%-30s FAILED"%tag); continue
    w,_=r
    print("%-30s %7.4f %7.4f %7.4f %7.4f %7.4f %7.4f %7.4f %7.4f %7.4f"%(tag,*w))

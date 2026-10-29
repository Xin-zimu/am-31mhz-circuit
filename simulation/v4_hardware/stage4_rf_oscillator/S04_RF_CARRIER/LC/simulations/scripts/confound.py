
# -*- coding: utf-8 -*-
"""Controlled: crystal with and without a 2k load on the emitter; and LC likewise (no load)."""
from pathlib import Path
import subprocess, math
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
    return [float(np.ptp(e[(t>=a*stop)&(t<(a+0.05)*stop)])) for a in [0.02,0.1,0.2,0.35,0.5,0.7,0.9]]

cm=10e-15;c0=3e-12;cl=18e-12
fs=31e6/math.sqrt(1+cm/(cl+c0));lm=1/((2*math.pi*fs)**2*cm)
def build(nm,branch,load):
    return f'''* control {nm}
VSUP vcc 0 PWL(0 0 1u 5)
R1 vcc b 10k
R2 b 0 10k
Q1 vcc b e 2N3904
R3 e 0 4.7k
C1 b e 33p
C2 e 0 33p
C3 vcc 0 100n
C4 vcc 0 10u
{branch}
RPROBE e 0 10meg
CPROBE e 0 12p
{load}
{MDL}
.options method=trap maxord=2 reltol=1e-3 trtol=7 temp=27 tnom=27
.control
set filetype=binary
set num_threads=1
save v(vcc) v(b) v(e) i(vsup)
tran 0.25n 1500u 0 0.25n uic
write {nm}.raw
quit
.endc
.end
'''
XTAL=f'''CSTRAY b 0 1p
CX0 b 0 3p
VXM b xr 0
RM xr xl 30
LM xl xc {lm:.16g}
CM xc 0 10f'''
def LC(Q):
    L=1280.07e-9; Rs=2*math.pi*F0*L/Q
    return f'''CBLK b nL 1000p
LR nL n1 {Rs:.6f}
L1 n1 0 1280.07n'''

print("=== emitter v(e) envelope, 1500 us ===")
print("%-24s %8s %8s %8s %8s %8s %8s %8s"%("case","2%","10%","20%","35%","50%","70%","90%"))
cases=[("crystal, no load",XTAL,""),
       ("crystal, 2k||10p",XTAL,"RLOAD e 0 2000\nCLOAD e 0 10p"),
       ("LC Q=1000, no load",LC(1000),""),
       ("LC Q=60, no load",LC(60),""),
       ("LC Q=60, 2k||10p",LC(60),"RLOAD e 0 2000\nCLOAD e 0 10p")]
for tag,br,ld in cases:
    nm="cf_"+str(abs(hash(tag))%99999)
    r=go(nm,build(nm,br,ld))
    if r is None: print("%-24s FAILED"%tag); continue
    print("%-24s %8.4f %8.4f %8.4f %8.4f %8.4f %8.4f %8.4f"%(tag,*r))

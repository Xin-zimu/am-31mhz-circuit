
# -*- coding: utf-8 -*-
"""DECISIVE: is the Rs=0 'oscillation' physical, or a trapezoidal-integration artifact
   on a LOSSLESS tank?  Test: same circuit, integrate with method=gear (numerically damped)."""
from pathlib import Path
import subprocess, math, json
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
    return {n:a[:,i] for i,n in enumerate(names)}

def net(name,Rs,method,maxord,stop_us=300):
    return f'''* artifact test: lossless vs lossy tank, trap vs gear
VSUP vcc 0 PWL(0 0 1u 5)
R1 vcc b 10k
R2 b 0 10k
Q1 vcc b e 2N3904
R3 e 0 4.7k
C1 b e 33p
C2 e 0 33p
CT e 0 0.5p
CBLK b nL 1000p
LR nL n1 {Rs}
L1 n1 0 1280.07n
CP n1 0 0.0p
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
.options method={method} maxord={maxord} reltol=1e-3 trtol=7 temp=27 tnom=27
.control
set filetype=binary
set num_threads=1
save v(vcc) v(out) i(vsup)
tran 0.125n {stop_us}u 0 0.125n uic
write {name}.raw
quit
.endc
.end
'''
def run(name,src):
    (ROOT/'cir'/(name+'.cir')).write_text(src,encoding='ascii')
    (WORK/(name+'.cir')).write_text(src,encoding='ascii')
    raw=WORK/(name+'.raw')
    if raw.exists(): raw.unlink()
    subprocess.run([str(EXE),'-b','-n','-o',str(WORK/(name+'.log')),str(WORK/(name+'.cir'))],
                   cwd=WORK,capture_output=True,timeout=900,creationflags=subprocess.CREATE_NO_WINDOW)
    if not raw.exists(): return None
    d=readraw(raw); t=d['time']; e=d['v(out)']
    def env(a,b):
        m=(t>=a*1e-6)&(t<b*1e-6)
        return np.ptp(e[m]) if m.sum()>50 else float('nan')
    return dict(v0=env(0,20),v1=env(50,70),v2=env(150,170),v3=env(280,300))

print("=== same circuit, different integrator: is Rs=0 'oscillation' physical? ===")
print("%-8s %-14s %10s %10s %10s %10s"%("Rs(Ω)","options","0-20us","50-70us","150-170us","280-300us"))
for Rs,tag in [(0,'0'),(0.001,'1m')]:
    for method,maxord in [("trap",2),("gear",2),("trap",1)]:
        nm="ar_%s_%s_%d"%(tag,method,maxord)
        r=run(nm, net(nm,Rs,method,maxord))
        if r is None: print("  %-8s %-14s FAILED"%(Rs,"%s/%d"%(method,maxord))); continue
        print("%-8s %-14s %10.4f %10.4f %10.4f %10.4f"%(Rs,"%s maxord=%d"%(method,maxord),r['v0'],r['v1'],r['v2'],r['v3']))

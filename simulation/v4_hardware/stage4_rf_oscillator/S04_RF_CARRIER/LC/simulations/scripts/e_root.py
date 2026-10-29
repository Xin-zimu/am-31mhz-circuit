
# -*- coding: utf-8 -*-
"""Root cause test:
   (1) lossless tank rings forever = NOT oscillation (no gain needed)
   (2) bias with real negative resistance (RE=1k) - does it actually GROW from a seed?"""
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
def net(name,RE,Rs,CPp,CTp,ic,stop_us):
    return f'''* root-cause test RE={RE} Rs={Rs} seed={ic}V
VSUP vcc 0 PWL(0 0 1u 5)
R1 vcc b 10k
R2 b 0 10k
Q1 vcc b e 2N3904
R3 e 0 {RE}
C1 b e 33p
C2 e 0 33p
CT e 0 {CTp}p
CBLK b nL 1000p
LR nL n1 {Rs}
L1 n1 0 1280.07n
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
.options method=gear maxord=2 reltol=1e-3 trtol=7 temp=27 tnom=27
.ic v(nL)={ic}
.control
set filetype=binary
set num_threads=1
save v(vcc) v(out) v(nL) i(vsup)
tran 0.25n {stop_us}u 0 0.25n uic
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
    d=readraw(raw); return d
def env(d,key,a,b):
    t=d['time']; e=d[key]; m=(t>=a*1e-6)&(t<b*1e-6)
    return float(np.ptp(e[m])) if m.sum()>50 else float('nan')

print("=== (1) lossless tank, 1.5 ms (gear): does it decay at all? ===")
d=run("rc_lossless", net("rc_lossless","4.7k",0,0.0,0.5,0.01,1500))
if d:
    for a,b in [(10,60),(100,150),(400,450),(700,750),(1000,1050),(1450,1500)]:
        print("   %4d-%4d us : V(out)pp = %.6f"%(a,b,env(d,'v(out)',a,b)))

print("\n=== (2) RE=1k (Re(Z) = -50 ohm at 31 MHz), REAL inductor Q=1000, seeded 10 mV ===")
d=run("rc_re1k", net("rc_re1k","1k",0.249,0.0,0.5,0.01,1500))
if d:
    print("%10s %14s"%("window","V(out)pp"))
    prev=None
    for a in [10,100,300,600,900,1200,1450]:
        v=env(d,'v(out)',a,a+50)
        g="" if prev is None or prev<=0 else " growth x%.2f"%(v/prev)
        print("   %4d-%4d us : %.6f%s"%(a,a+50,v,g)); prev=v

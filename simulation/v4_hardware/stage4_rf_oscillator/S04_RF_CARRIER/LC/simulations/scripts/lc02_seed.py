
# -*- coding: utf-8 -*-
"""Is the 2 mV a seed or just numerical residue? Seed the tank explicitly and watch growth."""
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
def net(name,R1,R2,RE,C1,C2,LnH,Q,SRF,ic,stop_us):
    L=LnH*1e-9; Rs=2*math.pi*F0*L/Q; CP=1.0/((2*math.pi*SRF*1e6)**2*L)
    return f'''* seeded self-excitation test | seed {ic}V on nL
VSUP vcc 0 PWL(0 0 1u 5)
R1 vcc b {R1}
R2 b 0 {R2}
Q1 vcc b e 2N3904
R3 e 0 {RE}
C1 b e {C1}p
C2 e 0 {C2}p
CT e 0 0.5p
CBLK b nL 1000p
LR nL n1 {Rs:.6f}
L1 n1 0 {LnH}n
CP n1 0 {CP:.9f}
C3 vcc 0 100n
C4 vcc 0 10u
COUT e out 1n
RLOAD out 0 2000
CLOAD out 0 10p
{MDL}
.options method=trap maxord=2 reltol=1e-3 trtol=7 temp=27 tnom=27
.ic v(nL)={ic}
.control
set filetype=binary
set num_threads=1
save v(vcc) v(b) v(e) v(out) v(nL) i(vsup)
tran 0.25n {stop_us}u 0 0.25n uic
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
    subprocess.run([str(EXE),'-b','-n','-o',str(WORK/(name+'.log')),str(WORK/(name+'.cir'))],
                   cwd=WORK,capture_output=True,timeout=900,creationflags=subprocess.CREATE_NO_WINDOW)
    if not raw.exists(): return None
    d=readraw(raw); t=d['time']; e=d['v(out)']
    stop=kw['stop_us']*1e-6
    out=[]
    for a in [0.02,0.1,0.2,0.35,0.5,0.7,0.9]:
        m=(t>=a*stop)&(t<(a+0.06)*stop)
        out.append(float(np.ptp(e[m])) if m.sum()>50 else float('nan'))
    return out,d

print("=== does an explicit 1 V tank seed GROW? (Q=60 real inductor) ===")
print("%-28s %9s %9s %9s %9s %9s %9s %9s"%("config","2%","10%","20%","35%","50%","70%","90%"))
for tag,R1,R2,RE,C1,C2 in [
  ("orig RE4.7k 33/33","10000","10000","4.7k",33,33),
  ("RE=220 33/33","10000","10000","220",33,33),
  ("RE=220 C1=220 C2=33","10000","10000","220",220,33),
  ("RE=220 C1=33 C2=220","10000","10000","220",33,220),
]:
    nm="sd_"+str(abs(hash(tag))%99999)
    r=run(nm,R1=R1,R2=R2,RE=RE,C1=C1,C2=C2,LnH=1280.07,Q=60,SRF=200,ic=1.0,stop_us=600)
    if r is None: print("%-28s FAILED"%tag); continue
    w,_=r
    print("%-28s %9.4f %9.4f %9.4f %9.4f %9.4f %9.4f %9.4f"%(tag,*w))

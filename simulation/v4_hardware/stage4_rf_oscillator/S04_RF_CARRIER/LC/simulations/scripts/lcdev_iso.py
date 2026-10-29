
# -*- coding: utf-8 -*-
"""Controlled isolation: what kills the oscillation?"""
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
def build(name,LnH,Cp,CTp,CT_at_e,Rs,CPp,stop_us=600):
    cte = f"CT e 0 {CTp}p" if CT_at_e else ""
    ctn = "" if CT_at_e else f"CT n1 0 {CTp}p"
    return f'''* isolation
VSUP vcc 0 PWL(0 0 1u 5)
R1 vcc b 10k
R2 b 0 10k
Q1 vcc b e 2N3904
R3 e 0 4.7k
C1 b e {Cp}p
C2 e 0 {Cp}p
{cte}
CBLK b nL 1000p
LR nL n1 {Rs}
L1 n1 0 {LnH}n
CP n1 0 {CPp}p
{ctn}
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
cases=[
 ("isoA_ideal",   dict(LnH=1280.07,Cp=33,CTp=0.5,CT_at_e=True, Rs=0,      CPp=0,      )),
 ("isoB_Rs3p9",   dict(LnH=1280.07,Cp=33,CTp=0.5,CT_at_e=True, Rs=3.9,    CPp=0,      )),
 ("isoC_Rs0p23",  dict(LnH=1280.07,Cp=33,CTp=0.5,CT_at_e=True, Rs=0.23,   CPp=0,      )),
 ("isoD_Rs0p01",  dict(LnH=1280.07,Cp=33,CTp=0.5,CT_at_e=True, Rs=0.01,   CPp=0,      )),
 ("isoE_Rs3p9_noQ",dict(LnH=1280.07,Cp=33,CTp=0.5,CT_at_e=True,Rs=3.9,    CPp=0,      )),
]
print("case             Rs(ohm)  envelope(tail Vpp)     f(kHz)")
for n,kw in cases:
    d=run(n,**kw)
    if d is None: print(n,"FAILED"); continue
    t=d['time']; e=d['v(out)']
    m=t>=500e-6
    f=f_of(t[m],e[m]) if m.sum()>100 else None
    print("%-16s %6.2f   %14.6f   %10.2f"%(n,kw['Rs'],np.ptp(e[m]),(f or 0)/1e3))


# -*- coding: utf-8 -*-
"""Is the LC tuned at all? Sweep L with high gm (RE=220) and real Q, 3 ms, look for ANY growth."""
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
    a1=float(np.ptp(e[(t>=0.1*stop)&(t<0.15*stop)]))
    a2=float(np.ptp(e[(t>=0.9*stop)&(t<0.95*stop)]))
    return a1,a2
def build(nm,LnH,RE,C1,C2,Q,R1="10k",R2="10k"):
    L=LnH*1e-9; Rs=2*math.pi*F0*L/Q
    return f'''* LC sweep L={LnH}nH RE={RE} C1={C1} C2={C2} Q={Q}
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
C3 vcc 0 100n
C4 vcc 0 10u
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
print("=== sweep L at RE=220 (Ie~8.6mA), C1=C2=33p, Q=60, 3000us ===")
print("%8s %10s %10s  %s"%("L(nH)","@10%","@90%","判定"))
for L in [800,1000,1280,1600,2000,2600]:
    nm="ls_%d"%L
    r=go(nm,build(nm,L,"220",33,33,60))
    if r is None: print("%8d FAILED"%L); continue
    a1,a2=r
    v = "增长" if a2>a1*1.5 and a2>0.05 else ("衰减" if a2<a1 else "持平")
    print("%8d %10.4f %10.4f  %s"%(L,a1,a2,v))

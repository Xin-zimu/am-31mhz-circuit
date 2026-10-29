
# -*- coding: utf-8 -*-
"""Rs anomaly: decay time constant vs Rs (part 1: Rs sweep)."""
from pathlib import Path
import subprocess, json
import numpy as np

EXE=Path('D:/ms_xsp/s04_crosscheck_20261017/Spice64/bin/ngspice_con.exe')
ROOT=Path(r'D:\实验报告文件夹\电路2\tmp\lc02b')
(ROOT/'cir').mkdir(parents=True,exist_ok=True)
WORK=ROOT/'work'; WORK.mkdir(parents=True,exist_ok=True)
MDL=Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage4_rf_oscillator\advance_20261029\2N3904_UNCG.lib').read_text(encoding='ascii').strip()

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

def build(nm,Rs,reltol="1e-3",tmax="0.25n",stop=600,seed=0.02):
    return f'''* Rs anomaly | Rs={Rs}
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
C3 vcc 0 100n
C4 vcc 0 10u
{MDL}
.options method=trap maxord=2 reltol={reltol} trtol=7 temp=27 tnom=27
.ic v(nL)={seed}
.control
set filetype=binary
set num_threads=1
save v(nL)
tran {tmax} {stop}u 0 {tmax} uic
write {nm}.raw
quit
.endc
.end
'''

def go(nm,src):
    (ROOT/'cir'/(nm+'.cir')).write_text(src,encoding='ascii')
    (WORK/(nm+'.cir')).write_text(src,encoding='ascii')
    raw=WORK/(nm+'.raw')
    if raw.exists(): raw.unlink()
    subprocess.run([str(EXE),'-b','-n','-o',str(WORK/(nm+'.log')),str(WORK/(nm+'.cir'))],
                   cwd=WORK,capture_output=True,timeout=400,creationflags=subprocess.CREATE_NO_WINDOW)
    return readraw(raw) if raw.exists() else None

def amp_bins(t,v,width=5e-6):
    out=[]
    for a in np.arange(0,t[-1]-width,width):
        m=(t>=a)&(t<a+width)
        if m.sum()>20: out.append((a+width/2, float(np.ptp(v[m]))/2))
    return out

def tau_of(amp):
    A=np.array([x for x in amp if x[1]>1e-9])
    if len(A)<8: return None,(amp[0][1] if amp else 0.0)
    a0=A[0,1]
    sel=(A[:,1]>a0*0.02)&(A[:,1]<a0*0.5)
    if sel.sum()<5: return None,a0
    p=np.polyfit(A[sel,0],np.log(A[sel,1]),1)
    return (-1.0/p[0] if p[0]<0 else None),a0

print("=== decay time constant vs Rs (seed 20 mV, 600 us) ===")
print("%-12s %10s %12s %14s"%("Rs","amp@0","tau(us)","amp@end"))
rows=[]
for Rs in [0,1e-6,1e-5,1e-4,1e-3,0.01,0.1,1.0,3.9]:
    nm="ra_"+str(Rs).replace('.','p').replace('-','m')
    d=go(nm,build(nm,Rs))
    if d is None:
        print("%-12g FAILED"%Rs); continue
    t=d['time']; v=d['v(nl)']
    amp=amp_bins(t,v); tau,a0=tau_of(amp)
    last=amp[-1][1] if amp else 0.0
    print("%-12.6g %10.4f %12s %14.4g"%(Rs,a0,("%.2f"%tau) if tau else "n/a",last))
    rows.append(dict(Rs=Rs,a0=a0,tau_us=tau,last=last))
(ROOT/'anomaly.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print("\nsaved")

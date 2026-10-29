
# -*- coding: utf-8 -*-
"""Rs anomaly part 2: NO uic. Start at DC op, settle, then inject a small current pulse.
   Envelope of the ring-down/growth is fitted. Monotonic tau(Rs) => physics; non-monotonic => numerics."""
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

def build(nm,Rs,R1="10k",R2="10k",RE="4.7k",C1=33,C2=33,amp="5m",
          kick_us=150,stop=320,tmax="0.25n",L="1280.07n"):
    return f'''* punch test | Rs={Rs} div={R1}/{R2} RE={RE} C={C1}/{C2}
VSUP vcc 0 5
R1 vcc b {R1}
R2 b 0 {R2}
Q1 vcc b e 2N3904
R3 e 0 {RE}
C1 b e {C1}p
C2 e 0 {C2}p
CT e 0 0.5p
CBLK b nL 1000p
LR nL n1 {Rs}
L1 n1 0 {L}
C3 vcc 0 100n
C4 vcc 0 10u
IP nL 0 PULSE(0 {amp} {kick_us}u 2n 2n 2n 1)
{MDL}
.options method=trap maxord=2 reltol=1e-3 trtol=7 temp=27 tnom=27
.control
set filetype=binary
set num_threads=1
save v(nL) v(e) v(b)
tran {tmax} {stop}u 0 {tmax}
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

def env_after(t,v,t0,width=1.0e-6):
    out=[]
    a=t0
    while a < t[-1]-width:
        m=(t>=a)&(t<a+width)
        if m.sum()>10: out.append((a+width/2, float(np.ptp(v[m]))/2))
        a+=width
    return out

def rate(env,frac=0.15):
    A=np.array([x for x in env if x[1]>1e-9])
    if len(A)<10: return None,None
    a0=A[0,1]
    sel=(A[:,1]>a0*0.02)&(A[:,1]<a0*0.9)
    if sel.sum()<5: return None,a0
    p=np.polyfit(A[sel,0],np.log(A[sel,1]),1)
    return float(p[0]),float(a0)   # slope 1/s : >0 growth, <0 decay

print("=== punch test at settled DC op (kick at 150us, state sampled to 320us) ===")
print("%-10s %10s %14s %14s"%("Rs","amp@kick","slope(1/s)","tau or growth"))
rows=[]
for Rs in [0,1e-4,1e-3,1e-2,0.1,1.0,3.9]:
    nm="pn_"+str(Rs).replace('.','p').replace('-','m')
    d=go(nm,build(nm,Rs))
    if d is None: print("%-10g FAILED"%Rs); continue
    t=d['time']; v=d['v(nl)']
    e=env_after(t,v,152e-6)
    s,a0=rate(e)
    if s is None: print("%-10.6g %10.4g  (no usable envelope)"%(Rs,a0 or 0)); continue
    desc = ("增长 τ=%.1f us"%(-1/s/1e-6)) if s>0 else ("衰减 τ=%.1f us"%(-1/s/1e-6))
    print("%-10.6g %10.4f %14.3e %14s"%(Rs,a0,s,desc))
    rows.append(dict(Rs=Rs,a0=a0,slope=s))
(ROOT/'anomaly_punch.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print("\nsaved")

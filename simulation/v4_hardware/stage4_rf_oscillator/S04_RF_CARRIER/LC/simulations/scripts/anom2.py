
# -*- coding: utf-8 -*-
"""DECISIVE anomaly closure:
   (A) same Rs, different integrator/tolerance -> amplitude changes?
       If yes at Rs=0 but no at Rs=1m, Rs=0 is a numerical artifact and there is NO physical threshold.
   (B) LC redesign: base driven through high impedance (RFC-like), not a hard 10k/10k divider."""
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
        a=np.fromfile(f,dtype='<f8')
    if len(a)%len(names)!=0:
        a=a[:(len(a)//len(names))*len(names)]
    a=a.reshape(-1,len(names))
    return {n:a[:,i] for i,n in enumerate(names)}

def go(nm,src):
    (ROOT/'cir'/(nm+'.cir')).write_text(src,encoding='ascii')
    (WORK/(nm+'.cir')).write_text(src,encoding='ascii')
    raw=WORK/(nm+'.raw')
    if raw.exists(): raw.unlink()
    subprocess.run([str(EXE),'-b','-n','-o',str(WORK/(nm+'.log')),str(WORK/(nm+'.cir'))],
                   cwd=WORK,capture_output=True,timeout=400,creationflags=subprocess.CREATE_NO_WINDOW)
    if not raw.exists(): return None
    d=readraw(raw)
    try: raw.unlink()
    except: pass
    return d

BASE='''VSUP vcc 0 5
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
'''

def net(nm,Rs,method,maxord,reltol,R1="10k",R2="10k",RE="4.7k",C1=33,C2=33,
        L="1280.07n",stop=300):
    return ("* anomaly/redesign | Rs=%s %s\n"%(Rs,method)
      + BASE.format(R1=R1,R2=R2,RE=RE,C1=C1,C2=C2,Rs=Rs,L=L)
      + MDL + f'''
.options method={method} maxord={maxord} reltol={reltol} trtol=7 temp=27 tnom=27
.control
set filetype=binary
set num_threads=1
save v(nL) v(e) v(b)
tran 0.25n {stop}u 0 0.25n uic
write {nm}.raw
quit
.endc
.end
''')

def tail_amp(d,frac0=0.8):
    t=d['time']; v=d['v(nl)']
    m=t>=frac0*t[-1]
    return float(np.ptp(v[m]))/2 if m.sum()>50 else float('nan')
def fb(d):
    t=d['time']; v=d['v(e)']
    m=t>=0.8*t[-1]
    if m.sum()<50: return float('nan'),None
    e=v[m]; tt=t[m]
    dc=float(np.trapezoid(e,tt)/(tt[-1]-tt[0])); x=e-dc
    idx=np.where((x[:-1]<=0)&(x[1:]>0))[0]
    f=None
    if len(idx)>10:
        cr=tt[idx]-x[idx]*(tt[idx+1]-tt[idx])/(x[idx+1]-x[idx])
        f=float((len(cr)-1)/(cr[-1]-cr[0]))
    return float(np.ptp(e)),f

print("=== (A) integrator/tolerance sensitivity: same Rs, different numerics ===")
print("%-8s %-16s %12s"%("Rs","numerics","amp@nL(end)"))
resA={}
for Rs in [0,1e-3]:
    for method,maxord,reltol in [("trap",2,"1e-3"),("trap",1,"1e-3"),("gear",2,"1e-3"),
                                 ("trap",2,"1e-4"),("trap",2,"1e-5")]:
        nm="A_%s_%s%d_%s"%(str(Rs).replace('.','p'),method,maxord,reltol.replace('.','p').replace('-','m'))
        d=go(nm,net(nm,Rs,method,maxord,reltol))
        if d is None: print("%-8g %-16s FAILED"%(Rs,"%s/%d/%s"%(method,maxord,reltol))); continue
        a=tail_amp(d)
        print("%-8g %-16s %12.4f"%(Rs,"%s maxord%d rt%s"%(method,maxord,reltol),a))
        resA["%s_%s_%d_%s"%(Rs,method,maxord,reltol)]=a
(ROOT/'anomaly_numerics.json').write_text(json.dumps(resA,indent=2),encoding='utf-8')
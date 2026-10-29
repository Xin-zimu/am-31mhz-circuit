
# -*- coding: utf-8 -*-
"""Minimal reproduction: identical perturbation, sweep Rs, measure envelope growth rate.
   Plus: DC operating point per Rs, and small-signal negative resistance at the tank node."""
from pathlib import Path
import subprocess, math, json
import numpy as np
EXE=Path('D:/ms_xsp/s04_crosscheck_20261017/Spice64/bin/ngspice_con.exe')
ROOT=Path(r'D:\实验报告文件夹\电路2\tmp\lcdev'); WORK=ROOT/'work'
MDL=Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage4_rf_oscillator\advance_20261029\2N3904_UNCG.lib').read_text(encoding='ascii').strip()
F0=31e6

def readraw(p):
    with open(p,'rb') as f:
        names=[];inside=False;flags=""
        while True:
            s=f.readline().decode('ascii').strip()
            if s=='Binary:':break
            if s.startswith('Flags:'):flags=s
            if s=='Variables:':inside=True;continue
            if inside and s:names.append(s.split()[1].lower())
        a=np.fromfile(f,dtype='<f8')
    if 'complex' in flags:
        a=a.reshape(-1,len(names),2); z=a[:,:,0]+1j*a[:,:,1]
    else:
        z=a.reshape(-1,len(names))
    return {n:z[:,i] for i,n in enumerate(names)}

# ---------- perturbation transient ----------
def pert_net(name,Rs,ic_v,stop_us=400):
    return f'''* minimal repro: identical 10 mV tank perturbation, only Rs changes
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
{MDL}
.options method=trap maxord=2 reltol=1e-3 trtol=7 temp=27 tnom=27
.ic v(nL)={ic_v}
.control
set filetype=binary
set num_threads=1
save v(b) v(e) v(nL)
tran 0.125n {stop_us}u 0 0.125n uic
write {name}.raw
quit
.endc
.end
'''
def run(name,src,**kw):
    (ROOT/'cir'/(name+'.cir')).write_text(src,encoding='ascii')
    (WORK/(name+'.cir')).write_text(src,encoding='ascii')
    raw=WORK/(name+'.raw')
    if raw.exists(): raw.unlink()
    subprocess.run([str(EXE),'-b','-n','-o',str(WORK/(name+'.log')),str(WORK/(name+'.cir'))],
                   cwd=WORK,capture_output=True,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
    return (readraw(raw) if raw.exists() else None)

def envelope(t,e,w=10e-6):
    out=[]
    for a in np.arange(0,t[-1]-w,w):
        m=(t>=a)&(t<a+w)
        if m.sum()<50: continue
        out.append((a+w/2, (np.ptp(e[m]) if np.ptp(e[m])>0 else 1e-12)))
    return out

print("=== minimal repro: same 10 mV perturbation at nL, only Rs differs ===")
print("%-8s %10s %10s %10s  %s"%("Rs","0-10us","100-110us","390-400us","trend"))
base=None
for Rs,tag in [(0,'0'),(0.001,'1m'),(0.01,'10m'),(0.1,'100m'),(1.0,'1'),(3.9,'3p9')]:
    d=run('pt_'+tag, pert_net('pt_'+tag,Rs,0.01))
    if d is None: print("  %-8s FAILED"%Rs); continue
    t=d['time']; e=d['v(nl)']
    env=envelope(t,e)
    if not env: print("  %-8s no data"%Rs); continue
    first=env[0][1]; mid=[v for (tt,v) in env if 0.1e-3<=tt<0.11e-3]; last=env[-1][1]
    growth = (np.log(last)-np.log(first))/t[-1]
    tr = "增长" if growth>0 else "衰减"
    print("%-8s %10.3e %10.3e %10.3e  %s (%+.3e 1/s)"%(Rs,first,mid[0] if mid else float('nan'),last,tr,growth))

# ---------- DC operating point per Rs ----------
def op_net(name,Rs):
    return f'''* DC operating point vs Rs
VSUP vcc 0 5
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
{MDL}
.control
op
print v(b) v(e) @r3[i]
quit
.endc
.end
'''
print("\n=== DC operating point vs Rs (must be identical) ===")
for Rs,tag in [(0,'0'),(0.001,'1m'),(3.9,'3p9')]:
    src=op_net('op_'+tag,Rs)
    (ROOT/'cir'/('op_'+tag+'.cir')).write_text(src,encoding='ascii')
    (WORK/('op_'+tag+'.cir')).write_text(src,encoding='ascii')
    subprocess.run([str(EXE),'-b','-n','-o',str(WORK/('op_'+tag+'.log')),str(WORK/('op_'+tag+'.cir'))],
                   cwd=WORK,capture_output=True,timeout=300,creationflags=subprocess.CREATE_NO_WINDOW)
    txt=(WORK/('op_'+tag+'.log')).read_text(errors='replace')
    kv={}
    for l in txt.splitlines():
        p=l.split()
        if len(p)>=3 and p[1]=='=':
            try: kv[p[0]]=float(p[2])
            except: pass
    vb=kv.get('op1.v(b)'); ve=kv.get('op1.v(e)'); ie=kv.get('op1.@r3[i]')
    print("  Rs=%-6s Vb=%.6f Ve=%.6f Ie=%.6f mA = %.6f mA"%(Rs,vb,ve,ie,(ie or 0)*1e3))


# -*- coding: utf-8 -*-
"""S04-LC-02 step 2-4: bias redesign + genuine self-excitation test.
   Port-free criterion: REAL lossy inductor + UIC cold start + envelope must GROW and SUSTAIN."""
from pathlib import Path
import subprocess, math, json, time
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

def net(name,R1,R2,RE,C1,C2,LnH,Q,SRF,stop_us=600,CTp=0.5):
    L=LnH*1e-9
    Rs=2*math.pi*F0*L/Q
    CP=1.0/((2*math.pi*SRF*1e6)**2*L)
    return f'''* LC-02 self-excitation | div {R1}/{R2} RE={RE} C1={C1}p C2={C2}p | L={LnH}nH Q={Q} SRF={SRF}
VSUP vcc 0 PWL(0 0 1u 5)
R1 vcc b {R1}
R2 b 0 {R2}
Q1 vcc b e 2N3904
R3 e 0 {RE}
C1 b e {C1}p
C2 e 0 {C2}p
CT e 0 {CTp}p
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
.control
set filetype=binary
set num_threads=1
save v(vcc) v(b) v(e) v(out) i(vsup)
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
    wins=[]
    stop=kw.get('stop_us',600)*1e-6
    for a in [0.1,0.2,0.3,0.4,0.5,0.55]:
        m=(t>=a*stop)&(t<(a+0.05)*stop)
        wins.append(float(np.ptp(e[m])) if m.sum()>50 else float('nan'))
    # frequency from last 10%
    m=t>=0.9*stop
    tt=t[m]; ee=e[m]
    dc=float(np.trapezoid(ee,tt)/(tt[-1]-tt[0])); v=ee-dc
    idx=np.where((v[:-1]<=0)&(v[1:]>0))[0]
    f=None
    if len(idx)>10:
        cr=tt[idx]-v[idx]*(tt[idx+1]-tt[idx])/(v[idx+1]-v[idx])
        f=float((len(cr)-1)/(cr[-1]-cr[0]))
    return dict(wins=wins,freq_hz=f,vpp_final=float(np.ptp(ee)),dc=dc,
                supply_mw=float(-np.trapezoid(d['v(vcc)']*d['i(vsup)'],t)/(t[-1]-t[0])*1e3),
                vb=float(np.mean(d['v(b)'][m])),ve=float(np.mean(d['v(e)'][m])))

print("=== bias redesign, REAL inductor Q=60, UIC cold start, 600 us ===")
print("%-26s %8s %8s %8s %8s %8s %8s  %9s %s"%("config","10%","20%","30%","40%","50%","55%","f(kHz)","判定"))
cfgs=[
 ("orig 10k/10k RE4.7k 33/33","10000","10000","4.7k",33,33),
 ("RE1k  10k/10k 33/33","10000","10000","1k",33,33),
 ("RE220 10k/10k 33/33","10000","10000","220",33,33),
 ("RE1k  10k/3.3k 33/33","10000","3300","1k",33,33),
 ("RE220 10k/3.3k 33/33","10000","3300","220",33,33),
 ("RE1k  22k/10k 33/33","22000","10000","1k",33,33),
 ("RE220 22k/3.3k 33/33","22000","3300","220",33,33),
]
out={}
for tag,R1,R2,RE,C1,C2 in cfgs:
    nm="sx_"+str(abs(hash(tag))%99999)
    r=run(nm,R1=R1,R2=R2,RE=RE,C1=C1,C2=C2,LnH=1280.07,Q=60,SRF=200)
    if r is None: print("%-26s FAILED"%tag); continue
    w=r['wins']
    grow = w[-1] > 0.05 and w[-1] > w[0]*1.2
    verdict = "起振" if grow else ("衰减" if w[-1]<0.05 else "不稳定")
    print("%-26s %8.4f %8.4f %8.4f %8.4f %8.4f %8.4f  %9.1f %s"%(
        tag,w[0],w[1],w[2],w[3],w[4],w[5],(r['freq_hz'] or 0)/1e3,verdict))
    out[tag]=r
(ROOT/'step2.json').write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding='utf-8')

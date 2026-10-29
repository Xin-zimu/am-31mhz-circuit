
# -*- coding: utf-8 -*-
"""Crystal oscillator + same emitter follower + same load (the missing matrix cell)."""
from pathlib import Path
import json, subprocess, math
import numpy as np
EXE=Path('D:/ms_xsp/s04_crosscheck_20261017/Spice64/bin/ngspice_con.exe')
WORK=Path(r'D:\实验报告文件夹\电路2\tmp\lc_study\work'); OUT=Path(r'D:\实验报告文件夹\电路2\tmp\lc_study')
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
    if len(idx)<10: return None,dc
    cr=t[idx]-v[idx]*(t[idx+1]-t[idx])/(v[idx+1]-v[idx])
    return float((len(cr)-1)/(cr[-1]-cr[0])),dc

cm=10e-15; c0=3e-12; cl=18e-12
fs=31e6/math.sqrt(1+cm/(cl+c0)); lm=1/((2*math.pi*fs)**2*cm)

def build(name,extra):
    return f'''* Crystal Colpitts 31 MHz + emitter follower + real load
VSUP vcc 0 PWL(0 0 1u 5)
R1 vcc b 10k
R2 b 0 10k
Q1 vcc b e 2N3904
R3 e 0 4.7k
C1 b e 33p
C2 e 0 33p
C3 vcc 0 100n
C4 vcc 0 10u
CSTRAY b 0 1p
CX0 b 0 {c0*1e12}p
VXM b xr 0
RM xr xl 30
LM xl xc {lm:.16g}
CM xc 0 {cm*1e15}f
{extra}
{MDL}
.options method=trap maxord=2 reltol=1e-3 trtol=7 temp=27 tnom=27
.control
set filetype=binary
set num_threads=1
save v(vcc) v(b) v(e) v(out) i(vsup) i(vxm)
tran 0.125n 1000u 900u 0.125n uic
write {name}.raw
quit
.endc
.end
'''
def run(name,extra):
    src=build(name,extra)
    (OUT/(name+'.cir')).write_text(src,encoding='ascii')
    (WORK/(name+'.cir')).write_text(src,encoding='ascii')
    raw=WORK/(name+'.raw')
    if raw.exists(): raw.unlink()
    subprocess.run([str(EXE),'-b','-n','-o',str(WORK/(name+'.log')),str(WORK/(name+'.cir'))],
                   cwd=WORK,capture_output=True,timeout=900,creationflags=subprocess.CREATE_NO_WINDOW)
    return readraw(raw) if raw.exists() else None

BUF="CIN e bf 1n\nRBT vcc bf 10k\nRBB bf 0 10k\nQB vcc bf ef 2N3904\nREB ef 0 330\nCOUT ef out 1n\nRLOAD out 0 2000\nCLOAD out 0 10p"
rows=[]
for n,ex,key,desc in [("xtalE_noload",'', 'v(e)',"空载"),
                      ("xtalE_buffered_2k",BUF,'v(out)',"经射随器 2 kΩ∥10 pF")]:
    d=run(n,ex)
    if d is None: print(n,"FAILED"); continue
    t=d['time']; e=d[key]
    f,dc=f_of(t,e)
    mm=t>=0.9e-3
    P=float(-np.trapezoid(d['v(vcc)']*d['i(vsup)'],t)/(t[-1]-t[0])*1e3)
    rows.append(dict(name=n,desc=desc,freq_hz=f,err_ppm=(f/F0-1)*1e6,vpp=float(np.ptp(e[mm])),dc=dc,supply_mw=P))
    print("%-20s f=%9.3f kHz  err=%+9.0f ppm (%+.4f%%)  Vpp=%7.4f  dc=%6.3f  P=%5.2f mW"
          %(n,f/1e3,(f/F0-1)*1e6,(f/F0-1)*100,np.ptp(e[mm]),dc,P))
(OUT/'xtal_load.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False),encoding='utf-8')
print("saved")

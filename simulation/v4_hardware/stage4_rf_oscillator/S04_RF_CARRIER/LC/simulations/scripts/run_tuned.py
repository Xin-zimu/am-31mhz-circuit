
# -*- coding: utf-8 -*-
"""Can LC be tuned IN CIRCUIT (loaded) to 31 MHz? And how far does it drift with temperature?"""
from pathlib import Path
import json, subprocess
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
BUF="CIN e bf 1n\nRBT vcc bf 10k\nRBB bf 0 10k\nQB vcc bf ef 2N3904\nREB ef 0 330\nCOUT ef out 1n\nRLOAD out 0 2000\nCLOAD out 0 10p"
def build(name,L,temp):
    return f'''* LC Colpitts, tuned WITH the load connected
VSUP vcc 0 PWL(0 0 1u 5)
R1 vcc b 10k
R2 b 0 10k
Q1 vcc b e 2N3904
R3 e 0 4.7k
C1 b e 33p
C2 e 0 33p
CT e 0 0.5p
CBLK b nL 1000p
L1 nL 0 {L}u
C3 vcc 0 100n
C4 vcc 0 10u
{BUF}
{MDL}
.options method=trap maxord=2 reltol=1e-3 trtol=7 temp={temp} tnom=27
.control
set filetype=binary
set num_threads=1
save v(vcc) v(b) v(e) v(out) i(vsup)
tran 0.125n 1000u 900u 0.125n uic
write {name}.raw
quit
.endc
.end
'''
def run(name,L,temp=27):
    src=build(name,L,temp)
    (OUT/(name+'.cir')).write_text(src,encoding='ascii')
    (WORK/(name+'.cir')).write_text(src,encoding='ascii')
    raw=WORK/(name+'.raw')
    if raw.exists(): raw.unlink()
    subprocess.run([str(EXE),'-b','-n','-o',str(WORK/(name+'.log')),str(WORK/(name+'.cir'))],
                   cwd=WORK,capture_output=True,timeout=900,creationflags=subprocess.CREATE_NO_WINDOW)
    return readraw(raw) if raw.exists() else None
# loaded freq was 30.292857 MHz at L=1.34053 -> rescale
L = round(1.34053*(30292.857/31000.0)**2, 5)
print("in-circuit tuned L = %.5f uH" % L)
rows=[]
for n,T in [("lcF_tuned_27C",27),("lcF_tuned_0C",0),("lcF_tuned_50C",50)]:
    d=run(n,L,T)
    if d is None: print(n,"FAILED"); continue
    t=d['time']; e=d['v(out)']
    f,dc=f_of(t,e); mm=t>=0.9e-3
    rows.append(dict(name=n,temp=T,L_uH=L,freq_hz=f,err_ppm=(f/F0-1)*1e6,vpp=float(np.ptp(e[mm])),dc=dc))
    print("%-14s T=%2dC  f=%9.3f kHz  err=%+9.0f ppm (%+.4f%%)  Vpp=%7.4f"%(
        n,T,f/1e3,(f/F0-1)*1e6,(f/F0-1)*100,np.ptp(e[mm])))
(OUT/'lc_tuned_loaded.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False),encoding='utf-8')
print("saved")

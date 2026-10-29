
# -*- coding: utf-8 -*-
"""Does the LC oscillator drive the real load? direct vs through emitter follower."""
from pathlib import Path
import json, subprocess
import numpy as np
EXE=Path('D:/ms_xsp/s04_crosscheck_20261017/Spice64/bin/ngspice_con.exe')
WORK=Path(r'D:\实验报告文件夹\电路2\tmp\lc_study\work'); OUT=Path(r'D:\实验报告文件夹\电路2\tmp\lc_study')
MDL=Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage4_rf_oscillator\advance_20261029\2N3904_UNCG.lib').read_text(encoding='ascii').strip()
F0=31e6; Lt=1.3068
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
def m(t,e):
    dc=float(np.trapezoid(e,t)/(t[-1]-t[0])); v=e-dc
    idx=np.where((v[:-1]<=0)&(v[1:]>0))[0]
    f=None
    if len(idx)>10:
        cr=t[idx]-v[idx]*(t[idx+1]-t[idx])/(v[idx+1]-v[idx]); f=float((len(cr)-1)/(cr[-1]-cr[0]))
    return f,dc,float(np.ptp(e))
def build(name,extra):
    return f'''* LC Colpitts 31 MHz + load study
VSUP vcc 0 PWL(0 0 1u 5)
R1 vcc b 10k
R2 b 0 10k
Q1 vcc b e 2N3904
R3 e 0 4.7k
C1 b e 33p
C2 e 0 33p
CT e 0 0.5p
CBLK b nL 1000p
L1 nL 0 {Lt}u
C3 vcc 0 100n
C4 vcc 0 10u
{extra}
{MDL}
.options method=trap maxord=2 reltol=1e-3 trtol=7 temp=27 tnom=27
.control
set filetype=binary
set num_threads=1
save v(vcc) v(b) v(e) v(out) i(vsup)
tran 0.0625n 200u 150u 0.0625n uic
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
                   cwd=WORK,capture_output=True,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
    return readraw(raw) if raw.exists() else None

cases={
 "lcC_noload": "",
 "lcC_direct_2k": "CCO e out 1n\nRLOAD out 0 2000\nCLOAD out 0 10p",
 "lcC_buffered_2k": "CIN e bf 1n\nRBT vcc bf 10k\nRBB bf 0 10k\nQB vcc bf ef 2N3904\nREB ef 0 330\nCOUT ef out 1n\nRLOAD out 0 2000\nCLOAD out 0 10p",
 "lcC_buffered_10k": "CIN e bf 1n\nRBT vcc bf 10k\nRBB bf 0 10k\nQB vcc bf ef 2N3904\nREB ef 0 330\nCOUT ef out 1n\nRLOAD out 0 10000\nCLOAD out 0 10p",
}
rows=[]
for n,ex in cases.items():
    d=run(n,ex)
    if d is None: print(n,"FAILED"); continue
    f,dc,vpp=m(d['time'],d['v(out)'] if 'v(out)' in d else d['v(e)'])
    _,_,ve=m(d['time'],d['v(e)'])
    P=float(-np.trapezoid(d['v(vcc)']*d['i(vsup)'],d['time'])/(d['time'][-1]-d['time'][0])*1e3)
    rows.append(dict(name=n,freq_hz=f,err_ppm=(f/F0-1)*1e6 if f else None,out_vpp=vpp,out_dc=dc,emitter_vpp=ve,supply_mw=P))
    print("%-18s f=%9.3f kHz  Vout=%7.4f Vpp  Vout_dc=%6.3f  Ve=%7.4f Vpp  P5V=%5.2f mW"%(n,(f or 0)/1e3,vpp,dc,ve,P))
(OUT/'lc_load.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False),encoding='utf-8')
print("saved")
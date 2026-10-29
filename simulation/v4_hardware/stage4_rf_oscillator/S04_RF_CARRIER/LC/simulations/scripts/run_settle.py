
# -*- coding: utf-8 -*-
"""LC settling check: same circuits, 1 ms, frequency in successive windows."""
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
def f_of(t,e):
    dc=float(np.trapezoid(e,t)/(t[-1]-t[0])); v=e-dc
    idx=np.where((v[:-1]<=0)&(v[1:]>0))[0]
    if len(idx)<10: return None
    cr=t[idx]-v[idx]*(t[idx+1]-t[idx])/(v[idx+1]-v[idx])
    return float((len(cr)-1)/(cr[-1]-cr[0]))
def build(name,extra,stop_us=1000,save_us=900):
    return f'''* LC Colpitts 31 MHz - settling check
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
tran 0.125n {stop_us}u {save_us}u 0.125n uic
write {name}.raw
quit
.endc
.end
'''
def run(name,extra,**kw):
    src=build(name,extra,**kw)
    (OUT/(name+'.cir')).write_text(src,encoding='ascii')
    (WORK/(name+'.cir')).write_text(src,encoding='ascii')
    raw=WORK/(name+'.raw')
    if raw.exists(): raw.unlink()
    subprocess.run([str(EXE),'-b','-n','-o',str(WORK/(name+'.log')),str(WORK/(name+'.cir'))],
                   cwd=WORK,capture_output=True,timeout=900,creationflags=subprocess.CREATE_NO_WINDOW)
    return readraw(raw) if raw.exists() else None

SPLIT="CCO e out 1n\nRLOAD out 0 2000\nCLOAD out 0 10p"
BUF2K="CIN e bf 1n\nRBT vcc bf 10k\nRBB bf 0 10k\nQB vcc bf ef 2N3904\nREB ef 0 330\nCOUT ef out 1n\nRLOAD out 0 2000\nCLOAD out 0 10p"
rows=[]
for n,ex,key in [("lcD_noload","","v(e)"),("lcD_direct_2k",SPLIT,"v(out)"),("lcD_buffered_2k",BUF2K,"v(out)")]:
    d=run(n,ex)
    if d is None: print(n,"FAILED"); continue
    t=d['time']; e=d[key]
    print("\n%s" % n)
    fr=[]
    for a,b in [(0.900,0.925),(0.925,0.950),(0.950,0.975),(0.975,1.000)]:
        mm=(t>=a*1e-3)&(t<=b*1e-3)
        if mm.sum()<50: continue
        f=f_of(t[mm],e[mm]); fr.append(f)
        print("   %.3f-%.3f ms : f=%9.3f kHz  Vpp=%.4f" % (a,b,(f or 0)/1e3, np.ptp(e[mm])))
    mm=t>=0.9e-3
    fend=f_of(t[mm],e[mm])
    rows.append(dict(name=n,freq_hz=fend,err_ppm=(fend/F0-1)*1e6 if fend else None,
                     vpp=float(np.ptp(e[mm])), dc=float(np.trapezoid(e[mm],t[mm])/(t[mm][-1]-t[mm][0])),
                     drift_hz=(max(fr)-min(fr)) if len(fr)>1 else None))
    if len(fr)>1:
        print("   drift across 4x25us windows: %.0f Hz (%.1f ppm)" % (max(fr)-min(fr),(max(fr)-min(fr))/F0*1e6))
(OUT/'lc_settling.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False),encoding='utf-8')
print("\nsaved")

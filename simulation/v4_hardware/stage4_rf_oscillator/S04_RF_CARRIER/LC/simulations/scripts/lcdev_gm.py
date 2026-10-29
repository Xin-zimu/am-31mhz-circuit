
# -*- coding: utf-8 -*-
"""Can the bias be redesigned so a REAL inductor (finite Q) still oscillates?"""
from pathlib import Path
import json, subprocess, math
import numpy as np
EXE=Path('D:/ms_xsp/s04_crosscheck_20261017/Spice64/bin/ngspice_con.exe')
ROOT=Path(r'D:\实验报告文件夹\电路2\tmp\lcdev'); WORK=ROOT/'work'
MDL=Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage4_rf_oscillator\advance_20261029\2N3904_UNCG.lib').read_text(encoding='ascii').strip()
F0=31e6; LC=1.0/(2*math.pi*F0)**2
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
def build(name,LnH,Cp,CTp,RE,Q,SRF,stop_us=400):
    L=LnH*1e-9; Rs=2*math.pi*F0*L/Q; CPAR=1.0/((2*math.pi*SRF*1e6)**2*L)
    Ctank=LC/(L/(1-(F0/(SRF*1e6))**2))*1e12
    return f'''* LC redesign: RE={RE} CP={Cp}p CT={CTp}p (tank {Ctank:.1f}pF)
VSUP vcc 0 PWL(0 0 1u 5)
R1 vcc b 10k
R2 b 0 10k
Q1 vcc b e 2N3904
R3 e 0 {RE}
C1 b e {Cp}p
C2 e 0 {Cp}p
CBLK b nL 1000p
LR nL n1 {Rs:.6f}
L1 n1 0 {LnH}n
CP n1 0 {CPAR*1e12:.6f}p
CT n1 0 {CTp}p
C3 vcc 0 100n
C4 vcc 0 10u
CIN e bf 1n
RBT vcc bf 10k
RBB bf 0 10k
QB vcc bf ef 2N3904
REB ef 0 330
COUT ef out 1n
RLOAD out 0 2000
CLOAD out 0 10p
{MDL}
.options method=trap maxord=2 reltol=1e-3 trtol=7 temp=27 tnom=27
.control
set filetype=binary
set num_threads=1
save v(vcc) v(b) v(e) v(out) i(vsup)
tran 0.125n {stop_us}u {stop_us-100}u 0.125n uic
write {name}.raw
quit
.endc
.end
'''
def run(name,**kw):
    src=build(name,**kw)
    (ROOT/'cir'/(name+'.cir')).write_text(src,encoding='ascii')
    (WORK/(name+'.cir')).write_text(src,encoding='ascii')
    raw=WORK/(name+'.raw')
    if raw.exists(): raw.unlink()
    subprocess.run([str(EXE),'-b','-n','-o',str(WORK/(name+'.log')),str(WORK/(name+'.cir'))],
                   cwd=WORK,capture_output=True,timeout=900,creationflags=subprocess.CREATE_NO_WINDOW)
    if not raw.exists(): return None
    d=readraw(raw); t=d['time']; e=d['v(out)']
    f=f_of(t,e)
    return dict(RE=kw['RE'],Cp=kw['Cp'],CTp=kw['CTp'],freq_hz=f,err_ppm=(f/F0-1)*1e6 if f else None,
                vpp=float(np.ptp(e)), supply_mw=float(-np.trapezoid(d['v(vcc)']*d['i(vsup)'],t)/(t[-1]-t[0])*1e3))

print("Q=60 (Rs=3.9 ohm), L=1.2uH, C1=C2=33p, CT=5.5p")
print("  RE       Osc?   Vout(Vpp)   f(kHz)      err(ppm)    P(mW)")
rows=[]
for RE in ["4.7k","2.2k","1k","470","220"]:
    r=run("gm_"+RE,LnH=1200,Cp=33,CTp=5.5,RE=RE,Q=60,SRF=200)
    if r is None: print("  %-6s FAILED"%RE); continue
    ok = r['vpp']>0.05
    print("  %-6s  %s  %8.4f   %9.2f   %+9.0f   %6.2f"%(
        RE,"YES " if ok else "no  ",r['vpp'],(r['freq_hz'] or 0)/1e3,r['err_ppm'] or 0,r['supply_mw']))
    if ok: rows.append(r)
(ROOT/'redesign.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')

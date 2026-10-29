
# -*- coding: utf-8 -*-
"""Rebuild the LC oscillator from the NEGATIVE-RESISTANCE criterion, then check it with REAL inductors."""
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
    if 'complex' in flags: a=a.reshape(-1,len(names),2); z=a[:,:,0]+1j*a[:,:,1]
    else: z=a.reshape(-1,len(names))
    return {n:z[:,i] for i,n in enumerate(names)}
def f_of(t,e):
    dc=float(np.trapezoid(e,t)/(t[-1]-t[0])); v=e-dc
    idx=np.where((v[:-1]<=0)&(v[1:]>0))[0]
    if len(idx)<10: return None
    cr=t[idx]-v[idx]*(t[idx+1]-t[idx])/(v[idx+1]-v[idx])
    return float((len(cr)-1)/(cr[-1]-cr[0]))

def osc(name,C1,C2,RE,LnH,Rs,CPp,CTp,stop_us=400):
    return f'''* LC Colpitts rebuilt: C1={C1}p C2={C2}p RE={RE} | L={LnH}nH Rs={Rs} CP={CPp}p CT={CTp}p
VSUP vcc 0 PWL(0 0 1u 5)
R1 vcc b 10k
R2 b 0 10k
Q1 vcc b e 2N3904
R3 e 0 {RE}
C1 b e {C1}p
C2 e 0 {C2}p
CT e 0 {CTp}p
CBLK b nL 1000p
LR nL n1 {Rs}
L1 n1 0 {LnH}n
CP n1 0 {CPp}p
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
def run(name,src):
    (ROOT/'cir'/(name+'.cir')).write_text(src,encoding='ascii')
    (WORK/(name+'.cir')).write_text(src,encoding='ascii')
    raw=WORK/(name+'.raw')
    if raw.exists(): raw.unlink()
    subprocess.run([str(EXE),'-b','-n','-o',str(WORK/(name+'.log')),str(WORK/(name+'.cir'))],
                   cwd=WORK,capture_output=True,timeout=900,creationflags=subprocess.CREATE_NO_WINDOW)
    if not raw.exists(): return None
    d=readraw(raw); t=d['time']; e=d['v(out)']
    f=f_of(t,e)
    return dict(freq_hz=f,err_ppm=(f/F0-1)*1e6 if f else None,vpp=float(np.ptp(e)),
                supply_mw=float(-np.trapezoid(d['v(vcc)']*d['i(vsup)'],t)/(t[-1]-t[0])*1e3))

print("=== rebuild with Re(Z)<0 bias: C1=33 C2=33 RE=1k ===")
print("%-10s %8s %10s %10s %10s"%("Q(SRF)","Rs(Ω)","Vout(Vpp)","f(kHz)","err(ppm)"))
rows=[]
for Q,SRF in [(1000,500),(300,400),(150,350),(100,300),(60,250),(30,200)]:
    L=1280.07e-9; Rs=2*math.pi*F0*L/Q; CP=1.0/((2*math.pi*SRF*1e6)**2*L)
    nm="nb_Q%d"%Q
    r=run(nm, osc(nm,33,33,"1k",1280.07,round(Rs,4),round(CP*1e12,4),0.5))
    if r is None: print("  Q=%4d FAILED"%Q); continue
    rows.append(dict(Q=Q,SRF=SRF,Rs=Rs,**r))
    print("Q=%-4d/%3dMHz %8.3f %10.4f %10.2f %+10.0f"%(Q,SRF,Rs,r['vpp'],(r['freq_hz'] or 0)/1e3,r['err_ppm'] or 0))
(ROOT/'rebuild.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')


# -*- coding: utf-8 -*-
"""Harmonics + temp + supply sensitivity: LC vs crystal, same transistor/bias."""
from pathlib import Path
import json, subprocess, time
import numpy as np

EXE  = Path('D:/ms_xsp/s04_crosscheck_20261017/Spice64/bin/ngspice_con.exe')
WORK = Path(r'D:\实验报告文件夹\电路2\tmp\lc_study\work')
OUT  = Path(r'D:\实验报告文件夹\电路2\tmp\lc_study')
MDL  = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage4_rf_oscillator\advance_20261029\2N3904_UNCG.lib').read_text(encoding='ascii').strip()
F0   = 31e6

def readraw(p):
    with open(p,'rb') as f:
        names=[];inside=False
        while True:
            s=f.readline().decode('ascii').strip()
            if s=='Binary:': break
            if s=='Variables:': inside=True; continue
            if inside and s: names.append(s.split()[1].lower())
        a=np.fromfile(f,dtype='<f8').reshape(-1,len(names))
    return dict(zip(names,a.T))

def freq_of(t,e):
    dc=float(np.trapezoid(e,t)/(t[-1]-t[0])); v=e-dc
    idx=np.where((v[:-1]<=0)&(v[1:]>0))[0]
    if len(idx)<10: return None,dc
    cr=t[idx]-v[idx]*(t[idx+1]-t[idx])/(v[idx+1]-v[idx])
    return float((len(cr)-1)/(cr[-1]-cr[0])),dc

def harmonics(t,e,f0):
    """THD on the last 20 us, resampled uniformly."""
    m=t>=t[-1]-20e-6
    tt=t[m]; ee=e[m]
    n=2**15
    tu=np.linspace(tt[0],tt[-1],n)
    eu=np.interp(tu,tt,ee)
    eu=eu-eu.mean()
    w=np.hanning(n); sp=np.abs(np.fft.rfft(eu*w))/ (n/4)
    fr=np.fft.rfftfreq(n,tu[1]-tu[0])
    def amp(fh):
        k=np.argmin(np.abs(fr-fh)); lo=max(0,k-2); hi=min(len(sp),k+3)
        return float(sp[lo:hi].max())
    a1=amp(f0); out={'f1':a1}
    tot=0.0
    for h in range(2,6):
        a=amp(f0*h); out['h%d'%h]=a
        out['h%d_dbc'%h]=20*np.log10(max(a,1e-15)/max(a1,1e-15))
        tot+=a*a
    out['thd_pct']=float(np.sqrt(tot)/max(a1,1e-15)*100)
    out['worst_dbc']=float(max(out['h%d_dbc'%h] for h in range(2,6)))
    return out

def run(name, netbody):
    p=OUT/(name+'.cir'); p.write_text(netbody,encoding='ascii')
    w=WORK/(name+'.cir'); w.write_text(netbody,encoding='ascii')
    raw=WORK/(name+'.raw'); log=WORK/(name+'.log')
    if raw.exists(): raw.unlink()
    subprocess.run([str(EXE),'-b','-n','-o',str(log),str(w)],cwd=WORK,capture_output=True,
                   timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
    if not raw.exists(): return None
    return readraw(raw)

def lc_net(name,L_uH,temp=27,vsup=5.0):
    return f'''* LC Colpitts 31 MHz - crystal branch replaced by L + DC block
VSUP vcc 0 PWL(0 0 1u {vsup})
R1 vcc b 10k
R2 b 0 10k
Q1 vcc b e 2N3904
R3 e 0 4.7k
C1 b e 33p
C2 e 0 33p
CT e 0 0.5p
CBLK b nL 1000p
L1 nL 0 {L_uH}u
C3 vcc 0 100n
C4 vcc 0 10u
RPROBE sense 0 10meg
CPROBE sense 0 12p
C5 e sense 2.2p
{MDL}
.options method=trap maxord=2 reltol=1e-3 trtol=7 temp={temp} tnom=27
.control
set filetype=binary
set num_threads=1
save v(vcc) v(b) v(e) i(vsup)
tran 0.125n 2m 1.9m 0.125n uic
write {name}.raw
quit
.endc
.end
'''

def xtal_net(name,temp=27):
    import math
    cm=10e-15; c0=3e-12; cl=18e-12
    fs=31e6/math.sqrt(1+cm/(cl+c0)); lm=1/((2*math.pi*fs)**2*cm)
    return f'''* Crystal Colpitts 31 MHz (C518062 assumed BVD), same transistor/bias
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
RPROBE sense 0 10meg
CPROBE sense 0 12p
C5 e sense 2.2p
{MDL}
.options method=trap maxord=2 reltol=1e-3 trtol=7 temp={temp} tnom=27
.control
set filetype=binary
set num_threads=1
save v(vcc) v(b) v(e) i(vsup) i(vxm)
tran 0.125n 2m 1.9m 0.125n uic
write {name}.raw
quit
.endc
.end
'''

Lt=1.3068
rows=[]
print("=== harmonic / amplitude comparison (27 C, 5.00 V) ===")
for tag,d in [("LC 31 MHz", run("cmp_lc", lc_net("cmp_lc",Lt))),
              ("Crystal 31 MHz", run("cmp_xtal", xtal_net("cmp_xtal")))]:
    if d is None: print(tag,"FAILED"); continue
    t=d['time']; e=d['v(e)']
    f,dc=freq_of(t,e); h=harmonics(t,e,f)
    row=dict(kind=tag,freq_hz=f,err_ppm=(f/F0-1)*1e6,vpp=float(np.ptp(e)),dc=dc,**h)
    rows.append(row)
    print("%-15s f=%9.3f kHz  err=%+8.0f ppm  Vpp=%6.3f  dc=%5.3f  H2=%6.1f dBc  H3=%6.1f dBc  THD=%5.2f%%"
          %(tag,f/1e3,row['err_ppm'],row['vpp'],dc,row['h2_dbc'],row['h3_dbc'],row['thd_pct']))

print("\n=== LC sensitivity (only the L is explicitly tuned; L tempco NOT modelled) ===")
for nm,temp,vsup in [("sens_lc_0C",0,5.0),("sens_lc_50C",50,5.0),("sens_lc_4p75V",27,4.75),("sens_lc_5p25V",27,5.25)]:
    d=run(nm, lc_net(nm,Lt,temp,vsup))
    if d is None: print(nm,"FAILED"); continue
    f,dc=freq_of(d['time'],d['v(e)'])
    row=dict(name=nm,temp=temp,vsupply=vsup,freq_hz=f,err_ppm=(f/F0-1)*1e6,vpp=float(np.ptp(d['v(e)'])),dc=dc)
    rows.append(row)
    print("%-14s T=%2d  V=%.2f  f=%9.3f kHz  err=%+8.0f ppm  Vpp=%6.3f"%(nm,temp,vsup,f/1e3,row['err_ppm'],row['vpp']))

(OUT/'lc_vs_xtal.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False),encoding='utf-8')
print("\nsaved",OUT/'lc_vs_xtal.json')

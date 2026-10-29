
# -*- coding: utf-8 -*-
"""LC Colpitts, same topology/bias as the crystal version: crystal branch -> L + DC block."""
from pathlib import Path
import json, subprocess, time, hashlib, sys
import numpy as np

EXE  = Path('D:/ms_xsp/s04_crosscheck_20261017/Spice64/bin/ngspice_con.exe')
WORK = Path(r'D:\实验报告文件夹\电路2\tmp\lc_study\work'); WORK.mkdir(parents=True, exist_ok=True)
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

def metrics(d):
    t=d['time']; e=d['v(e)']
    dc=float(np.trapezoid(e,t)/(t[-1]-t[0]))
    v=e-dc; idx=np.where((v[:-1]<=0)&(v[1:]>0))[0]
    freq=None
    if len(idx)>10:
        cr=t[idx]-v[idx]*(t[idx+1]-t[idx])/(v[idx+1]-v[idx])
        freq=float((len(cr)-1)/(cr[-1]-cr[0]))
    win=[]; t0=t[-1]-100e-6
    for k in range(10):
        m=(t>=t0+k*10e-6)&(t<t0+(k+1)*10e-6)
        if m.sum()<10: continue
        win.append((float(np.ptp(e[m])), float(np.trapezoid(e[m],t[m])/(t[m][-1]-t[m][0]))))
    vs=[w[0] for w in win]; ds=[w[1] for w in win]
    return dict(vpp=float(np.ptp(e)), dc=dc, freq=freq,
                vpp_span_pct=float((max(vs)-min(vs))/max(np.mean(vs),1e-12)*100),
                dc_span_mv=float((max(ds)-min(ds))*1e3),
                supply_mw=float(-np.trapezoid(d['v(vcc)']*d['i(vsup)'],t)/(t[-1]-t[0])*1e3),
                base_dc=float(np.trapezoid(d['v(b)'],t)/(t[-1]-t[0])))

def net(name,L_uH,Cblk_p,C1_p,C2_p,Ctrim_p,temp):
    return f'''* LC Colpitts 31 MHz - crystal branch replaced by L + DC block; identical bias/topology
* lossless L, ideal 5 V, UIC; screening only, no hardware qualification
VSUP vcc 0 PWL(0 0 1u 5)
R1 vcc b 10k
R2 b 0 10k
Q1 vcc b e 2N3904
R3 e 0 4.7k
C1 b e {C1_p}p
C2 e 0 {C2_p}p
CT e 0 {Ctrim_p}p
CBLK b nL {Cblk_p}p
L1 nL 0 {L_uH}u
C3 vcc 0 100n
C4 vcc 0 10u
* 10X probe represented as 10 Mohm || 12 pF at SENSE
RPROBE sense 0 10meg
CPROBE sense 0 12p
C5 e sense 2.2p
{MDL}
.options method=trap maxord=2 reltol=1e-3 trtol=7 temp={temp} tnom=27
.control
set filetype=binary
set num_threads=1
save v(vcc) v(b) v(e) v(sense) i(vsup)
tran 0.125n 2m 1.9m 0.125n uic
write {name}.raw
quit
.endc
.end
'''

def run(name,L_uH,Cblk_p=1000,C1_p=33,C2_p=33,Ctrim_p=0.5,temp=27):
    raw=WORK/(name+'.raw')
    src=net(name,L_uH,Cblk_p,C1_p,C2_p,Ctrim_p,temp)
    p=OUT/(name+'.cir'); p.write_text(src,encoding='ascii')
    w=WORK/(name+'.cir'); w.write_text(src,encoding='ascii')
    log=WORK/(name+'.log')
    if raw.exists(): raw.unlink()
    t0=time.monotonic()
    subprocess.run([str(EXE),'-b','-n','-o',str(log),str(w)],cwd=WORK,capture_output=True,
                   timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
    if not raw.exists():
        print("FAILED",name, log.read_text(errors='replace')[-300:]); return None
    m=metrics(readraw(raw)); m.update(name=name,L_uH=L_uH,temp=temp,seconds=round(time.monotonic()-t0,1))
    print("%-16s L=%5.3f uH T=%2d  f=%10.2f kHz  err=%+9.0f ppm  Ve=%7.4f Vpp  dc=%6.3f  P5V=%6.2f mW"
          %(name,L_uH,temp,(m['freq'] or 0)/1e3,((m['freq'] or 0)/F0-1)*1e6,m['vpp'],m['dc'],m['supply_mw']))
    return m

rows=[]
# step 1: one run at L=1.0 uH to locate resonance
a=run("lcB_L1p0uH",1.0)
if a and a['freq']:
    rows.append(a)
    Lt = 1.0*(a['freq']/F0)**2
    print("  -> f ~ 1/sqrt(L): L needed for 31.000 MHz = %.4f uH" % Lt)
    # step 2: verify
    b=run("lcB_Ltuned",round(Lt,4))
    if b: rows.append(b)
    # step 3: +5% inductor tolerance (as-purchased inductor)
    c=run("lcB_Lplus5pct",round(Lt*1.05,4))
    if c: rows.append(c)
    # step 4: -5%
    d=run("lcB_Lminus5pct",round(Lt*0.95,4))
    if d: rows.append(d)
    # step 5: temperature 47 C on the tuned build (transistor + model drift only; L tempco not modelled)
    e=run("lcB_T47C",round(Lt,4),temp=47)
    if e: rows.append(e)

(OUT/'lc_results_v2.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False),encoding='utf-8')
print("\nsaved",OUT/'lc_results_v2.json')

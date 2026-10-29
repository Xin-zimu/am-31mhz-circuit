
# -*- coding: utf-8 -*-
"""Analyse LC Colpitts runs; rerun any case whose .raw is missing."""
from pathlib import Path
import json, subprocess, time, hashlib
import numpy as np

EXE  = Path('D:/ms_xsp/s04_crosscheck_20261017/Spice64/bin/ngspice_con.exe')
WORK = Path(r'D:\实验报告文件夹\电路2\tmp\lc_study\work')
OUT  = Path(r'D:\实验报告文件夹\电路2\tmp\lc_study')
F0   = 31e6

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

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
        cross=t[idx]-v[idx]*(t[idx+1]-t[idx])/(v[idx+1]-v[idx])
        freq=float((len(cross)-1)/(cross[-1]-cross[0]))
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

cases=[("lc_L0p82uH",0.82,33,33,15.64),("lc_L1p0uH",1.0,33,33,9.86),("lc_L1p2uH",1.2,33,33,5.47)]
rows=[]
for name,L,c1,c2,ct in cases:
    raw=WORK/(name+'.raw'); cir=WORK/(name+'.cir')
    if not raw.exists():
        print("rerun", name)
        log=WORK/(name+'.log')
        subprocess.run([str(EXE),'-b','-n','-o',str(log),str(cir)],cwd=WORK,
                       capture_output=True,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
    if not raw.exists():
        print("FAILED", name); continue
    m=metrics(readraw(raw))
    m.update(name=name,L_uH=L,C1_p=c1,C2_p=c2,Ctrim_p=ct,
             freq_err_ppm=((m['freq'] or 0)/F0-1)*1e6, raw_sha256=sha(raw))
    rows.append(m)
    print("%-12s f=%9.2f kHz  err=%+8.0f ppm  Ve=%7.4f Vpp  dc=%6.3f  P5V=%6.2f mW  vppspan=%6.2f%%  dcspan=%6.3f mV"
          % (name,(m['freq'] or 0)/1e3,m['freq_err_ppm'],m['vpp'],m['dc'],m['supply_mw'],m['vpp_span_pct'],m['dc_span_mv']))

(OUT/'lc_results.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False),encoding='utf-8')
print("\nsaved", OUT/'lc_results.json')

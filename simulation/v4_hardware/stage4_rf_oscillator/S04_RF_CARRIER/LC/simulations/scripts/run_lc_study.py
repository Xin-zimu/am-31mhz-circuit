
# -*- coding: utf-8 -*-
"""LC Colpitts vs crystal Colpitts @31 MHz, same 2N3904, same 5 V bias.
   Screening only: Rm=30 ohm, lossless L (100 ppm/C), no layout parasitics."""
from pathlib import Path
import json, subprocess, time, hashlib
import numpy as np

EXE  = Path('D:/ms_xsp/s04_crosscheck_20261017/Spice64/bin/ngspice_con.exe')
WORK = Path(r'D:\实验报告文件夹\电路2\tmp\lc_study\work'); WORK.mkdir(parents=True, exist_ok=True)
OUT  = Path(r'D:\实验报告文件夹\电路2\tmp\lc_study'); OUT.mkdir(parents=True, exist_ok=True)
MDL  = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage4_rf_oscillator\advance_20261029\2N3904_UNCG.lib').read_text(encoding='ascii').strip()
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
    cross=t[idx]-v[idx]*(t[idx+1]-t[idx])/(v[idx+1]-v[idx])
    freq=float((len(cross)-1)/(cross[-1]-cross[0])) if len(idx)>10 else None
    # 末 100us 内 10 个 10us 窗
    win=[]
    t0=t[-1]-100e-6
    for k in range(10):
        m=(t>=t0+k*10e-6)&(t<t0+(k+1)*10e-6)
        if m.sum()<10: continue
        win.append((float(np.ptp(e[m])), float(np.trapezoid(e[m],t[m])/(t[m][-1]-t[m][0]))))
    vs=[w[0] for w in win]; ds=[w[1] for w in win]
    return dict(vpp=float(np.ptp(e)), dc=dc, freq=freq,
                vpp_span=float((max(vs)-min(vs))/max(np.mean(vs),1e-12)),
                dc_span=float((max(ds)-min(ds))),
                supply_w=float(-np.trapezoid(d['v(vcc)']*d['i(vsup)'],t)/(t[-1]-t[0])),
                base_dc=float(np.trapezoid(d['v(b)'],t)/(t[-1]-t[0])))

def net(name, L_uH, C1_p, C2_p, Ctrim_p, extra=""):
    L = L_uH*1e-6
    return f'''* LC Colpitts 31 MHz, same 2N3904 / 5 V / RE=4.7k as the crystal version
* lossless L ({L_uH} uH), ideal 5 V, UIC; screening only
VSUP vcc 0 PWL(0 0 1u 5)
R1 vcc b 10k
R2 b 0 10k
Q1 vcc b e 2N3904
R3 e 0 4.7k
C1 b e {C1_p}p
C2 e 0 {C2_p}p
CT e 0 {Ctrim_p}p
L1 vcc b {L_uH}u
C3 vcc 0 100n
C4 vcc 0 10u
* 10X probe represented as 10 Mohm || 12 pF at SENSE
RPROBE sense 0 10meg
CPROBE sense 0 12p
C5 e sense 2.2p
{extra}{MDL}
.options method=trap maxord=2 reltol=1e-3 trtol=7 temp=27 tnom=27
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

def run(name, L_uH, C1_p, C2_p, Ctrim_p, extra=""):
    src = net(name, L_uH, C1_p, C2_p, Ctrim_p, extra)
    p = OUT/(name+'.cir'); p.write_text(src, encoding='ascii')
    w = WORK/(name+'.cir'); w.write_text(src, encoding='ascii')
    log = WORK/(name+'.log'); raw = WORK/(name+'.raw')
    if raw.exists(): raw.unlink()
    t0=time.monotonic()
    r = subprocess.run([str(EXE),'-b','-n','-o',str(log),str(w)], cwd=WORK,
                       capture_output=True, timeout=900, creationflags=subprocess.CREATE_NO_WINDOW)
    secs=time.monotonic()-t0
    if not raw.exists():
        print(name, "NO RAW", log.read_text(errors='replace')[-400:]); return None
    res = metrics(readraw(raw))
    res.update(name=name, seconds=round(secs,1), L_uH=L_uH, C1_p=C1_p, C2_p=C2_p, Ctrim_p=Ctrim_p,
               raw_sha256=sha(raw), net_sha256=sha(p))
    print("%-18s f=%9.1f kHz  err=%+7.0f ppm  Ve=%7.4f Vpp  Ve_dc=%6.3f  P5V=%6.2f mW  vppspan=%.1f%%" % (
        name, (res['freq'] or 0)/1e3, ((res['freq'] or 0)/F0-1)*1e6, res['vpp'], res['dc'],
        res['supply_w']*1e3, res['vpp_span']*100))
    return res

# ---- design: f0 = 1/(2 pi sqrt(L * C_eff)), C_eff ~ C1*C2/(C1+C2) (+ Ct)
import math
LC = 1.0/(2*math.pi*F0)**2
C1=C2=33e-12
for L_uH in [0.82, 1.0, 1.2]:
    Ctot_needed = LC/(L_uH*1e-6)
    Ctrim = Ctot_needed - (C1*C2/(C1+C2))     # extra C to ground at e
    print("L=%s uH -> L*C=%.3e, Ctot=%.2f pF, C1||C2=16.5 pF, needed Ctrim=%.2f pF"
          % (L_uH, LC, Ctot_needed*1e12, Ctrim*1e12))

results=[]
for L_uH in [0.82, 1.0, 1.2]:
    Ctot_needed = LC/(L_uH*1e-6)
    Ctrim = max(Ctot_needed - (C1*C2/(C1+C2)), 0.5e-12)
    res = run("lc_L%suH"%str(L_uH).replace('.','p'), L_uH, 33, 33, round(Ctrim*1e12,2))
    if res: results.append(res)

(OUT/'lc_results.json').write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')
print("\nsaved", OUT/'lc_results.json')
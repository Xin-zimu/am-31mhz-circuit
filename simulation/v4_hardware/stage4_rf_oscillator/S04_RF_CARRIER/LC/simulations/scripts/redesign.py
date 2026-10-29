
# -*- coding: utf-8 -*-
"""Part B: LC bias redesigned for LC - base driven through HIGH impedance (RFC / big R),
   not a hard 10k/10k divider. Compare against the original as control."""
from pathlib import Path
import subprocess, json
import numpy as np

EXE=Path('D:/ms_xsp/s04_crosscheck_20261017/Spice64/bin/ngspice_con.exe')
ROOT=Path(r'D:\实验报告文件夹\电路2\tmp\lc02b')
(ROOT/'cir').mkdir(parents=True,exist_ok=True)
WORK=ROOT/'work'; WORK.mkdir(parents=True,exist_ok=True)
MDL=Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage4_rf_oscillator\advance_20261029\2N3904_UNCG.lib').read_text(encoding='ascii').strip()

def readraw(p):
    with open(p,'rb') as f:
        names=[];inside=False
        while True:
            s=f.readline().decode('ascii').strip()
            if s=='Binary:':break
            if s=='Variables:':inside=True;continue
            if inside and s:names.append(s.split()[1].lower())
        a=np.fromfile(f,dtype='<f8')
    if len(a)%len(names)!=0: a=a[:(len(a)//len(names))*len(names)]
    a=a.reshape(-1,len(names))
    return {n:a[:,i] for i,n in enumerate(names)}

def go(nm,src):
    (ROOT/'cir'/(nm+'.cir')).write_text(src,encoding='ascii')
    (WORK/(nm+'.cir')).write_text(src,encoding='ascii')
    raw=WORK/(nm+'.raw')
    if raw.exists(): raw.unlink()
    subprocess.run([str(EXE),'-b','-n','-o',str(WORK/(nm+'.log')),str(WORK/(nm+'.cir'))],
                   cwd=WORK,capture_output=True,timeout=400,creationflags=subprocess.CREATE_NO_WINDOW)
    if not raw.exists(): return None
    d=readraw(raw)
    try: raw.unlink()
    except: pass
    return d

def lc(nm,Rb_top,Rb_bot,Rfc,RE,C1,C2,Q,LnH="1280.07n",stop=2000,tmax="0.25n"):
    L=float(LnH.replace('n',''))*1e-9
    Rs=2*np.pi*31e6*L/Q
    rfc = f"RFC vcc b {Rfc}\n" if Rfc else ""
    return f'''* LC redesign | base fed via {Rb_top}/{Rb_bot} + RFC {Rfc} | RE={RE} C1={C1} C2={C2} Q={Q}
VSUP vcc 0 PWL(0 0 1u 5)
R1 vcc b {Rb_top}
R2 b 0 {Rb_bot}
{rfc}Q1 vcc b e 2N3904
R3 e 0 {RE}
C1 b e {C1}p
C2 e 0 {C2}p
CT e 0 0.5p
CBLK b nL 1000p
LR nL n1 {Rs:.6f}
L1 n1 0 {LnH}
C3 vcc 0 100n
C4 vcc 0 10u
{MDL}
.options method=trap maxord=2 reltol=1e-3 trtol=7 temp=27 tnom=27
.control
set filetype=binary
set num_threads=1
save v(e)
tran {tmax} {stop}u 0 {tmax} uic
write {nm}.raw
quit
.endc
.end
'''

def analyse(d):
    t=d['time']; e=d['v(e)']; stop=t[-1]
    w=[float(np.ptp(e[(t>=a*stop)&(t<(a+0.05)*stop)])) for a in
       [0.05,0.15,0.3,0.5,0.7,0.85,0.95]]
    return w

print("=== LC redesign: high-impedance base drive (RFC / large R) ===")
print("%-34s %8s %8s %8s %8s %8s %8s %8s"%("config","5%","15%","30%","50%","70%","85%","95%"))
cfgs=[
 ("control: 10k/10k, no RFC","10k","10k",None,"4.7k",33,33),
 ("control: 10k/10k RE=220","10k","10k",None,"220",33,33),
 ("RFC 1mH only","10meg","10meg","1m","1k",33,33),
 ("RFC 1mH + 220k/47k","220k","47k","1m","1k",33,33),
 ("RFC 1mH + 220k/47k C1=100","220k","47k","1m","1k",100,33),
 ("RFC 1mH + 470k/100k C1=220","470k","100k","1m","470",220,33),
]
rows=[]
for tag,Rt,Rb,Rfc,RE,C1,C2 in cfgs:
    nm="rd_"+str(abs(hash(tag))%99999)
    d=go(nm,lc(nm,Rt,Rb,Rfc,RE,C1,C2,60))
    if d is None: print("%-34s FAILED"%tag); continue
    w=analyse(d)
    grow = w[-1]>0.05 and w[-1]>w[1]*1.3
    print("%-34s %8.4f %8.4f %8.4f %8.4f %8.4f %8.4f %8.4f %s"%(tag,*w,"<= 增长" if grow else ""))
    rows.append(dict(tag=tag,w=w,grow=bool(grow)))
(ROOT/'redesign.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False),encoding='utf-8')

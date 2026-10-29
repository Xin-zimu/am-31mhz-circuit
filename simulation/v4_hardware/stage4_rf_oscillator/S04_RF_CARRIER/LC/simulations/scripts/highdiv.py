
# -*- coding: utf-8 -*-
"""Fix: RFC must still be a DC path (it is an inductor -> DC short, fine) BUT
   the base divider 220k/47k sets VB; RFC from vcc to b bypasses it in DC too.
   Correct topology: divider -> base (DC), RFC in SERIES between tank node and base is wrong.
   Standard Colpitts: base AC-grounded or base fed via divider; the tank sits b-e.
   Test: base divider with HIGH value (so AC not clamped) without any RFC."""
from pathlib import Path
import subprocess, json
import numpy as np
EXE=Path('D:/ms_xsp/s04_crosscheck_20261017/Spice64/bin/ngspice_con.exe')
ROOT=Path(r'D:\实验报告文件夹\电路2\tmp\lc02b')
WORK=ROOT/'work'
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
def lc(nm,R1,R2,RE,C1,C2,Q,bias_ind=None,stop=2000):
    L=1280.07e-9; Rs=2*np.pi*31e6*L/Q
    rf = f"LRF vcc b {bias_ind}\n" if bias_ind else ""
    return f'''* LC | div {R1}/{R2} RE={RE} C1={C1} C2={C2} Q={Q} {rf and ("RF="+str(bias_ind))}
VSUP vcc 0 PWL(0 0 1u 5)
R1 vcc b {R1}
R2 b 0 {R2}
{rf}Q1 vcc b e 2N3904
R3 e 0 {RE}
C1 b e {C1}p
C2 e 0 {C2}p
CT e 0 0.5p
CBLK b nL 1000p
LR nL n1 {Rs:.6f}
L1 n1 0 1280.07n
C3 vcc 0 100n
C4 vcc 0 10u
{MDL}
.options method=trap maxord=2 reltol=1e-3 trtol=7 temp=27 tnom=27
.control
set filetype=binary
set num_threads=1
save v(e) v(b)
tran 0.25n {stop}u 0 0.25n uic
write {nm}.raw
quit
.endc
.end
'''
def an(d):
    t=d['time']; e=d['v(e)']; s=t[-1]
    w=[float(np.ptp(e[(t>=a*s)&(t<(a+0.05)*s)])) for a in [0.05,0.15,0.3,0.5,0.7,0.85,0.95]]
    return w
print("=== high-value base divider (AC not clamped) vs low-value, real Q=60, 2 ms ===")
print("%-40s %8s %8s %8s %8s %8s %8s %8s"%("config","5%","15%","30%","50%","70%","85%","95%"))
rows=[]
for tag,R1,R2,RE,C1,C2 in [
 ("10k/10k RE4.7k 33/33 (control)","10k","10k","4.7k",33,33),
 ("100k/100k RE1k 33/33","100k","100k","1k",33,33),
 ("220k/220k RE1k 33/33","220k","220k","1k",33,33),
 ("470k/470k RE1k 33/33","470k","470k","1k",33,33),
 ("470k/470k RE220 C1=100 C2=33","470k","470k","220",100,33),
 ("470k/470k RE220 C1=220 C2=33","470k","470k","220",220,33),
 ("1meg/1meg RE220 C1=33 C2=220","1meg","1meg","220",33,220),
]:
    nm="hv_"+str(abs(hash(tag))%99999)
    d=go(nm,lc(nm,R1,R2,RE,C1,C2,60))
    if d is None: print("%-40s FAILED"%tag); continue
    w=an(d)
    g = w[-1]>0.05 and w[-1]>w[1]*1.3
    print("%-40s %8.4f %8.4f %8.4f %8.4f %8.4f %8.4f %8.4f %s"%(tag,*w,"<= 增长" if g else ""))
    rows.append(dict(tag=tag,w=w,grow=bool(g)))
(ROOT/'highdiv.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False),encoding='utf-8')


# -*- coding: utf-8 -*-
"""S04-LC-02 step1: CORRECT port. Keep the whole circuit (L present, DC path via L to gnd).
   Inject 1 A AC at the tank node nL, measure Z(nL).
   Oscillation condition: Im(Z)=0 AND Re(Z)<0 at that frequency.
   This is the total (active + tank) impedance in the parallel representation - no
   series/parallel mixing."""
from pathlib import Path
import subprocess, math, json
import numpy as np
EXE=Path('D:/ms_xsp/s04_crosscheck_20261017/Spice64/bin/ngspice_con.exe')
ROOT=Path(r'D:\实验报告文件夹\电路2\tmp\lc02'); WORK=ROOT/'work'
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

def net(name,R1,R2,RE,C1,C2,LnH,Q,SRF,CTp=0.5,CPp_extra=0.0):
    L=LnH*1e-9
    Rs=2*math.pi*F0*L/Q
    CP=1.0/((2*math.pi*SRF*1e6)**2*L)
    return f'''* LC-02 total impedance probe | RE={RE} div={R1}/{R2} C1={C1} C2={C2} L={LnH}nH Q={Q} SRF={SRF}
VSUP vcc 0 5
R1 vcc b {R1}
R2 b 0 {R2}
Q1 vcc b e 2N3904
R3 e 0 {RE}
C1 b e {C1}p
C2 e 0 {C2}p
CT e 0 {CTp}p
CBLK b nL 1000p
LR nL n1 {Rs:.6f}
L1 n1 0 {LnH}n
CP n1 0 {CP+CPp_extra*1e-12:.9f}
C3 vcc 0 100n
C4 vcc 0 10u
IAC nL 0 ac 1
{MDL}
.options method=trap maxord=2 reltol=1e-3 trtol=7 temp=27 tnom=27
.control
set filetype=binary
ac dec 2000 20meg 45meg
write {name}.raw v(nL)
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
                   cwd=WORK,capture_output=True,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
    return readraw(raw) if raw.exists() else None

def analyse(d,label):
    f=d['frequency'].real; z=d['v(nl)']
    im=z.imag; re=z.real
    s=np.sign(im); cr=np.where(s[:-1]!=s[1:])[0]
    print("\n  [%s]"%label)
    if len(cr)==0:
        print("    no Im(Z)=0 crossing in 20-45 MHz  (min|Im| = %.1f ohm)"%np.abs(im).min()); return None
    best=None
    for c in cr:
        w=np.abs(f[c]-F0)
        tag=" <== nearest 31 MHz" if w==min(abs(f[cc]-F0) for cc in cr) else ""
        print("    Im(Z)=0 at %8.4f MHz : Re(Z) = %+10.3f ohm%s"%(f[c]/1e6, re[c], tag))
        if w<2e6 and (best is None or re[c]<best[1]): best=(f[c],re[c])
    if best:
        verdict = "Re(Z)<0 -> 满足起振判据" if best[1]<0 else "Re(Z)>0 -> 不满足（无净负阻）"
        print("    => 31MHz 附近结论：%s"%verdict)
    return best

print("=== total impedance at tank node, REAL inductor, original crystal-derived bias ===")
d=run("t_orig", net("t_orig","10k","10k","4.7k",33,33,1280.07,60,200))
if d: analyse(d,"RE=4.7k 10k/10k C1=C2=33p Q=60")
print("\n=== sweep bias / divider / feedback ratio ===")
res={}
for R1,R2,RE,C1,C2,tag in [
  ("10k","10k","4.7k",33,33,"orig"),
  ("10k","10k","1k",33,33,"RE1k"),
  ("10k","10k","220",33,33,"RE220"),
  ("22k","10k","1k",33,33,"div22k_RE1k"),
  ("22k","3.3k","1k",33,33,"div22k3k3_RE1k"),
  ("10k","3.3k","1k",33,33,"div10k3k3_RE1k"),
]:
    R1v=float(R1.replace('k',''))*1e3; R2v=float(R2.replace('k',''))*1e3 if 'k' in R2 else float(R2)
    d=run("t_"+tag, net("t_"+tag,"%d"%R1v,"%d"%R2v,RE,C1,C2,1280.07,60,200))
    if d is None: continue
    b=analyse(d,"%s: div %s/%s RE=%s C1=C2=%dp"%(tag,R1,R2,RE,C1))
    if b: res[tag]=dict(f=b[0],re=b[1])
(ROOT/'step1.json').write_text(json.dumps(res,indent=2),encoding='utf-8')

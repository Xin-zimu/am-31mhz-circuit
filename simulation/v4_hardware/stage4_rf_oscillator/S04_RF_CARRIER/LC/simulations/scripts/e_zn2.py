
# -*- coding: utf-8 -*-
"""Correct negative-resistance measurement: Re(Z) of ACTIVE network at the tank node,
   with the L branch ABSENT, for several biases. Then compare with tank loss."""
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

def zn(name,RE,R1,R2,CTp,stop_note=""):
    return f'''* Znet: L removed, 1A AC injected at nL
VSUP vcc 0 5
R1 vcc b {R1}
R2 b 0 {R2}
Q1 vcc b e 2N3904
R3 e 0 {RE}
C1 b e 33p
C2 e 0 33p
CT e 0 {CTp}p
CBLK b nL 1000p
C3 vcc 0 100n
C4 vcc 0 10u
IAC nL 0 ac 1
{MDL}
.options method=trap maxord=2 reltol=1e-3 trtol=7 temp=27 tnom=27
.control
set filetype=binary
op
print v(b) v(e) @r3[i]
ac dec 800 20meg 45meg
write z_{name}.raw v(nL)
quit
.endc
.end
'''
def run(name,src):
    (ROOT/'cir'/(name+'.cir')).write_text(src,encoding='ascii')
    (WORK/(name+'.cir')).write_text(src,encoding='ascii')
    raw=WORK/('z_'+name+'.raw')
    if raw.exists(): raw.unlink()
    p=subprocess.run([str(EXE),'-b','-n','-o',str(WORK/(name+'.log')),str(WORK/(name+'.cir'))],
                   cwd=WORK,capture_output=True,timeout=300,creationflags=subprocess.CREATE_NO_WINDOW)
    log=(WORK/(name+'.log')).read_text(errors='replace')
    if not raw.exists(): return None,log
    return readraw(raw),log

print("=== Re(Z) of the ACTIVE network at the tank node (L removed) ===")
print("%-24s %10s %10s %12s %14s"%("RE / base divider","Vb(V)","Ve(V)","Re(Z)@31M","min Re(Z)"))
out={}
for RE,dv in [("4.7k","10k/10k"),("2.2k","10k/10k"),("1k","10k/10k"),("470","10k/10k"),("220","10k/10k"),
              ("1k","22k/10k"),("1k","10k/3.3k"),("4.7k","22k/10k")]:
    R1,R2=dv.split("/")
    nm="s_%s_%s_%s"%(RE.replace('.','p'),R1,R2)
    d,log=run(nm, zn(nm,RE,R1,R2,0.5))
    if d is None:
        print("%-24s FAILED"%("%s %s"%(RE,dv))); continue
    f=d['frequency']; z=d['v(nl)']
    k=np.argmin(np.abs(f-F0))
    vb=ve=None
    for l in log.splitlines():
        p=l.split()
        if len(p)>=3 and p[1]=='=':
            try: val=float(p[2])
            except: continue
            if p[0]=='op1.v(b)': vb=val
            elif p[0]=='op1.v(e)': ve=val
    print("%-24s %10.4f %10.4f %12.3f %14.3f"%("%s %s"%(RE,dv),vb or 0,ve or 0,z.real[k],z.real.min()))
    out["%s_%s"%(RE,R1)]=float(z.real[k])

# tank loss for reference
print("\n=== tank loss (series Rs -> equivalent parallel resistance across the tank) ===")
wL=2*math.pi*F0*1280.07e-9
for Q in [1000,300,150,100,60]:
    Rs=wL/Q
    Rp=(wL**2)/Rs
    print("  Q=%4d  Rs=%6.3f Ω   Rp = wL²/Rs = %9.0f Ω"%(Q,Rs,Rp))
(ROOT/'znet_sweep.json').write_text(json.dumps(out,indent=2),encoding='utf-8')

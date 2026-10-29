
# -*- coding: utf-8 -*-
"""E2 DC op + E3 small-signal negative resistance of the transistor network at the tank node."""
from pathlib import Path
import subprocess, math, json
import numpy as np
EXE=Path('D:/ms_xsp/s04_crosscheck_20261017/Spice64/bin/ngspice_con.exe')
ROOT=Path(r'D:\实验报告文件夹\电路2\tmp\lcdev'); WORK=ROOT/'work'
MDL=Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage4_rf_oscillator\advance_20261029\2N3904_UNCG.lib').read_text(encoding='ascii').strip()
F0=31e6

def probe_net(name,Rs):
    return f'''* probe: DC op + AC impedance at tank node nL
VSUP vcc 0 5
R1 vcc b 10k
R2 b 0 10k
Q1 vcc b e 2N3904
R3 e 0 4.7k
C1 b e 33p
C2 e 0 33p
CT e 0 0.5p
CBLK b nL 1000p
LR nL n1 {Rs}
L1 n1 0 1280.07n
CP n1 0 0.0p
C3 vcc 0 100n
C4 vcc 0 10u
IAC nL 0 ac 1
{MDL}
.options method=trap maxord=2 reltol=1e-3 trtol=7 temp=27 tnom=27
.control
op
print v(b) v(e) v(c)
ac dec 400 25meg 38meg
write ac_{name}.raw v(nL)
quit
.endc
.end
'''
def run(name,Rs):
    src=probe_net(name,Rs)
    (ROOT/'cir'/(name+'.cir')).write_text(src,encoding='ascii')
    (WORK/(name+'.cir')).write_text(src,encoding='ascii')
    raw=WORK/('ac_'+name+'.raw')
    if raw.exists(): raw.unlink()
    subprocess.run([str(EXE),'-b','-n','-o',str(WORK/(name+'.log')),str(WORK/(name+'.cir'))],
                   cwd=WORK,capture_output=True,timeout=300,creationflags=subprocess.CREATE_NO_WINDOW)
    return (WORK/(name+'.log')).read_text(errors='replace'), raw

def read_ac(p):
    with open(p,'rb') as f:
        names=[];inside=False;flags=""
        while True:
            line=f.readline()
            s=line.decode('ascii').strip()
            if s=='Binary:': break
            if s.startswith('Flags:'): flags=s
            if s=='Variables:': inside=True; continue
            if inside and s: names.append(s.split()[1].lower())
        a=np.fromfile(f,dtype='<f8')
    cplx = 'complex' in flags
    if cplx: a=a.reshape(-1,len(names),2); z=a[:,:,0]+1j*a[:,:,1]
    else: z=a.reshape(-1,len(names))
    return names,{n:z[:,i] for i,n in enumerate(names)}

print("=== E2: DC operating point (Rs must not change it) ===")
print("%-8s %8s %8s %8s %10s"%("Rs","V(b)","V(e)","V(c)","Ie(mA)"))
for Rs,tag in [(0,'r0'),(0.001,'r1m'),(0.23,'r230m'),(3.9,'r3p9')]:
    out,raw=run('dc_'+tag,Rs)
    vb=ve=vc=None
    for l in out.splitlines():
        p=l.split()
        if len(p)>=3 and p[1]=='=':
            try: val=float(p[2])
            except: continue
            if p[0]=='v(b)': vb=val
            elif p[0]=='v(e)': ve=val
            elif p[0]=='v(c)': vc=val
    ie = (ve/4700*1e3) if ve is not None else None
    print("%-8s %8.4f %8.4f %8.4f %10.3f"%(Rs,vb or 0,ve or 0,vc or 0,ie or 0))

print("\n=== E3: impedance Z = v(nL) with 1 A injected  (negative real part = gain available) ===")
rows={}
for Rs,tag in [(0,'r0'),(0.001,'r1m'),(0.23,'r230m'),(3.9,'r3p9')]:
    names,d=read_ac(WORK/('ac_dc_'+tag+'.raw'))
    f=d['frequency']; z=d['v(nl)']
    k=np.argmin(np.abs(f-F0))
    rows[Rs]=(f[k],z[k],f,z)
    print("  Rs=%-6s @%.4f MHz : Re(Z)=%+9.4f Ω   Im(Z)=%+9.4f Ω"%(Rs,f[k]/1e6,z[k].real,z[k].imag))

print("\n=== crossover: is Re(Z) < 0 anywhere in 25-38 MHz? ===")
for Rs,(fk,zk,f,z) in rows.items():
    neg = z.real<0
    if neg.any():
        print("  Rs=%-6s : Re(Z)<0 from %.4f to %.4f MHz (min %.3f Ω)"%(Rs,f[neg][0]/1e6,f[neg][-1]/1e6,z.real[neg].min()))
    else:
        print("  Rs=%-6s : Re(Z) >= 0 everywhere (min %.3f Ω)  -> no negative resistance"%(Rs,z.real.min()))

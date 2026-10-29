
# -*- coding: utf-8 -*-
"""DECISIVE: small-signal impedance looking into the active network at the tank node.
   If Re(Z_net) is only a few milliohms, then Rs=1 mOhm genuinely kills it."""
from pathlib import Path
import subprocess, math
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
    if 'complex' in flags:
        a=a.reshape(-1,len(names),2); z=a[:,:,0]+1j*a[:,:,1]
    else:
        z=a.reshape(-1,len(names))
    return {n:z[:,i] for i,n in enumerate(names)}

def znet_net(name):
    """L branch REMOVED. Inject 1 A at nL, read Z(nL) = impedance of the active network."""
    return f'''* Z of the active network at the tank node (no L, no Rs)
VSUP vcc 0 5
R1 vcc b 10k
R2 b 0 10k
Q1 vcc b e 2N3904
R3 e 0 4.7k
C1 b e 33p
C2 e 0 33p
CT e 0 0.5p
CBLK b nL 1000p
C3 vcc 0 100n
C4 vcc 0 10u
IAC nL 0 ac 1
{MDL}
.options method=trap maxord=2 reltol=1e-3 trtol=7 temp=27 tnom=27
.control
set filetype=binary
op
print v(b) v(e)
ac dec 800 25meg 40meg
write znet_{name}.raw v(nL)
quit
.endc
.end
'''
def run(name,src,rawname):
    (ROOT/'cir'/(name+'.cir')).write_text(src,encoding='ascii')
    (WORK/(name+'.cir')).write_text(src,encoding='ascii')
    raw=WORK/rawname
    if raw.exists(): raw.unlink()
    subprocess.run([str(EXE),'-b','-n','-o',str(WORK/(name+'.log')),str(WORK/(name+'.cir'))],
                   cwd=WORK,capture_output=True,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
    return raw.exists(), (WORK/(name+'.log')).read_text(errors='replace')

ok,log = run('znet','ZNET',"znet_x.raw") if False else run('znet', znet_net('x'), 'znet_x.raw')
if not ok:
    print("FAILED"); print(log[-1500:]); raise SystemExit
d=readraw(WORK/'znet_x.raw')
f=d['frequency']; z=d['v(nl)']
k=np.argmin(np.abs(f-F0))
print("=== active-network impedance at the tank node (Rs and L removed) ===")
print("  @%.4f MHz :  Re(Z) = %+10.4f ohm    Im(Z) = %+10.4f ohm"%(f[k]/1e6, z[k].real, z[k].imag))
neg=z.real<0
if neg.any():
    print("  Re(Z)<0 from %.3f to %.3f MHz ; most negative Re(Z) = %.4f ohm at %.3f MHz"%(
        f[neg][0]/1e6, f[neg][-1]/1e6, z.real.min(), f[np.argmin(z.real)]/1e6))
# find zero imaginary crossing near 31 MHz
im=z.imag
sign=np.sign(im)
cross=np.where((sign[:-1]!=sign[1:]))[0]
if len(cross):
    print("\n  Im(Z)=0 crossings (would-be oscillation frequency):")
    for c in cross:
        print("    f=%.4f MHz   Re(Z)=%+.4f ohm"%(f[c]/1e6, z.real[c]))
print("\n  For comparison, the loss the inductor adds at 31 MHz: Rs/(wL)^2 as a conductance")
wL=2*math.pi*F0*1280.07e-9
for Rs in [0.001,0.01,0.1,0.23,1.0,3.9]:
    print("    Rs=%7.3f ohm -> added conductance = %.3e S  (= 1/%.0f ohm equivalent shunt R)"%(
        Rs, Rs/(wL**2), wL**2/Rs))

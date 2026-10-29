
# -*- coding: utf-8 -*-
"""Control: does the SAME harness detect oscillation when oscillation exists?
   Use the crystal (known to work) and an ideal-L LC (known to ring) as positive controls."""
from pathlib import Path
import subprocess, math
import numpy as np
EXE=Path('D:/ms_xsp/s04_crosscheck_20261017/Spice64/bin/ngspice_con.exe')
ROOT=Path(r'D:\实验报告文件夹\电路2\tmp\lc02'); WORK=ROOT/'work'
MDL=Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage4_rf_oscillator\advance_20261029\2N3904_UNCG.lib').read_text(encoding='ascii').strip()
F0=31e6
def readraw(p):
    with open(p,'rb') as f:
        names=[];inside=False
        while True:
            s=f.readline().decode('ascii').strip()
            if s=='Binary:':break
            if s=='Variables:':inside=True;continue
            if inside and s:names.append(s.split()[1].lower())
        a=np.fromfile(f,dtype='<f8').reshape(-1,len(names))
    return {n:a[:,i] for i,n in enumerate(names)}
def run(name,src):
    (ROOT/'cir'/(name+'.cir')).write_text(src,encoding='ascii')
    (WORK/(name+'.cir')).write_text(src,encoding='ascii')
    raw=WORK/(name+'.raw')
    if raw.exists(): raw.unlink()
    subprocess.run([str(EXE),'-b','-n','-o',str(WORK/(name+'.log')),str(WORK/(name+'.cir'))],
                   cwd=WORK,capture_output=True,timeout=900,creationflags=subprocess.CREATE_NO_WINDOW)
    if not raw.exists(): return None
    d=readraw(raw); t=d['time']; e=d['v(out)']; stop=t[-1]
    return [float(np.ptp(e[(t>=a*stop)&(t<(a+0.06)*stop)])) for a in [0.02,0.1,0.2,0.35,0.5,0.7,0.9]]

HDR='''VSUP vcc 0 PWL(0 0 1u 5)
R1 vcc b 10k
R2 b 0 10k
Q1 vcc b e 2N3904
R3 e 0 4.7k
C1 b e 33p
C2 e 0 33p
C3 vcc 0 100n
C4 vcc 0 10u
COUT e out 1n
RLOAD out 0 2000
CLOAD out 0 10p
'''
TAIL=f'''{MDL}
.options method=trap maxord=2 reltol=1e-3 trtol=7 temp=27 tnom=27
.control
set filetype=binary
set num_threads=1
save v(vcc) v(b) v(e) v(out) i(vsup)
tran 0.25n 600u 0 0.25n uic
write NAME.raw
quit
.endc
.end
'''
cm=10e-15;c0=3e-12;cl=18e-12
fs=31e6/math.sqrt(1+cm/(cl+c0));lm=1/((2*math.pi*fs)**2*cm)
xtal=f'''* control: crystal (known-good)
{HDR}CSTRAY b 0 1p
CX0 b 0 3p
VXM b xr 0
RM xr xl 30
LM xl xc {lm:.16g}
CM xc 0 10f
'''+TAIL.replace("NAME","ctl_xtal")
lc_ideal=f'''* control: ideal L (rings, not oscillation)
{HDR}CBLK b nL 1000p
L1 nL 0 1280.07n
'''+TAIL.replace("NAME","ctl_ideal")
print("=== POSITIVE CONTROLS: same harness, 600 us, out Vpp in 7 windows ===")
print("%-22s %8s %8s %8s %8s %8s %8s %8s"%("control","2%","10%","20%","35%","50%","70%","90%"))
for nm,src in [("crystal",xtal),("ideal L (lossless)",lc_ideal)]:
    r=run(nm,src)
    if r is None: print("%-22s FAILED"%nm); continue
    print("%-22s %8.4f %8.4f %8.4f %8.4f %8.4f %8.4f %8.4f"%(nm,*r))

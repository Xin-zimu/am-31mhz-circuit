
# -*- coding: utf-8 -*-
"""Confirm: is the oscillation sustained ONLY because Re(Z)>0 (no negative resistance at all)?
   And how does the tank loss compare with the active network's positive resistance?"""
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
    if 'complex' in flags: a=a.reshape(-1,len(names),2); z=a[:,:,0]+1j*a[:,:,1]
    else: z=a.reshape(-1,len(names))
    return {n:z[:,i] for i,n in enumerate(names)}
def run(name,src,raw):
    (ROOT/'cir'/(name+'.cir')).write_text(src,encoding='ascii')
    (WORK/(name+'.cir')).write_text(src,encoding='ascii')
    p=WORK/raw
    if p.exists(): p.unlink()
    subprocess.run([str(EXE),'-b','-n','-o',str(WORK/(name+'.log')),str(WORK/(name+'.cir'))],
                   cwd=WORK,capture_output=True,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
    return p.exists(),(WORK/(name+'.log')).read_text(errors='replace')

# sweep the Colpitts divider ratio and RE to look for negative resistance
def znet(C1,C2,RE,NAME):
    return f'''* Znet sweep
VSUP vcc 0 5
R1 vcc b 10k
R2 b 0 10k
Q1 vcc b e 2N3904
R3 e 0 {RE}
C1 b e {C1}p
C2 e 0 {C2}p
CT e 0 0.5p
CBLK b nL 1000p
C3 vcc 0 100n
C4 vcc 0 10u
IAC nL 0 ac 1
{MDL}
.options method=trap maxord=2 reltol=1e-3 trtol=7 temp=27 tnom=27
.control
set filetype=binary
ac dec 400 25meg 40meg
write z_{NAME}.raw v(nL)
quit
.endc
.end
'''
print("=== does ANY bias point give negative resistance at the tank node? ===")
print("%-22s %14s %14s"%("C1/C2/RE","Re(Z)@31MHz","min Re(Z)"))
best=None
for C1,C2,RE in [(33,33,"4.7k"),(33,33,"1k"),(33,33,"220"),(100,33,"4.7k"),(220,33,"4.7k"),
                 (470,33,"4.7k"),(1000,33,"4.7k"),(33,100,"4.7k"),(33,220,"4.7k"),(33,1000,"4.7k"),
                 (100,100,"1k"),(470,100,"1k"),(1000,100,"220")]:
    nm="z_%d_%d_%s"%(C1,C2,RE.replace('.','p'))
    ok,log=run(nm, znet(C1,C2,RE,nm), 'z_%s.raw'%nm)
    if not ok: print("%-22s FAILED"%("%d/%d/%s"%(C1,C2,RE))); continue
    d=readraw(WORK/('z_%s.raw'%nm))
    f=d['frequency']; z=d['v(nl)']
    k=np.argmin(np.abs(f-F0))
    print("%-22s %+14.3f %+14.3f"%("%d pF / %d pF / %s"%(C1,C2,RE), z.real[k], z.real.min()))
    if best is None or z.real.min()<best[0]: best=(z.real.min(),C1,C2,RE)
print("\n  most negative Re(Z) found: %.3f ohm  at C1=%d C2=%d RE=%s"%(best[0],best[1],best[2],best[3]))
if best[0]>=0: print("  -> NO bias point tested gives negative resistance. This topology cannot sustain oscillation.")
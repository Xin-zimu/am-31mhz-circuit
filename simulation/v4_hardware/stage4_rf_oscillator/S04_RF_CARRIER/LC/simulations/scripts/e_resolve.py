
# -*- coding: utf-8 -*-
"""Resolve the Re(Z) contradiction: 'op' before 'ac' vs automatic OP; also series-source method."""
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
BODY='''VSUP vcc 0 5
R1 vcc b 10k
R2 b 0 10k
Q1 vcc b e 2N3904
R3 e 0 {RE}
C1 b e 33p
C2 e 0 33p
CT e 0 0.5p
CBLK b nL 1000p
C3 vcc 0 100n
C4 vcc 0 10u
'''
def run(name,src,raw):
    (ROOT/'cir'/(name+'.cir')).write_text(src,encoding='ascii')
    (WORK/(name+'.cir')).write_text(src,encoding='ascii')
    p=WORK/raw
    if p.exists(): p.unlink()
    subprocess.run([str(EXE),'-b','-n','-o',str(WORK/(name+'.log')),str(WORK/(name+'.cir'))],
                   cwd=WORK,capture_output=True,timeout=300,creationflags=subprocess.CREATE_NO_WINDOW)
    return p.exists()

def mk(RE, with_op, rawname):
    pre = "op\n" if with_op else ""
    return (f'''* Znet RE={RE} op={with_op}
'''+BODY.replace("{RE}",RE)+f'''IAC nL 0 ac 1
{MDL}
.options method=trap maxord=2 reltol=1e-3 trtol=7 temp=27 tnom=27
.control
set filetype=binary
{pre}ac dec 800 20meg 45meg
write {rawname} v(nL)
quit
.endc
.end
''')

print("=== Re(Z) at tank node: does 'op' change the answer? ===")
for RE in ["4.7k","1k"]:
    for w in [True,False]:
        raw="zz_%s_%d.raw"%(RE.replace('.','p'),int(w))
        ok=run("zz_%s_%d"%(RE.replace('.','p'),int(w)), mk(RE,w,raw), raw)
        if not ok: print("  RE=%s op=%s FAILED"%(RE,w)); continue
        d=readraw(WORK/raw); f=d['frequency']; z=d['v(nl)']
        k=np.argmin(np.abs(f-F0))
        print("  RE=%-6s op=%-5s : Re(Z)@31MHz = %+9.3f   min Re(Z)=%+9.3f  (points=%d)"%(
            RE,w,z.real[k],z.real.min(),len(f)))

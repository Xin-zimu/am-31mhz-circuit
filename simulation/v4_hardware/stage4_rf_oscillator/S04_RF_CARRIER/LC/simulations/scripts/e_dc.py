
# -*- coding: utf-8 -*-
"""Which Re(Z) matches the .ic-seeded transient reality?  And check the OP is sane."""
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
                   cwd=WORK,capture_output=True,timeout=300,creationflags=subprocess.CREATE_NO_WINDOW)
    log=(WORK/(name+'.log')).read_text(errors='replace')
    return (p.exists(),log)

# DC operating point WITHOUT the L (the network the AC analysis sees)
def dconly(RE):
    return f'''* DC op, no L
VSUP vcc 0 5
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
{MDL}
.control
op
print v(b) v(e) v(nL) @r3[i]
quit
.endc
.end
'''
print("=== DC operating point with the L branch open (AC sees this) ===")
for RE in ["4.7k","1k"]:
    nm="dc_"+RE.replace('.','p')
    ok,log=run(nm,dconly(RE),"none")
    vals=[]
    for l in log.splitlines():
        p=l.split()
        if len(p)>=3 and p[1]=='=':
            try: vals.append((p[0],float(p[2])))
            except: pass
    print("  RE=%-6s : %s"%(RE,", ".join("%s=%.4f"%(k.split('.')[-1],v) for k,v in vals)))
    # The circuit has NO DC path to ground at nL except through b (via CBLK blocks DC!)
    # -> nL floats. Report it.
print("\n  NOTE: CBLK blocks DC. With the L branch open the node nL has NO DC path at all.")
print("  An 'op' on such a floating node gives a meaningless (solver-chosen) point.")

# -*- coding: utf-8 -*-
"""Find which project element makes model B stall."""
import os, sys, time, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from ltraw import run, log
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
B=os.path.join(STAGE,"bench","iso")
SUP="VADP ADP 0 5\nVADN ADN 0 -5\n"
XNET="""RXA V1 XA 100k
RXB XA VN5 125k
RXC XA 0 12.947k
VXBIAS VN5 0 -5
"""
def T(name, body, analysis, to=70):
    p=os.path.join(B,name+".net")
    open(p,"w",encoding="utf-8").write("* iso\n"+body+"\n.options plotwinsize=0\n"+analysis+"\n.end\n")
    t0=time.time()
    try: r=run(p,ascii=False,timeout=to)
    except Exception: print("%-26s TIMEOUT(%ds)"%(name,to)); return None
    print("%-26s rc=%d %5.1fs"%(name,r.returncode,time.time()-t0))
    return r.returncode

# B1: subckt + 31MHz carrier through 470+680 network (like project TP2) + X net
print("--- progressively adding project elements ---")
T("s1_sine31", ".include ../../adapted/AD835_Behav.sub\n"+SUP+
  "VC TP2 0 SIN(0 1 31meg)\n"+XNET+
  "VX1x V1 0 PULSE(0.0748 4.0748 1u 1n 1n 5u 50u)\n"
  "XU XA 0 TP2 0 ADN TP2 TP3 ADP AD835_BEHAV\nRL TP3 0 150\n",
  ".tran 0 40u 0 0.5n")

T("s2_sine31_nox", ".include ../../adapted/AD835_Behav.sub\n"+SUP+
  "VC TP2 0 SIN(0 1 31meg)\n"
  "VXA XA 0 SIN(0 0.1 20k)\n"
  "XU XA 0 TP2 0 ADN TP2 TP3 ADP AD835_BEHAV\nRL TP3 0 150\n",
  ".tran 0 40u 0 0.5n")

T("s3_pulse31", ".include ../../adapted/AD835_Behav.sub\n"+SUP+
  "VC TP2 0 PULSE(-1 1 0 1n 1n 16.1n 32.3n)\n"
  "VXA XA 0 0\n"
  "XU XA 0 TP2 0 ADN TP2 TP3 ADP AD835_BEHAV\nRL TP3 0 150\n",
  ".tran 0 40u 0 0.5n")

# B2: LM393 baseband alone
print("\n--- baseband front-end alone (from frozen netlist) ---")

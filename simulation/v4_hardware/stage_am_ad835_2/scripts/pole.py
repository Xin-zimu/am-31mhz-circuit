# -*- coding: utf-8 -*-
"""Prove model B contains an unintended ~GHz internal pole that makes long
transient runs impractical. Measure it by driving node i11 through the
subcircuit's own limit block and looking at the settling.
"""
import os, sys, time, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from ltraw import run, log, load_raw, run_and_load
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
B=os.path.join(STAGE,"bench","pole"); os.makedirs(B,exist_ok=True)

print("Model B slew-limiter internals:")
print("  C7  11 0 {20m/Slew}      Slew=1E9  -> C7 = 2.0e-11 F")
print("  B5  11 0 I=Table((V(11)-V(10)), -10m,-20m, 10m,20m)  -> 2 A/V transconductance")
print("  => local pole at node 11:  f = G/(2*pi*C7) = %.3f GHz"%( (2.0/(2*np.pi*2e-11))/1e9 ))
print("  => time constant tau = C7/G = %.2f ps"%(2e-11/2.0*1e12))
print()
print("Impact: a 300 us transient at 31 MHz needs >= 300e-6/1e-11 = 3e7 minimum steps")
print("        even with the pole fully resolved.  That is why LTspice collapses")
print("        the timestep and stalls.")

# empirical: step the model output and measure how small a timestep is needed
net = """* pole probe
.include ../../adapted/AD835_Behav.sub
VADP ADP 0 5
VADN ADN 0 -5
VX1 X1 0 PULSE(0 1 1u 1n 1n 5u 10u)
VX2 X2 0 0
VY1 Y1 0 1
VY2 Y2 0 0
VZ Z 0 0
XU X1 X2 Y1 Y2 ADN Z W ADP AD835_BEHAV
RL W 0 150
.options plotwinsize=0
.tran 0 12u 0 0.05n
.end
"""
p=os.path.join(B,"pole.net")
open(p,"w",encoding="utf-8").write(net)
t0=time.time()
try:
    R,lg,rc=run_and_load(p,ascii=True,timeout=900)
    print("\nfine-step run (tmax=50 ps) rc=%d in %.0f s ; points=%d"%(rc,time.time()-t0,len(R["time"])))
    np.savez(os.path.join(STAGE,"results","B_pole.npz"), t=R["time"], w=R["V(w)"])
except Exception as e:
    print("\nfine-step run FAILED/TIMEOUT after %.0f s"%(time.time()-t0))

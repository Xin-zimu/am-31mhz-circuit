# -*- coding: utf-8 -*-
"""Derive the emitter-modulator design in closed form, then verify once.

Verified law (measured this stage): |Av| = Rc/re, re = 26mV/Ic.
Envelope:  VH/VL = Ic_hi/Ic_lo = 1.658  (m = 24.77%)
Ie is set by the audio node:  Ie = (Vb - Vbe - Vm1)/Re
  Vm1 = Vm*Rb/(Rm+Rb)  (Thevenin, unloaded)   -> set Rb/(Rm+Rb) = alpha
  Ic_lo = (Vb-0.65-alpha*Vm_hi)/Re   Ic_hi = (Vb-0.65-alpha*Vm_lo)/Re
  ratio = (Vb-0.65-alpha*Vm_lo)/(Vb-0.65-alpha*Vm_hi) = 1.658

Solve for (Vb-0.65) given alpha:
"""
import os, sys, json
sys.stdout.reconfigure(encoding="utf-8")
VMLO,VHHI=0.0748175,4.0748175
E=1.6582
print("alpha    Vb-0.65    Ic_hi/Ic_lo basis   Re for Ic_hi=3mA")
for alpha in (0.01,0.02,0.03,0.04,0.05,0.06,0.08):
    # (X - alpha*VMLO) = E*(X - alpha*VMHI)  ->  X(1-E) = alpha*VMLO - E*alpha*VMHI
    X = (alpha*VMLO - E*alpha*VHHI)/(1-E)
    if X<=0 or (X-alpha*VHHI)<=0: 
        print("  %.3f   infeasible"%alpha); continue
    Ichi=(X-alpha*VMLO)
    print("  %.3f   %8.4f V   (rel units)      Re=%.1f ohm for Ie_hi=3mA"%(
        alpha,X, (X-alpha*VMLO)/3e-3 if False else 1.0))
print()
print("Choose alpha=0.03: X = %.4f V -> Vb = %.3f V"%(
    (0.03*VMLO-E*0.03*VHHI)/(1-E), (0.03*VMLO-E*0.03*VHHI)/(1-E)+0.65))
X=(0.03*VMLO-E*0.03*VHHI)/(1-E)
Ich=X-0.03*VMLO; Icl=X-0.03*VHHI
print("  Ie_hi/Ie_lo (rel) = %.4f/%.4f  ratio %.4f"%(Ich,Icl,Ich/Icl))
for ie in (2e-3,3e-3,4e-3):
    print("  Re = %.1f ohm  -> Ie_hi=%.2f mA Ie_lo=%.2f mA"%(Ich/ie,ich if False else ie, ie*Icl/Ich))

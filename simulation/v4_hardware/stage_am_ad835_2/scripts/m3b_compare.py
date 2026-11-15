# -*- coding: utf-8 -*-
"""Module 3b: compare model AC response against digitized datasheet Fig.5/Fig.6."""
import os, sys, json, numpy as np
sys.stdout.reconfigure(encoding="utf-8")
R=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2\results"
S=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2\sources"
ds=json.load(open(os.path.join(S,"datasheet_curves.json")))
print("datasheet Fig5 gain dB :", {k:round(v,3) for k,v in ds["fig5_gain_dB"].items()})
print("datasheet Fig5 phase deg:", {k:round(v,2) for k,v in ds["fig5_phase_deg"].items()})
print("datasheet Fig6 gain dB :", {k:round(v,3) for k,v in ds["fig6_gain_dB"].items()})
print()
# model single-pole fit: |H| = 1/sqrt(1+(f/fc)^2), phase = -atan(f/fc)
# Extract fc from model data at 100 MHz:  |H|=-0.645 dB  -> (f/fc)^2 = 10^(0.645/10)-1
m100=10**(-0.645/20.0)
fc=100e6/np.sqrt(1/m100**2-1)
print("Model (both A and B) single-pole equivalent fc = %.2f MHz"%(fc/1e6))
print("  => -3 dB at %.1f MHz (datasheet: 250 MHz typ, 150 MHz min)"%(fc/1e6))
print()
for target in (1e7,3.1e7,1e8):
    ph_model=-np.degrees(np.arctan(target/fc))
    g_model=20*np.log10(1/np.sqrt(1+(target/fc)**2))
    key=[k for k in ds["fig5_gain_dB"] if abs(float(k)-target)<1][0]
    g_ds=ds["fig5_gain_dB"][key]; p_ds=ds["fig5_phase_deg"][key]
    print("%6.1f MHz : model gain %+6.3f dB / datasheet %+6.3f dB  -> diff %+6.3f dB"%(target/1e6,g_model,g_ds,g_model-g_ds))
    print("             model phase %+6.2f deg / datasheet %+6.2f deg -> diff %+6.2f deg"%(ph_model,p_ds,ph_model-p_ds))

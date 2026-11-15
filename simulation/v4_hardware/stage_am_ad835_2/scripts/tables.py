# -*- coding: utf-8 -*-
"""Emit the final consolidated numeric tables used in the report."""
import os, sys, json, numpy as np
sys.stdout.reconfigure(encoding="utf-8")
RES=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2\results"
m2=json.load(open(os.path.join(RES,"M2.json")))
print("=== M2 swings (Z sweep, X=Y=0) ===")
for k in sorted(m2):
    if k.startswith("swing_"):
        print("  %-12s +%.4f / %.4f"%(k,m2[k]["hi"],m2[k]["lo"]))
print("\n=== M2 bias currents (A into part) ===")
for k in ("ibias_A","ibias_B"):
    if k in m2: print("  %s %s"%(k,{kk:round(vv*1e6,2) for kk,vv in m2[k].items() if kk.startswith("I")}))
print("\n=== M13 envelopes ===")
e=json.load(open(os.path.join(RES,"M13_env.json")))
for k,v in e.items():
    print("  %-11s VH=%7.4f VL=%7.4f m=%6.3f%%  THD=%5.3f%%  LSB=%s USB=%s"%(
        k,v["VH"],v["VL"],v["m"],v["thd"],
        ("%.1f"%v["lsb_dBc"]) if v["lsb_dBc"] else "n/a",
        ("%.1f"%v["usb_dBc"]) if v["usb_dBc"] else "n/a"))
print("\n=== M14 loads ===")
lp=json.load(open(os.path.join(RES,"M14_load_power.json")))
for k,v in lp.items():
    if v: print("  %-8s VH=%.4f VL=%.4f m=%.2f%% Pload=%.3f mW"%(k,v["VH"],v["VL"],v["m"],v["Prload"]*1e3))
print("\n=== M14 L50p10 ===")
print(" ",json.load(open(os.path.join(RES,"M14_L50p10.json"))))

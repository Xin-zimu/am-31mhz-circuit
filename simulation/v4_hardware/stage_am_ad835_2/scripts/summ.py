# -*- coding: utf-8 -*-
"""Consolidate every measured number into one machine-readable summary."""
import os, sys, json, numpy as np
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
RES=os.path.join(STAGE,"results")
def L(n):
    p=os.path.join(RES,n)
    return json.load(open(p)) if os.path.exists(p) and os.path.getsize(p)>0 else None
summary={
 "datasheet_curves": L("datasheet_curves.json"),
 "M1_dc": "see M1_dc.json",
 "M2": L("M2.json"),
 "M3_ac_31MHz": {},
 "M13_env": L("M13_env.json"),
 "M14_load_power": L("M14_load_power.json"),
 "M14_L50p10": L("M14_L50p10.json"),
 "M15_power": L("M15_power.json"),
}
ac=L("M3_ac.json")
if ac:
    for m in ("A","B"):
        f=np.array(ac["acX_"+m]["f"]); mag=np.array(ac["acX_"+m]["mag"]); ph=np.array(ac["acX_"+m]["ph"])
        i=int(np.argmin(abs(np.log10(f)-np.log10(31e6))))
        summary["M3_ac_31MHz"][m]={"f":float(f[i]),"mag":float(mag[i]),"dB":float(20*np.log10(mag[i]/mag[0])),
                                   "phase":float(ph[i]),"dc_gain":float(mag[0])}
m2=L("M2.json")
brief={}
if m2:
    for k in m2:
        if k.startswith(("swing_","ibias_")):
            v=m2[k]
            if isinstance(v,dict):
                brief[k]={kk:(vv if not isinstance(vv,list) else None) for kk,vv in v.items()}
summary["M2_brief"]=brief
json.dump(summary,open(os.path.join(RES,"SUMMARY.json"),"w"),indent=1)
print(json.dumps(summary["M3_ac_31MHz"],indent=1))
print(json.dumps(summary["M15_power"],indent=1))
print("\nwrote SUMMARY.json")

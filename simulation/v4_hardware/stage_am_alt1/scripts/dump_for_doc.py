# -*- coding: utf-8 -*-
import os, sys, json
sys.stdout.reconfigure(encoding="utf-8")
ST=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_alt1\results"
for f in ("solid_findings.json","mechanism.json","solved.json","bias_grid.json","converge.json","gain_grid.json","final_grid.json","emod_final.json"):
    p=os.path.join(ST,f)
    if not os.path.exists(p): print(f,"MISSING"); continue
    print("="*70); print(f)
    print(json.dumps(json.load(open(p)),indent=1)[:1800])

# -*- coding: utf-8 -*-
import os, sys, json
sys.stdout.reconfigure(encoding="utf-8")
ST=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_alt1"
for f in ("c4_load_sweep.json","ref_and_zout.json","emod_grid.json","emod_final.json","collector_grid.json","emitter_grid2.json"):
    p=os.path.join(ST,"results",f)
    if os.path.exists(p):
        d=json.load(open(p))
        print("==",f)
        print(json.dumps(d,indent=1)[:1200])

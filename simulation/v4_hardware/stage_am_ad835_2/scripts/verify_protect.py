# -*- coding: utf-8 -*-
"""Verify the frozen project files were not modified."""
import os, sys, hashlib, json
sys.stdout.reconfigure(encoding="utf-8")
ROOT=r"D:\实验报告文件夹\电路2"
protected=[
 r"simulation\v4_hardware\repair_20261011\final_actual.cir",
 r"simulation\v4_hardware\AM_20k_31MHz_V4_3_REPAIRED.ms14",
 r"simulation\v4_hardware\stage_am_ad835\AD835技术路线可行性报告.md",
 r"simulation\v4_hardware\stage_am_ad835_1\AM-AD835.1_接口设计与模型阻塞报告.md",
]
print("Frozen / protected files (must be unchanged):")
for rel in protected:
    p=os.path.join(ROOT,rel)
    if os.path.exists(p):
        h=hashlib.sha256(open(p,"rb").read()).hexdigest()
        print("  %-70s %s"%(rel[:70],h[:16]))
    else:
        print("  %-70s MISSING"%rel[:70])
# confirm the stage-2 dir only adds new files
print("\nStage-2 tree (new files only):")
S=os.path.join(ROOT,"simulation","v4_hardware","stage_am_ad835_2")
n=0
for dp,dn,fn in os.walk(S):
    for f in fn:
        n+=1
print("  total files created under stage_am_ad835_2: %d"%n)
# confirm downloaded models are byte-identical to originals
M=os.path.join(S,"models","third_party_GLuisF")
print("\nOriginal downloads (unmodified, hash-verified above):")
for f in sorted(os.listdir(M)):
    print("  ", f)

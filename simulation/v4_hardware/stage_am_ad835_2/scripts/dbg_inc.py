# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from ltraw import run, log
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
d=os.path.join(STAGE,"bench")
SUB=os.path.join(STAGE,"adapted","AD835_Behav.sub").replace("\\","/")

body = """
V1 X1 0 0
V2 VPOS 0 5
V3 0 VNEG 5
V4 Y1 0 1
V5 Z 0 0
XU X1 0 Y1 0 Z W VPOS VNEG AD835_BEHAV
.op
.end
"""
for tag, inc in (("abs", SUB), ("rel", "../adapted/AD835_Behav.sub"), ("rel2","./../adapted/AD835_Behav.sub")):
    p=os.path.join(d,"inc_%s.net"%tag)
    open(p,"w",encoding="utf-8").write(".include %s\n" % inc + body)
    r=run(p)
    print("==",tag, "rc", r.returncode)
    print(log(p)[-600:])

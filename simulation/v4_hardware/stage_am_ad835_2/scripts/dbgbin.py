# -*- coding: utf-8 -*-
import os,sys
sys.path.insert(0, os.path.dirname(__file__))
from ltraw import run
sys.stdout.reconfigure(encoding="utf-8")
d=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2\bench"
p=os.path.join(d,"chk.net")
run(p, ascii=False)
raw=open(os.path.join(d,"chk.raw"),"rb").read()
print("size", len(raw))
print(repr(raw[:400]))

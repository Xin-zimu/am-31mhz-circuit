# -*- coding: utf-8 -*-
import fitz, sys, json, math
import numpy as np
sys.stdout.reconfigure(encoding="utf-8")
src = r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835\sources\ad835.pdf"
doc = fitz.open(src)
p = doc[6]
dr = p.get_drawings()
print("=== candidate frames / curves in right column (x>350, y<520) ===")
for k, dd in enumerate(dr):
    r = dd["rect"]
    if r.x0 > 350 and r.y1 < 520:
        print(k, dd.get("type"), [round(v,1) for v in r], "n=", len(dd["items"]), "w=", round(dd.get("width") or 0,2))

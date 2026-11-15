# -*- coding: utf-8 -*-
import fitz, sys
sys.stdout.reconfigure(encoding="utf-8")
src = r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835\sources\ad835.pdf"
doc = fitz.open(src)
p = doc[6]
dr = p.get_drawings()
dd = dr[74]
for i, it in enumerate(dd["items"]):
    if it[0] == "l":
        print(i, "l", (round(it[1].x,2), round(it[1].y,2)), "->", (round(it[2].x,2), round(it[2].y,2)))
    else:
        print(i, it[0], "OTHER")

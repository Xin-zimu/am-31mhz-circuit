# -*- coding: utf-8 -*-
import fitz, sys
sys.stdout.reconfigure(encoding="utf-8")
src = r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835\sources\ad835.pdf"
doc = fitz.open(src); p = doc[6]
for blk in p.get_text("dict")["blocks"]:
    if blk["type"]!=0: continue
    for ln in blk["lines"]:
        for sp in ln["spans"]:
            t = sp["text"].strip()
            if not t: continue
            b = sp["bbox"]
            if (345 < b[0] < 575) and (90 < b[1] < 460):
                print("%-22s" % t, [round(v,1) for v in b])

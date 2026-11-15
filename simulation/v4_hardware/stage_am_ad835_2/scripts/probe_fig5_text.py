import fitz
src = r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835\sources\ad835.pdf"
doc = fitz.open(src)
p = doc[6]
d = p.get_text("dict")
for blk in d["blocks"]:
    if blk["type"] != 0: continue
    for ln in blk["lines"]:
        for sp in ln["spans"]:
            t = sp["text"].strip()
            if not t: continue
            b = sp["bbox"]
            if b[1] > 495 and b[1] < 700 and b[2] < 340:
                print(repr(t), [round(v,1) for v in b], "size", round(sp["size"],1))

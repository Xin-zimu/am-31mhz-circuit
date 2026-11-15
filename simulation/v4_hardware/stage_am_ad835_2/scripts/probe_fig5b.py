import fitz
src = r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835\sources\ad835.pdf"
doc = fitz.open(src)
p = doc[6]
print("--- all drawings y0>520, x1<340 ---")
for k, dd in enumerate(p.get_drawings()):
    r = dd["rect"]
    if r.y0 > 515 and r.x1 < 345:
        print(k, dd.get("type"), [round(v,1) for v in r], "n=", len(dd["items"]), "w=", round(dd.get("width") or 0,2))

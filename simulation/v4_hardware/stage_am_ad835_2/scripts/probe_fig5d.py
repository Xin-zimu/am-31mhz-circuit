import fitz
src = r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835\sources\ad835.pdf"
doc = fitz.open(src)
p = doc[6]
print("--- ALL drawings with y0 between 500 and 760 ---")
for k, dd in enumerate(p.get_drawings()):
    r = dd["rect"]
    if 500 < r.y0 < 780 and r.x0 < 400:
        print(k, dd.get("type"), [round(v,1) for v in r], "n=", len(dd["items"]), "w=", round(dd.get("width") or 0,2))

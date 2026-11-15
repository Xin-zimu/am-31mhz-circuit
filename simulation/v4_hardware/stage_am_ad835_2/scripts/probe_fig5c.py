import fitz, json
src = r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835\sources\ad835.pdf"
doc = fitz.open(src)
p = doc[6]
print("--- vertical gridlines in fig5 ---")
for k, dd in enumerate(p.get_drawings()):
    r = dd["rect"]
    if r.y0 > 515 and r.y0 < 560 and r.y1 > 690 and r.x0 < 300:
        print("V", k, [round(v,1) for v in r], "n=", len(dd["items"]), "w=", round(dd.get("width") or 0,2))
print("--- bottom axis line ---")
for k, dd in enumerate(p.get_drawings()):
    r = dd["rect"]
    if 690 < r.y0 < 710 and r.x0 < 300 and r.x1 > 200:
        print("B", k, [round(v,1) for v in r], "n=", len(dd["items"]), "w=", round(dd.get("width") or 0,2))

import fitz
src = r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835\sources\ad835.pdf"
doc = fitz.open(src)
p = doc[6]
print("--- page 7: drawings in lower-left quadrant (fig5), n_items>5 ---")
for k, dd in enumerate(p.get_drawings()):
    r = dd["rect"]
    if r.y0 > 500 and r.x0 < 330:
        n = len(dd["items"])
        if n > 5:
            print(k, dd.get("type"), "rect=", [round(v,1) for v in r], "n=", n, "w=", round(dd.get("width") or 0,3))

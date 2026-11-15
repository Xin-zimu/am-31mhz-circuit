import fitz
src = r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835\sources\ad835.pdf"
doc = fitz.open(src)
for i in range(14):
    p = doc[i]
    d = p.get_drawings()
    im = p.get_images(full=True)
    print("page", i+1, "drawings:", len(d), "images:", len(im))
p = doc[6]
print("--- page 7 drawings summary ---")
for k, dd in enumerate(p.get_drawings()):
    items = dd["items"]
    print(k, dd.get("type"), "rect=", [round(v,1) for v in dd["rect"]], "n_items=", len(items), "width=", dd.get("width"), "color=", dd.get("color"), "fill=", dd.get("fill"))
    if k > 40: 
        print("...")
        break

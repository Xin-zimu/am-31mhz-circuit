import fitz, os
src = r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835\sources\ad835.pdf"
outdir = r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2\sources\pages"
doc = fitz.open(src)
p = doc[6]
R = p.rect
print("page rect", R)
# render full page at 600 dpi
pix = p.get_pixmap(dpi=600)
pix.save(os.path.join(outdir,"p7_600.png"))
print("full", pix.width, pix.height)

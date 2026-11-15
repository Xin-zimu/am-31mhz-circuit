import fitz, os
src = r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835\sources\ad835.pdf"
outdir = r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2\sources\pages"
os.makedirs(outdir, exist_ok=True)
doc = fitz.open(src)
for i in [6,7,8]:
    p = doc[i]
    pix = p.get_pixmap(dpi=200)
    f = os.path.join(outdir, "page%d.png" % (i+1))
    pix.save(f)
    print(f, pix.width, pix.height)

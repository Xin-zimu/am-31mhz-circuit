import fitz, os
src = r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835\sources\ad835.pdf"
outdir = r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2\sources\pages"
os.makedirs(outdir, exist_ok=True)
doc = fitz.open(src)
jobs = [(6,"fig5_6_7"),(7,"fig8_9_10_11_12_13_14"),(8,"fig15_17_18")]
for i, name in jobs:
    p = doc[i]
    pix = p.get_pixmap(dpi=300)
    f = os.path.join(outdir, name + ".png")
    pix.save(f)
    print(f, pix.width, pix.height)

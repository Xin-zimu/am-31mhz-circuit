import fitz, os
src = r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835\sources\ad835.pdf"
outdir = r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2\sources\pages"
doc = fitz.open(src)
p = doc[6]
# Figure 5 is bottom-left chart. Page is 612x792 pt. Chart approx x 60..300, y 545..700
clip = fitz.Rect(48, 540, 320, 715)
pix = p.get_pixmap(dpi=900, clip=clip)
f = os.path.join(outdir, "fig5_zoom.png")
pix.save(f)
print(f, pix.width, pix.height)

# Figure 6 upper right
clip2 = fitz.Rect(360, 120, 600, 300)
pix2 = p.get_pixmap(dpi=900, clip=clip2)
f2 = os.path.join(outdir, "fig6_zoom.png")
pix2.save(f2)
print(f2, pix2.width, pix2.height)

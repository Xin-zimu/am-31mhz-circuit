# -*- coding: utf-8 -*-
import json, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
sys.stdout.reconfigure(encoding="utf-8")
base = r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2\sources"
ov = json.load(open(base + r"\fig5_overlay.json"))
img = np.array(Image.open(base + r"\pages\fig5_overlay_base.png").convert("L"))
sc = ov["scale"]; x0,y0 = ov["clip"][0], ov["clip"][1]
H, W = img.shape
fig = plt.figure(figsize=(W/150, H/150), dpi=150)
ax = fig.add_axes([0,0,1,1]); ax.imshow(img, cmap="gray"); ax.axis("off")
def px(f, y_pdf):
    x_pdf = 59.45*np.log10(f) + (142.8 - 7*59.45)
    return (x_pdf - x0)*sc, (y_pdf - y0)*sc
g = np.array(ov["gain"]); ph = np.array(ov["phase"])
gx, gy = px(g[:,0], 563.2 - g[:,1]*7.16667)
ax.plot(gx, gy, lw=0.7, color="red", alpha=0.9)
px_, py_ = px(ph[:,0], 577.45 - ph[:,1]/90.0*14.3625)
ax.plot(px_, py_, lw=0.7, color="deepskyblue", alpha=0.9)
for t in [1e7, 3.1e7, 1e8]:
    xx,_ = px(t, 0)
    ax.axvline(xx, color="lime", lw=0.5, alpha=0.8)
fig.savefig(base + r"\pages\fig5_overlay.png", dpi=150)
print("saved. img", W, H)

# -*- coding: utf-8 -*-
import fitz, sys, json, math
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
sys.stdout.reconfigure(encoding="utf-8")
src = r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835\sources\ad835.pdf"
OUT = r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2\sources"
doc = fitz.open(src)

def bez(p0,p1,p2,p3,n=60):
    t=np.linspace(0,1,n); mt=1-t
    return list(zip(mt**3*p0[0]+3*mt*mt*t*p1[0]+3*mt*t*t*p2[0]+t**3*p3[0],
                    mt**3*p0[1]+3*mt*mt*t*p1[1]+3*mt*t*t*p2[1]+t**3*p3[1]))
def trace(dd, tol=0.4):
    sps=[]; cur=[]
    for it in dd["items"]:
        if it[0]=="l":
            a=(it[1].x,it[1].y); b=(it[2].x,it[2].y)
            if cur and (abs(cur[-1][0]-a[0])>tol or abs(cur[-1][1]-a[1])>tol):
                if len(cur)>2: sps.append(cur)
                cur=[]
            if not cur: cur=[a]
            cur.append(b)
        elif it[0]=="c":
            p0=(it[1].x,it[1].y);p1=(it[2].x,it[2].y);p2=(it[3].x,it[3].y);p3=(it[4].x,it[4].y)
            if cur and (abs(cur[-1][0]-p0[0])>tol or abs(cur[-1][1]-p0[1])>tol):
                if len(cur)>2: sps.append(cur)
                cur=[]
            pts=bez(p0,p1,p2,p3,60)
            if not cur: cur=[pts[0]]
            cur.extend(pts)
    if len(cur)>2: sps.append(cur)
    return sps
def interp_at(sp, target, xa, xb, y2v):
    arr=sorted((10**((x-xb)/xa), y2v(y)) for x,y in sp)
    xs=np.log10(np.array([a[0] for a in arr])); ys=np.array([a[1] for a in arr])
    ux,inv=np.unique(np.round(xs,9),return_inverse=True)
    uy=np.array([ys[inv==i].mean() for i in range(len(ux))])
    return float(np.interp(math.log10(target),ux,uy))

p7=doc[6]; d7=p7.get_drawings()
res={}

# Figure 5  (left axis dB: 0dB@y=563.2, 7.2px/dB ; right axis deg: 0deg@y=577.6, 14.325px/90deg)
A5=59.45; B5=142.8-7*A5
y2db5=lambda y:(563.2-y)/7.2
y2deg5=lambda y:(577.6-y)/14.325*90.0
sp5=trace(d7[74]); gain5, phase5 = sp5[0], sp5[1]
pre5=[q for q in phase5 if q[0]<=240.0]
Fs=[1e6,5e6,1e7,1.5e7,2e7,2.5e7,3.1e7,4e7,5e7,7e7,1e8]
res["fig5_gain_dB"]={str(f):round(interp_at(gain5,f,A5,B5,y2db5),3) for f in Fs}
res["fig5_phase_deg"]={str(f):round(interp_at(pre5,f,A5,B5,y2deg5),2) for f in Fs}

# Figure 6  (0dB@y=145.5, 14.2167px per 0.1dB -> 142.167px/dB)
A6=50.575; B6=399.5-6*A6
y2db6=lambda y:(145.5-y)/142.167
sp6=trace(d7[103])
res["fig6_gain_dB"]={str(f):round(interp_at(sp6[0],f,A6,B6,y2db6),3) for f in [3e5,1e6,3e6,1e7,1.5e7,2e7,2.5e7,3.1e7,5e7,7e7,9e7]}

# Figure 7 (-10dB@y=346.15, 14.32px/10dB)
A7=59.6; B7=372.8-6*A7
y2db7=lambda y:-10.0-(y-346.15)/14.32*10.0
for idx,label in ((133,"curveA"),(134,"curveB")):
    sp=trace(d7[idx])
    res["fig7_%s_dB"%label]={str(f):round(interp_at(sp[0],f,A7,B7,y2db7),1) for f in [1e6,1e7,3.1e7,1e8]}
json.dump(res, open(OUT+r"\datasheet_curves.json","w"), indent=1)
print(json.dumps(res, indent=1))

# ---- overlays ----
def overlay(pageidx, clip, curves, fname, xa, xb, yinv):
    p=doc[pageidx]
    pix=p.get_pixmap(dpi=600, clip=clip); tmp=OUT+r"\pages\_tmp_%s.png"%fname; pix.save(tmp)
    img=np.array(Image.open(tmp).convert("L")); sc=600/72.0
    H,W=img.shape
    fig=plt.figure(figsize=(W/150,H/150),dpi=150); ax=fig.add_axes([0,0,1,1])
    ax.imshow(img,cmap="gray"); ax.axis("off")
    for pts,color in curves:
        xs=[(xa*math.log10(f)+xb-clip.x0)*sc for f,y in pts]
        ys=[(yinv(y)-clip.y0)*sc for f,y in pts]
        ax.plot(xs,ys,lw=0.7,color=color,alpha=0.9)
    for t in (3.1e7,):
        ax.axvline((xa*math.log10(t)+xb-clip.x0)*sc,color="lime",lw=0.6)
    fig.savefig(OUT+r"\pages\%s.png"%fname,dpi=150); plt.close(fig)
    print("overlay", fname, W, H)

overlay(6, fitz.Rect(350,95,575,250),
        [([(10**((x-A6)/A6) if False else 0,0)],"r")], "tmp", A6,B6, lambda v:v) if False else None
# fig6 overlay
p=doc[6]
clip=fitz.Rect(350,95,575,250)
pix=p.get_pixmap(dpi=600,clip=clip); pix.save(OUT+r"\pages\_t6.png")
img=np.array(Image.open(OUT+r"\pages\_t6.png").convert("L")); sc=600/72.0; H,W=img.shape
fig=plt.figure(figsize=(W/150,H/150),dpi=150); ax=fig.add_axes([0,0,1,1]); ax.imshow(img,cmap="gray"); ax.axis("off")
xs=[(A6*math.log10(f)+B6-clip.x0)*sc for f,y in sp6[0]]
ys=[(145.5-y*142.167-clip.y0)*sc for f,y in [(0,0)]] # placeholder
# recompute properly: y = 145.5 - dB*142.167
ys=[(145.5-y2db6(y)*142.167-clip.y0)*sc for f,y in sp6[0]]
ax.plot(xs,ys,lw=0.7,color="red")
ax.axvline((A6*math.log10(3.1e7)+B6-clip.x0)*sc,color="lime",lw=0.6)
fig.savefig(OUT+r"\pages\fig6_overlay.png",dpi=150); plt.close(fig)
print("fig6 overlay", W, H)

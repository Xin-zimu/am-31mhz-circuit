# -*- coding: utf-8 -*-
import fitz, sys, json, math
import numpy as np
sys.stdout.reconfigure(encoding="utf-8")
src = r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835\sources\ad835.pdf"
outdir = r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2\sources\pages"
doc = fitz.open(src)
p = doc[6]
dr = p.get_drawings()

def bez(p0,p1,p2,p3,n=60):
    t = np.linspace(0,1,n); mt=1-t
    return list(zip(mt**3*p0[0]+3*mt*mt*t*p1[0]+3*mt*t*t*p2[0]+t**3*p3[0],
                    mt**3*p0[1]+3*mt*mt*t*p1[1]+3*mt*t*t*p2[1]+t**3*p3[1]))

subpaths=[]; cur=[]
def close():
    global cur
    if cur: subpaths.append(cur); cur=[]
for it in dr[74]["items"]:
    if it[0]=="l":
        a=(it[1].x,it[1].y); b=(it[2].x,it[2].y)
        if cur and (abs(cur[-1][0]-a[0])>0.4 or abs(cur[-1][1]-a[1])>0.4): close()
        if not cur: cur=[a]
        cur.append(b)
    elif it[0]=="c":
        p0=(it[1].x,it[1].y); p1=(it[2].x,it[2].y); p2=(it[3].x,it[3].y); p3=(it[4].x,it[4].y)
        if cur and (abs(cur[-1][0]-p0[0])>0.4 or abs(cur[-1][1]-p0[1])>0.4): close()
        pts=bez(p0,p1,p2,p3,60)
        if not cur: cur=[pts[0]]
        cur.extend(pts)
close()

# calibration from label centres
X10M, X100M, X1G = 142.8, 202.2, 261.7
A_X = 59.45; B_X = 142.8 - 7*A_X
def x2f(x): return 10**((x-B_X)/A_X)
Y_DB0 = 563.2; PX_PER_DB = 7.16667
def y2db(y): return (Y_DB0-y)/PX_PER_DB
Y_DEG0 = 577.45; PX_PER_90DEG = 14.3625
def y2deg(y): return (Y_DEG0-y)/PX_PER_90DEG*90.0

gain_sp = subpaths[0]
phase_sp = subpaths[1]

def at(target, sp, conv):
    best=None
    for x,y in sp:
        f=x2f(x)
        if f<=0: continue
        d=abs(math.log10(f/target))
        if best is None or d<best[0]: best=(d,f,conv(y))
    return best

print("=== GAIN (dB) from subpath0 ===")
gains={}
for t in [1e6,2e6,5e6,1e7,1.5e7,2e7,2.5e7,3.1e7,4e7,5e7,7e7,1e8]:
    d,f,v = at(t, gain_sp, y2db)
    gains[t]=v
    print("  %8.3f MHz : %+7.3f dB   (nearest px f=%.3f MHz)" % (t/1e6, v, f/1e6))

print("=== PHASE (deg) from subpath1, limited to pre-wrap region x<=240 ===")
pre = [q for q in phase_sp if q[0] <= 240]
print("  pre-wrap pts:", len(pre), " last:", (round(pre[-1][0],1), round(pre[-1][1],1)), "deg=", round(y2deg(pre[-1][1]),2))
for t in [1e6,2e6,5e6,1e7,1.5e7,2e7,2.5e7,3.1e7,4e7,5e7,7e7]:
    d,f,v = at(t, pre, y2deg)
    print("  %8.3f MHz : %+7.2f deg  (nearest px f=%.3f MHz)" % (t/1e6, v, f/1e6))

json.dump({"gain_dB":{str(k):v for k,v in gains.items()},
           "calib":{"x_a":A_X,"x_b":B_X,"y_db0":Y_DB0,"px_per_db":PX_PER_DB,"y_deg0":Y_DEG0,"px_per_90deg":PX_PER_90DEG}},
          open(r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2\sources\fig5_digitized.json","w"), indent=1)

# overlay render
clip = fitz.Rect(70, 495, 300, 660)
pix = p.get_pixmap(dpi=600, clip=clip)
pix.save(outdir + r"\fig5_overlay_base.png")
print("overlay base", pix.width, pix.height, "clip", clip)
# convert pdf coords to pixel coords for the clip
sc = 600/72.0
import json as js
js.dump({"clip":[clip.x0,clip.y0,clip.x1,clip.y1],"scale":sc,
         "gain":[[x2f(x), y2db(y)] for x,y in gain_sp],
         "phase":[[x2f(x), y2deg(y)] for x,y in phase_sp]},
        open(r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2\sources\fig5_overlay.json","w"))

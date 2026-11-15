# -*- coding: utf-8 -*-
import fitz, sys, json, math
import numpy as np
sys.stdout.reconfigure(encoding="utf-8")
src = r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835\sources\ad835.pdf"
doc = fitz.open(src)
p = doc[6]
dr = p.get_drawings()

def bez(p0,p1,p2,p3,n=24):
    t = np.linspace(0,1,n)
    mt = 1-t
    x = mt**3*p0[0] + 3*mt*mt*t*p1[0] + 3*mt*t*t*p2[0] + t**3*p3[0]
    y = mt**3*p0[1] + 3*mt*mt*t*p1[1] + 3*mt*t*t*p2[1] + t**3*p3[1]
    return list(zip(x,y))

pts = []
for it in dr[74]["items"]:
    if it[0] == "l":
        pts.append((it[1].x, it[1].y)); pts.append((it[2].x, it[2].y))
    elif it[0] == "c":
        p0=(it[1].x,it[1].y); p1=(it[2].x,it[2].y); p2=(it[3].x,it[3].y); p3=(it[4].x,it[4].y)
        for q in bez(p0,p1,p2,p3,24):
            pts.append((float(q[0]), float(q[1])))
print("total sampled points:", len(pts))

# Split into two curves by y band.
# GAIN curve at low freq sits near dB=0 -> y~563.2 ; PHASE near -2deg -> y~577.9
gain, phase = [], []
for x,y in pts:
    if 549.0 <= y <= 575.5:
        gain.append((x,y))
    elif 575.5 < y <= 660.0:
        phase.append((x,y))
    else:
        # above 549: gain rising above +2dB (peaking region)
        if y < 549.0:
            gain.append((x,y))
print("gain pts", len(gain), "phase pts", len(phase))

# calibration
def x2f(x):   # x = a*log10(f) + b, from majors 10M=142.8, 100M=202.2, 1G=261.7
    a = 59.45; b = 142.8 - 7*a
    return 10**((x-b)/a)
def y2db(y):
    return (563.2 - y)/7.1667
def y2deg(y):
    return (577.45 - y)/0.15892

def report(sel, conv, name, typeref):
    sel = sorted(sel)
    rows = []
    for x,y in sel:
        f = x2f(x); v = conv(y)
        if 1e6 <= f <= 1.05e9:
            rows.append((f, v))
    rows.sort()
    print("\n--", name, "n=", len(rows))
    for target in [1e6,2e6,5e6,1e7,2e7,3.1e7,5e7,1e8]:
        best = min(rows, key=lambda r: abs(math.log10(r[0]/target)))
        print("   f=%.3e  %s=%.4f  (px f=%.3e)" % (target, typeref, best[1], best[0]))
    return rows

g = report(gain, y2db, "GAIN", "dB")
ph = report(phase, y2deg, "PHASE", "deg")
json.dump({"gain":g,"phase":ph}, open(r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2\sources\fig5_digitized.json","w"))

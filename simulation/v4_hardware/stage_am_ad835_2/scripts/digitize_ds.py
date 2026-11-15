# -*- coding: utf-8 -*-
import fitz, sys, json, math
import numpy as np
sys.stdout.reconfigure(encoding="utf-8")
src = r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835\sources\ad835.pdf"
doc = fitz.open(src)
OUT = r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2\sources"

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

def interp_at(sp, target, xa, xb, conv, yconv_kind):
    # build (f, v) then linear-interp in log10(f)
    arr=[]
    for x,y in sp:
        f = 10**((x-xb)/xa)
        arr.append((f, conv(y)))
    arr.sort()
    fs=[a[0] for a in arr]; vs=[a[1] for a in arr]
    # average duplicate f
    xs=np.log10(np.array(fs)); ys=np.array(vs)
    ux, inv = np.unique(np.round(xs,9), return_inverse=True)
    uy = np.array([ys[inv==i].mean() for i in range(len(ux))])
    return float(np.interp(math.log10(target), ux, uy))

res={}

# ---------- Figure 5 : gain & phase vs frequency ----------
p7=doc[6]; d7=p7.get_drawings()
sp5 = trace(d7[74])
A5=59.45; B5=142.8-7*A5
gain5, phase5 = sp5[0], sp5[1]
y2db5 = lambda y: (563.2-y)/7.16667
y2deg5 = lambda y: (577.45-y)/14.3625*90.0
pre5 = [q for q in phase5 if q[0] <= 240.0]
res["fig5_gain_dB"] = {str(f): round(interp_at(gain5,f,A5,B5,y2db5,"db"),3) for f in [1e6,5e6,1e7,1.5e7,2e7,2.5e7,3.1e7,4e7,5e7,7e7,1e8]}
res["fig5_phase_deg"] = {str(f): round(interp_at(pre5,f,A5,B5,y2deg5,"deg"),2) for f in [1e6,5e6,1e7,1.5e7,2e7,2.5e7,3.1e7,4e7,5e7,7e7]}

# ---------- Figure 6 : gain flatness ----------
A6=50.575; B6=399.5-6*A6
y2db6 = lambda y: (145.5-y)/14.2167
sp6 = trace(d7[103])
res["fig6_gain_dB"] = {str(f): round(interp_at(sp6[0],f,A6,B6,y2db6,"db"),3) for f in [3e5,1e6,3e6,1e7,1.5e7,2e7,2.5e7,3.1e7,5e7,7e7,9e7]}

# ---------- Figure 7 : feedthrough ----------
A7=59.6; B7=372.8-6*A7
y2db7 = lambda y: -10.0-(y-346.15)/14.32*10.0
for idx in (133,134):
    sp7 = trace(d7[idx])
    vals = {str(f): round(interp_at(s,f,A7,B7,y2db7,"db"),1) for f in [1e6,1e7,3.1e7,1e8] for s in [sp7[0]]}
    print("fig7 curve", idx, "n_sub", len(sp7), vals)

json.dump(res, open(OUT+r"\datasheet_curves.json","w"), indent=1)
print(json.dumps(res, indent=1))

# -*- coding: utf-8 -*-
import fitz, sys, json, math
import numpy as np
sys.stdout.reconfigure(encoding="utf-8")
src = r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835\sources\ad835.pdf"
doc = fitz.open(src)
p = doc[6]
dr = p.get_drawings()

def bez(p0,p1,p2,p3,n=40):
    t = np.linspace(0,1,n); mt=1-t
    return list(zip(mt**3*p0[0]+3*mt*mt*t*p1[0]+3*mt*t*t*p2[0]+t**3*p3[0],
                    mt**3*p0[1]+3*mt*mt*t*p1[1]+3*mt*t*t*p2[1]+t**3*p3[1]))

subpaths = []   # list of list[(x,y)]
cur = []
def close():
    global cur
    if cur: subpaths.append(cur); cur=[]

for it in dr[74]["items"]:
    if it[0]=="l":
        a=(it[1].x,it[1].y); b=(it[2].x,it[2].y)
        if cur and (abs(cur[-1][0]-a[0])>0.4 or abs(cur[-1][1]-a[1])>0.4):
            close()
        if not cur: cur=[a]
        cur.append(b)
    elif it[0]=="c":
        p0=(it[1].x,it[1].y); p1=(it[2].x,it[2].y); p2=(it[3].x,it[3].y); p3=(it[4].x,it[4].y)
        if cur and (abs(cur[-1][0]-p0[0])>0.4 or abs(cur[-1][1]-p0[1])>0.4):
            close()
        pts=bez(p0,p1,p2,p3,40)
        if not cur: cur=[pts[0]]
        cur.extend(pts)
close()
print("subpaths:", len(subpaths))
for i,s in enumerate(subpaths):
    print(i, "n=",len(s), "start",(round(s[0][0],1),round(s[0][1],1)), "end",(round(s[-1][0],1),round(s[-1][1],1)),
          "ymin",round(min(q[1] for q in s),1), "ymax",round(max(q[1] for q in s),1),
          "xmin",round(min(q[0] for q in s),1), "xmax",round(max(q[0] for q in s),1))
json.dump([[list(map(float,q)) for q in s] for s in subpaths], open(r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2\sources\fig5_subpaths.json","w"))

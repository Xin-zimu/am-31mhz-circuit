# -*- coding: utf-8 -*-
import fitz, json, math, io, sys
sys.stdout.reconfigure(encoding="utf-8")
src = r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835\sources\ad835.pdf"
doc = fitz.open(src)
p = doc[6]
dr = p.get_drawings()

def pts(idx):
    dd = dr[idx]
    out = []
    for it in dd["items"]:
        if it[0] == "l":
            out.append((it[1].x, it[1].y)); out.append((it[2].x, it[2].y))
        elif it[0] == "c":
            for q in (it[1], it[2], it[3], it[4]):
                out.append((q.x, q.y))
    # dedupe consecutive
    res = []
    for q in out:
        if not res or abs(q[0]-res[-1][0]) > 1e-6 or abs(q[1]-res[-1][1]) > 1e-6:
            res.append(q)
    return res

c = pts(74)
print("curve74 points:", len(c))
print("first 6:", [(round(x,1), round(y,1)) for x,y in c[:6]])
print("last 6:", [(round(x,1), round(y,1)) for x,y in c[-6:]])
ys = [y for x,y in c]
print("y range:", round(min(ys),1), round(max(ys),1))

# split segments by continuity
segs = []
cur = [c[0]]
for q in c[1:]:
    if abs(q[0]-cur[-1][0]) > 6 or abs(q[1]-cur[-1][1]) > 6:
        segs.append(cur); cur=[q]
    else:
        cur.append(q)
segs.append(cur)
print("segments:", [(len(s), round(s[0][0],1), round(s[0][1],1), round(s[-1][0],1), round(s[-1][1],1)) for s in segs])
json.dump([[list(map(float,q)) for q in s] for s in segs], open(r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2\sources\fig5_raw.json","w"))

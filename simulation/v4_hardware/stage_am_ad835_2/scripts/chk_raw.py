# -*- coding: utf-8 -*-
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from ltraw import load_raw, run
sys.stdout.reconfigure(encoding="utf-8")
d=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2\bench"
p=os.path.join(d,"chk.net")
run(p, ascii=True)
r=load_raw(os.path.join(d,"chk.raw"))
t=r["time"]; v=r["V(a)"]
print("ASCII: n=",len(t)," t:",t[0],"->",t[-1])
print("  V(a) peak %.6f  (expect 1.0)"%np.max(np.abs(v)))
# analytic check
ref = 1.0*np.sin(2*np.pi*31e6*t)
print("  max |V(a)-sin| = %.3e"%np.max(np.abs(v-ref)))
print("  max |I(R1)+V(a)/150| = %.3e"%np.max(np.abs(r["I(R1)"]+v/150.0)))
raw=open(os.path.join(d,"chk.raw"),"rb").read()
run(p, ascii=False)
rawb=open(os.path.join(d,"chk.raw"),"rb").read()
print("\nBINARY file size", len(rawb))
i=rawb.find("Binary:".encode("utf-16-le"))
print("  marker at", i, "header len", i)
import re
hdr=rawb[:i].decode("utf-16-le","replace")
print("  ", [l for l in hdr.splitlines() if l.startswith(("No.","Flags"))])

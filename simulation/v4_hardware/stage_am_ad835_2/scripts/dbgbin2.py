# -*- coding: utf-8 -*-
import os, sys, numpy as np, re
sys.stdout.reconfigure(encoding="utf-8")
d=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2\bench"
rawb=open(os.path.join(d,"chk.raw"),"rb").read()
hdr=rawb[:762].decode("utf-16-le","replace")
nv=4; npts=5031
need=nv*npts*8
print("file",len(rawb),"need",need,"header",len(rawb)-need)
off=len(rawb)-need
print(repr(rawb[off-40:off+8]))
arr=np.frombuffer(rawb[off:off+need],dtype="<f8").reshape(npts,nv).T
t=arr[0]; v=arr[1]
print("t:",t[0],t[-1],"  V(a) peak",np.max(np.abs(v)))
print("max|V(a)-sin|",np.max(np.abs(v-np.sin(2*np.pi*31e6*t))))

import os, sys, numpy as np
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ngraw import load_ngraw
ST=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_alt1"
R=load_ngraw(os.path.join(ST,"bench","ac","a_90_470_10.raw"))
print("vectors:", list(R.keys()))
f=R["frequency"]; print("f dtype",f.dtype,"n",len(f),f[:2],f[-1])
for k in ("v(xbn)","v(xcn)","v(va)","v(vae)","v(ac)"):
    if k in R:
        v=R[k]; i=int(np.argmin(abs(np.log10(np.abs(f))-np.log10(31e6))))
        print("%-10s |v|@31M=%9.4f  @1M=%9.4f  @100M=%9.4f"%(k,abs(v[i]),
              abs(v[0]),abs(v[-1])))

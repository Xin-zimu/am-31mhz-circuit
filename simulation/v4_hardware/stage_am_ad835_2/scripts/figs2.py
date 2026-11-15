# -*- coding: utf-8 -*-
"""Second figure: model structure + pulse + load behaviour."""
import os, sys, json, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
RES=os.path.join(STAGE,"results")
plt.rcParams.update({"figure.dpi":130,"font.size":8,"axes.grid":True,"grid.alpha":0.3})
fig,axs=plt.subplots(1,3,figsize=(12,3.6))

# (a) output swing vs load, both models
m2=json.load(open(os.path.join(RES,"M2.json")))
RL=[150,50,25]
a=[m2["swing_A_%d"%r]["hi"] for r in RL]
b=[m2["swing_B_%d"%r]["hi"] for r in RL]
ax=axs[0]
ax.semilogx(RL,a,"o-",label="model A"); ax.semilogx(RL,b,"s-",label="model B")
ax.axhline(2.2,color="r",ls=":",lw=1,label="datasheet +-2.2 min (150R)")
ax.axhline(2.0,color="orange",ls=":",lw=1,label="datasheet +-2.0 min (50R)")
ax.set_xlabel("load resistance (ohm)"); ax.set_ylabel("peak |W| (V)")
ax.set_title("(a) Output swing vs load"); ax.legend(fontsize=6)

# (b) 5 us pulse / envelope corner
ax=axs[1]
Z=np.load(os.path.join(RES,"fin.npz"))
t=Z["A_510_680__time"]; v=Z["A_510_680__V(tp3)"]
m=(t>=t[0]+5e-6)&(t<t[0]+22e-6)
ax.plot((t[m]-t[m][0])*1e6, v[m], "tab:red", lw=0.6)
ax.set_title("(b) AD835 A output near a 5 us modulation edge")
ax.set_xlabel("time (us)"); ax.set_ylabel("V(TP3)")

# (c) bias current effect on the Y/Z node
b9=json.load(open(os.path.join(RES,"M9_bias.json")))
ax=axs[2]
if b9:
    xs=[r["iby_uA"] for r in b9]; ys=[r["VAdc"]*1e3 for r in b9]
    ax.bar(range(len(b9)), ys)
    ax.set_xticks(range(len(b9)))
    ax.set_xticklabels(["%+d/%+d"%(r["iby_uA"],r["ibz_uA"]) for r in b9], rotation=45, fontsize=6)
    ax.set_ylabel("V(A) DC (mV)")
ax.set_title("(c) Y/Z DC vs injected bias (uA)")
fig.tight_layout(); o=os.path.join(RES,"fig_am_ad835_2_aux.png")
fig.savefig(o,dpi=150); print("saved",o)

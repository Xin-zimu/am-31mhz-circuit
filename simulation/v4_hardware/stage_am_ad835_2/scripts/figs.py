# -*- coding: utf-8 -*-
"""Figures for stage AM-AD835.2"""
import os, sys, json, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
RES=os.path.join(STAGE,"results"); SRC=os.path.join(STAGE,"sources")
plt.rcParams.update({"figure.dpi":130,"font.size":8,"axes.grid":True,"grid.alpha":0.3})
Z=np.load(os.path.join(RES,"fin.npz"))
def arr(t,k):
    kk="%s__%s"%(t,k); return Z[kk] if kk in Z else None
ds=json.load(open(os.path.join(SRC,"datasheet_curves.json")))
ac=json.load(open(os.path.join(RES,"M3_ac.json")))

fig,axs=plt.subplots(2,2,figsize=(11.5,7.5))

ax=axs[0,0]
for tag,c,lab in (("ref_poly","k","POLY (frozen)"),("A_direct","tab:blue","AD835 A, direct"),
                  ("A_510_680","tab:red","AD835 A, 510/680")):
    t=arr(tag,"time"); v=arr(tag,"V(tp3)")
    m=(t>=t[0]+1e-6)&(t<t[0]+3e-6)
    ax.plot((t[m]-t[m][0])*1e6, v[m], c, lw=0.8, label=lab)
ax.set_title("(a) TP3 AM waveform (31 MHz / 20 kHz, real frozen source)")
ax.set_xlabel("time (us)"); ax.set_ylabel("V(TP3) [V]"); ax.legend(fontsize=6)

ax=axs[0,1]
FC=31e6
for tag,c in (("ref_poly","k"),("A_direct","tab:blue"),("A_510_680","tab:red")):
    t=arr(tag,"time"); v=arr(tag,"V(tp3)")
    T=32/FC; n=int((t[-1]-t[0])/T); tc=[];hi=[];lo=[]
    for i in range(n):
        m=(t>=t[0]+i*T)&(t<t[0]+(i+1)*T)
        if m.sum()>3: hi.append(v[m].max()); lo.append(v[m].min()); tc.append(t[0]+(i+0.5)*T)
    ax.plot((np.array(tc)-t[0])*1e6,np.array(hi),c,lw=1.0)
    ax.plot((np.array(tc)-t[0])*1e6,np.array(lo),c,lw=1.0,ls="--")
ax.set_title("(b) Carrier envelope  (solid=peak, dashed=trough)")
ax.set_xlabel("time (us)"); ax.set_ylabel("V [V]")

ax=axs[1,0]
for tag,c in (("ref_poly","k"),("A_direct","tab:blue"),("A_510_680","tab:red")):
    t=arr(tag,"time"); v=arr(tag,"V(tp3)")
    n=2**17; tt=t-t[0]; fs=n/(tt[-1]); tu=np.arange(n)/fs
    vu=np.interp(tu,tt,v); w=np.hanning(n)
    S=np.abs(np.fft.rfft(vu*w))*2/np.sum(w); f=np.fft.rfftfreq(n,1/fs)
    m=(f>29e6)&(f<33e6)
    ax.plot(f[m]/1e6, 20*np.log10(S[m]/S[m].max()+1e-14), c, lw=0.8, label=tag)
ax.set_title("(c) Spectrum near 31 MHz (normalised to carrier)")
ax.set_xlabel("frequency (MHz)"); ax.set_ylabel("dBc"); ax.set_ylim(-80,2); ax.legend(fontsize=6)

ax=axs[1,1]
f=np.array(ac["acX_A"]["f"]); mag=np.array(ac["acX_A"]["mag"]); ph=np.array(ac["acX_A"]["ph"])
ax.semilogx(f,20*np.log10(mag/mag[0]),"tab:red",lw=1.4,label="models A & B (identical)")
kd=sorted(float(x) for x in ds["fig5_gain_dB"])
gd=[ds["fig5_gain_dB"][str(k)] for k in kd]
ax.semilogx(kd,gd,"ko",ms=3.5,label="datasheet Fig.5 gain")
kp=sorted(float(x) for x in ds["fig5_phase_deg"])
pd=[ds["fig5_phase_deg"][str(k)] for k in kp]
ax2=ax.twinx()
ax2.semilogx(f,ph,"tab:red",lw=1.1,ls="--",alpha=0.75)
ax2.semilogx(kp,pd,"ks",ms=3.5,mfc="none")
ax2.set_ylabel("phase (deg)"); ax2.grid(False)
ax.axvline(31e6,color="g",lw=1.0,ls=":")
ax.axhline(0,color="0.7",lw=0.5)
ax.set_title("(d) Small-signal response vs datasheet Fig.5")
ax.set_xlabel("frequency (Hz)"); ax.set_ylabel("gain (dB)"); ax.set_ylim(-3,0.5)
ax.legend(fontsize=6,loc="lower left")
fig.tight_layout()
o=os.path.join(RES,"fig_am_ad835_2_main.png"); fig.savefig(o,dpi=150); print("saved",o)

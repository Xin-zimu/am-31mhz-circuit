
# -*- coding: utf-8 -*-
"""Device-level LC study: real inductor (Q, SRF) + real trimmer as the ONLY tuning element."""
from pathlib import Path
import json, subprocess, math, time
import numpy as np

EXE=Path('D:/ms_xsp/s04_crosscheck_20261017/Spice64/bin/ngspice_con.exe')
ROOT=Path(r'D:\实验报告文件夹\电路2\tmp\lcdev'); (ROOT/'cir').mkdir(parents=True,exist_ok=True)
WORK=ROOT/'work'; WORK.mkdir(parents=True,exist_ok=True)
MDL=Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage4_rf_oscillator\advance_20261029\2N3904_UNCG.lib').read_text(encoding='ascii').strip()
F0=31e6; LC=1.0/(2*math.pi*F0)**2

def readraw(p):
    with open(p,'rb') as f:
        names=[];inside=False
        while True:
            s=f.readline().decode('ascii').strip()
            if s=='Binary:':break
            if s=='Variables:':inside=True;continue
            if inside and s:names.append(s.split()[1].lower())
        a=np.fromfile(f,dtype='<f8').reshape(-1,len(names))
    return dict(zip(names,a.T))

def f_of(t,e):
    dc=float(np.trapezoid(e,t)/(t[-1]-t[0])); v=e-dc
    idx=np.where((v[:-1]<=0)&(v[1:]>0))[0]
    if len(idx)<10: return None,dc
    cr=t[idx]-v[idx]*(t[idx+1]-t[idx])/(v[idx+1]-v[idx])
    return float((len(cr)-1)/(cr[-1]-cr[0])),dc

def thd(t,e,f0):
    m=t>=t[-1]-20e-6
    tt=t[m];ee=e[m];n=2**15
    tu=np.linspace(tt[0],tt[-1],n);eu=np.interp(tu,tt,ee);eu-=eu.mean()
    sp=np.abs(np.fft.rfft(eu*np.hanning(n)))/(n/4); fr=np.fft.rfftfreq(n,tu[1]-tu[0])
    def amp(fh):
        k=np.argmin(np.abs(fr-fh));return float(sp[max(0,k-2):k+3].max())
    a1=amp(f0); tot=sum(amp(f0*h)**2 for h in range(2,6))
    return float(np.sqrt(tot)/max(a1,1e-15)*100)

def net(name,L_nH,C_p,CT_p,Q,SRF_MHz,temp,vs,load=True,buffer=True,stop_us=400,save_us=90):
    L=L_nH*1e-9
    Rs=2*math.pi*F0*L/Q                      # series loss from Q at 31 MHz
    Cp=1.0/((2*math.pi*SRF_MHz*1e6)**2*L)    # parallel C giving that SRF
    extra=""
    if buffer:
        extra+="CIN e bf 1n\nRBT vcc bf 10k\nRBB bf 0 10k\nQB vcc bf ef 2N3904\nREB ef 0 330\nCOUT ef out 1n\n"
    else:
        extra+="CCO e out 1n\n"
    if load: extra+="RLOAD out 0 2000\nCLOAD out 0 10p\n"
    extra+=f"RLK out 0 1e15\n"
    return f'''* Device-level LC Colpitts 31 MHz | L={L_nH}nH Q={Q} SRF={SRF_MHz}MHz | trimmer CT={CT_p}pF
* Rs={Rs:.4f} ohm, Cp={Cp*1e12:.4f} pF | C1=C2={C_p}pF | 5V | UIC
VSUP vcc 0 PWL(0 0 1u {vs})
R1 vcc b 10k
R2 b 0 10k
Q1 vcc b e 2N3904
R3 e 0 4.7k
C1 b e {C_p}p
C2 e 0 {C_p}p
CT e 0 {CT_p}p
CBLK b nL 1000p
LR nL n1 {Rs:.6f}
L1 n1 0 {L_nH}n
CP n1 0 {Cp*1e12:.6f}p
C3 vcc 0 100n
C4 vcc 0 10u
{extra}{MDL}
.options method=trap maxord=2 reltol=1e-3 trtol=7 temp={temp} tnom=27
.control
set filetype=binary
set num_threads=1
save v(vcc) v(b) v(e) v(out) i(vsup)
tran 0.125n {stop_us}u {save_us}u 0.125n uic
write {name}.raw
quit
.endc
.end
'''

def run(name,**kw):
    src=net(name,**kw)
    (ROOT/'cir'/(name+'.cir')).write_text(src,encoding='ascii')
    (WORK/(name+'.cir')).write_text(src,encoding='ascii')
    raw=WORK/(name+'.raw')
    if raw.exists(): raw.unlink()
    t0=time.monotonic()
    subprocess.run([str(EXE),'-b','-n','-o',str(WORK/(name+'.log')),str(WORK/(name+'.cir'))],
                   cwd=WORK,capture_output=True,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
    if not raw.exists(): return None
    d=readraw(raw); t=d['time']; e=d['v(out)']
    f,dc=f_of(t,e); mm=t>=(kw.get('save_us',90)*1e-6)
    P=float(-np.trapezoid(d['v(vcc)']*d['i(vsup)'],t)/(t[-1]-t[0])*1e3)
    return dict(name=name,freq_hz=f,err_ppm=(f/F0-1)*1e6 if f else None,
                vpp=float(np.ptp(e[mm])),dc=dc,supply_mw=P,
                thd_pct=(thd(t,e,f) if f else None),seconds=round(time.monotonic()-t0,1),**kw)

def designC(L_nH,Q,SRF_MHz):
    """Effective L at f0 (parallel SRF), then pick C1=C2 so CT sits mid-range."""
    L=L_nH*1e-9
    Leff=L/(1-(F0/(SRF_MHz*1e6))**2)
    T=LC/Leff                      # required total effective C
    CT0=32.5e-12
    # C(C+CT)/(2C+CT)=T  ->  C = [-(CT-2T)+sqrt((CT-2T)^2+4*2*... )] solve directly
    a=1.0; b=(CT0-2*T); c=-CT0*T
    C=(-b+math.sqrt(b*b-4*a*c))/(2*a)
    return C*1e12, T*1e12

# --- settling verify: 400us vs 1000us on one baseline ---
print("=== settle check ===")
for stop,save in [(400,90),(1000,90)]:
    C,T=designC(1200,60,200)
    r=run("settle_%dus"%stop,L_nH=1200,C_p=round(C,1),CT_p=32.5,Q=60,SRF_MHz=200,temp=27,vs=5,stop_us=stop,save_us=save)
    print("  stop=%4d us  f=%9.3f kHz  Vpp=%7.4f  (%.0fs)"%(stop,(r['freq_hz'] or 0)/1e3,r['vpp'],r['seconds']))
    print("     C1=C2=%.1f pF  (C_eff target %.2f pF)"%(round(C,1),T))

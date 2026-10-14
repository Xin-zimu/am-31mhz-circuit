from pathlib import Path
import subprocess, json, re
import numpy as np

ROOT = Path(__file__).resolve().parent
LT = Path(r'D:\tlspice\LTspice.exe')

def run_spice(path):
    p = subprocess.run([str(LT), '-b', '-ascii', str(path)], cwd=path.parent,
                       creationflags=0x08000000, timeout=180, capture_output=True)
    log = path.with_suffix('.log').read_text(errors='replace')
    if p.returncode or 'Fatal Error' in log:
        raise RuntimeError(log[-3000:])
    return log

def read_raw(path):
    text = path.read_text(encoding='utf-16le') if path.read_bytes()[:2] in (b'T\x00', b'\xff\xfe') else path.read_text()
    head, values = text.split('Values:\n', 1)
    names = [line.split()[1] for line in head.split('Variables:\n',1)[1].strip().splitlines()]
    vals = []
    for line in values.splitlines():
        parts=line.split()
        if parts: vals.append(float(parts[-1]))
    arr=np.asarray(vals).reshape(-1,len(names))
    offset=re.search(r'^Offset:\s*(\S+)',head,re.M)
    if offset: arr[:,0] += float(offset.group(1))
    return {n.lower():arr[:,i] for i,n in enumerate(names)}

# Educational finite-bandwidth macromodels, NOT vendor LM393B/OPA1652 models.
# Comparator open collector with 25-ohm on resistance and 100ns input pole.
MACRO = '''
.subckt COMP_OC P N OUT VP VN
ECP CI VN N P 1
RCOMP CI CD 1k
CCOMP CD VN 100p
SCOMP OUT VN CD VN SWOC
.ends COMP_OC
.model SWOC SW(Ron=25 Roff=1e10 Vt=0 Vh=0.001)
.subckt OP18 P N OUT VP VN
EGAIN A VN P N 100000
RDOM A B 1k
CDOM B VN 884.2n
BBUF C VN V=limit(V(B,VN),0.05,V(VP,VN)-0.05)
ROUT C OUT 50
.ends OP18
'''

def lf_net(rfreq=33000,duty_voltage=4.5,amp_pos=.95,original=False):
    top = max(1,10000*(1-amp_pos)); bot=max(1,10000*amp_pos)
    schmitt = ('R4 SQ_OSC HYST 20k\nR5 VREF HYST 10k\nXU1A HYST TRI SQ_OSC VCC 0 COMP_OC' if original else
               'R4 SQ_OSC HYST 30k\nR5 TRI HYST 10k\nXU1A HYST VREF SQ_OSC VCC 0 COMP_OC')
    return f'''LF oscillator {'ORIGINAL - expected latch' if original else 'CORRECTED'}
* Nodes: TRI=TP_TRI, V1=TP1. Rfreq includes R6+VR1.
* OP18 and COMP_OC are educational approximations, not vendor models.
VCC VCC 0 9
VREF VREF 0 4.5
VDUTY VDUTY 0 {duty_voltage:.9g}
R3 VCC SQ_OSC 2.2k
{schmitt}
RFREQ SQ_OSC INT_N {rfreq:.9g}
C8 TRI INT_N 1n
R7 TRI INT_N 1meg
XU2A VREF INT_N TRI VCC 0 OP18
XU1B TRI VDUTY PWM_RAW VCC 0 COMP_OC
R10 VCC PWM_RAW 2.2k
R11 PWM_RAW AMP_TOP 8.2k
RVR3A AMP_TOP V1_PRE {top:.9g}
RVR3B V1_PRE 0 {bot:.9g}
R12 V1_PRE V1 1k
RLOAD V1 0 1meg
{MACRO}
.ic V(TRI)=4.6 V(INT_N)=4.5
.options plotwinsize=0 reltol=0.0005
.save V(TRI) V(SQ_OSC) V(PWM_RAW) V(V1) V(VDUTY)
.tran 100n 1.2m 0 100n uic
.end
'''

def metrics(data,node='v(v1)',start=.0006):
    t=data['time']; y=data[node]; m=t>=start; ts=t[m]; ys=y[m]
    low,high=np.percentile(ys,[2,98]); mid=(low+high)/2
    def cross(up):
        ids=np.where(((ys[:-1]<mid)&(ys[1:]>=mid)) if up else ((ys[:-1]>=mid)&(ys[1:]<mid)))[0]
        return ts[ids]+(mid-ys[ids])/(ys[ids+1]-ys[ids])*(ts[ids+1]-ts[ids])
    rising=cross(True); falling=cross(False)
    period=np.median(np.diff(rising)) if len(rising)>1 else np.nan
    widths=[falling[falling>x][0]-x for x in rising if np.any(falling>x)]
    return {'frequency_hz':float(1/period),'duty':float(np.median(widths)/period) if widths else float('nan'),
            'vpp':float(high-low),'low_v':float(low),'high_v':float(high)}

if __name__=='__main__':
    dest=ROOT/'low_frequency'; dest.mkdir(parents=True,exist_ok=True)
    for name,orig in [('original_latched',True),('corrected_trial',False)]:
        p=dest/(name+'.cir'); p.write_text(lf_net(original=orig),encoding='ascii')
        run_spice(p); data=read_raw(p.with_suffix('.raw'))
        print(name, metrics(data), 'tri',np.percentile(data['v(tri)'][-2000:],[0,100]))

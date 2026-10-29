"""Decouple buffer feasibility from unknown crystal; ideal RF source is explicit."""
from pathlib import Path
import json, subprocess
import numpy as np
from run_3904 import HERE,WORK,EXE,model,readraw,sha

mdl,_=model()
results=[]
for name,amp,load in [('buf_small_2k',.265,2000),('buf_target_2k',1.2,2000),('buf_target_10k',1.2,10000)]:
    raw=WORK/(name+'.raw');log=WORK/(name+'.log')
    assert not raw.exists(), 'Do not overwrite evidence'
    net=f'''* Exploratory separate 2N3904 emitter follower, NOT integrated with oscillator
* Ideal sine input explicitly bypasses oscillator startup/amplitude uncertainty
VSUP vcc 0 5
VIN drive 0 SIN(0 {amp} 31meg) AC 1
CIN drive b 1n
RBT vcc b 10k
RBB b 0 10k
QBUF vcc b e 2N3904
RE e 0 330
COUT e out 1n
RLOAD out 0 {load}
CLOAD out 0 10p
{mdl}
.options method=trap reltol=1e-3 trtol=7
.control
set filetype=binary
save v(drive) v(b) v(e) v(out) i(vsup)
tran .0625n 100u 90u .0625n
write {raw.as_posix()}
quit
.endc
.end
'''
    src=HERE/(name+'.cir');src.write_text(net,encoding='ascii');local=WORK/src.name;local.write_text(net,encoding='ascii')
    p=subprocess.run([str(EXE),'-b','-n','-o',str(log),str(local)],cwd=WORK,capture_output=True,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
    assert p.returncode==0 and raw.exists()
    (HERE/log.name).write_text(log.read_text(errors='replace'),encoding='utf-8')
    d=readraw(raw);t=d['time'];v=d['v(out)'];mean=lambda x:float(np.trapezoid(x,t)/(t[-1]-t[0]))
    # Fit harmonics by time integral rather than treating adaptive time points as equally spaced.
    def harmonic(k):return 2*abs(np.trapezoid((v-mean(v))*np.exp(-2j*np.pi*31e6*k*t),t)/(t[-1]-t[0]))
    hs=[harmonic(k) for k in range(1,6)]
    r=dict(name=name,source_peak_v=amp,load_r_ohm=load,load_c_pf=10,vout_pp=float(np.ptp(v)),
        vout_dc=mean(v),supply_power_w=-5*mean(d['i(vsup)']),
        harmonic_2_to_5_ratio=float(np.linalg.norm(hs[1:])/hs[0]),
        note='Ideal RF source; no crystal; no numerical step convergence; no integrated verification',
        raw_sha256=sha(raw),net_sha256=sha(src))
    results.append(r);print(json.dumps(r),flush=True)
(HERE/'buffer_results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')

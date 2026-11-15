"""Independent interface checks; these are NOT AD835 device simulations.

Reuse the existing ngspice executable and binary RAW format. Historical
netlists are read only. All newly generated RAW evidence is retained.
"""
from pathlib import Path
import concurrent.futures as cf
import hashlib
import json
import re
import subprocess
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
HW = ROOT.parent
RF = HW / 'stage4_rf_oscillator'
EXE = Path('D:/ms_xsp/s04_crosscheck_20261017/Spice64/bin/ngspice_con.exe')
for name in ('netlists', 'results', 'sources'):
    (ROOT / name).mkdir(exist_ok=True)

def sha(p):
    return hashlib.file_digest(p.open('rb'), 'sha256').hexdigest()

def snapshot():
    dirs = [RF / n for n in ('AM01_2N3904_20261113', 'AM02_2_first_stage_20261113',
            'AM02_3_second_stage_20261113', 'S04_RF_CARRIER')]
    dirs += [HW / 'repair_20261011', HW / 'stage5_receiver']
    return {str(p.relative_to(HW)): sha(p) for d in dirs for p in d.rglob('*')
            if p.is_file() and p.suffix.lower() in ('.cir','.py','.md','.json','.lib','.mod')}

def read_raw(path):
    # Format/algorithm reused from AM01 scripts/am01_lib.py without importing
    # that module (its import creates historical output directories).
    blob = path.read_bytes(); off = blob.index(b'Binary:\n')
    head = blob[:off].decode('latin1').replace('\r','')
    nv = int(re.search(r'No\. Variables:\s+(\d+)', head)[1])
    npnt = int(re.search(r'No\. Points:\s+(\d+)', head)[1])
    names = re.findall(r'^\s*\d+\s+(\S+)\s+\S+\s*$',head.rsplit('Variables:',1)[1],re.M)
    if len(names)!=nv: raise ValueError('RAW variable count mismatch')
    a = np.frombuffer(blob, dtype=np.float64, count=nv*npnt, offset=off+8).reshape(npnt,nv)
    return dict(zip(names,a.T))

def run(name, circuit):
    p = ROOT/'netlists'/f'{name}.cir'
    p.write_text(circuit,encoding='utf8')
    with (ROOT/'results'/f'{name}.log').open('w') as log:
        r = subprocess.run([str(EXE),'-b',str(p)],cwd=ROOT/'results',stdout=log,stderr=subprocess.STDOUT,timeout=900)
    if r.returncode: raise RuntimeError(name+' failed; inspect log')
    d=read_raw(ROOT/'results'/f'{name}.raw')
    return d

def mean(t,x): return float(np.trapezoid(x,t)/(t[-1]-t[0]))

def oscillator(name, r, c, reuse=False):
    src=RF/'S04_RF_CARRIER/XTAL/c4_dual_load_20261030/netlists/c4_trap_0p125n_2k_rtol1e5.cir'
    s=src.read_text(encoding='utf8')
    s=s.replace('RLOADG out 0 2k',f'RLOADG out 0 {r}')
    s=s.replace('CLOADG out 0 10p',f'CLOADG out 0 {c}')
    s=s.replace('save v(out) v(e)','save v(out) v(e) i(vsup)')
    s=s.replace('tran 0.25n 5m 3m 0.125n uic','tran 0.25n 5m 4.9m 0.125n uic')
    s=re.sub(r'write .*',f'write {name}.raw',s)
    d=read_raw(ROOT/'results'/f'{name}.raw') if reuse else run(name,s)
    t=d['time'];y=d['v(out)']
    # Frequency from interpolated zero crossings, then harmonic least squares
    ix=np.where((y[:-1]<0)&(y[1:]>=0))[0]
    z=t[ix]-y[ix]*(t[ix+1]-t[ix])/(y[ix+1]-y[ix])
    f=float(1/np.mean(np.diff(z)))
    spans=[]
    for lo in (4.90e-3,4.95e-3):
        m=(t>=lo)&(t<lo+50e-6); spans.append(float(np.ptp(y[m])))
    m=t>t[-1]-10e-6;ts=t[m]-t[m][0];ys=y[m]
    mat=np.column_stack([np.ones(len(ts))]+[fun(2*np.pi*k*f*ts) for k in range(1,6) for fun in (np.sin,np.cos)])
    co=np.linalg.lstsq(mat,ys,rcond=None)[0];a=np.hypot(co[1::2],co[2::2])
    out=dict(status='interface RC approximation only; not AD835',r_ohm=r,c_f=c,
        f_hz=f,vpp=float(np.ptp(y)),minimum=float(y.min()),maximum=float(y.max()),
        fundamental_vpp=float(2*a[0]),thd_2_to_5=float(np.linalg.norm(a[1:])/a[0]),
        mean_supply_ma=-1000*mean(t,d['i(vsup)']),rail_power_mw=-5000*mean(t,d['i(vsup)']),
        last_two_windows_vpp=spans,window_relative_difference=abs(spans[1]-spans[0])/spans[1],
        source=str(src),source_sha256=sha(src),netlist_sha256=sha(ROOT/'netlists'/f'{name}.cir'))
    (ROOT/'results'/f'{name}.json').write_text(json.dumps(out,indent=2),encoding='utf8')
    print(name,json.dumps(out),flush=True)
    return out

def baseband(reuse=False):
    src=HW/'repair_20261011/final_actual.cir';s=src.read_text(encoding='utf8')
    s=s.split('*## Multisim Component VCC ##*')[0]
    s+='''
.options reltol=1e-5 method=trap
.control
set filetype=binary
save v(v1) v(osc) v(pwm_raw) i(vv5)
tran 20n 2m 1.5m 20n uic
write baseband.raw
quit
.endc
.end
'''
    d=read_raw(ROOT/'results/baseband.raw') if reuse else run('baseband',s)
    t=d['time'];y=d['v(v1)']
    out=dict(source=str(src),low_v=float(np.quantile(y,.1)),high_v=float(np.quantile(y,.9)),
         raw_vpp=float(np.ptp(y)),mean_supply_ma=-1000*mean(t,d['i(vv5)']),
         rail_power_mw=-5000*mean(t,d['i(vv5)']),status='original LM393 front end, isolated, nominal amplitude/duty only')
    (ROOT/'results/baseband.json').write_text(json.dumps(out,indent=2),encoding='utf8')
    print('baseband',json.dumps(out),flush=True);return out

if __name__=='__main__':
    frozen=snapshot();(ROOT/'sources/protected_before.json').write_text(json.dumps(frozen,indent=2,ensure_ascii=False),encoding='utf8')
    ver=subprocess.run([str(EXE),'--version'],capture_output=True,text=True)
    (ROOT/'sources/simulator_version.txt').write_text(ver.stdout+ver.stderr,encoding='utf8')
    with cf.ThreadPoolExecutor(3) as pool:
        jobs=[pool.submit(baseband),pool.submit(oscillator,'osc_reference',2000,10e-12),
              pool.submit(oscillator,'osc_yz_rc',37500,4e-12)]
        for job in cf.as_completed(jobs):job.result()
    after=snapshot(); changes=[k for k in set(frozen)|set(after) if frozen.get(k)!=after.get(k)]
    (ROOT/'results/protection_check.json').write_text(json.dumps(dict(count=len(frozen),changes=changes),indent=2))
    if changes:raise RuntimeError('Protected source changes detected')

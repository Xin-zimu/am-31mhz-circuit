"""Real LM393 source and existing TI OPA197 model; X load is only a fixture."""
from pathlib import Path
import json,re,concurrent.futures as cf,csv
import numpy as np
import rf_study as L
ROOT=L.ROOT;HW=L.HW
src=HW/'repair_20261011/final_actual.cir'
text=src.read_text(encoding='utf8')
model_path=HW/'models/OPA197_TI/OPAx197.LIB'
(ROOT/'sources/OPA197_TI_original.lib').write_bytes(model_path.read_bytes())
model='.include ../sources/OPA197_TI_original.lib\n'
def build(name,a,d,typ,ix=10e-6):
    source=HW/f'LM393_20k_D{d}_A{a}.cir'
    s=source.read_text(encoding='utf8').split('.options')[0]
    s+='\nVN vn 0 -5\nVP vp 0 5\n'
    # At 10% duty a calibrated physical comparator generates the short pulses.
    if typ=='bare':s+='RXD x 0 1meg\n'
    else:
        vm='V1'
        if typ=='prepost':
            s+='XPRE V1 vb vp vn vb OPAx197\n';vm='vb'
        target='x' if typ=='passive' else 'sum'
        conduct=1/10500-1/100000-1/125000-(1/100000 if typ=='passive' else 0)
        s+=f'RM {vm} {target} 100k\nRN vn {target} 125k\nRG {target} 0 {1/conduct}\n'
        if typ in ('post','prepost'):s+='XPOST sum x vp vn x OPAx197\n'
        s+=f'RX x 0 100k\nCX x 0 2p\nIX x 0 {ix}\n'
    s+=model+f'''
.options reltol=1e-4 method=gear maxord=2 trtol=3
.control
set filetype=binary
set num_threads=1
save v(v1) v(x) i(v5) i(vp) i(vn)
tran 20n 2m 1.5m 20n uic
write {name}.raw
quit
.endc
.end
'''
    return s
def measure(name,data,a,d,typ,ix):
    t=data['time'];v=data['v(v1)'];x=data['v(x)'];dt=10e-9
    # Uniform resampling before quantiles and edge metrics.
    tu=np.arange(t[0],t[-1],dt);v=np.interp(tu,t,v);x=np.interp(tu,t,x);t=tu
    vl=float(np.quantile(v,.05));vh=float(np.quantile(v,.98));thr=(vl+vh)/2
    edges=np.where(np.diff((v>thr).astype(int))!=0)[0]+1
    mask=np.ones(len(t),bool)
    for k in edges:mask &= abs(t-t[k])>1e-6
    high=mask&(v>thr);low=mask&(v<thr)
    target=.105*v-.42
    hi=float(np.median(x[high]));lo=float(np.median(x[low]))
    # X settling relative to its own final plateau, independent of DC error.
    rises=edges[v[edges]>thr];times=[]
    for k in rises:
        end=min(len(t),k+int(4e-6/dt));tol=.01*abs(hi-lo)
        bad=np.where(abs(x[k:end]-hi)>tol)[0]
        times.append(float((bad[-1]+1)*dt) if len(bad) else 0)
    res=dict(name=name,amplitude_setting=a,duty_setting=d,topology=typ,x_fixture_current_a=ix,
        vm_low=float(np.median(v[low])),vm_high=float(np.median(v[high])),
        x_low=lo,x_high=hi,target_x_low=float(np.median(target[low])),target_x_high=float(np.median(target[high])),
        plateau_max_error_v=float(np.max(abs(x[mask]-target[mask]))),
        settling_1pct_own_plateau_s=max(times) if times else None,
        max_total_waveform_error_v=float(np.max(abs(x-target))),
        x_min=float(x.min()),x_max=float(x.max()),
        source_mw=-5000*L.mean(data['time'],data['i(v5)']),
        positive_extra_mw=-5000*L.mean(data['time'],data['i(vp)']),
        negative_extra_mw=5000*L.mean(data['time'],data['i(vn)']),
        status='REAL_LM393_AND_EXISTING_OPA197_MODEL_X_IS_RC_CURRENT_FIXTURE')
    res['netlist_sha256']=L.sha(ROOT/'netlists'/f'{name}.cir')
    (ROOT/'results'/f'{name}.json').write_text(json.dumps(res,indent=2),encoding='utf8')
    print(name, 'Vmpp',res['vm_high']-res['vm_low'],'Xerr',res['plateau_max_error_v'],flush=True)
    return res
def job(a,d,typ,ix=10e-6):
    suffix='' if ix==10e-6 else '_ix'+str(round(ix*1e6))
    name=f'bb_{typ}_a{a}_d{d}'+suffix
    result_path=ROOT/'results'/f'{name}.json'
    if result_path.exists():return json.loads(result_path.read_text())
    full=build(name,a,d,typ,ix)
    source,control=full.split('.control',1)
    (ROOT/'netlists'/f'{name}_source.cir').write_text(source+'\n.end\n',encoding='utf8')
    wrapper=f'* Existing project PSpice compatibility workflow\n.control\nset ngbehavior=ps\nsource ../netlists/{name}_source.cir\n'+control
    data=L.run(name,wrapper)
    if data['time'][-1]<.001999:raise RuntimeError('incomplete transient')
    return measure(name,data,a,d,typ,ix)
if __name__=='__main__':
    cases=[(a,d,typ) for a in (1,2,3,4) for d in (10,30,50) for typ in ('bare','passive','post','prepost')]
    with cf.ThreadPoolExecutor(2) as pool:
        jobs=[pool.submit(job,*c) for c in cases]
        for j in cf.as_completed(jobs):j.result()
    for ix in (-27e-6,27e-6):job(4,10,'prepost',ix)

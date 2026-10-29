"""TI OPAx197 macro-model; compatibility setup before source loading.

Tests distinguish integrated RF with explicit capacitor prebias from a slow
baseband-only power-on test. Neither is the frozen Multisim full system.
"""
from pathlib import Path
import json,sys
import numpy as np
from run_selectivity import HERE,WORK,sha,execute,save,base,config,old
from run_validation import B

MODEL=HERE.parents[1]/'models/OPA197_TI/OPAx197.LIB'

def fixed_write(path,data):
    if path.exists():
        assert path.read_bytes()==data,str(path)+' dependency changed; use a new case name'
    else:path.write_bytes(data)

def bb(c):
    return f'''* Passive 3 V reference, isolated output, noninverting gain.
RVT vcc ref 20k
RVB ref 0 10k
CVREF ref 0 10u
CCOUP out bbin 100n
RBIAS bbin ref 100k
RG neg ref 10k
RFB bbo neg {c['feedback']}
XOPA bbin neg vcc 0 bbo OPAx197
ROUT bbo final 100
RBBLOAD final 0 {c['bb_load']}
CLOAD final 0 {c['bb_cap']}p
'''

def run(name,integrated=True,**kw):
    c=config(**B);c.update(dict(feedback=102000,bb_load=1e6,bb_cap=100,
        wave='sine',duty=.5,step=.5,stop=400,start=150,prebias=.4,cold=False,reference_start=False));c.update(kw)
    WORK.mkdir(exist_ok=True);(HERE/'sources').mkdir(exist_ok=True)
    modelbytes=MODEL.read_bytes();fixed_write(HERE/'sources/OPAx197.LIB',modelbytes)
    fixed_write(WORK/'OPAx197.LIB',modelbytes)
    if integrated:
        env='VMOD mod 0 SIN(0 1 20k)' if c['wave']=='sine' else f"VMOD mod 0 PULSE(-1 1 0 50n 50n {c['duty']*50e-6-50e-9:.12g} 50u)"
        src=env+f"\nBSIG src 0 V={c['ac']}*(1+{c['m']}*v(mod))*sin(2*pi*31meg*time)\n"
        # No duplicate 100k detector load: RBIAS provides the actual interface.
        circuit=base(c,src)+old.detector(dict(dc_return='direct',rd=4700,cd=100,rf=4700,cf=100,load=1e15))+old.models()
        circuit+=bb(c)+f".ic v(out)={c['prebias']} v(bbin)=3 v(ref)=3\n"
    else:
        # Powered-on periodic or cold-start baseband fixture; source is explicitly ideal.
        supply='PWL(0 0 1m 9)' if c['cold'] else '9'
        s=f"PULSE({c['low']} {c['high']} 2m 1u 1u {c['duty']*50e-6-1e-6:.12g} 50u)"
        circuit=f'* Baseband-only startup fixture\nVSUP vcc 0 {supply}\nVREPLAY stim 0 {s}\nRREPLAY stim out 4700\n'+bb(c)
        if c['reference_start']:
            circuit+=f".ic v(ref)=0 v(bbin)=0 v(out)={c['low']}\n"
    circuit+=f'.include "{(WORK/"OPAx197.LIB").as_posix()}"\n.options method=trap reltol=1e-4 trtol=3 temp=27\n.end\n'
    srcpath=HERE/'netlists'/(name+'_source.cir');fixed_write(srcpath,circuit.encode('ascii'))
    local=WORK/srcpath.name;fixed_write(local,srcpath.read_bytes())
    net=f'''* Wrapper; dependency hashes bind the source and original TI library.
* source_sha256={sha(srcpath)}
* model_sha256={sha(MODEL)}
.control
set ngbehavior=ps
source {local.as_posix()}
set filetype=binary
save v(out) v(bbin) v(ref) v(bbo) v(final) i(vsup)
tran {c['step']}n {c['stop']}u {c['start']}u {c['step']}n {'uic' if c['cold'] else ''}
write @RAW@
quit
.endc
.end
'''
    d,r=execute(name,net,c);t=d['time'];v=d['v(final)']
    # Last five complete cycles, independent of the saved start-up window.
    a=c['stop']*1e-6-250e-6;u=a+np.arange(25000)*10e-9
    vu=np.interp(u,t,v);inp=np.interp(u,t,d['v(out)'])
    hs=np.array([2*np.mean(vu*np.exp(-2j*np.pi*20e3*k*u)) for k in range(1,11)])
    low,high=np.quantile(vu,[.02,.98]);threshold=(low+high)/2
    def cross(up):
        ix=np.where(((vu[:-1]<=threshold)&(vu[1:]>threshold)) if up else ((vu[:-1]>=threshold)&(vu[1:]<threshold)))[0]
        return u[ix]+(threshold-vu[ix])/(vu[ix+1]-vu[ix])*(u[ix+1]-u[ix])
    us,ds=cross(True),cross(False);duties=[]
    for x,y in zip(us[:-1],us[1:]):
        fs=ds[(ds>x)&(ds<y)]
        if len(fs)==1:duties.append(100*(fs[0]-x)/(y-x))
    cycles=vu.reshape(5,-1)
    r['metrics']=dict(out_vpp=float(np.ptp(vu)),out_low=float(vu.min()),out_high=float(vu.max()),
        out_dc=float(vu.mean()),det_vpp=float(np.ptp(inp)),fundamental_peak=float(abs(hs[0])),
        thd_2to10=float(np.linalg.norm(hs[1:])/abs(hs[0])) if c['wave']=='sine' else None,
        duty_pct=float(np.mean(duties)) if duties else None,complete_cycles=len(duties),
        cycle_mean_span=float(np.ptp(cycles.mean(axis=1))),cycle_vpp_span=float(np.ptp(np.ptp(cycles,axis=1))),
        ref_final=float(d['v(ref)'][-1]),window_min=float(v.min()),window_max=float(v.max()),
        integrated=integrated,cold=c['cold'],source_sha256=sha(srcpath),model_sha256=sha(MODEL))
    save(r);print(json.dumps(dict(name=name,**r['metrics'])),flush=True);return r

if __name__=='__main__':
    run('B_bb_sine_v2')

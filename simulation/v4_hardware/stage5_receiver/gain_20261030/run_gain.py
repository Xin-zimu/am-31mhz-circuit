"""S05-06 immutable fixtures; original A filter and Q1/Q2 are preserved.

Uses the previous raw reader/runner, but redirects every new file to this stage.
No previous simulations, reports, or model libraries are rewritten.
"""
from pathlib import Path
import sys, json, re, subprocess, time
import numpy as np
HERE=Path(__file__).resolve().parent
STAGE=HERE.parent
PREV=STAGE/'blocker_20261029'
sys.path.insert(0,str(PREV))
import run_diagnosis as d
from run_baseband import bb, MODEL
d.HERE=HERE
d.WORK=Path('D:/ms_xsp/s05_gain_20261030')
WORK=d.WORK
fixed=d.fixed
sha=d.sha
FILTER=PREV/'filters/A2M_r1M.cir'

def execute_budgeted(name,net,c):
    """Explicit budget only after measured short-run cost; same immutable rules."""
    if c.get('timeout_s',90)==90:return d.execute(name,net,c)
    raw=WORK/(name+'.raw');log=WORK/(name+'.log')
    src=HERE/'netlists'/(name+'.cir');rp=HERE/'results'/(name+'.json')
    fixed(src,net.replace('@RAW@',raw.as_posix()).encode('ascii'));fixed(WORK/src.name,src.read_bytes())
    if rp.exists():
        r=json.loads(rp.read_text());assert r['config']==c
        assert all(sha(p)==r[k] for p,k in [(src,'net_sha256'),(raw,'raw_sha256'),(HERE/'results'/log.name,'log_sha256')])
        return d.readraw(raw),r
    assert not raw.exists() and not log.exists()
    tic=time.monotonic()
    try:
        p=subprocess.run([str(d.EXE),'-b','-n','-o',str(log),str(WORK/src.name)],cwd=WORK,capture_output=True,timeout=c['timeout_s'],creationflags=subprocess.CREATE_NO_WINDOW)
        assert p.returncode==0 and raw.exists(),f'exit_code={p.returncode}, raw_exists={raw.exists()}\n'+log.read_text(errors='replace')[-2000:]
        data=d.readraw(raw)
    except Exception as e:
        fixed(HERE/'failures'/(name+'.json'),json.dumps(dict(name=name,config=c,error=str(e),elapsed_s=time.monotonic()-tic,raw_exists=raw.exists()),indent=2).encode())
        if log.exists():fixed(HERE/'failures'/log.name,log.read_bytes())
        raise
    fixed(HERE/'results'/log.name,log.read_bytes())
    return data,dict(name=name,config=c,elapsed_s=time.monotonic()-tic,net_sha256=sha(src),raw_sha256=sha(raw),raw_path=str(raw),log_sha256=sha(log),simulator_sha256=sha(d.EXE))

def init():
    for p in ['sources','results','netlists','failures','records_before','plots']:
        (HERE/p).mkdir(parents=True,exist_ok=True)
    WORK.mkdir(parents=True,exist_ok=True)
    fixed(HERE/'sources/OPAx197.LIB',MODEL.read_bytes())
    fixed(WORK/'OPAx197.LIB',MODEL.read_bytes())

def cfg(**kw):
    c=d.config(front_file=str(FILTER),start=100,stop=400)
    c.update(feedback=210000,bb_load=1e6,bb_cap=100)
    c.update(kw)
    return c

def wrapper(name,net,cmd,c,saves='all'):
    init()
    src=HERE/'netlists'/(name+'_source.cir')
    fixed(src,(net+f'\n.include "{(WORK/"OPAx197.LIB").as_posix()}"\n.options method={c.get("method","trap")} reltol=1e-4 trtol=3 temp=27\n.end\n').encode('ascii'))
    fixed(WORK/src.name,src.read_bytes())
    w=f'''* S05-06. Source SHA256 {sha(src)}
.control
set ngbehavior=ps
source {(WORK/src.name).as_posix()}
set filetype=binary
set num_threads=1
save {saves}
{cmd}
write @RAW@
quit
.endc
.end
'''
    try:
        raw,r=execute_budgeted(name,w,c)
    except subprocess.TimeoutExpired as e:
        fixed(HERE/'failures'/(name+'_stdout.txt'),e.stdout or b'')
        fixed(HERE/'failures'/(name+'_stderr.txt'),e.stderr or b'')
        raise
    if cmd.startswith('tran'):
        t=raw.get('time',np.array([]))
        log=(HERE/'results'/(name+'.log')).read_text(errors='replace')
        if len(t)==0 or t[-1]<c['stop']*1e-6-1e-12 or 'aborted' in log:
            fixed(HERE/'failures'/(name+'_partial.json'),json.dumps(dict(name=name,reason='Incomplete transient; not accepted even if ngspice exit code is 0',last_time_s=float(t[-1]) if len(t) else None,record=r),indent=2).encode())
            raise RuntimeError(name+': incomplete transient, see retained log/raw')
    r['dependencies']={'source_sha256':sha(src),'model_sha256':sha(MODEL),'filter_sha256':sha(Path(c.get('front_file') or FILTER))}
    return raw,r

def probe(name,**kw):
    c=cfg(**kw)
    net='* OPA197 actual passive reference, no imposed node initial conditions\nVSUP vcc 0 9\nVIN out 0 DC 0.2 AC 1\n'+bb(c)
    raw,r=wrapper(name,net,'op',c)
    r['op']={k:float(v[0]) for k,v in raw.items()}
    d.save(r)
    print(json.dumps({'name':name,'op':{k:v for k,v in r['op'].items() if k in ['v(ref)','v(bbin)','v(bbo)','v(final)','i(vsup)']}}),flush=True)
    return raw,r

def rf(name,**kw):
    c=cfg(**kw)
    return d.tran(name,**c)

def metrics(raw,c):
    """Uniform 2 ns samples; count every crossing, retain invalid cycles."""
    a,b=c['start']*1e-6,c['stop']*1e-6
    dt=2e-9
    t=a+np.arange(round((b-a)/dt))*dt
    ans={}
    for node in ['out','bbin','ref','bbo','final']:
        k='v('+node+')'
        if k not in raw:continue
        y=np.interp(t,raw['time'],raw[k]);n=round(50e-6/dt)
        cy=y.reshape(-1,n)
        span=np.quantile(cy,.98,axis=1)-np.quantile(cy,.02,axis=1)
        z=d.coefficient(y,t,20e3)
        m=d.wave_metrics(t,y)
        m.update(dc=float(y.mean()),peak20=float(abs(z)),complex20=[float(z.real),float(z.imag)],
            cycle_count=len(cy),cycle_mean_span=float(np.ptp(cy.mean(axis=1))),
            cycle_robust_span=float(np.ptp(span)),
            mean_span_relative=float(np.ptp(cy.mean(axis=1))/span.mean()),
            robust_span_relative=float(np.ptp(span)/span.mean()),
            max_slew_v_us=float(np.max(np.abs(np.diff(y)))/dt/1e6))
        level=np.mean(np.quantile(y,[.02,.98]))
        def crosses(up):
            ix=np.where((y[:-1]<=level)&(y[1:]>level) if up else (y[:-1]>=level)&(y[1:]<level))[0]
            return t[ix]+(level-y[ix])/(y[ix+1]-y[ix])*dt
        up,dn=crosses(True),crosses(False)
        periods=np.diff(up)
        invalid=sum(len(dn[(dn>x)&(dn<z)])!=1 for x,z in zip(up[:-1],up[1:]))
        m.update(rising_crossings=len(up),falling_crossings=len(dn),complete_crossing_cycles=len(periods),invalid_crossing_cycles=int(invalid),
            period_span_relative=float(np.ptp(periods)/np.mean(periods)) if len(periods)>0 else None,
            rail_fraction=float(np.mean((y<.1)|(y>8.9))))
        m['window_repeatable']=bool(len(cy)>=5 and m['mean_span_relative']<=.001 and m['robust_span_relative']<=.001)
        ans[node]=m
    return ans

def full(name,**kw):
    c=cfg(**kw)
    # Independent, unforced DC solution supplies every internal macro-model
    # capacitor state. UIC then uses these states instead of repeating the
    # previously failed constrained DC solve. This is NOT cold-start evidence.
    op,opr=probe('P_G'+str(1+c['feedback']/10000).replace('.','p')+'_noic',feedback=c['feedback'])
    rc=dict(c);rc['load']=1e15
    rfraw,rfr=rf(name+'_RFopen',**rc)
    mean=rfr['metrics']['nodes']['out']['dc']
    ics={k[2:-1]:float(v[0]) for k,v in op.items() if k.startswith('v(')}
    ics['out']=mean
    for k,v in rfraw.items():
        if k.startswith('v(') and k!='v(out)':ics[k[2:-1]]=float(v[-1])
    net=d.circuit(c,d.source(c))+d.old.old.detector(dict(dc_return='direct',rd=4700,cd=100,rf=4700,cf=100,load=1e15))+d.old.old.models()+bb(c)
    net+='\n* Warm operating-point initialization, all macro internal voltages\n'
    net+=''.join(f'.ic v({k})={v:.16g}\n' for k,v in sorted(ics.items()))
    raw,r=wrapper(name,net,f"tran {c['step']}n {c['stop']}u {c['start']}u {c['step']}n uic",c,d.SAVES+' v(bbin) v(ref) v(bbo) v(final)')
    r['initialization']={'kind':'unforced standalone OPA DC internal state + detector mean','op_result_sha256':sha(HERE/'results'/(opr['name']+'.json')),'rf_result_sha256':sha(HERE/'results'/(rfr['name']+'.json')),'detector_mean':mean,'not_cold_start':True}
    r['metrics']=metrics(raw,c)
    r['rf_metrics']=d.measure(raw,c)
    d.save(r)
    print(json.dumps({'name':name,'final':r['metrics']['final'],'ref':r['metrics']['ref']['dc']}),flush=True)
    return raw,r

def precharge(name,**kw):
    c=cfg(**kw)
    rc=dict(c);rc['load']=1e15
    rfraw,rfr=rf(name+'_RFopen',**rc)
    mean=rfr['metrics']['nodes']['out']['dc']
    net=d.circuit(c,d.source(c))+d.old.old.detector(dict(dc_return='direct',rd=4700,cd=100,rf=4700,cf=100,load=1e15))+d.old.old.models()+bb(c)
    net+=f'''* Diagnostic precharge only: disconnected after 2 ns, not hardware.
VPRE pre 0 {mean:.16g}
VCTRL ctl 0 PWL(0 1 1n 1 2n 0)
SPRE out pre ctl 0 PRECHARGE
.model PRECHARGE SW(Ron=0.001 Roff=1e15 Vt=0.5 Vh=0.1)
'''
    raw,r=wrapper(name,net,f"tran {c['step']}n {c['stop']}u {c['start']}u {c['step']}n",c,d.SAVES+' v(bbin) v(ref) v(bbo) v(final)')
    r['initialization']={'kind':'DC precharge at out, disconnect at 2 ns; normal unforced OPA operating point','detector_mean':mean,'rf_result_sha256':sha(HERE/'results'/(rfr['name']+'.json')),'not_cold_start':True}
    r['metrics']=metrics(raw,c);r['rf_metrics']=d.measure(raw,c)
    d.save(r)
    print(json.dumps({'name':name,'final':r['metrics']['final'],'ref':r['metrics']['ref']['dc']}),flush=True)
    return raw,r

def bb_simple(name,**kw):
    c=cfg(step=20,start=100,stop=400,**kw)
    # DC is 0.2 V and AC starts at the correct cycle average; this is a local
    # sine fixture, not a reconstruction of the complete receiver.
    net='* Actual TI macro, standalone local sine test\nVSUP vcc 0 9\nVIN out 0 SIN(.2 .109 20k)\n'+bb(c)
    raw,r=wrapper(name,net,f"tran 20n 400u 100u 20n",c,'v(out) v(bbin) v(ref) v(bbo) v(final) i(vsup)')
    r['metrics']=metrics(raw,c);d.save(r)
    print(json.dumps({'name':name,'final':r['metrics']['final']}),flush=True)
    return raw,r

def seeded(name,**kw):
    c=cfg(**kw)
    op,opr=probe('P_G'+str(1+c['feedback']/10000).replace('.','p')+'_noic',feedback=c['feedback'])
    rc=dict(c);rc.update(start=100,stop=200,load=1e15)
    rfraw,rfr=rf(name+'_RFopen',**rc)
    mean=rfr['metrics']['nodes']['out']['dc']
    net=d.circuit(c,d.source(c))+d.old.old.detector(dict(dc_return='direct',rd=4700,cd=100,rf=4700,cf=100,load=1e15))+d.old.old.models()+bb(c)
    net+=f'.ic v(out)={mean:.16g} v(bbin)=3 v(ref)=3\n'
    net+=''.join(f'.nodeset {k}={float(v[0]):.16g}\n' for k,v in op.items() if k.startswith('v(xopa.') or k in ['v(bbo)','v(neg)'])
    raw,r=wrapper(name,net,f"tran {c['step']}n {c['stop']}u {c['start']}u {c['step']}n",c,d.SAVES+' v(bbin) v(ref) v(bbo) v(final)')
    r['initialization']={'kind':'internal model nodeset from unforced OP; capacitor prebias at detector mean','detector_mean':mean,'not_cold_start':True}
    if c['stop']-c['start']>=50:
        r['metrics']=metrics(raw,c);r['rf_metrics']=d.measure(raw,c)
    else:r['metrics']={'last':{k:float(v[-1]) for k,v in raw.items() if k in ['v(out)','v(bbin)','v(ref)','v(bbo)','v(final)']}}
    d.save(r);print(json.dumps({'name':name,'metrics':r['metrics'].get('final',r['metrics'])}),flush=True)
    return raw,r

if __name__=='__main__':
    init()
    probe('P_G22_noic')

"""S05-05: immutable short-window receiver diagnostics, ngspice-47.

Names B_* below mean this round's linearity route, NOT S05-03's B=R2.
No original circuit, historical result or model is overwritten.
"""
from pathlib import Path
import sys, json, time, subprocess, hashlib, argparse
import numpy as np
HERE=Path(__file__).resolve().parent
PARENT=HERE.parent
sys.path.insert(0,str(PARENT/'selectivity_20261029'))
import run_selectivity as old
from run_validation import B as R2
WORK=Path('D:/ms_xsp/s05_blocker_20261029')
EXE=old.EXE
sha=old.sha
readraw=old.readraw

def fixed(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        assert path.read_bytes()==data, str(path)+' changed; use a new case name'
    else:path.write_bytes(data)

def execute(name,net,c):
    WORK.mkdir(parents=True,exist_ok=True)
    raw=WORK/(name+'.raw'); log=WORK/(name+'.log')
    src=HERE/'netlists'/(name+'.cir'); result=HERE/'results'/(name+'.json')
    net=net.replace('@RAW@',raw.as_posix())
    fixed(src,net.encode('ascii'));fixed(WORK/src.name,src.read_bytes())
    if result.exists():
        r=json.loads(result.read_text())
        assert sha(src)==r['net_sha256'] and sha(raw)==r['raw_sha256']
        assert sha(HERE/'results'/log.name)==r['log_sha256']
        assert r['config']==c
        return readraw(raw),r
    assert not raw.exists() and not log.exists(), 'Previous incomplete attempt: use a new name'
    tic=time.monotonic()
    try:
        p=subprocess.run([str(EXE),'-b','-n','-o',str(log),str(WORK/src.name)],
            cwd=WORK,capture_output=True,timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
        assert p.returncode==0 and raw.exists(),log.read_text(errors='replace')[-3000:]
        d=readraw(raw)
        assert any(k in d for k in ['time','frequency','v(vcc)'])
    except Exception as e:
        fail=dict(name=name,config=c,error=str(e),elapsed_s=time.monotonic()-tic,
                  net_sha256=sha(src),raw_exists=raw.exists())
        fixed(HERE/'failures'/(name+'.json'),json.dumps(fail,indent=2).encode())
        if log.exists():fixed(HERE/'failures'/log.name,log.read_bytes())
        raise
    fixed(HERE/'results'/log.name,log.read_bytes())
    r=dict(name=name,config=c,elapsed_s=time.monotonic()-tic,net_sha256=sha(src),
           raw_sha256=sha(raw),raw_path=str(raw),log_sha256=sha(log),simulator_sha256=sha(EXE))
    return d,r

def save(r):
    fixed(HERE/'results'/(r['name']+'.json'),json.dumps(r,indent=2,allow_nan=False).encode())

VARIANTS={
 'R2':{},
 'B_E1':{'REU1 e1 eb1 33':'REU1 e1 eb1 47'},
 'B_E2':{'REU2 e2 eb2 33':'REU2 e2 eb2 47'},
 'B_bias1':{'RBT1 vcc b1 22k':'RBT1 vcc b1 27k'},
 'B_bias2':{'RBT2 vcc b2 22k':'RBT2 vcc b2 27k'},
 'B_gain1':{'RC1 vcc c1 1000':'RC1 vcc c1 820'},
 'B_gain2':{'RC2 vcc c2 1000':'RC2 vcc c2 820'},
}

def config(**kw):
    c=old.config(**R2);c.update(variant='R2',stop=200,start=100,blockers=[],
                                wave='sine',duty=.5,front_file=None)
    c.update(kw);return c

def source(c):
    env='VMOD mod 0 SIN(0 1 20k)' if c['wave']=='sine' else f"VMOD mod 0 PULSE(-1 1 0 50n 50n {c['duty']*50e-6-50e-9:.12g} 50u)"
    extra=''.join(f'+{a:.12g}*sin(2*pi*{f:.12g}*time+{p:.12g})' for f,a,p in c['blockers'])
    return env+f"\nBSIG src 0 V={c['ac']}*(1+{c['m']}*v(mod))*sin(2*pi*31meg*time){extra}\n"

def circuit(c,src):
    net=old.base(c,src)
    for a,b in VARIANTS.get(c['variant'],{}).items():
        assert a in net,a
        net=net.replace(a,b)
    if c.get('front_file'):
        net=net.replace(old.front(c),Path(c['front_file']).read_text())
    return net

def coefficient(y,t,f):
    return 2*np.mean(y*np.exp(-2j*np.pi*f*t))

def wave_metrics(t,y):
    lo,hi=np.quantile(y,[.02,.98]);span=hi-lo
    def crossings(level,up=True):
        ix=np.where(((y[:-1]<=level)&(y[1:]>level)) if up else ((y[:-1]>=level)&(y[1:]<level)))[0]
        return t[ix]+(level-y[ix])/(y[ix+1]-y[ix])*(t[ix+1]-t[ix])
    u=crossings((lo+hi)/2);d=crossings((lo+hi)/2,False)
    duty=[];period=[]
    for a,b in zip(u[:-1],u[1:]):
        fs=d[(d>a)&(d<b)]
        if len(fs)==1:duty.append((fs[0]-a)/(b-a)*100);period.append(b-a)
    rise=[];fall=[]
    for middle,up,dest in [(u,True,rise),(d,False,fall)]:
        ca=crossings(lo+span*(.1 if up else .9),up)
        cb=crossings(lo+span*(.9 if up else .1),up)
        for x in middle:
            a=ca[(ca<x)&(ca>x-5e-6)];b=cb[(cb>x)&(cb<x+5e-6)]
            if len(a) and len(b):dest.append(b[0]-a[-1])
    return dict(vpp=float(np.ptp(y)),robust_vpp=float(span),low=float(y.min()),high=float(y.max()),
        duty_pct=float(np.mean(duty)) if duty else None,
        frequency_hz=float(1/np.mean(period)) if period else None,
        rise_10_90_us=float(np.median(rise)*1e6) if rise else None,
        fall_90_10_us=float(np.median(fall)*1e6) if fall else None,
        overshoot_pct=float((y.max()-hi)/span*100),undershoot_pct=float((lo-y.min())/span*100))

def measure(d,c):
    t=d['time'];a=c['start']*1e-6;b=c['stop']*1e-6
    assert t[-1]>=b-1e-12 and t[0]<=a+1e-9
    u=a+np.arange(round((b-a)/.5e-9))*.5e-9
    m={'nodes':{}}
    freqs=[20e3,29e6,30.98e6,31e6,31.02e6,33e6]
    for node in ['src','input','port','b1','c1','b2','c2','ee','rf','det','out','final']:
        if 'v('+node+')' not in d:continue
        y=np.interp(u,t,d['v('+node+')'])
        cs={str(int(f)):coefficient(y,u,f) for f in freqs}
        m['nodes'][node]=dict(dc=float(y.mean()),raw_vpp=float(np.ptp(y)),
              spectral_peak={f:float(abs(z)) for f,z in cs.items()},
              spectral_complex={f:[float(z.real),float(z.imag)] for f,z in cs.items()})
        if node in ['det','out','final']:
            hs=np.array([coefficient(y,u,20e3*k) for k in range(1,11)])
            m['nodes'][node]['thd_2to10']=float(np.linalg.norm(hs[1:])/abs(hs[0])) if c['wave']=='sine' else None
            # Average one carrier cycle; retains 2MHz beat, as in historical report.
            n=round((b-a)*31e6);tt=a+np.arange(n*64)/31e6/64
            yy=np.interp(tt,t,d['v('+node+')']).reshape(n,64).mean(axis=1)
            te=a+(np.arange(n)+.5)/31e6
            m['nodes'][node]['envelope']=wave_metrics(te,yy)
            cy=yy.reshape(-1,1550)
            m['nodes'][node]['cycle_mean_span']=float(np.ptp(cy.mean(axis=1)))
            m['nodes'][node]['cycle_vpp_span']=float(np.ptp(np.ptp(cy,axis=1)))
    for k in [1,2]:
        if f'v(c{k})' not in d:continue
        vc=d[f'v(c{k})'];ve=d[f'v(e{k})'];vb=d[f'v(b{k})']
        m[f'q{k}']=dict(vce_min=float(np.min(vc-ve)),vbc_max=float(np.max(vb-vc)),
           vc_mean=float(np.trapezoid(vc,t)/(t[-1]-t[0])),ve_mean=float(np.trapezoid(ve,t)/(t[-1]-t[0])))
    if 'i(vsup)' in d:m['supply_power_w']=float(-9*np.trapezoid(d['i(vsup)'],t)/(t[-1]-t[0]))
    return m

SAVES='v(src) v(input) v(port) v(b1) v(c1) v(e1) v(b2) v(c2) v(e2) v(ee) v(rf) v(det) v(out) i(vsup)'
def tran(name,**kw):
    c=config(**kw)
    net=circuit(c,source(c))+old.old.detector(dict(dc_return='direct',rd=4700,cd=100,rf=4700,cf=100,load=c['load']))+old.old.models()
    net+=f'''
.options method=trap reltol=1e-4 trtol=3 abstol=1p vntol=1u temp=27 tnom=27
.control
set filetype=binary
set num_threads=1
save {SAVES}
tran {c['step']}n {c['stop']}u {c['start']}u {c['step']}n
write @RAW@
quit
.endc
.end
'''
    d,r=execute(name,net,c);r['metrics']=measure(d,c);save(r)
    print(json.dumps(dict(name=name,bb=r['metrics']['nodes']['out']['spectral_peak']['20000'],
        rf=r['metrics']['nodes']['rf']['spectral_peak']['31000000'],elapsed=r['elapsed_s'])),flush=True)
    return d,r

def ac(name,**kw):
    c=config(**kw)
    net=circuit(c,'VIN src 0 DC 0 AC 1\n')+'RTEST rf 0 2000\nCTEST rf 0 10p\n'+old.old.models()
    net+='''
.options temp=27 tnom=27
.control
set filetype=binary
save all
ac lin 2401 20meg 44meg
write @RAW@
quit
.endc
.end
'''
    d,r=execute(name,net,c);f=d['frequency'].real;g=abs(d['v(rf)']);g31=np.interp(31e6,f,g)
    good=f[g>=max(g)/np.sqrt(2)]
    r['metrics']=dict(g31=float(g31),peak_f=float(f[g.argmax()]),
       lo3=float(good.min()),hi3=float(good.max()),bw=float(np.ptp(good)),
       db29=float(20*np.log10(np.interp(29e6,f,g)/g31)),db33=float(20*np.log10(np.interp(33e6,f,g)/g31)))
    save(r);print(json.dumps(dict(name=name,**r['metrics'])),flush=True);return d,r

def op(name,**kw):
    c=config(**kw)
    net=circuit(c,'VIN src 0 DC 0\n')+old.old.detector(dict(dc_return='direct',rd=4700,cd=100,rf=4700,cf=100,load=100000))+old.old.models()
    net+='''
.control
set filetype=binary
save all @q1[ic] @q2[ic] @qbuf[ic]
op
write @RAW@
quit
.endc
.end
'''
    d,r=execute(name,net,c);r['metrics']={k:float(v[0]) for k,v in d.items()};save(r)
    return d,r

def baseline():
    ac('R2_ac');op('R2_op');tran('R2_clean')
    for f in [29e6,33e6]:
        for a in [.003,.006,.01]:tran(f'R2_{int(f/1e6)}_{a*1000:g}',blockers=[[f,a,0]])
    for a in [.003,.006,.01]:tran(f'R2_dual_{a*1000:g}',blockers=[[29e6,a,0],[33e6,a,0]])

def sweep_b():
    for v in VARIANTS:
        if v=='R2':continue
        op(v+'_op',variant=v);ac(v+'_ac',variant=v);tran(v+'_clean',variant=v)
        for f in [29e6,33e6]:tran(f'{v}_{int(f/1e6)}_6',variant=v,blockers=[[f,.006,0]])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('batch',choices=['baseline','b']);args=p.parse_args()
    baseline() if args.batch=='baseline' else sweep_b()

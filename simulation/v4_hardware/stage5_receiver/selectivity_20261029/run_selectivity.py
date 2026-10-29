"""S05 selection/blocker experiments, separate from immutable first batch.

All voltages are open-circuit source peak, including the independent blocker.
Small-signal AC uses the same 1k return plus 2k||10p test load as the R1 reference.
Inductor ESR is an explicit constant effective loss at 31 MHz, with parallel Cp.
"""
from pathlib import Path
import argparse,sys,subprocess,json,time,hashlib
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import run_s05 as old

HERE=Path(__file__).resolve().parent
WORK=Path('D:/ms_xsp/s05_selectivity_20261029')
EXE=old.EXE
sha=old.sha
readraw=old.readraw

def config(**kw):
    c=dict(kind='A',cs=33,lp=680,ct=10,cp=1,q=50,rs=50,reu=22,ceb=10000,
           inter=1000,temp=27,ac=.01,m=.5,wave='sine',duty=.5,
           blocker_f=1.6e6,blocker_a=0,phase=0,step=.5,stop=400,start=150,
           lscale=1,cscale=1,supply=9,load=100000)
    c.update(kw);return c

def front(c):
    if c['kind']=='R1':return 'RJOIN input port 1u\n'
    l=c['lp']*c['lscale']*1e-9;esr=2*np.pi*31e6*l/c['q']
    return f'''* Capacitive-input parallel resonator before any gain stage.
CSEL input port {c['cs']*c['cscale']}p
RLOSS port ln {esr:.12g}
LSEL ln 0 {l:.12g}
CSELF port 0 {c['cp']}p
CTUNE port 0 {c['ct']*c['cscale']}p
'''

def amp(c):
    s=old.amplifier(dict(reu=c['reu'],rreturn=1000))
    s=s.replace('VSUP vcc 0 9',f"VSUP vcc 0 {c['supply']}")
    for i in [1,2]:s=s.replace(f'CEB{i} eb{i} 0 10n',f"CEB{i} eb{i} 0 {c['ceb']}p")
    s=s.replace('CIN2 c1 b2 1n',f"CIN2 c1 b2 {c['inter']}p")
    s=s.replace('CBUF c2 bb 1n',f"CBUF c2 bb {c['inter']}p")
    return s

def base(c,source):
    return ('* S05 selection fixture; not wireless qualification\n'+source+
       f"RSOURCE src input {c['rs']}\n"+front(c)+amp(c))

def execute(name,net,c):
    WORK.mkdir(parents=True,exist_ok=True)
    for folder in ['netlists','results']:(HERE/folder).mkdir(exist_ok=True)
    raw=WORK/(name+'.raw'); log=WORK/(name+'.log'); src=HERE/'netlists'/(name+'.cir')
    rp=HERE/'results'/(name+'.json');net=net.replace('@RAW@',raw.as_posix())
    failures=HERE/'failures.json'
    if failures.exists():
        assert name not in {f['name'] for f in json.loads(failures.read_text())},name+' is a retained failed attempt; use a new case name'
    if rp.exists():
        r=json.loads(rp.read_text());assert sha(src)==r['net_sha256']
        assert src.read_text(encoding='ascii')==net,name+' config changed'
        assert sha(raw)==r['raw_sha256'];return readraw(raw),r
    assert not raw.exists(),name+' raw exists without completed result'
    # Write exact LF bytes; normalize reads in cache, hash actual evidence bytes.
    src.write_bytes(net.encode('ascii'));local=WORK/src.name;local.write_bytes(src.read_bytes())
    tic=time.monotonic()
    p=subprocess.run([str(EXE),'-b','-n','-o',str(log),str(local)],cwd=WORK,
        capture_output=True,timeout=240,creationflags=subprocess.CREATE_NO_WINDOW)
    (HERE/'results'/log.name).write_bytes(log.read_bytes())
    assert p.returncode==0 and raw.exists(),log.read_text(errors='replace')[-3000:]
    r=dict(name=name,config=c,elapsed_s=time.monotonic()-tic,net_sha256=sha(src),
        raw_sha256=sha(raw),raw_path=str(raw),log_sha256=sha(log),simulator_sha256=sha(EXE))
    d=readraw(raw)
    assert 'time' in d or 'frequency' in d,name+' has no numerical analysis array; inspect log'
    return d,r

def save(r):
    (HERE/'results'/(r['name']+'.json')).write_text(json.dumps(r,indent=2),encoding='utf-8')

def ac(name,**kw):
    c=config(**kw)
    cir=base(c,'VIN src 0 DC 0 AC 1\n')+'RTEST rf 0 2000\nCTEST rf 0 10p\n'+old.models()
    cir+=f"\n.options temp={c['temp']} tnom=27\n"
    net=cir+'''.control
set filetype=binary
save all
ac dec 400 100k 300meg
write @RAW@
quit
.endc
.end
'''
    d,r=execute(name,net,c);f=d['frequency'].real;h=d['v(rf)'];g=abs(h)
    gi=lambda x:float(np.interp(x,f,g))
    zi=c['rs']*d['v(input)']/(1-d['v(input)']);z31=np.interp(31e6,f,zi)
    ph=np.unwrap(np.angle(h));gd=-np.gradient(ph,2*np.pi*f)
    band=(f>=30.8e6)&(f<=31.2e6)
    valid=f[g>=max(g)/np.sqrt(2)]
    r['metrics']=dict(g31=gi(31e6),g1p6=gi(1.6e6),peak_gain=float(max(g)),
        peak_f=float(f[np.argmax(g)]),lo3db_sample=float(valid.min()),hi3db_sample=float(valid.max()),
        input_z31_real=float(z31.real),input_z31_imag=float(z31.imag),
        return_loss31_db=float(-20*np.log10(abs((z31-c['rs'])/(z31+c['rs'])))),
        sideband_minus_db=float(20*np.log10(gi(30.8e6)/gi(31e6))),
        sideband_plus_db=float(20*np.log10(gi(31.2e6)/gi(31e6))),
        group_delay31_s=float(np.interp(31e6,f,gd)),
        group_delay_band_span_s=float(np.ptp(gd[band])),
        relative_1p6_db=float(20*np.log10(gi(1.6e6)/gi(31e6))))
    save(r);print(json.dumps(dict(name=name,**r['metrics'])),flush=True)
    return r

def noise(name,**kw):
    c=config(**kw)
    net=base(c,'VIN src 0 DC 0 AC 1\n')+'RTEST rf 0 2000\nCTEST rf 0 10p\n'+old.models()
    net+=f'''\n.options temp={c['temp']} tnom=27
.control
set filetype=binary
noise v(rf) VIN dec 250 100k 300meg
setplot noise1
write @RAW@ all
quit
.endc
.end
'''
    d,r=execute(name,net,c);f=d['frequency'];en=d['inoise_spectrum'];on=d['onoise_spectrum']
    g=on/en;g31=float(np.interp(31e6,f,g));e31=float(np.interp(31e6,f,en))
    r['metrics']=dict(en31=e31,nf31_db=float(10*np.log10(e31**2/(4*1.380649e-23*(273.15+c['temp'])*c['rs']))),
        output_noise_rms_100k_300meg=float(np.sqrt(np.trapezoid(on**2,f))),
        gain_normalized_bw_hz=float(np.trapezoid(g**2,f)/g31**2),
        note='Finite 0.1-300 MHz model integration, DC linearized test load; no detector noise or external noise')
    save(r);print(json.dumps(dict(name=name,**r['metrics'])),flush=True);return r

def measure(d,c):
    t=d['time']; start=c['start']*1e-6;stop=c['stop']*1e-6
    assert t[-1]>=stop-1e-12 and t[0]<=start+1e-9
    # Coherent 5 modulation cycles, 0.5 ns grid. Fourier sums include all
    # broadband RF in RMS residual, not falsely labelled as thermal noise.
    dt=.5e-9;tu=np.arange(round((stop-start)/dt))*dt+start
    out=np.interp(tu,t,d['v(out)']);rf=np.interp(tu,t,d['v(rf)'])
    def coeff(v,f):return 2*np.mean(v*np.exp(-2j*np.pi*f*tu))
    hs=np.array([coeff(out,20e3*k) for k in range(1,21)])
    fit=out.mean()+sum((h*np.exp(2j*np.pi*20e3*(k+1)*tu)).real for k,h in enumerate(hs))
    rmsres=float(np.sqrt(np.mean((out-fit)**2)))
    # Envelope for peak/duty: average 1 RF cycle (old first-batch convention).
    nc=round((stop-start)*31e6);ug=start+np.arange(nc*64)/31e6/64
    env=np.interp(ug,t,d['v(out)']).reshape(nc,64).mean(axis=1)
    te=start+(np.arange(nc)+.5)/31e6
    lo,hi=np.quantile(env,[.02,.98]);th=(lo+hi)/2
    m=dict(out_raw_vpp=float(np.ptp(d['v(out)'])),out_envelope_vpp=float(np.ptp(env)),
       out_robust_vpp=float(hi-lo),out_dc=float(out.mean()),bb_fundamental_peak=float(abs(hs[0])),
       thd_2to10=float(np.linalg.norm(hs[1:10])/abs(hs[0])) if c['wave']=='sine' else None,
       rf_plus_unmodelled_residual_rms=rmsres,
       wanted_rf_carrier_peak=float(abs(coeff(rf,31e6))),
       blocker_rf_peak=float(abs(coeff(rf,c['blocker_f']))),
       supply_power_w=float(-c['supply']*np.trapezoid(d['i(vsup)'],t)/(t[-1]-t[0])))
    for k in [1,2]:
        m[f'q{k}_vce_min']=float(np.min(d[f'v(c{k})']-d[f'v(e{k})']))
        m[f'q{k}_vbc_max']=float(np.max(d[f'v(b{k})']-d[f'v(c{k})']))
    m['qbuf_vce_min']=float(c['supply']-np.max(d['v(ee)']))
    cyc=env.reshape(-1,1550)
    m['cycle_mean_span']=float(np.ptp(cyc.mean(axis=1)))
    m['cycle_vpp_span']=float(np.ptp(np.ptp(cyc,axis=1)))
    if c['wave']=='square':
        def cross(up):
            ix=np.where(((env[:-1]<=th)&(env[1:]>th)) if up else ((env[:-1]>=th)&(env[1:]<th)))[0]
            return te[ix]+(th-env[ix])/(env[ix+1]-env[ix])*(te[ix+1]-te[ix])
        ups=cross(True);downs=cross(False);ds=[];ps=[];bad=0
        for a,b in zip(ups[:-1],ups[1:]):
            falls=downs[(downs>a)&(downs<b)]
            if len(falls)==1:ds.append(100*(falls[0]-a)/(b-a));ps.append(b-a)
            else:bad+=1
        m.update(duty_pct=float(np.mean(ds)) if ds else None,
            frequency_hz=float(1/np.mean(ps)) if ps else None,
            rising_crossings=len(ups),falling_crossings=len(downs),complete_cycles=len(ds),bad_cycles=bad)
    return m

def tran(name,**kw):
    c=config(**kw)
    env='VMOD mod 0 SIN(0 1 20k)' if c['wave']=='sine' else f"VMOD mod 0 PULSE(-1 1 0 50n 50n {c['duty']*50e-6-50e-9:.12g} 50u)"
    source=env+f'''\nBSIG src 0 V={c['ac']}*(1+{c['m']}*v(mod))*sin(2*pi*31meg*time)+{c['blocker_a']}*sin(2*pi*{c['blocker_f']}*time+{c['phase']})
'''
    net=base(c,source)+old.detector(dict(dc_return='direct',rd=4700,cd=100,rf=4700,cf=100,load=c['load']))+old.models()
    net+=f'''\n.options method=trap reltol=1e-4 trtol=3 abstol=1p vntol=1u temp={c['temp']} tnom=27
.control
set filetype=binary
set num_threads=1
save v(src) v(port) v(rf) v(det) v(out) v(c1) v(b1) v(e1) v(c2) v(b2) v(e2) v(ee) i(vsup)
tran {c['step']}n {c['stop']}u {c['start']}u {c['step']}n
write @RAW@
quit
.endc
.end
'''
    d,r=execute(name,net,c);r['metrics']=measure(d,c);save(r)
    m=r['metrics'];print(json.dumps(dict(name=name,vpp=m['out_envelope_vpp'],fund=m['bb_fundamental_peak'],thd=m['thd_2to10'],q1min=m['q1_vce_min'],q2min=m['q2_vce_min'])),flush=True)
    return r

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('batch',choices=['screen'])
    a=p.parse_args()
    ac('baseline_ac',kind='R1')
    for cs in [22,33,47,68]:
        for ct in [0,5,10,15,22]:ac(f'A_cs{cs}_ct{ct}',cs=cs,ct=ct)
    for ceb in [220,330,470,680]:
        for ct in [5,10,15]:ac(f'B_ceb{ceb}_ct{ct}',kind='B',cs=33,ct=ct,ceb=ceb,reu=15,inter=100)

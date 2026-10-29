"""Independent S05 receiver experiments. No wireless/sensitivity acceptance implied."""
from pathlib import Path
import argparse, hashlib, json, subprocess, time, urllib.request
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WORK = Path('D:/ms_xsp/s05_receiver_20261029')
EXE = Path('D:/ms_xsp/s04_crosscheck_20261017/Spice64/bin/ngspice_con.exe')
FC, FM = 31e6, 20e3

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def prepare():
    WORK.mkdir(parents=True, exist_ok=True)
    (HERE/'sources').mkdir(exist_ok=True)
    p = HERE/'sources/BAT85_Nexperia.txt'
    url = 'https://assets.nexperia.com/documents/spice-model/BAT85.txt'
    if not p.exists():
        p.write_bytes(urllib.request.urlopen(url, timeout=45).read())
    assert '2.076E-7' in p.read_text(errors='replace')
    q = HERE.parent/'stage4_rf_oscillator/advance_20261029/2N3904_UNCG.lib'
    (HERE/'sources/2N3904_UNCG.lib').write_bytes(q.read_bytes())
    manifest = dict(date='2026-10-29', diode_url=url, diode_sha256=sha(p),
        transistor_url='https://home.uncg.edu/~ehhellen/spice_stuff.html',
        transistor_sha256=sha(q), simulator=str(EXE), simulator_sha256=sha(EXE),
        diode='Nexperia BAT85; NOT Vishay BAT85S',
        transistor='UNCG educational 2N3904; delivered manufacturer/lot not verified')
    (HERE/'sources/manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')

def models(c=None):
    # Comments may contain a non-ASCII micro sign; retain original source separately.
    d = (HERE/'sources/BAT85_Nexperia.txt').read_text(errors='replace')
    d = '\n'.join(s for s in d.splitlines() if not s.strip().startswith('*'))
    if c and c.get('diode_stress'):
        # Exploratory perturbation, NOT BAT85S or manufacturer process corners.
        d=d.replace('IS = 2.076E-7','IS = 1.038E-7').replace('RS = 2.326','RS = 4.652')
        d=d.replace('CJO = 1.21E-11','CJO = 2.42E-11')
        d=d.replace('.ENDS','+ TT = 2n\n.ENDS')
    return d + '\n' + (HERE/'sources/2N3904_UNCG.lib').read_text()

def readraw(p):
    with p.open('rb') as f:
        header=[]; names=[]; inside=False
        while True:
            b=f.readline()
            if not b: raise ValueError('Missing Binary marker')
            s=b.decode('ascii').strip()
            if s=='Binary:': break
            header.append(s)
            if s=='Variables:': inside=True; continue
            if inside and s: names.append(s.split()[1].lower())
        complex_data = any('complex' in s for s in header if s.startswith('Flags:'))
        a=np.fromfile(f,dtype='<c16' if complex_data else '<f8').reshape(-1,len(names))
    assert len(a)==int(next(s.split(':')[1] for s in header if s.startswith('No. Points:')))
    assert np.isfinite(a).all()
    return dict(zip(names,a.T))

def run_net(name, net, config):
    raw=WORK/(name+'.raw'); log=WORK/(name+'.log'); src=HERE/'netlists'/(name+'.cir')
    src.parent.mkdir(exist_ok=True)
    net=net.replace('@RAW@',raw.as_posix())
    record=HERE/'results'/(name+'.json'); record.parent.mkdir(exist_ok=True)
    if record.exists():
        r=json.loads(record.read_text())
        # net_sha256 is the hash of the netlist file as written to disk (CRLF on Windows);
        # compare content with newlines normalized so a re-run reuses evidence instead of
        # reporting a false "config changed".
        assert src.exists() and sha(src)==r['net_sha256'], 'Evidence changed: '+name
        assert src.read_bytes().replace(b'\r\n',b'\n').decode('ascii')==net, name+' config changed'
        assert raw.exists() and sha(raw)==r['raw_sha256'], 'Evidence changed'
        return readraw(raw),r
    assert not raw.exists(), 'Use a new name rather than overwrite evidence'
    src.write_text(net,encoding='ascii'); local=WORK/src.name;local.write_bytes(src.read_bytes())
    start=time.monotonic()
    p=subprocess.run([str(EXE),'-b','-n','-o',str(log),str(local)],cwd=WORK,
        capture_output=True,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
    (HERE/'results'/(name+'.log')).write_bytes(log.read_bytes())
    assert p.returncode==0 and raw.exists(), log.read_text(errors='replace')[-3000:]
    r=dict(name=name, config=config, elapsed_s=time.monotonic()-start,
           net_sha256=sha(src),raw_sha256=sha(raw),raw_path=str(raw),
           log_sha256=sha(log), simulator_sha256=sha(EXE))
    return readraw(raw),r

def save_result(r):
    (HERE/'results'/(r['name']+'.json')).write_text(json.dumps(r,indent=2),encoding='utf-8')

def detector(c):
    return f'''* Actual Nexperia BAT85 manufacturer model; not BAT85S
{('RCONNECT rf an 0.1' if c.get('dc_return')=='direct' else 'CCOUP rf an 1n')}
XDET an det BAT85
RDET det 0 {c.get('rd',10000)}
CDET det 0 {c.get('cd',100)}p
RFILT det out {c.get('rf',1000)}
CFILT out 0 {c.get('cf',470)}p
RLOAD out 0 {c.get('load',100000)}
'''

def amplifier(c):
    stages=c.get('stages',2)
    s='VSUP vcc 0 9\n'
    prev='port'
    for k in range(1,stages+1):
        s+=f'''CIN{k} {prev} b{k} 1n
RBT{k} vcc b{k} 22k
RBB{k} b{k} 0 4.7k
Q{k} c{k} b{k} e{k} 2N3904
RC{k} vcc c{k} {c.get('rc',1000)}
REU{k} e{k} eb{k} {c.get('reu',47)}
REB{k} eb{k} 0 220
CEB{k} eb{k} 0 10n
'''
        prev=f'c{k}'
        if c.get('tuned'):
            s+=f'''RLOSS{k} vcc l{k} 2.65
LTANK{k} l{k} c{k} 680n
CTANK{k} vcc c{k} {c.get('ct',33)}p
'''
    # Emitter follower reduces detector source impedance and isolates CE stages.
    s+=f'''CBUF {prev} bb 1n
RBTB vcc bb 10k
RBBB bb 0 10k
QBUF vcc bb ee 2N3904
REBUF ee 0 470
COBUF ee rf 1n
RRF rf 0 {c.get('rreturn','100k')}
'''
    return s

def transient(name, **kwargs):
    c=dict(ac=.5,m=.5,wave='sine',duty=.5,rs=50,cd=100,rd=10000,
           rf=1000,cf=470,load=100000,step_ns=.5,stop_us=300,start_us=100,temp=27,amp=False)
    c.update(kwargs)
    if c['wave']=='sine': env='VMOD mod 0 SIN(0 1 20k)'
    else:
        # 50 ns edges; width chosen so midpoint crossing duty is exact.
        env=f"VMOD mod 0 PULSE(-1 1 0 50n 50n {c['duty']*50e-6-50e-9:.12g} 50u)"
    net=f'''* S05 isolated AM fixture; Ac is open-circuit carrier peak, not Vpp
.param Ac={c['ac']} MODINDEX={c['m']}
{env}
BSIG src 0 V=Ac*(1+MODINDEX*v(mod))*sin(2*pi*31meg*time)
RSOURCE src {'port' if c['amp'] else 'rf'} {c['rs']}
'''
    if c['amp']: net+=amplifier(c)
    net+=detector(c)+models(c)+f'''
.options method=trap reltol=1e-4 abstol=1p vntol=1u trtol=3 temp={c['temp']} tnom=27
.control
set filetype=binary
set num_threads=1
save v(src) v(mod) v(rf) v(an) v(det) v(out) {'v(c1) v(e1) v(c2) v(e2) v(ee) i(vsup)' if c['amp'] else ''}
tran {c['step_ns']}n {c['stop_us']}u {c['start_us']}u {c['step_ns']}n
write @RAW@
quit
.endc
.end
'''
    d,r=run_net(name,net,c)
    r['metrics']=measure(d,c)
    save_result(r)
    m=r['metrics']
    print(json.dumps(dict(name=name,ac=c['ac'],vpp=m['out_envelope_vpp'],thd=m['out_thd_2to10'],duty=m.get('duty_pct'),ripple=m['out_rf_residual_rms']),ensure_ascii=True),flush=True)
    return r

def measure(d,c):
    t=d['time']; start=c['start_us']*1e-6; stop=c['stop_us']*1e-6
    assert t[-1]>=stop-1e-12 and t[0]<=start+1e-9
    # Uniform 64 samples per RF cycle, exactly 1550 RF cycles per modulation cycle.
    nc=int(round((stop-start)*FC)); tu=start+np.arange(nc*64)/FC/64
    te=start+(np.arange(nc)+.5)/FC
    envelopes={}; residual={}; metrics={}
    for key in ['src','rf','an','det','out']:
        v=np.interp(tu,t,d['v('+key+')']).reshape(nc,64)
        avg=v.mean(axis=1); envelopes[key]=avg
        metrics[key+'_raw_vpp']=float(np.ptp(d['v('+key+')']))
        metrics[key+'_dc']=float(avg.mean())
        if key in ['src','rf','an']:
            # Local carrier fundamental amplitude, insensitive to DC.
            amp=2*np.abs(v@np.exp(-2j*np.pi*np.arange(64)/64)/64)
            metrics[key+'_carrier_peak_min']=float(amp.min())
            metrics[key+'_carrier_peak_max']=float(amp.max())
        else:
            trend=np.interp(tu,te,avg).reshape(nc,64)
            residual[key]=v-trend
            # Exclude first/last carrier cycle where interpolation is clamped.
            metrics[key+'_rf_residual_rms']=float(np.sqrt(np.mean(residual[key][1:-1]**2)))
            metrics[key+'_rf_residual_pp_max']=float(np.max(np.ptp(residual[key][1:-1],axis=1)))
            metrics[key+'_envelope_vpp']=float(np.ptp(avg))
            hs=np.array([2*abs(np.mean(avg*np.exp(-2j*np.pi*FM*k*te))) for k in range(1,11)])
            metrics[key+'_fundamental_peak']=float(hs[0])
            metrics[key+'_thd_2to10']=float(np.linalg.norm(hs[1:])/hs[0]) if c['wave']=='sine' else None
            cyc=avg.reshape(-1,1550)
            metrics[key+'_cycle_mean_span']=float(np.ptp(cyc.mean(axis=1)))
            metrics[key+'_cycle_vpp_span']=float(np.ptp(np.ptp(cyc,axis=1)))
    v=envelopes['out']; lo,hi=np.quantile(v,[.02,.98]); metrics['out_robust_vpp']=float(hi-lo)
    if c['wave']=='square':
        threshold=(hi+lo)/2
        up=np.where((v[:-1]<=threshold)&(v[1:]>threshold))[0]
        down=np.where((v[:-1]>=threshold)&(v[1:]<threshold))[0]
        def crossings(idx): return te[idx]+(threshold-v[idx])/(v[idx+1]-v[idx])*(te[idx+1]-te[idx])
        ups=crossings(up);downs=crossings(down); duties=[]; periods=[]
        for a,b in zip(ups[:-1],ups[1:]):
            falls=downs[(downs>a)&(downs<b)]
            if len(falls)==1: duties.append((falls[0]-a)/(b-a)*100);periods.append(b-a)
        metrics.update(duty_pct=float(np.mean(duties)) if duties else None,
            frequency_hz=float(1/np.mean(periods)) if periods else None,
            rising_crossings=len(ups),falling_crossings=len(downs),complete_cycles=len(duties))
    if c['amp']:
        for k in [1,2]:
            metrics[f'q{k}_vce_min']=float(np.min(d[f'v(c{k})']-d[f'v(e{k})']))
        metrics['supply_power_w']=float(-9*np.trapezoid(d['i(vsup)'],t)/(t[-1]-t[0]))
    # Compact waveform evidence for plots; large raw retained with hashes.
    return metrics

def batch1():
    for a in [.01,.03,.05,.1,.2,.3,.5,.8,1.2,2.0]:
        transient('det_a'+str(a).replace('.','p'),ac=a)
    for cd in [47,220,470]: transient('det_cd'+str(cd),cd=cd)
    for load in [10000,1000000]: transient('det_load'+str(load),load=load)
    for rs in [200,1000]: transient('det_rs'+str(rs),rs=rs)
    for m in [.125,.25,.75,.9]: transient('det_m'+str(m).replace('.','p'),m=m)
    for a in [.1,.5,1.2]:
        for duty in [.1,.3,.5]:
            transient(f'square_a{a}_d{duty}'.replace('.','p'),ac=a,wave='square',duty=duty)
    transient('det_converge_025ns',step_ns=.25)
    transient('square_converge_025ns',wave='square',duty=.1,step_ns=.25)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('batch',choices=['prepare','detector'])
    args=parser.parse_args();prepare()
    if args.batch=='detector':batch1()

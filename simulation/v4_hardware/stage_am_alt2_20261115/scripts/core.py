"""AM-ALT.1 base modulation continuation. No historical file writes.

Fixtures are not antenna models or course output-amplitude requirements.
Binary reader adapted from stage_am_ad835_1/scripts/rf_study.py.
"""
from pathlib import Path
import sys, re, json, hashlib, subprocess
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
HW=ROOT.parent
NG=Path('D:/ms_xsp/s04_crosscheck_20261017/Spice64/bin/ngspice_con.exe')
sys.stdout.reconfigure(encoding='utf-8')
MODEL=(ROOT/'sources/C4_original.cir').read_text().split('.model')[1].split('.options')[0]
MODEL='.model'+MODEL

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def read_raw(p):
    b=p.read_bytes(); off=b.index(b'Binary:\n'); h=b[:off].decode('latin1')
    nv=int(re.search(r'No\. Variables:\s+(\d+)',h)[1]); n=int(re.search(r'No\. Points:\s+(\d+)',h)[1])
    names=re.findall(r'^\s*\d+\s+(\S+)\s+\S+\s*$',h.rsplit('Variables:',1)[1],re.M)
    assert len(names)==nv
    a=np.frombuffer(b,dtype=np.float64,count=nv*n,offset=off+8).reshape(n,nv)
    return dict(zip(names,a.T))

def mean(t,y): return float(np.trapezoid(y,t)/(t[-1]-t[0]))

def build(name,rtop=10000,rinj=47000,amp=4,duty=.5,rl=10000,cl=5e-12,
          full=False,real_bb=False,step=.5,stop=None,temp=27,beta=None,ce=1e-9,
          rfseries=2200,rfshunt=10,cin=1e-9,cb=100e-12,cout=10e-9,rtp3=1e6,
          filter_out=False,lq=40):
    stop=stop or (2e-3 if full else 300e-6)
    if full:
        s=(ROOT/'sources/C4_original.cir').read_text().split('.control')[0]
        s=re.sub(r'^RLOADG .*\n|^CLOADG .*\n','',s,flags=re.M)
        # Existing gain-stage output gets its own DC return; old bench load removed only in this copy.
        s+='\nRTP2DC out 0 1meg\n'
    else:
        s='* Base modulation isolated fixture; ideal RF source only\nVSUP vcc 0 5\nVRF out 0 SIN(0 1 31meg)\n'+MODEL
    if real_bb:
        src=HW/f'LM393_20k_D{round(duty*100)}_A{amp}.cir'
        (ROOT/'sources'/src.name).write_bytes(src.read_bytes())
        bb='\n'.join(src.read_text().split('.options')[0].splitlines()[1:])
        s+='\n'+bb+'\nRBBPORT V1 vm 0.001\n'
    else:
        s+=f'\nVMOD vm 0 PULSE(0.0748175 {0.0748175+amp} 20u 20n 20n {duty*50e-6-20e-9} 50u)\n'
    s+=f'''
* RF attenuation/coupling to base; no uncontrolled floating transistor terminal.
RMRF out mrftap {rfseries}
RMRG mrftap 0 {rfshunt}
CMRF mrftap mb {cin}
* DC-coupled base injection: no duty-dependent coupling-capacitor baseline.
RMT vcc mb {rtop}
RMB mb 0 3300
RMINJ vm mb {rinj}
QM mc mb me 2N3904
RMC vcc mc 1000
RME me 0 470
CME me 0 {ce}
* TP3 is the AC-coupled MODULATOR output, not automatically v3.
CMOUT mc tp3 {cout}
RTP3DC tp3 0 {rtp3}
* Explicit output follower and final AC-coupled connector.
CBUF tp3 ob {cb}
ROBT vcc ob 33000
ROBB ob 0 33000
QOB vcc ob oe 2N3904
ROE oe 0 330
COV3 oe v3 10n
* Measurement fixture, NOT a specified antenna or course load.
RTEST v3 0 {rl}
CTEST v3 0 {cl}
.options method=trap maxord=2 reltol=1e-5 trtol=7 temp={temp} tnom=27
.control
set filetype=binary
set num_threads=1
save v(out) v(vm) v(mb) v(me) v(mc) v(tp3) v(oe) v(ob) v(v3) i(vsup) {"i(v5)" if real_bb else "i(vmod)"}
tran {step}n {stop} {stop-150e-6} {step}n {"uic" if full or real_bb else ""}
write {name}.raw
quit
.endc
.end
'''
    if beta is not None:s=s.replace('Bf=416.4',f'Bf={beta}')
    if filter_out:
        # Finite-Q output preselection candidate; Q is an explicit assumption.
        loss=2*np.pi*31e6*470e-9/lq
        # 5pF nominal fixture capacitance + 51pF intentional tank capacitor.
        s=s.replace('COV3 oe v3 10n',f'''COV3 oe tx_drv 10n
ROISO tx_drv v3 1000
LTX v3 ltx_esr 470n
RLTX ltx_esr 0 {loss}
CTX v3 0 51p''')
    return s

def crossings(t,y):
    idx=np.flatnonzero((y[:-1]<0)&(y[1:]>=0))
    return t[idx]-y[idx]*(t[idx+1]-t[idx])/(y[idx+1]-y[idx])

def harmonic(t,y,f):
    # Short plateau fit; direct irregular-time samples, sufficiently oversampled.
    u=t-t[0]; mat=np.column_stack([np.ones(len(u))]+[fn(2*np.pi*k*f*u) for k in range(1,6) for fn in (np.cos,np.sin)])
    co=np.linalg.lstsq(mat,y,rcond=None)[0]; a=np.hypot(co[1::2],co[2::2])
    return dict(fund_vpp=float(2*a[0]),raw_vpp=float(np.ptp(y)),thd_h2_h5_pct=float(100*np.linalg.norm(a[1:])/a[0]))

def measure(name,d,params):
    t=d['time']; vm=d['v(vm)']; thr=(np.quantile(vm,.05)+np.quantile(vm,.95))/2
    edges=np.flatnonzero(np.diff((vm>thr).astype(int)))+1
    # Only COMPLETE source plateaus: recording-window endpoints are not edges.
    bounds=edges; plateaus=[]
    for a,b in zip(bounds[:-1],bounds[1:]):
        if t[b]-t[a]<3e-6:continue
        # Last 1us on each plateau, keep 0.4us guard before the next edge.
        sel=(t>t[b]-1.4e-6)&(t<t[b]-.4e-6)
        tt=t[sel]; vv=d['v(out)'][sel]; zz=crossings(tt,vv-mean(tt,vv))
        if len(zz)<10:continue
        f=float(1/np.mean(np.diff(zz)))
        zv=crossings(tt,d['v(v3)'][sel]-mean(tt,d['v(v3)'][sel]))
        f_v3=float(1/np.mean(np.diff(zv))) if len(zv)>10 else None
        row=dict(high=bool(vm[(a+b)//2]>thr),time_s=float(np.mean(tt)),vm=mean(tt,vm[sel]),
                 freq_hz=f,v3_frequency_hz=f_v3,ic_est_ma=mean(tt,(5-d['v(mc)'][sel])) ,
                 vce_min=float(np.min(d['v(mc)'][sel]-d['v(me)'][sel])),
                 vcb_min=float(np.min(d['v(mc)'][sel]-d['v(mb)'][sel])),
                 vb_mean=mean(tt,d['v(mb)'][sel]),ve_mean=mean(tt,d['v(me)'][sel]))
        for node in ['out','tp3','v3']:row[node]=harmonic(tt,d[f'v({node})'][sel],f)
        plateaus.append(row)
    if not any(x['high'] for x in plateaus) or not any(not x['high'] for x in plateaus):raise ValueError('Missing plateaus')
    vh=float(np.mean([p['v3']['fund_vpp'] for p in plateaus if p['high']]))
    vl=float(np.mean([p['v3']['fund_vpp'] for p in plateaus if not p['high']]))
    rises=edges[vm[edges]>thr]; bb_freq=float(1/np.mean(np.diff(t[rises]))) if len(rises)>1 else None
    load_p=mean(t,d['v(v3)']**2/params.get('rl',10000))
    row=dict(name=name,settings=params,plateaus=plateaus,v3_high_fund_vpp=vh,v3_low_fund_vpp=vl,
             modulation_index=(vh-vl)/(vh+vl),envelope_step_fund_vpp=vh-vl,bb_frequency_hz=bb_freq,
             rf_chain_supply_ma=-1000*mean(t,d['i(vsup)']),resistive_fixture_power_mw=1000*load_p,
             entire_window_vce_min=float(np.min(d['v(mc)']-d['v(me)'])),
             entire_window_vcb_min=float(np.min(d['v(mc)']-d['v(mb)'])),
             waveform_scope='SIMULATION_ONLY_NO_ANTENNA_NO_WIRELESS_OR_6M_CLAIM',netlist_sha256=sha(ROOT/'netlists'/f'{name}.cir'))
    if params.get('real_bb'):row['lm393_supply_ma']=-1000*mean(t,d['i(v5)'])
    # Time-domain evidence remains available in compact binary NPZ, raw also retained.
    np.savez_compressed(ROOT/'results'/f'{name}_trace.npz',**d)
    (ROOT/'results'/f'{name}.json').write_text(json.dumps(row,indent=2),encoding='utf8')
    print(name, 'm',round(row['modulation_index'],4),'VH/VL',round(vh,4),round(vl,4),
          'Vce',round(row['entire_window_vce_min'],3),'I5_mA',round(row['rf_chain_supply_ma'],3),flush=True)
    return row

def run(name,**params):
    p=ROOT/'netlists'/f'{name}.cir'
    if p.exists() or (ROOT/'results'/f'{name}.json').exists():
        raise FileExistsError('Use a new run name; existing evidence is retained: '+name)
    p.write_text(build(name,**params),encoding='utf8')
    with (ROOT/'results'/f'{name}.log').open('w') as log:
        r=subprocess.run([str(NG),'-b',str(p)],cwd=ROOT/'results',stdout=log,stderr=subprocess.STDOUT,timeout=1200)
    if r.returncode:raise RuntimeError(f'{name}: simulator failed; inspect log')
    return measure(name,read_raw(ROOT/'results'/f'{name}.raw'),params)

if __name__=='__main__':
    mode=sys.argv[1]
    if mode=='screen':
        for rt in [8200,10000,12000]:
            for ri in [47000,100000,220000]:run(f'screen_rt{rt}_ri{ri}',rtop=rt,rinj=ri,rfseries=47000,rfshunt=330,cin=100e-12,cb=1e-9)
    elif mode=='stiff':
        for rt in [10000,15000,18000]:
            for ri in [47000,100000,220000]:run(f'stiff_rt{rt}_ri{ri}',rtop=rt,rinj=ri)
    elif mode=='compensate':
        vb=.8699366597350188
        for ri in [47000,100000,220000]:
            rt=(5-vb)/((5-vb)/15000+(vb-.0748175)*(1/ri-1/100000))
            run(f'comp_ri{ri}',rtop=rt,rinj=ri)
    elif mode=='compensate2':
        vb=.8699366597350188
        for ri in [47000,100000,220000]:
            rt=(5-vb)/((5-vb)/15000+(vb-.0748175)*(1/ri-1/100000))
            run(f'comp2_ri{ri}',rtop=rt,rinj=ri,cout=100e-12,rtp3=1000,cin=100e-12)
    elif mode=='matrix':
        for a in [1,2,3,4]:
            for duty in [.1,.3,.5]:run(f'matrix_a{a}_d{round(100*duty)}',rtop=15000,rinj=47000,amp=a,duty=duty,cout=100e-12,rtp3=1000)
    elif mode=='matrix2':
        for a in [1,2,3,4]:
            for duty in [.1,.3,.5]:run(f'matrix2_a{a}_d{round(100*duty)}',rtop=15000,rinj=47000,amp=a,duty=duty,cout=100e-12,rtp3=1000,cin=100e-12)
    elif mode=='sensitivity':
        base=dict(rtop=15000,rinj=47000,cout=100e-12,rtp3=1000,cin=100e-12,filter_out=True)
        cases=[('nom',{}),('load2k10p',dict(rl=2000,cl=10e-12)),
               ('load1m2p',dict(rl=1e6,cl=2e-12)),('q20',dict(lq=20)),('q80',dict(lq=80)),
               ('temp0',dict(temp=0)),('temp50',dict(temp=50)),('beta100',dict(beta=100))]
        for tag,kw in cases:run('sens_'+tag,**(base|kw))
    elif mode=='remeasure':
        old=ROOT/'results/analysis_v1';old.mkdir(exist_ok=True)
        for p in sorted((ROOT/'results').glob('*.json')):
            d=json.loads(p.read_text())
            if 'settings' not in d:continue
            if not (old/p.name).exists():(old/p.name).write_bytes(p.read_bytes())
            measure(d['name'],read_raw(ROOT/'results'/f'{d["name"]}.raw'),d['settings'])
    elif mode=='case':
        run(sys.argv[2],**json.loads(sys.argv[3]))

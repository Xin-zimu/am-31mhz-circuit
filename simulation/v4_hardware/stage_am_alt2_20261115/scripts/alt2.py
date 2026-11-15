"""AM-ALT.2 independent fixtures. Never writes predecessor directories."""
import json,re,sys,subprocess
from pathlib import Path
import numpy as np
import core
ROOT=core.ROOT
HW=ROOT.parent

def replace(s,key,value):
    s,n=re.subn(r'^'+re.escape(key)+r' .*$',value,s,flags=re.M)
    assert n==1,(key,n)
    return s

def bbsource(amp,duty,pot=None,total=20000,pullup=2200,buffer=False):
    src=HW/f'LM393_20k_D{round(duty*100)}_A{amp}.cir'
    dst=ROOT/'sources'/src.name
    if not dst.exists():dst.write_bytes(src.read_bytes())
    s='\n'.join(src.read_text().split('.options')[0].splitlines()[1:])
    if pot is None:pot=float(re.search(r'^RVAT PWM_RAW V1 (\S+)',s,re.M)[1])*total/20000
    s=replace(s,'RVAT',f'RVAT PWM_RAW V1 {pot}')
    s=replace(s,'RVAB',f'RVAB V1 0 {total-pot}')
    s=replace(s,'RPU2',f'RPU2 V5 PWM_RAW {pullup}')
    if buffer:
        s+='\n.include ../sources/OPA197_TI_original.lib\nXBB V1 vm V5 0 vm OPAx197\n'
    else:s+='\nRBBPORT V1 vm 0.001\n'
    return s

def build(name,amp=4,duty=.5,pot=None,total=20000,pullup=2200,buffer=False,
          rinj=47000,rtop=15000,bb_only=False,full=False,step=.5,
          split=0,cap=0,cmout=100e-12,cb=100e-12,ce=1e-9,rfamp=1.83):
    bb=bbsource(amp,duty,pot,total,pullup,buffer)
    if bb_only:
        s='* ALT2 baseband and DC transistor load; no RF or wireless claim\n'
        s+=core.MODEL+'\nVSUP vcc 0 5\n'+bb
        s+=f'\nRMT vcc mb {rtop}\nRMB mb 0 3300\nRMINJ vm mb {rinj}\nQM mc mb me 2N3904\nRMC vcc mc 1000\nRME me 0 470\nCME me 0 {ce}\n'
        control=f'tran 20n 1.5m 1.2m 20n uic'
        saves='v(v1) v(vm) v(pwm_raw) v(mb) v(mc) v(me) i(v5) i(vsup)'
    else:
        s=core.build(name,amp=amp,duty=duty,rtop=rtop,rinj=rinj,
            cin=100e-12,cout=cmout,rtp3=1000,cb=cb,ce=ce,
            full=full,real_bb=False,filter_out=True,step=step).split('.control')[0]
        s=re.sub(r'^VMOD .*\n','',s,flags=re.M)
        if not full:s=replace(s,'VRF',f'VRF out 0 SIN(0 {rfamp} 31meg)')
        s+='\n'+bb
        stop=2e-3 if full else 400e-6
        control=f'tran {step}n {stop} {stop-150e-6} {step}n uic'
        saves='v(v1) v(vm) v(pwm_raw) v(out) v(mb) v(mc) v(me) v(tp3) v(ob) v(oe) v(v3) i(v5) i(vsup)'
    if split:
        assert 0<split<rinj
        s=replace(s,'RMINJ',f'RPRE vm mod_env {split}\nCENV mod_env 0 {cap}\nRMINJ mod_env mb {rinj-split}')
        saves+=' v(mod_env)'
    method='gear' if buffer and bb_only else 'trap'
    s+=f'\n.options method={method} maxord=2 reltol=1e-5 trtol=7 temp=27 tnom=27\n.control\nset filetype=binary\nset num_threads=1\nsave {saves}\n{control}\nwrite {name}.raw\nquit\n.endc\n.end\n'
    return s

def edges(t,y):
    lo,hi=np.quantile(y,[.05,.95]); threshold=(lo+hi)/2
    j=np.flatnonzero(np.diff((y>threshold).astype(int)))
    tx=t[j]+(threshold-y[j])*(t[j+1]-t[j])/(y[j+1]-y[j])
    up=y[j+1]>y[j]
    return tx,up

def bbmetrics(d,node='v(vm)'):
    t=d['time'];y=d[node];tx,up=edges(t,y)
    ps=[]
    for a,b,h in zip(tx[:-1],tx[1:],up[:-1]):
        z=(t>b-1.4e-6)&(t<b-.4e-6)
        if z.sum()>2:ps.append({'high':bool(h),'mean':core.mean(t[z],y[z])})
    hi=float(np.mean([p['mean'] for p in ps if p['high']]))
    lo=float(np.mean([p['mean'] for p in ps if not p['high']]))
    rises=tx[up];period=float(np.mean(np.diff(rises)))
    highs=[b-a for a,b,h in zip(tx[:-1],tx[1:],up[:-1]) if h]
    return {'high':hi,'low':lo,'vpp':hi-lo,'freq_hz':1/period,'duty_pct':100*np.mean(highs)/period}

def metrics(name,d,params):
    assert all(np.isfinite(v).all() for v in d.values())
    assert np.all(np.diff(d['time'])>0)
    m={'name':name,'settings':params,'vm':bbmetrics(d),'v1':bbmetrics(d,'v(v1)'),
       'i_bb_ma':-1000*core.mean(d['time'],d['i(v5)']),
       'i_rf_ma':-1000*core.mean(d['time'],d['i(vsup)']),
       'netlist_sha256':core.sha(ROOT/'netlists'/f'{name}.cir')}
    if not params.get('bb_only'):
        c=core.measure(name,d,params|{'real_bb':True})
        m['rf']=c
    (ROOT/'results'/f'{name}.json').write_text(json.dumps(m,indent=2),encoding='utf8')
    print(name, 'Vm',round(m['vm']['vpp'],6),'D',round(m['vm']['duty_pct'],4),'Ibb',round(m['i_bb_ma'],4),flush=True)
    return m

def run(name,**kw):
    net=ROOT/'netlists'/f'{name}.cir'
    if net.exists():raise FileExistsError(name)
    circuit=build(name,**kw)
    if kw.get('buffer'):
        network,control=circuit.split('.control',1)
        (ROOT/'netlists'/f'{name}_network.cir').write_text(network+'\n.end\n',encoding='utf8')
        circuit=f'* PSpice compatibility wrapper for preserved TI model\n.control\nset ngbehavior=ps\nsource ../netlists/{name}_network.cir\n'+control
    net.write_text(circuit,encoding='utf8')
    with (ROOT/'results'/f'{name}.log').open('w') as log:
        r=subprocess.run([str(core.NG),'-b',str(net)],cwd=ROOT/'results',stdout=log,stderr=subprocess.STDOUT,timeout=1800)
    if r.returncode:raise RuntimeError('Simulator failed; inspect '+name+'.log')
    data=core.read_raw(ROOT/'results'/f'{name}.raw')
    expected=1.5e-3 if kw.get('bb_only') else (2e-3 if kw.get('full') else 400e-6)
    if data['time'][-1]<expected-1e-12:raise RuntimeError('Incomplete transient: '+name)
    return metrics(name,data,kw)

def calibrate(amp,tag,**kw):
    # A bounded secant calibration, not a course tolerance; each trial retained.
    total=kw.get('total',20000);x0=total*(1-amp/4.4);x1=max(1,x0-total*.03)
    trials=[]
    for n in range(7):
        x=x0 if n==0 else x1
        m=run(f'cal_{tag}_a{amp}_i{n}',amp=amp,duty=.5,pot=x,bb_only=True,**kw)
        e=m['vm']['vpp']-amp;trials.append((x,e))
        if abs(e)<.0001:break
        if n>=1:
            xa,ea=trials[-2];xn=x-e*(x-xa)/(e-ea)
            x1=float(np.clip(xn,1,total-1))
    else:raise RuntimeError('Calibration did not converge')
    return {'pot_top_ohm':x,'pot_bottom_ohm':total-x,'result':m['name'],'actual_vpp':m['vm']['vpp'],'settings':kw}

if __name__=='__main__':
    mode=sys.argv[1]
    if mode=='compare':
        for tag,kw in [('original',{}),('stiffer',{'total':10000,'pullup':1500}),('rinj100k',{'rinj':100000,'rtop':15488}),('opa',{'buffer':True})]:
            run('bb_'+tag,bb_only=True,**kw)
    elif mode=='calibrate':
        tag=sys.argv[2];kw=json.loads(sys.argv[3]);result={}
        for a in [1,2,3,4]:result[str(a)]=calibrate(a,tag,**kw)
        (ROOT/'results'/f'calibration_{tag}.json').write_text(json.dumps(result,indent=2))
    elif mode=='run':run(sys.argv[2],**json.loads(sys.argv[3]))

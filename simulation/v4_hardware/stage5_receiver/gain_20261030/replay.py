"""Split simulation with a declared interface approximation.

Actual RF/BAT85 feeds the existing passive BB coupling, bias and reference.
An ideal 1e6 open-loop amplifier supplies feedback DC/current; 6.4 pF at
the input represents the TI common-mode capacitance. It has NO rail limit.
The resulting loaded detector waveform is replayed into the UNMODIFIED TI
macro-model and existing BB circuit. Cross-check against integrated results
is required; this split method alone is not an integrated/cold-start pass.
"""
from run_gain import *

def interface(name,**kw):
    c=cfg(**kw)
    rc=dict(c);rc.update(start=100,stop=200,load=1e15)
    rfraw,rfr=rf(name+'_RFopen',**rc)
    mean=rfr['metrics']['nodes']['out']['dc']
    b=bb(c).replace('XOPA bbin neg vcc 0 bbo OPAx197','EIDEAL bbo 0 bbin neg 1meg\nCINPUT bbin 0 6.4p')
    net=d.circuit(c,d.source(c))+d.old.old.detector(dict(dc_return='direct',rd=4700,cd=100,rf=4700,cf=100,load=1e15))+d.old.old.models()+b
    net+=f'.ic v(out)={mean:.16g} v(bbin)=3 v(ref)=3\n'
    raw,r=wrapper(name,net,f"tran {c['step']}n {c['stop']}u {c['start']}u {c['step']}n",c,d.SAVES+' v(bbin) v(ref) v(bbo) v(final)')
    r['metrics']=metrics(raw,c);r['rf_metrics']=d.measure(raw,c)
    r['qualification']='RF and BAT85 actual models; ideal op amp has no swing or bandwidth limitation; interface approximation'
    d.save(r)
    print(json.dumps(dict(name=name,ideal_vpp=r['metrics']['final']['vpp'],det_peak20=r['metrics']['out']['peak20'])),flush=True)
    return raw,r

def replay(name,interface_name,**kw):
    ir=json.loads((HERE/'results'/(interface_name+'.json')).read_text())
    idata=d.readraw(Path(ir['raw_path']))
    c=cfg(**{k:v for k,v in ir['config'].items() if k not in ['step']});c.update(step=5);c.update(kw)
    # One settled 50 us period, sampled at 5 ns; DC-correct initialization.
    phase=np.arange(10000)*5e-9
    y=np.interp(ir['config']['stop']*1e-6-50e-6+phase,idata['time'],idata['v(out)'])
    mean=float(y.mean())
    tt=np.arange(round(c['stop']*1e-6/5e-9)+1)*5e-9
    yy=y[np.arange(len(tt))%len(y)]
    points=[f'0 {mean:.12g}',f'1p {yy[0]:.12g}']+[f'{t:.12g} {v:.12g}' for t,v in zip(tt[1:],yy[1:])]
    stim='VREPLAY out 0 PWL(\n'+''.join('+ '+s+'\n' for s in points)+')\n'
    net='* Split RF-detector waveform replay; actual TI OPA197\nVSUP vcc 0 9\n'+stim+bb(c)
    raw,r=wrapper(name,net,f"tran {c['step']}n {c['stop']}u {c['start']}u {c['step']}n",c,'v(out) v(bbin) v(ref) v(bbo) v(final) i(vsup)')
    r['interface']={'name':interface_name,'sha256':sha(HERE/'results'/(interface_name+'.json')),'profile_sample_ns':5,'repeat_us':50,'profile_dc':mean,'qualification':'split simulation; detector loading uses ideal feedback and 6.4pF approximation'}
    r['metrics']=metrics(raw,c);d.save(r)
    print(json.dumps({'name':name,'final':r['metrics']['final']}),flush=True)
    return raw,r

def case(name,**kw):
    interface('I_'+name,**kw)
    return replay('T_'+name,'I_'+name)

if __name__=='__main__':
    case('sq10',wave='square',duty=.1)

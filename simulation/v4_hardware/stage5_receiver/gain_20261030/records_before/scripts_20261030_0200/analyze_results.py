"""Read completed immutable evidence and derive auditable comparison tables."""
from run_gain import *

def result(n):return json.loads((HERE/'results'/(n+'.json')).read_text())

def main():
    final=[]
    for p in sorted((HERE/'results').glob('*.json')):
        r=json.loads(p.read_text())
        if 'metrics' not in r or 'final' not in r['metrics'] or not r.get('name','').startswith('F'):continue
        c=r['config'];m=r['metrics']['final'];rf=r['rf_metrics']
        base='F22_sine_clean_gear'+('_h025' if c.get('step')==.25 else '') if c['wave']=='sine' else f"F22_sq{c['duty']*100:g}_sixcycles"
        if c['wave']=='square' and c.get('method')=='gear':base=f"F22_sq{c['duty']*100:g}_clean_gear"
        delta=None
        if c['blockers'] and (HERE/'results'/(base+'.json')).exists():delta=float(20*np.log10(m['peak20']/result(base)['metrics']['final']['peak20']))
        row=dict(name=r['name'],gain=1+c['feedback']/10000,ac_mV=c['ac']*1000,m=c['m'],wave=c['wave'],input_duty=100*c['duty'],blockers=c['blockers'],method=c.get('method','trap'),step_ns=c['step'],start_us=c['start'],stop_us=c['stop'],delta20_db=delta,normalization_base=base if c['blockers'] else None,**m)
        row.update(det_peak20=r['metrics']['out']['peak20'],bb_gain20=m['peak20']/r['metrics']['out']['peak20'],ref_dc=r['metrics']['ref']['dc'],input_common_mode_min=r['metrics']['bbin']['low'],input_common_mode_max=r['metrics']['bbin']['high'],q1=rf['q1'],q2=rf['q2'],supply_power_w=rf['supply_power_w'],thd_2to10=rf['nodes']['final']['thd_2to10'])
        final.append(row)
    comps=[]
    for p in sorted((HERE/'results').glob('C_*_physical.json')):
        n=p.stem[:-9];r=result(n);raw=d.readraw(Path(r['raw_path']));f=raw['frequency'].real;g=abs(raw['v(rf)']);cut=max(g)/np.sqrt(2);indices=np.where(np.diff(g>=cut))[0]
        edges=[float(f[i]+(cut-g[i])/(g[i+1]-g[i])*(f[i+1]-f[i])) for i in indices]
        comps.append(dict(name=n,**r['metrics'],**json.loads(p.read_text()),edges3_hz=edges,bw_interpolated_hz=edges[-1]-edges[0] if len(edges)>=2 else None))
    step=[]
    for n in ['BB22_smallstep','BB22_smallstep_C1000']:
        r=result(n);raw=d.readraw(Path(r['raw_path']));t=350e-6+np.arange(5000)*10e-9;y=np.interp(t,raw['time'],raw['v(final)'])
        hi=np.median(y[1000:2000]);lo=np.median(y[3500:4500])
        step.append(dict(name=n,local_plateau_span=float(hi-lo),positive_overshoot_pct=float(100*(max(y)-hi)/(hi-lo)),negative_overshoot_pct=float(100*(lo-min(y))/(hi-lo)),note='edge-response diagnostic; AC coupling mean is still settling, not a steady-window qualification'))
    data=dict(integrated=final,components=comps,local_step=step)
    (HERE/'summary.json').write_text(json.dumps(data,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps(dict(final_count=len(final),comparison=[{k:r[k] for k in ['name','vpp','duty_pct','delta20_db','rail_fraction']} for r in final]),indent=2))

if __name__=='__main__':main()

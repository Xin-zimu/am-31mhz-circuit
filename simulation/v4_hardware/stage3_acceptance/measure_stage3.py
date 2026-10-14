"""Measure native Multisim ASCII raw waveforms without loading text twice."""
from pathlib import Path
import argparse, json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent

def read_raw(path):
    with path.open(encoding='ascii') as f:
        names=[]; in_variables=False
        for line in f:
            if line.strip()=='Variables:': in_variables=True; continue
            if line.strip()=='Values:': break
            if in_variables and line.strip(): names.append(line.split()[-1])
        flat=np.fromiter((float(line.split()[-1]) for line in f if line.strip()),dtype=float)
    a=flat.reshape(-1,len(names))
    assert np.all(np.isfinite(a)) and np.all(np.diff(a[:,0])>=0)
    return names,a

def crossings(t,y,level):
    up=np.flatnonzero((y[:-1]<level)&(y[1:]>=level))
    dn=np.flatnonzero((y[:-1]>=level)&(y[1:]<level))
    def cross(i): return t[i]+(level-y[i])*(t[i+1]-t[i])/(y[i+1]-y[i])
    return cross(up),cross(dn)

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('raw',type=Path)
    parser.add_argument('--solver',default='Multisim XSPICE command interface; full exported circuit')
    parser.add_argument('--initial',default='UIC with three precharged capacitors; not cold startup')
    args=parser.parse_args()
    names,a=read_raw(args.raw); t=a[:,0]; label=args.raw.stem
    last=t>=max(t[-1]-.0003,0)
    uniform=np.arange(t[last][0],t[-1],2e-9)
    signals={n:np.interp(uniform,t,a[:,i]) for i,n in enumerate(names) if i}
    inp=signals['V(v1)']; threshold=float((np.percentile(inp,98)+np.percentile(inp,2))/2)
    up,dn=crossings(t,a[:,names.index('V(v1)')],threshold)
    cycles=[]
    for begin,end in zip(up[:-1],up[1:]):
        if begin<10e-6: continue
        grid=np.arange(begin,end,2e-9)
        if len(grid)<10: continue
        row={'start_s':float(begin),'end_s':float(end),'period_s':float(end-begin),'frequency_hz':float(1/(end-begin))}
        falls=dn[(dn>begin)&(dn<end)]
        row['input_falling_crossings']=len(falls)
        row['input_duty_percent']=float(100*(falls[0]-begin)/(end-begin)) if len(falls)==1 else None
        for n in ['V(v1)','V(bb_in)','V(bbo)','V(v2)']:
            y=np.interp(grid,t,a[:,names.index(n)])
            left=np.searchsorted(t,begin,side='left')
            right=np.searchsorted(t,end,side='right')
            raw=a[left:right,names.index(n)]
            lo,hi=np.percentile(y,[2,98])
            row[n]={'mean_v':float(np.trapezoid(y,grid)/(grid[-1]-grid[0])),
                    'raw_min_v':float(raw.min()),'raw_max_v':float(raw.max()),
                    'raw_vpp':float(np.ptp(raw)),'robust_vpp':float(hi-lo)}
        row['robust_gain']=row['V(v2)']['robust_vpp']/row['V(v1)']['robust_vpp']
        cycles.append(row)
    assert len(cycles)>=5
    tail=cycles[-5:]; amp=np.mean([r['V(v2)']['robust_vpp'] for r in tail])
    mean_span=np.ptp([r['V(v2)']['mean_v'] for r in tail])
    amp_span=np.ptp([r['V(v2)']['robust_vpp'] for r in tail])
    periods=np.array([r['period_s'] for r in tail])
    output=signals['V(v2)']; output_level=(np.percentile(output,98)+np.percentile(output,2))/2
    ou,od=crossings(uniform,output,output_level)
    output_cycles=[]
    for b,e in zip(ou[:-1],ou[1:]):
        fall=od[(od>b)&(od<e)]
        output_cycles.append({'frequency_hz':float(1/(e-b)), 'falling_crossings':len(fall),
                              'duty_percent':float(100*(fall[0]-b)/(e-b)) if len(fall)==1 else None})
    result={'run':label,'solver':args.solver,
            'points':len(a),'t_end_s':float(t[-1]),'recorded_nodes':names,
            'initial_condition':args.initial,
            'cycles_measured':len(cycles),'last_five_cycles':tail,
            'output_cycles_in_last_300us':output_cycles,
            'repeatability_screen':{'official_acceptance':False,'threshold_fraction':.001,
                 'V2_mean_span_V':float(mean_span),'V2_robust_vpp_span_V':float(amp_span),
                 'period_relative_span':float(np.ptp(periods)/np.mean(periods)),
                 'passes':bool(mean_span/amp<.001 and amp_span/amp<.001 and np.ptp(periods)/np.mean(periods)<.001)}}
    (HERE/f'{label}_metrics.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    (HERE/f'{label}_cycles.json').write_text(json.dumps(cycles,indent=2),encoding='utf-8')
    np.savez_compressed(HERE/f'{label}.npz',data=a,names=names)
    fig,ax=plt.subplots(2,1,figsize=(10,6),layout='constrained')
    times=[r['start_s']*1000 for r in cycles]
    ax[0].plot(times,[r['V(v2)']['mean_v'] for r in cycles],'.-',label='V2 cycle mean')
    ax[0].set(xlabel='Time (ms)',ylabel='Mean (V)',title=f'{label}: full-model cycle statistics')
    ax[1].plot(times,[r['V(v2)']['robust_vpp'] for r in cycles],'.-',label='V2 P98-P2')
    ax[1].set(xlabel='Time (ms)',ylabel='Amplitude (Vpp)')
    for axis in ax: axis.grid(alpha=.25);axis.legend()
    fig.savefig(HERE/f'{label}_cycles.png',dpi=150)
    print(json.dumps({k:v for k,v in result.items() if k not in ['last_five_cycles','output_cycles_in_last_300us']},indent=2))
    print('LAST_CYCLE',json.dumps(tail[-1],indent=2))

if __name__=='__main__':main()

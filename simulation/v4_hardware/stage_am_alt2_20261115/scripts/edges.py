"""Whole-edge diagnostics from raw RF cycle extrema; no smoothing filter."""
import json,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from alt2 import ROOT,edges,core

def envelope(d):
    t=d['time'];v=d['v(v3)'];rf=d['v(out)']
    z=core.crossings(t,rf)
    bins=np.searchsorted(t,z)
    tc=[];hi=[];lo=[]
    for a,b in zip(bins[:-1],bins[1:]):
        if b>a:
            tc.append((t[a]+t[b-1])/2);hi.append(v[a:b].max());lo.append(v[a:b].min())
    tc=np.array(tc);hi=np.array(hi);lo=np.array(lo)
    return tc,(hi-lo)/2,(hi+lo)/2,hi,lo

def assess(name,plot=True):
    d=core.read_raw(ROOT/'results'/f'{name}.raw')
    t=d['time'];tx,up=edges(t,d['v(vm)']);tc,env,center,hi,lo=envelope(d)
    records=[]
    for i in range(1,len(tx)-1):
        a=tx[i];b=tx[i+1];before=tx[i-1]
        old=env[(tc>a-1.4e-6)&(tc<a-.4e-6)].mean()
        new=env[(tc>b-1.4e-6)&(tc<b-.4e-6)].mean()
        z=(tc>a-.3e-6)&(tc<min(a+4e-6,b-.4e-6))
        tt=tc[z]-a;progress=(env[z]-old)/(new-old)
        def cross(level):
            ix=np.flatnonzero((progress[:-1]<level)&(progress[1:]>=level))
            if not len(ix):return None
            j=ix[0];return float(tt[j]+(level-progress[j])*(tt[j+1]-tt[j])/(progress[j+1]-progress[j]))
        t10=cross(.1);t90=cross(.9)
        post=tt>=0;bad=np.flatnonzero(post&(np.abs(progress-1)>.02))
        settle=float(tt[bad[-1]]+1/31e6) if len(bad) and bad[-1]<len(tt)-1 else (0. if not len(bad) else None)
        # Plateau tilt over middle-to-late regions, normalized to AM step.
        early=env[(tc>a+.5*(b-a))&(tc<a+.65*(b-a))].mean()
        records.append({'rising':bool(up[i]),'time_s':float(a),
            'overshoot_step_pct':float(max(0,progress.max()-1)*100),
            'reverse_excursion_step_pct':float(max(0,-progress.min())*100),
            'transition_10_90_ns':None if t10 is None or t90 is None else (t90-t10)*1e9,
            'settle_2pct_step_us':None if settle is None else settle*1e6,
            'plateau_tilt_step_pct':float((new-early)/abs(new-old)*100),
            'max_center_mv':float(np.max(np.abs(center[z]))*1000)})
    r={'name':name,'method':'raw carrier-cycle extrema, half peak-to-peak envelope; 2% settling is diagnostic only','edges':records,
       'max_overshoot_step_pct':max(x['overshoot_step_pct'] for x in records),
       'max_reverse_step_pct':max(x['reverse_excursion_step_pct'] for x in records),
       'max_abs_tilt_step_pct':max(abs(x['plateau_tilt_step_pct']) for x in records)}
    (ROOT/'results'/f'{name}_edges.json').write_text(json.dumps(r,indent=2))
    if plot:
        fig,ax=plt.subplots(3,1,figsize=(10,8),constrained_layout=True)
        start=tx[1]-1e-6;sel=(t>=start)&(t<=start+55e-6)
        ax[0].plot((t[sel]-start)*1e6,d['v(vm)'][sel],label='v1 / modulation input')
        if 'v(mod_env)' in d:ax[0].plot((t[sel]-start)*1e6,d['v(mod_env)'][sel],label='injection RC node')
        ax[0].legend();ax[0].set_ylabel('Baseband (V)')
        z=(tc>=start)&(tc<=start+55e-6)
        ax[1].plot((tc[z]-start)*1e6,hi[z]);ax[1].plot((tc[z]-start)*1e6,lo[z]);ax[1].set_ylabel('v3 raw cycle extrema (V)')
        for a in tx[1:3]:
            z=(tc>a-.4e-6)&(tc<a+4e-6)
            ax[2].plot((tc[z]-a)*1e6,env[z],label=f'edge at {a*1e6:.2f} us')
        ax[2].legend();ax[2].set_ylabel('Half peak-to-peak envelope (V)')
        for a in ax:a.grid(alpha=.25);a.set_xlabel('Time (us)')
        fig.suptitle(name+' | simulation RC fixture; not antenna or 6 m verification')
        fig.savefig(ROOT/'figures'/f'{name}.png',dpi=150);plt.close(fig)
    print(name,'overshoot step %',r['max_overshoot_step_pct'],'reverse %',r['max_reverse_step_pct'],flush=True)
    return r

if __name__=='__main__':
    for name in sys.argv[1:]:assess(name)

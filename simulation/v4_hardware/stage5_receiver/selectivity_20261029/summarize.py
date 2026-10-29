"""Rebuild compact tables/plots from result records and original arrays."""
from pathlib import Path
import json,csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from run_selectivity import HERE,WORK,readraw,sha

def main():
    rows=[json.loads(p.read_text()) for p in sorted((HERE/'results').glob('*.json'))]
    by={r['name']:r for r in rows}; get=lambda n:by[n]['metrics']
    def raw(n):return readraw(Path(by[n]['raw_path']))
    brief={}
    for name in ['R1','A','B']:
        brief[name]={k:get(name+'_'+k) for k in ['final_ac','noise','clean','square10']}
    for r in rows:
        m=r.get('metrics',{});c=r.get('config',{})
        if c.get('blocker_a',0)>0 and 'bb_fundamental_peak' in m:
            ref=get(('R1' if c['kind']=='R1' else c['kind'])+'_clean')['bb_fundamental_peak']
            m['useful_amplitude_change_db']=float(20*np.log10(m['bb_fundamental_peak']/ref))
    summary=dict(count=len(rows),analyses={k:sum(k in r.get('metrics',{}) for r in rows)
        for k in ['g31','en31','bb_fundamental_peak','integrated']},candidates=brief,
        results={r['name']:r['metrics'] for r in rows},
        boundaries=dict(wireless_sensitivity_qualified=False,bat85s_qualified=False,
          nearby_blocker_qualified=False,full_receiver_cold_start_qualified=False))
    (HERE/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    fields=['name']+sorted(set(k for r in rows for k in r['metrics']))
    with (HERE/'measurements.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        w.writerows(dict(name=r['name'],**r['metrics']) for r in rows)
    # RF scientific comparison.
    fig,axs=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    colors={'R1':'#9b4545','A':'#cf8c23','B':'#2476a1'}
    for name in colors:
        d=raw(name+'_final_ac');f=d['frequency'].real
        axs[0,0].semilogx(f/1e6,20*np.log10(abs(d['v(rf)'])),label=name,color=colors[name])
        axs[0,1].plot(f/1e6,20*np.log10(abs(d['v(rf)'])/get(name+'_final_ac')['g31']),label=name,color=colors[name])
        rr=sorted([r for r in rows if r['config']['kind']==('R1' if name=='R1' else name)
            and r['config'].get('blocker_f')==1.6e6 and r['config'].get('blocker_a',0)>0
            and 'useful_amplitude_change_db' in r['metrics']],key=lambda r:r['config']['blocker_a'])
        axs[1,0].semilogx([r['config']['blocker_a']*1e3 for r in rr],
            [r['metrics']['useful_amplitude_change_db'] for r in rr],'o-',label=name,color=colors[name])
    axs[0,0].set(xlabel='Frequency (MHz)',ylabel='RF voltage gain (dB)',xlim=(.1,300),ylim=(-80,60),title='Same 50 ohm source / AC test load')
    axs[0,0].axvline(31,color='gray',ls=':')
    axs[0,1].set(xlabel='Frequency (MHz)',ylabel='Relative gain to 31 MHz (dB)',xlim=(25,37),ylim=(-12,3),title='B remains a broad preselector')
    axs[0,1].axvspan(30.8,31.2,color='#dddddd',alpha=.5)
    axs[1,0].set(xlabel='1.6 MHz blocker source peak (mV)',ylabel='Useful 20 kHz amplitude change (dB)',title='31 MHz desired: 10 mV peak, m=0.5')
    for f,mark in [(29e6,'o'),(33e6,'s')]:
        rr=sorted([r for r in rows if r['name'].startswith(('B_blk_','B_near_')) and r['config']['blocker_f']==f],key=lambda r:r['config']['blocker_a'])
        axs[1,1].semilogx([r['config']['blocker_a']*1e3 for r in rr],[r['metrics']['useful_amplitude_change_db'] for r in rr],mark+'-',label=f'{f/1e6:g} MHz')
    axs[1,1].set(xlabel='Nearby blocker source peak (mV)',ylabel='Useful 20 kHz amplitude change (dB)',title='B: 1 dB boundary bracket is 3-6 mV')
    for ax in axs[1,:]:ax.axhline(-1,color='gray',ls=':',label='-1 dB engineering marker')
    for ax in axs.flat:ax.grid(alpha=.25);ax.legend(fontsize=8)
    fig.savefig(HERE/'selectivity_blockers.png',dpi=170);plt.close(fig)
    if 'B_output_square50' in by:
        fig,axs=plt.subplots(2,2,figsize=(12,7),layout='constrained')
        for ax,tag in zip(axs.flat,['sine','square10','square30','square50']):
            d=raw('B_output_'+tag);t=d['time'];u=np.linspace(300e-6,400e-6,10001)
            ax.plot((u-300e-6)*1e6,np.interp(u,t,d['v(final)']),color='#2476a1')
            ax.set(title=tag+' / OPA197 / fixed gain 11.2',xlabel='Time in saved window (us)',ylabel='Output (V)',ylim=(0,9));ax.grid(alpha=.25)
        fig.suptitle('Integrated RF + BAT85 + OPA197, explicitly prebiased capacitors')
        fig.savefig(HERE/'baseband_outputs.png',dpi=170);plt.close(fig)
    if 'BB_cold_400ms' in by:
        d=raw('BB_cold_400ms');t=d['time'];v=d['v(final)']
        edges=np.arange(0,.400001,.001);centers=(edges[:-1]+edges[1:])/2
        lows=[];highs=[];means=[]
        for a,b in zip(edges[:-1],edges[1:]):
            vals=v[(t>=a)&(t<b)];lows.append(float(min(vals)));highs.append(float(max(vals)));means.append(float(np.mean(vals)))
        fig,ax=plt.subplots(figsize=(9,4),layout='constrained')
        ax.fill_between(centers*1e3,lows,highs,alpha=.3,label='Output min-max per 1 ms')
        ax.plot(t[::200]*1e3,d['v(ref)'][::200],label='Passive reference')
        ax.set(xlabel='Time (ms)',ylabel='Voltage (V)',title='Baseband-only power-on test; ideal detector equivalent, not RF startup');ax.grid(alpha=.25);ax.legend()
        fig.savefig(HERE/'baseband_startup.png',dpi=170);plt.close(fig)
        (HERE/'startup_windows.json').write_text(json.dumps(dict(time_ms=(centers*1e3).tolist(),low=lows,high=highs,mean=means),indent=2))
    print(json.dumps(dict(count=summary['count'],analyses=summary['analyses'])))

if __name__=='__main__':main()

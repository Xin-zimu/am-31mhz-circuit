from system_simulation import *
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif']=['Microsoft YaHei','DejaVu Sans']
plt.rcParams['axes.unicode_minus']=False

def job(case):
    p,d,r=sim(*case)
    if case in [(22000,.5,4),(22000,.1,4),(22000,.5,1),(21000,.5,4)]:
        t=d['time']; mask=(t>=.00485)&(t<=.00499)
        fig,ax=plt.subplots(3,1,figsize=(11,7),constrained_layout=True)
        ax[0].plot((t[mask]-.0048)*1e6,d['v(v1)'][mask],lw=1,label='V1 发射方波')
        ax[0].plot((t[mask]-.0048)*1e6,d['v(v2)'][mask],lw=1,label='V2 检波恢复')
        ax[0].legend(loc='upper right');ax[0].set_ylabel('V')
        # Min/max envelope bins are computed from the actual SPICE RF samples.
        ids=np.arange(0,len(t)-80,80)
        tx=np.array([np.min(d['v(tp3)'][i:i+80]) for i in ids]); th=np.array([np.max(d['v(tp3)'][i:i+80]) for i in ids])
        ax[1].fill_between((t[ids]-.0048)*1e6,tx,th,color='#c86f2c',alpha=.7,label='TP3 AM 波形包络')
        ax[1].set_xlim(50,190);ax[1].legend(loc='upper right');ax[1].set_ylabel('V')
        ax[2].plot((t[mask]-.0048)*1e6,d['v(tp6)'][mask],color='#138c78',lw=.6,label='TP6 二极管检波')
        ax[2].legend(loc='upper right');ax[2].set_ylabel('V');ax[2].set_xlabel('时间（µs，原点为4.8ms）')
        for a in ax:a.grid(alpha=.2)
        fig.suptitle(f'31 MHz 调幅功能仿真 | {case[0]/1000:g} kHz · {case[1]*100:g}% · {case[2]} Vpp\n理想AM/信道/RF增益 + 近似肖特基二极管；LTspice 数值验证',fontsize=13)
        fig.savefig(p.with_suffix('.png'),dpi=160);plt.close(fig)
        # Baseband CSV only; RF columns omitted to avoid aliasing after decimation.
        indices=np.arange(0,len(t),10)
        np.savetxt(p.with_suffix('.csv'),np.column_stack([t[indices],d['v(v1)'][indices],d['v(v2)'][indices],d['v(tp6)'][indices]]),delimiter=',',header='time_s,V1_V,V2_V,DET_ENV_V',comments='')
    return r

if __name__=='__main__':
    cases=[(f,d,a) for f in [21000,22000] for d in [.1,.2,.3,.4,.5] for a in [1,4]]+[(22000,.5,2),(22000,.5,3)]
    results=[]
    # Plotting is serialized below by using one worker; simulation is fast with a 2ns limit.
    for c in cases:results.append(job(c))
    (DEST/'system_results.json').write_text(json.dumps(results,indent=2,ensure_ascii=False),encoding='utf-8')
    rows=[]
    for r in results:
        rows.append({'frequency_set_Hz':r['frequency_set_hz'],'duty_set_pct':100*r['duty_set'],'V1_set_Vpp':r['v1_set_vpp'],
                     'V2_frequency_Hz':r['v2']['frequency_hz'],'V2_duty_pct':100*r['v2']['duty'],
                     'V2_Vpp':r['v2']['vpp'],'V2_low_V':r['v2']['low_v'],'V2_high_V':r['v2']['high_v'],
                     'amplitude_ratio':r['v2']['vpp']/r['v1']['vpp']})
    with (DEST/'system_results.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

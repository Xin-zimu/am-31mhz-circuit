"""Summarize existing runs; no simulator invocation."""
import json,csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from study import ROOT,mean

def get(name):return json.loads((ROOT/'results'/f'{name}.json').read_text())
def avg(rows,key):return float(np.mean([p[key] for p in rows]))

rows=[]
for p in sorted((ROOT/'results').glob('*.json')):
    d=json.loads(p.read_text())
    if 'plateaus' not in d:continue
    ps=d['plateaus'];hi=[p for p in ps if p['high']];lo=[p for p in ps if not p['high']]
    row=dict(name=d['name'],VH=d['v3_high_fund_vpp'],VL=d['v3_low_fund_vpp'],m=d['modulation_index'],
             ic_low_ma=avg(lo,'ic_est_ma'),ic_high_ma=avg(hi,'ic_est_ma'),
             f_min_hz=min(p['freq_hz'] for p in ps),f_max_hz=max(p['freq_hz'] for p in ps),
             v3_f_min_hz=min((p['v3_frequency_hz'] for p in ps if p.get('v3_frequency_hz')),default=None),
             v3_f_max_hz=max((p['v3_frequency_hz'] for p in ps if p.get('v3_frequency_hz')),default=None),
             thd_max_pct=max(p['v3']['thd_h2_h5_pct'] for p in ps),
             vce_min=d['entire_window_vce_min'],vcb_min=d['entire_window_vcb_min'],
             i_rf_ma=d['rf_chain_supply_ma'],i_bb_ma=d.get('lm393_supply_ma',0),
             vh_repeat_pct=100*np.ptp([p['v3']['fund_vpp'] for p in hi])/d['v3_high_fund_vpp'],
             vl_repeat_pct=100*np.ptp([p['v3']['fund_vpp'] for p in lo])/d['v3_low_fund_vpp'])
    row['pbat_9v_iq8ma_est_mw']=9*(row['i_rf_ma']+row['i_bb_ma']+8) if d['settings'].get('full') else None
    rows.append(row)
with (ROOT/'results/summary.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(ROOT/'results/summary.json').write_text(json.dumps(rows,indent=2))

for name in ['coupled_nom','coupled_hp_d10','coupled_hp_d50','filtered_ideal_d10','coupled_filter_d10_r2','coupled_filter_d50_r2','coupled_filter_d50_fine']:
    p=ROOT/'results'/f'{name}_trace.npz'
    if not p.exists():continue
    d=np.load(p);t=d['time'];sel=t>t[-1]-100e-6;t=t[sel];v=d['v(v3)'][sel]
    edges=np.arange(t[0],t[-1],4/31e6);bins=np.searchsorted(t,edges)
    tc=[];hi=[];lo=[]
    for a,b in zip(bins[:-1],bins[1:]):
        if b>a:tc.append((t[a]+t[b-1])/2);hi.append(v[a:b].max());lo.append(v[a:b].min())
    fig,ax=plt.subplots(3,1,figsize=(10,7),constrained_layout=True)
    ax[0].plot((t-t[0])*1e6,d['v(vm)'][sel]);ax[0].set_ylabel('Baseband Vm (V)')
    ax[1].plot((np.array(tc)-t[0])*1e6,hi,label='raw maxima / 4 RF cycles')
    ax[1].plot((np.array(tc)-t[0])*1e6,lo,label='raw minima / 4 RF cycles');ax[1].set_ylabel('v3 envelope (V)');ax[1].legend(fontsize=8)
    z=(t>t[0]+35e-6)&(t<t[0]+35.3e-6)
    ax[2].plot((t[z]-t[z][0])*1e9,v[z]);ax[2].set_ylabel('v3 raw (V)');ax[2].set_xlabel('Zoom time (ns)')
    for a in ax[:2]:a.set_xlabel('Time in last 100 us (us)')
    for a in ax:a.grid(alpha=.25)
    fig.suptitle(name+' | simulation, test RC load; no antenna / 6 m claim')
    fig.savefig(ROOT/'figures'/f'{name}.png',dpi=160);plt.close(fig)

for row in rows:
    if row['name'].startswith(('coupled','comp2')):print(row)

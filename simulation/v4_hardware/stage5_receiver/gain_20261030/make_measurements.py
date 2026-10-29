"""Derive measurements.csv strictly from registered result records.

No value is estimated, interpolated across cases, or copied from a report.
Every row is one case that has a completed transient array; cases without a
complete array are listed in incomplete_cases.csv instead of being filled in.
"""
from run_gain import *
import csv, re

INTEGRATED_COLUMNS=['case','kind','wave','input_duty_pct','ac_source_peak_mV','m','blockers','method',
    'step_ns','window_us','vpp_V','robust_vpp_V','low_V','high_V','duty_out_pct','frequency_Hz',
    'peak20_V','delta20_db','normalization_base','rail_fraction','q1_vce_min_V','q2_vce_min_V',
    'supply_power_W','bb_gain20','elapsed_s']

def blockers_text(b):
    if not b:return ''
    return ';'.join(f'{f/1e6:g}MHz@{a*1000:g}mV@{p:g}rad' for f,a,p in b)

def main():
    data=json.loads((HERE/'summary.json').read_text())
    rows=[]
    for r in data['integrated']:
        rows.append(dict(case=r['name'],kind='integrated',wave=r['wave'],
            input_duty_pct=f"{r['input_duty']:g}",ac_source_peak_mV=f"{r['ac_mV']:g}",m=f"{r['m']:g}",
            blockers=blockers_text(r['blockers']),method=r['method'],step_ns=f"{r['step_ns']:g}",
            window_us=f"{r['start_us']:g}-{r['stop_us']:g}",
            vpp_V=f"{r['vpp']:.6f}",robust_vpp_V=f"{r['robust_vpp']:.6f}",
            low_V=f"{r['low']:.6f}",high_V=f"{r['high']:.6f}",
            duty_out_pct='' if r['duty_pct'] is None else f"{r['duty_pct']:.4f}",
            frequency_Hz='' if r['frequency_hz'] is None else f"{r['frequency_hz']:.3f}",
            peak20_V=f"{r['peak20']:.6f}",
            delta20_db='' if r['delta20_db'] is None else f"{r['delta20_db']:.4f}",
            normalization_base=r.get('normalization_base') or '',
            rail_fraction=f"{r['rail_fraction']:.5f}",
            q1_vce_min_V=f"{r['q1']['vce_min']:.4f}",q2_vce_min_V=f"{r['q2']['vce_min']:.4f}",
            supply_power_W=f"{r['supply_power_w']:.6f}",bb_gain20=f"{r['bb_gain20']:.4f}",
            elapsed_s=f"{json.loads((HERE/'results'/(r['name']+'.json')).read_text())['elapsed_s']:.2f}"))
    with (HERE/'measurements.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=INTEGRATED_COLUMNS);w.writeheader();w.writerows(rows)

    # Second file: network sensitivity (AC sweeps), never mixed with transient KPIs.
    ccols=['case','rs_ohm','q','bw_MHz','bw_interpolated_MHz','g31_dB','peak_MHz','db29','db33',
           'zin_real_ohm','zin_imag_ohm','return_loss50_dB','vswr50','params']
    crows=[dict(case=c['name'],rs_ohm=f"{c['parameters']['rs']:g}",
        q=f"{c['parameters'].get('q','')}",bw_MHz=f"{c['bw']/1e6:.4f}",
        bw_interpolated_MHz=f"{c['bw_interpolated_hz']/1e6:.4f}",g31_dB=f"{c['g31']:.4f}",
        peak_MHz=f"{c['peak_f']/1e6:.4f}",db29=f"{c['db29']:.3f}",db33=f"{c['db33']:.3f}",
        zin_real_ohm=f"{c['zin31'][0]:.3f}",zin_imag_ohm=f"{c['zin31'][1]:.3f}",
        return_loss50_dB=f"{c['return_loss50_db']:.3f}",vswr50=f"{c['vswr50']:.4f}",
        params=json.dumps(c['parameters'],sort_keys=True)) for c in data['components']]
    with (HERE/'network_sensitivity.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=ccols);w.writeheader();w.writerows(crows)

    # Third file: explicit incomplete/failed registry; no performance verdict here.
    fcols=['case','status','cause','elapsed_s','detail']
    frows=[]
    for p in sorted((HERE/'failures').glob('*.json')):
        r=json.loads(p.read_text())
        err=str(r.get('error',''))
        m=re.search(r'timed out after ([\d.]+) seconds',err)
        if m:cause='timeout';detail=f'compute budget of {float(m.group(1)):.0f} s expired; no complete array'
        elif 'Timestep too small' in err:cause='timestep';detail='solver timestep too small; no complete array'
        elif 'aborted' in err:cause='aborted';detail='solver aborted the transient; no complete array'
        elif r.get('reason'):cause='partial';detail=r['reason']
        elif err:cause='no_raw';detail='process ended without a raw file (log ends after the operating-point dump); cause not established by the retained evidence'
        else:cause='unknown';detail='retained failure record'
        frows.append(dict(case=p.stem,status='incomplete',cause=cause,
            elapsed_s='' if r.get('elapsed_s') is None else f"{r['elapsed_s']:.2f}",detail=detail))
    with (HERE/'incomplete_cases.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fcols);w.writeheader();w.writerows(frows)
    print(json.dumps(dict(integrated_rows=len(rows),component_rows=len(crows),incomplete_rows=len(frows)),indent=2))

if __name__=='__main__':main()

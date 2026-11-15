"""Reanalyze saved final waveforms and verify historical integrity; no simulation."""
import json, shutil
import numpy as np
from study import ROOT, read_raw, measure, sha

names=['coupled_filter_d10_r2','coupled_filter_d50_r2','coupled_filter_a2','coupled_filter_d50_fine']
backup=ROOT/'results/analysis_before_v3_frequency'
backup.mkdir(exist_ok=True)
checks={}
for name in names:
    p=ROOT/'results'/f'{name}.json'
    old=json.loads(p.read_text())
    if not (backup/p.name).exists():shutil.copy2(p,backup/p.name)
    raw=read_raw(ROOT/'results'/f'{name}.raw')
    assert all(np.isfinite(v).all() for v in raw.values())
    assert np.all(np.diff(raw['time'])>0)
    assert old['netlist_sha256']==sha(ROOT/'netlists'/f'{name}.cir')
    d=measure(name,raw,old['settings'])
    fs=[x['v3_frequency_hz'] for x in d['plateaus']]
    checks[name]={'finite_monotonic_raw':True,'netlist_hash_matches':True,
        'v3_frequency_range_hz':[min(fs),max(fs)],
        'VH':d['v3_high_fund_vpp'],'VL':d['v3_low_fund_vpp'],'m':d['modulation_index'],
        'thd_max_pct':max(x['v3']['thd_h2_h5_pct'] for x in d['plateaus']),
        'power_9v_iq8ma_est_mw':9*(d['rf_chain_supply_ma']+d['lm393_supply_ma']+8)}
workspace=ROOT.parents[2]
historical=json.loads((ROOT/'sources/historical_files_sha256.json').read_text())
changed=[]; resolved=[]
for p,h in historical.items():
    actual=workspace/p
    if actual.exists():
        if sha(actual)!=h:changed.append(p)
        continue
    # Original manifest contains two mojibake Chinese filenames; preserve it.
    # Resolve only a unique same-directory file with the original exact hash.
    matches=[q for q in actual.parent.glob('*'+actual.suffix) if sha(q)==h]
    if len(matches)==1:resolved.append({'manifest_path':p,'actual_path':str(matches[0].relative_to(workspace)),'sha256':h})
    else:changed.append(p)
checks['historical']={'count':len(historical),'changed_or_missing':changed,'manifest_filename_encoding_resolutions':resolved}
coarse=checks[names[1]];fine=checks[names[3]]
checks['fine_vs_coarse']={k:100*(fine[k]/coarse[k]-1) for k in ['VH','VL','m']}
checks['fine_vs_coarse']['v3_frequency_midpoint_delta_hz']=float(np.mean(fine['v3_frequency_range_hz'])-np.mean(coarse['v3_frequency_range_hz']))
(ROOT/'results/final_verification.json').write_text(json.dumps(checks,indent=2),encoding='utf8')
print(json.dumps(checks,indent=2))
assert not changed

"""Cross-check verdict_table.json against the frozen resupply metrics."""
import json
from pathlib import Path

H = Path(__file__).resolve().parent
v = json.loads((H / 'verdict_table.json').read_text(encoding='utf-8'))
fz = {r['case']: r for r in json.loads((H / 'resupply_frozen_summary.json').read_text(encoding='utf-8'))}

ok = True
for r in v['cases']:
    d = r['precharged_2ms_full']
    if not d:
        continue
    src = fz[r['case']]
    same_v = abs(d['vout_vpp'] - src['nodes']['V(v2)']['robust_vpp']) < 1e-12
    same_s = d['repeatability_screen_passes'] == src['repeatability_screen']['passes']
    ok &= (same_v and same_s)
    print(f"{r['case']}: verdict Vout={d['vout_vpp']:.6f} "
          f"frozen Vout={src['nodes']['V(v2)']['robust_vpp']:.6f} "
          f"screen={d['repeatability_screen_passes']}  match={same_v and same_s}")

print('ALL CONSISTENT' if ok else 'MISMATCH')

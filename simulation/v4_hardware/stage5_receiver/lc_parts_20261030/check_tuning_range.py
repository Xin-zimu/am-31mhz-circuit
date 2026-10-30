"""S05-08: does the proposed capacitor set actually cover the tuning demand?

The board is 30 pF + 2..18 pF on tank 1 and 39 pF + 2..18 pF on tank 2.
This reports, for every AC case that was re-tuned, where the two trimmers would
have to sit.  A demand outside 2..18 pF is a build the proposed BOM cannot reach,
regardless of how good the simulated response looks.
"""
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
AC = json.loads((HERE/'ac_cases.json').read_text(encoding='utf-8'))

FIXED = {'132-17L': (30.0, 39.0), 'IRF-24': (30.0, 39.0)}
TMIN, TMAX = 2.0, 18.0

rows = []
for case in AC:
    p = case['parameters']
    f1, f2 = FIXED[p['part']]
    # ct already includes the board stray; the trimmer sits on top of the fixed pad
    c1 = p['ct1'] + p['board1']
    c2 = p['ct2'] + p['board2']
    t1, t2 = c1 - f1, c2 - f2
    rows.append(dict(
        case=case['name'], part=p['part'],
        total_c1_pf=round(c1, 3), total_c2_pf=round(c2, 3),
        trimmer1_pf=round(t1, 3), trimmer2_pf=round(t2, 3),
        trimmer1_ok=bool(TMIN <= t1 <= TMAX), trimmer2_ok=bool(TMIN <= t2 <= TMAX),
        margin1_pf=round(min(t1-TMIN, TMAX-t1), 3),
        margin2_pf=round(min(t2-TMIN, TMAX-t2), 3)))

retuned = [r for r in rows if not r['case'].endswith(('_HELD', '_Rfreq', '_UNTUNED'))]
worst1 = min(retuned, key=lambda r: r['margin1_pf'])
worst2 = min(retuned, key=lambda r: r['margin2_pf'])

out = dict(
    board=dict(tank1='30 pF C0G + 2..18 pF trimmer = 32..48 pF',
               tank2='39 pF C0G + 2..18 pF trimmer = 41..57 pF'),
    trimmer_range_pf=[TMIN, TMAX],
    rows=rows,
    summary=dict(
        cases_checked=len(retuned),
        all_inside_range=all(r['trimmer1_ok'] and r['trimmer2_ok'] for r in retuned),
        trimmer1_span_pf=[min(r['trimmer1_pf'] for r in retuned),
                          max(r['trimmer1_pf'] for r in retuned)],
        trimmer2_span_pf=[min(r['trimmer2_pf'] for r in retuned),
                          max(r['trimmer2_pf'] for r in retuned)],
        tightest_tank1=worst1['case'], tightest_tank1_margin_pf=worst1['margin1_pf'],
        tightest_tank2=worst2['case'], tightest_tank2_margin_pf=worst2['margin2_pf']),
    caveat='the simulation tunes to an exact shape; on the bench the trimmer is set by '
           'observation, so the usable margin is smaller than the arithmetic suggests')
json.dump(out, open(HERE/'tuning_range.json', 'w', encoding='utf-8'), indent=2)
s = out['summary']
print(json.dumps(s, indent=1))
for r in rows:
    print('%-22s t1=%6.2f t2=%6.2f  ok=%s/%s' %
          (r['case'], r['trimmer1_pf'], r['trimmer2_pf'], r['trimmer1_ok'], r['trimmer2_ok']))

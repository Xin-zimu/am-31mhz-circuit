"""S05-08 full-chain case matrix (background job).

Every case re-uses the S05-06 warm-bias recipe; only the front end differs.
A failed case is retained and never retried under the same name.
"""
from pathlib import Path
import json, sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_chain as R

AC = json.loads((HERE/'ac_cases.json').read_text(encoding='utf-8'))
PAR = {row['name']: row['parameters'] for row in AC}


def case(name, front_name, **kw):
    front = R.register(front_name, PAR[front_name])
    return name, front, kw


CASES = [
    # --- nominal build: six-cycle square waves -----------------------------
    case('T_sq50_six',   'NOM_132', wave='square', duty=.5, stop=400, timeout_s=400),
    case('T_sq10_six',   'NOM_132', wave='square', duty=.1, stop=400, timeout_s=400),
    # --- blocking, sine reference and two CW frequencies --------------------
    case('T_sine_clean', 'NOM_132', stop=200, timeout_s=200),
    case('T_sine_29_10', 'NOM_132', stop=200, timeout_s=200, blockers=[[29e6, .01, 0]]),
    case('T_sine_29_50', 'NOM_132', stop=200, timeout_s=200, blockers=[[29e6, .05, 0]]),
    case('T_sine_33_10', 'NOM_132', stop=200, timeout_s=200, blockers=[[33e6, .01, 0]]),
    case('T_sine_33_40', 'NOM_132', stop=200, timeout_s=200, blockers=[[33e6, .04, 0]]),
    # --- square wave under a single 10 mV neighbour -------------------------
    case('T_sq10_29_10', 'NOM_132', wave='square', duty=.1, stop=200, timeout_s=200,
         blockers=[[29e6, .01, 0]]),
    case('T_sq50_33_10', 'NOM_132', wave='square', duty=.5, stop=200, timeout_s=200,
         blockers=[[33e6, .01, 0]]),
    # --- worst sensible build: Q31 = 40, retuned ---------------------------
    case('T_sq50_Q40_six', 'Q_PESS40', wave='square', duty=.5, stop=400, timeout_s=400),
    # --- tolerance corner retuned, and the same corner left as designed -----
    case('T_sq50_TOL_retuned', 'TOL_1p05_1p05', wave='square', duty=.5, stop=200, timeout_s=200),
    case('T_sq50_TOL_held', 'TOL_1p05_0p95_HELD', wave='square', duty=.5, stop=200,
         timeout_s=200),
]


def main():
    results = []
    ep = HERE/'chain_execution.json'
    prior = {}
    if ep.exists():
        prior = {r['name']: r for r in json.loads(ep.read_text(encoding='utf-8'))}
    for name, front, kw in CASES:
        if name in prior:
            print(json.dumps({'name': name, 'reused': True, 'completed': prior[name]['completed']}),
                  flush=True)
            results.append(prior[name])
            continue
        try:
            R.seeded(name, front, **kw)
            results.append(dict(name=name, completed=True))
        except Exception as e:                       # retained, not retried
            print(json.dumps({'name': name, 'error': str(e)[:400]}), flush=True)
            results.append(dict(name=name, completed=False, error=str(e)[:400]))
        ep.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'done': True, 'total': len(results),
                      'completed': sum(r['completed'] for r in results)}))


if __name__ == '__main__':
    main()

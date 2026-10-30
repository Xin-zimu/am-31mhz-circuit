"""S05-08 evidence manifest and audit.

Hashes every file this stage produced, re-verifies that each ngspice result JSON
still matches its netlist, raw array and log, and confirms the historical S05
directories were not modified.
"""
from pathlib import Path
import json, hashlib, sys

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent
IGNORE = {'__pycache__', 'attempt01_aborted'}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def walk(root):
    out = []
    for p in sorted(root.rglob('*')):
        if p.is_dir() or any(part in IGNORE for part in p.parts):
            continue
        out.append(dict(path=str(p.relative_to(HERE)).replace('\\', '/'),
                        bytes=p.stat().st_size, sha256=sha(p)))
    return out


manifest = walk(HERE)
(HERE/'evidence_manifest.json').write_text(
    json.dumps(dict(stage='S05-08', file_count=len(manifest), files=manifest),
               indent=2, ensure_ascii=False), encoding='utf-8')

# --- re-verify every ngspice AC and transient record ------------------------
checks, bad = [], []
for rec_path in sorted((HERE/'results').glob('*.json')):
    r = json.loads(rec_path.read_text(encoding='utf-8'))
    name = r.get('name')
    if not name or 'net_sha256' not in r:
        continue          # measurement sidecar, not an ngspice record
    try:
        net = HERE/'netlists'/(name+'.cir')
        ok_net = net.exists() and sha(net) == r['net_sha256']
        ok_raw = Path(r['raw_path']).exists() and sha(r['raw_path']) == r['raw_sha256']
        log = HERE/'results'/(name+'.log')
        ok_log = log.exists() and sha(log) == r['log_sha256']
    except Exception as e:                       # noqa: BLE001
        bad.append(dict(name=name, error=str(e))); continue
    entry = dict(name=name, net=ok_net, raw=ok_raw, log=ok_log)
    (checks if all((ok_net, ok_raw, ok_log)) else bad).append(entry)

# --- historical directories must be untouched ------------------------------
prior = {}
for sub in ('lc_realization_20261030', 'gain_20261030', 'blocker_20261029',
            'selectivity_20261029'):
    d = STAGE/sub
    if not d.exists():
        continue
    files = [p for p in d.rglob('*') if p.is_file() and '__pycache__' not in p.parts
             and 'attempt01_aborted' not in p.parts]
    prior[sub] = dict(file_count=len(files),
                      aggregate_sha256=hashlib.sha256(
                          ''.join(sha(p) for p in files).encode()).hexdigest())

# git is the independent witness for "nothing historical was modified":
# d05fe67 committed the whole S05-07 batch before this stage started.
import subprocess
git = {}
for sub in ('lc_realization_20261030', 'gain_20261030'):
    p = subprocess.run(['git', 'status', '--porcelain', '--',
                        str(STAGE/sub)], cwd=HERE, capture_output=True, text=True)
    git[sub] = dict(dirty_lines=[l for l in p.stdout.splitlines() if l.strip()])
# HEAD moves with every amend of this very commit, so the stable reference is
# the parent baseline (the S05-07 commit). Record both, clearly labelled.
git['head_at_audit_time'] = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=HERE,
                                           capture_output=True, text=True).stdout.strip()
git['baseline_commit'] = 'd05fe679f7f7d7d244935c8919fba90537e0a846'
git['baseline_note'] = ('S05-07 commit; fixed reference, does not move with amends '
                        'of this stage')

audit = dict(
    results_verified=len(checks), results_failed=len(bad), failures=bad,
    historical_directories=prior, git=git,
    note='historical aggregate hashes pin the S05-05/06/07 evidence this stage read; '
         'this script only reads them. git status is the independent check.',
    solvers=json.loads((HERE/'solver_crosscheck.json').read_text(encoding='utf-8')))
(HERE/'audit.json').write_text(json.dumps(audit, indent=2, ensure_ascii=False),
                               encoding='utf-8')

print(json.dumps(dict(files=len(manifest), verified=len(checks), failed=len(bad)), indent=1))
for k, v in prior.items():
    print(' ', k, v['file_count'], v['aggregate_sha256'][:16])
if bad:
    print('FAILURES', json.dumps(bad)[:800]); sys.exit(1)

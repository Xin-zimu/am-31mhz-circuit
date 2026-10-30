"""S05-09: manifest, hash audit and no-touch check for the S05-08 baseline."""
from pathlib import Path
import json, hashlib, subprocess, sys

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


files = []
for p in sorted(HERE.rglob('*')):
    if p.is_dir() or '__pycache__' in p.parts:
        continue
    files.append(dict(path=str(p.relative_to(HERE)).replace('\\', '/'),
                      bytes=p.stat().st_size, sha256=sha(p)))

checks, bad = [], []
for rec in sorted((HERE/'results').glob('*.json')):
    r = json.loads(rec.read_text(encoding='utf-8'))
    name = r.get('name')
    if not name or 'net_sha256' not in r:
        continue
    net = HERE/'netlists'/(name+'.cir')
    ok = (net.exists() and sha(net) == r['net_sha256']
          and Path(r['raw_path']).exists() and sha(r['raw_path']) == r['raw_sha256']
          and (HERE/'results'/(name+'.log')).exists()
          and sha(HERE/'results'/(name+'.log')) == r['log_sha256'])
    (checks if ok else bad).append(name)

s08 = subprocess.run(['git', 'status', '--porcelain', '--',
                      str(STAGE/'lc_parts_20261030')], cwd=HERE,
                     capture_output=True, text=True).stdout.splitlines()
s08 = [l for l in s08 if l.strip()]

out = dict(stage='S05-09', file_count=len(files), files=files,
           ngspice_results_verified=len(checks), ngspice_failures=bad,
           s05_08_baseline_dirty=s08,
           note=('lc_parts_20261030 is the committed S05-08 baseline; S05-09 artifacts '
                 'were initially written there by mistake and were moved out before this '
                 'audit, which is why the dirty list must be empty'))
(HERE/'audit.json').write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding='utf-8')

print(json.dumps({k: out[k] for k in ('file_count', 'ngspice_results_verified',
                                      'ngspice_failures', 's05_08_baseline_dirty')}, indent=1))
if s08 or bad:
    sys.exit(1)

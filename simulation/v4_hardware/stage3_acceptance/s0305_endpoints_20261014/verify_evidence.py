"""Audit source integrity, runtime copies and independently check reused numbers."""
from pathlib import Path
import hashlib
import json
import re
import numpy as np

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent
OLD = STAGE/'副本专用文件夹'/'final2_20261014'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    manifest = json.loads((HERE/'run_manifest.json').read_text('utf-8'))
    base = Path(manifest['baseline']).read_bytes()
    audit = {'baseline_manifest_checks': [], 'case_checks': [], 'reused_data_checks': [], 'artifacts': []}
    for source in json.loads((STAGE/'baseline_manifest.json').read_text('utf-8'))['sources']:
        path = Path(source['path'])
        got = digest(path)
        audit['baseline_manifest_checks'].append({'path': str(path), 'sha256': got, 'unchanged': got == source['sha256']})
        assert got == source['sha256'], path
    assert digest(STAGE/'S03_BASELINE_V4_3.ms14') == digest(STAGE.parent/'AM_20k_31MHz_V4_3_REPAIRED.ms14')
    for case in manifest['cases']:
        path = HERE/(case['tag']+'.cir')
        current = path.read_bytes()
        edits = {c['component']: c for c in case['changes']}
        changed = []
        assert len(current.splitlines()) == len(base.splitlines())
        for original, modified in zip(base.splitlines(), current.splitlines()):
            if original == modified:
                continue
            a, b = original.split(), modified.split()
            name = a[0].decode()
            assert name in edits
            assert a[:3] == b[:3] and a[4:] == b[4:]
            assert a[3].decode() == edits[name]['from'] and b[3].decode() == edits[name]['to']
            changed.append(name)
        assert set(changed) == set(edits)
        runtime = Path(manifest['runtime_dir'])/path.name
        assert digest(path) == digest(runtime) == case['cir_sha256']
        audit['case_checks'].append({'case': case['case'], 'changed_components': changed, 'source_runtime_hash_match': True,
                                     'all_other_lines_identical': True, 'external_includes': re.findall(rb'(?im)^\.(?:inc|include|lib)\s+.*', current)})
    results = json.loads((HERE/'summary.json').read_text('utf-8'))
    old_results = json.loads((OLD/'linearity_final.json').read_text('utf-8'))
    for case, key in [('C4', 'four_vpp'), ('C5', 'two_vpp')]:
        r = next(r for r in results if r['case'] == case)
        comparisons = {'vin': r['nodes']['V(v1)']['robust_vpp'], 'vout': r['nodes']['V(v2)']['robust_vpp'],
                       'v2_mean': r['nodes']['V(v2)']['mean_v'], 'freq': r['input_frequency_hz'], 'duty': r['input_duty_percent']}
        errors = {k: v-old_results[key][k] for k, v in comparisons.items()}
        assert max(abs(v) for v in errors.values()) < 1e-10
        audit['reused_data_checks'].append({'case': case, 'differences_vs_archived_result': errors})
    for r in results:
        path = Path(r['raw_path'])
        assert digest(path) == r['raw_sha256']
        if 'archived_raw_path' in r:
            assert digest(Path(r['archived_raw_path'])) == r['raw_sha256']
        with np.load(HERE/(r['case']+'_tail.npz')) as z:
            values = z['data']
            assert np.isfinite(values).all() and np.all(np.diff(values[:,0]) >= 0)
            assert len(values) == r['points'] and abs(values[-1,0]-.005) < 1e-12
        audit['artifacts'].append({'case': r['case'], 'source': str(path), 'sha256': r['raw_sha256'],
                                   'bytes': path.stat().st_size, 'points': r['points'], 'finite_monotonic_complete': True})
    audit['cases_available'] = len(results)
    audit['all_seven_available'] = len(results) == 7
    (HERE/'evidence_audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'source_hashes_unchanged': len(audit['baseline_manifest_checks']), 'variants_checked': len(audit['case_checks']),
                      'reused_data_exact': True, 'cases_available': len(results)}, ensure_ascii=True))


if __name__ == '__main__':
    main()

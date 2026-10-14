"""Read saved cold-start evidence; do not infer success from a filename."""
from pathlib import Path
import hashlib
import json
import re
import xml.etree.ElementTree as ET
import numpy as np

HERE = Path(__file__).resolve().parent

def digest(name):
    path = HERE / name
    return {"file": name, "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

def traces(name):
    result, arrays = {}, {}
    for trace in ET.parse(HERE / name).iter('CTrace'):
        data = trace.find('Data')
        if data is None:
            continue
        label = trace.get('Name').removeprefix('&ASC')
        x = np.frombuffer(bytes.fromhex(data.get('XData')), dtype='<f8')
        y = np.frombuffer(bytes.fromhex(data.get('YData')), dtype='<f8')
        assert len(x) == len(y) and len(x) > 1
        assert np.all(np.isfinite(x)) and np.all(np.isfinite(y))
        assert np.all(np.diff(x) >= 0)
        first = np.flatnonzero(x > 0)[0]
        result[label] = {'points': len(x), 'end_s': float(x[-1]),
                         'first_positive_time_s': float(x[first]),
                         'first_positive_value_v': float(y[first]),
                         'last_value_v': float(y[-1])}
        arrays[label] = (x, y)
    assert set(result) == {'V(bb_in)', 'V(bbo)', 'V(v1)', 'V(v2)'}
    return result, arrays

def settings(name):
    text = (HERE / name).read_text()
    start = text.index('TRAN:list{')
    start = text.index('ANALYSIS:list{', start)
    # First ASYS_OPT group following this transient analysis, before the next analysis.
    section = text[start:start + 4000]
    values = {}
    for key in ['TSTEP', 'TSTOP', 'TSTART', 'TMAX', 'IC']:
        match = re.search(r'\b' + key + r':\w+\{([^}]+)\}', section)
        values[key] = match.group(1)
    for key in ['itl4', 'method', 'reltol', 'trtol']:
        match = re.search(r'IsEnabled:long\{([01])\}\s+' + key + r':\w+\{([^}]+)\}', section)
        assert match, key
        values[key] = {'enabled': bool(int(match.group(1))), 'value': match.group(2)}
    return values

def components(name):
    text = (HERE / name).read_text()
    blocks = re.findall(r'<CiComponent Class="CiComponent".*?</CiComponent>', text, re.S)
    return [re.sub(r'\b(SymCompID|Circuit|CiID|Model)="[0-9]+"',
                   r'\1="RUNTIME_ID"', b) for b in blocks]

def main():
    trials = [
        ('TRAP500', 'S03_COLD_ZERO_TRAP500_20us', 'trap500_20us_settings.xml',
         'S03_COLD_ZERO_TRAP500_20us.gra'),
        ('GEAR500', 'S03_COLD_ZERO_GEAR500_20us', 'gear500_20us_settings.xml',
         'S03_COLD_GEAR_page_audit.gra'),
        ('GEAR500_REOPEN', 'S03_COLD_ZERO_GEAR500_20us', 'gear500_reopen_saved_settings.xml',
         'S03_COLD_ZERO_GEAR500_REOPEN_20us.gra')]
    baseline = components('cold_explicit_zero_settings.xml')
    result = {'date': '2026-10-13', 'stage': 'S03-04',
              'status': 'UNRESOLVED_TRANSIENT_NONCONVERGENCE',
              'solver': 'Multisim 14.3 native GUI', 'passed': False,
              'error': 'Unable to converge during transient analysis. Simulation canceled.',
              'trials': []}
    all_arrays = {}
    for label, project, config, gra in trials:
        data, arrays = traces(gra.removesuffix('.gra') + '.decoded.xml')
        all_arrays[label] = arrays
        current = components(config)
        assert len(current) == len(baseline) == 80
        equal = current == baseline
        assert equal
        result['trials'].append({'name': label, 'project': digest(project + '.ms14'),
                                'settings_snapshot': digest(config), 'gra': digest(gra),
                                'settings': settings(config), 'traces': data,
                                'completed_20us': all(abs(v['end_s'] - 20e-6) < 1e-12 for v in data.values()),
                                'component_blocks_equal_ignoring_runtime_ids': equal})
    result['gear_reopen_arrays_identical'] = all(
        np.array_equal(a, b) for name in all_arrays['GEAR500']
        for a, b in zip(all_arrays['GEAR500'][name], all_arrays['GEAR500_REOPEN'][name]))
    result['evidence_notes'] = [
        'TRAP/Gear first runs and Gear fresh-process reopen/run occurred before the interrupted turn; final save, export and audit were completed in this resumed turn.',
        'Gear first page retained an old TRAP title; fresh-process reopen page uses the Gear project title. Trace arrays match the Gear first run.',
        'Component block comparison does not by itself validate all wire topology or external model references.',
        'Ideal DC supplies; no supply ramp. Nonzero-time samples exclude the former 4.5 V precharge, but do not prove every internal macro-model state is zero.',
        'All three trials failed before 20 us. No startup-time, steady-state, or hardware-startup conclusion follows.'
    ]
    (HERE / 'cold_solver_trials.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'trials': [{k: t[k] for k in ['name', 'completed_20us', 'traces']} for t in result['trials']],
                      'gear_reopen_arrays_identical': result['gear_reopen_arrays_identical']}, indent=2))

if __name__ == '__main__':
    main()

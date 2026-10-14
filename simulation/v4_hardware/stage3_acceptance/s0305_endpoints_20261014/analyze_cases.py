"""Measure completed S03-05 cases with the frozen S03-04 6.2 method.

Run repeatedly while the serial batch is in progress. Existing metrics are
immutable caches; use --refresh to recompute them from archived raw data.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent
sys.path.insert(0, str(STAGE))
from measure_stage3 import read_raw, crossings

RUNTIME = Path('D:/ms_xsp/stage3_acceptance/s0305_endpoints_20261014')
OLD = Path('D:/ms_xsp/stage3_acceptance/s0304_final2_20261014')
NODES = ['V(v1)', 'V(bb_in)', 'V(bbo)', 'V(v2)']


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def cycle_rows(t, values, names):
    grid = np.arange(max(t[0], t[-1]-300e-6), t[-1], 2e-9)
    vin = np.interp(grid, t, values[:, names.index('V(v1)')])
    level = float(np.mean(np.percentile(vin, [2, 98])))
    up, down = crossings(t, values[:, names.index('V(v1)')], level)
    rows = []
    for start, end in zip(up[:-1], up[1:]):
        if start < t[0] or end > t[-1]:
            continue
        g = np.arange(start, end, 2e-9)
        falls = down[(down > start) & (down < end)]
        row = {'start_s': float(start), 'end_s': float(end), 'period_s': float(end-start),
               'input_frequency_hz': float(1/(end-start)), 'input_falling_crossings': int(len(falls)),
               'input_duty_percent': float(100*(falls[0]-start)/(end-start)) if len(falls) == 1 else None}
        for node in NODES:
            y = np.interp(g, t, values[:, names.index(node)])
            raw = values[np.searchsorted(t, start):np.searchsorted(t, end, side='right'), names.index(node)]
            lo, hi = np.percentile(y, [2, 98])
            row[node] = {'mean_v': float(np.trapezoid(y, g)/(g[-1]-g[0])),
                         'robust_vpp': float(hi-lo), 'p02_v': float(lo), 'p98_v': float(hi),
                         'raw_vpp': float(np.ptp(raw)), 'raw_min_v': float(raw.min()), 'raw_max_v': float(raw.max())}
        rows.append(row)
    return rows


def output_rows(t, values, names):
    g = np.arange(max(t[0], t[-1]-300e-6), t[-1], 2e-9)
    y = np.interp(g, t, values[:, names.index('V(v2)')])
    level = float(np.mean(np.percentile(y, [2, 98])))
    up, down = crossings(g, y, level)
    rows = []
    for start, end in zip(up[:-1], up[1:]):
        falls = down[(down > start) & (down < end)]
        rows.append({'start_s': float(start), 'end_s': float(end), 'frequency_hz': float(1/(end-start)),
                     'falling_crossings': int(len(falls)),
                     'duty_percent': float(100*(falls[0]-start)/(end-start)) if len(falls) == 1 else None})
    return level, rows


def slope(rows):
    x = np.array([(r['start_s']+r['end_s'])/2 for r in rows]) * 1000
    y = np.array([r['V(v2)']['mean_v'] for r in rows]) * 1000
    fit = np.polyfit(x-x.mean(), y, 1)
    residual = y-np.polyval(fit, x-x.mean())
    return {'start_s': rows[0]['start_s'], 'end_s': rows[-1]['end_s'], 'cycles': len(rows),
            'slope_mV_per_ms': float(fit[0]), 'fit_max_residual_mV': float(np.max(np.abs(residual)))}


def measure(case, raw_path):
    names, values = read_raw(raw_path)
    t = values[:, 0]
    header = raw_path.open(encoding='ascii')
    expected_points = None
    for line in header:
        if line.startswith('No. Points:'):
            expected_points = int(line.split(':')[1])
        if line.strip() == 'Values:':
            break
    header.close()
    assert expected_points == len(t), (expected_points, len(t))
    expected_stop = case.get('stop_s', .005)
    assert abs(t[-1]-expected_stop) < 1e-12, t[-1]
    assert 0 <= t[0]-(expected_stop-.0005) < 2.01e-9, t[0]
    rows = cycle_rows(t, values, names)
    assert len(rows) >= 5, 'Insufficient complete input cycles'
    tail = rows[-5:]
    out_level, out_rows = output_rows(t, values, names)
    assert len(out_rows) >= 5, 'Insufficient complete output cycles'
    out_tail = out_rows[-5:]
    node_summary = {node: {key: float(np.mean([r[node][key] for r in tail])) for key in tail[0][node]} for node in NODES}
    amp = node_summary['V(v2)']['robust_vpp']
    mean_span = float(np.ptp([r['V(v2)']['mean_v'] for r in tail]))
    amp_span = float(np.ptp([r['V(v2)']['robust_vpp'] for r in tail]))
    period_span = float(np.ptp([r['period_s'] for r in tail])/np.mean([r['period_s'] for r in tail]))
    drift = [slope(rows[i:i+4]) for i in range(len(rows)-3)]
    raw_sha = digest(raw_path)
    result = {**case, 'raw_path': str(raw_path), 'raw_sha256': raw_sha, 'raw_bytes': raw_path.stat().st_size,
              'points': len(t), 'saved_start_s': float(t[0]), 'saved_end_s': float(t[-1]),
              'min_step_s': float(np.diff(t).min()), 'max_step_s': float(np.diff(t).max()),
              'median_step_s': float(np.median(np.diff(t))),
              'method_source_sha256': digest(STAGE/'measure_stage3.py'),
              'nodes': node_summary, 'complete_input_cycles': len(rows),
              'last_five_start_s': tail[0]['start_s'], 'last_five_end_s': tail[-1]['end_s'],
              'input_frequency_hz': float(np.mean([r['input_frequency_hz'] for r in tail])),
              'input_duty_percent': float(np.mean([r['input_duty_percent'] for r in tail])) if all(r['input_duty_percent'] is not None for r in tail) else None,
              'output_frequency_hz': float(np.mean([r['frequency_hz'] for r in out_tail])),
              'output_duty_percent': float(np.mean([r['duty_percent'] for r in out_tail])) if all(r['duty_percent'] is not None for r in out_tail) else None,
              'output_crossing_level_v': out_level, 'output_cycles_last_300us': out_rows,
              'input_abnormal_crossing_cycles': sum(r['input_falling_crossings'] != 1 for r in rows),
              'output_abnormal_crossing_cycles': sum(r['falling_crossings'] != 1 for r in out_rows),
              'repeatability_screen': {'threshold_fraction': .001, 'official_scoring_criterion': False,
                                      'mean_span_v': mean_span, 'mean_span_percent': 100*mean_span/amp,
                                      'robust_vpp_span_v': amp_span, 'robust_vpp_span_percent': 100*amp_span/amp,
                                      'period_span_percent': 100*period_span,
                                      'passes': bool(mean_span/amp <= .001 and amp_span/amp <= .001 and period_span <= .001)},
              'drift_windows': drift, 'drift_all_tail': slope(rows), 'last_five_cycles': tail}
    result['robust_gain'] = amp / node_summary['V(v1)']['robust_vpp']
    result['raw_gain'] = node_summary['V(v2)']['raw_vpp']/node_summary['V(v1)']['raw_vpp']
    result['output_frequency_error_percent'] = (result['output_frequency_hz']/20000-1)*100
    result['input_duty_error_pp'] = result['input_duty_percent']-case['target_duty_percent'] if result['input_duty_percent'] is not None else None
    result['output_minus_input_duty_pp'] = result['output_duty_percent']-result['input_duty_percent'] if result['output_duty_percent'] is not None and result['input_duty_percent'] is not None else None
    output_key = case.get('output_key', case['case'])
    (HERE/(output_key+'_cycles.json')).write_text(json.dumps(rows, indent=2), encoding='utf-8')
    np.savez_compressed(HERE/(output_key+'_tail.npz'), data=values, names=names)
    if not case.get('reused'):
        dest = HERE/raw_path.name
        if dest.exists():
            assert digest(dest) == raw_sha
        else:
            shutil.copy2(raw_path, dest)
        result['archived_raw_path'] = str(dest)
    return result


def plot(results):
    fig, axes = plt.subplots(len(results), 2, figsize=(13, 2.5*len(results)), squeeze=False, layout='constrained')
    for ax, result in zip(axes, results):
        case = result['case']
        z = np.load(HERE/(case+'_tail.npz'))
        data, names = z['data'], z['names'].tolist()
        t = data[:, 0]
        g = np.arange(t[-1]-100e-6, t[-1], 5e-9)
        for node, label in [('V(v1)', 'Vin'), ('V(v2)', 'Vout')]:
            y = np.interp(g, t, data[:, names.index(node)])
            ax[0].plot((g-t[-1])*1e6, y, label=label, linewidth=.9)
        ax[0].set(title=f"{case}: {result['target_vpp']} Vpp / {result['target_duty_percent']}%", xlabel='Time relative to 5 ms (us)', ylabel='Voltage (V)')
        rows = json.loads((HERE/(case+'_cycles.json')).read_text())
        mid = [(r['start_s']+r['end_s'])*500 for r in rows]
        mean = np.array([r['V(v2)']['mean_v'] for r in rows])
        ax[1].plot(mid, (mean-mean[-1])*1000, '.-')
        first = result['drift_windows'][0]['slope_mV_per_ms']
        last = result['drift_windows'][-1]['slope_mV_per_ms']
        ax[1].set(title=f'DC drift rate: {first:+.3f} -> {last:+.3f} mV/ms', xlabel='Time (ms)', ylabel='Mean minus last cycle (mV)')
        ax[0].legend(loc='best')
        for a in ax:
            a.grid(alpha=.25)
    fig.savefig(HERE/'S03_05_waveforms_and_drift.png', dpi=160)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--refresh', action='store_true')
    args = parser.parse_args()
    manifest = json.loads((HERE/'run_manifest.json').read_text(encoding='utf-8'))
    selection_path = HERE/'selected_runs.json'
    selections = json.loads(selection_path.read_text(encoding='utf-8')) if selection_path.exists() else {}
    cases = list(manifest['cases']) + [
        {'case': 'C4', 'tag': 'REF_4Vpp_tail', 'target_vpp': 4, 'target_duty_percent': 50, 'reused': True},
        {'case': 'C5', 'tag': 'LIN_2Vpp_tail', 'target_vpp': 2, 'target_duty_percent': 50, 'reused': True}]
    results = []
    for case in sorted(cases, key=lambda c: c['case']):
        if case['case'] in selections:
            case = dict(case, tag=selections[case['case']])
            case['cir_sha256'] = digest(HERE/(case['tag']+'.cir'))
            case['cmd_sha256'] = digest(HERE/(case['tag']+'.cmd'))
            case['actual_tran'] = next(line for line in (HERE/(case['tag']+'.cmd')).read_text('ascii').splitlines() if line.startswith('tran '))
        if not case.get('reused'):
            status_path = HERE/(case['tag']+'_status.json')
            if not status_path.exists() or json.loads(status_path.read_text(encoding='utf-8-sig'))['status'] != 'COMPLETED':
                continue
        raw_path = (OLD if case.get('reused') else RUNTIME)/(case['tag']+'.raw')
        dest = HERE/(case['case']+'_metrics.json')
        if dest.exists() and not args.refresh:
            result = json.loads(dest.read_text(encoding='utf-8'))
        else:
            result = measure(case, raw_path)
            dest.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        results.append(result)
    ref = next(r for r in results if r['case'] == 'C4')
    for r in results:
        r['normalized_gain_error_percent'] = 100*(r['robust_gain']/ref['robust_gain']-1)
        r['setting_ratio_error_signed_percent'] = 100*(r['nodes']['V(v2)']['robust_vpp']/(ref['nodes']['V(v2)']['robust_vpp']*r['target_vpp']/4)-1)
        r['setting_ratio_error_absolute_percent'] = abs(r['setting_ratio_error_signed_percent'])
    (HERE/'summary.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    plot(results)
    for r in results:
        print(json.dumps({'case': r['case'], 'vin': r['nodes']['V(v1)']['robust_vpp'], 'vout': r['nodes']['V(v2)']['robust_vpp'],
                          'fout': r['output_frequency_hz'], 'din': r['input_duty_percent'], 'dout': r['output_duty_percent'],
                          'gain_error_percent': r['normalized_gain_error_percent'], 'screen': r['repeatability_screen'],
                          'drift_first': r['drift_windows'][0]['slope_mV_per_ms'], 'drift_last': r['drift_windows'][-1]['slope_mV_per_ms']}, ensure_ascii=True))


if __name__ == '__main__':
    main()

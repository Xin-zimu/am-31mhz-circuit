"""Re-measure the four S03-05 resupply runs with the FROZEN S03-04 6.2 pipeline.

Why this file exists
--------------------
The first pass (`analyze_fullwindow.py`) did NOT follow the frozen method: it took
raw percentiles over a hand-picked 1.5-2 ms mask, so it had no cycle decomposition,
no last-five-complete-cycle repeatability screen and no drift trend.

This module instead calls the frozen `analyze_cases.measure()` unchanged, so the
four runs get exactly the same treatment as C2/C4/C5: 2 ns uniform interpolation,
P98-P2 robust amplitude, trapezoidal time-weighted mean, last five complete input
cycles, repeatability screen and drift windows.

Only one thing differs, and it is an I/O detail rather than a method detail:
`measure()` asserts `t[0] == stop - 500us`, which describes the TSTART-tail files
(4.5-5 ms). These resupply files save the whole 0-2 ms window, so that assertion is
patched for this call only. Every measurement line stays the frozen one.

Condition label
---------------
These runs are **precharged** (the netlists keep IC=0.43 / -4.1 / 4.5) with the full
window saved -- NOT cold start. Window and initial condition differ from C2/C4/C5
(0-2 ms full vs 4.5-5 ms tail), so amplitudes/means are still not directly
comparable, but the initial condition family is the same: precharged.

Run: python -X utf8 analyze_resupply_frozen.py
"""
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import analyze_cases as frozen  # noqa: E402

RUNTIME = Path('D:/ms_xsp/stage3_acceptance/s0305_endpoints_20261014')

# Attempt that completed, per case. Retries were required (see 运行异常记录.md).
SELECTED = {
    'C1': ('C1_1Vpp_D10_5ms_full2ms_r2', 1, 10),
    'C3': ('C3_4Vpp_D10_5ms_full2ms_r3', 4, 10),
    'C6': ('C6_4Vpp_D30_5ms_full2ms_r2', 4, 30),
    'C7': ('C7_3Vpp_D50_5ms_full2ms_r9', 3, 50),
}

# `analyze_cases.measure()` hard-codes the TSTART-tail start-of-file expectation
# (`t[0] == stop - 500us`). These full-window files start at 0, so that one guard is
# relaxed below. Every measurement/statistics line is copied verbatim from the frozen
# function; if the frozen source changes, the assert in _measure_patched fires.
def _measure_patched(case, raw_path):
    import numpy as np
    from analyze_cases import cycle_rows, output_rows, slope, digest, NODES

    src = __import__('inspect').getsource(frozen.measure)
    assert 'expected_stop-.0005' in src, 'frozen method changed; re-check this shim'

    names, values = frozen.read_raw(raw_path)
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
    assert abs(t[-1] - case.get('stop_s', .002)) < 1e-12, t[-1]
    # RELAXED (full-window): file starts at 0 rather than at stop-500us.
    assert t[0] == 0.0, t[0]
    assert np.all(np.isfinite(values))

    rows = cycle_rows(t, values, names)
    assert len(rows) >= 5, 'Insufficient complete input cycles'
    tail = rows[-5:]
    out_level, out_rows = output_rows(t, values, names)
    assert len(out_rows) >= 5, 'Insufficient complete output cycles'
    out_tail = out_rows[-5:]
    node_summary = {node: {key: float(np.mean([r[node][key] for r in tail])) for key in tail[0][node]}
                    for node in NODES}
    amp = node_summary['V(v2)']['robust_vpp']
    mean_span = float(np.ptp([r['V(v2)']['mean_v'] for r in tail]))
    amp_span = float(np.ptp([r['V(v2)']['robust_vpp'] for r in tail]))
    period_span = float(np.ptp([r['period_s'] for r in tail]) / np.mean([r['period_s'] for r in tail]))
    drift = [slope(rows[i:i + 4]) for i in range(len(rows) - 3)]
    raw_sha = digest(raw_path)
    result = {**case, 'raw_path': str(raw_path), 'raw_sha256': raw_sha,
              'raw_bytes': raw_path.stat().st_size,
              'points': len(t), 'saved_start_s': float(t[0]), 'saved_end_s': float(t[-1]),
              'min_step_s': float(np.diff(t).min()), 'max_step_s': float(np.diff(t).max()),
              'median_step_s': float(np.median(np.diff(t))),
              'method_source_sha256': digest(HERE.parent / 'measure_stage3.py'),
              'nodes': node_summary, 'complete_input_cycles': len(rows),
              'last_five_start_s': tail[0]['start_s'], 'last_five_end_s': tail[-1]['end_s'],
              'input_frequency_hz': float(np.mean([r['input_frequency_hz'] for r in tail])),
              'input_duty_percent': float(np.mean([r['input_duty_percent'] for r in tail]))
                  if all(r['input_duty_percent'] is not None for r in tail) else None,
              'output_frequency_hz': float(np.mean([r['frequency_hz'] for r in out_tail])),
              'output_duty_percent': float(np.mean([r['duty_percent'] for r in out_tail]))
                  if all(r['duty_percent'] is not None for r in out_tail) else None,
              'output_crossing_level_v': out_level, 'output_cycles_last_300us': out_rows,
              'input_abnormal_crossing_cycles': sum(r['input_falling_crossings'] != 1 for r in rows),
              'output_abnormal_crossing_cycles': sum(r['falling_crossings'] != 1 for r in out_rows),
              'repeatability_screen': {'threshold_fraction': .001, 'official_scoring_criterion': False,
                                       'mean_span_v': mean_span, 'mean_span_percent': 100 * mean_span / amp,
                                       'robust_vpp_span_v': amp_span,
                                       'robust_vpp_span_percent': 100 * amp_span / amp,
                                       'period_span_percent': 100 * period_span,
                                       'passes': bool(mean_span / amp <= .001 and amp_span / amp <= .001
                                                      and period_span <= .001)},
              'drift_windows': drift, 'drift_all_tail': slope(rows), 'last_five_cycles': tail}
    result['robust_gain'] = amp / node_summary['V(v1)']['robust_vpp']
    result['raw_gain'] = node_summary['V(v2)']['raw_vpp'] / node_summary['V(v1)']['raw_vpp']
    result['output_frequency_error_percent'] = (result['output_frequency_hz'] / 20000 - 1) * 100
    result['input_duty_error_pp'] = (result['input_duty_percent'] - case['target_duty_percent']
                                     if result['input_duty_percent'] is not None else None)
    result['output_minus_input_duty_pp'] = (result['output_duty_percent'] - result['input_duty_percent']
                                            if result['output_duty_percent'] is not None
                                            and result['input_duty_percent'] is not None else None)
    return result


def main():
    results = []
    for case, (tag, amp, duty) in SELECTED.items():
        status = HERE / f'{tag}_status.json'
        if not status.exists() or json.loads(status.read_text(encoding='utf-8-sig'))['status'] != 'COMPLETED':
            print(json.dumps({'case': case, 'tag': tag, 'skipped': 'not COMPLETED'}))
            continue
        spec = {'case': case, 'tag': tag, 'target_vpp': amp, 'target_duty_percent': duty,
                'stop_s': 0.002, 'condition': 'precharged; full 0-2 ms window saved'}
        dest = HERE / f'{case}_resupply_frozen_metrics.json'
        result = json.loads(dest.read_text(encoding='utf-8')) if dest.exists() else _measure_patched(spec, RUNTIME / (tag + '.raw'))
        dest.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        results.append(result)
        print(json.dumps({
            'case': case, 'tag': tag,
            'last_five_start_ms': round(result['last_five_start_s'] * 1e3, 6),
            'complete_input_cycles': result['complete_input_cycles'],
            'vin_vpp': round(result['nodes']['V(v1)']['robust_vpp'], 6),
            'vout_vpp': round(result['nodes']['V(v2)']['robust_vpp'], 6),
            'fout': round(result['output_frequency_hz'], 3),
            'duty_err_pp': round(result['output_minus_input_duty_pp'], 4),
            'screen_passes': result['repeatability_screen']['passes'],
            'mean_span_percent': round(result['repeatability_screen']['mean_span_percent'], 4),
            'drift_last_mV_per_ms': round(result['drift_windows'][-1]['slope_mV_per_ms'], 3),
        }, ensure_ascii=True))
    (HERE / 'resupply_frozen_summary.json').write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()

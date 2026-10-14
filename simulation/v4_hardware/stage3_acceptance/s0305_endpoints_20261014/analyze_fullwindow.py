"""Measure the full-window (cold-start, no TSTART) S03-05 endpoint resupply runs.

Context
-------
The original S03-05 plan used `tran 2n 5m 4.5m 2n uic` (precharged, TSTART tail).
In the 2026-10-14 evening environment every 5 ms invocation failed or crashed, and
the TSTART-tail form proved unrecoverable by retry. A full-window form
(`tran 2n 2m 0 2n uic`, UIC from zero) DID complete on retry, so the four missing
endpoints were resupplied that way.

These runs are a DIFFERENT measurement condition from the accepted S03-03/S03-04
precharged tail: they start from zero initial conditions and are only 2 ms long.
They are recorded separately and must not be merged into the precharged 5 ms
comparison table. What they legitimately establish is that the engine CAN produce
these four endpoint waveforms, plus the input/output amplitude, frequency and duty
relationships over a settled late window.

Run: python -X utf8 analyze_fullwindow.py
"""
from pathlib import Path
import hashlib
import json
import numpy as np

HERE = Path(__file__).resolve().parent
import sys
sys.path.insert(0, str(HERE.parent))
from measure_stage3 import read_raw, crossings  # noqa: E402

RUNTIME = Path('D:/ms_xsp/stage3_acceptance/s0305_endpoints_20261014')
NODES = ['V(v1)', 'V(bb_in)', 'V(bbo)', 'V(v2)']

# Chosen tag per case: the attempt that completed. Retries were required because
# the engine failed intermittently on identical input (see 运行异常记录.md).
SELECTED = {
    'C1': ('C1_1Vpp_D10_5ms_full2ms_r2', 1, 10),
    'C3': ('C3_4Vpp_D10_5ms_full2ms_r3', 4, 10),
    'C6': ('C6_4Vpp_D30_5ms_full2ms_r2', 4, 30),
    'C7': ('C7_3Vpp_D50_5ms_full2ms_r9', 3, 50),
}
# Late window used for the settled comparison, in seconds.
TAIL_START = 1.5e-3


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def measure(tag, target_vpp, target_duty):
    path = RUNTIME / (tag + '.raw')
    names, values = read_raw(path)
    t = values[:, 0]
    header = path.open(encoding='ascii')
    expected_points = None
    for line in header:
        if line.startswith('No. Points:'):
            expected_points = int(line.split(':')[1])
        if line.strip() == 'Values:':
            break
    header.close()
    assert expected_points == len(t), (expected_points, len(t))
    assert abs(t[-1] - 0.002) < 1e-12, t[-1]
    assert t[0] == 0.0, t[0]
    assert np.all(np.isfinite(values))

    mask = t >= TAIL_START
    tt = t[mask]
    summary = {}
    for node in NODES:
        y = values[mask, names.index(node)]
        lo, hi = np.percentile(y, [2, 98])
        summary[node] = {
            'mean_v': float(np.trapezoid(y, tt) / (tt[-1] - tt[0])),
            'robust_vpp': float(hi - lo), 'p02_v': float(lo), 'p98_v': float(hi),
            'raw_vpp': float(np.ptp(y)), 'raw_min_v': float(y.min()), 'raw_max_v': float(y.max()),
        }

    # Input/output frequency and duty over the late window, using the frozen
    # 6.2 definition (2 ns interpolation, own-threshold crossings, complete cycles).
    grid = np.arange(TAIL_START, t[-1], 2e-9)
    vin = np.interp(grid, t, values[:, names.index('V(v1)')])
    vin_level = float(np.mean(np.percentile(vin, [2, 98])))
    up, down = crossings(grid, vin, vin_level)
    periods, duties = [], []
    for start, end in zip(up[:-1], up[1:]):
        falls = down[(down > start) & (down < end)]
        if len(falls) != 1:
            continue
        periods.append(end - start)
        duties.append(100 * (falls[0] - start) / (end - start))

    vout = np.interp(grid, t, values[:, names.index('V(v2)')])
    vout_level = float(np.mean(np.percentile(vout, [2, 98])))
    oup, odown = crossings(grid, vout, vout_level)
    operiods, oduties = [], []
    for start, end in zip(oup[:-1], oup[1:]):
        falls = odown[(odown > start) & (odown < end)]
        if len(falls) != 1:
            continue
        operiods.append(end - start)
        oduties.append(100 * (falls[0] - start) / (end - start))

    result = {
        'tag': tag, 'target_vpp': target_vpp, 'target_duty_percent': target_duty,
        'condition': 'cold start (UIC from zero), full window 0-2 ms, no TSTART tail',
        'tran': 'tran 2n 2m 0 2n uic',
        'raw_path': str(path), 'raw_sha256': digest(path), 'raw_bytes': path.stat().st_size,
        'points': len(t), 'saved_start_s': float(t[0]), 'saved_end_s': float(t[-1]),
        'median_step_s': float(np.median(np.diff(t))), 'max_step_s': float(np.max(np.diff(t))),
        'tail_start_s': TAIL_START, 'nodes': summary,
        'input_frequency_hz': float(1 / np.mean(periods)) if periods else None,
        'input_duty_percent': float(np.mean(duties)) if duties else None,
        'input_complete_cycles': len(periods),
        'output_frequency_hz': float(1 / np.mean(operiods)) if operiods else None,
        'output_duty_percent': float(np.mean(oduties)) if oduties else None,
        'output_complete_cycles': len(operiods),
        'output_crossing_level_v': vout_level,
    }
    result['robust_gain'] = summary['V(v2)']['robust_vpp'] / summary['V(v1)']['robust_vpp']
    result['frequency_error_percent'] = (
        (result['output_frequency_hz'] / 20000 - 1) * 100 if result['output_frequency_hz'] else None
    )
    return result


def main():
    results = []
    for case, spec in SELECTED.items():
        if spec is None:
            continue
        tag, amp, duty = spec
        dest = HERE / f'{case}_full2ms_metrics.json'
        status = HERE / f'{tag}_status.json'
        if not status.exists() or json.loads(status.read_text(encoding='utf-8-sig'))['status'] != 'COMPLETED':
            print(json.dumps({'case': case, 'tag': tag, 'skipped': 'not COMPLETED'}))
            continue
        result = json.loads(dest.read_text(encoding='utf-8')) if dest.exists() else measure(tag, amp, duty)
        result['case'] = case
        dest.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        results.append(result)
        print(json.dumps({'case': case, 'tag': tag,
                          'vin_vpp': round(result['nodes']['V(v1)']['robust_vpp'], 6),
                          'vout_vpp': round(result['nodes']['V(v2)']['robust_vpp'], 6),
                          'fout': round(result['output_frequency_hz'], 3),
                          'din': round(result['input_duty_percent'], 3),
                          'dout': round(result['output_duty_percent'], 3)}, ensure_ascii=True))
    (HERE / 'fullwindow_summary.json').write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()

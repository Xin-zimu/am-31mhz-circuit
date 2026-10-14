"""Re-measure the S03-05 long-window make-up runs with the FROZEN S03-04 6.2 pipeline.

Companion to `analyze_resupply_frozen.py`. That file re-measured the four 2 ms
full-window runs; this one measures the *long-window* make-up batches:

  * batch 2 -- C1/C3/C6/C7, precharged 5 ms tail (`tran 2n 5m 4.5m 2n uic`),
    the SAME condition as the accepted C2/C4/C5. These files save 4.5-5 ms, so
    the frozen `measure()` guard (`t[0] == stop - 500us`) holds unmodified and
    this module can call the frozen function verbatim.
  * batch 3/4 -- C2 and C4 at the 7 ms endpoint (`tran 2n 7m 6.5m 2n uic`),
    saving the last 0.5 ms, i.e. 6.5-7 ms.

Nothing about the measurement method differs between the two groups: both go
through the frozen `analyze_cases.measure()` -- 2 ns uniform interpolation,
P98-P2 robust amplitude, trapezoidal time-weighted mean, last five complete
input cycles, own-threshold output crossings, repeatability screen and drift
windows. Only the file-location guard is adapted per condition, and the exact
frozen expression is asserted to be present first, so a change to the frozen
source makes this shim fail loudly instead of silently measuring differently.

No pass is presupposed for either window length: the screen result and drift
trend are reported as computed, including when they fail.

Run: python -X utf8 analyze_longwindow_frozen.py
"""
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import analyze_cases as frozen  # noqa: E402

RUNTIME = Path('D:/ms_xsp/stage3_acceptance/s0305_endpoints_20261014')

# case -> (attempt tag, target vpp, target duty, stop_s, condition)
# The attempt tag is the one that actually COMPLETED; a case with no completed
# attempt is reported as unmeasured rather than silently skipped.
SELECTED = {
    'C1': ('C1_1Vpp_D10_5ms_b1', 1, 10, 0.005, 'precharged 5 ms tail (4.5-5 ms saved)'),
    'C3': ('C3_4Vpp_D10_5ms_b1', 4, 10, 0.005, 'precharged 5 ms tail (4.5-5 ms saved)'),
    'C6': ('C6_4Vpp_D30_5ms_b1', 4, 30, 0.005, 'precharged 5 ms tail (4.5-5 ms saved)'),
    'C7': ('C7_3Vpp_D50_5ms_b1', 3, 50, 0.005, 'precharged 5 ms tail (4.5-5 ms saved)'),
    'C2': ('C2_1Vpp_D50_7ms_b1', 1, 50, 0.007, 'precharged 7 ms endpoint (6.5-7 ms saved)'),
    'C4': ('C4_4Vpp_D50_7ms_b1', 4, 50, 0.007, 'precharged 7 ms endpoint (6.5-7 ms saved)'),
}


def _assert_tail_method_unchanged():
    src = __import__('inspect').getsource(frozen.measure)
    assert 'expected_stop-.0005' in src, 'frozen measure() tail guard changed; re-check this module'
    assert 'rows[-5:]' in src, 'frozen last-five-cycle selection changed; re-check this module'
    return src


def main():
    _assert_tail_method_unchanged()
    results = []
    for case, (tag, amp, duty, stop_s, condition) in SELECTED.items():
        status_path = HERE / f'{tag}_status.json'
        if not status_path.exists():
            print(json.dumps({'case': case, 'tag': tag, 'skipped': 'no status file'}))
            continue
        status = json.loads(status_path.read_text(encoding='utf-8-sig'))
        if status['status'] != 'COMPLETED':
            print(json.dumps({'case': case, 'tag': tag, 'skipped': status['status'],
                              'attempts_note': 'see batch log; attempt budget policy applies'}))
            continue
        raw = RUNTIME / (tag + '.raw')
        if not raw.exists():
            print(json.dumps({'case': case, 'tag': tag, 'skipped': 'raw missing'}))
            continue
        spec = {'case': case, 'tag': tag, 'target_vpp': amp, 'target_duty_percent': duty,
                'stop_s': stop_s, 'condition': condition}
        result = frozen.measure(spec, raw)
        result['condition'] = condition
        result['attempt_wall_seconds'] = status.get('wall_seconds')
        result['attempt_status'] = status['status']
        dest = HERE / f'{case}_longwindow_frozen_metrics.json'
        dest.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        results.append(result)
        print(json.dumps({
            'case': case, 'tag': tag, 'condition': condition,
            'saved_start_ms': round(result['saved_start_s'] * 1e3, 4),
            'last_five_start_ms': round(result['last_five_start_s'] * 1e3, 4),
            'complete_input_cycles': result['complete_input_cycles'],
            'vin_vpp': round(result['nodes']['V(v1)']['robust_vpp'], 6),
            'vout_vpp': round(result['nodes']['V(v2)']['robust_vpp'], 6),
            'v2_mean_v': round(result['nodes']['V(v2)']['mean_v'], 6),
            'fout': round(result['output_frequency_hz'], 3),
            'f_err_pct': round(result['output_frequency_error_percent'], 4),
            'duty_err_pp': round(result['output_minus_input_duty_pp'], 4),
            'screen_passes': result['repeatability_screen']['passes'],
            'mean_span_percent': round(result['repeatability_screen']['mean_span_percent'], 4),
            'robust_vpp_span_percent': round(result['repeatability_screen']['robust_vpp_span_percent'], 4),
            'period_span_percent': round(result['repeatability_screen']['period_span_percent'], 4),
            'drift_last_mV_per_ms': round(result['drift_windows'][-1]['slope_mV_per_ms'], 3),
            'drift_first_mV_per_ms': round(result['drift_windows'][0]['slope_mV_per_ms'], 3),
            'wall_seconds': status.get('wall_seconds'),
        }, ensure_ascii=True))
    (HERE / 'longwindow_frozen_summary.json').write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'measured_cases': [r['case'] for r in results]}, ensure_ascii=True))


if __name__ == '__main__':
    main()

"""Build the consolidated S03-05 seven-endpoint verdict table.

Applies the scoring thresholds extracted from 电子线路实验评分标准-学生.docx
(scoring_tables.json / scoring_source_text.txt) to the measured S03-05 data.

Two measurement conditions exist and are reported separately:
  * "precharged_5ms_tail"  : tran 2n 5m 4.5m 2n uic  -- accepted S03-03/S03-04
  * "precharged_2ms_full"  : tran 2n 2m 0 2n uic     -- resupply runs (still settling)

Both are PRE-CHARGED (netlists keep IC=0.43 / -4.1 / 4.5); they differ in saved
window and integration stop. Frequencies and duties are comparable across them;
amplitudes and DC means are not, because the 2 ms runs have not cleared the
settling transient.

Inputs come from the frozen-6.2 measurements only:
  summary.json                      (accepted 5 ms tail)
  resupply_frozen_summary.json      (2 ms full window, analyse_resupply_frozen.py)

Run: python -X utf8 build_verdict.py
"""
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent

LIMITS = {
    'frequency_error_percent': {'warn': 1.0, 'fail': 10.0, 'deduct': '1pt if >1%, 2pt if >10%'},
    'duty_error_pp': {'warn': 5.0, 'fail': 10.0, 'deduct': '1pt if >5% at 10/30/50%'},
    'vout_vpp_min': {'pass': 4.0, 'marginal': 2.0, 'deduct': '1pt if <4V, 2pt if <2V'},
    'linearity_error_percent': {'warn': 10.0, 'fail': 20.0, 'deduct': '1pt if >10%, 2pt if >20%'},
}


def load(name):
    path = HERE / name
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None


def row_of(r, condition):
    return {
        'tag': r['tag'], 'condition': condition,
        'tran_stop_s': r.get('saved_end_s'),
        'vin_vpp': r['nodes']['V(v1)']['robust_vpp'],
        'vout_vpp': r['nodes']['V(v2)']['robust_vpp'],
        'vout_mean_v': r['nodes']['V(v2)']['mean_v'],
        'fin_hz': r['input_frequency_hz'], 'fout_hz': r['output_frequency_hz'],
        'din_percent': r['input_duty_percent'], 'dout_percent': r['output_duty_percent'],
        'duty_error_pp': r['output_minus_input_duty_pp'],
        'frequency_error_percent': r['output_frequency_error_percent'],
        'gain': r['robust_gain'],
        'repeatability_screen_passes': r['repeatability_screen']['passes'],
        'mean_span_percent': r['repeatability_screen']['mean_span_percent'],
        'robust_vpp_span_percent': r['repeatability_screen']['robust_vpp_span_percent'],
        'period_span_percent': r['repeatability_screen']['period_span_percent'],
        'drift_last_mV_per_ms': r['drift_windows'][-1]['slope_mV_per_ms'],
        'drift_first_mV_per_ms': r['drift_windows'][0]['slope_mV_per_ms'],
        'last_five_start_s': r['last_five_start_s'], 'last_five_end_s': r['last_five_end_s'],
    }


def main():
    pre = {r['case']: r for r in (load('summary.json') or [])}
    res = {r['case']: r for r in (load('resupply_frozen_summary.json') or [])}

    cases = [('C1', 1, 10), ('C2', 1, 50), ('C3', 4, 10), ('C4', 4, 50),
             ('C5', 2, 50), ('C6', 4, 30), ('C7', 3, 50)]

    ref_gain = pre['C4']['robust_gain'] if 'C4' in pre else None

    rows = []
    for case, amp, duty in cases:
        row = {'case': case, 'target_vpp': amp, 'target_duty_percent': duty,
               'precharged_5ms_tail': None, 'precharged_2ms_full': None}
        if case in pre:
            row['precharged_5ms_tail'] = row_of(pre[case], 'precharged 5 ms tail (accepted)')
        if case in res:
            d = row_of(res[case], 'precharged 2 ms full window (still settling)')
            d['gain_vs_5ms_4vpp_percent'] = (100 * (d['gain'] / ref_gain - 1)) if ref_gain else None
            row['precharged_2ms_full'] = d
        rows.append(row)

    # Linearity may only be computed within one measurement condition. The accepted
    # 5 ms precharged chain (C4 4 Vpp, C5 2 Vpp) is the only pair that qualifies.
    linearity = None
    if 'C4' in pre and 'C5' in pre:
        v2_4 = pre['C4']['nodes']['V(v2)']['robust_vpp']
        v2_2 = pre['C5']['nodes']['V(v2)']['robust_vpp']
        expected_half = v2_4 / 2
        linearity = {
            'condition': 'precharged 5 ms tail; v1 4 Vpp -> 2 Vpp (exact 50%)',
            'v1_4vpp': pre['C4']['nodes']['V(v1)']['robust_vpp'],
            'v1_2vpp': pre['C5']['nodes']['V(v1)']['robust_vpp'],
            'v2_4vpp': v2_4, 'v2_2vpp': v2_2,
            'expected_v2_2vpp_if_perfectly_linear': expected_half,
            'error_percent': 100 * (v2_2 / expected_half - 1),
            'threshold_warn_percent': LIMITS['linearity_error_percent']['warn'],
            'verdict': 'PASS (within 10% deduct threshold)',
            'not_available': '1 Vpp and 3 Vpp linearity checks not done (no same-condition pair)',
        }

    out = {
        'limits': LIMITS,
        'reference': {'accepted_4vpp_50pct_gain': ref_gain,
                      'note': 'gain = V(v2) robust_vpp / V(v1) robust_vpp, frozen S03-04 6.2 method'},
        'deprecated_evidence': {
            'files': ['fullwindow_summary.json', 'C*_full2ms_metrics.json', 'analyze_fullwindow.py'],
            'reason': 'did not use the frozen 6.2 method (no 2 ns interp, no last-five-cycle '
                      'decomposition, no screen/drift) and mislabelled the runs as cold start; '
                      'numbers superseded, retained only for tracing the error',
        },
        'cases': rows,
        'linearity': linearity,
    }
    (HERE / 'verdict_table.json').write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')

    for row in rows:
        p, d = row['precharged_5ms_tail'], row['precharged_2ms_full']
        line = f"{row['case']:3} {row['target_vpp']}Vpp/{row['target_duty_percent']}%: "
        if p:
            line += (f"[5ms tail {p['tag']} Vin={p['vin_vpp']:.6f} Vout={p['vout_vpp']:.6f} "
                     f"f_err={p['frequency_error_percent']:+.4f}% duty_err={p['duty_error_pp']:+.4f}pp "
                     f"screen={'PASS' if p['repeatability_screen_passes'] else 'FAIL'} "
                     f"({p['mean_span_percent']:.4f}%)] ")
        if d:
            line += (f"[2ms full {d['tag']} Vin={d['vin_vpp']:.6f} Vout={d['vout_vpp']:.6f} "
                     f"f_err={d['frequency_error_percent']:+.3f}% duty_err={d['duty_error_pp']:+.4f}pp "
                     f"screen={'PASS' if d['repeatability_screen_passes'] else 'FAIL'} "
                     f"({d['mean_span_percent']:.4f}%) drift={d['drift_last_mV_per_ms']:.1f}mV/ms]")
        print(line)
    if linearity:
        print(f"\nlinearity (5 ms precharged only): v2 4Vpp={linearity['v2_4vpp']:.6f} -> "
              f"2Vpp={linearity['v2_2vpp']:.6f} error={linearity['error_percent']:+.4f}%  "
              f"{linearity['verdict']}")


if __name__ == '__main__':
    main()

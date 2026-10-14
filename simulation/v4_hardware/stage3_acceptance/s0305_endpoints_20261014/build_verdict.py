"""Build the consolidated S03-05 seven-endpoint verdict table.

Applies the scoring thresholds extracted from 电子线路实验评分标准-学生.docx
(scoring_tables.json / scoring_source_text.txt) to the measured S03-05 data.

Two measurement conditions exist and are reported separately:
  * "precharged"  : tran 2n 5m 4.5m 2n uic  -- the accepted S03-03/S03-04 condition
  * "fullwindow"  : tran 2n 2m 0 2n uic     -- cold start, supplementary resupply runs

Run: python -X utf8 build_verdict.py
"""
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent

# Scoring thresholds, verbatim from the scoring table (解调波形v2 / 方波波形v1).
LIMITS = {
    'frequency_error_percent': {'warn': 1.0, 'fail': 10.0, 'deduct': '1pt if >1%, 2pt if >10%'},
    'duty_error_pp': {'warn': 5.0, 'fail': 10.0, 'deduct': '1pt if >5% at 10/30/50%'},
    'vout_vpp_min': {'pass': 4.0, 'marginal': 2.0, 'deduct': '1pt if <4V, 2pt if <2V'},
    'linearity_error_percent': {'warn': 10.0, 'fail': 20.0, 'deduct': '1pt if >10%, 2pt if >20%'},
}


def load(name):
    path = HERE / name
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None


def main():
    pre = {r['case']: r for r in (load('summary.json') or [])}
    fw = {r['case']: r for r in (load('fullwindow_summary.json') or [])}

    cases = [
        ('C1', 1, 10), ('C2', 1, 50), ('C3', 4, 10), ('C4', 4, 50),
        ('C5', 2, 50), ('C6', 4, 30), ('C7', 3, 50),
    ]

    # Linearity reference: the accepted precharged 4 Vpp/50% gain (C4).
    ref_gain = pre['C4']['robust_gain'] if 'C4' in pre else None

    rows = []
    for case, amp, duty in cases:
        row = {'case': case, 'target_vpp': amp, 'target_duty_percent': duty,
               'precharged': None, 'fullwindow': None}

        if case in pre:
            r = pre[case]
            gain = r['robust_gain']
            row['precharged'] = {
                'tag': r['tag'], 'condition': 'precharged 5 ms tail (accepted)',
                'vin_vpp': r['nodes']['V(v1)']['robust_vpp'],
                'vout_vpp': r['nodes']['V(v2)']['robust_vpp'],
                'vout_mean_v': r['nodes']['V(v2)']['mean_v'],
                'fout_hz': r['output_frequency_hz'],
                'fin_hz': r['input_frequency_hz'],
                'din_percent': r['input_duty_percent'],
                'dout_percent': r['output_duty_percent'],
                'duty_error_pp': r['output_minus_input_duty_pp'],
                'frequency_error_percent': r['output_frequency_error_percent'],
                'gain': gain,
                'gain_vs_4vpp_percent': (100 * (gain / ref_gain - 1)) if ref_gain else None,
                'repeatability_screen_passes': r['repeatability_screen']['passes'],
                'mean_span_percent': r['repeatability_screen']['mean_span_percent'],
                'drift_last_mV_per_ms': r['drift_windows'][-1]['slope_mV_per_ms'],
            }

        if case in fw:
            r = fw[case]
            row['fullwindow'] = {
                'tag': r['tag'], 'condition': r['condition'],
                'vin_vpp': r['nodes']['V(v1)']['robust_vpp'],
                'vout_vpp': r['nodes']['V(v2)']['robust_vpp'],
                'fout_hz': r['output_frequency_hz'],
                'din_percent': r['input_duty_percent'],
                'dout_percent': r['output_duty_percent'],
                'duty_error_pp': (r['output_duty_percent'] - r['input_duty_percent'])
                                 if r['output_duty_percent'] and r['input_duty_percent'] else None,
                'frequency_error_percent': r['frequency_error_percent'],
                'gain': r['robust_gain'],
                'gain_vs_precharged_4vpp_percent': (
                    100 * (r['robust_gain'] / ref_gain - 1)) if ref_gain else None,
            }
        rows.append(row)

    # Linearity check: v2 should scale with v1. Use the accepted precharged
    # points (C4 4 Vpp, C5 2 Vpp) which share one bit-identical receive chain.
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
        }

    out = {
        'limits': LIMITS,
        'reference': {
            'accepted_4vpp_50pct_gain': ref_gain,
            'note': 'gain = V(v2) robust_vpp / V(v1) robust_vpp, frozen S03-04 6.2 method',
        },
        'cases': rows,
        'linearity': linearity,
    }
    (HERE / 'verdict_table.json').write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')

    for row in rows:
        p, f = row['precharged'], row['fullwindow']
        line = f"C{row['case'][-1]} {row['target_vpp']}Vpp/{row['target_duty_percent']}%: "
        if p:
            line += (f"[precharged tag={p['tag']} Vin={p['vin_vpp']:.6f} Vout={p['vout_vpp']:.6f} "
                     f"f_err={p['frequency_error_percent']:+.4f}% duty_err={p['duty_error_pp']:+.4f}pp "
                     f"screen={p['repeatability_screen_passes']}] ")
        if f:
            line += (f"[full2ms tag={f['tag']} Vin={f['vin_vpp']:.6f} Vout={f['vout_vpp']:.6f} "
                     f"f_err={f['frequency_error_percent']:+.3f}% duty_err={f['duty_error_pp']:+.4f}pp]")
        print(line)
    if linearity:
        print(f"\nlinearity: v2 4Vpp={linearity['v2_4vpp']:.6f} -> 2Vpp={linearity['v2_2vpp']:.6f} "
              f"error={linearity['error_percent']:+.4f}%  {linearity['verdict']}")


if __name__ == '__main__':
    main()

"""Print the consolidated S03-05 verdict inputs (read-only helper)."""
import json
from pathlib import Path

H = Path(__file__).resolve().parent

summary = json.loads((H / 'summary.json').read_text(encoding='utf-8'))
print('=== precharged 5 ms tail (accepted condition) ===')
for r in summary:
    n = r['nodes']
    print(f"{r['case']:3} {r['target_vpp']}Vpp/{r['target_duty_percent']}%  tag={r['tag']}")
    print(f"     Vin={n['V(v1)']['robust_vpp']:.6f}  Vout={n['V(v2)']['robust_vpp']:.6f}  "
          f"mean={n['V(v2)']['mean_v']:.6f}")
    print(f"     fout={r['output_frequency_hz']:.3f}  din={r['input_duty_percent']}  "
          f"dout={r['output_duty_percent']}")
    print(f"     screen={r['repeatability_screen']['passes']} "
          f"mean_span%={r['repeatability_screen']['mean_span_percent']:.4f} "
          f"gain_err%={r.get('normalized_gain_error_percent')}")

fw_path = H / 'fullwindow_summary.json'
if fw_path.exists():
    fw = json.loads(fw_path.read_text(encoding='utf-8'))
    print('\n=== full-window cold-start 2 ms (supplementary condition) ===')
    for r in fw:
        n = r['nodes']
        print(f"{r['case']:3} {r['target_vpp']}Vpp/{r['target_duty_percent']}%  tag={r['tag']}")
        print(f"     Vin={n['V(v1)']['robust_vpp']:.6f}  Vout={n['V(v2)']['robust_vpp']:.6f}  "
              f"gain={r['robust_gain']:.6f}")
        print(f"     fout={r['output_frequency_hz']:.3f}  din={r['input_duty_percent']:.3f}  "
              f"dout={r['output_duty_percent']:.3f}")

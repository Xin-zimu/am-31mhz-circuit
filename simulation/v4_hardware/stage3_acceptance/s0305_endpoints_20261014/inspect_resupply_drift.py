"""Inspect drift trends of the four resupply runs under the frozen 6.2 method."""
import json
from pathlib import Path

H = Path(__file__).resolve().parent
for c in ['C1', 'C3', 'C6', 'C7']:
    p = H / f'{c}_resupply_frozen_metrics.json'
    if not p.exists():
        continue
    r = json.loads(p.read_text(encoding='utf-8'))
    print(f"--- {c} (2 ms precharged full window, {r['complete_input_cycles']} complete input cycles) ---")
    print(f"  last-five window : {r['last_five_start_s']*1e3:.4f} -> {r['last_five_end_s']*1e3:.4f} ms")
    print(f"  V2 last-five mean: {r['nodes']['V(v2)']['mean_v']:.6f} V")
    print(f"  V2 robust_vpp    : {r['nodes']['V(v2)']['robust_vpp']:.6f} Vpp")
    print(f"  drift windows    : {[round(d['slope_mV_per_ms'], 1) for d in r['drift_windows']]} mV/ms")
    print(f"  drift all-tail   : {r['drift_all_tail']['slope_mV_per_ms']:.1f} mV/ms "
          f"over {r['drift_all_tail']['cycles']} cycles")
    print(f"  screen passes    : {r['repeatability_screen']['passes']} "
          f"(mean {r['repeatability_screen']['mean_span_percent']:.4f}%, "
          f"amp {r['repeatability_screen']['robust_vpp_span_percent']:.4f}%, "
          f"period {r['repeatability_screen']['period_span_percent']:.4f}%)")

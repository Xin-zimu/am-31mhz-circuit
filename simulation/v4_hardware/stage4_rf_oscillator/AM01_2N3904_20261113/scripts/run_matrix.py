# -*- coding: utf-8 -*-
"""Full AM-01 matrix: 4 amplitudes x 3 duty cycles x 2 specified loads."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import am01_lib as L

PARAMS = {"rbb": 62e3, "re": 1200.0, "rin": 2200.0, "rsh": 10.0, "cin": 1e-9}
AMPS = [1.0, 2.0, 3.0, 4.0]
DUTIES = [0.1, 0.3, 0.5]
LOADS = [2000.0, 10000.0]
OUT = L.RESULTS / "matrix_final.json"


def main():
    records = []
    for load in LOADS:
        for duty in DUTIES:
            for amp in AMPS:
                tag = f"m{int(load/1000)}k_d{round(duty*100):02d}_a{amp:g}"
                print(f"RL={load:g} D={duty:.0%} A={amp:g} Vpp")
                item = L.evaluate_case(PARAMS, amp, duty, load, tag,
                                       keep_raw=(load == 2000 and duty == 0.5 and amp == 4),
                                       verbose=False)
                records.append(item)
                print(f"  m={100*item['modulation_index']:.2f}% "
                      f"step={item['envelope_step_vpp']:.5f} "
                      f"Q1Vce={item['q1_vce_low_v']:.3f}/{item['q1_vce_high_v']:.3f}")

    linearity = {}
    for load in LOADS:
        for duty in DUTIES:
            subset = [r for r in records if r["load_ohm"] == load
                      and abs(r["duty_pct"] - 100 * duty) < 1e-9]
            reference = next(r for r in subset if r["amp_vpp"] == 4.0)["envelope_step_vpp"]
            errors = []
            for r in subset:
                expected = r["amp_vpp"] / 4.0 * reference
                errors.append(abs(r["envelope_step_vpp"] / expected - 1.0))
            key = f"rl{int(load)}_d{round(duty*100):02d}"
            linearity[key] = {
                "max_error_pct": 100.0 * max(errors),
                "error_by_amp_pct": {r["amp_vpp"]: 100.0 * e for r, e in zip(subset, errors)},
            }

    def point(load, amp, duty):
        return next(r for r in records if r["load_ohm"] == load
                    and r["amp_vpp"] == amp and abs(r["duty_pct"] - 100 * duty) < 1e-9)

    key_points = [point(load, 4.0, 0.5) for load in LOADS]
    checks = {
        "modulation_index_4v_50pct_within_23_27": all(
            0.23 <= r["modulation_index"] <= 0.27 for r in key_points),
        "linearity_max_error_le_5pct_both_loads": all(
            v["max_error_pct"] <= 5.0 for v in linearity.values()),
        "all_envelope_steps_positive": all(r["envelope_step_vpp"] > 0 for r in records),
        "all_envelope_duty_error_le_5pp": all(
            abs(r["envelope_duty_pct"] - r["duty_pct"]) <= 5.0 for r in records),
        "all_q1_q2_vce_above_0p3v": all(
            min(r["q1_vce_high_v"], r["q1_vce_low_v"],
                r["q2_vce_high_v"], r["q2_vce_low_v"]) > 0.3 for r in records),
        "no_rf_supply_clipping": all(
            r["rf_out_max_v"] < 4.95 for r in records),
        "coupling_residual_below_1mv": all(
            abs(r["final_coupling_residual_mv"]) < 1.0 for r in records),
        "period_repeat_below_0p1pct": all(
            abs(r["period_to_period_high_pct"]) < 0.1
            and abs(r["period_to_period_low_pct"]) < 0.1 for r in records),
    }
    output = {
        "selected_parameters": PARAMS,
        "conditions": {
            "carrier": "31 MHz, 2 Vpp into the designed input attenuator",
            "amplitudes_vpp": AMPS,
            "duties_pct": [100 * d for d in DUTIES],
            "loads_ohm": LOADS,
            "parallel_load_capacitance_pf": 10,
        },
        "linearity": linearity,
        "checks": checks,
        "all_checks_pass": all(checks.values()),
        "records": records,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nLinearity:")
    for key, value in linearity.items():
        print(f"  {key}: {value['max_error_pct']:.3f}%")
    print("Checks:")
    for key, value in checks.items():
        print(f"  {key}: {value}")
    print("ALL PASS:", output["all_checks_pass"])
    print("Wrote", OUT)


if __name__ == "__main__":
    main()

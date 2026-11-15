# -*- coding: utf-8 -*-
"""AM-02.3 step 4: full-cascade check of the candidate second stages.

AM-01 (frozen) -> AM-02.2 scheme A (frozen) -> second stage -> 50 ohm || 10 pF.
Every candidate is run at 4 Vpp / 50 % first; only the ones that reach the
2.0 Vpp target are carried into the duty / level matrix.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import am023_lib as M  # noqa: E402

CANDS = {
    "S1_ef_ce": ("S1", {"rbat": 2.7e3, "rbab": 1.1e3, "rax": 2.0,
                        "rb1": 100e3, "rb2": 100e3, "ref": 900.0,
                        "ltank": 1.2e-6, "ct1": 22e-12, "ct2": 68e-12}),
    "S2_ce_tank": ("S2", {"rbat": 2.7e3, "rbab": 1.1e3, "rax": 2.0,
                          "ltank": 1.2e-6, "ct1": 22e-12, "ct2": 68e-12}),
    "S3_ce_rfc_ef": ("S3", {"rbat": 2.7e3, "rbab": 1.1e3, "rax": 2.0,
                            "lrfc": 2.2e-6, "reb": 180.0}),
    "S4_cascode": ("S4", {"rbat": 2.2e3, "rbab": 1.5e3, "rax": 5.0,
                          "rbx1": 1e3, "rbx2": 3.9e3,
                          "ltank": 1.2e-6, "ct1": 22e-12, "ct2": 82e-12}),
}


def run_one(label, top, stage, amp=4.0, duty=0.5):
    print(f"\n=== {label} ({top}) {amp:g} Vpp duty {duty:.0%} ===")
    solve = M.solve_cap(top, stage, amp, duty, tag=f"{label}_d{int(duty*100)}")
    state = dict(solve["op"]["nodes"])
    state["b2ac"] = -amp * duty + solve["vcap"]
    name = f"{label}_a{amp:g}_d{int(duty*100)}"
    M.run(name, M.build(top, stage, amp, duty, state=state, stop_us=128.0,
                        raw_name=name + ".raw"), timeout=900)
    m = M.measure(M.RESULTS / (name + ".raw"), top, duty, p0_us=75.0, load_r=50.0)
    m.update({"label": label, "topology": top, "amp_vpp": amp,
              "cap_v": solve["vcap"], "cap_residual_mv": 1e3 * solve["residual"],
              "netlist": str(M.NETLISTS / (name + ".cir"))})
    Path(M.RESULTS / (name + ".raw")).unlink(missing_ok=True)
    print(f"  out {m['vpp_high']*1e3:.1f} / {m['vpp_low']*1e3:.1f} mVpp  "
          f"m={100*m['modulation_index']:.2f}%  THD {m['thd_high_pct']:.2f}/"
          f"{m['thd_low_pct']:.2f}%  P={m['supply_mw']:.1f} mW  "
          f"ca {m['ca_min_v']:.2f}-{m['ca_max_v']:.2f} V  "
          f"VCE {m['qa_vce_high_v']:.2f}/{m['qa_vce_low_v']:.2f} V")
    return m


def main():
    rows = []
    for label, (top, stage) in CANDS.items():
        try:
            rows.append(run_one(label, top, stage))
        except Exception as exc:  # keep going, report the failure
            print(f"  FAILED: {exc}")
            rows.append({"label": label, "topology": top, "error": str(exc)})
    (M.RESULTS / "cascade_candidates.json").write_text(
        json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nlabel            high Vpp  low Vpp   m %    THD%   P mW")
    for r in rows:
        if "error" in r:
            print(f"{r['label']:<16} FAILED")
        else:
            print(f"{r['label']:<16} {r['vpp_high']:7.3f} {r['vpp_low']:8.3f} "
                  f"{100*r['modulation_index']:6.2f} {r['thd_high_pct']:6.2f} "
                  f"{r['supply_mw']:6.1f}")


if __name__ == "__main__":
    main()

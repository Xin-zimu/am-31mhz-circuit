# -*- coding: utf-8 -*-
"""AM-02.3 step 5: input-match sweep of S6 measured in the real cascade.

The stand-alone AC sweep cannot judge an input match, because its source is
ideal (0 ohm). The only honest test is the loaded cascade: AM-01 (frozen) ->
scheme A (frozen, ~150 ohm) -> S6. The coupling capacitor is already at its
solved periodic state, so one transient per point is enough.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import am023_lib as M  # noqa: E402

BASE = dict(M.default_stage("S6"), rax=5.0, rea=39.0, rbat=2.2e3, rbab=1.1e3,
            ltank=0.47e-6, ct1=100e-12, ct2=56e-12)
LM = [0.68e-6, 0.82e-6, 1.0e-6, 1.2e-6, 1.5e-6]
CM = [47e-12, 68e-12, 100e-12, 150e-12]


def main():
    rows = []
    for lm in LM:
        for cm in CM:
            st = dict(BASE, lm=lm, cm=cm)
            name = f"m6_{int(lm*1e9)}_{int(cm*1e12)}"
            op = M.op_state("S6", st, tag="op_m6")
            state = dict(op["nodes"])
            state["b2ac"] = -2.0 + M.VCAP_REF
            try:
                M.run(name, M.build("S6", st, 4.0, 0.5, state=state, stop_us=88.0,
                                    raw_name=name + ".raw"), timeout=600)
                m = M.measure(M.RESULTS / (name + ".raw"), "S6", 0.5,
                              p0_us=35.0, load_r=50.0)
            except RuntimeError as exc:
                print("skip", name, exc)
                continue
            m.update({"lm_uh": lm * 1e6, "cm_pf": cm * 1e12})
            rows.append(m)
            Path(M.RESULTS / (name + ".raw")).unlink(missing_ok=True)
            print(f"LM={lm*1e6:.2f}uH CM={cm*1e12:.0f}pF  out={m['vpp_high']*1e3:7.1f}"
                  f" / {m['vpp_low']*1e3:7.1f} mVpp  m={100*m['modulation_index']:5.2f}%"
                  f"  THD={m['thd_high_pct']:5.2f}%  P={m['supply_mw']:6.1f} mW"
                  f"  ca={m['ca_min_v']:.2f}-{m['ca_max_v']:.2f}V")

    rows.sort(key=lambda r: -r["vpp_high"])
    (M.RESULTS / "s6_match_sweep.json").write_text(
        json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nbest:")
    for r in rows[:5]:
        print(f"  LM={r['lm_uh']:.2f}uH CM={r['cm_pf']:.0f}pF -> {r['vpp_high']:.3f} Vpp, "
              f"m={100*r['modulation_index']:.1f}%, THD={r['thd_high_pct']:.1f}%")


if __name__ == "__main__":
    main()

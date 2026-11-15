# -*- coding: utf-8 -*-
"""AM-02.3 step 8: repeat the 50 % points on 2 kOhm || 10 pF.

The first matrix forgot to pass the load into the stage dictionary, so every
row was actually 50 ohm. This run fixes that and is the only 2 kOhm evidence.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import am023_lib as M  # noqa: E402

CONFIGS = {
    "S3": dict(rbat=2.7e3, rbab=1.1e3, rax=2.0, rea=100.0, lrfc=2.2e-6, reb=180.0),
    "S6": dict(rbat=2.2e3, rbab=1.1e3, rax=8.0, rea=39.0, lm=0.82e-6, cm=68e-12,
               rser=10.0, ltank=0.47e-6, ct1=100e-12, ct2=56e-12),
}
rows = []
for name, st in CONFIGS.items():
    for load in (50.0, 2000.0):
        for amp in (1.0, 2.0, 3.0, 4.0):
            stage = dict(st, rload=load)
            tag = f"ld2_{name}_{int(load)}_{int(amp)}"
            sol = M.solve_cap(name, stage, amp, 0.5, tag=tag, stop_us=45.0, max_iter=4)
            state = dict(sol["op"]["nodes"])
            state["b2ac"] = -amp * 0.5 + sol["vcap"]
            M.run(tag, M.build(name, stage, amp, 0.5, state=state, stop_us=128.0,
                               raw_name=tag + ".raw"))
            m = M.measure(M.RESULTS / (tag + ".raw"), name, 0.5, p0_us=75.0, load_r=load)
            Path(M.RESULTS / (tag + ".raw")).unlink(missing_ok=True)
            m.update(config=name, amp_vpp=amp, cap_v=sol["vcap"],
                     cir_sha256=M.sha256(M.NETLISTS / (tag + ".cir")))
            rows.append(m)
            print(f"{name} {load:6.0f}ohm {amp:g}Vpp -> {m['vpp_high']*1e3:7.1f}/"
                  f"{m['vpp_low']*1e3:7.1f} mVpp m={100*m['modulation_index']:6.2f}% "
                  f"THD={m['thd_high_pct']:5.2f}% P={m['supply_mw']:6.1f}mW", flush=True)
(M.RESULTS / "load2k_matrix.json").write_text(
    json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

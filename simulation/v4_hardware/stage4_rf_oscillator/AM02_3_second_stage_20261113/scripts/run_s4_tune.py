# -*- coding: utf-8 -*-
"""AM-02.3 step 3: tune the cascode second stage at 31 MHz.

Fixed bias, swept tank (L, CT1, CT2). Selection criteria, in order:
  1. gain peak close to 31 MHz (a detuned tank wastes the whole budget);
  2. highest gain at 31 MHz into 50 ohm || 10 pF;
  3. input impedance large enough not to destroy scheme A's 150 ohm drive.
"""
import itertools
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import am023_lib as M  # noqa: E402

BIAS = {"rbat": 2.2e3, "rbab": 1.5e3, "rax": 5.0, "rea": 100.0,
        "rbx1": 1e3, "rbx2": 3.9e3, "cbx": 100e-9, "ltank": 1.0e-6}
GRID = {
    "ltank": [0.68e-6, 0.82e-6, 1.0e-6, 1.2e-6, 1.5e-6, 1.8e-6],
    "ct1": [12e-12, 15e-12, 18e-12, 22e-12, 27e-12, 33e-12],
    "ct2": [47e-12, 56e-12, 68e-12, 82e-12, 100e-12],
}


def main():
    rows = []
    for l, c1, c2 in itertools.product(GRID["ltank"], GRID["ct1"], GRID["ct2"]):
        st = dict(BIAS, ltank=l, ct1=c1, ct2=c2)
        name = f"tune_L{l*1e6:.2f}_C1{c1*1e12:.0f}_C2{c2*1e12:.0f}".replace(".", "p")
        try:
            M.run(name, M.standalone("S4", st, mode="ac", raw_name=name + ".raw"))
            m, _, _ = M.ac_metrics(M.RESULTS / (name + ".raw"))
        except RuntimeError as exc:
            print("skip", name, exc)
            continue
        m.update({"ltank_uh": l * 1e6, "ct1_pf": c1 * 1e12, "ct2_pf": c2 * 1e12,
                  "f_peak_err_mhz": m["f_peak_mhz"] - 31.0})
        rows.append(m)

    rows.sort(key=lambda r: -r["gain_db"])
    print("\nbest gain at 31 MHz:")
    for r in rows[:10]:
        print(f"  L={r['ltank_uh']:.2f}uH C1={r['ct1_pf']:.0f}p C2={r['ct2_pf']:.0f}p "
              f"G={r['gain_db']:.2f}dB fpk={r['f_peak_mhz']:.2f}MHz "
              f"Zin={r['zin_real']:.1f}{r['zin_imag']:+.1f}j")

    tuned = [r for r in rows if abs(r["f_peak_err_mhz"]) < 0.6]
    tuned.sort(key=lambda r: -r["gain_db"])
    print("\npeak within 0.6 MHz of 31 MHz:")
    for r in tuned[:10]:
        print(f"  L={r['ltank_uh']:.2f}uH C1={r['ct1_pf']:.0f}p C2={r['ct2_pf']:.0f}p "
              f"G={r['gain_db']:.2f}dB fpk={r['f_peak_mhz']:.2f}MHz "
              f"Zin={r['zin_real']:.1f}{r['zin_imag']:+.1f}j")

    (M.RESULTS / "s4_tune.json").write_text(
        json.dumps(rows, indent=1), encoding="utf-8")
    print(f"\n{len(rows)} points -> results/s4_tune.json")


if __name__ == "__main__":
    main()

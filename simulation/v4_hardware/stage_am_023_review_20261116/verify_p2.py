"""Read-only verifier for P2: the antenna measurement procedure and calculator.

Runs the calculator's own self-test (which checks the physics relations and the
uncertainty model against the stage's recorded design values), then checks that
the procedure document and the record template are honest about what is and is
not measured.

    py -3 simulation/v4_hardware/stage_am_023_review_20261116/verify_p2.py
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent   # 2026-11-19：P2 已从根目录移入本目录
A3 = ROOT / "simulation/v4_hardware/stage_am_alt3_20261115"
SCRIPTS = A3 / "scripts"

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  -- {detail}" if detail else ""))
    return bool(ok)


def read(p):
    return Path(p).read_text(encoding="utf-8", errors="replace")


# ------------------------------------------------ 1. calculator self-test
def check_calculator_runs():
    exe = SCRIPTS / "p2_antenna_calculator.py"
    if not check("calculator exists", exe.exists(), str(exe)):
        return
    proc = subprocess.run([sys.executable, str(exe), "--demo"],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=120)
    out = proc.stdout + proc.stderr
    check("calculator self-test exits 0", proc.returncode == 0,
          f"exit={proc.returncode}")
    check("self-test reproduces the recorded 191.57 mV rms", "True" in out
          and "191.57" in out)
    check("self-test recovers L = 2.9572 uH", "2.9572" in out)
    check("self-test separates Vpp from rms", "4.0 Vpp = 1.4142 V rms" in out)
    check("in-band pair is flagged >10x worse", "in-band pair is >10x worse: True" in out)
    check("100/220 pF pair tolerance is sub-1%", "tolerance +-0.36%" in out)
    check("4.7/6.8 pF pair tolerance is ~17%", "tolerance +-16.8%" in out)


# ------------------------------------- 2. calculator internals are correct
def check_calculator_physics():
    sys.path.insert(0, str(SCRIPTS))
    try:
        import p2_antenna_calculator as calc
    except Exception as exc:                     # noqa: BLE001
        check("calculator imports", False, repr(exc))
        return

    check("calculator imports", True)

    # L = 2.9572 uH resonates with 8.913 pF at 31 MHz
    import math
    f = 1 / (2 * math.pi * math.sqrt(2.9572e-6 * 8.913e-12))
    check("design L and C resonate at 31 MHz", abs(f - 31e6) / 31e6 < 1e-3,
          f"{f / 1e6:.4f} MHz")

    # two-capacitor L round-trip
    L_true, c_stray = 2.9572e-6, 3.0e-12
    f1 = 1 / (2 * math.pi * math.sqrt(L_true * (100e-12 + c_stray)))
    f2 = 1 / (2 * math.pi * math.sqrt(L_true * (220e-12 + c_stray)))
    L_got = calc.inductance_two_capacitor(f1, 100e-12, f2, 220e-12)
    check("two-capacitor L round-trip", abs(L_got - L_true) / L_true < 1e-12,
          f"{L_got * 1e6:.4f} uH")

    # uncertainty relation: dC/C = -2 df/f - dL/L
    u = calc.c_uncertainty_pct(0.1, 2.0)
    expected = math.hypot(0.2, 2.0)
    check("quadrature uncertainty uses 2*df/f", abs(u - expected) < 1e-12,
          f"{u:.4f}%")

    # R_total relation
    r = calc.loop_resistance_ohm(1.4142135623730951, 19.156555623822808e-3)
    check("loop resistance reproduces the design 73.824-60 ohm", abs(r - 13.824) < 0.05,
          f"{r:.3f} ohm")

    # absolute-capacitor tolerance drives L tolerance
    cal_a = calc.CoilCalibration("a", 100.0, 220.0, f1, f2)
    cal_b = calc.CoilCalibration("b", 4.7, 6.8,
                                 1 / (2 * math.pi * math.sqrt(L_true * (4.7e-12 + c_stray))),
                                 1 / (2 * math.pi * math.sqrt(L_true * (6.8e-12 + c_stray))))
    check("100/220 pF L tolerance < 1%", cal_a.L_tol_pct < 1.0, f"{cal_a.L_tol_pct:.2f}%")
    check("4.7/6.8 pF L tolerance > 10%", cal_b.L_tol_pct > 10.0, f"{cal_b.L_tol_pct:.2f}%")


# ---------------------------------------- 3. procedure document completeness
def check_procedure_doc():
    doc = HERE / "P2_天线阻抗实测规程.md"
    if not check("P2 procedure doc exists", doc.exists(), str(doc)):
        return
    txt = read(doc)
    must_mention = {
        "never probe the antenna node": "绝不在天线节点接探头",
        "the 18.5 MHz failure mode": "18.5 MHz",
        "+-3% target": "±3%",
        "R_total gets no +-3% verdict": "不设 ±3% 判据",
        "absolute capacitor tolerance": "绝对容差",
        "the 0.36% figure": "±0.36%",
        "the 16.8% figure": "±16.8%",
        "differential residual rule": "残差 > 5%",
        "the three blockers": "阻塞前提",
        "no model values pre-filled": "不得预填模型值",
    }
    for label, needle in must_mention.items():
        check(f"procedure covers {label}", needle in txt)

    # the record template must remain empty
    tpl = A3 / "measurement_record_template.json"
    if check("record template exists", tpl.exists()):
        data = json.loads(read(tpl))
        check("template declares is_measurement = false",
              data.get("is_measurement") is False)
        check("template status says not measured",
              data.get("measurement_status", {}).get("user_confirmed") == "未测")
        ant = data.get("antenna_measurement", {})
        filled = [k for k, v in ant.items() if v is not None]
        check("template antenna fields are all null", not filled, str(filled))
        drv = data.get("driver_measurement", {})
        filled_d = [k for k, v in drv.items() if v is not None]
        check("template driver fields are all null", not filled_d, str(filled_d))


# --------------------------------------------- 4. the stage stays blocked
def check_stage_still_blocked():
    comp = json.loads(read(A3 / "stage_completion.json"))

    # the stage is "executed, erratum done, awaiting technical closure" -- not complete
    check("stage status is the 'not yet closed' wording",
          comp.get("status") == "已执行、勘误完成、待技术闭合", repr(comp.get("status")))
    check("stage records that no bench measurement was performed",
          comp.get("current_review", {}).get("bench_measurement_performed") is False)
    check("stage lists the measured antenna impedance as a pending closure item",
          any("Measured antenna impedance" in s
              for s in comp.get("current_review", {}).get("closure_pending", [])))
    check("stage records the antenna impedance as an open item",
          any("antenna impedance not measured" in s
              for s in comp.get("open_items", [])))
    check("stage keeps 6 m as unverifiable by simulation",
          any("cannot be verified by simulation" in s
              for s in comp.get("open_items", [])))

    doc = read(HERE / "P2_天线阻抗实测规程.md")
    check("procedure states this step is the stage exit condition",
          "出口条件" in doc)

    # the calculator must not have written anything
    check("no new .raw was produced by the calculator",
          not list(SCRIPTS.glob("*.raw")))


def main():
    print("=" * 78)
    print("P2 verification - antenna measurement procedure and calculator")
    print(ROOT)
    print("=" * 78)
    for fn in (check_calculator_runs, check_calculator_physics,
               check_procedure_doc, check_stage_still_blocked):
        print(f"\n-- {fn.__name__} " + "-" * max(0, 58 - len(fn.__name__)))
        try:
            fn()
        except Exception as exc:                # noqa: BLE001
            check(f"{fn.__name__} raised", False, repr(exc))

    npass = sum(1 for ok, _, _ in results if ok)
    nfail = len(results) - npass
    print("\n" + "=" * 78)
    print(f"{npass} passed, {nfail} failed, {len(results)} checks")
    print("=" * 78)
    if nfail:
        print("\nFAILURES:")
        for ok, name, detail in results:
            if not ok:
                print(f"  - {name}  {detail}")
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())

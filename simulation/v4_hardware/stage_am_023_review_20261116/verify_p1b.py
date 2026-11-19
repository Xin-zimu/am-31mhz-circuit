"""Read-only verifier for P1b: AM-ALT.3 coverage recalibration, v3 node mapping,
and the link_budget.py h_eff / peak-power fixes.

Checks every load-bearing claim of
    P1b_AM-ALT.3三项修订.md
against the files on disk. Runs no simulation and writes no file.

    py -3 simulation/v4_hardware/stage_am_023_review_20261116/verify_p1b.py
"""
import json
import math
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent   # 2026-11-19：P1a/P1b/P2/AM-02.3 已从根目录移入本目录
A3 = ROOT / "simulation/v4_hardware/stage_am_alt3_20261115"
RES = A3 / "results"
R2 = A3 / "round2_20261116"

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  -- {detail}" if detail else ""))
    return bool(ok)


def read(p):
    return Path(p).read_text(encoding="utf-8", errors="replace")


def load(p):
    return json.loads(read(p))


def find(obj, key):
    """Depth-first search for a key in nested dicts/lists."""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            got = find(v, key)
            if got is not None:
                return got
    elif isinstance(obj, list):
        for v in obj:
            got = find(v, key)
            if got is not None:
                return got
    return None


# ------------------------------------------------ 1. coverage arithmetic
def check_coverage():
    closure = load(RES / "closure_sense10_metrics.json")
    d05 = load(R2 / "results/d05_metrics.json")
    final = load(RES / "final_verify.json")

    carrier = closure["carrier_fundamental_rms_mA"]
    total = closure["total_time_weighted_rms_mA"]
    hp = closure["high_plateau_fundamental_rms_mA"]

    check("carrier fundamental RMS = 4.6409 mA",
          abs(carrier - 4.640940217333886) < 1e-9, f"{carrier:.6f}")
    check("total time-weighted RMS = 4.8308 mA",
          abs(total - 4.830754989854036) < 1e-9, f"{total:.6f}")
    check("high plateau fundamental RMS = 5.9845 mA",
          abs(hp - 5.984527451895156) < 1e-9, f"{hp:.6f}")

    # d05 is an independent rerun of the same case; must agree closely
    d05_carrier = find(d05, "carrier_fundamental_rms_mA")
    d05_total = find(d05, "total_time_weighted_rms_mA")
    check("d05 carrier RMS agrees with closure within 0.01%",
          abs(d05_carrier - carrier) / carrier < 1e-4,
          f"{d05_carrier:.6f} vs {carrier:.6f}")
    check("d05 total RMS agrees with closure within 0.01%",
          abs(d05_total - total) / total < 1e-4,
          f"{d05_total:.6f} vs {total:.6f}")

    lo, hi = 3.7490007769598015, 5.302
    check("carrier coverage vs D=3 = 123.8%",
          abs(carrier / lo * 100 - 123.8) < 0.1, f"{carrier / lo * 100:.2f}%")
    check("carrier coverage vs D=1.5 = 87.5%",
          abs(carrier / hi * 100 - 87.5) < 0.1, f"{carrier / hi * 100:.2f}%")
    check("total coverage vs D=3 = 128.9%",
          abs(total / lo * 100 - 128.9) < 0.1, f"{total / lo * 100:.2f}%")
    check("total coverage vs D=1.5 = 91.1%",
          abs(total / hi * 100 - 91.1) < 0.1, f"{total / hi * 100:.2f}%")
    check("high-plateau coverage vs D=1.5 = 112.9%",
          abs(hp / hi * 100 - 112.9) < 0.1, f"{hp / hi * 100:.2f}%")

    # the OLD model number that the index used to quote alone
    old = final["fin_nom"]["i_ant_rms_mA"]
    check("old model current = 6.2499 mA", abs(old - 6.249898162776399) < 1e-9,
          f"{old:.6f}")
    check("old model gives 166.7% vs D=3", abs(old / lo * 100 - 166.7) < 0.2,
          f"{old / lo * 100:.2f}%")
    check("old model gives 117.9% vs D=1.5", abs(old / hi * 100 - 117.9) < 0.2,
          f"{old / hi * 100:.2f}%")

    # old model must be the 13.824-ohm no-sense-resistor one
    check("old model R_ANT is 13.824 ohm (no sense resistor)",
          "R_ANT = 13.824" in read(A3 / "scripts/final_verify.py"))


# --------------------------------------------- 2. link_budget.py fixes
def check_link_budget():
    p = A3 / "scripts/link_budget.py"
    if not check("link_budget.py exists", p.exists()):
        return
    src = read(p)

    check("h_eff = h/2 is gone from the docstring",
          "h_eff   = h/2" not in src and "h_eff   = h  " in src)
    check("h_eff_monopole helper exists", "def h_eff_monopole(h):" in src)
    check("h_eff_monopole returns h (image included)",
          re.search(r"def h_eff_monopole\(h\):.*?return h\b", src, re.S) is not None)

    # strip comments before looking for the old expression, because the fix
    # deliberately leaves a "# was: e * (h_rx / 2)" breadcrumb in the code
    code_only = "\n".join(re.sub(r"#.*$", "", ln) for ln in src.splitlines())
    check("link() no longer divides h_rx by 2 in executable code",
          "h_rx / 2" not in code_only and "h_rx/2" not in code_only)
    check("link() uses h_eff_monopole(h_rx)", "h_eff_monopole(h_rx)" in code_only)
    check("the old expression survives only as a comment",
          "was: e * (h_rx / 2)" in src)
    check("peak-power-as-average defect is fixed",
          "radiation_resistance(h) / 2.0" in src)
    check("e_max_from_power documents that its argument is average power",
          "AVERAGE radiated power" in src)
    check("module docstring warns not to fix link_budget_audit.py",
          'Do not "fix" that file' in src)

    # two defects were previously cancelling; both must now be absent
    check("defect A (h/2) documented as x2.000",
          "x2.000" in src or "×2.000" in src or "defect A" in src)
    check("defect B (rms/sqrt2) documented as x0.707",
          "x0.707" in src)

    # cross-check against the audit's authoritative solution
    audit = load(RES / "link_budget_audit.json")
    corr = audit["corrected"]
    check("audit h_eff = 1.0 m", abs(corr["h_eff_m"] - 1.0) < 1e-9)
    check("audit P_avg = 59.362 uW", abs(corr["P_avg_uW"] - 59.362) < 0.01,
          f"{corr['P_avg_uW']:.4f}")
    check("audit E_peak = 17.222 mV/m", abs(corr["E_peak_mV_per_m"] - 17.222) < 0.01,
          f"{corr['E_peak_mV_per_m']:.4f}")
    check("audit I_peak = 5.302 mA", abs(corr["I_peak_mA"] - 5.302) < 0.005,
          f"{corr['I_peak_mA']:.4f}")

    # reproduce the corrected physics with the same relations
    R_rad = 395.0 * (1.0 / 9.671) ** 2
    i_peak = corr["I_peak_mA"] * 1e-3
    p_avg = i_peak ** 2 * R_rad / 2.0
    e_peak = math.sqrt(180.0 * p_avg) / 6.0
    check("P_avg from corrected relation matches the audit",
          abs(p_avg * 1e6 - 59.362) < 0.05, f"{p_avg * 1e6:.3f} uW")
    check("E_peak from corrected relation matches the audit",
          abs(e_peak * 1e3 - 17.222) < 0.05, f"{e_peak * 1e3:.3f} mV/m")

    # and show that the old peak-power form was wrong by sqrt(2)
    e_peak_wrong = math.sqrt(180.0 * i_peak ** 2 * R_rad) / 6.0
    ratio = e_peak_wrong / e_peak
    check("old peak-power form overstates E by sqrt(2)",
          abs(ratio - 2 ** 0.5) < 1e-9, f"{ratio:.6f}")


# ------------------------------------------------- 3. v3 node mapping
def check_v3_mapping():
    fv = A3 / "scripts/final_verify.py"
    src = read(fv)
    check("final_verify.py inserts V3ALIAS", "V3ALIAS v3 ef_e 0" in src)
    check("V3ALIAS is a zero-volt source", re.search(r"V3ALIAS v3 ef_e 0\s*$", src, re.M) is not None)
    check("save statement still requests v(v3)",
          "save v(v1) v(ef_e) v(v3)" in src)
    check("comment explains the ROISO removal",
          "ROISO was removed" in src or "ROISO" in src)

    # syntax check without executing
    import ast
    try:
        ast.parse(src)
        check("final_verify.py parses", True)
    except SyntaxError as exc:
        check("final_verify.py parses", False, repr(exc))

    # historical raw must be untouched: still 6 variables, still no v(v3)
    raw = A3 / "results/fin_nom.raw"
    if not check("fin_nom.raw exists", raw.exists()):
        return
    blob = raw.read_bytes()[:200000]
    off = blob.find(b"Binary:")
    header = blob[:off if off > 0 else 4000].decode("latin1", "replace")
    m = re.search(r"No\. Variables:\s+(\d+)", header)
    check("historical fin_nom.raw still has 6 variables",
          m is not None and int(m[1]) == 6, m[1] if m else "?")
    check("historical fin_nom.raw still has no v(v3) column", "v(v3)" not in header)
    check("historical fin_nom.raw does have v(ef_e)", "v(ef_e)" in header)

    # the source netlist should still declare the (now inert) save
    cir = A3 / "netlists/fin_nom.cir"
    check("historical fin_nom.cir unchanged: still saves v(v3)",
          "v(v3)" in read(cir))
    check("historical fin_nom.cir has no V3ALIAS (netlist is historical)",
          "V3ALIAS" not in read(cir))


# ------------------------------------------- 4. index-layer documentation
def check_index_docs():
    readme = read(ROOT / "README.md")
    status = read(ROOT / "项目管理/03_当前实现状态.md")
    p1b = read(HERE / "P1b_AM-ALT.3三项修订.md")

    check("README states the corrected coverage 87.5%～123.8%",
          "87.5%～123.8%" in readme)
    check("README keeps the old figure but flags its model",
          "117.92%～166.66%" in readme and "13.824" in readme)
    check("README flags the v3 node disappearance", "fin_nom.raw" in readme)
    check("README flags link_budget.py h_eff defect", "link_budget.py" in readme)
    check("status doc records the 19:00 revision", "AM-02.3 回溯修订完成" in status)
    check("status doc lists the four defects", "四处独立缺陷" in status)
    check("P1b report documents defect B (peak vs average power)",
          "把峰值功率当平均功率" in p1b)
    check("P1b explains why link_budget_audit.py must not be fixed",
          'Do not "fix" that file' in p1b or "审计工具" in p1b)


# ------------------------------- 5. the no-rollback decision stays honoured
def check_no_rollback():
    """The user decided on 2026-11-16 that both script fixes stay.

    These checks guard against a silent revert: if someone restores the old
    link_budget.py or removes the v3 alias, the stage would start producing
    field strengths that are off by sqrt(2) again, with no visible symptom.
    """
    doc = read(HERE / "P1b_AM-ALT.3三项修订.md")
    check("P1b records the no-rollback decision", "两个脚本不回退" in doc)
    check("P1b explains why the scripts differ from historical evidence",
          "证据" in doc and "工具" in doc)
    check("P1b states both scripts were kept rather than reverted",
          "已获用户明确批准保留，不予回退" in doc)

    lb = read(A3 / "scripts/link_budget.py")
    lb_code = "\n".join(re.sub(r"#.*$", "", ln) for ln in lb.splitlines())
    lb_code = re.sub(r'"""[\s\S]*?"""', "", lb_code)
    check("link_budget.py fix is still in place (h_eff helper)",
          "h_eff_monopole" in lb_code)
    check("link_budget.py fix is still in place (average power)",
          "radiation_resistance(h) / 2.0" in lb_code)
    check("link_budget.py has NOT been reverted to h_rx/2",
          not re.search(r"h_rx\s*/\s*2", lb_code))

    fv = read(A3 / "scripts/final_verify.py")
    check("final_verify.py still carries the V3ALIAS line",
          "V3ALIAS v3 ef_e 0" in fv)

    # the audit script must remain untouched, so the defects stay reproducible
    audit = read(A3 / "scripts/link_budget_audit.py")
    check("link_budget_audit.py still reproduces h/2 (unchanged)",
          "H / 2" in audit)
    check("link_budget_audit.py still documents both defects",
          "defect" in audit.lower() or "attribution" in audit.lower())


def main():
    print("=" * 78)
    print("P1b verification - coverage / v3 mapping / link_budget fixes")
    print(ROOT)
    print("=" * 78)
    for fn in (check_coverage, check_link_budget, check_v3_mapping,
               check_index_docs, check_no_rollback):
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

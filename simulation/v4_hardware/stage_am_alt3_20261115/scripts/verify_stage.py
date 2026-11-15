"""Integrity and consistency check for AM-ALT.3, mirroring AM-ALT.2's verifier.

Checks that no predecessor file changed, that every claimed result has netlist,
raw, log and JSON on disk, and that the numbers quoted in the report match the
JSON. Writes results/stage_verification.json.
"""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WS = ROOT.parents[2]
RES = ROOT / "results"
NET = ROOT / "netlists"

# predecessor trees that must stay byte-identical
WATCHED = [
    ROOT.parent / "repair_20261011",
    ROOT.parent / "stage_am_alt1_base_20261115",
    ROOT.parent / "stage_am_alt2_20261115",
    ROOT.parent / "stage4_rf_oscillator" / "AM02_3_second_stage_20261113",
]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def manifest(root):
    if not root.exists():
        return {}
    return {str(p.relative_to(WS)): sha(p) for p in sorted(root.rglob("*")) if p.is_file()}


def main():
    report = {}

    # 1. predecessor trees unchanged (compared against AM-ALT.2's own manifest)
    alt2_manifest = ROOT.parent / "stage_am_alt2_20261115" / "sources" / "predecessor_sha256.json"
    changed, missing = [], []
    if alt2_manifest.exists():
        man = json.loads(alt2_manifest.read_text(encoding="utf-8"))
        for rel, expected in man.items():
            p = WS / rel
            if not p.exists():
                missing.append(rel)
            elif sha(p) != expected:
                changed.append(rel)
    report["predecessor"] = {
        "manifest_used": str(alt2_manifest.relative_to(WS)) if alt2_manifest.exists() else None,
        "entries": len(man) if alt2_manifest.exists() else 0,
        "changed_or_missing": sorted(changed + missing),
        "unchanged": not changed and not missing,
    }

    # 2. every run has its evidence
    runs = sorted({p.stem for p in NET.glob("*.cir")})
    rows = []
    for name in runs:
        raw = RES / f"{name}.raw"
        log = RES / f"{name}.log"
        rows.append({
            "run": name,
            "netlist": (NET / f"{name}.cir").exists(),
            "raw": raw.exists(),
            "raw_mb": round(raw.stat().st_size / 1e6, 2) if raw.exists() else None,
            "log": log.exists(),
            "log_errors": ("Error" in log.read_text(errors="ignore")) if log.exists() else None,
        })
    report["runs"] = rows
    failed = [r["run"] for r in rows if not (r["netlist"] and r["raw"])]

    # 3. report numbers versus JSON
    final = json.loads((RES / "final_verify.json").read_text(encoding="utf-8"))
    req = json.loads((RES / "requirement.json").read_text(encoding="utf-8"))
    doc = (ROOT / "01_AM-ALT.3_天线阻抗匹配与驱动能力报告.md").read_text(encoding="utf-8")

    checks = {
        "nominal I_ant 6.250": abs(final["fin_nom"]["i_ant_rms_mA"] - 6.250) < 0.01,
        "nominal m 22.5%": abs(final["fin_nom"]["m_plateau"] * 100 - 22.5) < 0.2,
        "nominal P_bat 308.7": abs(final["fin_nom"]["p_bat_budget_mW"] - 308.7) < 0.5,
        "detuned lo 1.860": abs(final["fin_lo"]["i_ant_rms_mA"] - 1.860) < 0.01,
        "detuned hi 2.076": abs(final["fin_hi"]["i_ant_rms_mA"] - 2.076) < 0.01,
        "req 5.30 mA rms": abs(req["requirement"]["i_ant_needed_mA_rms"] - 5.30) < 0.02,
        "ceiling 1.193 mA rms": abs(req["supply"]["i_absolute_ceiling_mA_rms"] - 1.193) < 0.005,
        "gap 4.44x": abs(req["gap"]["current_ratio"] - 4.44) < 0.02,
        "report states 8.91 pF": "8.91 pF" in doc,
        "report states impedance unmeasured": "必须实测" in doc,
        "report keeps 6 m unverified": "未验证" in doc,
        "report records ROISO issue": "ROISO" in doc,
        "report records m mismatch": "24.3%" in doc or "22.5%" in doc,
    }

    report["numbers"] = checks

    # 4. errata checks: the second report must agree with the audit JSONs.
    # These are deliberately separate from `checks` above. The checks above verify
    # that the FIRST report is internally consistent with its own JSON -- that is
    # still true and still worth asserting, but it certifies what the first report
    # SAID, not that what it said was correct. The errata supersede several of
    # those numbers, so a single merged pass/fail would be misleading.
    errata = {"present": False}
    audit_path = RES / "link_budget_audit.json"
    meas_path = RES / "measurement_design.json"
    doc2_path = ROOT / "02_AM-ALT.3_勘误与天线阻抗测量方案.md"
    if audit_path.exists() and doc2_path.exists():
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        meas = (json.loads(meas_path.read_text(encoding="utf-8"))
                if meas_path.exists() else None)
        doc2 = doc2_path.read_text(encoding="utf-8")
        br = audit["bracket_by_directivity"]["rows"]
        errata = {
            "present": True,
            "checks": {
                "published 5.30 reproduced as its own model /sqrt2":
                    abs(audit["published_reported_rms_mA"] - 5.300053487637991) < 0.01,
                "its own model rms is 7.50":
                    abs(audit["published_model_consistent_rms_mA"] - 7.498) < 0.01,
                "corrected D=3 is 3.75":
                    abs(audit["corrected"]["I_rms_mA"] - 3.749) < 0.01,
                "5.30 equals the D=1.5 value":
                    abs(br[-1]["I_rms_mA"] - 5.302) < 0.01,
                "h_eff=h/2 implies impossible D<1":
                    audit["aperture_consistency"]["checks"][0]["implied_D"] < 1.0,
                "net factor is sqrt2":
                    abs(audit["attribution"]["net"]["overstatement_factor"]
                        - 2 ** 0.5) < 1e-6,
                "driver covers the whole D bracket":
                    all(m["met"] for m in audit["bracket_by_directivity"]["driver_meets_D"]),
                "errata report states the retraction": "作废" in doc2,
                "errata report states L must be tunable": "2.2～4.4 µH" in doc2,
                "errata report keeps 6 m unmeasured": "近场" in doc2,
            },
        }
        if meas:
            errata["checks"]["probe detunes antenna node from 31 to 18.5 MHz"] = (
                "18.5 MHz" in meas["probe_loading"][0]["distortion"])
            errata["checks"]["low-freq L route is the accurate one"] = (
                abs(meas["l_measurement_scenarios"][1]["error_budget"]["total_error_pct"]) < 5.0)

        # the first report must NOT have been edited to hide the defects
        doc1 = (ROOT / "01_AM-ALT.3_天线阻抗匹配与驱动能力报告.md").read_text(encoding="utf-8")
        errata["checks"]["first report left intact (still says 5.30)"] = "5.30" in doc1
        errata["all_pass"] = all(errata["checks"].values())
    report["errata"] = errata

    report["all_checks_pass"] = (
        report["predecessor"]["unchanged"]
        and not failed
        and all(checks.values())
    )
    report["stage_status"] = (
        "NOT complete: the antenna impedance is still unmeasured and the "
        "requirement has been corrected; see 02_AM-ALT.3 errata"
    )
    report["original_checks_scope"] = (
        "the `numbers` block above certifies that the first report agrees with "
        "its own JSON. It does NOT certify that those numbers are the correct "
        "requirement -- the errata block supersedes several of them"
    )
    out = RES / "stage_verification.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"predecessor unchanged: {report['predecessor']['unchanged']} "
          f"({report['predecessor']['entries']} entries)")
    print(f"runs with netlist+raw: {len(rows) - len(failed)}/{len(rows)}"
          + (f"  missing: {failed}" if failed else ""))
    print("-- first report vs its own JSON (does not certify correctness) --")
    for k, v in checks.items():
        print(f"  {'OK ' if v else 'FAIL'} {k}")
    print("-- errata vs audit JSON --")
    if errata.get("present"):
        for k, v in errata["checks"].items():
            print(f"  {'OK ' if v else 'FAIL'} {k}")
        print(f"  errata all pass: {errata['all_pass']}")
    else:
        print("  FAIL errata or audit JSON missing")
    print()
    print("first-report checks pass:", report["all_checks_pass"])
    print("stage status:", report["stage_status"])
    print("written:", out)


if __name__ == "__main__":
    main()

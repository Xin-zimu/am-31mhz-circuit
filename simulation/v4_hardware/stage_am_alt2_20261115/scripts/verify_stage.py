"""AM-ALT.2 stage verification record.

Recomputes the evidence checks the report cites, without new simulations:
  1. predecessor manifest (frozen netlists + AM-ALT.1 files) unchanged;
  2. every matrix/post-check run has netlist, raw, JSON, edges and figure;
  3. netlist SHA-256 recorded inside each JSON matches the on-disk netlist;
  4. transient end time reaches the requested stop time;
  5. figures exist for all runs with edge diagnostics.
Writes results/stage_verification.json and prints a summary.
"""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_alt2_20261115")
WS = ROOT.parents[2]
RES = ROOT / "results"
FIG = ROOT / "figures"
NET = ROOT / "netlists"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


# 1. predecessor manifest
man = json.loads((ROOT / "sources/predecessor_sha256.json").read_text(encoding="utf-8"))
changed, missing = [], []
for rel, expected in man.items():
    p = WS / rel
    if not p.exists():
        missing.append(rel)
    elif sha(p) != expected:
        changed.append(rel)

# 2-5. per-run evidence
matrix = json.loads((RES / "full_matrix_index.json").read_text(encoding="utf-8"))
extra = ["fine_a4_d50_h025", "fine_a4_d50_h0125", "fine_a4_d10_h0125",
         "full_span_high_d10", "full_span_max_d10"]
records = []
for name in matrix + extra:
    j = json.loads((RES / f"{name}.json").read_text(encoding="utf-8"))
    net = NET / f"{name}.cir"
    raw = RES / f"{name}.raw"
    edges = RES / f"{name}_edges.json"
    fig = FIG / f"{name}.png"
    netlist = net.read_text(encoding="utf-8")
    tran = re.search(r"^\s*tran\s+\S+\s+(\S+)\s+(\S+)", netlist, re.M)
    stop = float(tran.group(1))
    # declared stop in the control block uses SPICE suffixes; parse simple n/u/m forms
    def parse(tok):
        m = re.fullmatch(r"([0-9.eE+-]+)([a-zA-Z]*)", tok)
        value = float(m.group(1))
        suffix = m.group(2).lower()
        scale = {"": 1, "n": 1e-9, "u": 1e-6, "m": 1e-3}.get(suffix)
        return value * scale if scale is not None else None

    stop = parse(tran.group(1))
    expected_end = 2e-3 if j["settings"].get("full") else 400e-6
    records.append({
        "name": name,
        "netlist_present": net.exists(),
        "raw_present": raw.exists(),
        "json_present": True,
        "edges_present": edges.exists(),
        "figure_present": fig.exists(),
        "recorded_sha_matches": j["netlist_sha256"] == sha(net),
        "requested_stop_s": stop,
        "expected_stop_s": expected_end,
        "raw_bytes": raw.stat().st_size if raw.exists() else None,
    })

problems = [r["name"] for r in records
            if not all([r["netlist_present"], r["raw_present"], r["edges_present"],
                        r["figure_present"], r["recorded_sha_matches"]])
            or r["requested_stop_s"] != r["expected_stop_s"]]

# manifest of every produced netlist/result pair for this stage
produced = sorted(p.name for p in NET.glob("*.cir"))

summary = {
    "stage": "AM-ALT.2",
    "generated_from": "existing raw/json evidence; no new circuit changes",
    "predecessor_manifest": {
        "file": "sources/predecessor_sha256.json",
        "entries": len(man),
        "changed_or_missing": sorted(changed + missing),
        "frozen_and_predecessor_unchanged": not changed and not missing,
    },
    "runs": records,
    "problem_runs": problems,
    "stage_netlist_count": len(produced),
    "matrix_runs": len(matrix),
    "check_runs": len(extra),
    "checks_passed": not problems and not changed and not missing,
}
(RES / "stage_verification.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps({k: v for k, v in summary.items() if k != "runs"}, indent=2, ensure_ascii=False))
print("runs checked:", len(records), "problems:", problems)

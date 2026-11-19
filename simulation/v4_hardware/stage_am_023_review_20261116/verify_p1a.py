"""Read-only verifier for P1a: AM-02.3 retrospective conclusion revision and
pseudo-2k annotation.

Checks every load-bearing claim of
    P1a_AM-02.3历史结论修订与伪2kΩ标注.md
against the files on disk. Runs no simulation and writes no file.

    py -3 simulation/v4_hardware/stage_am_023_review_20261116/verify_p1a.py
"""
import csv
import hashlib
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REVIEW = Path(__file__).resolve().parent
STAGE = ROOT / "simulation/v4_hardware/stage4_rf_oscillator/AM02_3_second_stage_20261113"
NET = STAGE / "netlists"
RES = STAGE / "results"

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  -- {detail}" if detail else ""))
    return bool(ok)


def read(p):
    return Path(p).read_text(encoding="utf-8", errors="replace")


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def netlist_load(netlist_path):
    """Parse the RLD value out of a generated AM-02.3 netlist."""
    txt = read(netlist_path)
    m = re.search(r"(?im)^RLD\s+\S+\s+\S+\s+(\S+)", txt)
    return float(m[1]) if m else None


def read_matrix_csv():
    """Read AM02_3_matrix.csv, tolerating its UTF-8 BOM.

    The file starts with a byte-order mark, so csv.DictReader names the first
    column '\\ufeffsource' rather than 'source'. Using encoding='utf-8-sig'
    strips it; without this the row lookups raise KeyError.
    """
    p = STAGE / "AM02_3_matrix.csv"
    with p.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert "source" in rows[0], f"unexpected header: {list(rows[0])}"
    return rows


# ------------------------------------------------ 1. originals untouched
def check_hash_protection():
    manifest = STAGE / "SHA256SUMS.txt"
    if not check("SHA256SUMS.txt exists", manifest.exists()):
        return
    entries = {}
    for line in read(manifest).splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) == 2:
            entries[parts[1].strip()] = parts[0].strip()
    check("manifest has 1530 entries", len(entries) == 1530, f"{len(entries)}")

    protected = {
        "AM02_3_报告.md": "172b3f5dc92705f8892f594be2635ceee421edeb73ae07a3d4ec6daf37000db0",
        "AM02_3_matrix.csv": "1745dbb6421d20e52f7453e803102d34f3a97bba6ed96b87d43445cb3907e7a3",
        "results/final_matrix.json": "bd440cfbb759e12ed8ddaa110c7eef87ec6581ed4f963e69d58fcd88b509c6a7",
        "results/load2k_matrix.json": "b81487d80421fc55b25c7f05da1b75daef857720e51d9823b6f7e80848eb2b6f",
    }
    for rel, expected in protected.items():
        p = STAGE / rel
        if not check(f"{rel} exists", p.exists()):
            continue
        actual = sha256(p)
        check(f"{rel} is byte-identical to the manifest", actual == expected, actual[:16] + "...")
        check(f"{rel} matches the manifest entry", entries.get(rel) == expected)


# ------------------------------------------- 2. the netlist-level bug
def check_netlist_bug():
    cases = [
        ("mx_S3_50_4_50.cir", 50.0),
        ("mx_S3_2000_4_50.cir", 50.0),      # name lies
        ("ld2_S3_2000_4.cir", 2000.0),      # genuine
    ]
    for name, expected in cases:
        p = NET / name
        if not check(f"{name} exists", p.exists()):
            continue
        actual = netlist_load(p)
        check(f"{name} loads {expected:g} ohm", actual == expected, f"{actual:g}")

    # all four mislabelled netlists must also load 50
    for amp in (1, 2, 3, 4):
        name = f"mx_S3_2000_{amp}_50.cir"
        p = NET / name
        if p.exists():
            check(f"{name} also loads 50 (bug)", netlist_load(p) == 50.0,
                  f"{netlist_load(p):g}")


# ------------------------------- 3. bit-identity of the pseudo-2k rows
def check_bit_identity():
    csv_path = STAGE / "AM02_3_matrix.csv"
    if not check("AM02_3_matrix.csv exists", csv_path.exists()):
        return
    rows = read_matrix_csv()
    check("CSV has 44 data rows", len(rows) == 44, f"{len(rows)}")
    check("CSV first column is 'source' (BOM stripped)", "source" in rows[0],
          str(list(rows[0])[:3]))

    cols = ["vpp_high", "vpp_low", "step_vpp", "modulation_index",
            "thd_high_pct", "supply_mw", "cap_v", "plateau_flatness", "overshoot"]

    def find(source, load, amp):
        for r in rows:
            if (r["source"] == source and float(r["load_ohm"]) == load
                    and r["config"] == "S3" and float(r["amp_vpp"]) == amp
                    and float(r["duty_pct"]) == 50.0):
                return r
        return None

    for amp in (1.0, 2.0, 3.0, 4.0):
        fifty = find("final_matrix", 50.0, amp)
        pseudo = find("final_matrix", 2000.0, amp)
        if not check(f"amp {amp:g}: both 50 and mislabelled-2000 rows exist",
                     fifty and pseudo):
            continue
        diffs = [c for c in cols if fifty[c] != pseudo[c]]
        check(f"amp {amp:g}: pseudo-2000 row is identical to the 50-ohm row on all physics columns",
              not diffs, str(diffs))
        check(f"amp {amp:g}: only cir_sha256 differs", fifty["cir_sha256"] != pseudo["cir_sha256"])

    # the genuine 2k rows must actually differ
    genuine = find("load2k", 2000.0, 4.0)
    fifty4 = find("load2k", 50.0, 4.0)
    if check("genuine 2k and 50-ohm rows both exist", genuine and fifty4):
        check("genuine 2k row differs from the 50-ohm row",
              genuine["vpp_high"] != fifty4["vpp_high"],
              f"{genuine['vpp_high']} vs {fifty4['vpp_high']}")


# ---------------------------------------- 4. final_matrix.json same story
def check_final_matrix():
    p = RES / "final_matrix.json"
    if not check("final_matrix.json exists", p.exists()):
        return
    fm = json.loads(read(p))
    labelled_2k = [r for r in fm if abs(r["load_ohm"] - 2000.0) < 1e-9]
    check("final_matrix has exactly 4 rows labelled 2000 ohm", len(labelled_2k) == 4,
          f"{len(labelled_2k)}")

    fifty = {round(r["amp_vpp"], 6): r["vpp_high"] for r in fm
             if abs(r["load_ohm"] - 50.0) < 1e-9 and r["config"] == "S3"
             and abs(r["duty_pct"] - 50.0) < 1e-9}
    check("found 4 S3 50-ohm duty-50 reference rows", len(fifty) == 4, str(sorted(fifty)))

    same = all(abs(r["vpp_high"] - fifty[round(r["amp_vpp"], 6)]) < 1e-12
               for r in labelled_2k)
    check("all 4 mislabelled rows are bit-identical to their 50-ohm counterparts", same)

    # each mislabelled row must point at a netlist that actually loads 50
    for r in labelled_2k:
        nl = Path(r["netlist"])
        if not check(f"mislabelled netlist exists: {nl.name}", nl.exists()):
            continue
        check(f"{nl.name} actually loads 50 ohm (so the 2000 label is wrong)",
              netlist_load(nl) == 50.0, f"{netlist_load(nl):g}")


# --------------------------------------------- 5. the two 50-ohm values
def check_two_values():
    load2k = json.loads(read(RES / "load2k_matrix.json"))
    casc = json.loads(read(RES / "cascade_candidates.json"))

    def pick(rows, cfg, load, amp):
        for r in rows:
            key = r.get("config", r.get("topology"))
            if (key == cfg and abs(r["load_ohm"] - load) < 1e-9
                    and abs(r["amp_vpp"] - amp) < 1e-9
                    and abs(r["duty_pct"] - 50.0) < 1e-9):
                return r
        return None

    a = pick(load2k, "S3", 50.0, 4.0)
    b = pick(casc, "S3", 50.0, 4.0)
    if not check("both S3 50-ohm 4 Vpp rows found", a and b):
        return
    check("source A vpp_high = 0.3856931",
          abs(a["vpp_high"] - 0.38569311162061176) < 1e-12)
    check("source B vpp_high = 0.3770370",
          abs(b["vpp_high"] - 0.37703694057203) < 1e-12)
    diff = 20 * math.log10(a["vpp_high"] / b["vpp_high"])
    check("the two differ by 0.197 dB", abs(diff - 0.197) < 0.005, f"{diff:.4f} dB")
    check("cap_v differs by 0.222 V", abs(a["cap_v"] - b["cap_v"] - 0.2217) < 0.01,
          f"{a['cap_v']:.4f} vs {b['cap_v']:.4f}")

    # the report must carry both figures -> this is why P1a documents it
    rep = read(STAGE / "AM02_3_报告.md")
    check("report quotes 14.3 dB (from source A)", "14.3" in rep)
    check("report quotes 14.5 dB (from source B)", "电平差 14.5 dB" in rep)
    check("report declares the load-propagation bug",
          "漏把 `rload` 传进级参数" in rep)


# ------------------------------------------------ 6. the dB arithmetic
def check_arithmetic():
    gap_50 = 20 * math.log10(2.0 / 0.38569311162061176)
    gap_2k = 20 * math.log10(2.0 / 0.440567473966195)
    low_50 = 20 * math.log10(1.2 / 0.2267683267244924)
    low_2k = 20 * math.log10(1.2 / 0.25848605422905924)
    mean_50 = 20 * math.log10(1.6 / 0.38569311162061176)
    mean_2k = 20 * math.log10(1.6 / 0.440567473966195)

    check("14.3 dB at 50 ohm reproduces", abs(gap_50 - 14.296) < 0.005, f"{gap_50:.4f}")
    check("13.1 dB at 2 kohm reproduces", abs(gap_2k - 13.140) < 0.005, f"{gap_2k:.4f}")
    check("low-envelope 14.5 dB at 50 ohm", abs(low_50 - 14.472) < 0.005, f"{low_50:.4f}")
    check("low-envelope 13.3 dB at 2 kohm", abs(low_2k - 13.335) < 0.005, f"{low_2k:.4f}")
    check("POLY-mean 12.4 dB at 50 ohm", abs(mean_50 - 12.358) < 0.005, f"{mean_50:.4f}")
    check("POLY-mean 11.2 dB at 2 kohm", abs(mean_2k - 11.202) < 0.005, f"{mean_2k:.4f}")
    check("load change recovers 1.155 dB", abs((gap_50 - gap_2k) - 1.155) < 0.005,
          f"{gap_50 - gap_2k:.4f}")


# ----------------------------------------------- 7. annotation consistency
def check_annotation():
    p = REVIEW / "pseudo_2k_annotation.json"
    if not check("pseudo_2k_annotation.json exists", p.exists()):
        return
    try:
        ann = json.loads(read(p))
    except Exception as exc:                    # noqa: BLE001
        check("annotation parses", False, repr(exc))
        return
    check("annotation parses", True)
    check("annotation records no original file modified",
          ann["meta"]["original_files_modified"] is False)
    rows = ann["rows"]
    check("annotation lists 8 rows (4 pseudo + 4 genuine)", len(rows) == 8, f"{len(rows)}")
    check("exactly 4 rows are PSEUDO_2K",
          sum(1 for r in rows if r["verdict"] == "PSEUDO_2K") == 4)
    check("exactly 4 rows are GENUINE_2K",
          sum(1 for r in rows if r["verdict"] == "GENUINE_2K") == 4)
    check("pseudo rows claim actual_load 50",
          all(r["actual_load_ohm"] == 50.0 for r in rows if r["verdict"] == "PSEUDO_2K"))
    check("genuine rows claim actual_load 2000",
          all(r["actual_load_ohm"] == 2000.0 for r in rows if r["verdict"] == "GENUINE_2K"))

    # every claimed vpp_high must match the CSV
    csv_rows = read_matrix_csv()
    mismatched = []
    for r in rows:
        match = [c for c in csv_rows
                 if c["source"] == r["source"] and c["config"] == r["config"]
                 and float(c["load_ohm"]) == r["load_ohm_labelled"]
                 and float(c["amp_vpp"]) == r["amp_vpp"]]
        if not match or abs(float(match[0]["vpp_high"]) - r["vpp_high"]) > 1e-15:
            mismatched.append((r["source"], r["amp_vpp"]))
    check("every annotated vpp_high matches the CSV", not mismatched, str(mismatched))

    # hash-protection block must quote the real hashes
    for item in ann["hash_protection"]["protected_files"]:
        actual = sha256(STAGE / item["file"])
        check(f"annotation quotes the real hash of {item['file']}",
              actual == item["sha256"], actual[:16] + "...")


def main():
    print("=" * 78)
    print("P1a verification - AM-02.3 revision + pseudo-2k annotation")
    print(ROOT)
    print("=" * 78)
    for fn in (check_hash_protection, check_netlist_bug, check_bit_identity,
               check_final_matrix, check_two_values, check_arithmetic,
               check_annotation):
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

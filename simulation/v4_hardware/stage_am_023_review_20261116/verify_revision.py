"""Read-only verifier for the AM-02.3 retrospective revision (2026-11-16).

Checks every load-bearing claim of
    AM-02.3_回溯修订_50Ω口径与AM-ALT.3目标复核.md
against the files on disk. Runs no simulation and writes no file.

    py -3 simulation/v4_hardware/stage_am_023_review_20261116/verify_revision.py
"""
import hashlib
import html
import json
import math
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REVIEW = Path(__file__).resolve().parent

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  -- {detail}" if detail else ""))
    return bool(ok)


def read(p):
    return Path(p).read_text(encoding="utf-8", errors="replace")


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ---------------------------------------------------------------- 1. course docx
TAG_RE = re.compile(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", re.S)
PARA_RE = re.compile(r"<w:p[\s>].*?</w:p>", re.S)


def docx_text(path):
    """Extract body text from a .docx, paragraph by paragraph.

    Three traps this implementation avoids, each of which produced a wrong
    answer when first written:

      1. The tag regex must be ``<w:t(?:\\s[^>]*)?>`` -- writing ``<w:t[^>]*>``
         also matches ``<w:tbl>`` and ``<w:tc>``, dragging whole-table XML into
         the "text" (61,860 chars instead of the true 3,908).
      2. Run-level text nodes inside one paragraph must be concatenated (Word
         splits a sentence across many ``<w:t>``), but *paragraphs* must be
         separated. Table cells are paragraphs too, so each cell becomes its
         own line.
      3. Concatenating cells invents spurious matches. The page-7 similarity
         table stores ``1``, ``0.8``, ``0.5``, ``0.2`` as four cells; joined
         blindly they read ``0.80.50.20`` and fabricate a "50".

    XML entities (``&gt;``, ``&lt;``, ``&amp;``) are unescaped so that text
    such as ``>1m扣4分`` is searchable as written.
    """
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8")

    def runs(block):
        return "".join(html.unescape(m) for m in TAG_RE.findall(block))

    paragraphs = [runs(p) for p in PARA_RE.findall(xml)]
    if not any(paragraphs):                          # fallback: no <w:p> found
        paragraphs = [runs(xml)]
    return "\n".join(p for p in paragraphs if p)


def check_course_document():
    p = ROOT / "电子线路实验评分标准-学生.docx"
    if not check("course docx exists", p.exists(), str(p)):
        return
    check("course docx sha256", sha256(p).lower().startswith("657a5112"),
          sha256(p)[:16] + "...")
    try:
        body = docx_text(p)
    except Exception as exc:                     # noqa: BLE001
        check("course docx unzipped", False, repr(exc))
        return
    nchars = len(body.replace("\n", ""))
    check("course docx unzipped", 3000 < nchars < 5000,
          f"{nchars} chars of body text in {body.count(chr(10)) + 1} paragraphs")

    zero_terms = ["\u03a9", "\u2126", "\u03c9", "ohm", "Ohm", "欧", "负载",
                  "假负载", "终端", "匹配", "阻抗", "2.0", "包络", "调制度",
                  "调制指数", "探头", "倍率", "校准"]
    for term in zero_terms:
        label = "Omega" if term in ("\u03a9", "\u2126") else term
        check(f"course text has no '{label}'", term not in body,
              f"count={body.count(term)}")

    for needle in ("指定调制波形", "峰峰值不小于4V", "指定距离6m",
                   "功耗小于0.5W", ">1m扣4分", "峰峰值1~4V可调",
                   "占空比10~50%"):
        check(f"course text contains '{needle}'", needle in body)

    # every occurrence of "50" must be a duty-cycle percentage or 500kHz
    fifty = list(re.finditer("50", body))
    check("'50' occurs exactly 11 times (paragraph-separated)", len(fifty) == 11,
          f"count={len(fifty)}")
    bad = [body[max(0, m.start() - 10):m.start() + 8]
           for m in fifty
           if not (body[m.start():m.start() + 3] == "50%"
                   or body[m.start():m.start() + 4] == "500k")]
    check("every '50' is a percentage or part of 500kHz", not bad, str(bad))

    # the counting trap must stay demonstrable: blind concatenation fabricates one
    with zipfile.ZipFile(p) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    blind = "".join(html.unescape(t) for t in TAG_RE.findall(xml))
    check("blind concatenation would fabricate a 12th '50'",
          blind.count("50") == 12 and "0.80.50.2" in blind,
          f"blind count={blind.count('50')}")

    check("no bare '50' token that could be a resistance",
          not re.search(r"(?<![\d.])50(?![\d.%]|0k)", body))


# ------------------------------------------------------- 2. frozen netlist TP3
def check_tp3():
    p = ROOT / "simulation/v4_hardware/repair_20261011/final_actual.cir"
    if not check("frozen netlist exists", p.exists(), str(p)):
        return
    check("frozen netlist sha256",
          sha256(p) == "d9aba8eff74e679f709bc6a680bf569e6dab87a00303b6ff138f19d4964ccaaf",
          sha256(p)[:16] + "...")

    lines = read(p).splitlines()
    hits = [(i + 1, ln) for i, ln in enumerate(lines)
            if "tp3" in ln.lower()]
    check("TP3 appears on exactly 2 lines", len(hits) == 2,
          "; ".join(f"{n}" for n, _ in hits))
    joined = " ".join(ln for _, ln in hits)
    check("TP3 driven by POLY subcircuit", "POLYSourceEAM_-EAM" in joined)
    check("TP3 read by ideal VCVS eEPA", "eEPA TP4 0 TP3 0 1" in joined)

    # any finite element tied to TP3?
    tl = {n for n, _ in hits}
    offenders = []
    for i, ln in enumerate(lines, 1):
        s = ln.strip()
        if not s or s.startswith("*") or s.startswith(".") or i in tl:
            continue
        toks = s.split()
        if len(toks) >= 3 and "TP3" in toks[1:6]:
            offenders.append((i, s[:70]))
    check("no other element references TP3", not offenders, str(offenders[:3]))

    body = "\n".join(lines)
    check("RRF 50 ohm is a series element TP5->RF_OUT",
          "rRRF TP5 RF_OUT 50" in body)
    check("RRF is not a shunt to ground",
          not re.search(r"(?im)^rRRF\s+\S+\s+0\s+50\b", body))

    net = ROOT / "simulation/v4_hardware/repair_20261011/final_reopen.net.txt"
    if net.exists():
        nt = read(net)
        tp3_rows = [ln for ln in nt.splitlines()
                    if re.match(r"^\s*TP3\s", ln)]
        check("Multisim net table lists exactly 2 TP3 pins",
              len(tp3_rows) == 2, f"{len(tp3_rows)} rows")
        check("Multisim net table: no resistor pin on TP3",
              all("RRF" not in ln for ln in tp3_rows))


# ------------------------------------------------- 3. 50 ohm library defaults
def check_library_defaults():
    p = (ROOT / "simulation/v4_hardware/stage4_rf_oscillator/"
         "AM02_3_second_stage_20261113/scripts/am023_lib.py")
    if not check("am023_lib.py exists", p.exists()):
        return
    body = read(p)
    check("default_stage hard-codes rload=50.0",
          re.search(r'"rload":\s*50\.0', body) is not None)
    check("default_stage hard-codes cload=10 pF",
          re.search(r'"cload":\s*10e-12', body) is not None)
    check("measure() defaults to load_r=50.0",
          re.search(r"def measure\([^)]*load_r=50\.0", body) is not None)
    check("output power is scaled by load_r",
          re.search(r"/\s*\(\s*8\.0\s*\*\s*load_r\s*\)", body) is not None)


# --------------------------------------------- 4. load not propagated -> 2k bug
def check_final_matrix_bug():
    d = (ROOT / "simulation/v4_hardware/stage4_rf_oscillator/"
         "AM02_3_second_stage_20261113")
    a = d / "netlists/mx_S3_50_4_50.cir"
    b = d / "netlists/mx_S3_2000_4_50.cir"
    c = d / "netlists/ld2_S3_2000_4.cir"
    for tag, f in (("50-ohm run", a), ("mislabeled 2000-ohm run", b),
                   ("genuine 2000-ohm run", c)):
        if not check(f"{tag} netlist exists", f.exists(), f.name):
            return
    rld = lambda f: re.search(r"(?im)^RLD\s+\S+\s+\S+\s+(\S+)", read(f))[1]  # noqa: E731
    check("mx_S3_50_4_50.cir loads 50", rld(a) == "50", rld(a))
    check("mx_S3_2000_4_50.cir ALSO loads 50 (the bug)", rld(b) == "50", rld(b))
    check("ld2_S3_2000_4.cir loads 2000", rld(c) == "2000", rld(c))

    fm = json.loads(read(d / "results/final_matrix.json"))
    mislabeled = [r for r in fm if abs(r["load_ohm"] - 2000.0) < 1e-9]
    check("final_matrix has 4 records labelled 2000 ohm",
          len(mislabeled) == 4, f"{len(mislabeled)}")
    fifty = {r["amp_vpp"]: r["vpp_high"] for r in fm
             if abs(r["load_ohm"] - 50.0) < 1e-9 and r["config"] == "S3"
             and abs(r["duty_pct"] - 50.0) < 1e-9}
    same = all(abs(r["vpp_high"] - fifty[r["amp_vpp"]]) < 1e-12
               for r in mislabeled)
    check("mislabeled 2000-ohm rows are bit-identical to 50-ohm rows", same)

    csv = d / "AM02_3_matrix.csv"
    if check("AM02_3_matrix.csv exists", csv.exists()):
        rows = [ln.split(",") for ln in read(csv).splitlines()[1:] if ln.strip()]
        # columns: source,config,load_ohm,amp_vpp,duty_pct,vpp_high,...
        labelled_2k = [r for r in rows if len(r) > 5 and r[2] == "2000.0"]
        from_buggy = [r for r in labelled_2k if r[0] == "final_matrix"]
        from_rerun = [r for r in labelled_2k if r[0] == "load2k"]
        check("matrix.csv has 4 rows labelled 2000 ohm from the buggy matrix",
              len(from_buggy) == 4, f"{len(from_buggy)}")
        check("matrix.csv has genuine 2000-ohm rows from the load2k rerun",
              len(from_rerun) >= 4, f"{len(from_rerun)}")
        # the two S3 4Vpp rows disagree, proving they are different loads
        s3 = {}
        for r in labelled_2k:
            if r[1] == "S3" and abs(float(r[3]) - 4.0) < 1e-9:
                s3[r[0]] = float(r[5])
        check("matrix.csv S3/4Vpp 2000-ohm rows disagree between sources",
              len(s3) == 2 and abs(s3["final_matrix"] - s3["load2k"]) > 1e-6,
              str(s3))


# --------------------------------------------- 5. the two S3 50-ohm values
def check_two_values():
    d = (ROOT / "simulation/v4_hardware/stage4_rf_oscillator/"
         "AM02_3_second_stage_20261113/results")
    load2k = json.loads(read(d / "load2k_matrix.json"))
    casc = json.loads(read(d / "cascade_candidates.json"))

    def pick(rows, cfg, load, amp):
        for r in rows:
            if (r.get("config", r.get("topology")) == cfg
                    and abs(r["load_ohm"] - load) < 1e-9
                    and abs(r["amp_vpp"] - amp) < 1e-9
                    and abs(r["duty_pct"] - 50.0) < 1e-9):
                return r
        return None

    a = pick(load2k, "S3", 50.0, 4.0)
    b = pick(casc, "S3", 50.0, 4.0)
    if not check("both S3 50-ohm 4Vpp rows found", a and b):
        return
    check("load2k row high envelope = 0.3856931",
          abs(a["vpp_high"] - 0.38569311162061176) < 1e-12, f"{a['vpp_high']!r}")
    check("cascade row high envelope = 0.3770370",
          abs(b["vpp_high"] - 0.37703694057203) < 1e-12, f"{b['vpp_high']!r}")
    diff = 20 * math.log10(a["vpp_high"] / b["vpp_high"])
    check("the two differ by ~0.197 dB", abs(diff - 0.197) < 0.005, f"{diff:.4f} dB")
    check("cap_v differs by ~0.222 V",
          abs(a["cap_v"] - b["cap_v"] - 0.2217) < 0.01,
          f"{a['cap_v']:.4f} vs {b['cap_v']:.4f}")

    # the report carries both gap figures
    rep = read(d.parent / "AM02_3_报告.md")
    check("report states 14.3 dB gap", "14.3" in rep)
    check("report states 14.5 dB gap in section 4", "电平差 14.5 dB" in rep)


# --------------------------------------------------- 6. dB arithmetic & coverage
def check_arithmetic():
    gap_50 = 20 * math.log10(2.0 / 0.38569311162061176)
    gap_2k = 20 * math.log10(2.0 / 0.440567473966195)
    check("14.3 dB gap reproduces", abs(gap_50 - 14.296) < 0.005, f"{gap_50:.4f}")
    check("13.1 dB gap at 2 kohm reproduces", abs(gap_2k - 13.140) < 0.005,
          f"{gap_2k:.4f}")
    check("load change recovers 1.155 dB", abs((gap_50 - gap_2k) - 1.155) < 0.005,
          f"{gap_50 - gap_2k:.4f}")

    low_50 = 20 * math.log10(1.2 / 0.2267683267244924)
    check("14.5 dB low-envelope gap reproduces", abs(low_50 - 14.472) < 0.005,
          f"{low_50:.4f}")

    # 2.0 Vpp into 50 ohm
    i_pk = (1.0 / 50) * 1e3
    p_avg = (1.0 ** 2) / (2 * 50) * 1e3
    check("2.0 Vpp into 50 ohm = 20 mA peak", abs(i_pk - 20.0) < 1e-9, f"{i_pk}")
    check("2.0 Vpp into 50 ohm = 10 mW average", abs(p_avg - 10.0) < 1e-9, f"{p_avg}")

    # coverage on the 10-ohm sense-resistor model
    carrier, total = 4.6407, 4.8306
    check("carrier coverage vs D=3 requirement = 123.8%",
          abs(carrier / 3.749 * 100 - 123.8) < 0.1,
          f"{carrier / 3.749 * 100:.1f}%")
    check("carrier coverage vs D=1.5 requirement = 87.5%",
          abs(carrier / 5.3019 * 100 - 87.5) < 0.1,
          f"{carrier / 5.3019 * 100:.1f}%")
    check("total-RMS coverage 91.1% - 128.9%",
          abs(total / 5.3019 * 100 - 91.1) < 0.1 and
          abs(total / 3.749 * 100 - 128.9) < 0.1,
          f"{total / 5.3019 * 100:.1f}% - {total / 3.749 * 100:.1f}%")


# ------------------------------------------------ 7. AM-ALT.3 target / v3 node
def check_alt3():
    a3 = ROOT / "simulation/v4_hardware/stage_am_alt3_20261115"

    # no 50-ohm element anywhere in the netlists
    offenders = []
    for f in list((a3 / "netlists").glob("*.cir")) + \
             list((a3 / "round2_20261116" / "netlists").glob("*.cir")):
        for i, ln in enumerate(read(f).splitlines(), 1):
            s = ln.strip()
            if not s or s.startswith("*"):
                continue
            if re.search(r"(?<![\d.])50(?![\d.])", s):
                offenders.append(f"{f.name}:{i}: {s[:60]}")
    check("no bare '50' token in any AM-ALT.3 netlist", not offenders,
          str(offenders[:3]))

    # explicit declaration that the generator 50 ohm is not a driver load
    r03 = read(a3 / "03_AM-ALT.3_测量匹配与驱动复核.md")
    check("03 report forbids writing the generator 50 ohm into the driver load",
          "不应写入实际驱动级负载" in r03)

    # requirement chain is anchored on the course v2 / 6 m clauses
    req = read(a3 / "scripts/requirement.py")
    check("requirement.py targets v2 = 4 Vpp", "V2_REQUIRED = 4.0" in req)
    check("requirement.py uses r = 6 m", "DIST = 6.0" in req)
    check("requirement.py uses the 50-ohm-calibrated S05 sensitivity",
          "V2_PER_MV_AT_M05 = 4.7770 / 10.0" in req)

    # driver loaded by the antenna model, not 50 ohm
    for fname, needle in (("final_verify.py", "R_ANT = 13.824"),
                          ("driver_sized.py", "R_ANT = 13.824")):
        check(f"{fname} loads the antenna model", needle in read(a3 / "scripts" / fname))

    # v3 node vanished from the raw file
    cir = a3 / "netlists/fin_nom.cir"
    if check("fin_nom.cir exists", cir.exists()):
        check("fin_nom.cir still saves v(v3)", "v(v3)" in read(cir))
    raw = a3 / "results/fin_nom.raw"
    if check("fin_nom.raw exists", raw.exists()):
        blob = raw.read_bytes()[:200000]
        off = blob.find(b"Binary:")
        header = blob[:off if off > 0 else 4000].decode("latin1", "replace")
        nvars = re.search(r"No\. Variables:\s+(\d+)", header)
        check("fin_nom.raw has 6 variables",
              nvars is not None and int(nvars[1]) == 6,
              nvars[1] if nvars else "?")
        check("fin_nom.raw contains no v(v3) column", "v(v3)" not in header)

    # link_budget.py carried the refuted h/2 until P1b fixed it; assert the fix
    # by looking at the executed relations, not at prose. The module docstring
    # legitimately mentions h/2 while explaining the correction, so strip
    # comment and docstring text before searching.
    lb = read(a3 / "scripts/link_budget.py")
    lb_code = "\n".join(re.sub(r"#.*$", "", ln) for ln in lb.splitlines())
    lb_code = re.sub(r'"""[\s\S]*?"""', "", lb_code)      # drop module docstring
    check("link_budget.py defines an h_eff helper that returns h (image included)",
          re.search(r"def h_eff_monopole\(h\):\s*\n(?:.*\n)*?\s*return h\b", lb_code)
          is not None)
    check("link_budget.py feeds h_eff_monopole into the receive voltage",
          "v_oc = e * h_eff_monopole(h_rx)" in lb_code)
    check("link_budget.py no longer computes h/2 in executable code",
          not re.search(r"h_rx\s*/\s*2", lb_code))
    check("link_budget.py fixes the peak-power-as-average defect",
          "radiation_resistance(h) / 2.0" in lb_code)
    check("link_budget.py documents the old defect for traceability",
          "defect A" in lb)
    check("link_budget.py warns not to 'fix' the audit script",
          'Do not "fix" that file' in lb)

    # the audit script must keep reproducing both defects -- it is the evidence
    lb_audit = read(a3 / "scripts/link_budget_audit.py")
    check("link_budget_audit.py still evaluates the h/2 convention on purpose",
          "H / 2" in lb_audit)
    check("link_budget_audit.py still records published_h_eff_m = H/2",
          '"published_h_eff_m": H / 2' in lb_audit)

    # convergence + VCE numbers quoted in the report
    summ = json.loads(read(a3 / "round2_20261116/summary.json"))
    txt = json.dumps(summ)
    check("summary.json reports 12 completed cases", '"completed_simulation_cases": 12' in txt
          or summ.get("completed_simulation_cases") == 12,
          str(summ.get("completed_simulation_cases")))

    d05 = json.loads(read(a3 / "round2_20261116/results/d05_metrics.json"))
    flat = json.dumps(d05)

    def find(obj, key):
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

    vce = find(d05, "minimum_QCE_VCE_V")
    check("d05 min QCE VCE = 0.167 V",
          vce is not None and abs(vce - 0.16706078) < 1e-6, str(vce))
    off_edge = find(d05, "minimum_VCE_offset_from_nearest_edge_us")
    check("min VCE sits 0.39 us from the nearest edge",
          off_edge is not None and abs(off_edge - 0.39075) < 0.001, str(off_edge))


# ---------------------------------------------------------- 8. json consistency
def check_json():
    p = REVIEW / "reclassification.json"
    if not check("reclassification.json exists", p.exists()):
        return
    try:
        data = json.loads(read(p))
    except Exception as exc:                     # noqa: BLE001
        check("reclassification.json parses", False, repr(exc))
        return
    check("reclassification.json parses", True)
    check("it records zero modified files", data.get("files_modified") == [])
    check("item 2 (course failure) is marked withdrawn",
          any(i["verdict"] == "withdrawn_no_basis"
              for i in data["reclassification"]["items"]))
    check("item 1 (14.3 dB) is marked retained",
          any(i["verdict"] == "retained_valid"
              for i in data["reclassification"]["items"]))
    check("class (c) is empty",
          data["am_alt3_target_audit"]["dependence_classification"]
          ["c_fully_dependent_on_50_ohm"] == [])


def main():
    print("=" * 78)
    print("AM-02.3 retrospective revision - read-only verification")
    print(ROOT)
    print("=" * 78)
    for fn in (check_course_document, check_tp3, check_library_defaults,
               check_final_matrix_bug, check_two_values, check_arithmetic,
               check_alt3, check_json):
        print(f"\n-- {fn.__name__} " + "-" * (60 - len(fn.__name__)))
        try:
            fn()
        except Exception as exc:                 # noqa: BLE001
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

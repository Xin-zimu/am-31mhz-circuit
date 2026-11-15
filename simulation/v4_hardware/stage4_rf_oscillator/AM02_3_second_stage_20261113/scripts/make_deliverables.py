# -*- coding: utf-8 -*-
"""AM-02.3 deliverables: matrix CSV, BOM, manifest."""
import csv
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import am023_lib as M  # noqa: E402

ROOT = M.ROOT

BOM = [
    ("R1", "2.2 kΩ", "1/4 W 1% 金属膜", "第二级 S6 基极偏置上", "偏置"),
    ("R2", "1.1 kΩ", "1/4 W 1%", "S6 基极偏置下", "偏置"),
    ("R3", "1 kΩ", "1/4 W 1%", "S6 级间直流回路 RLK", "接口"),
    ("RAX", "8.2 Ω", "1/4 W 5%", "S6 射极交流退化", "增益设定"),
    ("REA", "39 Ω", "1/4 W 5%", "S6 射极直流反馈", "直流稳定"),
    ("RSER", "10 Ω", "1/4 W 5%", "S6 输入匹配阻尼", "稳定"),
    ("LM", "820 nH", "空心/磁芯，Q≥40 @31 MHz", "S6 输入匹配串联电感", "匹配"),
    ("CM", "68 pF", "NP0 50 V", "S6 输入匹配并联电容", "匹配"),
    ("LTANK", "470 nH", "空心，Q≥50 @31 MHz", "S6 集电极谐振电感兼直流馈电", "谐振"),
    ("CT1", "100 pF", "NP0 50 V", "S6 集电极到输出抽头", "匹配"),
    ("CT2", "56 pF", "NP0 50 V", "S6 输出端到地抽头", "匹配"),
    ("CIN6", "10 nF", "X7R 50 V", "S6 输入隔直", "耦合"),
    ("CEA", "1 nF", "NP0 50 V", "S6 射极旁路", "旁路"),
    ("CLD", "10 pF", "NP0 50 V", "测试负载并联电容", "测试"),
]

BOM_S3 = [
    ("R1", "2.7 kΩ", "1/4 W 1%", "S3 基极偏置上", "偏置"),
    ("R2", "1.1 kΩ", "1/4 W 1%", "S3 基极偏置下", "偏置"),
    ("RAX", "2 Ω", "1/4 W 5%", "S3 射极退化", "增益"),
    ("REA", "100 Ω", "1/4 W 5%", "S3 射极直流反馈", "直流稳定"),
    ("LRFC", "2.2 µH", "轴向，SRF≥40 MHz", "S3 集电极扼流", "负载"),
    ("REB", "180 Ω", "1/4 W 5%", "S3 射随偏置", "输出级"),
    ("CIN2", "100 nF", "X7R 50 V", "S3 级间耦合", "耦合"),
    ("CEA", "1 nF", "NP0 50 V", "S3 射极旁路", "旁路"),
    ("COUT2", "100 nF", "X7R 50 V", "S3 输出耦合", "耦合"),
    ("CLD", "10 pF", "NP0 50 V", "测试负载并联电容", "测试"),
]

CHANGES = [
    ("新增", "第二级 Q1 (2N3904)", "AM-02.2 之后新增，S6 或 S3 各 1 只"),
    ("新增", "LTANK 470 nH + CT1 100 pF + CT2 56 pF", "S6 谐振集电极与电容抽头"),
    ("新增", "LM 820 nH + CM 68 pF + RSER 10 Ω", "S6 输入匹配（S3 无此三项）"),
    ("新增", "LRFC 2.2 µH + REB 180 Ω", "S3 扼流负载与射随输出（S6 无此项）"),
    ("新增", "RLK 10 kΩ", "AM-01 输出节点直流回路，必须有"),
    ("未改", "AM-01 全部元件", "冻结"),
    ("未改", "方案 A 全部元件", "冻结"),
]


def main():
    rows = []
    for name, path in (("final_matrix", "final_matrix.json"),
                       ("load2k", "load2k_matrix.json")):
        p = ROOT / "results" / path
        if p.exists():
            for r in json.loads(p.read_text(encoding="utf-8")):
                r["source"] = name
                rows.append(r)

    fields = ["source", "config", "load_ohm", "amp_vpp", "duty_pct", "vpp_high",
              "vpp_low", "step_vpp", "modulation_index", "thd_high_pct",
              "thd_low_pct", "supply_mw", "qa_vce_high_v", "ca_min_v", "ca_max_v",
              "plateau_flatness", "overshoot", "cap_v", "cir_sha256"]
    with (ROOT / "AM02_3_matrix.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    with (ROOT / "AM02_3_BOM.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["方案", "位号", "值", "规格", "用途", "类别"])
        for row in BOM:
            w.writerow(["S6（推荐）"] + list(row))
        for row in BOM_S3:
            w.writerow(["S3（备选）"] + list(row))

    with (ROOT / "AM02_3_BOM_changes.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["类型", "对象", "说明"])
        for row in CHANGES:
            w.writerow(row)

    # manifest
    lines = []
    for path in sorted(ROOT.rglob("*")):
        if path.is_dir() or path.name == "SHA256SUMS.txt":
            continue
        if path.suffix == ".raw":
            continue
        h = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{h}  {path.relative_to(ROOT).as_posix()}")
    (ROOT / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"matrix rows: {len(rows)}")
    print(f"manifest files: {len(lines)}")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""补漏：对账本中 FAIL 的文件补指标+图，并更新账本 SHA256 行。"""
import json
import os
import re
import sys

sys.path.insert(0, r"D:\实验报告文件夹\电路2\raw归档")
from raw_archive import extract_one

# (账本md路径, raw所在目录, 需要补的raw文件名列表)
CASES = [
    (r"D:\实验报告文件夹\电路2\raw归档\s04_power_20261016_归档\归档记录.md",
     r"D:\ms_xsp\s04_power_20261016",
     ["monitor_control.raw"]),
    (r"D:\实验报告文件夹\电路2\raw归档\s04_poly_20261016_verified_归档\归档记录.md",
     r"D:\ms_xsp\s04_poly_20261016\verified",
     ["truth_table.raw"]),
    (r"D:\实验报告文件夹\电路2\raw归档\s04_c518062_20261016_归档\归档记录.md",
     r"D:\ms_xsp\s04_c518062_20261016",
     ["lowdrive_port_ac.raw"]),
]

for ledger, raw_dir, names in CASES:
    arch_dir = os.path.dirname(ledger)
    met_dir = os.path.join(arch_dir, "metrics")
    fig_dir = os.path.join(arch_dir, "figures")
    for name in names:
        p = os.path.join(raw_dir, name)
        if not os.path.exists(p):
            print("跳过（已不存在）:", p)
            continue
        m = extract_one(p, os.path.join(met_dir, name + ".json"),
                        os.path.join(fig_dir, name + ".png"), max_vars=2, title=name)
        with open(ledger, "r", encoding="utf-8") as f:
            text = f.read()
        new_row = "| %s | %.2f | %s | %s | %s | OK |" % (
            name, m["meta"]["size_bytes"] / 1048576.0, m["meta"]["sha256"],
            m["meta"]["plotname"], m["meta"]["n_points"])
        text = re.sub(r"^\| %s \|.*\|$" % re.escape(name), new_row, text, flags=re.M)
        with open(ledger, "w", encoding="utf-8") as f:
            f.write(text)
        print("补录:", name)
print("补漏完成")

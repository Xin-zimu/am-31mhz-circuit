# -*- coding: utf-8 -*-
"""为 2 个截断的 LTspice .op.raw 手工登记（仅头部+哈希，不解析数据）。"""
import json
import os
import re
import sys

sys.path.insert(0, r"D:\实验报告文件夹\电路2\raw归档")
from raw_archive import parse_raw_header, sha256_file

CASES = [
    (r"D:\实验报告文件夹\电路2\simulation\rf\rf_chain.op.raw",
     r"D:\实验报告文件夹\电路2\raw归档\ws_rf_归档\归档记录.md"),
    (r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2\ltspice_netlist\AD835_Behav_Model.op.raw",
     r"D:\实验报告文件夹\电路2\raw归档\ws_v4_hardware__stage_am_ad835_2__ltspice_netlist_归档\归档记录.md"),
]

for path, ledger in CASES:
    if not os.path.exists(path):
        print("跳过（不存在）:", path)
        continue
    info, blob = parse_raw_header(path)
    h = sha256_file(path)
    size = os.path.getsize(path)
    name = os.path.basename(path)
    meta = {
        "file": name, "title": info.get("title", ""), "date": info.get("date", ""),
        "plotname": info.get("plotname", ""), "flags": info.get("flags", ""),
        "n_points": info["n_points"], "n_variables": info["n_variables"],
        "sha256": h, "size_bytes": size, "is_ac": False,
        "note": "LTspice 截断的操作点输出：数据段不完整，仅登记头部与哈希，未解析波形",
    }
    out_dir = os.path.dirname(ledger)
    met_dir = os.path.join(out_dir, "metrics")
    os.makedirs(met_dir, exist_ok=True)
    with open(os.path.join(met_dir, name + ".json"), "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "variables": {}}, f, ensure_ascii=False, indent=1)
    if os.path.exists(ledger):
        with open(ledger, "r", encoding="utf-8") as f:
            text = f.read()
        new_row = "| %s | %.2f | %s | %s | %s | 仅登记（数据截断） |" % (
            name, size / 1048576.0, h, info.get("plotname", "?"), info["n_points"])
        if re.search(r"^\| %s \|" % re.escape(name), text, re.M):
            text = re.sub(r"^\| %s \|.*\|$" % re.escape(name), new_row, text, flags=re.M)
        else:
            text = text.rstrip() + "\n" + new_row + "\n"
        with open(ledger, "w", encoding="utf-8") as f:
            f.write(text)
        print("登记:", name)
    else:
        print("账本不存在，跳过:", ledger)

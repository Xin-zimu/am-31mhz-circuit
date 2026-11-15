# -*- coding: utf-8 -*-
"""核验账本 SHA256 与实际文件一致，通过后删除 raw。"""
import json
import os
import re
import sys
import hashlib

ledger = sys.argv[1]
raw_dir = sys.argv[2]
do_delete = len(sys.argv) > 3 and sys.argv[3] == "--delete"

with open(ledger, "r", encoding="utf-8") as f:
    text = f.read()

rows = []
for line in text.splitlines():
    m = re.match(r"^\|\s*([^|]+?)\s*\|\s*([\d.]+)\s*\|\s*([0-9A-F]{64})\s*\|", line)
    if m:
        rows.append((m.group(1).strip(), m.group(2), m.group(3)))

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()

mismatch = []
missing = []
deleted = []
for fname, size_mb, want in rows:
    p = os.path.join(raw_dir, fname)
    if not os.path.exists(p):
        missing.append(fname)
        continue
    got = sha256(p)
    if got != want:
        mismatch.append((fname, got))
        continue
    if do_delete:
        os.remove(p)
        deleted.append(fname)

print("账本行数:", len(rows))
print("文件缺失:", len(missing))
for m in missing:
    print("  MISSING", m)
print("哈希不符:", len(mismatch))
for m in mismatch:
    print("  MISMATCH", m[0], m[1])
print("已删除:", len(deleted))
if mismatch or missing:
    sys.exit(2)
print("核验通过" + ("，删除完成" if do_delete else ""))

# -*- coding: utf-8 -*-
"""Hash the AM-02.2 evidence set, excluding transient raw files."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


lines = []
for path in sorted(ROOT.rglob("*")):
    if not path.is_file():
        continue
    rel = path.relative_to(ROOT)
    if "raw" in rel.parts or path.suffix == ".raw" or path.name == "SHA256SUMS.txt":
        continue
    lines.append(f"{sha(path)}  {rel}")
(ROOT / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("Wrote", ROOT / "SHA256SUMS.txt", len(lines), "files")

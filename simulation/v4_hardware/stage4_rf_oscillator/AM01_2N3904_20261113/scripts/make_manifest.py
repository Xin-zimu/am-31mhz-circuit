# -*- coding: utf-8 -*-
"""Create SHA-256 manifests for the frozen baseline and AM-01 evidence."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_manifest(path, entries):
    lines = []
    for item in entries:
        if item.exists():
            lines.append(f"{sha(item)}  {item.relative_to(ROOT) if item.is_relative_to(ROOT) else item}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    baseline = sorted((ROOT / "baseline").glob("*"))
    external = [
        Path("D:/实验报告文件夹/电路2/simulation/v4_hardware/repair_20261011/final_actual.cir"),
        Path("D:/实验报告文件夹/电路2/simulation/v4_hardware/AM_20k_31MHz_V4_3_REPAIRED.ms14"),
    ]
    write_manifest(ROOT / "baseline" / "SHA256SUMS.txt", baseline + [p for p in external if p.exists()])
    entries = []
    for item in ROOT.rglob("*"):
        if not item.is_file():
            continue
        rel = item.relative_to(ROOT)
        if any(part == "raw" for part in rel.parts):
            continue
        if item.suffix == ".raw":
            continue
        if item.name in ("SHA256SUMS.txt",):
            continue
        entries.append(item)
    write_manifest(ROOT / "SHA256SUMS.txt", sorted(entries))
    print("Manifests written")


if __name__ == "__main__":
    main()

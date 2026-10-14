"""Read-only: has anything been modified, and which file is open in Multisim?

Compares the 11 archived source files against their recorded hashes.
"""
from pathlib import Path
import json
import hashlib

S = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance')
E = S / '副本专用文件夹/gui_evidence_20261014'
ref = json.loads((E / 'source_hash_verification.json').read_text(encoding='utf-8'))

print('=' * 92)
print('1. THE 11 ARCHIVED SOURCES -- intact?')
print('=' * 92)
all_ok = True
for rec in ref:
    src = Path(rec['source']['path'])
    if not src.exists():
        print(f'  MISSING  {src.name}')
        all_ok = False
        continue
    h = hashlib.sha256(src.read_bytes()).hexdigest()
    ok = h == rec['source']['sha256']
    all_ok &= ok
    print(f'  {"OK  " if ok else "CHANGED"}  {src.name:46s} {src.stat().st_size:>9d} B')
print()
print(f'  ALL 11 UNCHANGED: {all_ok}')

print()
print('=' * 92)
print('2. EVERY S03_GUI_COLD_20us* FILE ON DISK')
print('=' * 92)
hits = []
for base in [S, S / '副本专用文件夹', E, Path(r'D:\ms_xsp')]:
    if not base.exists():
        continue
    for p in base.rglob('S03_GUI_COLD_20us*'):
        if p.is_file():
            hits.append(p)
for p in sorted(set(hits), key=lambda x: str(x)):
    print(f'  {p.stat().st_mtime:>0.0f}  {p.stat().st_size:>9d} B  {p}')
    import datetime
    print(f'      {datetime.datetime.fromtimestamp(p.stat().st_mtime)}')

print()
print('=' * 92)
print('3. ANY FILE IN THE WORKSPACE MODIFIED AFTER 14:40 TODAY')
print('=' * 92)
cut = 0  # epoch compare via mtime of a known time
import datetime
cutoff = datetime.datetime(2026, 10, 14, 14, 40).timestamp()
recent = []
for p in Path(r'D:\实验报告文件夹\电路2').rglob('*'):
    if p.is_file() and p.stat().st_mtime > cutoff:
        recent.append(p)
if recent:
    for p in sorted(recent, key=lambda x: -x.stat().st_mtime):
        print(f'  {datetime.datetime.fromtimestamp(p.stat().st_mtime)}  {p.stat().st_size:>9d} B  {p}')
else:
    print('  (none -- no workspace file written since 14:40)')

print()
print('=' * 92)
print('4. READING OF THE EVIDENCE-FOLDER PROJECT')
print('=' * 92)
for n in ['S03_GUI_COLD_20us.ms14', 'S03_GUI_COLD_20us (Security copy)'.replace(' (Security copy)', '.ms14 (Security copy)'),
          'S03_GUI_COLD_20us_input.ms14']:
    p = E / n
    if p.exists():
        print(f'  {n:46s} {p.stat().st_size:>9d} B  sha256={hashlib.sha256(p.read_bytes()).hexdigest()[:16]}')

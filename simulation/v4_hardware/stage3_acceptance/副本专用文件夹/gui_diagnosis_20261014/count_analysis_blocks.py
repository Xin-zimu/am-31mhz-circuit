"""Read-only: how many transient analysis blocks does each project hold, and
which one is active? Determines whether the saved snapshot can be trusted as
'the settings that ran'.

No simulator calls.
"""
from pathlib import Path
import re

S = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance')
NEW = S / '副本专用文件夹/gui_evidence_20261014/S03_GUI_COLD_20us_saved.xml'

for name, path in [('gui_2ms_saved_settings.xml', S / 'gui_2ms_saved_settings.xml'),
                   ('gear500_uic_settings.xml', S / 'gear500_uic_settings.xml'),
                   ('NEW saved (reltol1e3 run)', NEW)]:
    if not path.exists():
        print(f'{name}: MISSING')
        continue
    t = path.read_text(encoding='utf-8', errors='replace')
    print('=' * 96)
    print(f'{name}   ({len(t)} chars)')
    print('=' * 96)
    print(f"  'TRAN:list{{'      occurrences = {len(re.findall(r'TRAN:list[{]', t))}")
    print(f"  'ANALYSIS:list{{'  occurrences = {len(re.findall(r'ANALYSIS:list[{]', t))}")
    print(f"  'ASYS_OPT:list{{'  occurrences = {len(re.findall(r'ASYS_OPT:list[{]', t))}")
    print(f'  USE:long      = {re.findall(r"USE:long[{](-?\d+)[}]", t)[:6]}')
    print(f'  CURRENT_ID    = {re.findall(r"CURRENT_ID:long[{](-?\d+)[}]", t)[:6]}')
    ts = re.findall(r'TSTEP:\w*[{]([^}]*)[}]', t)
    tp = re.findall(r'TSTOP:\w*[{]([^}]*)[}]', t)
    ta = re.findall(r'TSTART:\w*[{]([^}]*)[}]', t)
    print(f'  TSTEP  sequence = {ts[:10]}')
    print(f'  TSTOP  sequence = {tp[:10]}')
    print(f'  TSTART sequence = {ta[:10]}')

    # Identify every analysis the project stores, with its id and title
    ids = re.findall(r'ID:long[{](\d+)[}]\s*\n?\s*(?:Name|Title|PLOT_TITLE|READABLE_NAME)', t)
    print(f'  analysis ids following a name/title field: {ids[:10]}')

    # locate each ASYS_OPT and report the reltol right after it
    for k, m in enumerate(re.finditer(r'ASYS_OPT:list[{]', t)):
        seg = t[m.start():m.start() + 9000]
        rel = re.search(r'IsEnabled:long[{]([01])[}]\s+reltol:\w*[{]([^}]*)[}]', seg)
        trt = re.search(r'IsEnabled:long[{]([01])[}]\s+trtol:\w*[{]([^}]*)[}]', seg)
        itl = re.search(r'IsEnabled:long[{]([01])[}]\s+itl4:\w*[{]([^}]*)[}]', seg)
        print(f'    ASYS_OPT #{k}: reltol={rel.groups() if rel else None} '
              f'trtol={trt.groups() if trt else None} itl4={itl.groups() if itl else None}')
    print()

"""Read-only: what tolerance does the NEWLY SAVED project record?

Compares the newly decoded project (post-RELTOL change) with the old saved dump
(pre-change), locating the TRANSIENT analysis's own option block in each.

No simulator calls.
"""
from pathlib import Path
import re
import json

E = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹\gui_evidence_20261014')
S = E.parent.parent
OUT = Path(__file__).resolve().parent

CASES = [
    ('OLD project dump (pre-change, FAILED)', S / '副本专用文件夹/gui_evidence_20261014/S03_GUI_COLD_20us_saved.xml'),
    ('NEW project dump (post-change, PASSED)', E / 'S03_GUI_COLD_20us_reltol1e3_decoded.xml'),
]

KEYS = ['TSTEP', 'TSTOP', 'TSTART', 'TMAX', 'IC', 'reltol', 'trtol', 'itl4',
        'method', 'maxord', 'suposc', 'rshunt']


def all_opt_blocks(text):
    """Every ASYS_OPT block with its enabled flags, in document order."""
    out = []
    for k, m in enumerate(re.finditer(r'ASYS_OPT:list[{]', text)):
        seg = text[m.start():m.start() + 12000]
        d = {}
        for key in KEYS:
            mm = re.search(r'IsEnabled:long[{]([01])[}]\s+' + key + r':\w*[{]([^}]*)[}]', seg)
            if mm:
                d[key] = {'enabled': mm.group(1) == '1', 'value': mm.group(2)}
        out.append(d)
    return out


report = {}
for label, path in CASES:
    if not path.exists():
        print(f'{label}: MISSING {path}')
        continue
    text = path.read_text(encoding='utf-8', errors='replace')
    blocks = all_opt_blocks(text)

    # the transient analysis settings block
    i = text.find('TRAN:list{')
    j = text.find('ANALYSIS:list{', i)
    tran_seg = text[i:j + 400] if i >= 0 and j > i else ''
    tran = {}
    for key in ['TSTEP', 'TSTOP', 'TSTART', 'TMAX', 'IC']:
        m = re.search(key + r':\w*[{]([^}]*)[}]', tran_seg)
        if m:
            tran[key] = m.group(1)

    print('=' * 100)
    print(label)
    print('=' * 100)
    print(f'  file    : {path.name}  ({path.stat().st_size/1e6:.2f} MB)')
    print(f'  TRAN block: ' + ', '.join(f'{k}={v}' for k, v in tran.items()))
    print(f'  ASYS_OPT blocks found: {len(blocks)}')
    print()
    print('  every block that has any option ENABLED:')
    for k, b in enumerate(blocks):
        on = {key: v['value'] for key, v in b.items() if v['enabled']}
        if on:
            print(f'    #{k:2d}: {on}')
    report[label] = {'tran': tran, 'n_blocks': len(blocks),
                     'enabled_blocks': [{kk: vv['value'] for kk, vv in b.items() if vv['enabled']}
                                        for b in blocks]}

    # Decide which block the transient analysis actually uses.
    print()

(OUT / 'new_project_settings.json').write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

# --- direct textual comparison of the two dumps around reltol
a = CASES[0][1].read_text(encoding='utf-8', errors='replace')
b = CASES[1][1].read_text(encoding='utf-8', errors='replace')
print('=' * 100)
print('DIRECT TEXT DIFF OF ALL reltol/trtol OCCURRENCES')
print('=' * 100)


def reltol_patterns(t):
    return re.findall(r'IsEnabled:long[{]([01])[}]\s+(reltol|trtol):\w*[{]([^}]*)[}]', t)


pa, pb = reltol_patterns(a), reltol_patterns(b)
print(f'  OLD: {len(pa)} occurrences')
print(f'  NEW: {len(pb)} occurrences')
print()
print(f'  OLD enabled reltol/trtol values: {sorted({(v, ) for f2, k, v in pa if f2 == "1"})}')
print(f'  NEW enabled reltol/trtol values: {sorted({(v, ) for f2, k, v in pb if f2 == "1"})}')
print()
print('  side-by-side enabled entries:')
print(f'    {"OLD":>40s} | {"NEW":>40s}')
for k in range(max(len(pa), len(pb))):
    l = f'{pa[k][1]}={pa[k][2]} (en={pa[k][0]})' if k < len(pa) else ''
    r = f'{pb[k][1]}={pb[k][2]} (en={pb[k][0]})' if k < len(pb) else ''
    if 'en=1' in l or 'en=1' in r or k < 6:
        print(f'    {l:>40s} | {r:>40s}')

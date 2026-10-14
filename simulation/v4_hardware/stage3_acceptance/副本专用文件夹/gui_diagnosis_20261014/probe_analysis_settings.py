"""Read-only: which analysis entry in the settings dumps is the transient one,
and what tolerance did each archived GUI run actually have enabled?

No simulator calls.
"""
from pathlib import Path
import re
import json

S = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance')
OUT = Path(__file__).resolve().parent

FILES = ['gui_saved_settings.xml', 'gui_2ms_saved_settings.xml',
         'cold_2ms_saved_settings.xml', 'cold_explicit_zero_settings.xml',
         'trap500_20us_settings.xml', 'gear500_20us_settings.xml',
         'gear500_uic_settings.xml', 'gear500_reopen_saved_settings.xml']

# The settings dump was produced by the project's own extractor. Find how
# analyses are declared, and dump one file's structure around 'reltol'.
p = S / 'gui_2ms_saved_settings.xml'
t = p.read_text(encoding='utf-8', errors='replace')
print('=' * 96)
print(f'STRUCTURE PROBE: {p.name}  ({len(t)} chars)')
print('=' * 96)

# look for the container that holds the 40 entries
for key in ['TRAN', 'ANALYSIS', 'Analysis', 'analyses', 'Sheet', 'sheet']:
    idxs = [m.start() for m in re.finditer(re.escape(key), t)]
    print(f'  {key!r:12s} occurrences: {len(idxs)}')
print()

# Show the neighbourhood of the FIRST enabled reltol (expected: transient block)
m = re.search(r'IsEnabled:long\{([01])\}\s+reltol:\w+\{([^}]+)\}', t)
print('  first reltol entry at char', m.start() if m else None)
if m:
    lo = max(0, m.start() - 2600)
    print('  --- context before the first reltol entry ---')
    print(t[lo:m.start() + 200])

print()
print('=' * 96)
print('ALL ANALYSIS BLOCKS: name / enabled tolerances')
print('=' * 96)


def blocks(text):
    """Split on the analysis-container boundaries the dump uses."""
    # entries appear as repeated groups; find every 'reltol' with its enabled flag
    out = []
    for mm in re.finditer(r'IsEnabled:long\{([01])\}\s+reltol:\w+\{([^}]+)\}', text):
        start = mm.start()
        # find the nearest preceding name-like field
        head = text[max(0, start - 3000):start]
        names = re.findall(r'(?:Name|Title|Analysis|Type|_?name)\w*:\w*\{([^}]{1,40})\}', head)
        out.append({'enabled': mm.group(1), 'reltol': mm.group(2),
                    'nearby_names': names[-3:]})
    return out


for name in FILES:
    f = S / name
    if not f.exists():
        continue
    tt = f.read_text(encoding='utf-8', errors='replace')
    bl = blocks(tt)
    enabled = [b for b in bl if b['enabled'] == '1']
    print(f'\n  {name}')
    print(f'    total reltol entries: {len(bl)}   ENABLED: {len(enabled)}')
    for b in enabled:
        print(f'      enabled reltol = {b["reltol"]}   names={b["nearby_names"]}')
    # trtol / itl4 / method at the same enabled slot
    for key in ['trtol', 'itl4', 'method', 'maxord', 'suposc']:
        vals = re.findall(r'IsEnabled:long\{([01])\}\s+' + key + r':\w*\{([^}]+)\}', tt)
        en = [v for fl, v in vals if fl == '1']
        if en:
            print(f'      enabled {key:8s} = {sorted(set(en))}')

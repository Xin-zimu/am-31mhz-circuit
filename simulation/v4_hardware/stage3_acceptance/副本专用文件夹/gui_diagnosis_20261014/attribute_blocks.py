"""Read-only: which analysis block is the TRANSIENT one, in each project?

The saved dumps hold 40 ASYS_OPT blocks. Identify the block belonging to the
transient analysis that actually ran, by matching TSTOP to the known run length.

No simulator calls.
"""
from pathlib import Path
import re
import json

S = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance')
E = S / '副本专用文件夹/gui_evidence_20261014'
OUT = Path(__file__).resolve().parent

# name -> (file, the TSTOP the run actually used)
CASES = [
    ('PRECHARGED 2 ms GUI (PASSED)', S / 'gui_2ms_saved_settings.xml', '0.002'),
    ('PRECHARGED 2 ms cold-named', S / 'cold_2ms_saved_settings.xml', '0.002'),
    ('COLD 20 us gear UIC (FAILED)', S / 'gear500_uic_settings.xml', '2e-05'),
    ('COLD 20 us UIC reltol1e3 (PASSED)', E / 'S03_GUI_COLD_20us_reltol1e3_decoded.xml', '2e-05'),
]

print('=' * 104)
print('FIND THE ANALYSIS BLOCK WHOSE TSTOP MATCHES THE RUN')
print('=' * 104)
report = {}
for label, path, tstop in CASES:
    if not path.exists():
        print(f'\n  {label}: MISSING')
        continue
    t = path.read_text(encoding='utf-8', errors='replace')
    # every TSTOP with its char offset
    hits = [(m.start(), m.group(1)) for m in re.finditer(r'TSTOP:\w*[{]([^}]*)[}]', t)]
    print(f'\n  {label}')
    print(f'    file: {path.name}')
    print(f'    TSTOP values found: {[h[1] for h in hits]}')
    match = [h for h in hits if h[1].strip() == tstop]
    if not match:
        print(f'    -> no block with TSTOP == {tstop}; cannot attribute')
        continue
    off = match[0][0]
    print(f'    -> block at offset {off} has TSTOP={tstop}')

    # read TSTEP/TSTART/IC near it, then the nearest FOLLOWING ASYS_OPT
    head = t[max(0, off - 1200):off + 400]
    vals = {}
    for k in ['TSTEP', 'TSTOP', 'TSTART', 'TMAX', 'IC']:
        m = re.search(k + r':\w*[{]([^}]*)[}]', head)
        if m:
            vals[k] = m.group(1)
    print(f'       settings: {vals}')

    nxt = t.find('ASYS_OPT:list{', off)
    prv = t.rfind('ASYS_OPT:list{', 0, off)
    print(f'       nearest ASYS_OPT after  : {"yes" if nxt > 0 else "no"} '
          f'(distance {nxt-off if nxt > 0 else "n/a"})')
    print(f'       nearest ASYS_OPT before : {"yes" if prv > 0 else "no"} '
          f'(distance {off-prv if prv > 0 else "n/a"})')
    for tag, pos in [('BEFORE', prv), ('AFTER', nxt)]:
        if pos < 0:
            continue
        seg = t[pos:pos + 12000]
        got = {}
        for k in ['reltol', 'trtol', 'itl4', 'method']:
            m = re.search(r'IsEnabled:long[{]([01])[}]\s+' + k + r':\w*[{]([^}]*)[}]', seg)
            if m:
                got[k] = {'enabled': m.group(1) == '1', 'value': m.group(2)}
        on = {k: v['value'] for k, v in got.items() if v['enabled']}
        print(f'       {tag:6s} block options: {on}')
    report[label] = {'file': path.name, 'tstop': tstop, 'settings': vals}

print()
print('=' * 104)
print('WHAT WE CAN AND CANNOT ATTRIBUTE')
print('=' * 104)
print("""  CONFIRMED (single-block diff, cross-checked against the user's own
  Transient Options screenshots):
    S03_GUI_COLD_20us   1e-4/1  -> FAILED at 225.8 ns
    same project        1e-3/7  -> COMPLETED 20 us
    Exactly one option block changed.

  CONFIRMED (engine side, proven earlier):
    The command engine IGNORES .options entirely, so all engine data
    (nominal 5 ms, cold 5/7/9 ms) ran on SPICE defaults reltol 1e-3, trtol 7.

  NOT RELIABLY ATTRIBUTABLE:
    The pre-charged GUI 2 ms run's transient tolerance. Its saved dump holds
    multiple transient-like blocks and the extraction is ambiguous.
    => Do NOT claim it ran at 1e-3.
""")
(OUT / 'block_attribution.json').write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

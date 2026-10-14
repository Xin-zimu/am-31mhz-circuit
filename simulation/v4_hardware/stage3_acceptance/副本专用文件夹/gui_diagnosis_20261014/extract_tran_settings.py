"""Read-only: extract the TRANSIENT analysis block from each saved settings dump.

Uses the same scoping the earlier audit used: locate 'TRAN:list{' then the
following 'ANALYSIS:list{' and read the options inside it. This answers whether
the PASSING precharged GUI run and the FAILING cold-start GUI runs differed in
tolerance, or only in initial condition.

No simulator calls.
"""
from pathlib import Path
import re
import json

S = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance')
OUT = Path(__file__).resolve().parent

FILES = [
    ('2026-10-12 17:59', 'gui_saved_settings.xml', 'precharged 2 ms (early)'),
    ('2026-10-12 23:24', 'gui_2ms_saved_settings.xml', 'PRECHARGED 2 ms GUI -- PASSED'),
    ('2026-10-12 23:40', 'cold_2ms_saved_settings.xml', 'precharged-ish 2 ms'),
    ('2026-10-13 13:23', 'cold_explicit_zero_settings.xml', 'explicit zero IC'),
    ('2026-10-13 18:26', 'trap500_20us_settings.xml', 'COLD 20 us trap -- FAILED'),
    ('2026-10-13 18:34', 'gear500_20us_settings.xml', 'COLD 20 us gear -- FAILED'),
    ('2026-10-13 23:35', 'gear500_reopen_saved_settings.xml', 'COLD 20 us gear reopen -- FAILED'),
    ('2026-10-13 23:45', 'gear500_uic_settings.xml', 'COLD 20 us gear UIC -- FAILED'),
]

KEYS = ['TSTEP', 'TSTOP', 'TSTART', 'TMAX', 'IC', 'reltol', 'trtol', 'itl4',
        'method', 'maxord', 'abstol', 'vntol', 'chgtol', 'gmin', 'suposc',
        'converlimit', 'rshunt']


def tran_block(text):
    """Return the substring of the transient analysis options."""
    i = text.find('TRAN:list{')
    if i < 0:
        return None, 'no TRAN:list'
    j = text.find('ANALYSIS:list{', i)
    if j < 0:
        return None, 'no ANALYSIS:list after TRAN'
    # the options live in the ASYS_OPT list inside this analysis
    k = text.find('ASYS_OPT:list{', j)
    if k < 0:
        return text[j:j + 6000], 'no ASYS_OPT (raw slice)'
    return text[k:k + 9000], 'ok'


print('=' * 104)
print('TRANSIENT ANALYSIS SETTINGS AS SAVED IN EACH PROJECT')
print('=' * 104)
rows = []
for stamp, name, note in FILES:
    p = S / name
    if not p.exists():
        print(f'\n  {name}: MISSING')
        continue
    text = p.read_text(encoding='utf-8', errors='replace')
    sec, how = tran_block(text)
    rec = {'file': name, 'note': note, 'extraction': how}
    if sec:
        for key in KEYS:
            m = re.search(r'IsEnabled:long\{([01])\}\s+' + key + r':\w*\{([^}]*)\}', sec)
            if m:
                rec[key] = {'enabled': m.group(1) == '1', 'value': m.group(2)}
            else:
                m2 = re.search(r'\b' + key + r':\w*\{([^}]*)\}', sec)
                if m2:
                    rec[key] = {'enabled': None, 'value': m2.group(1)}
    rows.append(rec)

    print(f'\n  [{stamp}] {name}')
    print(f'    {note}   (extraction: {how})')
    for key in KEYS:
        if key in rec:
            e = rec[key]['enabled']
            flag = 'ON ' if e is True else ('off' if e is False else ' ? ')
            print(f'      {flag} {key:12s} = {rec[key]["value"]}')

print()
print('=' * 104)
print('SUMMARY TABLE')
print('=' * 104)
hdr = f'  {"project":46s} {"TSTEP/TMAX":>16s} {"IC":>8s} {"reltol":>16s} {"trtol":>13s} {"itl4":>13s}'
print(hdr)
print('  ' + '-' * (len(hdr) - 2))
for rec in rows:
    def g(k):
        if k not in rec:
            return '--'
        v = rec[k]['value']
        e = rec[k]['enabled']
        return f'{v}{"" if e in (True, None) else " (off)"}'
    tt = f'{g("TSTEP")}/{g("TMAX")}'
    print(f'  {rec["note"]:46s} {tt:>16s} {g("IC"):>8s} '
          f'{g("reltol"):>16s} {g("trtol"):>13s} {g("itl4"):>13s}')

(OUT / 'tran_settings_by_project.json').write_text(
    json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
print()
print(f'written: {OUT / "tran_settings_by_project.json"}')

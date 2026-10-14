"""Read-only: which potentiometer CSV row does the ACCEPTED baseline correspond to?

The accepted nominal_full.cir has RVRF=15288.9, RVDT=7362.47, RVDB=2637.53,
RVAT=1847.93, RVAB=18152.1. Find that row, then take the 2 Vpp row that differs
ONLY in RVAT/RVAB (i.e. the same D), so receive gain and duty stay fixed.
"""
from pathlib import Path
import csv

CSV = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\potentiometer_settings.csv')
text = CSV.read_text(encoding='utf-8-sig')      # strip BOM
rows = list(csv.DictReader(text.splitlines()))
# normalise any residual BOM on the first key
rows = [{k.lstrip('\ufeff'): v for k, v in r.items()} for r in rows]

BASE = {'RVRF': 15288.9, 'RVDT': 7362.47, 'RVDB': 2637.53,
        'RVAT': 1847.93, 'RVAB': 18152.1}

print('=' * 92)
print('FIND THE ROW MATCHING THE ACCEPTED BASELINE')
print('=' * 92)
found = None
for r in rows:
    ok_rvdt = abs(float(r['RVDT_ohm']) - BASE['RVDT']) < 0.01
    ok_rvdb = abs(float(r['RVDB_ohm']) - BASE['RVDB']) < 0.01
    ok_rvat = abs(float(r['RVAT_ohm']) - BASE['RVAT']) < 0.01
    ok_rvab = abs(float(r['RVAB_ohm']) - BASE['RVAB']) < 0.1
    if ok_rvdt and ok_rvdb and ok_rvat and ok_rvab:
        found = r
        print(f"  MATCH: D={r['D_percent']}%  Vpp={r['Vpp']}")
        for k in ['RVRF_ohm', 'RVDT_ohm', 'RVDB_ohm', 'RVAT_ohm', 'RVAB_ohm']:
            print(f'    {k:10s} = {r[k]}')
if not found:
    print('  no exact row match')
    raise SystemExit(1)

D = found['D_percent']
print()
print('=' * 92)
print(f'ALL ROWS AT D={D}%  (same duty/attenuator bias, differing Vpp)')
print('=' * 92)
print(f"  {'Vpp':>5s} {'RVAT':>14s} {'RVAB':>14s} {'RVDT':>12s} {'RVDB':>12s}")
for r in rows:
    if r['D_percent'] == D:
        print(f"  {r['Vpp']:>5s} {float(r['RVAT_ohm']):>14.6f} {float(r['RVAB_ohm']):>14.6f} "
              f"{float(r['RVDT_ohm']):>12.4f} {float(r['RVDB_ohm']):>12.4f}")

print()
print('=' * 92)
print('THE 2 Vpp TARGET (same D, receiver chain untouched)')
print('=' * 92)
for r in rows:
    if r['D_percent'] == D and r['Vpp'] == '2':
        for k in ['RVRF_ohm', 'RVDT_ohm', 'RVDB_ohm', 'RVAT_ohm', 'RVAB_ohm']:
            same = ''
            if k in ('RVDT_ohm', 'RVDB_ohm', 'RVRF_ohm'):
                same = '  (unchanged from baseline)'
            print(f'    {k:10s} = {r[k]}{same}')
        print()
        print(f"  => swap ONLY rRVAT -> {r['RVAT_ohm']}")
        print(f"     and        rRVAB -> {r['RVAB_ohm']}")
        out = {'D_percent': D, 'RVAT_ohm': r['RVAT_ohm'], 'RVAB_ohm': r['RVAB_ohm'],
               'baseline_RVAT_ohm': found['RVAT_ohm'],
               'baseline_RVAB_ohm': found['RVAB_ohm']}
        import json
        (Path(__file__).resolve().parent / 'target_2vpp.json').write_text(
            json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
        print()
        print(f"  written: {Path(__file__).resolve().parent / 'target_2vpp.json'}")

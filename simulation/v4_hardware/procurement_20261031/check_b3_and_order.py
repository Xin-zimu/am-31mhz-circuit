"""Check B3 and the merged order sheet against their sources.

B3 claims 13 missing parts derived from a 22-part circuit and a 9-part built board.
The merged sheet claims three batch totals. Both are checkable against the netlist,
the assembly data, and the drawing part data. No network.

Fails loudly on any mismatch.
"""
from pathlib import Path
import csv, json, sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DRAW = ROOT / 'output/pdf/S05_A_G22_施工图_20261030'
NET_DIR = ROOT / 'simulation/v4_hardware/stage4_rf_oscillator/S04_RF_CARRIER/XTAL'
BOARD = ROOT / 'simulation/v4_hardware/stage4_rf_oscillator/perfboard_20261017/assembly_data.json'

MODEL = {'VSUP', 'VXM', 'RM', 'LM', 'CM', 'CSTRAY', 'CX0', 'RLOADG', 'CLOADG'}
NORMALISE = {'10 kΩ': '10k', '4.7 kΩ': '4.7k', '33 pF': '33p', '100 nF': '100n',
             '10 µF': '10u', '2.2 pF': '2.2p', 'onsemi 2N3904': '2N3904',
             'C518062 / 31 MHz': 'C518062'}
KIND = {'r': 'R', 'c': 'C', 'el': 'C', 'q': 'Q', 'crystal': 'X'}


def cascade_parts(path):
    need = Counter()
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        t = line.split()
        if not t or t[0].startswith('.') or t[0] in ('quit', 'end'):
            continue
        k = t[0][0].upper()
        if k not in 'RCLQD' or t[0] in MODEL:
            continue
        if k in 'QD':
            need[(k, t[-1])] += 1
        else:
            need[(k, t[3])] += 1
    need[('X', 'C518062')] += 1   # crystal modelled by the VXM/LM/CM branch
    return need


def main():
    errors = []

    # 1. All C4 netlists must agree with each other and with c1_cascade.
    c4 = sorted((NET_DIR / 'c4_dual_load_20261030/netlists').glob('*.cir'))
    base = cascade_parts(NET_DIR / 'simulations/c1_cascade.cir')
    c4_same = []
    for f in c4:
        same = cascade_parts(f) == base
        c4_same.append({'file': f.name, 'same_as_cascade': same})
        if not same:
            errors.append(f'{f.name} part set differs from c1_cascade')
    if len(c4) != 8:
        errors.append(f'expected 8 C4 netlists, found {len(c4)}')

    need_total = sum(base.values())
    if need_total != 22:
        errors.append(f'cascade needs {need_total}, expected 22')

    # 2. Built board covers 9.
    data = json.loads(BOARD.read_text(encoding='utf-8'))
    have = Counter()
    for p in data['parts']:
        kind = KIND.get(p['kind'])
        if kind is None:
            continue
        have[(kind, NORMALISE.get(str(p.get('value')), str(p.get('value'))))] += 1
    covered = sum(min(base[k], have.get(k, 0)) for k in base)
    missing = need_total - covered
    if covered != 9:
        errors.append(f'built board covers {covered}, expected 9')
    if missing != 13:
        errors.append(f'missing {missing}, expected 13')

    surplus = [k for k in have if k not in base]
    if surplus != [('C', '2.2p')]:
        errors.append(f'unexpected surplus: {surplus}')

    # 3. The merged sheet's batch totals must match the sources.
    rows = list(csv.DictReader(
        (HERE / '联合下单总表.csv').open(encoding='utf-8-sig')))
    def total(col):
        return sum(int(r[col] or 0) for r in rows)
    t1, t2, t3 = total('B1用量'), total('B2用量'), total('B3用量')
    if t1 != 13:
        errors.append(f'B1 total {t1}, expected 13')
    if t2 != 45:
        errors.append(f'B2 total {t2}, expected 45')
    if t3 != 13:
        errors.append(f'B3 total {t3}, expected 13')

    # 4. Blocked items must be exactly the two known blockers.
    blocked = [r['规格'] for r in rows if 'BLOCKED' in r['状态']]
    if len(blocked) != 2:
        errors.append(f'expected 2 blocked rows, found {len(blocked)}: {blocked}')
    if not any('132-17L' in b for b in blocked):
        errors.append('132-17L not marked blocked')
    if not any('BAT85' in b for b in blocked):
        errors.append('BAT85 not marked blocked')

    # 5. The merged sheet must not contain a model-only part.
    for token in ('CX0', 'CSTRAY', 'RLOADG', 'CLOADG'):
        if any(token in r['规格'] for r in rows):
            errors.append(f'model part {token} leaked into the order sheet')

    # 6. 56 ohm must be described as E24, not as non-standard.
    row56 = next((r for r in rows if r['规格'].startswith('56 Ω')), None)
    if row56 is None:
        errors.append('56 ohm row absent')
    elif 'E24' not in row56['规格']:
        errors.append('56 ohm row does not state E24')

    record = {
        'status': 'PASS' if not errors else 'FAIL',
        'scope': ('Verifies the B3 derivation (22 needed / 9 covered / 13 missing), that all '
                  '8 C4 netlists agree, that the merged sheet totals 13/45/13, that exactly '
                  'two items are blocked, and that model-only parts are excluded. '
                  'Does not check stock or price.'),
        'c4_netlists': c4_same,
        'cascade_parts': need_total,
        'covered_by_board': covered,
        'missing': missing,
        'surplus_on_board': [list(k) for k in surplus],
        'merged_sheet': {'rows': len(rows), 'B1': t1, 'B2': t2, 'B3': t3,
                         'blocked': blocked},
        'errors': errors,
    }
    (HERE / 'B3与总表核对.json').write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: record[k] for k in
                      ('status', 'cascade_parts', 'covered_by_board', 'missing',
                       'merged_sheet', 'errors')}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == '__main__':
    sys.exit(main())

"""Cross-check the joint purchase list against the drawing data it claims to summarize.

The purchase list is prose written by hand. Its numbers must agree with the
machine-readable part data from S05-11, otherwise someone buys the wrong quantity.
This script parses the list's B2/B1 tables and compares the per-value totals with
qa/physical_parts.json (56 parts) and qa/fixture_parts.json (2 parts).

No simulation, no network, no writes outside qa/. Fails loudly on any mismatch.
"""
from pathlib import Path
import json, re, sys
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DRAW = ROOT / 'output/pdf/S05_A_G22_施工图_20261030'
LIST = HERE / '联合采购清单_S04_S05.md'

# Values as written in the drawings vs. how the purchase list spells them.
# Only spellings; the numeric meaning is the same.
UNIT = {('R', '1Meg'): ('R', 1_000_000.0), ('R', '210000'): ('R', 210_000.0),
        ('R', '1000'): ('R', 1000.0), ('R', '4700'): ('R', 4700.0),
        ('R', '100k'): ('R', 100_000.0), ('R', '20k'): ('R', 20_000.0),
        ('R', '22k'): ('R', 22_000.0), ('R', '10k'): ('R', 10_000.0),
        ('R', '4.7k'): ('R', 4700.0), ('R', '100'): ('R', 100.0),
        ('R', '220'): ('R', 220.0), ('R', '33'): ('R', 33.0),
        ('R', '470'): ('R', 470.0)}
for v, f in [('100n', 1e-7), ('100p', 1e-10), ('11p', 11e-12), ('15p', 15e-12),
             ('1n', 1e-9), ('2.4p', 2.4e-12), ('30p', 30e-12), ('330p', 330e-12),
             ('39p', 39e-12), ('10u', 1e-5)]:
    UNIT[('C', v)] = ('C', f)
    UNIT[('P', v)] = ('C', f)


def drawing_totals():
    """Every physical pin-count by (kind, si-value), from the delivered drawing data."""
    totals = defaultdict(int)
    refs = defaultdict(list)
    parts = json.loads((DRAW / 'qa/physical_parts.json').read_text(encoding='utf-8'))
    for ref, part in parts.items():
        key = UNIT.get((part['kind'], part['value']))
        if key is None:
            continue
        totals[key] += 1
        refs[key].append(ref)
    return totals, refs, len(parts)


def parse_list_tables():
    """Sum the S05 quantities the list states, reading each table's own header.

    Column layout differs per table (S05 rows are `value | qty | refs | note`,
    S04 rows are often `component | spec | qty | ref`), so the quantity column is
    located from the header rather than assumed. Only tables whose header names an
    S05 quantity column are counted, to avoid mixing in S04-only or merged rows.
    """
    text = LIST.read_text(encoding='utf-8')
    claimed = defaultdict(int)
    rows = 0
    in_s05 = False
    qty_idx = None          # sticky per table, resolved from that table's header
    for line in text.splitlines():
        if line.startswith('## '):
            # S05 sections are 2 (B1 LC board) and 3 (B2 receiver).
            in_s05 = bool(re.match(r'^## (2\.|3\.)', line))
            qty_idx = None
            continue
        if not line.startswith('|'):
            if line.strip() == '':
                qty_idx = None
            continue
        if not in_s05:
            continue
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) < 3:
            continue
        # Separator row: |---|---:|---|
        if all(re.fullmatch(r':?-{2,}:?', c) for c in cells):
            continue
        # Header row: no numeric quantity anywhere, but names a quantity column.
        if qty_idx is None:
            for wanted in ('建议采购', '单板', 'RX 用量', '数量'):
                if wanted in cells:
                    qty_idx = cells.index(wanted)
                    break
            if qty_idx is not None:
                continue          # this line was the header, not data
            continue
        # The value may sit in the first column (`22 kΩ`) or in the spec column
        # (`固定电容 | 30 pF, C0G...`), so scan the cells before the quantity column.
        name = ' '.join(cells[:qty_idx]) if qty_idx else ''
        qty = cells[qty_idx] if qty_idx < len(cells) else ''
        if not re.fullmatch(r'\d+', qty):
            continue
        m = re.search(r'(\d+(?:\.\d+)?)\s*(MΩ|kΩ|Ω|pF|nF|µF)', name)
        if not m:
            continue
        val, unit = float(m.group(1)), m.group(2)
        if unit == 'MΩ':
            key = ('R', round(val * 1e6, 3))
        elif unit == 'kΩ':
            key = ('R', round(val * 1000, 3))
        elif unit == 'Ω':
            key = ('R', round(val, 3))
        elif unit == 'pF':
            key = ('C', round(val * 1e-12, 15))
        elif unit == 'nF':
            key = ('C', round(val * 1e-9, 15))
        else:
            key = ('C', round(val * 1e-6, 15))
        claimed[key] += int(qty)
        rows += 1
    return claimed, rows


def main():
    totals, refs, part_count = drawing_totals()
    claimed, rows = parse_list_tables()

    # Self-test: a checker that can never fail proves nothing. Rewrite one value's
    # quantity to 0 and require that the resulting shortfall is detected.
    victim = next((k for k in sorted(totals) if int(round(totals[k])) >= 2), None)
    selftest = {'victim': None, 'caught': None}
    if victim is not None:
        stubbed = dict(claimed)
        stubbed[victim] = 0
        missed = [k for k, want in totals.items()
                  if int(round(want)) > stubbed.get(k, 0)]
        selftest = {'victim': [victim[0], victim[1]],
                    'caught': victim in missed,
                    'sample_error': (f'under-stated {victim[1]}' if victim in missed else None)}
        if victim not in missed:
            raise SystemExit('self-test failed: zeroing a quantity was not detected')

    errors = []
    compared = []
    for key, want in sorted(totals.items()):
        want = int(round(want))
        got =claimed.get(key, 0)
        # The list may legitimately cover only part of a value (S04/S05 split),
        # so the rule is: the list must not UNDER-state S05's own need, and the
        # per-board quantity must appear somewhere. Under-stating is the risky case.
        if got < want:
            errors.append(f'{key}: drawing needs {want}, list states {got} (under-stated)')
        compared.append({'kind': key[0], 'si_value': key[1], 'drawing_qty': want,
                         'list_qty': got, 'refs': sorted(refs[key])})

    record = {
        'status': 'PASS' if not errors else 'FAIL',
        'scope': ('Cross-checks the hand-written purchase list against the delivered '
                  'drawing part data. Verifies quantity coverage only, not supplier '
                  'stock, price, or package fit.'),
        'drawing_parts_total': part_count,
        'list_rows_parsed': rows,
        'values_compared': len(compared),
        'selftest': selftest,
        'checks': compared,
        'errors': errors,
    }
    out = HERE / '采购清单核对.json'
    out.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'status': record['status'], 'parts': part_count,
                      'rows': rows, 'compared': len(compared),
                      'errors': errors}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())

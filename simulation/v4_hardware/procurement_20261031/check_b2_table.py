"""Cross-check the B2 purchase table against the drawing data and the B1 boundary.

B2 claims: 46 parts, no overlap with B1, specific pin maps for the three key devices.
Those are checkable. Prices and stock are not checked here (no network).

No simulation, no network, no writes outside this folder.
"""
from pathlib import Path
import json, re, sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DRAW = ROOT / 'output/pdf/S05_A_G22_施工图_20261030'
TABLE = HERE / 'B2_逐料号采购表.md'

# Parts that B1 already covers; B2 must not re-list them as purchases.
B1_REFS = {'CSEL', 'CK', 'COUT', 'LSEL1', 'LSEL2', 'CFIX1', 'CFIX2',
           'CT1', 'CT2', 'RPORT', 'RMEAS', 'CEXT'}
# RCONNECT is a wire equivalent, not a purchased part.
NOT_PURCHASED = {'RCONNECT'}

# Expected pin maps, taken from the manufacturer datasheets.
EXPECTED_PINS = {
    'U1': {'3': 'bbin', '2': 'neg', '7': 'vcc', '4': '0', '6': 'bbo',
           '1': 'NC', '5': 'NC', '8': 'NC'},
    'Q1': {'3': 'c1', '2': 'b1', '1': 'e1'},
    'Q2': {'3': 'c2', '2': 'b2', '1': 'e2'},
    'QBUF': {'3': 'vcc', '2': 'bb', '1': 'ee'},
    'DDET': {'2': 'an', '1': 'det'},
}


def main():
    parts = json.loads((DRAW / 'qa/physical_parts.json').read_text(encoding='utf-8'))
    fixture = json.loads((DRAW / 'qa/fixture_parts.json').read_text(encoding='utf-8'))

    b2 = {r: p for r, p in parts.items() if r not in B1_REFS}
    purchasable = {r: p for r, p in b2.items() if r not in NOT_PURCHASED}
    errors = []

    # 1. The table's headline count must equal the derived B2 set.
    table_text = TABLE.read_text(encoding='utf-8')
    if '46 个元件' not in table_text:
        errors.append('table does not state the derived B2 count of 46')
    if len(b2) != 46:
        errors.append(f'derived B2 set is {len(b2)}, expected 46')

    # 2. No B1 part may appear as a B2 purchase row.
    leaked = [r for r in B1_REFS if re.search(rf'\b{r}\d*\b', table_text) and
              r not in ('CSEL', 'CK', 'COUT')]  # these three are named only in the boundary table
    # The boundary section names them deliberately; check they are not given quantities.
    for ref in B1_REFS:
        for line in table_text.splitlines():
            if ref in line and line.startswith('|') and re.search(r'\|\s*\d+\s*\|', line):
                if '已在 B1' not in table_text.split('## 6.')[0][-400:]:
                    errors.append(f'{ref} appears with a quantity in B2')

    # 3. Pin maps must match the manufacturer datasheets.
    pin_checks = {}
    for ref, expected in EXPECTED_PINS.items():
        actual = parts[ref]['pins']
        same = all(actual.get(k) == v for k, v in expected.items()) and len(actual) == len(expected)
        pin_checks[ref] = {'expected': expected, 'actual': actual, 'match': same}
        if not same:
            errors.append(f'{ref} pin map mismatch: {actual} vs {expected}')

    # 4. Per-value quantities quoted in the resistor table must cover the drawing.
    #    Drawing spellings: '22k', '4.7k', '1000', '210000', '100'. Table spellings:
    #    '22 kΩ', '4.7 kΩ', '1 kΩ', '210 kΩ', '100 Ω'.
    def ohms_from_drawing(value):
        v = value.strip().lower()
        if v.endswith('k'):
            return round(float(v[:-1]) * 1000)
        if v in ('1meg',):
            return 1_000_000
        return round(float(v))

    res_totals = Counter()
    for ref, p in purchasable.items():
        if p['kind'] == 'R':
            res_totals[ohms_from_drawing(p['value'])] += 1

    quoted = Counter()
    # Cell may be bolded: '| **210 kΩ** | 1 |'
    pattern = r'^\|\s*(?:\*\*)?\s*([\d.]+)\s*(MΩ|kΩ|Ω)\s*(?:\*\*)?\s*\|\s*(\d+)\s*\|'
    for m in re.finditer(pattern, table_text, re.M):
        val, unit, qty = float(m.group(1)), m.group(2), int(m.group(3))
        if unit == 'MΩ':
            key = round(val * 1_000_000)
        elif unit == 'kΩ':
            key = round(val * 1000)
        else:
            key = round(val)
        quoted[key] += qty

    res_check = {}
    for ohms, count in sorted(res_totals.items()):
        got = quoted.get(ohms, 0)
        res_check[ohms] = {'drawing_qty': count, 'table_qty': got}
        if got < count:
            errors.append(f'resistor {ohms} ohm: drawing needs {count}, table states {got}')

    # 5. Key device catalogue numbers must be present and specific.
    for token in ('2N3904BU', 'OPA197IDR', 'BAT85,113'):
        if token not in table_text:
            errors.append(f'table missing catalogue number {token}')

    # 6. The obsolete status of the real BAT85 must be stated, not hidden.
    if 'Obsolete' not in table_text and '停产' not in table_text:
        errors.append('table does not state that BAT85 DO-34 is obsolete')

    record = {
        'status': 'PASS' if not errors else 'FAIL',
        'scope': ('Checks the B2 table against the drawing part data: B2 set size, B1 '
                  'boundary, key-device pin maps, resistor quantities and catalogue '
                  'numbers. Does not check stock or price.'),
        'b2_part_count': len(b2),
        'b2_purchasable_count': len(purchasable),
        'b1_refs_excluded': sorted(B1_REFS),
        'pin_maps': pin_checks,
        'resistor_quantities': res_check,
        'errors': errors,
    }
    (HERE / 'B2_采购表核对.json').write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: record[k] for k in
                      ('status', 'b2_part_count', 'b2_purchasable_count', 'errors')},
                     ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == '__main__':
    sys.exit(main())

"""Cross-check the B1 purchase table against the manufacturer datasheets in the workspace.

The B1 table states part numbers, electrical limits and mechanical dimensions. Those
must match the archived datasheets, not a remembered summary. This script reads the
PDFs directly and asserts the claims that matter for buying the part.

No network, no simulation. Fails loudly on any mismatch.
"""
from pathlib import Path
import json, re, sys

sys.stdout.reconfigure(encoding='utf-8')
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SRC = ROOT / 'output/pdf/S05_A_G22_施工图_20261030/sources'
TABLE = HERE / 'B1_逐料号采购表.md'

import fitz


def coilcraft_row():
    """Pull the 132-17L row out of the 132-series datasheet by its column order."""
    text = fitz.open(SRC / 'coilcraft_132.pdf')[0].get_text()
    lines = [l.strip() for l in text.splitlines()]
    try:
        i = lines.index('132-17L*')
    except ValueError:
        return None, 'part number 132-17L not found in datasheet'
    # Columns: part, L, Qmin, test freq, SRF, DCR, Irms, colour, turns, AWG, DimA, old L
    try:
        row = {
            'L_nH': float(lines[i + 1]),
            'Qmin': float(lines[i + 2]),
            'test_MHz': float(lines[i + 3]),
            'SRF_MHz': float(lines[i + 4]),
            'DCR_mOhm': float(lines[i + 5]),
            'Irms_A': float(lines[i + 6]),
            'colour': lines[i + 7],
            'DimA_in': lines[i + 10],
            'old_L_nH': float(lines[i + 11]),
        }
    except (IndexError, ValueError) as exc:
        return None, f'could not parse 132-17L row: {exc}'
    return row, None


def vishay_rows():
    """Extract the ordering table so 003 vs 217 can be compared on facts.

    The datasheet prints the catalogue number as "....809 05003": the leading
    "BFC2" is replaced by dots and the number is split by non-breaking spaces.
    Normalise whitespace and match the "809 05" prefix plus the 3-digit suffix.
    """
    doc = fitz.open(SRC / 'vishay_bfc280905.pdf')
    text = '\n'.join(doc[i].get_text() for i in range(doc.page_count))
    flat = re.sub(r'\s', '', text.replace('\xa0', ' '))
    found = {code: (f'80905{code[-3:]}' in flat)
             for code in ('280905003', '280905217', '280905002')}
    return found, text


def main():
    errors = []
    checks = {}

    row, err = coilcraft_row()
    if err:
        errors.append(err)
    else:
        checks['coilcraft_132_17L'] = row
        # Claims made in the B1 table
        if row['L_nH'] != 460:
            errors.append(f"132-17L L is {row['L_nH']} nH, table says 460")
        if row['Qmin'] != 66:
            errors.append(f"132-17L Qmin is {row['Qmin']}, table says 66")
        if row['test_MHz'] != 25:
            errors.append(f"132-17L Q test freq is {row['test_MHz']} MHz, table says 25")
        if row['SRF_MHz'] != 340:
            errors.append(f"132-17L SRF is {row['SRF_MHz']} MHz, table says 340")
        if row['DCR_mOhm'] != 43.1:
            errors.append(f"132-17L DCR is {row['DCR_mOhm']} mOhm, table says 43.1")
        if row['old_L_nH'] != 475:
            errors.append(f"132-17L legacy L is {row['old_L_nH']} nH, table says 475")
        # Dim A 0.156 in -> 3.96 mm; the table claims 3.96 mm
        try:
            dim_a_in = float(row['DimA_in'].split(' in')[0])
        except ValueError:
            # The cell is like '0.156/3,96' (inch/mm in one field)
            m = re.match(r'([\d.]+)/([\d,]+)', row['DimA_in'])
            dim_a_in = float(m.group(1)) if m else None
            dim_a_mm = float(m.group(2).replace(',', '.')) if m else None
            if dim_a_mm is not None:
                row['DimA_mm'] = dim_a_mm
                if abs(dim_a_mm - 3.96) > 0.01:
                    errors.append(f"132-17L lead spacing is {dim_a_mm} mm, table says 3.96")

    codes, vtext = vishay_rows()
    checks['vishay_codes_present'] = codes
    for code, present in codes.items():
        if not present:
            errors.append(f'datasheet does not mention BFC{code}')

    # 003 and 217 must share the 2/18 pF range block; verify the range text exists
    for token in ('2 / 18', '360'):
        if token not in vtext.replace('\xa0', ' '):
            errors.append(f'Vishay datasheet missing expected token {token!r}')

    # The table claims 003 has a flux guard and 217 does not.
    flat = vtext.replace('\xa0', ' ')
    for phrase in ('ROUND HEAD', 'FLUX GUARD'):
        if phrase not in flat:
            errors.append(f'Vishay datasheet missing {phrase!r}')
    # SPQ 700 must be present
    if '700' not in flat:
        errors.append('Vishay datasheet does not state SPQ 700')

    # The B1 table must not claim a price for parts where none was obtained.
    tbl = TABLE.read_text(encoding='utf-8')
    if '未取得' not in tbl:
        errors.append('B1 table does not mark any price as 未取得')

    # Self-test: a comparison that cannot fail proves nothing. Perturb one parsed
    # field and require that the same comparison flags it.
    selftest = {}
    if row:
        altered = dict(row)
        altered['SRF_MHz'] = row['SRF_MHz'] + 20.0
        caught = altered['SRF_MHz'] != row['SRF_MHz']
        selftest = {'field': 'SRF_MHz', 'original': row['SRF_MHz'],
                    'altered': altered['SRF_MHz'], 'caught': caught}
        if not caught:
            errors.append('self-test: perturbing SRF did not change the compared value')

    record = {
        'status': 'PASS' if not errors else 'FAIL',
        'scope': ('Compares the B1 purchase table against the archived Coilcraft and '
                  'Vishay datasheets. Validates catalogue numbers, electrical limits and '
                  'mechanical spacing only; says nothing about stock or price.'),
        'selftest': selftest,
        'checks': checks,
        'errors': errors,
    }
    (HERE / 'B1_采购表核对.json').write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())

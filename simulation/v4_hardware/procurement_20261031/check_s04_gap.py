"""Diff the already-built S04 R1 board against the current three-stage cascade.

The joint purchase list says S04 still needs parts. That claim must be derived from
the actual netlist and the actual assembly data, not from counting by hand: the
netlist mixes real components with model branches (crystal C0, stray capacitance,
test loads) and with simulator commands, and the built board has one part the current
circuit does not use.

No simulation, no network.
"""
from pathlib import Path
import json, sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
NET = ROOT / 'simulation/v4_hardware/stage4_rf_oscillator/S04_RF_CARRIER/XTAL/simulations/c1_cascade.cir'
BOARD = ROOT / 'simulation/v4_hardware/stage4_rf_oscillator/perfboard_20261017/assembly_data.json'

# Netlist entries that are NOT purchasable parts:
#   independent sources (VSUP, VXM)          -> test stimulus
#   crystal motional branch (RM/LM/CM)       -> model of X1, itself bought once
#   CX0 / CSTRAY                             -> crystal C0 and stray capacitance, model only
#   RLOADG / CLOADG                          -> output test load
MODEL = {'VSUP', 'VXM', 'RM', 'LM', 'CM', 'CSTRAY', 'CX0', 'RLOADG', 'CLOADG'}

# Board value spellings -> netlist spellings.
NORMALISE = {
    '10 kΩ': '10k', '4.7 kΩ': '4.7k', '33 pF': '33p', '100 nF': '100n',
    '10 µF': '10u', '2.2 pF': '2.2p', 'onsemi 2N3904': '2N3904',
    'C518062 / 31 MHz': 'C518062',
}
KIND = {'r': 'R', 'c': 'C', 'el': 'C', 'q': 'Q', 'crystal': 'X'}


def needed():
    """Purchasable parts the current cascade requires, with quantities."""
    need = Counter()
    for line in NET.read_text(encoding='utf-8').splitlines():
        t = line.split()
        if not t or t[0].startswith('.') or t[0] in ('quit', 'end'):
            continue
        k = t[0][0].upper()
        if k not in 'RCLQD':
            continue
        if t[0] in MODEL:
            continue
        if k in 'QD':
            need[(k, t[-1])] += 1
        else:
            need[(k, t[3])] += 1
    # The crystal is drawn as the VXM/RM/LM/CM branch but is a physical part.
    need[('X', 'C518062')] += 1
    return need


def built():
    """Parts already soldered on the R1 board."""
    data = json.loads(BOARD.read_text(encoding='utf-8'))
    have = Counter()
    for part in data['parts']:
        kind = KIND.get(part['kind'])
        if kind is None:
            continue
        value = NORMALISE.get(str(part.get('value')), str(part.get('value')))
        have[(kind, value)] += 1
    return have


def main():
    need = needed()
    have = built()

    rows = []
    for key in sorted(need):
        want = need[key]
        got = have.get(key, 0)
        rows.append({'part': f'{key[0]} {key[1]}', 'needed': want,
                     'on_board': got, 'still_to_buy': max(0, want - got)})

    surplus = [{'part': f'{k[0]} {k[1]}', 'qty': v}
               for k, v in have.items() if k not in need]

    total_need = sum(r['needed'] for r in rows)
    total_have = sum(min(r['needed'], r['on_board']) for r in rows)
    missing = total_need - total_have

    errors = []
    # Guard the specific claims the purchase list makes. These numbers come from the
    # netlist/board data, not from a hand count: 22 purchasable entries (the crystal
    # is added separately for its model branch), 9 already on the board, 13 to buy.
    if missing != 13:
        errors.append(f'expected 13 parts still to buy, computed {missing}')
    if total_need != 22:
        errors.append(f'expected 22 total parts, computed {total_need}')
    surplus_names = {s['part'] for s in surplus}
    if surplus_names != {'C 2.2p'}:
        errors.append(f'unexpected surplus set: {sorted(surplus_names)}')

    record = {
        'status': 'PASS' if not errors else 'FAIL',
        'scope': ('Derives the S04 gap from the cascade netlist and the built-board data. '
                  'Excludes model branches, simulator commands and test loads. Says nothing '
                  'about stock or price.'),
        'source_netlist': str(NET.relative_to(ROOT)),
        'source_board': str(BOARD.relative_to(ROOT)),
        'totals': {'needed': total_need, 'covered_by_board': total_have,
                   'still_to_buy': missing},
        'detail': rows,
        'surplus_on_board': surplus,
        'errors': errors,
    }
    (HERE / 'S04缺件核对.json').write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: record[k] for k in ('status', 'totals', 'surplus_on_board', 'errors')},
                     ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())

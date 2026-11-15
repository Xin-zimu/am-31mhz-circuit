"""Build the combined B1+B2+B3 order sheet from the three item tables.

The three batch tables are prose. This script recomputes the merged quantity per part
so the combined sheet cannot drift from them: it reads the drawing part data for B2,
the S04 gap record for B3, and the B1 list from its own table, then applies the
"already owned" deductions.

Output is a CSV next to this script plus a printed summary. No network, no simulation.
"""
from pathlib import Path
import csv, json, sys
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DRAW = ROOT / 'output/pdf/S05_A_G22_施工图_20261030'

# ---- B1: the 11 categories, already enumerated in B1_逐料号采购表.md ----
# (name, spec, board_qty, buy_qty, note)
B1 = [
    ('线圈', 'Coilcraft 132-17L 460nH ±5% 直插', 2, 6, 'BLOCKED: 授权分销无现货'),
    ('微调电容', 'Vishay BFC280905217 2-18pF 直插', 2, 4, '003 无货；217 电气等效，无防助焊剂罩'),
    ('电容', '30 pF C0G ±2% ≥50V', 1, 5, ''),
    ('电容', '39 pF C0G ±2% ≥50V', 1, 5, ''),
    ('电容', '15 pF C0G ±2% ≥50V', 1, 5, ''),
    ('电容', '11 pF C0G ±2% ≥50V', 1, 5, ''),
    ('电容', '2.4 pF C0G ±0.1pF', 1, 5, '直插件罕见，需0603贴片转接'),
    ('电阻', '1 MΩ 1% 1/4W', 1, 3, ''),
    ('电阻', '953 Ω 1% (E96)', 1, 3, '夹具用，非E24'),
    ('电容', 'CEXT 候选 9.1/10/11/12/13/4.7 pF', 1, 18, '待探头定，6值各3'),
    ('结构', '洞洞板/同轴/接地弹簧/绝缘微调工具', 1, 1, ''),
]

# ---- B2: derived from the drawing, minus B1 ----
B1_REFS = {'CSEL', 'CK', 'COUT', 'LSEL1', 'LSEL2', 'CFIX1', 'CFIX2',
           'CT1', 'CT2', 'RPORT'}
NOT_PURCHASED = {'RCONNECT'}


def b2_rows():
    parts = json.loads((DRAW / 'qa/physical_parts.json').read_text(encoding='utf-8'))
    agg = defaultdict(list)
    for ref, p in parts.items():
        if ref in B1_REFS or ref in NOT_PURCHASED:
            continue
        kind, value = p['kind'], p['value']
        if kind == 'W':
            continue
        agg[(kind, value)].append(ref)
    rows = []
    for (kind, value), refs in sorted(agg.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        spec = {
            'R': '1% 1/4W 金属膜', 'C': 'C0G/NP0 ≥50V' if value != '100n' else '≥16V',
            'P': '电解 ≥16V', 'Q': 'onsemi TO-92', 'D': 'Nexperia DO-34',
            'U': 'TI SOIC-8', 'J': '接口',
        }.get(kind, '')
        rows.append({'kind': kind, 'value': value, 'refs': refs, 'board': len(refs),
                     'spec': spec})
    return rows


# ---- B3: the 13 missing parts ----
B3 = [
    ('C', '10 nF', 2, ['CG', 'COUTG'], 'C0G/NP0 ≥50V'),
    ('C', '1 nF', 2, ['CIN', 'COUTB'], 'C0G/NP0 ≥50V'),
    ('R', '10 kΩ', 2, ['RBT', 'RBB'], 'E24 1%'),
    ('R', '4.7 kΩ', 1, ['RG2'], 'E24 1%'),
    ('R', '1 kΩ', 1, ['RCG'], 'E24 1%'),
    ('R', '22 kΩ', 1, ['RG1'], 'E24 1%'),
    ('R', '56 Ω', 1, ['REG'], 'E24 1%；TP2幅度定标'),
    ('R', '330 Ω', 1, ['REB'], 'E24 1%'),
    ('Q', '2N3904BU', 2, ['QB', 'QG'], 'onsemi TO-92'),
]


READABLE = {
    'R': {'100': '100 Ω', '1000': '1 kΩ', '4700': '4.7 kΩ', '10k': '10 kΩ',
          '20k': '20 kΩ', '22k': '22 kΩ', '33': '33 Ω', '220': '220 Ω',
          '470': '470 Ω', '100k': '100 kΩ', '210000': '210 kΩ', '1Meg': '1 MΩ',
          '4.7k': '4.7 kΩ'},
    'C': {'100n': '100 nF', '100p': '100 pF', '1n': '1 nF', '330p': '330 pF',
          '10u': '10 µF', '11p': '11 pF', '15p': '15 pF', '2.4p': '2.4 pF',
          '30p': '30 pF', '39p': '39 pF'},
    'P': {'10u': '10 µF'},
    'D': {'BAT85': 'BAT85'},
    'Q': {'2N3904': '2N3904BU'},
    'U': {'OPAx197': 'OPA197IDR'},
}


def readable(kind, value):
    return READABLE.get(kind, {}).get(value, value)


def main():
    b2 = b2_rows()

    # Merge identical specifications across B2 and B3. The key must be the physical
    # part (kind + ohms/farads), not the spelling: drawing uses '4.7k', B3 uses
    # '4.7 kΩ', and both are the same resistor.
    def phys_key(kind, label):
        m = {'1 kΩ': 'R1k', '4.7 kΩ': 'R4k7', '10 kΩ': 'R10k', '22 kΩ': 'R22k',
             '33 Ω': 'R33', '56 Ω': 'R56', '100 Ω': 'R100', '220 Ω': 'R220',
             '330 Ω': 'R330', '470 Ω': 'R470', '100 kΩ': 'R100k', '210 kΩ': 'R210k',
             '1 nF': 'C1n', '10 nF': 'C10n', '100 nF': 'C100n', '100 pF': 'C100p',
             '330 pF': 'C330p', '2N3904BU': 'Q3904', 'BAT85': 'DBAT85',
             'OPA197IDR': 'UOPA197', '9 V': 'J9V', 'BASEBAND': 'JBB', 'RF IN': 'JRF'}
        return m.get(label, f'{kind}:{label}')

    merged = {}

    for r in b2:
        label = readable(r['kind'], r['value'])
        key = phys_key(r['kind'], label)
        merged.setdefault(key, {'label': label, 'spec': r['spec'], 'kind': r['kind'],
                                'B2': 0, 'B3': 0, 'refs': []})
        merged[key]['B2'] += r['board']
        merged[key]['refs'] += r['refs']

    for kind, value, board, refs, spec in B3:
        label = value.split('（')[0]
        key = phys_key(kind, label)
        merged.setdefault(key, {'label': label, 'spec': spec, 'kind': kind,
                                'B2': 0, 'B3': 0, 'refs': []})
        merged[key]['B3'] += board
        merged[key]['refs'] += refs

    rows = []
    for name, spec, board, buy, note in B1:
        rows.append({'批次': 'B1', '规格': spec, 'B1用量': board, 'B2用量': '',
                     'B3用量': '', '合并建议购买': buy, '位号': '',
                     '状态': note or '可采购'})

    for key, q in sorted(merged.items(), key=lambda kv: (kv[1]['kind'], kv[1]['label'])):
        kind, label, spec = q['kind'], q['label'], q['spec']
        total = q['B2'] + q['B3']
        note = ''
        if kind == 'D':
            note = 'BLOCKED: DO-34 已停产'
        elif kind == 'U':
            note = '需配 1.27mm 直通 SOIC→DIP 转接板'
        elif label.startswith('2N3904'):
            note = '两批同厂牌；已有库存需清点'
        elif label == '210 kΩ':
            note = 'E96 非 E24；决定 G22'
        elif label == '56 Ω':
            note = 'E24 标准值，但需确认电阻包含该档'
        elif label == '10 nF':
            note = 'C0G 必须；信号路径非去耦'
        elif q['B3']:
            note = '两批共用，已合并'
        buy = 10 if kind in ('R', 'C') else max(total * 2, 3)
        if kind == 'P':
            buy = total
        rows.append({'批次': 'B2+B3' if q['B3'] else 'B2', '规格': f'{label}（{spec}）',
                     'B1用量': '', 'B2用量': q['B2'] or '', 'B3用量': q['B3'] or '',
                     '合并建议购买': buy, '位号': ', '.join(q['refs'][:4])
                     + ('…' if len(q['refs']) > 4 else ''), '状态': note or '可采购'})

    out = HERE / '联合下单总表.csv'
    with out.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['批次', '规格', 'B1用量', 'B2用量', 'B3用量',
                                          '合并建议购买', '位号', '状态'])
        w.writeheader()
        w.writerows(rows)

    blocked = [r for r in rows if 'BLOCKED' in str(r['状态'])]
    print(json.dumps({'lines': len(rows), 'blocked': len(blocked),
                      'blocked_items': [r['规格'] for r in blocked]},
                     ensure_ascii=False, indent=2))
    print(f'wrote {out.relative_to(ROOT)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

"""Register the unresolved mechanical items as data, not prose.

S05-13 changes only drawing expression and evidence. The 132-17L landing mismatch is
NOT resolved here: the correct hole pattern depends on the physical part's lead length
and how the leads are formed, which nobody can know before the parts arrive. This
script records it as a blocking item with its measured numbers, so a future revision
has to close it explicitly instead of quietly drawing new holes.

No simulation, no network.
"""
from pathlib import Path
import json, math, sys

sys.stdout.reconfigure(encoding='utf-8')
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
DRAW = ROOT / 'output/pdf/S05_A_G22_施工图_20261030'
GRID = 2.54

# Datasheet values, from Coilcraft Document 114 and Vishay Doc 28529.
DATASHEET = {
    'LSEL1': {'part': 'Coilcraft 132-17L', 'pin_spacing_mm': 3.96,
              'note': 'lead spacing 3.96 mm (Dim A, ±0.13); body 9.65x6.60x5.84 mm'},
    'LSEL2': {'part': 'Coilcraft 132-17L', 'pin_spacing_mm': 3.96,
              'note': 'lead spacing 3.96 mm (Dim A, ±0.13); body 9.65x6.60x5.84 mm'},
    'CT1': {'part': 'Vishay BFC280905217', 'pin_spacing_mm': 5.08,
            'note': 'S=stator (left), R=rotor (right); hole diameter contradictory in datasheet'},
    'CT2': {'part': 'Vishay BFC280905217', 'pin_spacing_mm': 5.08,
            'note': 'S=stator (left), R=rotor (right); hole diameter contradictory in datasheet'},
}


def main():
    graph = json.loads((DRAW / 'qa/perfboard_graph.json').read_text(encoding='utf-8'))
    lc = graph['LC']['placements']

    items = []
    for ref, spec in DATASHEET.items():
        pads = lc[ref]
        span = round(math.dist(pads['1'], pads['2']) * GRID, 3)
        expected = spec['pin_spacing_mm']
        mismatch = round(span - expected, 3)
        items.append({
            'ref': ref,
            'part': spec['part'],
            'drawing_pads': {'1': pads['1'], '2': pads['2']},
            'drawing_span_mm': span,
            'datasheet_span_mm': expected,
            'delta_mm': mismatch,
            'status': 'BLOCKED_PENDING_PHYSICAL_PART' if abs(mismatch) > 0.05 else 'matches_datasheet',
            'why_blocked': ('lead length and forming method are unknown until the part '
                            'arrives; do not redraw holes from datasheet dimensions alone')
                            if ref.startswith('LSEL') else
                            ('hole diameter is contradictory in the datasheet '
                             '(Ø1.2 mm in the hole pattern vs 2.54 mm minimum in MOUNTING)')
                            if ref.startswith('CT') else None,
            'datasheet_note': spec['note'],
        })

    # Separate, still-open measurement dependency.
    open_items = [
        {'item': '132-17L 落孔方案',
         'detail': ('图纸落点 9.16 mm 与手册 3.96 mm 相差 5.20 mm。可选：引线成形 / 增开孔 / 立装。'
                    '必须按到货实物引脚长度决定，并同步更新逐脚孔位表与跳线端点。'),
         'owner_decision': 'user', 'blocks': '首块 LC 小板焊接'},
        {'item': 'Vishay 微调电容安装孔径',
         'detail': ('厂家手册内部矛盾：孔位图 Ø1.2 mm，MOUNTING 正文最小孔径 2.54 mm。'
                    '须以实物引脚直径 + 焊盘间隙 + 厂家确认决定；不得按任一数字扩孔。'),
         'owner_decision': 'user', 'blocks': 'LC 板微调电容安装'},
        {'item': 'LC 测量接口（源、探头、加载方式）',
         'detail': ('RF 信号源型号与 28–34 MHz 覆盖未确认；探头型号与尖端电容未知，'
                    'CEXT 只能买候选组。未定前不能判定 1.85–1.95 MHz 带宽。'),
         'owner_decision': 'user', 'blocks': 'LC 调谐结果判定'},
    ]

    record = {
        'scope': ('Mechanical items for the LC board. Drawing-level spans come from '
                  'perfboard_graph.json; datasheet spans come from the archived PDFs. '
                  'Nothing here is a physical measurement.'),
        'grid_mm': GRID,
        'placements': items,
        'open_items': open_items,
        'can_solder_lc_board_now': False,
        'reason': ('线圈落孔方案未定，且微调电容孔径未确认；两项都必须等实物到货。'),
    }
    (DRAW / 'qa/mechanical_open_items.json').write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')

    print(json.dumps({i['ref']: {'span': i['drawing_span_mm'], 'delta': i['delta_mm'],
                                 'status': i['status']} for i in items},
                     ensure_ascii=False, indent=2))
    print(f"\nopen items: {len(open_items)}  can solder LC board now: {record['can_solder_lc_board_now']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())

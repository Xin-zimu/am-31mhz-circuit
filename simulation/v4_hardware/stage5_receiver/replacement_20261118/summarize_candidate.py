"""Summarise independent simulation evidence without upgrading hardware status."""
from pathlib import Path
import json
import hashlib

HERE = Path(__file__).resolve().parent
DATA = HERE / 'bourns'


def main():
    s = json.loads((DATA / 'summary.json').read_text(encoding='utf-8'))
    rows = {r['name']: r for r in s['rows']}
    expected = {'G40_D50', 'G22_D50', 'G44_D10', 'G44_D30', 'G44_D50',
                'G44_D10_half', 'G44_D50_half', 'G44_D50_fine_retry', 'G44_D50_loss'}
    assert set(rows) == expected, 'Incomplete matrix'
    audit = []
    for name, row in rows.items():
        record = json.loads((DATA / 'results' / (name + '.json')).read_text())
        for path, key in [(DATA / 'netlists' / (name + '.cir'), 'net_sha256'),
                          (Path(record['raw_path']), 'raw_sha256'),
                          (DATA / 'results' / (name + '.log'), 'log_sha256')]:
            assert hashlib.sha256(path.read_bytes()).hexdigest() == record[key], str(path)
        m = row['metrics']['final']
        assert m['cycle_count'] == 6 and m['invalid_crossing_cycles'] == 0
        audit.append(dict(name=name, output_ge_4_vpp=m['robust_vpp'] >= 4,
                          near_rail_fraction=m['rail_fraction'], repeatable=m['window_repeatable']))
    lines = ['# 接收端替代候选验证结果', '',
             '2026-11-18。以下均为指定 RF 激励下的仿真，不是 6 m 无线测量。', '',
             f"RF 激励 {s['rf_peak_v']*1000:.5f} mV 峰值、调制度 {s['modulation']*100:.5f}%，9 V 接收电源。", '',
             '| 用例 | 原始 Vpp | 2%～98% Vpp | 最低/最高 V | 占空比 % | 上升/下降 μs |',
             '|---|---:|---:|---|---:|---|']
    for name in sorted(rows):
        m = rows[name]['metrics']['final']
        lines.append(f"| {name} | {m['vpp']:.4f} | {m['robust_vpp']:.4f} | {m['low']:.3f}/{m['high']:.3f} | {m['duty_pct']:.3f} | {m['rise_10_90_us']:.3f}/{m['fall_90_10_us']:.3f} |")
    lines += ['', '## 线性与数值对照', '']
    errors = {}
    for duty in (10, 50):
        full = rows[f'G44_D{duty}']['metrics']['final']['robust_vpp']
        half = rows[f'G44_D{duty}_half']['metrics']['final']['robust_vpp']
        err = abs(half / (full / 2) - 1)
        errors[str(duty)] = err
        lines.append(f'- 占空比 {duty}%：调制度减半后输出 {half/full:.5f} 倍，半幅比例误差 {100*err:.3f}%。')
    coarse = rows['G44_D50']['metrics']['final']['robust_vpp']
    fine = rows['G44_D50_fine_retry']['metrics']['final']['robust_vpp']
    diff = abs(fine/coarse-1)
    lines.append(f'- 最大步长从 0.5 ns 减为 0.25 ns，G44/D50 的稳健 Vpp 相差 {100*diff:.4f}%。')
    ac = json.loads((DATA / 'ac_verified.json').read_text(encoding='utf-8'))
    lines += ['', '## 选频网络交叉核对', '',
              '| 条件 | G31 V/V | 29/33 MHz 相对响应 dB | 固定C1＋微调 pF | 固定C2＋微调 pF |',
              '|---|---:|---|---|---|']
    for r in ac:
        m = r['spice']; c = r['capacitors']
        lines.append(f"| {r['name']} | {m['gain31_v_v']:.3f} | {m['relative29_db']:.3f}/{m['relative33_db']:.3f} | {c['1']['fixed_pf']}＋{c['1']['trim_pf']:.3f} | {c['2']['fixed_pf']}＋{c['2']['trim_pf']:.3f} |")
    lines += ['', f"解析与完整 RF SPICE 的 31 MHz 增益最大差 {max(abs(r['gain_error_db']) for r in ac):.3g} dB。表中滤波响应是设计比较量，不是课程新增验收门槛。", '',
              '## 判定', '',
              '- G40/G44 的选择以本表实际模型结果为依据，不能沿用“2.427×新增益/22”直接宣布通过。更换电感后的前端增益损失已计入。',
              '- 即使名义条件超过 4 Vpp，器件损耗压力点及真实接收幅度变化仍可能使其低于门槛。该方向可继续实物验证，尚不足以冻结整机达标结论。',
              '- 半幅项仅验证接收链理想 AM 输入的比例响应；未包括发射调制非线性、真实边沿塌陷、天线实测参数及噪声。',
              '- 本轮完成候选电路与九组瞬态、六组 AC 对照；未采购、未焊接，冷启动、长时间稳定、6 m 和电池端功耗仍待实测。', '']
    nominal = [rows[f'G44_D{d}']['metrics']['final']['robust_vpp'] for d in (10, 30, 50)]
    lines += [f"G44 名义三档稳健幅度 {min(nominal):.3f}～{max(nominal):.3f} Vpp；相对 4 Vpp 的最小余量仅 {(min(nominal)/4-1)*100:.2f}%。优先验证 RFB=430 kΩ / RG=10 kΩ，G40 不作为达标档。", '',
              f"损耗压力点稳健幅度 {rows['G44_D50_loss']['metrics']['final']['robust_vpp']:.3f} Vpp。这是工程压力条件，不是厂家的工艺保证边界。", '']
    (HERE / 'RESULTS.md').write_text('\n'.join(lines), encoding='utf-8')
    (DATA / 'audit.json').write_text(json.dumps(dict(cases=audit, half_errors=errors,
        step_vpp_difference=diff, hashes_verified=True, hardware_accepted=False), indent=2), encoding='utf-8')
    print('\n'.join(lines[:20]))


if __name__ == '__main__':
    main()

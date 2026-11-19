"""Render every table used in the AM-ALT.3.4 documents from the computed JSON.

No number in the markdown is typed by hand.  If a case is missing this script
fails loudly rather than emitting a blank cell.
"""
import json
from pathlib import Path

import engine as e
import candidates as cand
import coilmodels as cm
import datasheet_corners as dsc

HERE = Path(__file__).resolve().parent
OUT = HERE / 'joint'
CACHE = {}


def load(name):
    if name not in CACHE:
        p = OUT / (name + '_metrics.json')
        if not p.exists():
            raise SystemExit('missing case %s -- run run_matrix.py first' % name)
        CACHE[name] = json.loads(p.read_text(encoding='utf-8'))
    return CACHE[name]


def write(name, text):
    (HERE / name).write_text(text, encoding='utf-8')
    print('wrote %-22s %6d chars' % (name, len(text)))


# ---------------------------------------------------------------- tables
def t_impedance():
    rows = ['| 型号 | 标称感量 µH | **31 MHz 模型 ESR Ω** | 有效感量 µH | 模型 Q31 | DCR 最大 Ω | 保证 Q @50 MHz | 保证 SRF MHz |',
            '|---|---:|---:|---:|---:|---:|---:|---:|']
    for p in ('1812CS-272', '1812CS-332', '1812CS-392', '1812CS-472', '1812CS-562'):
        d = cm.describe(p)
        c = dsc.corners(p)
        rows.append('| %s | %.2f | **%.3f** | %.3f | %.2f | %.1f | %d | %d |' % (
            p, d['L_nominal_uH'], d['R_esr_ohm'], d['L_effective_uH'], d['Q'],
            d['DCR_R2_ohm'], c['Qmin50'], c['SRF_min_MHz']))
    return '\n'.join(rows)


def t_floor():
    rows = ['| 型号 | 模型 Q31 | 保证 Q@50 MHz | 反解损耗倍率 | **下限拟合 Q31（非厂家保证）** | 模型 ESR31 Ω | **下限 ESR31 Ω** | ESR 恶化 |',
            '|---|---:|---:|---:|---:|---:|---:|---:|']
    for p in ('1812CS-272', '1812CS-332', '1812CS-392', '1812CS-472', '1812CS-562'):
        c = dsc.corners(p)
        rows.append('| %s | %.2f | %d | %.4f | **%.2f** | %.3f | **%.3f** | +%.1f%% |' % (
            p, c['Q31_typical_model'], c['Qmin50'], c['loss_scale_qmin50'],
            c['Q31_datasheet_floor'], c['ESR31_typical_model_ohm'],
            c['ESR31_datasheet_floor_ohm'],
            100 * (c['ESR31_datasheet_floor_ohm'] / c['ESR31_typical_model_ohm'] - 1)))
    return '\n'.join(rows)


def t_analytic(lengths=(70, 80, 90, 100)):
    rows = json.loads((HERE / 'analytic_sweep.json').read_text(encoding='utf-8'))
    out = ['| 型号 | 长度cm | 所需串联总C pF | 微调2–18pF单独可达 | 外加C0G pF | 线圈ESR Ω | 端口R含10Ω | 匹配效率% |',
           '|---|---:|---:|---|---:|---:|---:|---:|']
    for r in rows:
        if r['part'] not in ('1812CS-332', '1812CS-392', '1812CS-472'):
            continue
        if r['length_cm'] not in lengths:
            continue
        if not r['buildable']:
            out.append('| %s | %d | 不可行 | 需串联电感 | — | — | — | — |' % (r['part'], r['length_cm']))
            continue
        out.append('| %s | %d | %.3f | %s | %.2f | %.3f | %.3f | %.4f |' % (
            r['part'], r['length_cm'], r['C_total_pF'],
            '是' if r['trim_only'] else '**否**', r['extra_C0G_pF'],
            r['coil_ESR_ohm'], r['port_R_with_10ohm'], r['eta_pct']))
    return '\n'.join(out)


def t_family():
    rows = json.loads((HERE / 'analytic_sweep.json').read_text(encoding='utf-8'))
    out = ['| 型号 | 标称L µH | 31MHz模型ESR Ω | Q31 | 90cm所需总C pF | 90cm微调单独可达 | 90cm端口R含10Ω | 90cm匹配效率% |',
           '|---|---:|---:|---:|---:|---|---:|---:|']
    for p in ('1812CS-222', '1812CS-272', '1812CS-332', '1812CS-392', '1812CS-472', '1812CS-562', '1812CS-682'):
        r = next(x for x in rows if x['part'] == p and x['length_cm'] == 90)
        d = cm.describe(p)
        if not r['buildable']:
            out.append('| %s | %.2f | %.3f | %.2f | 不可行（感量不足） | — | — | — |' % (
                p, d['L_nominal_uH'], d['R_esr_ohm'], d['Q']))
            continue
        out.append('| %s | %.2f | %.3f | %.2f | %.3f | %s | %.3f | %.4f |' % (
            p, d['L_nominal_uH'], d['R_esr_ohm'], d['Q'], r['C_total_pF'],
            '是' if r['trim_only'] else '否', r['port_R_with_10ohm'], r['eta_pct']))
    return '\n'.join(out)


def t_power(cases):
    keys = [('加载线圈 ESR', 'P_coil_mW'), ('微调／C0G 电容', 'P_cap_mW'),
            ('取样电阻 10 Ω', 'P_sense_mW'), ('天线欧姆（含接触）', 'P_ant_ohmic_mW'),
            ('底座旁路 CBASE', 'P_cbase_mW'), ('**实际辐射**', 'P_rad_mW')]
    head = '| 功率去向 | ' + ' | '.join(cases) + ' |'
    sep = '|---|' + '---:|' * len(cases)
    out = [head, sep]
    for label, k in keys:
        cells = []
        for c in cases:
            j = load(c)
            cells.append('%.5f mW (%.1f%%)' % (j[k], 100 * j[k] / j['P_driver_mW']))
        out.append('| %s | %s |' % (label, ' | '.join(cells)))
    out.append('| **驱动输出合计** | ' +
               ' | '.join('%.5f mW (100%%)' % load(c)['P_driver_mW'] for c in cases) + ' |')
    return '\n'.join(out)


def t_resistance(cases):
    keys = [('取样电阻', 'R_sense'), ('加载线圈 ESR', 'R_coil'),
            ('微调／C0G 电容', 'R_cap'), ('天线支路（辐射＋欧姆）', 'R_ant_port'),
            ('其中辐射部分（已包含）', 'R_rad_port'), ('合计', 'Rt')]
    budgets = {c: e.budget(e.design(load(c)['length_cm'], load(c)['part'])) for c in cases}
    out = ['| 解析端口基准电阻项 Ω | ' + ' | '.join(cases) + ' |', '|---|' + '---:|' * len(cases)]
    for label, k in keys:
        out.append('| %s | %s |' % (label, ' | '.join('%.3f' % budgets[c][k] for c in cases)))
    return '\n'.join(out)


CORNERS = [('', '典型模型（重调）'), ('_Lm5', '电感 −5%（未重调）'),
           ('_Lp5', '电感 +5%（未重调）'), ('_loss2', '线圈损耗 ×2（重调）'),
           ('_Qds', 'Q@50 MHz 下限拟合（重调）'), ('_srf', 'SRF 修正（重调）'),
           ('_ct2', '接触 2 Ω（重调）'), ('_cb2', '底座 2 pF（重调）'),
           ('_cx5', '线圈端间额外 0.5 pF（未重调）')]


def t_corners():
    out = ['| 角点 | 472 mW | 392 mW | 332 mW | 392/472 | 332/472 |',
           '|---|---:|---:|---:|---:|---:|']
    for suf, label in CORNERS:
        p = [load('h90_' + tag + suf)['P_rad_mW'] for tag in ('472', '392', '332')]
        out.append('| %s | %.6f | %.6f | %.6f | %.2f× | %.2f× |' %
                   (label, *p, p[1]/p[0], p[2]/p[0]))
    return '\n'.join(out)


def t_ceiling():
    out = ['| 型号 | 含 10 Ω 解析效率 % | 线圈无损解析效率 % | 同口径改善倍数 |',
           '|---|---:|---:|---:|']
    for tag in ('332', '392', '472'):
        b = e.budget(e.design(90, '1812CS-' + tag))
        bi = e.budget(e.design(90, '1812CS-' + tag, coil_loss_scale=1e-6))
        out.append('| %s | %.4f | %.4f | %.2f× |' % (tag, b['eta']*100, bi['eta']*100, bi['eta']/b['eta']))
    return '\n'.join(out)


def _sweep(part, length):
    if part not in CACHE.get('__sweep__', {}):
        rows = json.loads((HERE / 'analytic_sweep.json').read_text(encoding='utf-8'))
        CACHE['__sweep__'] = {r['part'] + str(r['length_cm']): r for r in rows}
    return CACHE['__sweep__']['1812CS-' + part + str(length)]


def _cell(vals, fmts, bold):
    """Render one row, bolding the winning column when a direction is given.

    Bold is reserved for a column that is genuinely better on the stated metric.
    Rows where 'lower' merely means a smaller ask (total C, extra C0G) or where the
    verdict is a cost (peak dissipation) pass bold=None and stay unemphasised.
    """
    best = None
    if bold:
        best = vals.index(min(vals) if bold == 'min' else max(vals))
    out = []
    for i, (v, f) in enumerate(zip(vals, fmts)):
        s = f % v
        out.append('**%s**' % s if i == best else s)
    return ' | '.join(out)


def _closure(v):
    return ('−%.1e' % -v) if v < 0 else ('%.1e' % v)


def _sgn(v, f):
    """Format a signed percentage/count with a true minus sign."""
    return (f % v).replace('-', '−')


def t_main90():
    """Section 2 of 04: the 90 cm head-to-head, every cell from metrics."""
    tags = ('472', '392', '332')
    js = [load('h90_' + t) for t in tags]
    rows = ['| 项目 | **472（历史对照）** | **392（主基准）** | **332（效率对照）** |',
            '|---|---:|---:|---:|']

    def line(label, key, f, bold=None):
        rows.append('| %s | %s |' % (label, _cell([j[key] for j in js], [f] * 3, bold)))

    line('线圈 ESR Ω（模型典型）', 'coil_ESR_ohm', '%.3f', 'min')
    line('线圈 Q31（模型典型）', 'coil_Q31', '%.2f', 'max')
    line('所需串联总 C pF', 'C_total_pF', '%.3f')
    trim = []
    for t in tags:
        r = _sweep(t, 90)
        trim.append('**是**' if r['trim_only'] else '否（需 %.2f pF C0G）' % r['extra_C0G_pF'])
    rows.append('| 微调单独可达 | %s |' % ' | '.join(trim))
    line('端口电阻含 10 Ω', 'port_R_with_10ohm', '%.3f', 'min')
    line('**辐射支路载波电流 mA**', 'I_rad_carrier_mA', '%.4f', 'max')
    line('端口载波电流 mA', 'I_port_carrier_mA', '%.4f', 'max')
    line('调制度 m', 'modulation_index', '%.5f', 'max')
    line('**辐射功率 mW**', 'P_rad_mW', '%.6f', 'max')
    line('匹配网络效率 %', 'eta_match_to_rad_pct', '%.4f', 'max')
    line('驱动→辐射 %', 'eta_driver_to_rad_pct', '%.4f', 'max')
    line('电池→辐射 %', 'eta_battery_to_rad_pct', '%.6f', 'max')
    line('V2 估算 Vpp', 'V2_est_Vpp', '%.4f', 'max')
    line('链路缺口倍', 'link_shortfall', '%.2f', 'min')
    line('QCE 最小 VCE V', 'min_QCE_VCE_V', '%.4f', 'max')
    line('QEF 最小 VCE V', 'min_QEF_VCE_V', '%.3f', 'max')
    line('QEF 峰值 Ic mA', 'qef_peak_ic_mA', '%.2f')
    line('QEF 峰值功耗 mW', 'qef_peak_power_mW', '%.2f')
    line('包络欠冲 %阶跃', 'undershoot_pct', '%.1f', 'min')
    line('天线节点峰值 V', 'antenna_peak_V', '%.3f', 'min')
    line('整机预算 mW', 'battery_mW', '%.2f')
    rows.append('| 能量闭合相对误差 | %s |' % ' | '.join(
        _closure(j['energy_closure']['relative_error']) for j in js))
    return '\n'.join(rows)


def t_recheck100():
    """Section 3 of 04: the independent 100 cm recheck."""
    tags = ('472', '392', '332')
    js = [load('h100_' + t) for t in tags]
    rows = ['| 项目 | 472 | 392 | 332 |', '|---|---:|---:|---:|']

    def line(label, key, f, bold='max'):
        rows.append('| %s | %s |' % (label, _cell([j[key] for j in js], [f] * 3, bold)))

    line('所需串联总 C pF', 'C_total_pF', '%.3f', None)
    ex = [_sweep(t, 100)['extra_C0G_pF'] for t in tags]
    rows.append('| 外加 C0G pF | %s |' % ' | '.join(
        ('**%.2f**' % v) if v == 0 else ('%.2f' % v) for v in ex))
    line('端口电阻 Ω', 'port_R_with_10ohm', '%.3f', 'min')
    line('辐射支路载波 mA', 'I_rad_carrier_mA', '%.4f', 'max')
    line('辐射功率 mW', 'P_rad_mW', '%.5f', 'max')
    line('匹配效率 %', 'eta_match_to_rad_pct', '%.4f', 'max')
    line('V2 估算 Vpp', 'V2_est_Vpp', '%.4f', 'max')
    line('链路缺口倍', 'link_shortfall', '%.2f', 'min')
    return '\n'.join(rows)


def t_stress():
    """The stress/penalty table shared by README and the answer to question 3."""
    tags = ('472', '392', '332')
    js = [load('h90_' + t) for t in tags]
    pmax = 100 * (js[2]['qef_peak_power_mW'] / js[0]['qef_peak_power_mW'] - 1)
    dm = 100 * (js[2]['modulation_index'] / js[0]['modulation_index'] - 1)
    rows = ['| 检查项 | 472 | 392 | 332 | 判定 |', '|---|---:|---:|---:|---|']

    def line(label, key, f, verdict, bold=None):
        rows.append('| %s | %s | %s |' % (
            label, _cell([j[key] for j in js], [f] * 3, bold), verdict))

    line('QCE 最小 VCE V', 'min_QCE_VCE_V', '%.4f', '无恶化')
    line('QEF 最小 VCE V', 'min_QEF_VCE_V', '%.3f', '**改善**', 'max')
    line('QEF 峰值 Ic mA', 'qef_peak_ic_mA', '%.2f', '在能力内')
    line('QEF 峰值功耗 mW', 'qef_peak_power_mW', '%.2f', '+%s%%，可接受' % _sgn(pmax, '%.1f'))
    line('整机预算 mW', 'battery_mW', '%.2f', '**不变**')
    line('调制度 m', 'modulation_index', '%.5f', '**%s%%（代价）**' % _sgn(dm, '%.1f'), 'max')
    line('包络欠冲 %阶跃', 'undershoot_pct', '%.1f', '**变差（代价）**', 'min')
    return '\n'.join(rows)


def t_penalty():
    """The price of choosing 332 over 472 at 90 cm, all differences computed."""
    a, b = load('h90_472'), load('h90_332')
    ea, eb = _sweep('472', 90), _sweep('332', 90)
    dm = 100 * (b['modulation_index'] / a['modulation_index'] - 1)
    dv = 100 * (b['antenna_peak_V'] / a['antenna_peak_V'] - 1)
    dp = 100 * (b['qef_peak_power_mW'] / a['qef_peak_power_mW'] - 1)
    du = b['undershoot_pct'] - a['undershoot_pct']
    rows = ['| 332 相对 472 的代价 | 数值 |', '|---|---|',
            '| 所需串联电容 | %.2f pF vs %.2f pF（**%.1f 倍**） |' % (
                b['C_total_pF'], a['C_total_pF'], b['C_total_pF'] / a['C_total_pF']),
            '| 额外元件 | 必须外加 %.2f pF C0G（472 无需外加） |' % eb['extra_C0G_pF'],
            '| 调制度 | %.5f vs %.5f（**%s%%**） |' % (
                b['modulation_index'], a['modulation_index'], _sgn(dm, '%.1f')),
            '| 天线节点峰值电压 | %.3f V vs %.3f V（**+%s%%**） |' % (
                b['antenna_peak_V'], a['antenna_peak_V'], _sgn(dv, '%.1f')),
            '| QEF 峰值功耗 | %.2f vs %.2f mW（+%s%%） |' % (
                b['qef_peak_power_mW'], a['qef_peak_power_mW'], _sgn(dp, '%.1f')),
            '| 包络欠冲 | %.1f%% vs %.1f%%（**变差 %s 个百分点**） |' % (
                b['undershoot_pct'], a['undershoot_pct'], _sgn(du, '%.1f'))]
    return '\n'.join(rows)


def t_transient(cases, cols=None):
    cols = cols or [('I_rad_carrier_mA', '辐射支路载波 mA', '%.4f'),
                    ('I_port_carrier_mA', '端口载波 mA', '%.4f'),
                    ('modulation_index', '调制度 m', '%.4f'),
                    ('V2_est_Vpp', 'V2 估算 Vpp', '%.3f'),
                    ('min_QCE_VCE_V', 'QCE 最小 VCE V', '%.4f'),
                    ('qef_peak_ic_mA', 'QEF 峰值 Ic mA', '%.2f'),
                    ('undershoot_pct', '欠冲 %阶跃', '%.1f'),
                    ('eta_match_to_rad_pct', '匹配效率 %', '%.4f')]
    out = ['| 工况 | ' + ' | '.join(c[1] for c in cols) + ' |',
           '|---|' + '---:|' * len(cols)]
    for n in cases:
        j = load(n)
        out.append('| %s | ' % n + ' | '.join(c[2] % j[c[0]] for c in cols) + ' |')
    return '\n'.join(out)


def t_efficiency(cases):
    out = ['| 工况 | 端口R Ω | 辐射功率 mW | 匹配网络效率 % | 驱动→辐射 % | 电池→辐射 % |',
           '|---|---:|---:|---:|---:|---:|']
    for n in cases:
        j = load(n)
        out.append('| %s | %.3f | %.5f | %.4f | %.4f | %.5f |' % (
            n, j['port_R_with_10ohm'], j['P_rad_mW'], j['eta_match_to_rad_pct'],
            j['eta_driver_to_rad_pct'], j['eta_battery_to_rad_pct']))
    return '\n'.join(out)


def t_chain():
    """Chain 1 vs chain 2 is NOT allowed: 31 MHz < 2 x 30.72 MHz."""
    return ('| 阶次 | 频点 | 结论 |\n|---|---|---|\n'
            '| 基波 | 31.00 MHz | 载波，唯一辐射项 |\n'
            '| 2 次 | 62.00 MHz | 仍低于 2×30.72=61.44？否，已高于；但幅度由集电极电流削顶决定，需实测 |\n'
            '| 3 次 | 93.00 MHz | 高于 1812CS-472 保证 SRF 115 MHz 以下，寄生并联支路开始分流 |\n')


def main():
    base = [c[0] for c in cand.BASE_CASES]
    sec = [c[0] for c in cand.SECONDARY_CASES]
    for c in base + sec:
        load(c)
    write('tables.md',
          '# 自动生成的表\n\n## 31 MHz 模型阻抗\n\n' + t_impedance() +
          '\n\n## 保证下限\n\n' + t_floor() +
          '\n\n## 候选总表\n\n' + t_analytic() +
          '\n\n## 同族扫描\n\n' + t_family() +
          '\n\n## 功率\n\n' + t_power(base) +
          '\n\n## 电阻\n\n' + t_resistance(base) +
          '\n\n## 瞬态\n\n' + t_transient(base) +
          '\n\n## 效率\n\n' + t_efficiency(base))
    write('table_corners.md', t_corners())
    write('table_corners3.md', t_corners())
    write('table_power.md', t_power(base))
    write('table_transient.md', t_transient(base + sec) + '\n\n' + t_efficiency(base + sec))
    write('table_ceiling.md', t_ceiling())
    write('table_main90.md', t_main90())
    write('table_recheck100.md', t_recheck100())
    write('table_stress.md', t_stress())
    write('table_penalty.md', t_penalty())
    summary = [json.loads(p.read_text(encoding='utf-8')) for p in sorted(OUT.glob('*_metrics.json'))]
    write('joint_summary.json', json.dumps(summary, indent=2, ensure_ascii=False))
    print('OK')


if __name__ == '__main__':
    main()

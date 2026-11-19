"""Refresh the handoff report from audited cached metrics; never simulates."""
import json
import re
from pathlib import Path
import make_results as m

HERE = Path(__file__).resolve().parent


def write(name, text):
    (HERE / name).write_text(text, encoding='utf-8')


def swap_block(text, head, body):
    """Replace the markdown block that starts with head by body, keeping the tail.

    Documents quote rendered tables; this keeps the two in step so the audit's
    verbatim-copy check stays satisfiable after a regeneration.
    """
    a = text.index(head)
    b = text.index('\n\n', a)
    return text[:a] + body.strip() + text[b:]


def _num(v, f='%.4f'):
    """Format a number with a true minus sign, matching the documents' style."""
    return (f % v).replace('-', '−')


def main():
    verification = json.loads((HERE / 'verification.json').read_text(encoding='utf-8'))
    if verification['status'] != 'PASS':
        raise SystemExit('audit must pass before updating the report')
    ratios = [[m.load('h90_' + tag + suf)['P_rad_mW'] / m.load('h90_472' + suf)['P_rad_mW']
               for suf, _ in m.CORNERS] for tag in ('392', '332')]
    ranges = ['%.2f–%.2f×' % (min(r), max(r)) for r in ratios]
    worst = max(abs(json.loads(p.read_text(encoding='utf-8'))['energy_closure']['relative_error'])
                for p in (HERE / 'joint').glob('*_metrics.json'))
    s = (HERE / '04_候选对照与验证.md').read_text(encoding='utf-8')
    s = s.replace('全部工况为冻结驱动完整瞬态，各候选各自重调到 31 MHz。',
                  '全部工况为冻结驱动完整瞬态；名义比较各自按解析模型重调到 31 MHz，L±5% 与额外 0.5 pF 为未重调失谐压力点。解析模型与网表的差异见 [05 §8](05_瞬态验证与边界.md)。')
    s = s.replace('能量闭合 ≤1.6×10⁻⁷', '能量闭合最大绝对相对误差 %.2e' % worst)
    # The section 2 and section 3 tables are rendered, never typed by hand.
    s = swap_block(s, '| 项目 | **472（历史对照）** |', m.t_main90())
    s = swap_block(s, '| 项目 | 472 | 392 | 332 |', m.t_recheck100())
    s = swap_block(s, '| 332 相对 472 的代价 |', m.t_penalty())
    g90 = [100 * (m.load('h90_' + t)['P_rad_mW'] / m.load('h90_472')['P_rad_mW'] - 1)
           for t in ('392', '332')]
    g100 = [100 * (m.load('h100_' + t)['P_rad_mW'] / m.load('h100_472')['P_rad_mW'] - 1)
            for t in ('392', '332')]
    s = re.sub(r'\*\*100 cm 上 392 比 472 高 .*?几乎一致。',
               '**100 cm 上 392 比 472 高 %.1f%%、332 比 472 高 %.1f%%**，与 90 cm 的 %.1f%%/%.1f%% 几乎一致。'
               % (g100[0], g100[1], g90[0], g90[1]), s)
    s = s.replace('100 cm 独立复核给出 25.7%/36.6%',
                  '100 cm 独立复核给出 %.1f%%/%.1f%%' % (g100[0], g100[1]))
    exact = '（%.4f%%／%.4f%%，下文百分比均由指标 JSON 直接相除）' % (g90[0], g90[1])
    s = re.sub(r'\*\*以辐射功率计：392 比 472 高 .*?(?=\n)',
               '**以辐射功率计：392 比 472 高 %.1f%%，332 比 472 高 %.1f%%。**%s'
               % (g90[0], g90[1], exact), s)
    a = s.index('| 角点 |', s.index('## 4.'))
    b = s.index('\n---', a)
    p0 = m.load('h90_472')['P_rad_mW']
    drops = [100 * (1 - m.load('h90_472' + suf)['P_rad_mW'] / p0)
             for suf in ('_Lm5', '_Lp5', '_cx5')]
    s = (s[:a] + m.t_corners() + '\n\n**典型工况及全部 8 类角点中，392 与 332 均优于 472**，392/472 为 '
         + ranges[0] + '，332/472 为 ' + ranges[1] + '。这只覆盖列出的模型压力点，不代表全部器件与安装容差组合。\n\n'
         + 'L−5%%、L+5%% 与线圈端间额外 0.5 pF 均保留名义调谐电容。472 的辐射功率分别下降 %.1f%%、%.1f%%、%.1f%%。这些压力点说明安装后重新调谐的重要性。损耗 ×2 时 332 仍约为 472 的 1.60 倍。\n' % tuple(drops) + s[b:])
    a = s.index('| 型号 | 下限 Q31') if '| 型号 | 下限 Q31' in s else s.index('| 型号 | 拟合 Q31')
    b = s.index('\n---', a)
    rows = ['| 型号 | 拟合 Q31 | 解析端口 R Ω | 辐射功率 mW | 相对 472 同一下限角点 |', '|---|---:|---:|---:|---:|']
    ref = m.load('h90_472_Qds')['P_rad_mW']
    for tag in ('472', '392', '332'):
        j = m.load('h90_' + tag + '_Qds')
        rows.append('| %s | %.2f | %.3f | %.6f | %.2f× |' %
                    (tag, j['coil_Q31'], j['port_R_with_10ohm'], j['P_rad_mW'], j['P_rad_mW'] / ref))
    s = s[:a] + '\n'.join(rows) + '\n\n三个型号在各自下限拟合角点下仍保持优势。Q@50 MHz 的保证值不能直接变成厂家保证的 Q31；这里是模型敏感性推演。\n' + s[b:]
    a, b = s.index('## 6.'), s.index('## 7.')
    s = s[:a] + '''## 6. 剩余降低空间：必须按同一效率口径比较

原文将含 10 Ω 的解析效率上限与不含 10 Ω 的瞬态匹配效率混排，得出的“5.36%→5.55%、仅剩 3.5%”无效。以下统一采用 **31 MHz 解析端口输入（含 10 Ω）→辐射** 口径，仅比较闭式预算，不是冻结驱动下的辐射功率增益预测。

''' + m.t_ceiling() + '''

332 对应 3.1365%→5.5536%，同口径为 1.77 倍；392/472 分别为 1.84/2.12 倍。“线圈无损”指模型损耗倍率设为 1e-6 的解析边界，未运行无损线圈完整瞬态。若按排除 10 Ω 的匹配网络输入口径，332 的解析值为 5.4592%→22.5174%；同样不能与瞬态值混除。

''' + m.t_power(['h90_472', 'h90_392', 'h90_332']) + '''

332 的线圈损耗仍约 44.0%，取样电阻约 42.4%，**取样电阻是第二大损耗项**。继续降低线圈损耗仍有解析空间，但实际收益必须连同补偿元件及驱动负载变化重新验证；固定 10 Ω 的边界不变。

---

''' + s[b:]
    a = s.index('**答：', s.index('### 问题一'))
    b = s.index('### 问题二', a)
    s = s[:a] + '''**答：在含 10 Ω 的统一解析端口口径下，线圈趋于无损对应 1.77–2.12 倍效率上限；不是整机辐射功率已经验证的增益。**

90 cm 主比较的瞬态匹配效率为 3.6320%（472）、4.8153%（392）、5.3649%（332）。它们排除了取样电阻，不能与含取样电阻的 5.55% 解析上限直接相除。332 的取样损耗占 42.4%，略低于线圈 44.0%；后续需共同考虑线圈、补偿网络与固定 10 Ω 的限制。

''' + s[b:]
    s = re.sub(r'8 个角点全部保持优势（392：.*?）；',
               '8 个角点全部保持优势（392：' + ranges[0] + '，332：' + ranges[1] + '）；', s)
    s = s.replace('链路缺口从 1.89× 略增到 1.65× 的**改善**被部分抵消', '链路缺口从 1.89× 降到 1.65× 的改善被部分抵消')
    s = s.replace('| **辐射功率 mW** | 0.01327 | 0.01671 | **0.01802** |', '| **辐射功率 mW** | 0.013272 | 0.016711 | **0.018021** |')
    s = s.replace('**答：没有。**', '**答：在本轮已核查的候选集合内，未找到有足够证据证明整体更优的外购件。**')
    write('04_候选对照与验证.md', s)
    s = (HERE / 'README.md').read_text(encoding='utf-8')
    s = re.sub(r'4\. \*\*收益在.*?(?=\n5\.)',
               '4. **收益在已测试容差与寄生下仍成立。** 8 类角点（L±5%、损耗×2、各型号 Q 下限、SRF 修正、接触 2 Ω、底座 2 pF、额外 0.5 pF）中，392/472 为 '
               + ranges[0] + '，332/472 为 ' + ranges[1] + '。L±5% 与额外 0.5 pF 均未重调。', s, flags=re.S)
    s = re.sub(r'3\. \*\*指标改为重调后的辐射收益。\*\*.*?(?=\n4\.)',
               '3. **指标改为重调后的辐射收益。** 90 cm、10 Ω 取样、各自重调到 31 MHz：'
               '**332 的辐射功率比 472 高 %.1f%%，392 高 %.1f%%**。100 cm 独立复核得 %.1f%%／%.1f%%，一致。'
               % (g90[1], g90[0], g100[1], g100[0]), s, flags=re.S)
    s = re.sub(r'6\. \*\*剩余.*?(?=\n\n)',
               '6. **剩余空间按同一效率口径重算。** 含 10 Ω 的解析端口效率，332 为 3.1365%→5.5536%（线圈趋于无损），即 1.77 倍；不是“瞬态匹配效率 5.36%→5.55%”。取样电阻占 42.4%，仍略低于线圈 44.0%。', s, flags=re.S)
    a = s.index('\n\n', s.index('### 一、'))
    b = s.index('### 二、', a)
    s = s[:a] + '\n\n**同一解析口径下，线圈趋于无损的效率上限为 1.77–2.12 倍；实际辐射收益须重新做完整瞬态。**\n\n' + m.t_ceiling() + '\n\n原“只剩 3.5%”结论因混用效率分母而作废。上述表全部为 90 cm 解析结果，不能与不含 10 Ω 的瞬态匹配效率直接相除。\n\n' + s[b:]
    s = s.replace('| 35 工况汇总 |', '| 33 工况汇总（30 正式 + 3 历史 Qx） |')
    s = s.replace('# 4) 汇总\npy -3 make_results.py\n\n# 5) 校验\npy -3 verify_stage.py', '# 4) 只读缓存重算与审计\npy -3 reanalyse_all.py\npy -3 verify_stage.py\n\n# 5) 生成表格与回填报告\npy -3 make_results.py\npy -3 finish_report.py')
    s = s.replace('**没有。** 详见', '**本轮已核查集合内未找到有充分证据的更优件。** 详见')
    s = swap_block(s, '| 检查项 | 472 | 392 | 332 | 判定 |', m.t_stress())
    s = s.split('\n\n## 交接执行验收')[0]
    s += '\n\n## 交接执行验收\n\n已补齐 33 份波形并完成串行重算；%d 项数值/缓存审计通过，能量闭合最大绝对相对误差 %.2e。' % (verification['checks'], worst)
    s += '文档中的表格均为渲染副本，由审计逐字比对。'
    s += '详见 [执行记录](07_交接执行记录.md)。解析模型与冻结瞬态网表存在连接位置差异，见 [05 §8](05_瞬态验证与边界.md)；通过审计不等于硬件验收。价格库存沿用原核查快照，本次未重新核查市场。\n'
    write('README.md', s)
    records = ['# AM-ALT.3.4 交接执行记录', '', '2026-11-17。交接要求的缓存补齐、重算、审计和报告回填已完成。', '',
               '## 执行结果', '',
               '- 33 个工况的 `.cir/.raw/.log/*_metrics.json` 已齐备：30 个正式工况，3 个历史 `_Qx` 对照。',
               '- 补跑六个 L±5% 未重调压力点及 h90_332、h100_332、h100_472；保留已有其他波形。',
               '- 串行只读缓存重算后，`verify_stage.py` 共 %d 项检查通过，0 失败。' % verification['checks'],
               '- 能量闭合最大绝对相对误差 %.3e；门槛为 1e-5。' % worst, '',
               '## 核心复核', '',
               '| 工况 | 辐射功率 mW | 解析端口电抗 Ω | 网表实际端口电抗 Ω |', '|---|---:|---:|---:|']
    for name in ['h90_472', 'h90_392', 'h90_332', 'h100_332', 'h100_472', 'h90_472_Lm5', 'h90_472_Lp5']:
        j = m.load(name)
        za, zn = j['port_Z31'][1], j['netlist_port_Z31'][1]
        records.append('| %s | %.6f | %s | %s |' % (
            name, j['P_rad_mW'], _num(za), _num(zn)))
    records += ['', '## 修复与更正', '',
                '1. 旧六个 L±5% 指标仍标记 retune=True；修复重建脚本，明确采用 False，完成重跑。',
                '2. reanalyse_all 原来只枚举存在的 raw，会漏报缺失波形；改为枚举全部指标模板，并拒绝缺失或不兼容缓存，不再隐式启动仿真。reanalyse.py 同样改为只读重算。',
                '3. 修复 candidates.py 的 SRF 电容重复单位换算；移除解析端口计算中把 CINSTALL 重复加到天线支路的错误。',
                '4. 修复校验脚本把 100 cm 的 392/472 与 90 cm 的 332/472 比较的问题；覆盖 Qds、SRF 和全部失谐角点，检查网表、设置与工况完整性。',
                '5. 修复表格生成器读取不存在的电阻键；生成角点表、功率表、瞬态表、同口径解析上限表和 33 工况汇总。',
                '6. 更正“5.36%→5.55%、只剩 3.5%”的分母混用，以及“取样电阻已为第一大损耗”的表述。332 的线圈约 44.0%，取样约 42.4%。',
                '7. 回填 04 与 README 的角点及 Qds 数据，补齐 06，并追加上级索引；上一阶段历史文件未改写。',
                '8. 交接最后一步曾中断：`verify_stage.py` 有 1 项失败，因此 `finish_report.py` 从未执行。失败项是窗口端点约定不一致——'
                '存储值在落入 `window_s` 的采样点上积分，校验式却把插值出来的零交叉边界也纳入积分域，二者相差 8.1e-7（相对）。'
                '改为对同一采样区间独立积分后逐位吻合，并新增“端点约定不影响结果”的界限检查。',
                '9. 04 §2/§3 的原表是手打数字，末位与指标不符 6 处（调制度、欠冲、100 cm 的 V2）。改为由 `make_results.py` 渲染 '
                '`table_main90/table_recheck100/table_stress/table_penalty`，并新增“文档中的表必须是渲染表的逐字副本”检查；'
                '该检查已用注入一位偏差的方式验证过能失败。',
                '10. 05 §8 引用的网表线圈 ESR（10.366/11.683/16.170 Ω）原为手写声明，现已纳入审计，由 `verify_stage.py` '
                '按冻结网表拓扑复算后与文档逐位比对，并确认三者均高于对应解析值。', '',
                '## 明确保留的限制', '',
                '- 解析线圈与冻结瞬态网表的拓扑不同，现已分别报告阻抗，见 [05 §8](05_瞬态验证与边界.md)。本轮未通过重写整个负载模型来改变冻结基线。',
                '- Q31 下限是模型推演，非厂家直接保证；无损线圈上限是解析结果，非完整瞬态增益。',
                '- 未重新查询价格库存；未采购、未焊接、未实测；6 m / V2≥4 Vpp 与包络质量尚未通过硬件验收。', '',
                '## 复现', '', '```powershell', 'py -3 reanalyse_all.py', 'py -3 verify_stage.py',
                'py -3 make_results.py', 'py -3 finish_report.py', '```', '']
    write('07_交接执行记录.md', '\n'.join(records))
    handoff = HERE / '00_交接.md'
    old = handoff.read_text(encoding='utf-8')
    marker = '## 接手执行追加（2026-11-17）'
    if marker not in old:
        old += ('\n\n---\n\n' + marker + '\n\n'
                '本交接待办已执行完成，以上内容保留为接手时的历史快照；当前状态以 '
                '[07_交接执行记录.md](07_交接执行记录.md) 和 [README.md](README.md) 为准。'
                '已补齐 33 工况、完成只读缓存重算与审计、回填角点及 Qds 数据。'
                '原 §3.5 的效率上限表混用了分母，已在 04 §6 更正；不再使用“只剩 3.5%”结论。'
                '解析模型与冻结网表差异保留为明确限制，不能把数值审计通过等同于硬件验收。\n')
        handoff.write_text(old, encoding='utf-8')
    root = HERE.parents[2]
    for rel in ['README.md', '项目管理/01_总计划.md', '项目管理/02_当前阶段目标.md', '项目管理/03_当前实现状态.md']:
        path = root / rel
        text = path.read_text(encoding='utf-8')
        title = '## AM-ALT.3.4 交接收尾（2026-11-17）'
        if title in text:
            continue
        prefix = ('../' if path.parent != root else '') + 'simulation/v4_hardware/stage_am_alt3_4_20261117/'
        intro = (title + '\n\n当前阶段报告见 [AM-ALT.3.4](' + prefix + 'README.md)。'
                 '33 工况已补齐并完成重算与审计；52.3% 的旧损耗比例更正见 [01_三条更正]('
                 + prefix + '01_三条更正.md)，完成情况与模型限制见 [交接执行记录]('
                 + prefix + '07_交接执行记录.md)。仍固定 90 cm 主比较、10 Ω 取样与外购成品边界；未通过硬件验收。'
                 '\n\n以下保留原阶段记录；与本条冲突的阶段状态以上述 AM-ALT.3.4 为准。\n\n---\n\n')
        path.write_text(intro + text, encoding='utf-8')
    print('Updated report; ranges', ranges, 'closure', worst)


if __name__ == '__main__':
    main()

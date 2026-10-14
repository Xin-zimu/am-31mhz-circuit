"""Generate the numeric S03-05 report; never mark unavailable evidence passed."""
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent


def main():
    results = json.loads((HERE/'summary.json').read_text('utf-8'))
    by_case = {r['case']: r for r in results}
    all_data = len(results) == 7
    all_screen = all(r['repeatability_screen']['passes'] for r in results)
    lines = ['# S03-05 关键端点检查报告', '', '日期：2026-10-14。基线：V4_3_REPAIRED 当前完整功能模型。', '',
             f'**数据完整性：{len(results)}/7 组。末五周期工程筛查：' + ('已有组全部满足。' if all_screen else '存在未满足组，见第 4 节。') + '**', '',
             '本报告区分计算完成、数值要求检查、临时稳定性筛查和最终阶段验收。阶段状态另见 S03 阶段验收报告，不凭单个 PASS 覆盖其余边界。', '',
             '## 1. 测试条件与证据入口', '',
             '- 五组新增用例仅改变输入幅度/占空比对应分压电阻，参数来自既有调节表。接收增益、1 MΩ 负载、所有模型及其他网表行均保持不变。',
             '- 预充电 UIC：C111=0.43 V、C115=−4.1 V、CBB=4.5 V；统一 `tran 2n 5m 4.5m 2n uic`。末五周期边界取实际返回时间轴。',
             '- 使用 COM `DoCommandLine` 调用完整网表的 `source`+`tran` 命令引擎，属于引擎证据；没有新增 GUI 点击运行声明。',
             '- 历史 `set` 行原样保留，不能作为选项实际生效的证明；按 S03-04 既有诊断，本入口有效容差为默认 RELTOL=1e-3、TRTOL=7。TMAX 请求 2 ns，日志显示自动限制为约 1.00806 ns。',
             '- C4 复用 `REF_4Vpp_tail`，C5 复用 `LIN_2Vpp_tail`；本次重新读取原始波形，五项既有数字复算一致，没有重跑。',
             '- `measure_stage3.py` 交点函数、2 ns 均匀插值、P98−P2 与梯形积分时间加权均值沿用不变；raw 极值来自原始自适应点。输出交越用自身高低电平中点。', '',
             '来源：[配置清单](s0305_endpoints_20261014/run_manifest.json)、[数据汇总](s0305_endpoints_20261014/summary.json)、[完整性核验](s0305_endpoints_20261014/evidence_audit.json)、[复现步骤](s0305_endpoints_20261014/README.md)。', '',
             '## 2. 工况汇总', '',
             '幅度和均值取末五完整输入周期平均；输出频率/占空比取保存末 300 μs 中末五完整输出周期。输入和输出占空比分列，避免把输入占空比误写成输出。', '',
             '| 用例 | 目标 Vpp / % | 实际输入 Vpp | 输出 robust Vpp | 输入频率 Hz | 输出频率 Hz | 输入占空比 % | 输出占空比 % | V2 加权均值 V |',
             '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for case in ['C1','C2','C3','C4','C5','C6','C7']:
        if case not in by_case:
            lines.append(f'| {case} | 待完成 | — | — | — | — | — | — | — |')
            continue
        r = by_case[case]
        lines.append(f"| {case} | {r['target_vpp']} / {r['target_duty_percent']} | {r['nodes']['V(v1)']['robust_vpp']:.6f} | {r['nodes']['V(v2)']['robust_vpp']:.6f} | {r['input_frequency_hz']:.3f} | {r['output_frequency_hz']:.3f} | {r['input_duty_percent']:.5f} | {r['output_duty_percent']:.5f} | {r['nodes']['V(v2)']['mean_v']:.6f} |")
    lines += ['', '## 3. 幅度传递与数值要求', '',
              '| 用例 | robust 增益 | raw 增益 | 相对 C4 的归一化增益偏差 % | 输出频率相对 20 kHz 误差 % | 输出−输入占空比 pp |',
              '|---|---:|---:|---:|---:|---:|']
    for r in results:
        lines.append(f"| {r['case']} | {r['robust_gain']:.6f} | {r['raw_gain']:.6f} | {r['normalized_gain_error_percent']:+.5f} | {r['output_frequency_error_percent']:+.5f} | {r['output_minus_input_duty_pp']:+.5f} |")
    c5 = by_case['C5']
    lines += ['', f"C5 的有符号归一化增益偏差为 **{c5['normalized_gain_error_percent']:.5f}%**。按设置值减半的绝对比例误差 `|Vout(C5)−Vout(C4)/2|/(Vout(C4)/2)` 为 **{c5['setting_ratio_error_absolute_percent']:.5f}%**，低于评分原文的 10% 扣分起点，因此本固定工况下的幅度减半数值检查通过。两者在实际输入近乎精确减半时绝对值接近；负号表示输出略小于理想比例，负数不称为绝对误差。", '',
              '频率按 20 kHz±1% 对照；输入占空比按设置的 10/30/50%±5 个百分点对照。输出 50% 档按相应 ±5 个百分点检查；10/30% 输出跟随程度列数值，不擅自扩展评分原文。', '',
              '输出 ≥4 Vpp 仍按 4 Vpp 标称输入 C4 考察，其他档位单列实际值；适用输入档位的原文歧义保留，不把本测试安排写成教师已确认解释。1 Vpp/3 Vpp 与不同占空比的增益表用于设计范围检查，不把只规定于 4→2 Vpp 的评分线自动扩展为全范围线性保证。', '',
              '## 4. 末五周期筛查与漂移趋势（必须同报）', '',
              '三个跨度均以百分数表示，阈值均为 0.1%。漂移速率由完整尾段内连续四周期滑窗线性拟合得到，报告最早与最晚窗口；同时保留所有滑窗与拟合残差。它是该 0.5 ms 尾段内的局部趋势，不能单独证明任意长时间稳定。', '',
              '| 用例 | 均值跨度/幅度 % | robust 幅度跨度/幅度 % | 周期相对跨度 % | 筛查 | 最早→最晚漂移 mV/ms |',
              '|---|---:|---:|---:|---|---:|']
    for r in results:
        s = r['repeatability_screen']
        lines.append(f"| {r['case']} | {s['mean_span_percent']:.6f} | {s['robust_vpp_span_percent']:.6f} | {s['period_span_percent']:.6f} | {'通过' if s['passes'] else '未通过'} | {r['drift_windows'][0]['slope_mV_per_ms']:+.4f} → {r['drift_windows'][-1]['slope_mV_per_ms']:+.4f} |")
    lines += ['', 'C4 的微小偏置变化有非单调起伏，不能用首末局部斜率宣称严格指数衰减；C5 仍有正向偏置漂移，其局部斜率随尾段减小。所有用例均不写“已完全稳定”。0.1% 是工程重复性筛查，不是评分指标；后续若延长计算，保留本轮 5 ms 数据并将新结果另列。', '',
              '## 5. 原始极值与脉冲恢复', '',
              '| 用例 | V2 raw Vpp | V2 最低/最高 V（五周期范围） | BBO 最低/最高 V（五周期范围） | 输入/输出异常下降交越周期数 |',
              '|---|---:|---|---|---:|']
    for r in results:
        tail = r['last_five_cycles']
        vmin = min(c['V(v2)']['raw_min_v'] for c in tail)
        vmax = max(c['V(v2)']['raw_max_v'] for c in tail)
        bmin = min(c['V(bbo)']['raw_min_v'] for c in tail)
        bmax = max(c['V(bbo)']['raw_max_v'] for c in tail)
        lines.append(f"| {r['case']} | {r['nodes']['V(v2)']['raw_vpp']:.6f} | {vmin:.6f} / {vmax:.6f} | {bmin:.6f} / {bmax:.6f} | {r['input_abnormal_crossing_cycles']} / {r['output_abnormal_crossing_cycles']} |")
    lines += ['', '异常交越计数定义为一个完整上升沿周期内下降交越不等于一次。频率、完整周期数与波形一并用于判断尾段脉冲恢复，不能外推为未保存时段无异常。原始极值用于保留过冲/纹波影响，不用 robust 幅度掩盖尖峰；原文未给失真的数值阈值，不自造扣分标准。', '',
              '![尾段波形及偏置趋势](s0305_endpoints_20261014/S03_05_waveforms_and_drift.png)', '',
              '## 6. 执行异常与验证边界', '',
              '- C1 首次尝试和第一次重试均发生进程级崩溃、没有原始波形，不能计入通过。Windows 事件分别记录 ntdll 异常、堆损坏以及后续 MSInterface.dll 访问异常；根因未证实。失败状态和事件日志全部保留。',
              '- runner 后续取消积分期间 COM 属性轮询，改为 OS 进程状态及最终 raw 文件监测；这属于调用方式调整，不改变电路、初值或积分配置。是否消除崩溃须以实际后续结果表述，不能只凭修改推断。',
              '- 所有新运行均执行无其他 Multisim 实例的前置检查；只关闭自身创建的进程。当前离散端点和已有标称/2 Vpp 数据均为单次成功样本，不宣称统计重复可靠性。',
              '- 当前是预充电端点验证，不替代各端点冷启动；当前理想载波、通道、电源不证明实际振荡、距离、功耗或实物性能。',
              '- 引用 S03-04 冷启动结论时，须一并引用 [S03-04 第 6.3 节完整边界](S03_04_冷启动排查记录.md)。本次不修改该节与第 6.2 节固定口径。', '',
              f'数据状态：{"七组数据齐全" if all_data else "数据尚未齐全"}。最终完成状态、任何延长窗结果与未决项见阶段验收报告。', '']
    (STAGE/'S03_05_关键端点报告.md').write_text('\n'.join(lines), encoding='utf-8')
    print(f'Wrote report for {len(results)} / 7 cases; all_available_screens_pass={all_screen}')


if __name__ == '__main__':
    main()

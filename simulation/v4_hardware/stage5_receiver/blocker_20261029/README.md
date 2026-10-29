# S05-05 独立证据目录

执行于2026-10-29～30。入口：[S05-05报告](../S05_05_R2邻近阻塞诊断与AB决策.md)。

本轮命名：`R2` 是 S05-03 的 B/R2 历史候选；`B_E1` 等是本轮线性度对照；`A2M_r1M` / `A1M_r1M` 是约2/1 MHz的有损双调谐夹具。两轮的 A/B 命名不能混用。没有替换原 R2 或冻结整机。

## 证据与有效性

- `results/*.json`、`results/*.log`、`netlists/*.cir`：不可变用例记录。
- raw：`D:/ms_xsp/s05_blocker_20261029/`，二进制数组不入 Git，迁移必须另带。
- `summary.json`：有效比较用例；`excluded_or_unqualified_arrays` 保留排除名单。
- `failures/`：无有效数组的数值失败、超时或主动中止；不自动重试。
- `qualification_notes.json`：解释悬浮节点和 G=22 初始化问题，包括主动终止记录。
- `baseline_snapshot.json` / `records_before/`：起点哈希与管理文档备份。
- `audit.json`：网表/数组/日志/模型哈希、原基线保持、独立傅里叶复算。
- `evidence_manifest.json`：小文件及原始数组索引。报告、摘要和绘图可重新生成；原始用例不可覆盖。

成功求解不等于工作点或电路验收通过。旧 `A2M_*` / `A1M_*` 中未带 `_r1M` 的悬浮节点结果不得引用为 A 路线通过；`A2M_dc_ac` 仅是1 GΩ回路诊断。G=22无后缀及`_ns`的输出虽有数组，参考初值不符合3 V且有漂移，不纳入正常工作结论。`_ic`两次未得到有效数组。

## 运行环境和入口

Windows，Python 3.13，NumPy 2.3.5，SciPy 1.17.1，matplotlib 3.10.8；求解器路径固定在 `run_diagnosis.py` 所导入的历史运行模块中，ngspice-47的SHA-256写入每个结果。

在仓库根目录依次执行：

```powershell
py -3.13 simulation/v4_hardware/stage5_receiver/blocker_20261029/run_diagnosis.py baseline
py -3.13 simulation/v4_hardware/stage5_receiver/blocker_20261029/isolate_detector.py
py -3.13 simulation/v4_hardware/stage5_receiver/blocker_20261029/run_diagnosis.py b
py -3.13 simulation/v4_hardware/stage5_receiver/blocker_20261029/run_a.py
py -3.13 simulation/v4_hardware/stage5_receiver/blocker_20261029/run_final.py
py -3.13 simulation/v4_hardware/stage5_receiver/blocker_20261029/run_checks.py
py -3.13 simulation/v4_hardware/stage5_receiver/blocker_20261029/ideal_bandwidth.py
py -3.13 simulation/v4_hardware/stage5_receiver/blocker_20261029/analyze_waveforms.py
py -3.13 simulation/v4_hardware/stage5_receiver/blocker_20261029/summarize.py
py -3.13 simulation/v4_hardware/stage5_receiver/blocker_20261029/audit.py
```

主入口只复用/运行有效批次，不触发失败G=22或旧启动测试。`design_filters.py`只用于复查线性网络设计，不是求解器验收；正式A测试直接使用已保存的`filters/*_r1M.cir`。

`wave_metrics`为通用波形函数。其阈值交越的频率/占空比字段仅用于无强拍频的方波，不可拿正弦或强拍频出现的多个交越认定频率异常。阻塞主指标是相干20 kHz傅里叶系数；RF载波和边带分别保存。

`run_diagnosis.py`使用新名字保存改变的配置，90 s为单次求解预算。完整OPA仿真保持显式预偏置，绝非冷启动；G=22失败说明需要进一步隔离初始化问题，不证明电路不能启动。

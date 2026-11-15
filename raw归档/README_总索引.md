# raw 归档总索引

生成：2026-11-15 21:20。用途：本次 raw 清理（ABCD 档方案）的入口索引。
原则：先记录（SHA256/指标/波形图/重跑配方）、后删除；A 档零记录、B/C 档全量记录、D 档保留。

## 工具

| 文件 | 用途 |
|---|---|
| `raw_archive.py` | 解析 raw（ngspice ASCII/Binary、LTspice UTF-16、纯 ASCII Values）、生成指标 JSON + 波形 PNG + 汇总网格图 + 归档记录.md |
| `verify_and_delete.py` | 按账本 SHA256 核验后删除 raw（核验不通过绝不删） |
| `batch_ms_xsp.ps1` / `batch2_ms_xsp.ps1` / `batch3_workspace.ps1` | 批量驱动器 |
| `fix_ledger_gaps.py` / `register_truncated_ops.py` | 补录脚本 |

命令（本机 python）：
```
python raw_archive.py raw_summary <含raw目录> <归档输出目录>
python verify_and_delete.py <归档记录.md> <含raw目录> --delete
```

## 分档执行账

| 档 | 范围 | 状态 | 账本 |
|---|---|---|---|
| A | tmp 13.5GB、debug 留档件、ms_xsp 根目录 out_*.raw | ✅ 已删除（7 文件 13.35GB） | [A档删除总账.md](A档删除总账.md) |
| B/C | ms_xsp 全部（除 D 档）、workspace 历史阶段 | ✅ 已删除（含截断 op.raw 2 件、collision 冲突件 2 件） | 各目录下 `*_归档\归档记录.md`（见下方清单） |
| D | ms_xsp\stage3_acceptance（S03 冻结验收 raw） | 🔒 保留到最终验收结束 | — |
| 活跃 | stage_am_alt1/alt2/alt3 的 results raw（今晚还在跑） | ⏸ 暂缓，阶段结束后走 B/C 流程 | — |

## B/C 档归档目录清单

ms_xsp（按批处理顺序）：
- `s05_lc_20261030_归档`（38）、`s05_parts_20261030_attempt01_归档`（39，作废批）
- `s05_parts_20261030_归档`（23）、`s05_measurement_20261030_归档`（4）
- `v3_20k_归档`（2）、`v4_lm393_归档`（8）、`s04_power_20261016_归档`（2）
- `s04_poly_20261016_verified_归档`（3）、`s04_3904_20261029_归档`（7）
- `s04_c518062_20261016_归档`（7）、`s04_crosscheck_20261017_归档`（6）
- `repair_20261011_归档`（2）、`s05_parts_tran_20261030_归档`（49）
- `s05_gain_20261030_归档`（88）、`s05_blocker_20261029_归档`（154）
- `s05_receiver_20261029_归档`（127）、`s05_selectivity_20261029_归档`（79）
- `ms_collision_归档`（2，冲突隔离件）

workspace（前缀 `ws_`，相对 simulation\ 的路径用 `__` 分隔）：
- `ws_low_frequency_归档`（23）、`ws_rf_归档`（8，含 LTspice 截断 op.raw 1 件）
- `ws_v4_hardware__stage_am_ad835_1__results_归档`（102）
- `ws_v4_hardware__stage_am_ad835_2__ltspice_netlist_归档`（2，含截断 op.raw 1 件）
- `ws_v4_hardware__stage_am_ad835_2__netlists_归档`（1）
- `ws_v4_hardware__stage_am_ad835__results_归档`（3）
- `ws_v4_hardware__stage4_rf_oscillator__am_modulator_review_20261113_归档`（14）
- `ws_v4_hardware__stage4_rf_oscillator__AM01_2N3904_20261113_归档`（1）
- `ws_v4_hardware__stage4_rf_oscillator__AM01_2N3904_20261113__results__raw_归档`（24）
- `ws_v4_hardware__stage4_rf_oscillator__AM02_3_second_stage_20261113__results_归档`（587）
- `ws_v4_hardware__stage4_rf_oscillator__AM02_3_second_stage_20261113__results__raw_归档`（49）

> 括号内为已删除 raw 数量。每份归档含：`归档记录.md`（SHA256 全表）、`metrics\*.json`（分段指标）、`figures\*.png`（逐文件波形）、`figures\汇总网格图.png`。

## 特殊处理说明

1. **截断文件**（`rf_chain.op.raw`、`AD835_Behav_Model.op.raw`）：LTspice 操作点输出写盘中断，数据段不完整。已登记头部信息 + SHA256（账本状态"仅登记（数据截断）"）后删除；波形不可复现，但同类 .op 数据在对应 .log 与阶段报告中均有结论。
2. **长度微缺文件**（3 个，差 1~9 字节）：按完整点数降级读取，指标与图均正常生成。
3. **NaN/Inf**：部分 LTspice 瞬态含发散残留，指标与绘图已过滤（绘图上限 1e12）。
4. **账本中"文件缺失"**：verify_and_delete 对已删行报 MISSING 属正常（账本保留全量历史，重复执行幂等）。
5. **第一批旧账**：`s05_*_归档\归档记录_第一批_含已删.md` 为解析器修复前的手工账备份，仅留档。

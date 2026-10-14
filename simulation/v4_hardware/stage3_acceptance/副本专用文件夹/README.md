# 副本专用文件夹（S03-04 专用）

> 2026-10-14更正：短窗矩阵来自COM，5/7/9 ms与2 Vpp用例来自命令行引擎。GUI冷启动20 μs最初在225.797635 ns失败；只读诊断定位根因为GUI入口默认reltol=1e-4/trtol=1过紧（非步长上限），改RELTOL=1e-3/TRTOL=7后原生GUI跑满20 μs（20,038点/曲线），前置检查解除。TSTART短窗对照经本机实测有效（重叠区逐位相同）。9 ms尾段跑通：偏置速率以τ≈1.005 ms衰减，外推最终差标称0.0155%<0.1%（外推非实测；末五周期0.0447%通过是短窗假象）。12 ms尾段失败归因未定（遗留GUI实例干扰；已排除全局TSTOP上限）。2 Vpp线性（预充电+尾段）运行中。S03-04未验收。报告：[GUI与加权复核](gui_evidence_20261014/S03_04_GUI与加权复核报告.md)、[GUI失败诊断](gui_diagnosis_20261014/GUI失败原因诊断报告.md)、[GUI冷启动20 μs成功](gui_evidence_20261014/GUI冷启动20us成功报告.md)、[TSTART对照](engine_acceptance_20261014/TSTART短窗对照报告.md)、[9 ms稳定性](cold9ms_20261014/冷启动9ms稳定性报告.md)、[TSTOP诊断与线性度设计](final2_20261014/TSTOP诊断与线性度设计.md)。状态文档另已备份后更正，源工程与旧原始波形不变。

用途：S03-04 排查的全部工作都在本目录内进行。**上级目录的源工程与既有证据文件未被改动。**

## 目录结构

| 目录 | 内容 |
|---|---|
| `原始只读引用/` | 11 份权威源文件的逐字节副本 + 4 份文档原始副本（改动前备份），SHA-256 已核对 |
| `工作副本/` | 本次生成的工程副本（TSTEP/TMAX 变体、2 ms 探针）及其解码 XML |
| `engine/` | 引擎命令、网表、清单 JSON |
| `api_logs/`、`ab_runs/`、`confirm/` | 运行日志与重复性输出 |
| `gui_evidence_20261014/` | GUI 失败与成功（reltol=1e-3）两轮原生运行证据、截图、实际网表、审计 JSON、`records_before/` |
| `gui_diagnosis_20261014/` | GUI 失败只读诊断脚本与报告、reltol=1e-3 成功对照分析、`records_before_sync/`（本轮记录同步前备份） |
| `engine_acceptance_20261014/` | 4 个隔离验收用例输入（TSTART×2 已跑通；9 ms×2 输入备用，实际 9 ms 运行在 `cold9ms_20261014/`）、修复版 `run_one.ps1`、TSTART 对照报告 |
| `cold9ms_20261014/` | 冷启动 9 ms 尾段运行与稳定性分析（τ 拟合、外推投影、验证脚本、报告） |
| `final2_20261014/` | 12 ms 尝试与 TSTOP 上限诊断、2 Vpp 线性用例（`LIN_2Vpp_tail`/`REF_4Vpp_tail`）输入与分析脚本 |

## 有效证据（可直接引用）

| 文件 | 内容 |
|---|---|
| `S03_04_步骤1_控制行差集.md` | 历史请求文本差集；**不等于**有效设置一致（诊断已证明引擎忽略`.options`，两者生效容差不同） |
| `S03_04_冷启动排查记录_更新.md` | 排查记录全文（已复制为上级 `S03_04_冷启动排查记录.md`） |
| `gui_diagnosis_20261014/GUI失败原因诊断报告.md` | GUI冷启动失败根因：入口默认reltol=1e-4/trtol=1过紧；225.806 ns（第7载波周期）为电路固有收敛危机 |
| `gui_evidence_20261014/GUI冷启动20us成功报告.md` + `S03_GUI_COLD_20us_reltol1e3.gra` | 仅改RELTOL=1e-3/TRTOL=7后原生GUI跑满20 μs（20,038点/曲线），单变量对照 |
| `engine_acceptance_20261014/TSTART短窗对照报告.md` + `tstart_comparison.json` | TSTART本机实测：尾段与全窗重叠区逐位相同，9 ms保存量降约18× |
| `cold9ms_20261014/冷启动9ms稳定性报告.md` + `cold9ms_final.json`、`tau_final.json` | 9 ms尾段：漂移速率11.9058 mV/ms、局部τ≈1.005 ms、外推最终差标称−0.7446 mV（0.0155%）；外推非实测 |
| `final2_20261014/TSTOP诊断与线性度设计.md` | 12 ms失败归因未定（遗留实例干扰）；PROBE_rc_20ms证明无全局TSTOP上限；2 Vpp改预充电+尾段设计 |
| `../../../项目管理/交接_S03-04收尾_20261014.md` | 并行会话自包含交接文档：平台约束、运行器用法、待跑任务与开放决策项 |
| `S03_04_cold_vs_nominal.png` | 冷启动 vs 预充电标称对比图 |
| `matrix3_results.json`、`confirm/` | TSTEP/TMAX 单变量矩阵，各重复 2 次 |
| `engine/manifest_stepmap.json` + `M_*.raw` | 上限映射（实际接受步长） |
| `engine/manifest_2ms.json` + `Z_2ms_1ns.raw` | 零初值 2 ms 运行（2,023,504 点） |
| `startup_characterisation.json`、`cold_trend.py` | 冷启动 2 ms 偏置分析（时间常数约 1.03 ms） |
| `cold_start_5ms_analysis.json`、`cold_vs_nominal5ms.py` | 历史普通样本平均分析；4.218 ms为最后一次低于1 V的事件，不是稳定时间 |
| `S03_04_cold_5ms_vs_nominal.png` | 冷启动 5 ms vs 预充电标称 5 ms 对比图 |
| `cold_5ms_1ns.npz` | 5 ms 冷启动完整双精度数组（5,086,826 点） |
| `cold_7ms_1ns.npz` | 7 ms 冷启动完整双精度数组（7,127,505 点；加权复核未通过重复性筛查） |
| `cold_start_7ms_analysis.json`、`S03_04_cold_7ms_convergence.png` | 历史普通样本平均分析；“6.5 ms稳定／通过”已撤回，以本轮时间加权结果为准 |
| `engine/manifest_7ms.json` + `L_7ms_1ns.raw` | 7 ms 冷启动原始波形（7,127,505 点，引擎暂存区） |
| `engine/manifest_10ms.json` | 10 ms 冷启动：**失败**，`Internal simulation error`，无波形 |
| `engine/manifest_syntax/rc3/lte/order/scan.json` | 已测选项通道现象；不证明GUI与引擎有效配置相同 |
| `工作副本/V_*.ms14` | 四个 TSTEP/TMAX 组合的工程副本 |
| `工作副本/S03_COLD_ZERO_GEAR500_UIC_TMAX1ns_2ms.ms14` | 通过配置的 2 ms 副本 |

## 作废证据（不得引用）

以下是排查过程中的失败尝试，网表或参数有误，**结论无效**，仅留作过程记录：

- `R*`、`S*` 系列引擎试验：首个网表行被 Multisim 当成元件（`Not enough nodes`/`invalid combination of resistor parameters`），实际跑的是被删空的电路。
- `T*`、`U*`、`X*`、`Y*`、`V*`、`O*` 系列引擎试验：目的是探测 `set`/`.options` 通道；其“全部逐位相同”的结论**有效**（见第 5 节），但**不能**用来判定求解设置是否影响 GUI。
- `repro_*.ms14`、`roundtrip_*.ms14`、`enc_*.ms14`：编码器开发期产物；`repro_GEAR500_UIC.ms14` 已验证忠实（复现 225 ns 停下），其余未逐项验证。
- `matrix_results.json`、`matrix2_results.json`：脚本参数解析错误（`1e-7` 被当成 1），结果无效；有效版本为 `matrix3_results.json`。

## 工程级修改的可行做法（本次建立）

1. 解码 `.ms14`（`decode_ms14.mjs`）得到 XML；
2. 字节级只替换目标字符串（长度不变，避免破坏容器分块）；
3. 重新编码（`mkms14.mjs`，PKWare implode / binary / large / 900000 字节分块）；
4. 用 Multisim 打开，核对组件数（45）与网表；
5. 再运行。

注意：编码出的容器 Multisim **能打开**，但 `ReportNetlist` 的输出格式与原生报告不同（列宽、标题），不能据此判定不一致；判定忠实性应看**功能行为**（`repro_GEAR500_UIC.ms14` 复现了 225 ns 停下）。

# 副本专用文件夹（S03-04 专用）

> 2026-10-14更正：短窗矩阵来自COM，5/7 ms来自命令行引擎。本轮GUI点击20 μs在225.797635 ns失败；7 ms末五周期偏置跨度0.3193%，S03-04未通过。[最新报告](gui_evidence_20261014/S03_04_GUI与加权复核报告.md)。状态文档另已备份后更正，源工程与旧原始波形不变。

用途：S03-04 排查的全部工作都在本目录内进行。**上级目录的源工程与既有证据文件未被改动。**

## 目录结构

| 目录 | 内容 |
|---|---|
| `原始只读引用/` | 11 份权威源文件的逐字节副本 + 4 份文档原始副本（改动前备份），SHA-256 已核对 |
| `工作副本/` | 本次生成的工程副本（TSTEP/TMAX 变体、2 ms 探针）及其解码 XML |
| `engine/` | 引擎命令、网表、清单 JSON |
| `api_logs/`、`ab_runs/`、`confirm/` | 运行日志与重复性输出 |

## 有效证据（可直接引用）

| 文件 | 内容 |
|---|---|
| `S03_04_步骤1_控制行差集.md` | 历史请求文本差集；不等于有效设置一致 |
| `S03_04_冷启动排查记录_更新.md` | 排查记录全文（已复制为上级 `S03_04_冷启动排查记录.md`） |
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

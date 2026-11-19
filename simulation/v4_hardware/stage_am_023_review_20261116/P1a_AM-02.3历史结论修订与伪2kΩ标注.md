# P1a｜AM-02.3 历史结论修订与伪 2 kΩ 数据标注（勘误，不改写原文）

日期：2026-11-16
工作区：`D:\实验报告文件夹\电路2`
性质：**勘误与标注。原始报告、原始 CSV、原始 JSON 一字未改。** 未运行仿真。

**本文件为什么是"勘误"而不是"改原文"**：`AM02_3_second_stage_20261113/SHA256SUMS.txt` 逐字节哈希了 `AM02_3_报告.md`、`AM02_3_matrix.csv`、`results/final_matrix.json`、`results/load2k_matrix.json`。项目既定规则是「历史网表、报告和原始结果不改写」。改原文件会让 1,530 项的哈希台账失效，等于销毁完整性证据。因此本轮采取**追加勘误 + 独立标注文件**，原文保持可校验。

核验：`py -3 simulation\v4_hardware\stage_am_023_review_20261116\verify_revision.py`（98/98 通过）。

---

## 1. 修订一：撤销"课程验收失败"判定

### 1.1 原文（保持原样，供追溯）

`AM02_3_报告.md:3`：

> 日期：2026-11-13　阶段：AM-02.3　结论状态：**未通过 50 Ω / 2.0 Vpp 验收，判定 AM-02 不完成**

`AM02_3_报告.md:248`：

> **AM-02 不完成。** 第二级在 50 Ω 上只能给出 0.386 Vpp（S3）/ 0.574 Vpp（S6），距 2.0 Vpp 分别差 14.3 / 10.9 dB。

### 1.2 修订后的表述

> **原判定所依据的两个数均无课程原文依据，故"课程验收失败"不成立。**
> - **2.0 Vpp** 来自冻结 POLY 模型的代数结果：`V(TP3) = Vc×(0.6+0.1×Vm)`，`Vc` 峰值 1 V、`Vm` 高电平 4 V → 高平台 ±1 V = 2.0 Vpp（`final_actual.cir:268`；`review_candidate.py:220`）。这是**仿真模型的代数性质**，不是课程条款，也不是实物测量。
> - **50 Ω** 来自一次性候选负载试验（`review_candidate.py:201 rload="50"`），经 `AM01_报告.md:45` 一句"末级都必须能向 50 Ω 提供 1.6 Vpp"升格为准入条件，最终由 `am023_lib.py:201` 的 `"rload": 50.0` 与 `measure(..., load_r=50.0)` 固化为**库的默认值**。全程没有任何一次记录选择 50 Ω 的理由，也没有指向教师条文的引用。
> - 课程原文（`电子线路实验评分标准-学生.docx`）中 `Ω/ohm/欧/负载/终端/匹配/阻抗` **零命中**，`2.0/包络/调制度/调制指数` **零命中**。v3 的正式判据只有「明显失真」与「载波中心频率漂移」两项。
>
> **正确归类：AM-02.3 未通过的是"当时自行指定的历史工程测试条件"，不是课程验收。**

### 1.3 同时保留的部分（不可连带撤销）

撤销的是**判定**，不是**数据**。以下全部继续有效：

| 保留项 | 关键数据 | 出处 |
|---|---|---|
| 50 Ω 下的实测结果 | S3 高/低包络 0.3857 / 0.2268 Vpp，m 25.95% | `load2k_matrix.json` |
| 14.3 dB 这个数 | `20·log10(2.0/0.385693) = 14.296 dB` | 本文复算 |
| 五个拓扑的全表 | S1/S2/S3/S4/S6 的增益、输入阻抗、等效并联电容 | `topology_table.json` |
| 两个负输入电阻 | S1 −87.7 − j264.9 Ω、S4 −40.5 − j132.1 Ω（含注入自检 50.00−j0.05、99.6+j99.9） | `AM02_3_报告.md:107` |
| **S6 在 2 kΩ 起振** | 47.7 mVpp、m=−1.05%、THD 91.9%、功耗 101→197 mW | `AM02_3_报告.md:194–197` |
| S1 起振 | 集电极 −3.15…21.29 V、THD 62.4% | `cascade_candidates.json` |
| S4 压缩 | 0.54 Vpp 时 m 塌到 7.88% | `AM02_3_报告.md:121` |
| 逐节点调制指数不丢 | `out`→`rl` 全程 26.7–26.9% | `AM02_3_报告.md:130–136` |
| 增益上限论证 | `gm·R_L` 在 5 V/10 mW 下最多 43.7 dB | `AM02_3_报告.md:151` |
| 整机功耗 413 mW | 对应课程「功耗小于0.5W」 | `AM02_3_报告.md:238` |
| 两个实质性 bug 的修正 | 耦合电容初值按 `v(mod)−v(b2ac)`（残差 991 mV→0.05 mV）；`out` 节点需 `RLK 10k` | `AM02_3_报告.md:47–48` |

**特别强调**：`S6 在 2 kΩ 起振` 这一条**价值反而上升**了。它是"只测一个负载会得出错误结论"的直接反例，且与 50 Ω 无关——因为撤销 50 Ω 后，2 kΩ 这类中等阻抗反而更接近真实天线量级。详见 `AM02_3_报告.md:197` 原文：「这一点在 50 Ω 上是看不到的——**只测一个负载会得出错误结论**」。

### 1.4 一句话替换

原「未通过 50 Ω / 2.0 Vpp 验收，判定 AM-02 不完成」应读作：

> **「在 50 Ω∥10 pF 这一历史工程测试条件下，S3 的高包络为 0.386 Vpp，距该条件自设的 2.0 Vpp 目标差 14.3 dB；该目标与负载条件均无课程原文依据，故不构成课程验收判定。调制链路、功耗、稳定性方面的技术结论继续有效，其中 S6 的负载相关起振与 S4 的压缩是保留的工程风险。」**

---

## 2. 修订二：伪 2 kΩ 数据的标注

### 2.1 缺陷机制

`run_final_matrix.py` 想把 S3 跑 50 Ω 和 2 kΩ 两档：

```python
20 : CONFIGS = {
21 :     "S3": ({..., "lrfc": 2.2e-6, "reb": 180.0}, [50.0, 2000.0]),
...
31 :     tag = f"mx_{top}_{int(load)}_{amp:g}_{int(duty*100)}"
32 :     solve = M.solve_cap(top, stage, amp, duty, tag=tag, stop_us=45.0, max_iter=4)
37 :     m = M.measure(M.RESULTS / (tag + ".raw"), top, duty, p0_us=75.0, load_r=load)
```

`load` 只进了**文件名（:31）**和**测量元数据（:37）**，而 `stage` 字典（:20–21）从不含 `rload`。因此 `am023_lib.py:201` 的 `"rload": 50.0` 默认值永远生效。

**网表级铁证**：

| 文件 | 第 38 行 | 文件名声称 |
|---|---|---|
| `netlists/mx_S3_50_4_50.cir` | `RLD rl 0 50` | 50 Ω |
| `netlists/mx_S3_2000_4_50.cir` | **`RLD rl 0 50`** | 2 kΩ ← **不符** |
| `netlists/ld2_S3_2000_4.cir`（`run_load2k.py` 产物） | `RLD rl 0 2000` | 2 kΩ ← 正确 |

### 2.2 逐字节证明：伪行是 50 Ω 行的重复

对 `AM02_3_matrix.csv` 中 `source=final_matrix`、`config=S3`、`duty_pct=50.0` 的 4 组配对，比较**全部物理列**（`vpp_high`、`vpp_low`、`step_vpp`、`modulation_index`、`thd_high_pct`、`supply_mw`、`cap_v`、`plateau_flatness`、`overshoot`）：

| amp | 与 50 Ω 行不同的物理列 |
|---:|---|
| 1 Vpp | **无** |
| 2 Vpp | **无** |
| 3 Vpp | **无** |
| 4 Vpp | **无** |

即：**这 4 条标 `load_ohm=2000.0` 的记录，在物理量上与 50 Ω 行完全一致**，只有 `cir_sha256`（因文件名不同）和 `netlist` 路径不同。它们不是"2 kΩ 的测量结果"，而是"同一批 50 Ω 数据的第二次登记"。

### 2.3 受影响的产物清单

| 文件 | 受影响内容 | 处置 |
|---|---|---|
| `results/final_matrix.json` | 4 条 `load_ohm=2000.0` 记录（S3 × 1/2/3/4 Vpp）实为 50 Ω | **加注**，见 §2.4；文件本身不改（受哈希保护） |
| `AM02_3_matrix.csv` | 同样 4 行，与 `load2k` 来源的 4 行真 2 kΩ 并列，同名 `2000.0` | **加注**，见 §2.4 |
| ~~`AM02_3_报告.md` §5.1~~ | **未受影响**。报告第 201 行已声明该 bug 并说明"本报告只引用重跑结果"；§5.1 表格数值经逐字段核对取自 `load2k_matrix.json` | 无需处置 |
| `results/load2k_matrix.json` | 4 条真 2 kΩ（0.3649/0.3902/0.4154/0.4406 Vpp）+ 4 条 50 Ω | 正确，无需处置 |

**结论：报告正文没被污染，被污染的是两个交付数据文件。** 任何直接读 `final_matrix.json` 或 `AM02_3_matrix.csv` 而不读报告的人，会得到"2 kΩ 与 50 Ω 输出完全相同"的错误印象——这正是原始 bug 的表象。

### 2.4 机器可读标注

新增 `simulation/v4_hardware/stage_am_023_review_20261116/pseudo_2k_annotation.json`，逐条列出 12 行 CSV 记录（4 条伪 + 4 条真 2 kΩ + 4 条 50 Ω 对照）的判定、证据与建议读法。任何下游脚本或人工查阅应**先读该标注，再读原始 CSV**。

标注规则（可直接用于过滤）：

```python
# 读到 AM02_3_matrix.csv / final_matrix.json 后应当这样过滤
def is_genuine_2k(row):
    """只有 load2k 来源的行才是真 2 kΩ。"""
    return row["source"] == "load2k" and float(row["load_ohm"]) == 2000.0
```

对于 `final_matrix.json`（无 `source` 列），判据是**看网表**：

```python
import re, pathlib
def netlist_load(netlist_path):
    txt = pathlib.Path(netlist_path).read_text(encoding="utf-8")
    return float(re.search(r"(?im)^RLD\s+\S+\s+\S+\s+(\S+)", txt)[1])
# netlist_load(.../mx_S3_2000_4_50.cir) == 50.0  -> 该行标签不可信
```

---

## 3. 修订三：同一 50 Ω 点的两个数值（0.2 dB 不一致）

### 3.1 现象

同一标称条件（S3、50 Ω∥10 pF、4 Vpp、50%、31 MHz）在两个产物里给出不同答案：

| 产物 | 高包络 | 低包络 | m | `cap_v` | 求解设置 |
|---|---:|---:|---:|---:|---|
| `results/load2k_matrix.json`（`run_load2k.py`） | **0.385693 Vpp** | 0.226768 Vpp | 25.95% | **1.3808 V** | `max_iter=4`, `stop_us=45` |
| `results/cascade_candidates.json`（`run_cascade_candidates.py`） | **0.377037 Vpp** | 0.218082 Vpp | 26.71% | **1.1591 V** | `max_iter=5`（默认）, `stop_us=50` |

差 **0.197 dB**。根源是耦合电容周期稳态求解的收敛点不同（`cap_v` 相差 0.222 V），而两个脚本的迭代上限与终止时间不一致：

- `run_load2k.py:25` → `solve_cap(..., stop_us=45.0, max_iter=4)`
- `run_cascade_candidates.py:31` → `solve_cap(...)`，用 `am023_lib.py:384` 的默认 `max_iter=5`

### 3.2 后果

`AM02_3_报告.md` 内部并存两套缺口数字，且从未解释这 0.2 dB：

- §0.1 与 §8.1 用 0.385693 → **14.296 dB**（报告写 14.3）
- §4 表格第 120 行与 §4.1 逐节点表用 0.377037 → **14.493 dB**（报告写 14.5）

### 3.3 处置

**不改任何数值，不重跑。** 只登记事实并给出引用建议：

- 引用"到 2.0 Vpp 的缺口"时，**统一采用 `load2k_matrix.json` 的 0.385693 Vpp → 14.3 dB**，因为它是 `max_iter=4`、`stop_us=45` 的显式参数化运行，且被 §5.1 与 §8.1 引用。
- 引用"逐节点追踪表"（§4.1）时，注明该表来自 `cascade_candidates.json` 的另一次收敛运行，其绝对电平比 §5.1 低 0.2 dB，**但调制指数（26.7–26.9%）与相对结论不受影响**。
- 若要消除该不一致，需要**统一 `max_iter` 与 `stop_us` 后重跑**——属新仿真，不在本轮范围内。

---

## 4. 修订四：交付物清单的可用性说明

`AM02_3_报告.md:274–292` 列了 15 项交付物。经本轮核查，逐项状态：

| 交付物 | 状态 |
|---|---|
| `AM02_3_报告.md` | 有效，但第 3 行与第 248 行的判定须按本文 §1.2 阅读 |
| `AM02_3_topology_table.csv` | 有效 |
| `AM02_3_matrix.csv` | **含 4 行伪 2 kΩ**，须按 §2.4 过滤后使用 |
| `AM02_3_BOM.csv` / `AM02_3_BOM_changes.csv` | 有效 |
| `AM02_3_schematic.svg` | 有效 |
| `results/am01_load_sweep.json` | 有效 |
| `results/schemeA_interface.json` | 有效（Rs=149.6 Ω 反解） |
| `results/topology_table.json` | 有效 |
| `results/cascade_candidates.json` | 有效（注意其 50 Ω 点与 `load2k` 差 0.2 dB，见 §3） |
| `results/final_matrix.json` | **含 4 条伪 2 kΩ**，须按 §2.4 过滤 |
| `results/load2k_matrix.json` | 有效（真 2 kΩ 数据的唯一可靠来源） |
| `results/s6_match_sweep.json` 等三个细扫 | 有效（悬崖证据） |
| `results/am01_level_check.json` | 有效 |
| `netlists/repro_cascade_A_10000.cir` | 有效（AM-02.2 历史点复现） |
| `scripts/*.py` | 有效，但 `am023_lib.py:201` 的 `rload: 50.0` 默认值**是本次问题的根源**，下游若复用该库必须显式传入 `rload` |

**新增的下游使用规则**（写在这里，因为改不了原报告）：

> 任何复用 `am023_lib.py` 的新工作**必须**在 `stage` 字典里显式给出 `rload`，不得依赖默认值。`run_final_matrix.py` 的 bug 正是依赖了默认值。

---

## 5. 本轮没有做的事（明确边界）

| 事项 | 为什么不做 |
|---|---|
| 改 `AM02_3_报告.md` 的第 3 行判定 | 受 `SHA256SUMS.txt` 保护；项目规则是历史报告不改写 |
| 删除或覆盖 `final_matrix.json` 的伪 2 kΩ 行 | 同上。且删除会销毁"bug 曾经存在"这个证据 |
| 重跑 S3 在真 2 kΩ 下的 4 个电平 | 属新仿真。现有 `load2k_matrix.json` 已有真 2 kΩ 数据（0.3649/0.3902/0.4154/0.4406 Vpp），无需重跑 |
| 统一 `max_iter`/`stop_us` 消除 0.2 dB | 属新仿真 |
| 按新的课程口径重算 `gm·R_L` 上限 | 需等 P0 的教师答复（若 Q3 答"有幅度规定"，才需要重新立项） |
| 修改 `am023_lib.py` 的默认 `rload` | 会改变历史可复现性。改为在下游加显式参数 + 本文档的强制规则 |

---

## 6. 复现与核验

```powershell
cd D:\实验报告文件夹\电路2
py -3 simulation\v4_hardware\stage_am_023_review_20261116\verify_revision.py
py -3 simulation\v4_hardware\stage_am_023_review_20261116\verify_p1a.py
```

两个脚本都只读既有文件，不写任何产物（除 `verify_p1a.py` 的 stdout）。`verify_p1a.py` 专门核验本文的每一条结论：原文哈希未变、伪 2 kΩ 行逐字节等于 50 Ω 行、两个 50 Ω 数值的 0.197 dB 差、以及 14.3/14.5 的算式。

---

## 7. 相关文件

- 上级裁定：[AM-02.3 回溯修订：50 Ω 口径与 AM-ALT.3 目标复核](AM-02.3_回溯修订_50Ω口径与AM-ALT.3目标复核.md)
- 课程口径待确认：[P0 课程 v3 验收口径确认单](../../../项目管理/P0_课程v3验收口径确认单.md)
- 原始报告（未改动）：`simulation/v4_hardware/stage4_rf_oscillator/AM02_3_second_stage_20261113/AM02_3_报告.md`
- 机器标注：`simulation/v4_hardware/stage_am_023_review_20261116/pseudo_2k_annotation.json`
